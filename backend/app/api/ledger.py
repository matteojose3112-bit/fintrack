"""Versioned API for Aurelius accounts and double-entry ledger."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import SessionLocal, engine, get_db
from app.models import User
from app.api.ledger_schemas import (
    AccountCreateRequest,
    JournalCreateRequest,
    JournalReversalRequest,
)
from app.persistence.models import (
    AuditEventModel,
    CurrencyDefinitionModel,
    FinancialAccountModel,
    FinancialOwnerPreferenceModel,
    JournalEntryModel,
    JournalPostingModel,
)
from app.persistence.posting_service import (
    AccountClosed,
    AccountNotFound,
    AccountingPeriodUnavailable,
    CurrencyMismatch,
    IdempotencyConflict,
    IdempotencyInProgress,
    InvalidJournal,
    JournalAlreadyReversed,
    JournalNotFound,
    PostJournalCommand,
    PostingLine,
    ReverseJournalCommand,
    post_journal,
    reverse_journal,
)

router = APIRouter(prefix="/v1", tags=["Aurelius Ledger"])


def _require_postgresql() -> None:
    if engine.dialect.name != "postgresql":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Aurelius ledger writes require PostgreSQL. SQLite is supported for legacy MVP tests only.",
        )


def _cash_currency_definition(db: Session, code: str) -> CurrencyDefinitionModel:
    definition = db.scalars(
        select(CurrencyDefinitionModel)
        .where(
            CurrencyDefinitionModel.code == code.upper(),
            CurrencyDefinitionModel.registry_list == "one",
            CurrencyDefinitionModel.withdrawal_key == "",
            CurrencyDefinitionModel.fund.is_(False),
            CurrencyDefinitionModel.minor_unit_exponent.is_not(None),
        )
        .order_by(CurrencyDefinitionModel.published_on.desc())
        .limit(1)
    ).first()
    if definition is None:
        registry_count = db.scalar(
            select(func.count()).select_from(CurrencyDefinitionModel)
        )
        if not registry_count:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The ISO currency registry has not been seeded. Run the explicit registry seed command after database migration.",
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{code.upper()} is not an enabled current cash currency.",
        )
    return definition


def _serialize_account(
    account: FinancialAccountModel, currency: CurrencyDefinitionModel
) -> dict:
    return {
        "id": str(account.id),
        "name": account.name,
        "account_type": account.account_type,
        "status": account.status,
        "currency": currency.code,
        "currency_registry_release": currency.registry_release,
        "minor_unit_exponent": currency.minor_unit_exponent,
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "closed_at": account.closed_at.isoformat() if account.closed_at else None,
    }


def _serialize_journal(
    journal: JournalEntryModel, currency: CurrencyDefinitionModel
) -> dict:
    return {
        "id": str(journal.id),
        "effective_date": journal.effective_date.isoformat(),
        "recorded_at": journal.recorded_at.isoformat(),
        "description": journal.description,
        "status": journal.status,
        "currency": currency.code,
        "currency_registry_release": currency.registry_release,
        "reversal_of": str(journal.reversal_of) if journal.reversal_of else None,
        "correction_of": str(journal.correction_of) if journal.correction_of else None,
    }


def _raise_posting_http_error(error: Exception) -> None:
    if isinstance(error, (IdempotencyConflict, IdempotencyInProgress)):
        raise HTTPException(status_code=409, detail=str(error))
    if isinstance(error, (AccountNotFound, JournalNotFound)):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(
        error,
        (AccountClosed, AccountingPeriodUnavailable, JournalAlreadyReversed),
    ):
        raise HTTPException(status_code=409, detail=str(error))
    if isinstance(error, (CurrencyMismatch, InvalidJournal, TypeError, ValueError)):
        raise HTTPException(status_code=422, detail=str(error))
    if isinstance(error, IntegrityError):
        raise HTTPException(
            status_code=422,
            detail="The ledger database rejected an accounting invariant.",
        )
    if isinstance(error, DBAPIError):
        raise HTTPException(
            status_code=503,
            detail="The ledger database is temporarily unavailable. Retry with the same Idempotency-Key.",
        )
    raise error


@router.get("/currencies")
def list_supported_cash_currencies():
    """List current ISO monetary codes eligible for ordinary cash accounts."""
    from app.domain.currency import DEFAULT_CURRENCY_REGISTRY

    definitions = [
        item
        for item in DEFAULT_CURRENCY_REGISTRY.current_definitions
        if item.supports_exact_money and not item.fund
    ]
    return [
        {
            "code": item.code,
            "numeric_code": item.numeric_code,
            "name": item.name,
            "minor_unit_exponent": item.minor_unit_exponent,
            "countries": list(item.countries),
            "registry_release": item.registry_release,
        }
        for item in definitions
    ]


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_financial_account(
    payload: AccountCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_postgresql()
    currency = _cash_currency_definition(db, payload.currency)
    account = FinancialAccountModel(
        id=uuid4(),
        owner_id=user.id,
        name=payload.name,
        account_type=payload.account_type,
        currency_definition_id=currency.id,
        status="OPEN",
    )
    try:
        db.add(account)
        db.flush()
        db.add(
            AuditEventModel(
                id=uuid4(),
                owner_id=user.id,
                actor_id=user.id,
                event_type="ledger.account.created",
                aggregate_type="financial_account",
                aggregate_id=account.id,
                payload={
                    "account_type": account.account_type,
                    "currency": currency.code,
                    "currency_registry_release": currency.registry_release,
                },
            )
        )
        db.commit()
        db.refresh(account)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="The financial account could not be created."
        )
    except DBAPIError:
        db.rollback()
        raise HTTPException(
            status_code=503, detail="The ledger database is temporarily unavailable."
        )
    return _serialize_account(account, currency)


@router.get("/accounts")
def list_financial_accounts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_postgresql()
    rows = db.execute(
        select(FinancialAccountModel, CurrencyDefinitionModel)
        .join(
            CurrencyDefinitionModel,
            FinancialAccountModel.currency_definition_id == CurrencyDefinitionModel.id,
        )
        .where(FinancialAccountModel.owner_id == user.id)
        .order_by(FinancialAccountModel.name, FinancialAccountModel.id)
    ).all()
    return [_serialize_account(account, currency) for account, currency in rows]


@router.get("/accounts/{account_id}/balance")
def get_financial_account_balance(
    account_id: UUID,
    as_of: date | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_postgresql()
    account = db.execute(
        select(FinancialAccountModel, CurrencyDefinitionModel)
        .join(
            CurrencyDefinitionModel,
            FinancialAccountModel.currency_definition_id == CurrencyDefinitionModel.id,
        )
        .where(
            FinancialAccountModel.id == account_id,
            FinancialAccountModel.owner_id == user.id,
        )
    ).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Financial account not found")
    account_model, currency = account
    preferences = db.get(FinancialOwnerPreferenceModel, user.id)
    timezone_name = preferences.accounting_timezone if preferences else "UTC"
    try:
        owner_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        owner_timezone = timezone.utc
    cutoff = as_of or datetime.now(owner_timezone).date()
    debit_signed = case(
        (JournalPostingModel.side == "DEBIT", JournalPostingModel.amount_minor),
        else_=-JournalPostingModel.amount_minor,
    )
    net_debit = db.scalar(
        select(func.coalesce(func.sum(debit_signed), 0))
        .select_from(JournalPostingModel)
        .join(
            JournalEntryModel,
            JournalPostingModel.journal_entry_id == JournalEntryModel.id,
        )
        .where(
            JournalPostingModel.account_id == account_id,
            JournalPostingModel.owner_id == user.id,
            JournalEntryModel.owner_id == user.id,
            JournalEntryModel.effective_date <= cutoff,
        )
    )
    normal_debit = account_model.account_type in {"ASSET", "EXPENSE"}
    balance = Decimal(net_debit or 0)
    if not normal_debit:
        balance = -balance
    return {
        "account_id": str(account_id),
        "currency": currency.code,
        "currency_registry_release": currency.registry_release,
        "balance_minor": str(int(balance)),
        "as_of": cutoff.isoformat(),
    }


@router.post("/ledger/journals", status_code=status.HTTP_201_CREATED)
def create_ledger_journal(
    payload: JournalCreateRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_postgresql()
    currency = _cash_currency_definition(db, payload.currency)
    command = PostJournalCommand(
        owner_id=user.id,
        actor_id=user.id,
        effective_date=payload.effective_date,
        description=payload.description,
        currency_definition_id=currency.id,
        postings=tuple(
            PostingLine(
                account_id=UUID(line.account_id),
                side=line.side,
                amount_minor=int(line.amount_minor),
            )
            for line in payload.postings
        ),
    )
    try:
        result = post_journal(SessionLocal, command, idempotency_key)
    except Exception as error:
        _raise_posting_http_error(error)
    return result.body


@router.post(
    "/ledger/journals/{journal_id}/reversal",
    status_code=status.HTTP_201_CREATED,
)
def reverse_ledger_journal(
    journal_id: UUID,
    payload: JournalReversalRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    user: User = Depends(get_current_user),
):
    _require_postgresql()
    command = ReverseJournalCommand(
        owner_id=user.id,
        actor_id=user.id,
        source_journal_id=journal_id,
        effective_date=payload.effective_date,
        description=payload.description,
    )
    try:
        result = reverse_journal(SessionLocal, command, idempotency_key)
    except Exception as error:
        _raise_posting_http_error(error)
    return result.body


@router.get("/ledger/journals")
def list_ledger_journals(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_postgresql()
    rows = db.execute(
        select(JournalEntryModel, CurrencyDefinitionModel)
        .join(
            CurrencyDefinitionModel,
            JournalEntryModel.currency_definition_id == CurrencyDefinitionModel.id,
        )
        .where(JournalEntryModel.owner_id == user.id)
        .order_by(
            JournalEntryModel.effective_date.desc(),
            JournalEntryModel.recorded_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()
    return [_serialize_journal(journal, currency) for journal, currency in rows]


@router.get("/ledger/journals/{journal_id}")
def get_ledger_journal(
    journal_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_postgresql()
    row = db.execute(
        select(JournalEntryModel, CurrencyDefinitionModel)
        .join(
            CurrencyDefinitionModel,
            JournalEntryModel.currency_definition_id == CurrencyDefinitionModel.id,
        )
        .where(
            JournalEntryModel.id == journal_id,
            JournalEntryModel.owner_id == user.id,
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Journal not found")
    journal, currency = row
    postings = db.scalars(
        select(JournalPostingModel)
        .where(
            JournalPostingModel.journal_entry_id == journal.id,
            JournalPostingModel.owner_id == user.id,
        )
        .order_by(JournalPostingModel.account_id)
    ).all()
    response = _serialize_journal(journal, currency)
    response["postings"] = [
        {
            "account_id": str(line.account_id),
            "side": line.side,
            "amount_minor": str(int(line.amount_minor)),
        }
        for line in postings
    ]
    return response
