from __future__ import annotations

import re
from datetime import date, time
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


KPD_RE = re.compile(r"^\d{2}\.\d{2}\.\d{2}$")
OIB_RE = re.compile(r"^\d{11}$")
IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")


def is_valid_oib(value: str) -> bool:
    """Validate a Croatian OIB using the ISO 7064 MOD 11,10 algorithm."""
    value = value.removeprefix("HR")
    if not OIB_RE.fullmatch(value):
        return False

    intermediary = 10
    for digit in value[:10]:
        intermediary = (intermediary + int(digit)) % 10
        if intermediary == 0:
            intermediary = 10
        intermediary = (intermediary * 2) % 11

    control = 11 - intermediary
    if control == 10:
        control = 0
    return control == int(value[-1])


def is_valid_iban(value: str) -> bool:
    """Validate an IBAN using ISO 13616 MOD-97."""
    compact = re.sub(r"\s+", "", value).upper()
    if not IBAN_RE.fullmatch(compact):
        return False
    rearranged = compact[4:] + compact[:4]
    remainder = 0
    for character in rearranged:
        expanded = str(ord(character) - 55) if character.isalpha() else character
        for digit in expanded:
            remainder = (remainder * 10 + int(digit)) % 97
    return remainder == 1


Money = Annotated[Decimal, Field(max_digits=30, decimal_places=10, gt=0)]
Quantity = Annotated[Decimal, Field(max_digits=30, decimal_places=10, gt=0)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Address(StrictModel):
    street: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=2, max_length=20)
    country_code: Literal["HR"] = "HR"


class Party(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    oib: str
    address: Address

    @field_validator("oib")
    @classmethod
    def validate_oib(cls, value: str) -> str:
        normalized = value.removeprefix("HR")
        if not is_valid_oib(normalized):
            raise ValueError("Invalid Croatian OIB checksum")
        return normalized


class InvoiceLine(StrictModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Quantity
    unit_price: Money
    unit_code: str = Field(default="H87", pattern=r"^[A-Z0-9]{1,8}$")
    vat_rate: Literal[5, 13, 25] = 25
    kpd_code: str

    @field_validator("kpd_code")
    @classmethod
    def validate_kpd_code(cls, value: str) -> str:
        if not KPD_RE.fullmatch(value):
            raise ValueError("KPD code must use the six-digit NN.NN.NN form")
        return value


class InvoiceRequest(StrictModel):
    invoice_number: str = Field(min_length=1, max_length=100, pattern=r"^\S+$")
    issue_date: date
    issue_time: time
    due_date: date
    delivery_date: date | None = None
    profile_id: str = Field(default="P1", pattern=r"^(P(?:[1-9]|1[0-2])|P99:.+)$", max_length=200)
    currency: Literal["EUR"] = "EUR"
    supplier: Party
    customer: Party
    supplier_operator_name: str = Field(default="Automated system", min_length=1, max_length=100)
    payment_id: str = Field(min_length=1, max_length=100)
    supplier_iban: str
    lines: list[InvoiceLine] = Field(min_length=1, max_length=500)

    @field_validator("supplier_iban")
    @classmethod
    def validate_iban(cls, value: str) -> str:
        compact = re.sub(r"\s+", "", value).upper()
        if not compact.startswith("HR") or len(compact) != 21 or not is_valid_iban(compact):
            raise ValueError("A valid 21-character Croatian IBAN is required")
        return compact

    @model_validator(mode="after")
    def validate_dates(self) -> "InvoiceRequest":
        if self.issue_date < date(2026, 1, 1) or self.issue_date >= date(2100, 1, 1):
            raise ValueError("issue_date must be between 2026-01-01 and 2099-12-31")
        if self.due_date < self.issue_date:
            raise ValueError("due_date cannot precede issue_date")
        if self.delivery_date and self.delivery_date >= date(2100, 1, 1):
            raise ValueError("delivery_date must be before 2100-01-01")
        return self


class XmlValidationRequest(StrictModel):
    xml: str = Field(min_length=1, max_length=2_000_000)


class ValidationFinding(StrictModel):
    rule_id: str
    severity: Literal["fatal", "error", "warning"]
    path: str
    message: str


class ValidationResult(StrictModel):
    valid: bool
    profile: str | None
    findings: list[ValidationFinding]
    checks_run: list[str]
    production_ready: bool = False


class PreflightResponse(StrictModel):
    xml: str
    validation: ValidationResult
    totals: dict[str, str]
