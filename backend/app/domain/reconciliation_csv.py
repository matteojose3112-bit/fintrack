"""Pure, bounded CSV statement parser for FinTrack reconciliation.

This module performs validation only. It never writes ledger records, infers
journal entries, normalizes untrusted descriptions, or converts currencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import hashlib
import io
import re
from typing import Final


REQUIRED_COLUMNS: Final = frozenset({"booking_date", "amount", "currency", "description"})
OPTIONAL_COLUMNS: Final = frozenset({
    "source_transaction_id", "value_date", "counterparty", "reference"
})
ALLOWED_COLUMNS: Final = REQUIRED_COLUMNS | OPTIONAL_COLUMNS
MAX_FILE_BYTES: Final = 5 * 1024 * 1024
MAX_ROWS: Final = 50_000
MAX_COLUMNS: Final = 32
MAX_FIELD_CHARS: Final = 4_096
MAX_AMOUNT_DIGITS: Final = 38
_DATE_PATTERN: Final = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_AMOUNT_PATTERN: Final = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")


@dataclass(frozen=True, slots=True)
class StatementRow:
    row_number: int
    booking_date: date
    amount_minor_units: int
    currency: str
    description: str
    source_transaction_id: str | None = None
    value_date: date | None = None
    counterparty: str | None = None
    reference: str | None = None
    source_payload: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class RowError:
    row_number: int
    field: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class CsvParseResult:
    file_sha256: str
    rows: tuple[StatementRow, ...]
    errors: tuple[RowError, ...]
    headers: tuple[str, ...]
    total_data_rows: int
    currency_exponent: int

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def accepted_row_count(self) -> int:
        return len(self.rows)


class StatementCsvError(ValueError):
    """File-level CSV validation failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_minor_units(value: str, exponent: int) -> int:
    """Parse a canonical decimal string into exact integer minor units."""
    if not isinstance(value, str):
        raise TypeError("amount must be supplied as a string")
    if isinstance(exponent, bool) or not isinstance(exponent, int) or exponent < 0:
        raise ValueError("currency exponent must be a non-negative integer")

    amount = value.strip()
    if not amount or not _AMOUNT_PATTERN.fullmatch(amount):
        raise ValueError("amount must use canonical decimal notation")
    unsigned = amount[1:] if amount.startswith("-") else amount
    whole, dot, fraction = unsigned.partition(".")
    digits = whole + fraction
    if len(digits) > MAX_AMOUNT_DIGITS:
        raise ValueError("amount exceeds the supported 38-digit precision")
    if len(fraction) > exponent:
        raise ValueError("amount has more fractional digits than the currency allows")
    if dot and not fraction:
        raise ValueError("amount must include digits after the decimal point")
    scale = 10 ** exponent
    minor_units = int(whole) * scale
    if fraction:
        minor_units += int(fraction.ljust(exponent, "0"))
    return -minor_units if amount.startswith("-") else minor_units


