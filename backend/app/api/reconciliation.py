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
from app.persistence.models import CurrencyDefinitionModel, FinancialAccountModel
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
