from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from lxml import etree

from .models import InvoiceRequest, Party


INV_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CAC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CUSTOMIZATION_ID = (
    "urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.hr:cius-2025:1.0"
    "#conformant#urn:mfin.gov.hr:ext-2025:1.0"
)
NSMAP = {None: INV_NS, "cac": CAC_NS, "cbc": CBC_NS}


def q(namespace: str, local: str) -> str:
    return f"{{{namespace}}}{local}"


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def decimal_text(value: Decimal, places: int = 2) -> str:
    quantum = Decimal("1").scaleb(-places)
    return format(value.quantize(quantum, rounding=ROUND_HALF_UP), f".{places}f")


def add_text(parent: etree._Element, namespace: str, name: str, value: Any, **attrs: str) -> etree._Element:
    child = etree.SubElement(parent, q(namespace, name), **attrs)
    child.text = str(value)
    return child


def add_party(parent: etree._Element, party: Party) -> None:
    party_node = etree.SubElement(parent, q(CAC_NS, "Party"))
    add_text(party_node, CBC_NS, "EndpointID", party.oib, schemeID="9934")

    postal = etree.SubElement(party_node, q(CAC_NS, "PostalAddress"))
    add_text(postal, CBC_NS, "StreetName", party.address.street)
    add_text(postal, CBC_NS, "CityName", party.address.city)
    add_text(postal, CBC_NS, "PostalZone", party.address.postal_code)
    country = etree.SubElement(postal, q(CAC_NS, "Country"))
    add_text(country, CBC_NS, "IdentificationCode", party.address.country_code)

    tax_scheme = etree.SubElement(party_node, q(CAC_NS, "PartyTaxScheme"))
    add_text(tax_scheme, CBC_NS, "CompanyID", f"HR{party.oib}")
    tax = etree.SubElement(tax_scheme, q(CAC_NS, "TaxScheme"))
    add_text(tax, CBC_NS, "ID", "VAT")

    legal = etree.SubElement(party_node, q(CAC_NS, "PartyLegalEntity"))
    add_text(legal, CBC_NS, "RegistrationName", party.name)


def calculate_totals(invoice: InvoiceRequest) -> dict[str, Decimal]:
    net_by_rate: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for line in invoice.lines:
        net_by_rate[line.vat_rate] += money(line.quantity * line.unit_price)

    net_total = money(sum(net_by_rate.values(), Decimal("0")))
    tax_by_rate = {
        rate: money(net * Decimal(rate) / Decimal("100"))
        for rate, net in net_by_rate.items()
    }
    tax_total = money(sum(tax_by_rate.values(), Decimal("0")))
    gross_total = money(net_total + tax_total)
    return {
        "net_total": net_total,
        "tax_total": tax_total,
        "gross_total": gross_total,
        "payable_total": gross_total,
        **{f"net_{rate}": net for rate, net in net_by_rate.items()},
        **{f"tax_{rate}": tax for rate, tax in tax_by_rate.items()},
    }


