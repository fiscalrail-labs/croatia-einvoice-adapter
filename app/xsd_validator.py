from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from lxml import etree


@dataclass
class XsdStatus:
    ready: bool
    detail: str
    schema_path: str | None = None
    source_sha256: str | None = None


class UblXsdValidator:
    def __init__(self) -> None:
        self._schema: etree.XMLSchema | None = None
        self._lock = Lock()
        self._status = XsdStatus(False, "not loaded")

    @property
    def status(self) -> XsdStatus:
        return self._status

    def load(self) -> None:
        root = Path(os.getenv("UBL_XSD_ROOT", "/opt/fiscalrail/ubl"))
        marker = root / "invoice-schema.path"
        try:
            if marker.exists():
                schema_path = Path(marker.read_text(encoding="utf-8").strip())
            else:
                schema_path = next(root.rglob("UBL-Invoice-2.1.xsd"))
            parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
            document = etree.parse(str(schema_path), parser)
            self._schema = etree.XMLSchema(document)
            sha_file = root / "source.sha256"
            sha = sha_file.read_text(encoding="utf-8").strip() if sha_file.exists() else None
            self._status = XsdStatus(True, "ready", str(schema_path), sha)
        except Exception as exc:
            self._schema = None
            self._status = XsdStatus(False, str(exc))

    def validate(self, xml: str) -> list[dict[str, object]]:
        if self._schema is None:
            raise RuntimeError(f"UBL XSD validator unavailable: {self._status.detail}")
        if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
            return [{
                "rule_id": "SEC-XML-1",
                "severity": "fatal",
                "profile": "security",
                "business_terms": [],
                "path": "/",
                "line": None,
                "column": None,
                "message": "DOCTYPE and entity declarations are not accepted",
                "hint": "Remove DTD and entity declarations.",
            }]
        parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
        try:
            document = etree.fromstring(xml.encode("utf-8"), parser)
        except etree.XMLSyntaxError as exc:
            return [{
                "rule_id": "XML-WELLFORMED",
                "severity": "fatal",
                "profile": "xsd",
                "business_terms": [],
                "path": "/",
                "line": exc.lineno,
                "column": exc.position[1] if exc.position else None,
                "message": str(exc),
                "hint": "Correct the XML syntax before running business-rule validation.",
            }]
        with self._lock:
            valid = self._schema.validate(document)
            errors = list(self._schema.error_log)
        if valid:
            return []
        findings: list[dict[str, object]] = []
        for index, error in enumerate(errors[:200], start=1):
            findings.append({
                "rule_id": f"UBL-XSD-{error.type_name or index}",
                "severity": "fatal",
                "profile": "ubl-xsd",
                "business_terms": [],
                "path": error.path or "/",
                "line": error.line,
                "column": error.column,
                "message": error.message,
                "hint": "Make the document conform to the official Croatian UBL 2.1 schema.",
            })
        return findings
