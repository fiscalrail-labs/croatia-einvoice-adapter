from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from lxml import etree

from .models import ValidationFinding, ValidationResult, is_valid_iban, is_valid_oib
from .ubl import CAC_NS, CBC_NS, CUSTOMIZATION_ID, INV_NS, money


NS = {"ubl": INV_NS, "cac": CAC_NS, "cbc": CBC_NS}
PROFILE_RE = re.compile(r"^(P(?:[1-9]|1[0-2])|P99:.+)$")
TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}$")
KPD_RE = re.compile(r"^\d{2}\.\d{2}\.\d{2}$")


def _finding(rule_id: str, path: str, message: str, severity: str = "fatal") -> ValidationFinding:
    return ValidationFinding(rule_id=rule_id, severity=severity, path=path, message=message)


def _text(root: etree._Element, xpath: str) -> str | None:
    result = root.xpath(xpath, namespaces=NS)
    if not result:
        return None
    value = result[0]
    if isinstance(value, etree._Element):
        return value.text.strip() if value.text else None
    return str(value).strip()


def _decimal(root: etree._Element, xpath: str) -> Decimal | None:
    value = _text(root, xpath)
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _safe_parser() -> etree.XMLParser:
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        remove_comments=False,
    )


def validate_xml(xml: str) -> ValidationResult:
    findings: list[ValidationFinding] = []
    checks = [
        "secure XML parsing",
        "Croatian customization identifier",
        "Croatian document-level business rules",
        "OIB and IBAN check digits",
        "KPD line classification presence and format",
        "invoice arithmetic consistency",
        "empty XML element detection",
    ]

    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        findings.append(
            _finding("SEC-XML-1", "/", "DOCTYPE and entity declarations are not accepted")
        )
        return ValidationResult(valid=False, profile=None, findings=findings, checks_run=checks)

    try:
        root = etree.fromstring(xml.encode("utf-8"), parser=_safe_parser())
    except (etree.XMLSyntaxError, ValueError) as exc:
        findings.append(_finding("XML-WELLFORMED", "/", f"XML parsing failed: {exc}"))
        return ValidationResult(valid=False, profile=None, findings=findings, checks_run=checks)

    if root.tag != f"{{{INV_NS}}}Invoice":
        findings.append(
            _finding(
                "UBL-DOC-1",
                "/",
                "This prototype accepts only UBL 2.1 Invoice documents",
            )
        )

    customization = _text(root, "/ubl:Invoice/cbc:CustomizationID")
    if customization != CUSTOMIZATION_ID:
        findings.append(
            _finding(
                "HR-BR-5",
                "/Invoice/CustomizationID",
                "CustomizationID does not match the Croatian CIUS/extension identifier",
            )
        )

    invoice_id = _text(root, "/ubl:Invoice/cbc:ID")
    if not invoice_id:
        findings.append(_finding("EN-BR-2", "/Invoice/ID", "Invoice number is required"))
    elif re.search(r"\s", invoice_id):
        findings.append(
            _finding("HR-BR-1", "/Invoice/ID", "Invoice number must not contain whitespace")
        )

    issue_date = _text(root, "/ubl:Invoice/cbc:IssueDate")
    try:
        parsed_date = date.fromisoformat(issue_date or "")
        if not date(2026, 1, 1) <= parsed_date < date(2100, 1, 1):
            raise ValueError
    except ValueError:
        findings.append(
            _finding(
                "HR-BR-40",
                "/Invoice/IssueDate",
                "IssueDate must be an ISO date from 2026-01-01 through 2099-12-31",
            )
        )

    issue_time = _text(root, "/ubl:Invoice/cbc:IssueTime")
    valid_time = bool(issue_time and TIME_RE.fullmatch(issue_time))
    if valid_time:
        try:
            datetime.strptime(issue_time, "%H:%M:%S")
        except ValueError:
            valid_time = False
    if not valid_time:
        findings.append(
            _finding(
                "HR-BR-2",
                "/Invoice/IssueTime",
                "IssueTime is required in valid hh:mm:ss form",
            )
        )

    profile = _text(root, "/ubl:Invoice/cbc:ProfileID")
    if not profile or not PROFILE_RE.fullmatch(profile):
        findings.append(
            _finding(
                "HR-BR-34",
                "/Invoice/ProfileID",
                "ProfileID must be P1-P12 or begin with P99:",
            )
        )
    elif len(profile) > 200:
        findings.append(
            _finding("HR-BR-42", "/Invoice/ProfileID", "ProfileID exceeds 200 characters")
        )

    empty_elements = root.xpath(
        "//*[not(*) and not(normalize-space())]",
        namespaces=NS,
    )
    for element in empty_elements:
        findings.append(
            _finding(
                "HR-BR-33",
                root.getroottree().getpath(element),
                "Empty XML elements are not permitted in this prototype",
            )
        )

    oib_paths = {
        "/Invoice/AccountingSupplierParty/Party/EndpointID": "/ubl:Invoice/cac:AccountingSupplierParty/cac:Party/cbc:EndpointID",
        "/Invoice/AccountingCustomerParty/Party/EndpointID": "/ubl:Invoice/cac:AccountingCustomerParty/cac:Party/cbc:EndpointID",
    }
    for path, xpath in oib_paths.items():
        oib = _text(root, xpath)
        if not oib or not is_valid_oib(oib):
            findings.append(_finding("HR-OIB-1", path, "Missing or invalid Croatian OIB"))

    iban = _text(
        root,
        "/ubl:Invoice/cac:PaymentMeans/cac:PayeeFinancialAccount/cbc:ID",
    )
    if not iban or not iban.startswith("HR") or len(iban) != 21 or not is_valid_iban(iban):
        findings.append(
            _finding(
                "HR-IBAN-1",
                "/Invoice/PaymentMeans/PayeeFinancialAccount/ID",
                "Missing or invalid Croatian IBAN",
            )
        )

    line_nodes = root.xpath("/ubl:Invoice/cac:InvoiceLine", namespaces=NS)
    if not line_nodes:
        findings.append(_finding("EN-BR-16", "/Invoice/InvoiceLine", "At least one invoice line is required"))

    calculated_net = Decimal("0")
    calculated_tax = Decimal("0")
    for index, line in enumerate(line_nodes, start=1):
        kpd = _text(
            line,
            "./cac:Item/cac:CommodityClassification/cbc:ItemClassificationCode",
        )
        if not kpd or not KPD_RE.fullmatch(kpd):
            findings.append(
                _finding(
                    "HR-KPD-1",
                    f"/Invoice/InvoiceLine[{index}]/Item/CommodityClassification/ItemClassificationCode",
                    "A KPD code in NN.NN.NN form is required for every line",
                )
            )

        quantity = _decimal(line, "./cbc:InvoicedQuantity")
        price = _decimal(line, "./cac:Price/cbc:PriceAmount")
        stated_line = _decimal(line, "./cbc:LineExtensionAmount")
        rate = _decimal(line, "./cac:Item/cac:ClassifiedTaxCategory/cbc:Percent")
        if None in (quantity, price, stated_line, rate):
            findings.append(
                _finding(
                    "CALC-LINE-1",
                    f"/Invoice/InvoiceLine[{index}]",
                    "Quantity, unit price, line amount, and tax percentage must be numeric",
                )
            )
            continue
        expected_line = money(quantity * price)
        if money(stated_line) != expected_line:
            findings.append(
                _finding(
                    "CALC-LINE-2",
                    f"/Invoice/InvoiceLine[{index}]/LineExtensionAmount",
                    f"Line amount {stated_line} does not equal quantity x unit price ({expected_line})",
                )
            )
        calculated_net += expected_line
        calculated_tax += money(expected_line * rate / Decimal("100"))

    stated_net = _decimal(root, "/ubl:Invoice/cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount")
    stated_tax = _decimal(root, "/ubl:Invoice/cac:TaxTotal/cbc:TaxAmount")
    stated_gross = _decimal(root, "/ubl:Invoice/cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount")
    stated_payable = _decimal(root, "/ubl:Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount")

    expected_net = money(calculated_net)
    expected_tax = money(calculated_tax)
    expected_gross = money(expected_net + expected_tax)
    total_checks = (
        ("CALC-TOTAL-1", "/Invoice/LegalMonetaryTotal/TaxExclusiveAmount", stated_net, expected_net),
        ("CALC-TOTAL-2", "/Invoice/TaxTotal/TaxAmount", stated_tax, expected_tax),
        ("CALC-TOTAL-3", "/Invoice/LegalMonetaryTotal/TaxInclusiveAmount", stated_gross, expected_gross),
        ("CALC-TOTAL-4", "/Invoice/LegalMonetaryTotal/PayableAmount", stated_payable, expected_gross),
    )
    for rule_id, path, stated, expected in total_checks:
        if stated is None or money(stated) != expected:
            findings.append(
                _finding(rule_id, path, f"Amount must equal {expected}")
            )

    return ValidationResult(
        valid=not any(item.severity in {"fatal", "error"} for item in findings),
        profile=customization,
        findings=findings,
        checks_run=checks,
        production_ready=False,
    )
