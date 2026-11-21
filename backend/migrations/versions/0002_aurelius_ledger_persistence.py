"""Add isolated Aurelius global ledger persistence schema.

The migration is portable for schema creation. PostgreSQL-only deferred
integrity and append-only triggers are installed only on PostgreSQL; SQLite
remains a fast schema/unit-test backend and is not a concurrency substitute.
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_aurelius_ledger"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _uuid_type():
    return sa.Uuid(as_uuid=True)


def upgrade():
    op.create_table(
        "currency_definitions",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column("code", sa.String(3), nullable=False),
        sa.Column("numeric_code", sa.String(3), nullable=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("minor_unit_exponent", sa.SmallInteger(), nullable=True),
        sa.Column("registry_list", sa.String(8), nullable=False),
        sa.Column("registry_release", sa.String(80), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=False),
        sa.Column("fund", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("withdrawal_key", sa.String(32), nullable=False, server_default=""),
        sa.Column("withdrawn_label", sa.String(32), nullable=True),
        sa.Column("countries", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.String(512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "code",
            "registry_release",
            "registry_list",
            "withdrawal_key",
            name="uq_currency_definition_release_record",
        ),
        sa.CheckConstraint(
            "minor_unit_exponent IS NULL OR minor_unit_exponent >= 0",
            name="ck_currency_minor_unit_exponent_nonnegative",
        ),
        sa.CheckConstraint(
            "registry_list IN ('one', 'three')",
            name="ck_currency_registry_list",
        ),
    )
    op.create_index("ix_currency_definitions_code", "currency_definitions", ["code"])

    op.create_table(
        "financial_accounts",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("account_type", sa.String(16), nullable=False),
        sa.Column(
            "currency_definition_id",
            _uuid_type(),
            sa.ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(12), nullable=False, server_default="OPEN"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "id",
            "owner_id",
            "currency_definition_id",
            name="uq_financial_accounts_owner_currency",
        ),
        sa.CheckConstraint(
            "account_type IN ('ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE')",
            name="ck_financial_accounts_type",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'CLOSED')", name="ck_financial_accounts_status"
        ),
    )
    op.create_index(
        "ix_financial_accounts_owner_status",
        "financial_accounts",
        ["owner_id", "status"],
    )

    op.create_table(
        "journal_entries",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column(
            "currency_definition_id",
            _uuid_type(),
            sa.ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(12), nullable=False, server_default="POSTED"),
        sa.Column("reversal_of", _uuid_type(), nullable=True),
        sa.Column("correction_of", _uuid_type(), nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint("id", "owner_id", name="uq_journal_entries_id_owner"),
        sa.UniqueConstraint(
            "id",
            "owner_id",
            "currency_definition_id",
            name="uq_journal_entries_owner_currency",
        ),
        sa.UniqueConstraint("reversal_of", name="uq_journal_entries_reversal_source"),
        sa.ForeignKeyConstraint(
            ["reversal_of", "owner_id"],
            ["journal_entries.id", "journal_entries.owner_id"],
            ondelete="RESTRICT",
            name="fk_journal_entries_reversal_owner",
        ),
        sa.ForeignKeyConstraint(
            ["correction_of", "owner_id"],
            ["journal_entries.id", "journal_entries.owner_id"],
            ondelete="RESTRICT",
            name="fk_journal_entries_correction_owner",
        ),
        sa.CheckConstraint("status = 'POSTED'", name="ck_journal_entries_posted_only"),
    )
    op.create_index(
        "ix_journal_entries_owner_effective_date",
        "journal_entries",
        ["owner_id", "effective_date"],
    )

    op.create_table(
        "journal_postings",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column("journal_entry_id", _uuid_type(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("account_id", _uuid_type(), nullable=False),
        sa.Column("currency_definition_id", _uuid_type(), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("amount_minor", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id", "owner_id", "currency_definition_id"],
            [
                "journal_entries.id",
                "journal_entries.owner_id",
                "journal_entries.currency_definition_id",
            ],
            ondelete="RESTRICT",
            name="fk_journal_postings_journal_owner_currency",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "owner_id", "currency_definition_id"],
            [
                "financial_accounts.id",
                "financial_accounts.owner_id",
                "financial_accounts.currency_definition_id",
            ],
            ondelete="RESTRICT",
            name="fk_journal_postings_account_owner_currency",
        ),
        sa.CheckConstraint(
            "side IN ('DEBIT', 'CREDIT')", name="ck_journal_postings_side"
        ),
        sa.CheckConstraint(
            "amount_minor > 0", name="ck_journal_postings_positive_minor_units"
        ),
    )
    op.create_index("ix_journal_postings_journal", "journal_postings", ["journal_entry_id"])
    op.create_index(
        "ix_journal_postings_account_journal",
        "journal_postings",
        ["account_id", "journal_entry_id"],
    )

    op.create_table(
        "idempotency_records",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("operation", sa.String(80), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("journal_entry_id", _uuid_type(), nullable=True),
        sa.Column("response_status", sa.SmallInteger(), nullable=True),
        sa.Column("response_body", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "owner_id",
            "operation",
            "idempotency_key",
            name="uq_idempotency_owner_operation_key",
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id", "owner_id"],
            ["journal_entries.id", "journal_entries.owner_id"],
            ondelete="RESTRICT",
            name="fk_idempotency_journal_owner",
        ),
    )
    op.create_index(
        "ix_idempotency_owner_created", "idempotency_records", ["owner_id", "created_at"]
    )

    op.create_table(
        "audit_events",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", _uuid_type(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("correlation_id", _uuid_type(), nullable=True),
    )
    op.create_index(
        "ix_audit_events_owner_occurred", "audit_events", ["owner_id", "occurred_at"]
    )
    op.create_index(
        "ix_audit_events_aggregate", "audit_events", ["aggregate_type", "aggregate_id"]
    )

    op.create_table(
        "accounting_periods",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="OPEN"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "ends_on >= starts_on", name="ck_accounting_periods_valid_range"
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'CLOSED')", name="ck_accounting_periods_status"
        ),
    )
    op.create_index(
        "ix_accounting_periods_owner_dates",
        "accounting_periods",
        ["owner_id", "starts_on", "ends_on"],
    )

    op.create_table(
        "financial_owner_preferences",
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "base_currency_definition_id",
            _uuid_type(),
            sa.ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "accounting_timezone", sa.String(64), nullable=False, server_default="UTC"
        ),
        sa.Column("locale", sa.String(32), nullable=False, server_default="en-US"),
        sa.Column(
            "reporting_calendar",
            sa.String(24),
            nullable=False,
            server_default="GREGORIAN",
        ),
    )

    if op.get_bind().dialect.name == "postgresql":
        _install_postgresql_guards()


def _install_postgresql_guards():
    op.execute(
        """
        ALTER TABLE journal_postings
        ADD CONSTRAINT ck_journal_postings_integral_minor_units
        CHECK (
            amount_minor = trunc(amount_minor)
            AND amount_minor > 0
            AND amount_minor < 100000000000000000000000000000000000000::numeric
        )
        """
    )
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE accounting_periods
        ADD CONSTRAINT ex_accounting_periods_owner_no_overlap
        EXCLUDE USING gist (
            owner_id WITH =,
            daterange(starts_on, ends_on, '[]') WITH &&
        )
        """
    )
    op.execute(
        """
        CREATE FUNCTION aurelius_reject_immutable_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Aurelius append-only record cannot be updated or deleted'
                USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in ("currency_definitions", "journal_entries", "journal_postings", "audit_events"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION aurelius_reject_immutable_mutation()
            """
        )
    op.execute(
        """
        CREATE FUNCTION aurelius_guard_account_identity()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.owner_id IS DISTINCT FROM OLD.owner_id
               OR NEW.account_type IS DISTINCT FROM OLD.account_type
               OR NEW.currency_definition_id IS DISTINCT FROM OLD.currency_definition_id
               OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'Aurelius financial account identity is immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_financial_accounts_identity_immutable
        BEFORE UPDATE ON financial_accounts
        FOR EACH ROW EXECUTE FUNCTION aurelius_guard_account_identity()
        """
    )
    op.execute(
        """
        CREATE FUNCTION aurelius_guard_idempotency_record()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Aurelius idempotency records cannot be deleted'
                    USING ERRCODE = '55000';
            END IF;
            IF OLD.owner_id IS DISTINCT FROM NEW.owner_id
               OR OLD.operation IS DISTINCT FROM NEW.operation
               OR OLD.idempotency_key IS DISTINCT FROM NEW.idempotency_key
               OR OLD.request_hash IS DISTINCT FROM NEW.request_hash
               OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
                RAISE EXCEPTION 'Aurelius idempotency identity is immutable'
                    USING ERRCODE = '55000';
            END IF;
            IF OLD.completed_at IS NOT NULL THEN
                RAISE EXCEPTION 'Aurelius completed idempotency result is immutable'
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.completed_at IS NULL
               OR NEW.response_status IS NULL
               OR NEW.response_body IS NULL THEN
                RAISE EXCEPTION 'Aurelius idempotency completion must be atomic'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_idempotency_records_completion
        BEFORE UPDATE OR DELETE ON idempotency_records
        FOR EACH ROW EXECUTE FUNCTION aurelius_guard_idempotency_record()
        """
    )
    op.execute(
        """
        CREATE FUNCTION aurelius_validate_journal()
        RETURNS trigger AS $$
        DECLARE
            target_journal_id UUID;
            journal_row journal_entries%ROWTYPE;
            posting_count BIGINT;
            debit_total NUMERIC;
            credit_total NUMERIC;
        BEGIN
            IF TG_TABLE_NAME = 'journal_entries' THEN
                target_journal_id := NEW.id;
            ELSE
                target_journal_id := NEW.journal_entry_id;
            END IF;

            SELECT * INTO journal_row
            FROM journal_entries
            WHERE id = target_journal_id;

            IF NOT FOUND THEN
                RETURN NULL;
            END IF;

            SELECT
                COUNT(*),
                COALESCE(SUM(amount_minor) FILTER (WHERE side = 'DEBIT'), 0),
                COALESCE(SUM(amount_minor) FILTER (WHERE side = 'CREDIT'), 0)
            INTO posting_count, debit_total, credit_total
            FROM journal_postings
            WHERE journal_entry_id = target_journal_id;

            IF posting_count < 2 OR debit_total <> credit_total THEN
                RAISE EXCEPTION 'Aurelius journal must contain at least two balanced postings'
                    USING ERRCODE = '23514';
            END IF;

            IF journal_row.reversal_of IS NULL AND EXISTS (
                SELECT 1
                FROM journal_postings p
                JOIN financial_accounts a ON a.id = p.account_id
                WHERE p.journal_entry_id = target_journal_id
                  AND a.status <> 'OPEN'
            ) THEN
                RAISE EXCEPTION 'Aurelius ordinary postings require open accounts'
                    USING ERRCODE = '23514';
            END IF;

            IF journal_row.reversal_of IS NOT NULL AND EXISTS (
                SELECT 1 FROM (
                    (
                        SELECT account_id, side, amount_minor
                        FROM journal_postings
                        WHERE journal_entry_id = journal_row.reversal_of
                        EXCEPT ALL
                        SELECT
                            account_id,
                            CASE side WHEN 'DEBIT' THEN 'CREDIT' ELSE 'DEBIT' END,
                            amount_minor
                        FROM journal_postings
                        WHERE journal_entry_id = target_journal_id
                    )
                    UNION ALL
                    (
                        SELECT
                            account_id,
                            CASE side WHEN 'DEBIT' THEN 'CREDIT' ELSE 'DEBIT' END,
                            amount_minor
                        FROM journal_postings
                        WHERE journal_entry_id = target_journal_id
                        EXCEPT ALL
                        SELECT account_id, side, amount_minor
                        FROM journal_postings
                        WHERE journal_entry_id = journal_row.reversal_of
                    )
                ) AS reversal_mismatch
            ) THEN
                RAISE EXCEPTION 'Aurelius reversal must exactly invert its source journal'
                    USING ERRCODE = '23514';
            END IF;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_journal_entries_validate_deferred
        AFTER INSERT ON journal_entries
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION aurelius_validate_journal()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_journal_postings_validate_deferred
        AFTER INSERT ON journal_postings
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION aurelius_validate_journal()
        """
    )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_journal_postings_validate_deferred ON journal_postings")
        op.execute("DROP TRIGGER IF EXISTS trg_journal_entries_validate_deferred ON journal_entries")
        op.execute("DROP FUNCTION IF EXISTS aurelius_validate_journal()")
        op.execute(
            "ALTER TABLE journal_postings "
            "DROP CONSTRAINT IF EXISTS ck_journal_postings_integral_minor_units"
        )
        op.execute("DROP TRIGGER IF EXISTS trg_idempotency_records_completion ON idempotency_records")
        op.execute("DROP FUNCTION IF EXISTS aurelius_guard_idempotency_record()")
        op.execute("DROP TRIGGER IF EXISTS trg_financial_accounts_identity_immutable ON financial_accounts")
        op.execute("DROP FUNCTION IF EXISTS aurelius_guard_account_identity()")
        for table in ("currency_definitions", "journal_entries", "journal_postings", "audit_events"):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
        op.execute("DROP FUNCTION IF EXISTS aurelius_reject_immutable_mutation()")
        op.execute(
            "ALTER TABLE accounting_periods "
            "DROP CONSTRAINT IF EXISTS ex_accounting_periods_owner_no_overlap"
        )

    op.drop_table("financial_owner_preferences")
    op.drop_index("ix_accounting_periods_owner_dates", table_name="accounting_periods")
    op.drop_table("accounting_periods")
    op.drop_index("ix_audit_events_aggregate", table_name="audit_events")
    op.drop_index("ix_audit_events_owner_occurred", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_idempotency_owner_created", table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_index("ix_journal_postings_account_journal", table_name="journal_postings")
    op.drop_index("ix_journal_postings_journal", table_name="journal_postings")
    op.drop_table("journal_postings")
    op.drop_index("ix_journal_entries_owner_effective_date", table_name="journal_entries")
    op.drop_table("journal_entries")
    op.drop_index("ix_financial_accounts_owner_status", table_name="financial_accounts")
    op.drop_table("financial_accounts")
    op.drop_index("ix_currency_definitions_code", table_name="currency_definitions")
    op.drop_table("currency_definitions")
