# Halal Crypto Screener

A one-page site that screens crypto coins by category using HalalScreener's verdicts, plus CoinMarketCap's top 500 with live prices, market cap and FDV.

Live at `https://<your-username>.github.io/halal/`.

## How it updates

`.github/workflows/update-and-deploy.yml` runs at **07:00 and 19:00 WIB** (00:00 and 12:00 UTC) and on manual runs. It calls CoinMarketCap's `listings/latest` for every active coin, 5,000 per page, and writes `data/market.json`. That costs 1 credit per 200 coins, about 50 credits a run and roughly 3,000 a month, within the free plan's 10,000.

A **push** only redeploys the site: it copies the `market.json` the live site already serves, so it spends no credits. If the key is missing or a call fails, the last `data/market.json` is kept.

Coins that HalalScreener hasn't rated and that aren't in `data/estimates.csv` get a category from their CoinMarketCap tags (rules in `scripts/update_prices.py`), shown as **Auto (tags)**. Prohibited and doubtful tags are checked before permissible ones.

## One-time setup

1. **Settings → Secrets and variables → Actions → New repository secret**: name `CMC_API_KEY`, value your key from https://pro.coinmarketcap.com (free Basic plan is enough).
2. **Settings → Pages → Build and deployment → Source**: choose **GitHub Actions**.
3. **Actions → Update prices and deploy → Run workflow** to publish the first time.

## Data

- `data/coins.csv`, `data/categories.csv`: HalalScreener category pages, read 17 Nov 2026.
- `data/halal_map.csv`: CoinMarketCap id → HalalScreener ticker for the 499 coins screened on 17 Nov 2026.
- `data/estimates.csv`: category and verdict for coins HalalScreener hasn't rated, applying the rule of the closest HalalScreener category. These are estimates, not HalalScreener verdicts. Coins that enter the top 500 later are matched by ticker if HalalScreener lists them, otherwise shown as Unrated.
- `data/market.json`: every active CoinMarketCap coin with its tag-based category, replaced by the workflow.

Not financial or religious advice.
