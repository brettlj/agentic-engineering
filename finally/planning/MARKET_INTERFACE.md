# Market Data Interface Design

Unified Python interface for market data in FinAlly. Two implementations — simulator (default) and Massive API client — behind one abstract interface. All downstream code (SSE streaming, portfolio valuation, trade execution) is source-agnostic.

## Architecture

```
create_market_data_source(cache)    # Factory: picks implementation from env
        │
        ├── SimulatorDataSource     # Default: GBM simulation, no API key needed
        └── MassiveDataSource       # When MASSIVE_API_KEY is set
                │
                ▼
         PriceCache                 # Thread-safe in-memory store
                │
                ├──→ SSE stream     # GET /api/stream/prices (reads every 500ms)
                ├──→ Portfolio      # Valuation at current prices
                └──→ Trade exec     # Fill price for market orders
```

## Core Data Model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PriceUpdate:
    """A single price update for one ticker."""
    ticker: str
    price: float
    previous_price: float
    timestamp: float          # Unix seconds
    change: float             # price - previous_price
    direction: str            # "up", "down", or "flat"
```

This is the **only data structure** that leaves the market data layer. Everything downstream works with `PriceUpdate` objects.

## Abstract Interface

```python
from abc import ABC, abstractmethod

class MarketDataSource(ABC):
    """Abstract interface for market data providers."""

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates for the given tickers."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop producing price updates and clean up."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the active set."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of active tickers."""
```

Both implementations write to a shared `PriceCache`. The interface does **not** return prices directly — it pushes updates into the cache on its own schedule.

## Price Cache

Thread-safe in-memory store. Producers (data sources) write; consumers (SSE, portfolio, trades) read.

```python
import time
from threading import Lock

class PriceCache:
    """Thread-safe cache of latest prices per ticker."""

    def __init__(self):
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()
        self._version: int = 0    # Increments on every update (SSE change detection)

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Update price for a ticker. Returns the PriceUpdate."""
        with self._lock:
            ts = timestamp or time.time()
            previous = self._prices.get(ticker)
            previous_price = previous.price if previous else price

            if price > previous_price:
                direction = "up"
            elif price < previous_price:
                direction = "down"
            else:
                direction = "flat"

            update = PriceUpdate(
                ticker=ticker,
                price=price,
                previous_price=previous_price,
                timestamp=ts,
                change=price - previous_price,
                direction=direction,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        with self._lock:
            return self._prices.get(ticker)

    def get_price(self, ticker: str) -> float | None:
        with self._lock:
            p = self._prices.get(ticker)
            return p.price if p else None

    def get_all(self) -> dict[str, PriceUpdate]:
        with self._lock:
            return dict(self._prices)

    def remove(self, ticker: str) -> None:
        with self._lock:
            self._prices.pop(ticker, None)

    @property
    def version(self) -> int:
        return self._version
```

## Factory Function

```python
import os

def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment."""
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        from .massive_client import MassiveDataSource
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        from .simulator import SimulatorDataSource
        return SimulatorDataSource(price_cache=price_cache)
```

## Simulator Implementation

Default when no `MASSIVE_API_KEY` is set. Uses Geometric Brownian Motion with correlated moves across tickers.

```python
import asyncio

