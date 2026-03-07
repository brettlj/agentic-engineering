# Massive API Reference (formerly Polygon.io)

Reference documentation for the Massive REST API as used in FinAlly. Polygon.io rebranded to Massive; the API structure is unchanged. Legacy `api.polygon.io` URLs redirect to `api.massive.com`.

## Overview

| Item | Value |
|------|-------|
| Base URL | `https://api.massive.com` |
| Python package | `massive` (`uv add massive`) |
| Min Python | 3.9+ |
| Auth | API key via `Authorization: Bearer <API_KEY>` header (client handles this) |
| Env var | `MASSIVE_API_KEY` |
| Timestamps | Unix milliseconds (trades, bars) or nanoseconds (quotes) |

## Rate Limits

| Tier | Limit | Recommended Poll Interval |
|------|-------|---------------------------|
| Free | 5 requests/minute | Every 15 seconds |
| Paid (all tiers) | Unlimited (stay under 100 req/s) | Every 2-5 seconds |

## Python Client Setup

```python
from massive import RESTClient

# Reads MASSIVE_API_KEY from environment automatically
client = RESTClient()

# Or pass explicitly
client = RESTClient(api_key="your_key_here")
```

---

## Endpoints Used in FinAlly

### 1. All Tickers Snapshot (Primary Endpoint)

Gets current prices for **multiple tickers in a single API call**. This is the main endpoint for polling — critical for staying within free-tier rate limits.

**REST**: `GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,MSFT`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tickers` | string | No | Comma-separated list of tickers. Omit for all tickers. |
| `include_otc` | boolean | No | Include OTC securities. Default: false. |

**Python client**:

```python
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

client = RESTClient()

