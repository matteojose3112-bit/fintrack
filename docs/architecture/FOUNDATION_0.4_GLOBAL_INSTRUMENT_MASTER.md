# Foundation 0.4 — Global Asset, Unit, and Instrument Master

**Status:** Domain and schema design; no provider feed, trading, or instrument database migration in this milestone.

## Objective

Aurelius must represent a broad global financial universe: currencies, equities, bonds, ETFs, funds, commodities, futures, options, swaps, cryptoassets, tokenized assets, prediction/event contracts, real estate, private assets, liabilities, and non-investable benchmarks.

The architecture must be extensible. A new asset class or instrument type is a registered data vocabulary, not a code rewrite. Coverage is measured separately as:
1. representable in the domain;
2. identity/reference data verified;
3. market/valuation data available and licensed;
4. tradable/accessible in a user's jurisdiction.

No claim is made that every instrument has a public price, is listed, is investable, or is legally available everywhere.

## Domain separation

- **Asset definition:** underlying economic thing (gold, crude oil, a company, a property, an event).
- **Instrument definition:** contractual/financial wrapper (share, bond, ETF, future, option, swap, token, event outcome).
- **Identifier:** namespaced external identifier (ISIN, FIGI, CUSIP, SEDOL, LEI, DTI, exchange contract code, crypto network/address, provider ID).
- **Venue:** exchange or trading venue with MIC, country, timezone, trading calendar, and status.
- **Listing:** time-bounded relationship between an instrument and venue; ticker is unique only within its relevant venue/time context.
- **Unit:** exact quantity dimension and unit (troy ounce, barrel, MMBtu, bushel, metric tonne, share, contract, token, MWh, square metre).
- **Contract specification:** futures/options/bonds/prediction contracts have explicit terms, not inferred from a ticker.
- **Holding:** owner-specific position in an instrument; separate from the global instrument master.
- **Observation:** price, yield, FX rate, benchmark, or fundamental datum with source, timestamp, currency/unit, methodology, and license provenance.
- **Forecast:** a probabilistic model output with target, horizon, model version, evidence, and outcome rule. It is not an instrument or a market price.

## Open asset-class vocabulary

Initial classes include:
- cash_currency, fx_pair, equity, depositary_receipt, fixed_income, fund, money_market, commodity, derivative, crypto_asset, stablecoin, tokenized_asset, real_estate, private_equity, private_credit, loan, receivable, royalty, collectible, infrastructure, liability, index, benchmark, macro_series, prediction_contract, forecast_target, and other.

This vocabulary is intentionally open. Unknown but valid class/type strings can be registered with metadata and validation rules. New classes must declare identity, units, lifecycle, valuation method, provenance, and jurisdiction rules.

## Commodity coverage model

The underlying commodity is distinct from each venue's contract:
- Precious metals: gold, silver, platinum, palladium.
- Industrial/base metals: copper, aluminium, nickel, zinc, tin, lead.
- Energy: WTI/Brent crude, natural gas, gasoline, diesel, heating oil, coal, electricity.
- Agriculture: wheat, corn, soybeans, rice, sugar, coffee, cocoa, cotton, livestock.
- Environmental: emissions allowances, renewable certificates, water rights.

A futures instrument must retain exchange, contract code, underlying, grade/quality, delivery location, contract unit, contract size, tick size/value, expiry, first notice date, last trade date, settlement/delivery method, margin currency, and lifecycle. "Gold" is not a futures contract; a COMEX gold future is a dated venue-specific contract with its own specification.

## Securities and fixed income

- Equity/security master uses internal stable ID plus ISIN/FIGI and provider identifiers.
- Listings bind instruments to MIC venues and retain ticker history, quote currency, active dates, and trading calendar.
- Bonds require issuer, currency, face value, issue/maturity dates, coupon/rate type, frequency, day-count convention, seniority, redemption, and optional call/put terms.
- Funds/ETFs retain share class, domicile, base currency, replication, distribution policy, and identifiers.
- Corporate actions are separate dated events and must not overwrite raw prices or historical holdings.

