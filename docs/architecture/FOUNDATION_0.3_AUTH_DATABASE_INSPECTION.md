# Foundation 0.3 — Authentication, Database, and Environment Inspection

**Inspection date:** 2026-11-17  
**Branch:** Foundation 0.3 global persistence  
**Scope:** repository inspection only; no hosted environment queried or modified.

## Authentication findings

Inspected:
- backend/app/models.py
- backend/app/auth.py
- backend/app/database.py
- backend/migrations/versions/0001_initial_schema.py
- backend/migrations/env.py

Findings:
- User.id is SQLAlchemy Integer primary key.
- JWT subject is the string representation of User.id; current-user dependency parses it to int and loads User.
- Existing transactions, budgets, and goals use Integer user_id foreign keys.
- The first Aurelius persistence models should reference users.id as INTEGER. Do not create a second identity table or use UUID owner IDs in the first release.
- Financial history must not cascade-delete with login records. New owner foreign keys should RESTRICT deletion; account closure/deactivation is a separate lifecycle.
- The existing user model has no organization/household abstraction. Future legal/entity ownership needs a dedicated financial owner model and explicit migration.

## Database findings

- SQLAlchemy 2.0.36, Alembic 1.14.0, psycopg 3.2.3 are pinned in backend/requirements.txt.
- DATABASE_URL defaults to SQLite for local development. PostgreSQL URLs are normalized to psycopg.
- The migration environment loads app.models and uses Base.metadata.
- The existing initial migration creates users and legacy financial tables; it uses floating-point amounts in legacy records.
- The Render Blueprint references a managed database connection string but does not pin a PostgreSQL major version.
- No Docker Compose/PostgreSQL service or declared PostgreSQL major version was found in the inspected paths.

## Decisions for isolated Foundation 0.3 work

- Owner FK type: INTEGER -> users.id.
- Ledger entity IDs: UUID, separate from authentication identity.
- PostgreSQL CI baseline: version 16. This is not evidence that the existing hosted database is version 16; that remains unverified and must be checked before any migration/deployment.
- Cross-row ledger integrity: initially deferred PostgreSQL constraint triggers, with append-only triggers and restricted runtime privileges.
- No hosted database inspection or changes, no Render operations, no secret access, and no production data access.

## Global product implications

Do not encode country, residence, base currency, timezone, or tax jurisdiction into the authentication user ID. Store separate owner preferences and effective-dated jurisdiction attributes. Accounts may use any supported ISO currency independently of the owner's reporting currency. Market instruments/listings and crypto/commodity units are separate from cash currency.
