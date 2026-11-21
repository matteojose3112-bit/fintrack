"""Authenticated FinTrack statement-import API."""

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import engine, get_db
from app.models import User
from app.domain.reconciliation_csv import (
    MAX_FILE_BYTES,
    StatementCsvError,
    StatementRow,
    parse_statement_csv,
)
from app.domain.reconciliation_matching import (
    LedgerMatchCandidate,
    MatchDecision,
    MatchProposal,
    MatchStatus,
    MatchStrategy,
    build_match_proposals,
)
from app.persistence.models import (
    CurrencyDefinitionModel,
    FinancialAccountModel,
    JournalEntryModel,
    JournalPostingModel,
    ReconciliationImportBatchModel,
    ReconciliationMatchModel,
    ReconciliationStatementRowModel,
)
from app.persistence.reconciliation_import_service import (
    InvalidStatementEvidence,
    ReconciliationAccountUnavailable,
    ReconciliationCurrencyMismatch,
    persist_statement_import,
)
from app.persistence.reconciliation_match_service import (
    ReconciliationCandidateUnavailable,
    ReconciliationMatchConflict,
    ReconciliationMatchNotFound,
    confirm_reconciliation_match,
    persist_match_decisions,
    reject_reconciliation_match,
    unmatch_reconciliation_match,
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
    matches = db.scalars(
        select(ReconciliationMatchModel).where(
            ReconciliationMatchModel.owner_id == user.id,
            ReconciliationMatchModel.batch_id == batch.id,
            ReconciliationMatchModel.statement_row_id.in_([row.id for row in rows]),
        )
    ).all() if rows else []
    match_by_row = {match.statement_row_id: match for match in matches}
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



@router.get("/imports/{batch_id}/proposals")
def preview_statement_match_proposals(
    batch_id: UUID,
    date_window_days: int = 3,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compute deterministic, read-only match proposals for one import batch."""
    if engine.dialect.name != "postgresql":
        raise HTTPException(status_code=503, detail="Reconciliation proposals require PostgreSQL.")
    if date_window_days < 0 or date_window_days > 31:
        raise HTTPException(status_code=422, detail="date_window_days must be between 0 and 31.")

    batch = db.scalar(
        select(ReconciliationImportBatchModel).where(
            ReconciliationImportBatchModel.id == batch_id,
            ReconciliationImportBatchModel.owner_id == user.id,
        )
    )
    if batch is None:
        raise HTTPException(status_code=404, detail="Statement import not found")

    account_row = db.execute(
        select(FinancialAccountModel, CurrencyDefinitionModel)
        .join(
            CurrencyDefinitionModel,
            CurrencyDefinitionModel.id == FinancialAccountModel.currency_definition_id,
        )
        .where(
            FinancialAccountModel.id == batch.account_id,
            FinancialAccountModel.owner_id == user.id,
        )
    ).one_or_none()
    if account_row is None:
        raise HTTPException(status_code=404, detail="Financial account not found")
    account, currency = account_row
    if account.account_type != "ASSET":
        raise HTTPException(status_code=422, detail="Only asset accounts can be reconciled.")

    statement_models = db.scalars(
        select(ReconciliationStatementRowModel)
        .where(
            ReconciliationStatementRowModel.batch_id == batch.id,
            ReconciliationStatementRowModel.owner_id == user.id,
        )
        .order_by(ReconciliationStatementRowModel.row_number)
    ).all()
    if not statement_models:
        return {"batch_id": str(batch.id), "proposals": []}

    statement_rows = tuple(
        StatementRow(
            row_number=item.row_number,
            booking_date=item.booking_date,
            amount_minor_units=int(item.amount_minor),
            currency=item.currency_code,
            description=item.description,
            source_transaction_id=item.source_transaction_id,
            value_date=item.value_date,
            counterparty=item.counterparty,
            reference=item.reference,
        )
        for item in statement_models
    )
    lower_date = min(item.booking_date for item in statement_rows) - timedelta(days=date_window_days)
    upper_date = max(item.booking_date for item in statement_rows) + timedelta(days=date_window_days)
    postings = db.execute(
        select(JournalPostingModel, JournalEntryModel)
        .join(
            JournalEntryModel,
            JournalEntryModel.id == JournalPostingModel.journal_entry_id,
        )
        .where(
            JournalPostingModel.owner_id == user.id,
            JournalPostingModel.account_id == batch.account_id,
            JournalPostingModel.currency_definition_id == batch.currency_definition_id,
            JournalEntryModel.owner_id == user.id,
            JournalEntryModel.effective_date >= lower_date,
            JournalEntryModel.effective_date <= upper_date,
        )
        .order_by(JournalEntryModel.effective_date, JournalPostingModel.id)
    ).all()
    candidates = tuple(
        LedgerMatchCandidate(
            candidate_id=posting.id,
            journal_id=journal.id,
            owner_id=user.id,
            account_id=batch.account_id,
            effective_date=journal.effective_date,
            amount_minor=(
                int(posting.amount_minor)
                if posting.side == "DEBIT"
                else -int(posting.amount_minor)
            ),
            currency_code=currency.code,
            description=journal.description,
        )
        for posting, journal in postings
    )
    decisions = build_match_proposals(
        statement_rows,
        candidates,
        owner_id=user.id,
        account_id=batch.account_id,
        currency_code=currency.code,
        date_window_days=date_window_days,
    )
    return {
        "batch_id": str(batch.id),
        "date_window_days": date_window_days,
        "proposals": [
            {
                "row_number": decision.row_number,
                "status": decision.status.value,
                "proposal": (
                    {
                        "candidate_posting_id": str(decision.proposal.candidate_id),
                        "journal_id": str(decision.proposal.journal_id),
                        "strategy": decision.proposal.strategy.value,
                        "date_difference_days": decision.proposal.date_difference_days,
                    }
                    if decision.proposal else None
                ),
                "candidate_posting_ids": [str(item) for item in decision.candidate_ids],
            }
            for decision in decisions
        ],
    }


class MatchActionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


@router.post("/imports/{batch_id}/proposals")
def create_statement_match_proposals(
    batch_id: UUID,
    date_window_days: int = 3,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compute and persist deterministic suggestions; no match is auto-confirmed."""
    preview = preview_statement_match_proposals(
        batch_id=batch_id,
        date_window_days=date_window_days,
        db=db,
        user=user,
    )
    decisions = []
    for item in preview["proposals"]:
        status_value = MatchStatus(item["status"])
        proposal_data = item["proposal"]
        proposal = None
        if proposal_data is not None:
            proposal = MatchProposal(
                row_number=item["row_number"],
                candidate_id=UUID(proposal_data["candidate_posting_id"]),
                journal_id=UUID(proposal_data["journal_id"]),
                strategy=MatchStrategy(proposal_data["strategy"]),
                date_difference_days=proposal_data["date_difference_days"],
            )
        decisions.append(MatchDecision(
            row_number=item["row_number"],
            status=status_value,
            proposal=proposal,
            candidate_ids=tuple(UUID(value) for value in item["candidate_posting_ids"]),
        ))
    try:
        result = persist_match_decisions(
            db,
            owner_id=user.id,
            actor_id=user.id,
            batch_id=batch_id,
            decisions=tuple(decisions),
        )
        db.commit()
    except ReconciliationMatchNotFound as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except (ReconciliationCandidateUnavailable, ReconciliationMatchConflict, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Proposal persistence conflicted with existing reconciliation state.")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Reconciliation storage is temporarily unavailable.")
    return {
        "batch_id": str(batch_id),
        "created": result.created,
        "updated": result.updated,
        "unchanged": result.unchanged,
        "protected": result.protected,
        "confirmed_automatically": 0,
    }


@router.post("/matches/{match_id}/confirm")
def confirm_statement_match(
    match_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Explicitly confirm one proposal after user review."""
    if engine.dialect.name != "postgresql":
        raise HTTPException(status_code=503, detail="Reconciliation writes require PostgreSQL.")
    try:
        match = confirm_reconciliation_match(
            db, owner_id=user.id, actor_id=user.id, match_id=match_id,
        )
        db.commit()
    except ReconciliationMatchNotFound as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except (ReconciliationMatchConflict, ReconciliationCandidateUnavailable) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This ledger posting is already confirmed against another statement row.")
    except DBAPIError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Reconciliation storage is temporarily unavailable.")
    return {"match_id": str(match.id), "status": match.status}


@router.post("/matches/{match_id}/reject")
def reject_statement_match(
    match_id: UUID,
    payload: MatchActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if engine.dialect.name != "postgresql":
        raise HTTPException(status_code=503, detail="Reconciliation writes require PostgreSQL.")
    try:
        match = reject_reconciliation_match(
            db, owner_id=user.id, actor_id=user.id,
            match_id=match_id, reason=payload.reason,
        )
        db.commit()
    except ReconciliationMatchNotFound as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except (ReconciliationMatchConflict, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except DBAPIError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Reconciliation storage is temporarily unavailable.")
    return {"match_id": str(match.id), "status": match.status}


@router.post("/matches/{match_id}/unmatch")
def unmatch_statement_match(
    match_id: UUID,
    payload: MatchActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if engine.dialect.name != "postgresql":
        raise HTTPException(status_code=503, detail="Reconciliation writes require PostgreSQL.")
    try:
        match = unmatch_reconciliation_match(
            db, owner_id=user.id, actor_id=user.id,
            match_id=match_id, reason=payload.reason,
        )
        db.commit()
    except ReconciliationMatchNotFound as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except (ReconciliationMatchConflict, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except DBAPIError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Reconciliation storage is temporarily unavailable.")
    return {"match_id": str(match.id), "status": match.status}
