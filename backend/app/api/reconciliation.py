"""Authenticated FinTrack statement-import API."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from uuid import UUID

from app.auth import get_current_user
from app.database import engine, get_db
from app.models import User
from app.domain.reconciliation_csv import (
    MAX_FILE_BYTES,
    StatementCsvError,
    parse_statement_csv,
)
from app.persistence.models import (
    CurrencyDefinitionModel,
    FinancialAccountModel,
    ReconciliationImportBatchModel,
    ReconciliationStatementRowModel,
)
from app.persistence.reconciliation_import_service import (
    InvalidStatementEvidence,
    ReconciliationAccountUnavailable,
    ReconciliationCurrencyMismatch,
    persist_statement_import,
)


router = APIRouter(prefix="/v1/reconciliation", tags=["FinTrack Reconciliation"])


@router.post("/imports")
async def import_statement(
    account_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Validate and persist an immutable bank-statement import batch."""
    if engine.dialect.name != "postgresql":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reconciliation imports require PostgreSQL.",
        )

    account_row = db.execute(
        select(FinancialAccountModel, CurrencyDefinitionModel)
        .join(
            CurrencyDefinitionModel,
            CurrencyDefinitionModel.id == FinancialAccountModel.currency_definition_id,
        )
        .where(
            FinancialAccountModel.id == account_id,
            FinancialAccountModel.owner_id == user.id,
        )
    ).one_or_none()
    if account_row is None:
        raise HTTPException(status_code=404, detail="Financial account not found")
    account, currency = account_row
    if account.status != "OPEN" or account.account_type != "ASSET":
        raise HTTPException(
            status_code=409,
            detail="Statement imports require an open asset account.",
        )
    if currency.registry_list != "one" or currency.minor_unit_exponent is None:
        raise HTTPException(status_code=422, detail="Account currency is not eligible for cash reconciliation.")

    content = await file.read(MAX_FILE_BYTES + 1)
    try:
        parsed = parse_statement_csv(
            content,
            currency_exponent=currency.minor_unit_exponent,
            expected_currency=currency.code,
        )
    except StatementCsvError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)})

    if parsed.errors:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "statement_rows_invalid",
                "total_data_rows": parsed.total_data_rows,
                "accepted_rows": parsed.accepted_row_count,
                "errors": [
                    {
                        "row_number": error.row_number,
                        "field": error.field,
                        "code": error.code,
                        "message": error.message,
                    }
                    for error in parsed.errors
                ],
            },
        )

    try:
        result = persist_statement_import(
            db,
            owner_id=user.id,
            account_id=account_id,
            parsed=parsed,
            original_filename=file.filename,
        )
        db.commit()
    except (ReconciliationAccountUnavailable, ReconciliationCurrencyMismatch, InvalidStatementEvidence) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Statement import conflicted with existing account evidence.")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Reconciliation storage is temporarily unavailable.")

    return JSONResponse(
        status_code=201 if result.inserted else 200,
        content={
            "batch_id": str(result.batch_id),
            "created": result.inserted,
            "file_sha256": result.file_sha256,
            "parser_version": result.parser_version,
            "row_count": result.row_count,
            "status": "VALIDATED",
        },
    )



@router.get("/imports")
def list_statement_imports(
    account_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List only the authenticated owner's statement import batches."""
    if engine.dialect.name != "postgresql":
        raise HTTPException(status_code=503, detail="Reconciliation reads require PostgreSQL.")
    if limit < 1 or limit > 100 or offset < 0:
        raise HTTPException(status_code=422, detail="limit must be 1..100 and offset non-negative.")
    query = select(ReconciliationImportBatchModel).where(
        ReconciliationImportBatchModel.owner_id == user.id
    )
    if account_id is not None:
        query = query.where(ReconciliationImportBatchModel.account_id == account_id)
    batches = db.scalars(
        query.order_by(
            ReconciliationImportBatchModel.imported_at.desc(),
            ReconciliationImportBatchModel.id,
        ).limit(limit).offset(offset)
    ).all()
    return [
        {
            "batch_id": str(batch.id),
            "account_id": str(batch.account_id),
            "file_sha256": batch.file_sha256,
            "parser_version": batch.parser_version,
            "status": batch.status,
            "row_count": batch.row_count,
            "imported_at": batch.imported_at.isoformat(),
            "original_filename": batch.original_filename,
        }
        for batch in batches
    ]


@router.get("/imports/{batch_id}")
def get_statement_import(
    batch_id: UUID,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Read a paginated slice of the owner's immutable statement evidence."""
    if engine.dialect.name != "postgresql":
        raise HTTPException(status_code=503, detail="Reconciliation reads require PostgreSQL.")
    if limit < 1 or limit > 200 or offset < 0:
        raise HTTPException(status_code=422, detail="limit must be 1..200 and offset non-negative.")
    batch = db.scalar(
        select(ReconciliationImportBatchModel).where(
            ReconciliationImportBatchModel.id == batch_id,
            ReconciliationImportBatchModel.owner_id == user.id,
        )
    )
    if batch is None:
        raise HTTPException(status_code=404, detail="Statement import not found")
    rows = db.scalars(
        select(ReconciliationStatementRowModel)
        .where(
            ReconciliationStatementRowModel.batch_id == batch.id,
            ReconciliationStatementRowModel.owner_id == user.id,
        )
        .order_by(ReconciliationStatementRowModel.row_number)
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "batch_id": str(batch.id),
        "account_id": str(batch.account_id),
        "file_sha256": batch.file_sha256,
        "parser_version": batch.parser_version,
        "status": batch.status,
        "row_count": batch.row_count,
        "imported_at": batch.imported_at.isoformat(),
        "rows": [
            {
                "row_number": row.row_number,
                "booking_date": row.booking_date.isoformat(),
                "value_date": row.value_date.isoformat() if row.value_date else None,
                "amount_minor": str(row.amount_minor),
                "currency": row.currency_code,
                "description": row.description,
                "source_transaction_id": row.source_transaction_id,
                "counterparty": row.counterparty,
                "reference": row.reference,
                "source_payload": row.source_payload,
            }
            for row in rows
        ],
    }
