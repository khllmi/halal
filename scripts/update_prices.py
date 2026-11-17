"""Write the site's CoinMarketCap data, with a tag-based category on each coin.

Two files:
  data/market.json      the top 500, refreshed hourly (3 credits a run, ~2,200 a month)
  data/market_all.json  every active coin, refreshed at 07:00 and 19:00 WIB
                        (~50 credits a run, ~3,000 a month)

Modes, chosen by the workflow:
  top500  fetch the top 500 only; keep the live copy of the all-coins file
  all     fetch every coin, then take the top 500 from the same data, so the hourly
          file is refreshed at no extra cost
  reuse   a push that only changes the site: copy both files the live site serves,
          so redeploying spends no credits

Together that is ~5,200 of the free plan's 10,000 credits a month. If the key is missing
or a call fails, the file already in place is kept. Standard library only.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
OUT_TOP = os.path.join(DATA, "market.json")
OUT_ALL = os.path.join(DATA, "market_all.json")
TOP_N = 500
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


def fetch_cmc(key, limit=None):
    """Fetch coins by market cap. limit=None means every active coin."""
    coins, start, credits, stamp = [], 1, 0, None
    while start <= (limit or MAX_COINS):
        page_size = PAGE if limit is None else min(PAGE, limit - start + 1)
        url = f"{API}?start={start}&limit={page_size}&convert=USD&sort=market_cap"
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
        if len(page) < page_size:
            break
        start += page_size
    coins.sort(key=lambda c: c["rank"])
    return {"updated": stamp or datetime.now(timezone.utc).isoformat(), "source": "coinmarketcap",
            "credits": credits, "count": len(coins), "coins": coins}


def top_slice(data):
    coins = [c for c in data["coins"] if c["rank"] <= TOP_N]
    return {**data, "count": len(coins), "coins": coins}


def live_copy(name, min_coins):
    """The file the published site is serving right now, or None."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repo:
        return None
    owner, project = repo.split("/", 1)
    url = f"https://{owner.lower()}.github.io/{project}/data/{name}"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            data = json.load(r)
    except Exception as e:
        print(f"No live {name} ({e})")
        return None
    if data.get("source") != "coinmarketcap" or len(data.get("coins", [])) < min_coins:
        print(f"Live {name} is not usable CoinMarketCap data")
        return None
    return data


def write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    print(f"Wrote {os.path.basename(path)}: {data['count']} coins, updated {data['updated']}")


def keep_live(name, path, min_coins):
    """Carry the live file into this deploy so it is not lost or left stale."""
    data = live_copy(name, min_coins)
    if data:
        write(path, data)
    elif os.path.exists(path):
        print(f"Keeping the repo's {name}")
    else:
        print(f"No {name} yet; the site will fall back to the other file")


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "top500").lower()
    key = os.environ.get("CMC_API_KEY", "").strip()

    if mode == "reuse":
        keep_live("market.json", OUT_TOP, 100)
        keep_live("market_all.json", OUT_ALL, 600)
        print("Reused live data, no credits used")
        return 0

    if not key:
        print("CMC_API_KEY not set; keeping the files already in place")
        return 0

    if mode == "all":
        try:
            data = fetch_cmc(key)
        except Exception as e:
            print(f"CoinMarketCap request failed: {e}; keeping the files already in place")
            return 0
        if len(data["coins"]) < 600:
            print(f"Only {len(data['coins'])} coins returned; keeping the files already in place")
            return 0
        write(OUT_ALL, data)
        write(OUT_TOP, top_slice(data))   # same data, so the hourly file costs nothing extra
        print(f"Credits used {data['credits']}")
        return 0

    # hourly: the top 500 only, and carry the all-coins file through unchanged
    try:
        data = fetch_cmc(key, TOP_N)
    except Exception as e:
        print(f"CoinMarketCap request failed: {e}; keeping the files already in place")
        keep_live("market_all.json", OUT_ALL, 600)
        return 0
    if len(data["coins"]) < 100:
        print(f"Only {len(data['coins'])} coins returned; keeping the files already in place")
    else:
        write(OUT_TOP, data)
        print(f"Credits used {data['credits']}")
    keep_live("market_all.json", OUT_ALL, 600)
    return 0


if __name__ == "__main__":
    sys.exit(main())
