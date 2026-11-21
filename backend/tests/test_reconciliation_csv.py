from datetime import date
import pytest

from app.domain.reconciliation_csv import (
    MAX_AMOUNT_DIGITS,
    StatementCsvError,
    parse_minor_units,
    parse_statement_csv,
)


@pytest.mark.parametrize(("value", "exponent", "expected"), [
    ("12", 2, 1200),
    ("12.3", 2, 1230),
    ("12.34", 2, 1234),
    ("-0.01", 2, -1),
    ("0", 0, 0),
    ("1.234", 3, 1234),
    ("  1.20  ", 2, 120),
])
def test_parse_minor_units_exact(value, exponent, expected):
    assert parse_minor_units(value, exponent) == expected


@pytest.mark.parametrize("value", [
    "", "1,000.00", "1.000,00", "+1.00", "1e3", "NaN", "Infinity",
    "1.", ".5", "--1", "1.001",
])
def test_parse_minor_units_rejects_noncanonical_or_excess_precision(value):
    with pytest.raises(ValueError):
        parse_minor_units(value, 2)


def test_parse_minor_units_rejects_non_string_and_invalid_exponent():
    with pytest.raises(TypeError):
        parse_minor_units(1.25, 2)
    with pytest.raises(ValueError):
        parse_minor_units("1.00", -1)


def test_parse_minor_units_caps_precision_at_38_digits():
    with pytest.raises(ValueError, match="38-digit"):
        parse_minor_units("9" * (MAX_AMOUNT_DIGITS + 1), 0)


def test_valid_csv_preserves_untrusted_description_and_returns_digest():
    raw = (
        b"booking_date,amount,currency,description,source_transaction_id,value_date,counterparty,reference\n"
        b"2026-11-21,-125.50,COP,=HYPERLINK(\"https://bad.example\"),bank-1,2026-11-22,Shop,ref-7\n"
    )
    result = parse_statement_csv(raw, currency_exponent=2, expected_currency="COP")
    assert result.is_valid
    assert result.accepted_row_count == 1
    row = result.rows[0]
    assert row.booking_date == date(2026, 11, 21)
    assert row.amount_minor_units == -12550
    assert row.description == '=HYPERLINK("https://bad.example")'
    assert row.source_transaction_id == "bank-1"
    assert row.value_date == date(2026, 11, 22)
    assert len(result.file_sha256) == 64


def test_row_level_errors_are_returned_without_accepting_invalid_row():
    raw = (
        b"booking_date,amount,currency,description\n"
        b"11/21/2026,1.001,USD,invalid\n"
        b"2026-11-21,2.00,EUR,wrong account currency\n"
    )
    result = parse_statement_csv(raw, currency_exponent=2, expected_currency="USD")
    assert result.accepted_row_count == 0
    assert result.total_data_rows == 2
    assert {(error.field, error.code) for error in result.errors} == {
        ("booking_date", "invalid_date"),
        ("amount", "invalid_amount"),
        ("currency", "currency_mismatch"),
    }


@pytest.mark.parametrize(("header", "code"), [
    ("booking_date,amount,currency,description,amount\n", "duplicate_header"),
    ("booking_date,amount,currency\n", "missing_columns"),
    ("booking_date,amount,currency,description,extra\n", "unknown_columns"),
    ("booking_date,amount,currency,description,\n", "blank_header"),
])
def test_header_validation(header, code):
    with pytest.raises(StatementCsvError) as exc:
        parse_statement_csv(header.encode(), currency_exponent=2)
    assert exc.value.code == code


def test_rejects_invalid_utf8_and_malformed_csv():
    with pytest.raises(StatementCsvError) as exc:
        parse_statement_csv(b"booking_date,amount,currency,description\n\xff", currency_exponent=2)
    assert exc.value.code == "invalid_encoding"

    malformed = b'booking_date,amount,currency,description\n2026-01-01,1.00,USD,"unfinished\n'
    with pytest.raises(StatementCsvError) as exc:
        parse_statement_csv(malformed, currency_exponent=2)
    assert exc.value.code == "malformed_csv"


def test_rejects_inconsistent_column_counts_and_oversized_fields():
    mismatch = b"booking_date,amount,currency,description\n2026-01-01,1.00,USD\n"
    result = parse_statement_csv(mismatch, currency_exponent=2)
    assert result.errors[0].code == "column_count"

    oversized = (
        b"booking_date,amount,currency,description\n2026-01-01,1.00,USD,"
        + b"x" * 4097 + b"\n"
    )
    result = parse_statement_csv(oversized, currency_exponent=2)
    assert result.errors[0].code == "field_too_large"


def test_rejects_empty_file_and_file_over_limit():
    with pytest.raises(StatementCsvError) as exc:
        parse_statement_csv(b"", currency_exponent=2)
    assert exc.value.code == "empty_file"
    with pytest.raises(StatementCsvError) as exc:
        parse_statement_csv(b"x" * (5 * 1024 * 1024 + 1), currency_exponent=2)
    assert exc.value.code == "file_too_large"


def test_bom_and_blank_lines_are_supported_deterministically():
    raw = b"\xef\xbb\xbfbooking_date,amount,currency,description\n\n2026-01-01,1.00,USD,ok\n"
    result = parse_statement_csv(raw, currency_exponent=2)
    assert result.is_valid
    assert result.rows[0].row_number == 3



def test_header_only_csv_is_rejected_as_empty_statement():
    with pytest.raises(StatementCsvError) as exc:
        parse_statement_csv(
            b"booking_date,amount,currency,description\\n",
            currency_exponent=2,
        )
    assert exc.value.code == "no_data_rows"



def test_optional_source_fields_obey_database_storage_limits():
    raw = (
        b"booking_date,amount,currency,description,source_transaction_id\n"
        + b"2026-01-01,1.00,USD,ok,"
        + b"x" * 513 + b"\n"
    )
    result = parse_statement_csv(raw, currency_exponent=2)
    assert not result.is_valid
    assert result.errors[0].field == "source_transaction_id"
    assert result.errors[0].code == "field_too_large"
