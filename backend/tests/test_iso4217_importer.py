from scripts.update_iso4217_snapshot import build_snapshot, parse_current, parse_historical


LIST_ONE = b"""<?xml version="1.0"?>
<ISO_4217 Pblshd="2026-09-17"><CcyTbl>
<CcyNtry><CtryNm>UNITED STATES</CtryNm><CcyNm>US Dollar</CcyNm><Ccy>USD</Ccy><CcyNbr>840</CcyNbr><CcyMnrUnts>2</CcyMnrUnts></CcyNtry>
<CcyNtry><CtryNm>ECUADOR</CtryNm><CcyNm>US Dollar</CcyNm><Ccy>USD</Ccy><CcyNbr>840</CcyNbr><CcyMnrUnts>2</CcyMnrUnts></CcyNtry>
<CcyNtry><CtryNm>ARAB MONETARY FUND</CtryNm><CcyNm IsFund="true">Arab Accounting Dinar</CcyNm><Ccy>XAD</Ccy><CcyNbr>396</CcyNbr><CcyMnrUnts>2</CcyMnrUnts></CcyNtry>
<CcyNtry><CtryNm>ANTARCTICA</CtryNm><CcyNm>No universal currency</CcyNm></CcyNtry>
</CcyTbl></ISO_4217>"""

LIST_THREE = b"""<?xml version="1.0"?>
<ISO_4217 Pblshd="2026-01-01"><HstrcCcyTbl>
<HstrcCcyNtry><CtryNm>KYRGYZSTAN</CtryNm><CcyNm>Russian Ruble</CcyNm><Ccy>RUR</Ccy><CcyNbr>810</CcyNbr><WthdrwlDt>1993-01</WthdrwlDt></HstrcCcyNtry>
<HstrcCcyNtry><CtryNm>GEORGIA</CtryNm><CcyNm>Russian Ruble</CcyNm><Ccy>RUR</Ccy><CcyNbr>810</CcyNbr><WthdrwlDt>1994-04</WthdrwlDt></HstrcCcyNtry>
<HstrcCcyNtry><CtryNm>ARMENIA</CtryNm><CcyNm>Russian Ruble</CcyNm><Ccy>RUR</Ccy><CcyNbr>810</CcyNbr><WthdrwlDt>1994-08</WthdrwlDt></HstrcCcyNtry>
</HstrcCcyTbl></ISO_4217>"""


def test_current_import_groups_countries_and_preserves_fund_flag():
    published, entries = parse_current(LIST_ONE)
    assert published == "2026-09-17"
    assert len(entries) == 2
    usd = next(row for row in entries if row["code"] == "USD")
    assert usd["countries"] == ["UNITED STATES", "ECUADOR"]
    fund = next(row for row in entries if row["code"] == "XAD")
    assert fund["fund"] is True


def test_historical_import_keeps_country_specific_withdrawal_dates():
    published, entries = parse_historical(LIST_THREE)
    assert published == "2026-01-01"
    assert len(entries) == 3
    assert {(row["withdrawn"], row["countries"][0]) for row in entries} == {
        ("1993-01", "KYRGYZSTAN"),
        ("1994-04", "GEORGIA"),
        ("1994-08", "ARMENIA"),
    }
    assert all(row["minor_unit_exponent"] is None for row in entries)


def test_snapshot_builder_records_release_and_authoritative_source():
    snapshot = build_snapshot(LIST_ONE, LIST_THREE)
    assert snapshot["registry_release"] == "SIX-ISO4217-L1-2026-09-17+L3-2026-01-01"
    assert snapshot["source"]["authority"] == "ISO 4217 Maintenance Agency"
