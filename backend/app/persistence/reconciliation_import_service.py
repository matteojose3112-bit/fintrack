"""Transactional persistence for validated statement-file evidence.

The caller owns the transaction. Imports are read-only with respect to the
posted ledger and are idempotent by owner, account, file digest, and parser
version. This service never confirms matches or creates journal entries.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.domain.reconciliation_csv import CsvParseResult
from app.persistence.models import (
    CurrencyDefinitionModel,
    FinancialAccountModel,
    AuditEventModel,
    ReconciliationImportBatchModel,
    ReconciliationStatementRowModel,
)


PARSER_VERSION = "csv-v1"
_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class ReconciliationImportError(Exception):
    """Base class for safe, deterministic statement-import failures."""


class ReconciliationAccountUnavailable(ReconciliationImportError):
    """The account is missing, closed, or not an eligible owned cash asset."""


class ReconciliationCurrencyMismatch(ReconciliationImportError):
    """The parsed statement currency does not match the account's currency."""


class InvalidStatementEvidence(ReconciliationImportError):
    """The supplied parse result is incomplete or not a valid full-file parse."""


@dataclass(frozen=True, slots=True)
class ImportBatchResult:
    batch_id: UUID
    inserted: bool
    row_count: int
    file_sha256: str
    parser_version: str


def persist_statement_import(
    session: Session,
    *,
    owner_id: int,
    account_id: UUID,
    parsed: CsvParseResult,
    parser_version: str = PARSER_VERSION,
    original_filename: str | None = None,
) -> ImportBatchResult:
    """Persist a fully valid parse result in the caller's active transaction."""
    if not session.in_transaction():
        raise RuntimeError("persist_statement_import requires an active transaction")
    if isinstance(owner_id, bool) or not isinstance(owner_id, int) or owner_id <= 0:
        raise ValueError("owner_id must be a positive authenticated user ID")
    if not isinstance(account_id, UUID):
        raise TypeError("account_id must be UUID")
    if not isinstance(parsed, CsvParseResult):
        raise TypeError("parsed must be a CsvParseResult")
    if not parsed.is_valid or parsed.errors or parsed.total_data_rows != len(parsed.rows):
        raise InvalidStatementEvidence("only fully valid statement files can be persisted")
    if not _SHA256_PATTERN.fullmatch(parsed.file_sha256):
        raise InvalidStatementEvidence("statement file digest must be lowercase SHA-256 hex")
    if not isinstance(parser_version, str) or not parser_version.strip() or len(parser_version) > 32:
        raise ValueError("parser_version must be a non-empty string up to 32 characters")
    if original_filename is not None:
        if not isinstance(original_filename, str) or len(original_filename) > 255:
            raise ValueError("original_filename must be at most 255 characters")
        # Keep a basename only; never persist client-supplied directory paths.
        original_filename = original_filename.replace("\\", "/").rsplit("/", 1)[-1]

    account = session.execute(
        select(FinancialAccountModel, CurrencyDefinitionModel)
        .join(
            CurrencyDefinitionModel,
            CurrencyDefinitionModel.id == FinancialAccountModel.currency_definition_id,
        )
        .where(
            FinancialAccountModel.id == account_id,
            FinancialAccountModel.owner_id == owner_id,
        )
        .with_for_update()
    ).one_or_none()
    if account is None:
        raise ReconciliationAccountUnavailable("cash account was not found for this owner")
    account_model, currency = account
    if account_model.status != "OPEN" or account_model.account_type != "ASSET":
        raise ReconciliationAccountUnavailable("statement imports require an open ASSET account")
    if currency.registry_list != "one" or currency.minor_unit_exponent is None:
        raise ReconciliationAccountUnavailable("account currency is not a current monetary unit")

    if parsed.currency_exponent != currency.minor_unit_exponent:\n        raise ReconciliationCurrencyMismatch("parser precision does not match the account currency definition")\n    if any(row.currency != currency.code for row in parsed.rows):
        raise ReconciliationCurrencyMismatch("every statement row must match the account currency")

    batch_id = uuid4()
    values = {
        "id": batch_id,
        "owner_id": owner_id,
        "account_id": account_id,
        "currency_definition_id": currency.id,
        "file_sha256": parsed.file_sha256,
        "parser_version": parser_version,
        "original_filename": original_filename,
        "status": "VALIDATED",
        "row_count": len(parsed.rows),
        "error_count": 0,
    }
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        insert_stmt = pg_insert(ReconciliationImportBatchModel).values(**values)
    elif dialect == "sqlite":
        insert_stmt = sqlite_insert(ReconciliationImportBatchModel).values(**values)
    else:
        raise RuntimeError(f"unsupported reconciliation database dialect: {dialect}")

    inserted_id = session.execute(
        insert_stmt.on_conflict_do_nothing(
            index_elements=[
                ReconciliationImportBatchModel.owner_id,
                ReconciliationImportBatchModel.account_id,
                ReconciliationImportBatchModel.file_sha256,
                ReconciliationImportBatchModel.parser_version,
            ]
        ).returning(ReconciliationImportBatchModel.id)
    ).scalar_one_or_none()

    if inserted_id is None:
        existing = session.execute(
            select(ReconciliationImportBatchModel)
            .where(
                ReconciliationImportBatchModel.owner_id == owner_id,
                ReconciliationImportBatchModel.account_id == account_id,
                ReconciliationImportBatchModel.file_sha256 == parsed.file_sha256,
                ReconciliationImportBatchModel.parser_version == parser_version,
            )
            .with_for_update()
        ).scalar_one()
        return ImportBatchResult(
            batch_id=existing.id,
            inserted=False,
            row_count=existing.row_count,
            file_sha256=existing.file_sha256,
            parser_version=existing.parser_version,
        )

    session.add(AuditEventModel(\n        id=uuid4(),\n        owner_id=owner_id,\n        actor_id=owner_id,\n        event_type="RECONCILIATION_IMPORT_CREATED",\n        aggregate_type="RECONCILIATION_IMPORT_BATCH",\n        aggregate_id=batch_id,\n        reason=None,\n        payload={\n            "account_id": str(account_id),\n            "file_sha256": parsed.file_sha256,\n            "parser_version": parser_version,\n            "row_count": len(parsed.rows),\n        },\n    ))\n    session.add_all([\n        ReconciliationStatementRowModel(
            id=uuid4(),
            batch_id=batch_id,
            owner_id=owner_id,
            row_number=row.row_number,
            booking_date=row.booking_date,
            value_date=row.value_date,
            amount_minor=row.amount_minor_units,
            currency_code=row.currency,
            description=row.description,
            source_transaction_id=row.source_transaction_id,
            counterparty=row.counterparty,
            reference=row.reference,
            source_payload=dict(row.source_payload),
        )
        for row in parsed.rows
    ])
    session.flush()

    return ImportBatchResult(
        batch_id=batch_id,
        inserted=True,
        row_count=len(parsed.rows),
        file_sha256=parsed.file_sha256,
        parser_version=parser_version,
    )
