# Foundation 0.5 — Global Data Provider Candidate Review

**Reviewed:** 2026-11-17  
**Status:** Research only. No provider selected, connected, paid for, or granted credentials.

## Executive conclusion

There is no single free, universally licensed provider for all global securities, commodities, futures, fixed income, FX, crypto, prediction markets, and macro data. Aurelius should use a multi-provider architecture and treat coverage, freshness, licensing, redistribution, and jurisdiction as separate facts.

## Candidate matrix

### ECB Data Portal — reference FX and macro-financial series
- Official SDMX 2.1 REST API supports data retrieval and metadata discovery.
- Useful for daily reference exchange rates against EUR and selected central-bank/statistical series.
- Reference rates are not executable bid/ask prices or real-time trading quotes.
- Candidate for the first no-subscription FX adapter.
- Official docs: https://data.ecb.europa.eu/help/api/overview
- Examples: https://data.ecb.europa.eu/help/api/data-examples

### World Bank Data Catalog — global development and macro datasets
- Many World Bank-produced datasets default to CC BY 4.0, with attribution and change disclosure.
- Third-party datasets can carry different licenses or redistribution restrictions; each dataset's metadata must be checked.
- General site/API terms may be more restrictive than the dataset-specific license. Do not infer commercial rights from public accessibility.
- Candidate for explicitly CC-BY macro/development series, not market prices.
- Terms: https://www.worldbank.org/ext/en/legal/terms-conditions/datasets
- License catalog: https://datacatalog.worldbank.org/public-licenses

### Twelve Data — broad market-data candidate
- Basic: free; currently lists 8 API credits/minute and 800/day, real-time US equities/ETFs, forex, crypto, reference data, and global trial symbols. The plan is described as internal non-display usage.
- Grow: currently listed at USD 79/month for personal use; 20+ markets, EOD global equities/ETFs, commodities, fundamentals, and real-time US stocks.
- Pro: currently listed at USD 229/month for personal use; 70+ markets, real-time EU, delayed AU, fixed income, and mutual funds NAV.
- Some exchange data requires paid add-ons; CUSIP and ISIN add-ons are separately priced and can be expensive.
- Promising broad-market candidate, but plan scope, personal/commercial use, display rights, and exchange add-ons must be verified for each intended Aurelius workflow before subscribing.
- Pricing: https://twelvedata.com/pricing

### CoinGecko — crypto reference and market data
- Demo: free, currently 10,000 calls/month and 100 calls/minute; attribution is required.
- Paid Basic currently starts at USD 35/month billed monthly, with 100,000 credits/month and commercial license.
- Useful for broad crypto metadata/aggregated pricing and tokenized-asset exploration; not a substitute for exchange-specific execution prices.
- Demo is suitable for testing, not an assumed commercial redistribution license.
- Pricing: https://www.coingecko.com/en/api/pricing

### Alpha Vantage — low-volume prototyping
- Free stock API currently offers 25 requests/day for most datasets.
- Real-time and 15-minute delayed US stock market data are premium-only due to exchange licensing.
- Suitable for narrow prototypes and some macro/FX/crypto/commodity endpoints, not as a complete global data backbone.
- Usage/market-data notes: https://www.alphavantage.co/support/

### FRED — US macroeconomic data
- FRED API v2 requires an API key associated with a FRED account.
- Strong US macro/economic history and release-aware data; not a global securities/commodities provider.
- Limits may be changed by the provider; monitor current terms and quota.
- API: https://fred.stlouisfed.org/docs/api/fred/

### Nasdaq Data Link — specialized datasets
- Marketplace approach is useful for specialist commodity, macro, alternative, and financial datasets.
- Licensing is contract/order-form specific. Current terms restrict redistribution and use in SaaS/cloud services unless the applicable order form expressly permits it.
- Do not build a commercial product around a dataset until its exact license and order form are reviewed.
- Terms: https://data.nasdaq.com/terms

## Recommended staged provider strategy

1. **First no-subscription adapters:** ECB daily reference FX; selected World Bank CC-BY datasets; only after dataset-level license metadata is stored.
2. **Crypto prototype:** CoinGecko Demo or an exchange's own public API for exchange-specific data. Keep attribution and Demo restrictions visible; no redistribution.
3. **Broad market prototype:** evaluate Twelve Data Basic for internal non-display testing within 8 credits/minute and 800/day; no subscription or add-on without explicit approval.
4. **Global equities/commodities/fixed income:** compare Twelve Data Grow/Pro with specialist providers by exact venue, instrument, delay, history, and rights requirements. Do not assume the plan covers every exchange or futures contract.
5. **Futures/options:** treat exchange contract specs and market-data rights separately; CME, ICE, and other venues may require venue-specific licensing.
6. **Prediction/event markets:** evaluate each operator's API, jurisdiction/eligibility rules, resolution source, and data rights independently.
7. **Commercial release:** require explicit license review for internal use, display, derived analytics, model training, retention, redistribution, and customer access.

## Decision

Keep the provider adapter framework vendor-neutral. The first live adapter should be ECB reference FX because it has a clear official API and a bounded data scope. World Bank macro datasets are a second candidate only when their individual license is CC BY 4.0 or otherwise explicitly approved. Broad market-data subscriptions remain deferred until the product's actual usage and budget justify them.

No provider API key, paid subscription, external connection, or live data fetch was created during this review.