def _parse_date(value: str) -> date:
    if not _DATE_PATTERN.fullmatch(value):
        raise ValueError("date must use YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("date is not a valid calendar date") from exc


def _optional(value: str) -> str | None:
    normalized = value.strip()
    return normalized or None


def parse_statement_csv(
    content: bytes,
    *,
    currency_exponent: int,
    expected_currency: str | None = None,
) -> CsvParseResult:
    """Validate an entire UTF-8 CSV statement without side effects.

    The exponent and optional expected account currency must come from the
    caller's trusted, immutable account/currency configuration.
    """
    if not isinstance(content, bytes):
        raise TypeError("CSV content must be bytes")
    if not content:
        raise StatementCsvError("empty_file", "CSV file is empty")
    if len(content) > MAX_FILE_BYTES:
        raise StatementCsvError("file_too_large", "CSV exceeds the 5 MiB limit")
    if isinstance(currency_exponent, bool) or not isinstance(currency_exponent, int) or currency_exponent < 0:
        raise ValueError("currency exponent must be a non-negative integer")

    digest = hashlib.sha256(content).hexdigest()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise StatementCsvError("invalid_encoding", "CSV must be UTF-8 encoded") from exc

    reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
    try:
        raw_headers = next(reader)
    except StopIteration as exc:
        raise StatementCsvError("missing_header", "CSV header row is missing") from exc
    except csv.Error as exc:
        raise StatementCsvError("malformed_csv", "CSV header is malformed") from exc

    if len(raw_headers) > MAX_COLUMNS:
        raise StatementCsvError("too_many_columns", "CSV has too many columns")
    headers = tuple(header.strip().lower() for header in raw_headers)
    if any(not header for header in headers):
        raise StatementCsvError("blank_header", "CSV contains a blank column name")
    if len(headers) != len(set(headers)):
        raise StatementCsvError("duplicate_header", "CSV contains duplicate column names")
    missing = REQUIRED_COLUMNS - set(headers)
    if missing:
        raise StatementCsvError(
            "missing_columns", "CSV is missing required columns: " + ", ".join(sorted(missing))
        )
    unknown = set(headers) - ALLOWED_COLUMNS
    if unknown:
        raise StatementCsvError(
            "unknown_columns", "CSV contains unsupported columns: " + ", ".join(sorted(unknown))
        )

    rows: list[StatementRow] = []
    errors: list[RowError] = []
    total = 0
    normalized_expected = expected_currency.upper() if expected_currency else None
    if normalized_expected is not None and not re.fullmatch(r"[A-Z]{3}", normalized_expected):
        raise ValueError("expected_currency must be a three-letter code")

    try:
        for values in reader:
            line_number = reader.line_num
            if not values or (len(values) == 1 and not values[0].strip()):
                continue
            total += 1
            if total > MAX_ROWS:
                raise StatementCsvError("too_many_rows", "CSV exceeds the 50,000-row limit")
            if len(values) != len(headers):
                errors.append(RowError(line_number, "__row__", "column_count", "row has a different number of columns than the header"))
                continue
            if any(len(value) > MAX_FIELD_CHARS for value in values):
                errors.append(RowError(line_number, "__row__", "field_too_large", "one or more fields exceed the 4,096-character limit"))
                continue

            record = dict(zip(headers, values))
            row_errors: list[RowError] = []
            try:
                booking_date = _parse_date(record["booking_date"].strip())
            except ValueError as exc:
                row_errors.append(RowError(line_number, "booking_date", "invalid_date", str(exc)))
                booking_date = None
            try:
                amount = parse_minor_units(record["amount"], currency_exponent)
            except (TypeError, ValueError) as exc:
                row_errors.append(RowError(line_number, "amount", "invalid_amount", str(exc)))
                amount = None

            currency = record["currency"].strip().upper()
            if not re.fullmatch(r"[A-Z]{3}", currency):
                row_errors.append(RowError(line_number, "currency", "invalid_currency", "currency must be a three-letter code"))
            elif normalized_expected and currency != normalized_expected:
                row_errors.append(RowError(line_number, "currency", "currency_mismatch", "statement currency does not match the account currency"))

            description = record["description"]
            if not description.strip():
                row_errors.append(RowError(line_number, "description", "required", "description cannot be blank"))

            value_date = None
            if "value_date" in record and record["value_date"].strip():
                try:
                    value_date = _parse_date(record["value_date"].strip())
                except ValueError as exc:
                    row_errors.append(RowError(line_number, "value_date", "invalid_date", str(exc)))

            if row_errors:
                errors.extend(row_errors)
                continue

            rows.append(StatementRow(
                row_number=line_number,
                booking_date=booking_date,
                amount_minor_units=amount,
                currency=currency,
                description=description,
                source_transaction_id=_optional(record.get("source_transaction_id", "")),
                value_date=value_date,
                counterparty=_optional(record.get("counterparty", "")),
                reference=_optional(record.get("reference", "")),
                source_payload=tuple((header, record[header]) for header in headers),
            ))
    except csv.Error as exc:
        raise StatementCsvError("malformed_csv", "CSV structure is malformed") from exc

    if total == 0:
        raise StatementCsvError("no_data_rows", "CSV must contain at least one statement row")

    return CsvParseResult(
        file_sha256=digest,
        rows=tuple(rows),
        errors=tuple(errors),
        headers=headers,
        total_data_rows=total,
        currency_exponent=currency_exponent,
    )