snapshots = client.get_snapshot_all(
    market_type=SnapshotMarketType.STOCKS,
    tickers=["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
)

for snap in snapshots:
    print(f"{snap.ticker}: ${snap.last_trade.price}")
    print(f"  Day change: {snap.todays_change_perc}%")
    print(f"  Day OHLC: O={snap.day.open} H={snap.day.high} L={snap.day.low} C={snap.day.close}")
    print(f"  Volume: {snap.day.volume}")
```

**Response structure** (per ticker in the `tickers` array):

```json
{
  "ticker": "AAPL",
  "day": {
    "o": 129.61,
    "h": 130.15,
    "l": 125.07,
    "c": 125.07,
    "v": 111237700,
    "vw": 127.35
  },
  "prevDay": {
    "o": 128.50,
    "h": 130.00,
    "l": 127.90,
    "c": 129.61,
    "v": 98000000,
    "vw": 129.10
  },
  "lastTrade": {
    "p": 125.07,
    "s": 100,
    "x": 4,
    "t": 1675190399000
  },
  "lastQuote": {
    "P": 125.08,
    "S": 1000,
    "p": 125.06,
    "s": 500,
    "t": 1675190399500
  },
  "min": {
    "o": 125.10,
    "h": 125.15,
    "l": 125.05,
    "c": 125.07,
    "v": 50000
  },
  "todaysChange": -4.54,
  "todaysChangePerc": -3.50,
  "updated": 1675190399000
}
```

**Key fields for FinAlly**:
- `lastTrade.p` → current price (via Python client: `snap.last_trade.price`)
- `prevDay.c` → previous day close (via Python client: `snap.prev_day.close`)
- `todaysChangePerc` → day change % (via Python client: `snap.todays_change_perc`)
- `lastTrade.t` → timestamp in Unix ms (via Python client: `snap.last_trade.timestamp`)

> **Note**: The Python client normalizes the abbreviated JSON field names (e.g., `p` → `price`, `c` → `close`).

---

### 2. Single Ticker Snapshot

Detailed snapshot for one ticker. Same structure as above but for a single symbol.

**REST**: `GET /v2/snapshot/locale/us/markets/stocks/tickers/{stocksTicker}`

**Python client**:

```python
snapshot = client.get_snapshot_ticker(
    market_type=SnapshotMarketType.STOCKS,
    ticker="AAPL",
)

print(f"Price: ${snapshot.last_trade.price}")
print(f"Bid/Ask: ${snapshot.last_quote.bid} / ${snapshot.last_quote.ask}")
print(f"Day range: ${snapshot.day.low} - ${snapshot.day.high}")
print(f"Change: {snapshot.todays_change_perc}%")
```

---

### 3. Previous Close

Previous trading day's OHLCV bar for a ticker. Useful for seed prices or calculating overnight gaps.

**REST**: `GET /v2/aggs/ticker/{stocksTicker}/prev`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `stocksTicker` | string | Yes | Ticker symbol (path param) |
| `adjusted` | boolean | No | Adjust for splits. Default: true. |

**Python client**:

```python
prev = client.get_previous_close_agg(ticker="AAPL")

for agg in prev:
    print(f"Previous close: ${agg.close}")
    print(f"OHLC: O={agg.open} H={agg.high} L={agg.low} C={agg.close}")
    print(f"Volume: {agg.volume}")
```

**Response**:

```json
{
  "ticker": "AAPL",
  "adjusted": true,
  "queryCount": 1,
  "resultsCount": 1,
  "status": "OK",
  "results": [
    {
      "T": "AAPL",
      "o": 150.0,
      "h": 155.0,
      "l": 149.0,
      "c": 154.5,
      "v": 1000000,
      "vw": 152.3,
      "t": 1672531200000,
      "n": 450000
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `o` | Open price |
| `h` | High price |
| `l` | Low price |
| `c` | Close price |
| `v` | Volume (shares) |
| `vw` | Volume-weighted average price |
| `t` | Timestamp (Unix ms) |
| `n` | Number of transactions |

---

### 4. Aggregates (Bars)

Historical OHLCV bars over a date range. Not needed for live polling but useful if historical charts are added later.

**REST**: `GET /v2/aggs/ticker/{stocksTicker}/range/{multiplier}/{timespan}/{from}/{to}`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `stocksTicker` | string | Ticker symbol |
| `multiplier` | integer | Timespan multiplier (e.g., `1` for 1-day bars) |
| `timespan` | string | `second`, `minute`, `hour`, `day`, `week`, `month`, `quarter`, `year` |
| `from` | string | Start date (`YYYY-MM-DD` or Unix ms) |
| `to` | string | End date (`YYYY-MM-DD` or Unix ms) |

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `adjusted` | boolean | true | Adjust for splits |
| `sort` | string | `asc` | `asc` or `desc` |
| `limit` | integer | 5000 | Max results (up to 50,000) |

**Python client**:

```python
aggs = []
for a in client.list_aggs(
    ticker="AAPL",
    multiplier=1,
    timespan="day",
    from_="2024-01-01",
    to="2024-01-31",
    limit=50000,
):
    aggs.append(a)

for a in aggs:
    print(f"Date: {a.timestamp}, O={a.open} H={a.high} L={a.low} C={a.close} V={a.volume}")
```

**Response** (each result):

```json
{
  "o": 130.0,
  "h": 132.5,
  "l": 129.8,
  "c": 131.2,
  "v": 50000000,
  "vw": 131.0,
  "t": 1672531200000,
  "n": 500000
}
```

---

### 5. Last Trade

Most recent trade for a single ticker.

**REST**: `GET /v1/last/stocks/{stocksTicker}`

**Python client**:

```python
trade = client.get_last_trade(ticker="AAPL")
print(f"Last trade: ${trade.price} x {trade.size}")
```

---

### 6. Last Quote (NBBO)

Most recent National Best Bid and Offer for a ticker.

**REST**: `GET /v2/last/nbbo/{stocksTicker}`

**Python client**:

```python
quote = client.get_last_quote(ticker="AAPL")
print(f"Bid: ${quote.bid} x {quote.bid_size}")
print(f"Ask: ${quote.ask} x {quote.ask_size}")
```

**Response**:

```json
{
  "status": "OK",
  "request_id": "b84e24636301f19f88e0dfbf9a45ed5c",
  "results": {
    "P": 127.98,
    "S": 7,
    "T": "AAPL",
    "p": 127.96,
    "s": 1,
    "t": 1617827221349730300,
    "x": 11,
    "X": 19,
    "z": 3
  }
}
```

| Field | Description |
|-------|-------------|
| `P` | Ask price |
| `S` | Ask size (shares) |
| `p` | Bid price |
| `s` | Bid size (shares) |
| `T` | Ticker |
| `t` | SIP timestamp (nanoseconds) |
| `x` | Bid exchange ID |
| `X` | Ask exchange ID |
| `z` | Tape (1=NYSE, 2=ARCA, 3=NASDAQ) |

---

## How FinAlly Uses the API

The Massive poller runs as a background task with a single workflow:

1. Collect all tickers from the active watchlist
2. Call `get_snapshot_all()` with those tickers — **one API call for all tickers**
3. Extract `last_trade.price` and `prev_day.close` from each snapshot
4. Write each price to the shared in-memory `PriceCache`
5. Sleep for the poll interval, then repeat

```python
import asyncio
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

async def poll_massive(api_key: str, get_tickers, price_cache, interval: float = 15.0):
    """Poll Massive API and update the price cache."""
    client = RESTClient(api_key=api_key)

    while True:
        tickers = get_tickers()
        if tickers:
            # Run synchronous client in thread pool
            snapshots = await asyncio.to_thread(
                client.get_snapshot_all,
                market_type=SnapshotMarketType.STOCKS,
                tickers=tickers,
            )
            for snap in snapshots:
                price_cache.update(
                    ticker=snap.ticker,
                    price=snap.last_trade.price,
                    timestamp=snap.last_trade.timestamp / 1000,  # ms -> seconds
                )

        await asyncio.sleep(interval)
```

## Error Handling

| Status | Meaning |
|--------|---------|
| 401 | Invalid API key |
| 403 | Insufficient plan permissions |
| 429 | Rate limit exceeded (free tier: 5 req/min) |
| 5xx | Server error (client retries 3 times by default) |

## Important Notes

- The snapshot endpoint returns data for **all requested tickers in one call** — essential for free-tier rate limits
- During market hours, `lastTrade.p` is the most recent traded price
- During closed hours, `lastTrade.p` reflects the last traded price (may include after-hours)
- The `day` object resets at market open; during pre-market, values may be from the previous session
- The Python `massive` client normalizes abbreviated field names (`p` → `price`, `c` → `close`, etc.)
- `list_aggs()` handles pagination automatically via an iterator
