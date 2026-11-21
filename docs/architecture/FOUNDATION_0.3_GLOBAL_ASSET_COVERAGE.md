# Aurelius Global Asset and Instrument Coverage

**Status:** Product/domain coverage baseline for Foundation 0.3 and subsequent market-data foundations.

## Product objective

Aurelius should represent and analyze a very broad range of financial and real-world assets across global markets. The goal is extensible coverage, not a brittle hard-coded list of tickers. A new asset class, venue, unit, identifier namespace, or provider should be addable without rewriting the accounting core.

"Everything" is an extensibility objective, not a claim that every asset has a reliable public price, tradable market, legal availability, or licensed data feed. Coverage must distinguish supported representation, verified reference data, observable market data, and executable market access.

## Separate concepts that must not be conflated

- **Asset / underlying:** the economic thing being owned, referenced, consumed, or measured (gold, a company, a bond issuer, a building, an event outcome).
- **Instrument / contract:** the legal or financial wrapper that creates rights and obligations (share, bond, ETF, future, option, swap, perpetual, prediction contract).
- **Listing / venue:** where an instrument is quoted or traded, with MIC, ticker, quote currency, session calendar, timezone, and active dates.
- **Position / holding:** an owner's quantity or exposure to an instrument, with lot, custody, leverage, collateral, and lifecycle attributes.
- **Unit / quantity:** shares, troy ounces, barrels, MMBtu, bushels, metric tonnes, MWh, contracts, tokens, square metres, event-outcome shares, etc.
- **Price / valuation:** an observation with unit, currency, timestamp, market session, source, methodology, quality, and licensing provenance.
- **Cash currency:** ISO 4217 currency registry entry; it is not a generic asset/instrument type.
- **Forecast / prediction:** a time-stamped probabilistic claim about a future event or value, not a holding or guaranteed price.

## Initial coverage taxonomy

### Cash, FX, and monetary units
Fiat currencies, historical currencies, fund/accounting units, FX pairs, spot/forward rates, NDFs, and currency futures. ISO 4217 applies to monetary codes; fund/reference codes and precious-metal codes must not be silently treated as ordinary cash currencies.

### Public securities
Common/preferred equities, depositary receipts, ETFs, ETNs, mutual funds, money-market funds, closed-end funds, sovereign/municipal/corporate bonds, bills, notes, commercial paper, sukuk, warrants, rights, convertibles, and structured notes.

### Derivatives
Listed and OTC futures, options, forwards, swaps, swaptions, CFDs, spread bets, warrants, perpetual swaps, structured products, and bespoke contracts. Preserve underlying, multiplier, contract size, tick size/value, expiry, exercise style, strike, settlement type, delivery location/grade, margin/collateral, clearing house, and lifecycle events.

### Commodities and physical markets
Precious metals (gold, silver, platinum, palladium), base/industrial metals (copper, aluminium, nickel, zinc, tin, lead), energy (WTI/Brent crude, natural gas, gasoline, diesel, heating oil, coal, power), agriculture (wheat, corn, soybeans, rice, sugar, coffee, cocoa, cotton, livestock), and emissions/environmental certificates. Units and contract grades differ by market and venue; never assume a generic commodity ticker defines contract terms.

### Digital assets
Native cryptocurrencies, fungible tokens, stablecoins, wrapped assets, liquid staking tokens, NFTs, tokenized securities/real-world assets, protocol positions, and on-chain lending/liquidity positions. Identity must include chain/network and contract address where relevant; decimals, custody, bridge risk, issuer, and depeg/contract risks are distinct attributes.

### Real and alternative assets
Residential/commercial/industrial/agricultural real estate, land, infrastructure, private equity, venture capital, private credit, loans, receivables, royalties, art, collectibles, precious-metal physical holdings, equipment, vehicles, and other illiquid assets. Track ownership share, location/jurisdiction, valuation method, valuation date, appraisal source, liquidity assumptions, encumbrances, and provenance.

### Prediction and event markets
Binary and multi-outcome event contracts, sports/political/economic/scientific/weather event markets, conditional tokens, and forecast instruments. Preserve event definition, outcome set, resolution source, resolution timestamp/rules, market operator, jurisdiction eligibility, fees, collateral/settlement asset, order book, and probability/price semantics. Distinguish a market-implied probability from a calibrated forecast or objective truth.

### Indices, benchmarks, and macro data
Equity/bond/commodity indices, volatility indices, benchmark rates, yield curves, inflation, employment, GDP, central-bank policy rates, money supply, trade, housing, and other official statistical series. These are reference/observation series, not necessarily investable holdings.

### Liabilities and obligations
Mortgages, consumer/business loans, credit cards, leases, margin loans, accrued interest, tax liabilities, and contingent obligations. A liability is not modeled as a positive asset holding.

## Identifier strategy

- Internal immutable UUID/ULID-style instrument identity is primary inside Aurelius.
- Preserve external identifiers with namespace and source: ISIN, FIGI, CUSIP, SEDOL, LEI, DTI, MIC, OCC/OSI option symbol, exchange contract code, crypto chain/contract address, and provider IDs.
- A ticker is never globally unique. A listing is a time-bounded relationship between instrument and venue.
- Identifiers can be missing, reused, retired, corrected, or disputed; preserve history and source confidence rather than overwriting identity.

## Quantity and precision

Do not force every position into fiat minor units or a single Decimal scale. Store exact decimal quantities as canonical decimal strings at API boundaries and NUMERIC at persistence boundaries, with per-instrument/unit precision and explicit rounding rules. Contract multipliers, tick size, lot size, minimum increment, and fractional ownership are separate from quote currency precision.

## Market data and provenance

Every observation should include:
- instrument/series identity and field/measure;
- value and unit, quote currency where relevant;
- event/observation time, retrieval time, timezone/session;
- provider, source record ID, source payload/hash, adjustment methodology;
- delay/freshness, quality flags, and license/redistribution classification.

Keep raw provider payloads separate from normalized records. Provider adapters normalize data but must not erase source provenance. Support multiple sources and disagreement analysis; do not silently select one "truth" for conflicting observations.

## Architecture and rollout

1. ISO 4217 registry and exact monetary-unit handling.
2. Generic unit/asset ontology and instrument master.
3. Exchange MICs, listings, calendars, corporate actions, and contract specifications.
4. Commodity spot/futures reference models and historical market data.
5. Securities and fixed-income reference models.
6. FX and cross-currency portfolio valuation.
7. Crypto and on-chain assets.
8. Prediction/event market contracts and probabilistic forecast registry.
9. Real/alternative asset valuations and liabilities.
10. Cross-asset risk, portfolio analytics, research, and AI orchestration.

Each vertical is enabled only when identity, units, lifecycle, source provenance, data rights, and jurisdiction rules are defined. Trading/brokerage execution remains separately gated and disabled by default.
