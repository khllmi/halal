# Halal Crypto Screener

A one-page site that screens crypto coins by category using HalalScreener's verdicts, plus CoinMarketCap's top 500 with live prices, market cap and FDV.

Live at `https://<your-username>.github.io/halal/`.

## How it updates

`.github/workflows/update-and-deploy.yml` runs on every push and every 20 minutes. It calls CoinMarketCap's `listings/latest` (top 500, 3 credits per run, about 6,500 credits a month on the free plan's 10,000), writes `data/market.json`, and deploys the site to GitHub Pages. If the API key is missing or the call fails, the last `data/market.json` is kept.

## One-time setup

1. **Settings → Secrets and variables → Actions → New repository secret**: name `CMC_API_KEY`, value your key from https://pro.coinmarketcap.com (free Basic plan is enough).
2. **Settings → Pages → Build and deployment → Source**: choose **GitHub Actions**.
3. **Actions → Update prices and deploy → Run workflow** to publish the first time.

## Data

- `data/coins.csv`, `data/categories.csv`: HalalScreener category pages, read 17 Nov 2026.
- `data/halal_map.csv`: CoinMarketCap id → HalalScreener ticker for the 499 coins screened on 17 Nov 2026.
- `data/estimates.csv`: category and verdict for coins HalalScreener hasn't rated, applying the rule of the closest HalalScreener category. These are estimates, not HalalScreener verdicts. Coins that enter the top 500 later are matched by ticker if HalalScreener lists them, otherwise shown as Unrated.
- `data/market.json`: CoinMarketCap top 500, replaced by the workflow.

Not financial or religious advice.
