#!/usr/bin/env python3
"""Refresh the bundled ISO 4217 snapshot from SIX's official XML lists.

Maintainer command (not application runtime behavior):
    python backend/scripts/update_iso4217_snapshot.py
Current List One rows are grouped by currency code. Historical List Three rows
are grouped by code AND withdrawal date because a shared currency code can have
different withdrawal dates in different jurisdictions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET


LIST_ONE_URL = (
    "https://www.six-group.com/dam/download/financial-information/"
    "data-center/iso-currrency/lists/list-one.xml"
)
LIST_THREE_URL = (
    "https://www.six-group.com/dam/download/financial-information/"
    "data-center/iso-currrency/lists/list-three.xml"
)
OFFICIAL_PAGE = (
    "https://www.six-group.com/en/products-services/financial-information/"
    "market-reference-data/data-standards.html"
)
OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "domain"
    / "data"
    / "iso4217_snapshot.json"
)


def download(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "Aurelius-ISO4217-Snapshot-Maintainer/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def text(element: ET.Element, tag: str) -> str | None:
    child = element.find(tag)
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def parse_current(xml_bytes: bytes) -> tuple[str, list[dict]]:
    root = ET.fromstring(xml_bytes)
    published = root.attrib.get("Pblshd")
    if not published:
        raise ValueError("SIX List One XML is missing its Pblshd release date")

    grouped: dict[str, dict] = {}
    for entry in root.findall(".//CcyNtry"):
        code = text(entry, "Ccy")
        name = text(entry, "CcyNm")
        if not code or not name:
            continue
        numeric = text(entry, "CcyNbr")
        raw_exponent = text(entry, "CcyMnrUnts")
        exponent = int(raw_exponent) if raw_exponent and raw_exponent.isdigit() else None
        name_element = entry.find("CcyNm")
        is_fund = (
            name_element is not None
            and name_element.attrib.get("IsFund", "").lower() == "true"
        )
        row = grouped.setdefault(
            code,
            {
                "code": code,
                "numeric_code": numeric,
                "name": name,
                "minor_unit_exponent": exponent,
                "fund": is_fund,
                "withdrawn": None,
                "countries": [],
            },
        )
        if (
            row["numeric_code"] != numeric
            or row["name"] != name
            or row["minor_unit_exponent"] != exponent
        ):
            raise ValueError(f"inconsistent duplicate ISO List One rows for {code}")
        row["fund"] = row["fund"] or is_fund
        country = text(entry, "CtryNm")
        if country and country not in row["countries"]:
            row["countries"].append(country)

    return published, [grouped[code] for code in sorted(grouped)]


def parse_historical(xml_bytes: bytes) -> tuple[str, list[dict]]:
    root = ET.fromstring(xml_bytes)
    published = root.attrib.get("Pblshd")
    if not published:
        raise ValueError("SIX List Three XML is missing its Pblshd release date")

    grouped: dict[tuple[str, str | None], dict] = {}
    for entry in root.findall(".//HstrcCcyNtry"):
        code = text(entry, "Ccy")
        name = text(entry, "CcyNm")
        if not code or not name:
            continue
        numeric = text(entry, "CcyNbr")
        withdrawn = text(entry, "WthdrwlDt")
        key = (code, withdrawn)
        row = grouped.setdefault(
            key,
            {
                "code": code,
                "numeric_code": numeric,
                "name": name,
                # List Three does not publish minor-unit exponents. Do not infer.
                "minor_unit_exponent": None,
                "fund": False,
                "withdrawn": withdrawn,
                "countries": [],
            },
        )
        if row["numeric_code"] != numeric or row["name"] != name:
            raise ValueError(
                f"inconsistent duplicate ISO List Three rows for {code} withdrawn {withdrawn}"
            )
        country = text(entry, "CtryNm")
        if country and country not in row["countries"]:
            row["countries"].append(country)

    ordered = sorted(grouped, key=lambda item: (item[0], item[1] or ""))
    return published, [grouped[key] for key in ordered]


def build_snapshot(list_one: bytes, list_three: bytes) -> dict:
    current_date, current = parse_current(list_one)
    historical_date, historical = parse_historical(list_three)
    return {
        "schema_version": 1,
        "registry_release": f"SIX-ISO4217-L1-{current_date}+L3-{historical_date}",
        "source": {
            "publisher": "SIX Group / SIX Interbank Clearing Ltd",
            "authority": "ISO 4217 Maintenance Agency",
            "official_page": OFFICIAL_PAGE,
            "list_one_url": LIST_ONE_URL,
            "list_three_url": LIST_THREE_URL,
        },
        "current_published": current_date,
        "historical_published": historical_date,
        "current": current,
        "historical": historical,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if snapshot is stale")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    snapshot = build_snapshot(download(LIST_ONE_URL), download(LIST_THREE_URL))
    rendered = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print("ISO 4217 snapshot is stale; run update_iso4217_snapshot.py")
            return 1
        print(
            f"ISO 4217 snapshot current: {len(snapshot['current'])} current codes, "
            f"{len(snapshot['historical'])} jurisdiction/date historical records, "
            f"release {snapshot['registry_release']}"
        )
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(
        f"Wrote {args.output}: {len(snapshot['current'])} current codes, "
        f"{len(snapshot['historical'])} jurisdiction/date historical records, "
        f"release {snapshot['registry_release']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
