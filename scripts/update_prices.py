"""Fetch CoinMarketCap's current top 500 and write data/market.json.

Runs in GitHub Actions with the CMC_API_KEY secret. Uses only the standard library.
listings/latest costs 1 credit per 200 coins, so one run of 500 coins costs 3 credits.
If the key is missing or the call fails, the existing data/market.json is left as it is.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "market.json")
URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?start=1&limit=500&convert=USD&sort=market_cap"


def main():
    key = os.environ.get("CMC_API_KEY", "").strip()
    if not key:
        print("CMC_API_KEY not set; keeping existing data/market.json")
        return 0
    req = urllib.request.Request(URL, headers={"X-CMC_PRO_API_KEY": key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.load(r)
    except Exception as e:  # keep the last good file rather than failing the deploy
        print(f"CoinMarketCap request failed: {e}; keeping existing data/market.json")
        return 0
    status = body.get("status", {})
    if status.get("error_code"):
        print(f"CoinMarketCap error {status.get('error_code')}: {status.get('error_message')}; keeping existing file")
        return 0
    coins = []
    for c in body.get("data", []):
        q = (c.get("quote") or {}).get("USD") or {}
        coins.append({
            "id": c.get("id"),
            "rank": c.get("cmc_rank"),
            "name": c.get("name"),
            "symbol": c.get("symbol"),
            "slug": c.get("slug"),
            "price": q.get("price"),
            "pct24": q.get("percent_change_24h"),
            "pct7d": q.get("percent_change_7d"),
            "mcap": q.get("market_cap"),
            "fdv": q.get("fully_diluted_market_cap"),
        })
    if len(coins) < 100:
        print(f"Only {len(coins)} coins returned; keeping existing file")
        return 0
    out = {
        "updated": status.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "source": "coinmarketcap",
        "credits": status.get("credit_count"),
        "coins": coins,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"Wrote {len(coins)} coins, updated {out['updated']}, credits used {out['credits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
