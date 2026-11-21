# Aurelius Global Markets and Internationalization Architecture

**Status:** Foundation design baseline  
**Principle:** global by architecture; market/provider availability remains jurisdiction- and license-aware.

## Product coverage

Aurelius should be able to serve users across countries without assuming their residence, tax jurisdiction, preferred language, accounting timezone, home currency, or broker. A user may hold accounts in several countries and currencies, own instruments listed on multiple exchanges, and choose a separate reporting currency.

## Separate domain concepts

1. **Person / login:** authentication identity and credentials.
2. **Financial owner:** person, household, company, trust, or other legal/accounting owner. First release maps owner to the existing user; future multi-entity support gets an explicit owner entity.
3. **Jurisdiction:** residence, tax residence, legal entity domicile, account location, and regulatory classification. These are separate time-bounded attributes, not one country field.
4. **Currency:** ISO 4217 fiat and recognized currency/fund reference codes, with historical/versioned registry facts.
5. **Instrument:** security, ETF, bond, derivative, commodity, fund, or cryptoasset with stable internal identity and instrument-specific precision.
6. **Listing / venue:** an instrument's tradable listing on a venue, with MIC, ticker, quote currency, timezone, trading calendar, and active dates.
7. **Market observation:** price, FX, fundamental, macro, or news datum with source, observed timestamp, retrieval timestamp, unit, currency, market session, and provenance.

## Currency coverage and registry maintenance

Use the official ISO 4217 Maintenance Agency (SIX) as the source of truth for currency codes and minor-unit metadata. Import an identified release into an immutable registry version; preserve the source URL, retrieval date, release identifier, and checksum. Never fetch mutable registry data at runtime to interpret historical journal amounts.

Keep current currencies, historical denominations, fund codes, and precious-metal/reference codes distinguishable. Only cash currencies with defined minor-unit exponents can be selected for cash accounts. Historical currency codes remain available for old ledger events. A redenomination creates a new effective-dated definition and explicit conversion event; it does not mutate prior balances.

Cryptocurrencies are not ISO fiat currencies. Support them through a separate namespaced asset registry with issuer/network, contract address where applicable, quantity precision, and valuation currency. Commodity units (troy ounce, barrel, MWh, etc.) and derivative contract multipliers also require instrument/unit metadata. Do not apply fiat currency exponents to those quantities.

## International accounting and presentation

- Each owner has an optional reporting/base currency, independent of account currencies.
- Each owner has an IANA timezone for accounting date cutoffs and a locale for presentation.
- Store instants as UTC; retain exchange-local timestamps/session identifiers for market events.
- Store accounting effective dates as DATE under explicit owner accounting timezone policy.
- Display decimal separators, grouping, symbols, and date formats by locale, but never parse or persist money using locale-dependent strings.
- Tax rules are jurisdiction-specific and effective-dated; no universal tax treatment is assumed.
- Financial products, brokers, market data, and trading features must check country eligibility and contractual data rights.

## FX and valuation

FX is market data, not a formatting conversion. Every valuation conversion records base currency, quote currency, rate, bid/ask/mid, source/provider, observed_at, retrieved_at, and methodology. Portfolio valuations preserve the exact FX observation used so historical reports can be reproduced. Cross-currency transfers create linked balanced legs and explicit FX gain/loss/fee treatment; a single journal is never balanced across currencies.

## Global market identifiers

- ISO 10383 MIC identifies trading venues; MIC is not a ticker.
- ISIN identifies securities where available; FIGI and provider identifiers may supplement it.
- Ticker alone is not globally unique and may be reused over time.
- Listings retain venue, quote currency, timezone, trading calendar, symbol, and active date range.
- Market data adapters normalize provider data without erasing original source payload/provenance.

## Global rollout sequence

1. Complete ISO currency registry ingestion and historical version tests.
2. Complete account/journal persistence in multiple currencies.
3. Add FX observations and reproducible multi-currency valuation.
4. Add instrument master and listings/venue calendars.
5. Add provider adapters and coverage/licensing registry.
6. Add jurisdiction-specific tax and regulatory modules only with verified sources and explicit scope.
7. Add broker integrations only after eligibility, permissions, audit, and explicit user approval controls.

## Authoritative reference sources

- ISO 4217 overview: https://www.iso.org/iso-4217-currency-codes.html
- SIX, official ISO 4217 Maintenance Agency and current/historical lists: https://www.six-group.com/en/products-services/financial-information/market-reference-data/data-standards.html
- ISO 10383 MIC standard overview: https://www.iso20022.org/market-identifier-codes