class SimulatorDataSource(MarketDataSource):
    def __init__(self, price_cache: PriceCache, update_interval: float = 0.5):
        self._cache = price_cache
        self._interval = update_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._sim: GBMSimulator | None = None

    async def start(self, tickers: list[str]) -> None:
        self._tickers = list(tickers)
        self._sim = GBMSimulator(tickers=self._tickers)
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            self._sim.add_ticker(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self._tickers = [t for t in self._tickers if t != ticker]
        self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _run_loop(self) -> None:
        while True:
            prices = self._sim.step()  # Returns dict[str, float]
            for ticker, price in prices.items():
                self._cache.update(ticker=ticker, price=price)
            await asyncio.sleep(self._interval)
```

### GBM Simulator Details

- **Model**: `S(t+dt) = S(t) * exp((mu - sigma^2/2) * dt + sigma * sqrt(dt) * Z)`
- **Update interval**: 500ms (dt ~8.5e-8 of a trading year)
- **Correlated moves**: Cholesky decomposition of a sector-based correlation matrix
  - Tech (AAPL, GOOGL, MSFT, AMZN, META, NVDA, NFLX): rho = 0.6
  - Finance (JPM, V): rho = 0.5
  - Cross-sector: rho = 0.3
  - TSLA: rho = 0.3 with everything (independent streak)
- **Random events**: ~0.1% chance per tick of a 2-5% shock (for visual drama)
- **Seed prices**: Realistic starting values (AAPL ~$190, NVDA ~$800, etc.)
- **Per-ticker volatility**: TSLA sigma=0.50, JPM sigma=0.18, etc.
- **Dynamic tickers**: Unknown tickers start at random $50-$300 with default params

## Massive API Implementation

Active when `MASSIVE_API_KEY` is set. Polls the Massive snapshot endpoint on a timer.

```python
import asyncio
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

class MassiveDataSource(MarketDataSource):
    def __init__(self, api_key: str, price_cache: PriceCache, poll_interval: float = 15.0):
        self._client = RESTClient(api_key=api_key)
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._tickers = list(tickers)
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self._tickers:
            self._tickers.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _poll_loop(self) -> None:
        while True:
            await self._poll_once()
            await asyncio.sleep(self._interval)

    async def _poll_once(self) -> None:
        if not self._tickers:
            return
        # Synchronous Massive client runs in thread pool
        snapshots = await asyncio.to_thread(
            self._client.get_snapshot_all,
            market_type=SnapshotMarketType.STOCKS,
            tickers=self._tickers,
        )
        for snap in snapshots:
            self._cache.update(
                ticker=snap.ticker,
                price=snap.last_trade.price,
                timestamp=snap.last_trade.timestamp / 1000,  # ms -> seconds
            )
```

### Massive API Usage

- **Primary endpoint**: `GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,...` — all tickers in **one call**
- **Python client**: `client.get_snapshot_all(market_type=SnapshotMarketType.STOCKS, tickers=[...])`
- **Key fields extracted**: `snap.last_trade.price` (current price), `snap.last_trade.timestamp` (Unix ms)
- **Poll interval**: 15s for free tier (5 req/min limit), 2-5s for paid tiers
- **Thread pool**: Synchronous `massive` client is called via `asyncio.to_thread()` to avoid blocking the event loop
- **Rate limit safety**: One API call per poll covers all tickers; even the free tier supports this comfortably

See `planning/MASSIVE_API.md` for full API endpoint documentation and response schemas.

## SSE Integration

The SSE endpoint reads from `PriceCache` and pushes to connected browser clients.

```python
import json

async def price_stream(price_cache: PriceCache):
    """SSE generator that yields price updates."""
    last_version = -1
    while True:
        if price_cache.version != last_version:
            last_version = price_cache.version
            prices = price_cache.get_all()
            data = {
                ticker: {
                    "ticker": p.ticker,
                    "price": p.price,
                    "previous_price": p.previous_price,
                    "change": p.change,
                    "direction": p.direction,
                    "timestamp": p.timestamp,
                }
                for ticker, p in prices.items()
            }
            yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(0.5)
```

The version counter avoids sending duplicate data when nothing has changed.

## File Structure

```
backend/
  app/
    market/
      __init__.py             # Re-exports: PriceUpdate, PriceCache, MarketDataSource, create_market_data_source
      models.py               # PriceUpdate frozen dataclass
      cache.py                # PriceCache (thread-safe, version counter)
      interface.py            # MarketDataSource ABC
      seed_prices.py          # SEED_PRICES, TICKER_PARAMS, DEFAULT_PARAMS, CORRELATION_GROUPS
      simulator.py            # GBMSimulator + SimulatorDataSource
      massive_client.py       # MassiveDataSource (REST polling)
      factory.py              # create_market_data_source()
      stream.py               # create_stream_router() — FastAPI SSE endpoint
```

## Lifecycle

```python
from app.market import PriceCache, create_market_data_source

# 1. App startup
cache = PriceCache()
source = create_market_data_source(cache)  # Reads MASSIVE_API_KEY
await source.start(["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
                     "NVDA", "META", "JPM", "V", "NFLX"])

# 2. Read prices (any consumer)
update = cache.get("AAPL")          # PriceUpdate | None
price = cache.get_price("AAPL")     # float | None
all_prices = cache.get_all()        # dict[str, PriceUpdate]

# 3. Dynamic watchlist changes
await source.add_ticker("PYPL")
await source.remove_ticker("GOOGL")

# 4. App shutdown
await source.stop()
```

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Strategy pattern (ABC) | Downstream code doesn't know or care about the data source |
| PriceCache as single point of truth | Decouples producers from consumers; no direct coupling |
| `asyncio.to_thread()` for Massive | The `massive` package is synchronous; thread pool keeps event loop free |
| Version counter on cache | SSE endpoint skips redundant pushes when no prices changed |
| Frozen dataclass for PriceUpdate | Immutable; safe to pass between async tasks without copying |
| One snapshot call for all tickers | Maximizes data per API call; essential for free-tier rate limits |