## Digital assets

A token identity must include network/chain and contract address where applicable, plus token decimals, issuer/protocol, custody model, wrapped/bridged status, and source confidence. Native coins, stablecoins, wrapped assets, liquid-staking tokens, NFTs, tokenized securities, and DeFi positions are separate instrument/position types. A ticker or token name alone is not globally unique.

## Prediction/event markets versus forecasts

Prediction markets are instruments/contracts with:
- event identity and precise question;
- finite or continuous outcome space;
- resolution authority/source and objective resolution criteria;
- resolution deadline/timezone;
- settlement asset/currency, payout, fees, and market operator;
- jurisdiction/eligibility rules;
- market price and implied probability semantics.

Aurelius's own forecasts are separate records with model/version, probability, horizon, target, evidence, timestamp, and later outcome. Market-implied probability is not ground truth and is not the same as a calibrated Aurelius forecast.

## Units and precision

Do not store all quantities as fiat minor units. Use an explicit unit registry with:
- stable unit code and dimension;
- symbol and canonical base unit;
- exact rational conversion numerator/denominator where a universal conversion exists;
- context-required flag where conversion depends on commodity grade/contract (e.g. bushel weight);
- quantity precision and rounding policy.

Contract size, tick size, lot size, multiplier, minimum increment, and quantity precision are distinct from quote-currency precision. No binary floats for quantities or prices.

## Global venue identity

Use ISO 10383 MICs for trading venues. Store venue timezone as an IANA TZ database identifier and retain market calendar/version. A venue MIC is not a country code, and a ticker is not a global identifier. Listings are time-bounded.

## Planned persistence tables

1. unit_definitions
2. asset_definitions
3. instrument_definitions
4. instrument_identifiers
5. market_venues
6. instrument_listings
7. derivative_contract_specs
8. bond_contract_specs
9. prediction_contract_specs

Later:
- market_observations, provider_sources, provider_licenses, corporate_actions;
- portfolio_holdings, position_lots, valuation_snapshots;
- forecast_records, prediction_outcomes, model_evaluations.

Global reference data is not owner-scoped. Holdings, accounts, decisions, forecasts, and portfolios are owner-scoped and must preserve account isolation.

## Initial reference assets for domain tests

The initial seed catalog is illustrative and extensible, not an exhaustive market database: gold, silver, platinum, palladium, WTI crude, Brent crude, natural gas, copper, aluminium, wheat, corn, soybeans, coffee, cocoa, and electricity. No prices, tickers, exchange listings, or futures expiry data are fabricated.

## Rollout sequence

1. Exact unit registry and generic asset definitions.
2. Instrument definitions and namespaced identifiers.
3. MIC venue registry and time-bounded listings.
4. Derivative/futures/options/bond/prediction contract specifications.
5. PostgreSQL persistence and seed/version process.
6. Licensed provider adapters and market observations.
7. Owner holdings, valuation, FX, and portfolio analytics.

No broker order execution is included in this foundation.

## Domain implementation status

Implemented in backend/app/domain/asset_registry.py: exact unit registry, extensible asset catalog, namespaced identifiers, instrument definitions, MIC/timezone venues, time-bounded listings, derivative/futures specifications, bond terms, and prediction-contract resolution specifications. These are domain types only; persistence and provider adapters remain future work.

## Persistence implementation status

Foundation 0.4 persistence is implemented in backend/app/persistence/instrument_models.py and Alembic revision 0003_global_instrument_master.py. The migration adds exact unit/asset/instrument reference tables, identifiers, MIC venues/listings, derivative/bond/prediction contract specs, provider source terms, market observations, forecast records, and separate resolutions. PostgreSQL enforces non-overlapping identifier/listing validity windows and append-only reference/observation/forecast history. The curated unit/asset seed is idempotent and explicit. Latest CI: 31 PostgreSQL integration tests and 125 backend tests passed. No external market data or provider subscription has been added.
