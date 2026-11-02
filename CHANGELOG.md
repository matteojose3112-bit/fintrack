# Changelog

All notable project changes are documented here.

## [1.2.0] - 2026-11-02

### Added
- Automated FastAPI integration tests for health checks and transaction workflows.
- Coverage for transaction validation, dashboard summaries, budget creation and duplicate protection.
- Coverage for savings-goal creation, contributions, missing-goal handling, and CSV export.
- Isolated in-memory SQLite test fixtures to keep tests separate from local finance data.
- pytest and a compatible httpx test dependency.
- GitHub Actions execution of backend tests on pushes and pull requests to `main`.

## [1.1.0] - 2026-11-02

### Added
- Dedicated budget management screen with category spending progress and remaining limits.
- Budget creation form connected to the FastAPI endpoint.
- Dedicated savings goals screen with target progress.
- Savings goal creation and contribution forms connected to the API.
- Context-aware primary action for transactions, budgets, and savings goals.

## [1.0.0] - 2026-11-02

### Added
- Initial FinTrack repository and project documentation.
- React + Vite frontend with a responsive dark dashboard.
- FastAPI backend with SQLite persistence through SQLAlchemy.
- Transaction creation, listing, and deletion.
- Monthly income and expense summaries with chart-ready analytics.
- Budget and savings-goal API foundations.
- CSV transaction export.
- Local development setup and API documentation through FastAPI Swagger UI.
