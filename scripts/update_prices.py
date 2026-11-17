"""Write data/market.json: every active coin on CoinMarketCap, with a tag-based category.

Two modes, chosen by the workflow:
  fetch  (schedule 07:00 / 19:00 WIB, or a manual run) – call CoinMarketCap's listings/latest,
         paging 5,000 coins at a time. It costs 1 credit per 200 coins, so ~10,000 coins is ~50
         credits a run, ~3,000 a month on the free plan's 10,000.
  reuse  (a push that only changes the site) – copy the market.json the live site already serves,
         so redeploying spends no credits. Falls back to fetch only if the live file is missing.

If the key is missing or a call fails, the existing data/market.json is kept. Standard library only.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "market.json")
API = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
PAGE = 5000          # the largest page listings/latest allows
MAX_COINS = 20000    # safety cap

# CoinMarketCap tag slug -> (category, verdict). First matching rule wins, and the rules run from
# strictest to most lenient, so a coin with any doubtful or prohibited tag is never marked Halal.
RULES = [
    ("Gambling & Prediction", "Not Halal", ["gambling", "casino", "prediction-markets", "betting"]),
    ("Lending, Yield & Derivatives", "Not Halal", ["lending-borowing", "lending-borrowing", "derivatives", "perpetuals",
                                                   "yield-aggregator", "tokenized-treasury-bonds", "tokenized-treasury-bills"]),
    ("Meme Coins", "Doubtful", ["memes", "meme", "animal-memes", "political-memes", "celebrity-memes", "ai-memes",
                                "cat-themed", "dog-themed", "doggone-doggerel", "frog-themed", "pump-fun-ecosystem", "four-meme-ecosystem"]),
    ("Stablecoins", "Doubtful", ["stablecoin", "usd-stablecoin", "eur-stablecoin", "asset-backed-stablecoin",
                                 "algorithmic-stablecoin", "fiat-stablecoin"]),
    ("Tokenized & Wrapped", "Doubtful", ["tokenized-stock", "tokenized-assets", "tokenized-gold", "tokenized-commodities",
                                         "wrapped-tokens", "real-world-assets-protocols"]),
    ("Privacy Coins", "Doubtful", ["privacy-blockchain"]),
    ("DeFi & Staking", "Doubtful", ["defi", "decentralized-exchange-dex-token", "dex", "amm", "staking", "liquid-staking-derivatives",
                                    "restaking", "yield-farming", "launchpad"]),
    ("Gaming & NFT", "Halal", ["gaming", "play-to-earn", "metaverse", "collectibles-nfts", "nft", "trading-card-game"]),
    ("Payments & Exchange", "Halal", ["centralized-exchange", "payments", "discount-token", "wallet", "remittance"]),
    ("Infrastructure & AI", "Halal", ["ai-big-data", "distributed-computing", "storage", "filesharing", "oracles", "depin",
                                      "iot", "interoperability", "cross-chain", "identity", "data-provenance", "generative-ai", "ai-agents"]),
    ("Layer 1 & Layer 2", "Halal", ["layer-1", "layer-2", "platform", "smart-contracts", "scaling", "pow", "pos", "dpos",
                                    "mineable", "modular-blockchain", "zero-knowledge-proofs"]),
]


def classify(tags):
    tags = set(tags or [])
    for cat, verdict, keys in RULES:
        hit = next((k for k in keys if k in tags), None)
        if hit:
            return cat, verdict, hit
    return "", "Unrated", ""


def fetch_cmc(key):
    coins, start, credits, stamp = [], 1, 0, None
    while start <= MAX_COINS:
        url = f"{API}?start={start}&limit={PAGE}&convert=USD&sort=market_cap"
        req = urllib.request.Request(url, headers={"X-CMC_PRO_API_KEY": key, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.load(r)
        status = body.get("status", {})
        if status.get("error_code"):
            raise RuntimeError(f"CoinMarketCap error {status.get('error_code')}: {status.get('error_message')}")
        credits += status.get("credit_count") or 0
        stamp = stamp or status.get("timestamp")
        page = body.get("data", [])
        for c in page:
            if c.get("cmc_rank") is None:
                continue
            q = (c.get("quote") or {}).get("USD") or {}
            cat, verdict, tag = classify(c.get("tags"))
            coins.append({
                "id": c.get("id"), "rank": c.get("cmc_rank"), "name": c.get("name"), "symbol": c.get("symbol"),
                "slug": c.get("slug"), "price": q.get("price"), "pct24": q.get("percent_change_24h"),
                "pct7d": q.get("percent_change_7d"), "mcap": q.get("market_cap"), "fdv": q.get("fully_diluted_market_cap"),
                "ac": cat, "as": verdict, "at": tag,
            })
        if len(page) < PAGE:
            break
        start += PAGE
    coins.sort(key=lambda c: c["rank"])
    return {"updated": stamp or datetime.now(timezone.utc).isoformat(), "source": "coinmarketcap",
            "credits": credits, "count": len(coins), "coins": coins}


def live_copy():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repo:
        return None
    owner, name = repo.split("/", 1)
    url = f"https://{owner.lower()}.github.io/{name}/data/market.json"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            data = json.load(r)
    except Exception as e:
        print(f"Live copy not available ({e})")
        return None
    if data.get("source") != "coinmarketcap" or len(data.get("coins", [])) < 100:
        print("Live copy is not CoinMarketCap data")
        return None
    return data


def write(data):
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "fetch").lower()
    if mode == "reuse":
        data = live_copy()
        if data:
            write(data)
            print(f"Reused live data: {len(data['coins'])} coins from {data['updated']} (no credits used)")
            return 0
        print("Falling back to a fresh fetch")
    key = os.environ.get("CMC_API_KEY", "").strip()
    if not key:
        print("CMC_API_KEY not set; keeping existing data/market.json")
        return 0
    try:
        data = fetch_cmc(key)
    except Exception as e:
        print(f"CoinMarketCap request failed: {e}; keeping existing data/market.json")
        return 0
    if len(data["coins"]) < 100:
        print(f"Only {len(data['coins'])} coins returned; keeping existing file")
        return 0
    write(data)
    print(f"Wrote {data['count']} coins, updated {data['updated']}, credits used {data['credits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
