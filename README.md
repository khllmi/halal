# Halal Crypto Screener

A one-page site that screens crypto coins by category using HalalScreener's verdicts, plus CoinMarketCap's top 500 with live prices, market cap and FDV.

Live at `https://<your-username>.github.io/halal/`.

## How it updates

`.github/workflows/update-and-deploy.yml` runs on two schedules:

| When | What it fetches | File | Credits |
|---|---|---|---|
| Every hour | Top 500 | `data/market.json` | 3 a run, ~2,200 a month |
| 07:00 and 19:00 WIB (00:00, 12:00 UTC) | Every active coin | `data/market_all.json`, and the top 500 from the same data | ~50 a run, ~3,000 a month |

That is about 5,200 of the free plan's 10,000 credits a month.

A **push** only redeploys the site: it copies both files the live site already serves, so it spends no credits. If the key is missing or a call fails, the file already in place is kept.

Coins that HalalScreener hasn't rated and that aren't in `data/estimates.csv` get a category from their CoinMarketCap tags (rules in `scripts/update_prices.py`), shown as **Auto (tags)**. Prohibited and doubtful tags are checked before permissible ones.

Run it by hand from **Actions → Update prices and deploy → Run workflow**, choosing `all`, `top500` or `reuse`.

## One-time setup

1. **Settings → Secrets and variables → Actions → New repository secret**: name `CMC_API_KEY`, value your key from https://pro.coinmarketcap.com (free Basic plan is enough).
2. **Settings → Pages → Build and deployment → Source**: choose **GitHub Actions**.
3. **Actions → Update prices and deploy → Run workflow** to publish the first time.

## Data

- `data/coins.csv`, `data/categories.csv`: HalalScreener category pages, read 17 Nov 2026.
- `data/halal_map.csv`: CoinMarketCap id → HalalScreener ticker for the 499 coins screened on 17 Nov 2026.
- `data/estimates.csv`: category and verdict for coins HalalScreener hasn't rated, applying the rule of the closest HalalScreener category. These are estimates, not HalalScreener verdicts. Coins that enter the top 500 later are matched by ticker if HalalScreener lists them, otherwise shown as Unrated.
- `data/market.json`: CoinMarketCap's top 500 with its tag-based category, replaced hourly.
- `data/market_all.json`: every active CoinMarketCap coin, replaced twice a day. The site loads it only when you pick **All coins**.

Not financial or religious advice.