def build_invoice_xml(invoice: InvoiceRequest) -> tuple[str, dict[str, str]]:
    totals = calculate_totals(invoice)
    root = etree.Element(q(INV_NS, "Invoice"), nsmap=NSMAP)

    add_text(root, CBC_NS, "CustomizationID", CUSTOMIZATION_ID)
    add_text(root, CBC_NS, "ProfileID", invoice.profile_id)
    add_text(root, CBC_NS, "ID", invoice.invoice_number)
    add_text(root, CBC_NS, "IssueDate", invoice.issue_date.isoformat())
    add_text(root, CBC_NS, "IssueTime", invoice.issue_time.strftime("%H:%M:%S"))
    add_text(root, CBC_NS, "DueDate", invoice.due_date.isoformat())
    add_text(root, CBC_NS, "InvoiceTypeCode", "380")
    add_text(root, CBC_NS, "DocumentCurrencyCode", invoice.currency)

    supplier = etree.SubElement(root, q(CAC_NS, "AccountingSupplierParty"))
    add_party(supplier, invoice.supplier)
    seller_contact = etree.SubElement(supplier, q(CAC_NS, "SellerContact"))
    add_text(seller_contact, CBC_NS, "ID", invoice.supplier.oib)
    add_text(seller_contact, CBC_NS, "Name", invoice.supplier_operator_name)

    customer = etree.SubElement(root, q(CAC_NS, "AccountingCustomerParty"))
    add_party(customer, invoice.customer)

    delivery = etree.SubElement(root, q(CAC_NS, "Delivery"))
    add_text(
        delivery,
        CBC_NS,
        "ActualDeliveryDate",
        (invoice.delivery_date or invoice.issue_date).isoformat(),
    )

    payment = etree.SubElement(root, q(CAC_NS, "PaymentMeans"))
    add_text(payment, CBC_NS, "PaymentMeansCode", "30")
    add_text(payment, CBC_NS, "PaymentID", invoice.payment_id)
    account = etree.SubElement(payment, q(CAC_NS, "PayeeFinancialAccount"))
    add_text(account, CBC_NS, "ID", invoice.supplier_iban)

    tax_total = etree.SubElement(root, q(CAC_NS, "TaxTotal"))
    add_text(
        tax_total,
        CBC_NS,
        "TaxAmount",
        decimal_text(totals["tax_total"]),
        currencyID=invoice.currency,
    )

    rates = sorted({line.vat_rate for line in invoice.lines})
    for rate in rates:
        subtotal = etree.SubElement(tax_total, q(CAC_NS, "TaxSubtotal"))
        add_text(
            subtotal,
            CBC_NS,
            "TaxableAmount",
            decimal_text(totals[f"net_{rate}"]),
            currencyID=invoice.currency,
        )
        add_text(
            subtotal,
            CBC_NS,
            "TaxAmount",
            decimal_text(totals[f"tax_{rate}"]),
            currencyID=invoice.currency,
        )
        category = etree.SubElement(subtotal, q(CAC_NS, "TaxCategory"))
        add_text(category, CBC_NS, "ID", "S")
        add_text(category, CBC_NS, "Percent", rate)
        scheme = etree.SubElement(category, q(CAC_NS, "TaxScheme"))
        add_text(scheme, CBC_NS, "ID", "VAT")

    monetary = etree.SubElement(root, q(CAC_NS, "LegalMonetaryTotal"))
    for name, key in (
        ("LineExtensionAmount", "net_total"),
        ("TaxExclusiveAmount", "net_total"),
        ("TaxInclusiveAmount", "gross_total"),
        ("PayableAmount", "payable_total"),
    ):
        add_text(
            monetary,
            CBC_NS,
            name,
            decimal_text(totals[key]),
            currencyID=invoice.currency,
        )

    for index, line in enumerate(invoice.lines, start=1):
        line_net = money(line.quantity * line.unit_price)
        invoice_line = etree.SubElement(root, q(CAC_NS, "InvoiceLine"))
        add_text(invoice_line, CBC_NS, "ID", index)
        add_text(
            invoice_line,
            CBC_NS,
            "InvoicedQuantity",
            decimal_text(line.quantity, 3),
            unitCode=line.unit_code,
        )
        add_text(
            invoice_line,
            CBC_NS,
            "LineExtensionAmount",
            decimal_text(line_net),
            currencyID=invoice.currency,
        )

        item = etree.SubElement(invoice_line, q(CAC_NS, "Item"))
        add_text(item, CBC_NS, "Name", line.description)
        commodity = etree.SubElement(item, q(CAC_NS, "CommodityClassification"))
        add_text(
            commodity,
            CBC_NS,
            "ItemClassificationCode",
            line.kpd_code,
            listID="CG",
        )
        tax_category = etree.SubElement(item, q(CAC_NS, "ClassifiedTaxCategory"))
        add_text(tax_category, CBC_NS, "ID", "S")
        add_text(tax_category, CBC_NS, "Name", f"HR:PDV{line.vat_rate}")
        add_text(tax_category, CBC_NS, "Percent", line.vat_rate)
        scheme = etree.SubElement(tax_category, q(CAC_NS, "TaxScheme"))
        add_text(scheme, CBC_NS, "ID", "VAT")

        price = etree.SubElement(invoice_line, q(CAC_NS, "Price"))
        add_text(
            price,
            CBC_NS,
            "PriceAmount",
            decimal_text(line.unit_price, 6),
            currencyID=invoice.currency,
        )
        add_text(
            price,
            CBC_NS,
            "BaseQuantity",
            decimal_text(Decimal("1"), 3),
            unitCode=line.unit_code,
        )

    xml = etree.tostring(
        root,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    ).decode("utf-8")

    public_totals = {
        key: decimal_text(value)
        for key, value in totals.items()
        if key in {"net_total", "tax_total", "gross_total", "payable_total"}
    }
    return xml, public_totals
