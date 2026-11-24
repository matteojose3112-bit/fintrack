# FinTrack Roadmap

## 0.1 — Public portfolio experience
- [x] Replace the temporary CSV Studio entry experience with the FinTrack dashboard.
- [x] Establish Aster-aligned dark styling and responsive layout.
- [x] Add overview, transactions, budgets, savings goals, investments and accounts.
- [x] Add interactive demo transactions, budget creation and savings contributions.
- [x] Disclose sample data and unavailable live integrations.
- [x] Verify production build and publish GitHub Pages.

## 0.2 — Frontend quality
- [ ] Add interaction tests for navigation, transactions, budgets and goals.
- [ ] Improve chart accessibility and empty states.
- [x] Add versioned local browser storage for demo transactions, budgets, goals, holdings and accounts.
- [ ] Add portfolio screenshots and project presentation.

## 0.3 — API integration
- [ ] Connect authentication and owner-scoped financial data.
- [ ] Replace sample transactions, budgets and goals with API-backed records.
- [ ] Add loading, error, retry and session-expiry states.
- [ ] Verify production CORS and API configuration.

## 0.4 — Full personal finance
- [x] Add validated account, category and transaction domain models.
- [x] Add balanced paired-entry transfers with integrity validation.
- [x] Add recurring transaction rules with safe calendar scheduling.
- [x] Add currency-scoped account balance and cash-flow reporting.
- [ ] Add user-facing transfer, reconciliation and recurring transaction screens.
- [x] Add integer minor-unit money parsing and arithmetic for USD, COP, CAD, EUR and GBP.
- [ ] Add persisted currency-aware multi-currency reporting.
- [x] Add a reusable cash-flow reporting primitive with internal transfers excluded.
- [ ] Add interactive cash-flow reports, budgets and goal analytics.
- [x] CSV export for demo transactions with spreadsheet-formula injection protection.\n- [ ] CSV import with column mapping, validation preview and duplicate detection.\n- [ ] Audit history.

## 0.5 — Investments
- [ ] Persist portfolios, holdings and instrument metadata.
- [ ] Connect appropriately licensed market/reference data providers.
- [ ] Show timestamped valuations and source attribution.
- [ ] No brokerage execution without a separately approved design.
