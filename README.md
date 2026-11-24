# FinTrack

**Personal finance, made clearer.**

A responsive personal finance dashboard concept for cash flow, transactions, budgets, savings goals, accounts and investment holdings.

## Demo

The public-facing dashboard uses illustrative sample data. No bank, brokerage or payment account is connected.

## Features
- Financial overview with balance, income, expenses and savings-rate cards.
- Cash-flow and spending visualizations.
- Searchable transaction list and add-transaction interaction.
- Budget categories and spending progress.
- Savings goals and contributions.
- Multi-account and investment holdings views.
- USD/COP display toggle for the demo workspace.
- Versioned browser-local persistence for demo workspace collections.
- Responsive desktop and mobile navigation.

## Run locally
```bash
npm install
npm run dev
npm test
npm run build
```

## Product boundaries
This frontend currently runs in demo mode with browser-memory sample data. It does not claim live bank balances, live market prices, authenticated account storage, brokerage connectivity or trade execution. API integration is a subsequent milestone.

## Technology
Vanilla JavaScript, HTML5, CSS3, Vite and Vitest.
