# Market Data Backend — Complete Implementation Design

Comprehensive implementation guide for the FinAlly market data backend. This document covers every API, module, data structure, and integration point needed to build the market data subsystem from scratch. All code lives under `backend/app/market/`.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [File Structure & Module Map](#2-file-structure--module-map)
3. [Data Model — `models.py`](#3-data-model--modelspy)
4. [Price Cache — `cache.py`](#4-price-cache--cachepy)
5. [Abstract Interface — `interface.py`](#5-abstract-interface--interfacepy)
6. [Seed Prices & Parameters — `seed_prices.py`](#6-seed-prices--parameters--seed_pricespy)
7. [GBM Simulator — `simulator.py`](#7-gbm-simulator--simulatorpy)
8. [Massive API Client — `massive_client.py`](#8-massive-api-client--massive_clientpy)
9. [Factory — `factory.py`](#9-factory--factorypy)
10. [SSE Streaming Endpoint — `stream.py`](#10-sse-streaming-endpoint--streampy)
11. [Package Init — `__init__.py`](#11-package-init--__init__py)
12. [FastAPI Lifecycle Integration](#12-fastapi-lifecycle-integration)
13. [REST API Endpoints for Market Data](#13-rest-api-endpoints-for-market-data)
14. [Watchlist Coordination](#14-watchlist-coordination)
15. [Portfolio & Trade Integration](#15-portfolio--trade-integration)
16. [Error Handling & Edge Cases](#16-error-handling--edge-cases)
17. [Testing Strategy](#17-testing-strategy)
18. [Configuration Reference](#18-configuration-reference)

---

## 1. Architecture Overview

The market data backend follows a **strategy pattern** with a shared cache as the single point of truth. Two interchangeable data sources push prices into a thread-safe cache; all downstream consumers read from it.

```
┌─────────────────────────────────────────────────────────────────┐
│  Market Data Layer (backend/app/market/)                        │
│                                                                 │
│  MarketDataSource (ABC)                                         │
│  ├── SimulatorDataSource  →  GBM simulator (default)            │
│  └── MassiveDataSource    →  Polygon.io REST poller             │
│          │                                                      │
│          ▼                                                      │
│     PriceCache (thread-safe, in-memory)                         │
│          │                                                      │
│          ├──→ GET /api/stream/prices  (SSE live stream)          │
│          ├──→ GET /api/prices         (REST snapshot)            │
│          ├──→ GET /api/prices/{ticker} (single ticker price)     │
│          ├──→ POST /api/portfolio/trade (trade execution)        │
│          └──→ GET /api/portfolio       (portfolio valuation)     │
│                                                                 │
│  Factory: create_market_data_source(cache)                      │
│    → reads MASSIVE_API_KEY env var                              │
│    → returns SimulatorDataSource or MassiveDataSource            │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

- **Source-agnostic downstream code**: SSE streaming, portfolio valuation, and trade execution never know which data source is active.
- **Push model**: Data sources write to the cache on their own schedule. The cache is polled by consumers independently.
- **Thread safety**: `threading.Lock` protects the cache because the Massive client's synchronous `get_snapshot_all()` runs in `asyncio.to_thread()`.
- **Immediate data availability**: Both data sources seed the cache before their background loops begin, so the SSE endpoint has data from the first tick.

---

## 2. File Structure & Module Map

```
backend/
  app/
    market/
      __init__.py             # Public API re-exports
      models.py               # PriceUpdate frozen dataclass
      cache.py                # PriceCache (thread-safe in-memory store)
      interface.py            # MarketDataSource ABC
      seed_prices.py          # SEED_PRICES, TICKER_PARAMS, CORRELATION_GROUPS
      simulator.py            # GBMSimulator + SimulatorDataSource
      massive_client.py       # MassiveDataSource (Polygon.io REST poller)
      factory.py              # create_market_data_source()
      stream.py               # SSE endpoint factory (FastAPI router)
  tests/
    market/
      __init__.py
      test_models.py          # PriceUpdate tests
      test_cache.py           # PriceCache tests
      test_simulator.py       # GBMSimulator tests
      test_simulator_source.py # SimulatorDataSource integration tests
      test_factory.py         # Factory tests
      test_massive.py         # MassiveDataSource tests (mocked API)
```

### Module dependency graph

```
models.py          ← no internal deps
    ↑
cache.py           ← imports models
    ↑
interface.py       ← no internal deps (ABC only)
    ↑
seed_prices.py     ← no internal deps (constants only)
    ↑
simulator.py       ← imports cache, interface, seed_prices, models
massive_client.py  ← imports cache, interface
    ↑
factory.py         ← imports cache, interface (lazy imports simulator/massive)
    ↑
stream.py          ← imports cache
    ↑
__init__.py        ← re-exports public API
```

---

## 3. Data Model — `models.py`

`PriceUpdate` is the **only data structure** that leaves the market data layer. Every downstream consumer works exclusively with this type.

```python
# backend/app/market/models.py

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Immutable snapshot of a single ticker's price at a point in time.

    This is the sole data contract between the market data layer and
    all consumers (SSE streaming, portfolio valuation, trade execution).
    """

    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)  # Unix seconds

    @property
    def change(self) -> float:
        """Absolute price change from previous update."""
        return round(self.price - self.previous_price, 4)

    @property
    def change_percent(self) -> float:
        """Percentage change from previous update."""
        if self.previous_price == 0:
            return 0.0
        return round(
            (self.price - self.previous_price) / self.previous_price * 100, 4
        )

    @property
    def direction(self) -> str:
        """Price direction: 'up', 'down', or 'flat'."""
        if self.price > self.previous_price:
            return "up"
        elif self.price < self.previous_price:
            return "down"
        return "flat"

    def to_dict(self) -> dict:
        """Serialize for JSON / SSE transmission."""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "timestamp": self.timestamp,
            "change": self.change,
            "change_percent": self.change_percent,
            "direction": self.direction,
        }
```

### Design decisions

| Decision | Rationale |
|----------|-----------|
| `frozen=True` | Immutable value objects — safe to share across async tasks without copying |
| `slots=True` | Memory optimization — many instances created per second |
| Computed properties | `change`, `direction`, `change_percent` derived from `price`/`previous_price` — impossible to be inconsistent |
| `to_dict()` | Single serialization point used by SSE endpoint and REST responses |

### Usage examples

```python
from app.market.models import PriceUpdate

# Create directly (rare — normally created by PriceCache)
update = PriceUpdate(
    ticker="AAPL",
    price=191.50,
    previous_price=190.00,
    timestamp=1707580800.5,
)

print(update.direction)       # "up"
print(update.change)          # 1.5
print(update.change_percent)  # 0.7895
print(update.to_dict())       # Full JSON-ready dict
```

---

## 4. Price Cache — `cache.py`

The price cache is the **central data hub**. Data sources write to it; SSE streaming, portfolio valuation, and trade execution read from it. Thread-safe via `threading.Lock`.

```python
# backend/app/market/cache.py

from __future__ import annotations

import time
from threading import Lock

from .models import PriceUpdate


class PriceCache:
    """Thread-safe in-memory cache of the latest price for each ticker.

    Writers: SimulatorDataSource or MassiveDataSource (one at a time).
    Readers: SSE streaming endpoint, portfolio valuation, trade execution.

    The version counter enables efficient SSE change detection — the SSE
    loop only serializes and sends data when the version has changed.
    """

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()
        self._version: int = 0

    # --- Write API (called by data sources) ---

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Record a new price for a ticker. Returns the created PriceUpdate.

        Automatically computes direction and change from the previous price.
        First update for a ticker sets previous_price == price (direction='flat').
        """
        with self._lock:
            ts = timestamp or time.time()
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev else price

            update = PriceUpdate(
                ticker=ticker,
                price=round(price, 2),
                previous_price=round(previous_price, 2),
                timestamp=ts,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def remove(self, ticker: str) -> None:
        """Remove a ticker from the cache (e.g., when removed from watchlist)."""
        with self._lock:
            self._prices.pop(ticker, None)

    # --- Read API (called by consumers) ---

    def get(self, ticker: str) -> PriceUpdate | None:
        """Get the latest PriceUpdate for a single ticker, or None."""
        with self._lock:
            return self._prices.get(ticker)

    def get_price(self, ticker: str) -> float | None:
        """Convenience: get just the price float, or None."""
        update = self.get(ticker)
        return update.price if update else None

    def get_all(self) -> dict[str, PriceUpdate]:
        """Snapshot of all current prices. Returns a shallow copy."""
        with self._lock:
            return dict(self._prices)

    @property
    def version(self) -> int:
        """Monotonically increasing counter. Bumped on every update().
        Used by SSE streaming for change detection."""
        return self._version

    def __len__(self) -> int:
        with self._lock:
            return len(self._prices)

    def __contains__(self, ticker: str) -> bool:
        with self._lock:
            return ticker in self._prices
```

### Why `threading.Lock` instead of `asyncio.Lock`?

The Massive client's synchronous `get_snapshot_all()` runs in `asyncio.to_thread()`, which operates in a **real OS thread**. An `asyncio.Lock` would not protect against concurrent access from that thread. `threading.Lock` works correctly from both sync threads and the async event loop.

### Version counter for SSE efficiency

```python
# In the SSE loop — skip sending when nothing changed
last_version = -1
while True:
    if price_cache.version != last_version:
        last_version = price_cache.version
        yield format_sse(price_cache.get_all())
    await asyncio.sleep(0.5)
```

This is important for the Massive data source, which only updates every 15 seconds. Without the version counter, the SSE endpoint would redundantly serialize and send identical data 30 times between polls.

### Usage examples

```python
from app.market.cache import PriceCache

cache = PriceCache()

# First update — direction is "flat" (no previous price)
update = cache.update("AAPL", 190.50)
assert update.direction == "flat"
assert update.previous_price == 190.50

# Second update — direction computed automatically
update = cache.update("AAPL", 191.00)
assert update.direction == "up"
assert update.change == 0.50

# Read APIs
price = cache.get_price("AAPL")        # 191.0
full = cache.get("AAPL")               # PriceUpdate object
all_prices = cache.get_all()           # {"AAPL": PriceUpdate(...)}

# Remove
cache.remove("AAPL")
assert cache.get("AAPL") is None
```

---

## 5. Abstract Interface — `interface.py`

The strategy pattern interface that both data sources implement.

```python
# backend/app/market/interface.py

from __future__ import annotations

from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """Contract for market data providers.

    Implementations push price updates into a shared PriceCache on their
    own schedule. Downstream code never calls the data source directly
    for prices — it reads from the cache.

    Lifecycle:
        source = create_market_data_source(cache)
        await source.start(["AAPL", "GOOGL", ...])
        # ... app runs ...
        await source.add_ticker("TSLA")
        await source.remove_ticker("GOOGL")
        # ... app shutting down ...
        await source.stop()
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates for the given tickers.

        Starts a background task that periodically writes to the PriceCache.
        Seeds the cache with initial prices before the loop begins.
        Must be called exactly once.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task and release resources.

        Safe to call multiple times. After stop(), the source will not
        write to the cache again.
        """

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set. No-op if already present.

        The next update cycle will include this ticker.
        """

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the active set. No-op if not present.

        Also removes the ticker from the PriceCache.
        """

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of actively tracked tickers."""
```

### Why push-to-cache instead of returning prices?

This **decouples timing**. The simulator ticks at 500ms, Massive polls at 15s, but SSE always reads from the cache at its own 500ms cadence. No consumer needs to know which data source is active or what its update interval is.

---

## 6. Seed Prices & Parameters — `seed_prices.py`

Constants only — no logic, no imports beyond stdlib. Shared by the simulator (initial prices + GBM parameters) and potentially by the Massive client (fallback prices).

```python
# backend/app/market/seed_prices.py

"""Seed prices and per-ticker parameters for the market simulator."""

# Realistic starting prices for the default watchlist
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 185.00,
    "TSLA": 250.00,
    "NVDA": 800.00,
    "META": 500.00,
    "JPM": 195.00,
    "V": 280.00,
    "NFLX": 600.00,
}

# Per-ticker GBM parameters
# sigma: annualized volatility (higher = more price movement)
# mu: annualized drift / expected return
TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL":  {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT":  {"sigma": 0.20, "mu": 0.05},
    "AMZN":  {"sigma": 0.28, "mu": 0.05},
    "TSLA":  {"sigma": 0.50, "mu": 0.03},   # High volatility
    "NVDA":  {"sigma": 0.40, "mu": 0.08},   # High volatility, strong drift
    "META":  {"sigma": 0.30, "mu": 0.05},
    "JPM":   {"sigma": 0.18, "mu": 0.04},   # Low volatility (bank)
    "V":     {"sigma": 0.17, "mu": 0.04},   # Low volatility (payments)
    "NFLX":  {"sigma": 0.35, "mu": 0.05},
}

# Default for dynamically added tickers not in the list above
DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}

# Correlation groups for the simulator's Cholesky decomposition
CORRELATION_GROUPS: dict[str, set[str]] = {
    "tech": {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

# Correlation coefficients
INTRA_TECH_CORR = 0.6       # Tech stocks move together
INTRA_FINANCE_CORR = 0.5    # Finance stocks move together
CROSS_GROUP_CORR = 0.3      # Between sectors
TSLA_CORR = 0.3             # TSLA does its own thing
```

---

## 7. GBM Simulator — `simulator.py`

This file contains two classes:
- **`GBMSimulator`**: Pure math engine — stateful, holds current prices, advances them one step at a time using Geometric Brownian Motion with Cholesky-correlated random draws.
- **`SimulatorDataSource`**: The `MarketDataSource` implementation wrapping `GBMSimulator` in an async loop.

### 7.1 GBMSimulator — The Math Engine

**GBM Formula:**
```
S(t+dt) = S(t) * exp((mu - sigma²/2) * dt + sigma * sqrt(dt) * Z)
```

Where `dt = 0.5 / (252 * 6.5 * 3600) ≈ 8.5e-8` for 500ms ticks across a trading year.

```python
# backend/app/market/simulator.py

from __future__ import annotations

import asyncio
import logging
import math
import random

import numpy as np

from .cache import PriceCache
from .interface import MarketDataSource
from .seed_prices import (
    CORRELATION_GROUPS,
    CROSS_GROUP_CORR,
    DEFAULT_PARAMS,
    INTRA_FINANCE_CORR,
    INTRA_TECH_CORR,
    SEED_PRICES,
    TICKER_PARAMS,
    TSLA_CORR,
)

logger = logging.getLogger(__name__)


class GBMSimulator:
    """Geometric Brownian Motion simulator for correlated stock prices.

    Produces realistic price paths with:
    - Per-ticker drift (mu) and volatility (sigma)
    - Sector-based correlations via Cholesky decomposition
    - Random shock events for visual drama (~0.1% chance per tick per ticker)
    """

    # 500ms expressed as a fraction of a trading year
    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5,896,800
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR   # ~8.48e-8

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.001,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability
        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None

        for ticker in tickers:
            self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def step(self) -> dict[str, float]:
        """Advance all tickers by one time step. Returns {ticker: new_price}.

        This is the hot path — called every 500ms.
        """
        n = len(self._tickers)
        if n == 0:
            return {}

        # Generate n independent standard normal draws
        z_independent = np.random.standard_normal(n)

        # Apply Cholesky to get correlated draws
        if self._cholesky is not None:
            z_correlated = self._cholesky @ z_independent
        else:
            z_correlated = z_independent

        result: dict[str, float] = {}
        for i, ticker in enumerate(self._tickers):
            params = self._params[ticker]
            mu = params["mu"]
            sigma = params["sigma"]

            # GBM: S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
            drift = (mu - 0.5 * sigma ** 2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z_correlated[i]
            self._prices[ticker] *= math.exp(drift + diffusion)

            # Random shock event: ~0.1% chance per tick per ticker
            if random.random() < self._event_prob:
                shock_magnitude = random.uniform(0.02, 0.05)
                shock_sign = random.choice([-1, 1])
                self._prices[ticker] *= 1 + shock_magnitude * shock_sign
                logger.debug(
                    "Random event on %s: %.1f%% %s",
                    ticker,
                    shock_magnitude * 100,
                    "up" if shock_sign > 0 else "down",
                )

            result[ticker] = round(self._prices[ticker], 2)

        return result

    def add_ticker(self, ticker: str) -> None:
        """Add a ticker. Rebuilds correlation matrix."""
        if ticker in self._prices:
            return
        self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker. Rebuilds correlation matrix."""
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        del self._params[ticker]
        self._rebuild_cholesky()

    def get_tickers(self) -> list[str]:
        """Return the current list of tracked tickers."""
        return list(self._tickers)

    def get_price(self, ticker: str) -> float | None:
        """Current price for a ticker, or None if not tracked."""
        return self._prices.get(ticker)

    def _add_ticker_internal(self, ticker: str) -> None:
        """Add a ticker without rebuilding Cholesky (for batch init)."""
        if ticker in self._prices:
            return
        self._tickers.append(ticker)
        self._prices[ticker] = SEED_PRICES.get(ticker, random.uniform(50.0, 300.0))
        self._params[ticker] = TICKER_PARAMS.get(ticker, dict(DEFAULT_PARAMS))

    def _rebuild_cholesky(self) -> None:
        """Rebuild Cholesky decomposition of the correlation matrix."""
        n = len(self._tickers)
        if n <= 1:
            self._cholesky = None
            return

        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                rho = self._pairwise_correlation(self._tickers[i], self._tickers[j])
                corr[i, j] = rho
                corr[j, i] = rho

        self._cholesky = np.linalg.cholesky(corr)

    @staticmethod
    def _pairwise_correlation(t1: str, t2: str) -> float:
        """Determine correlation based on sector grouping."""
        tech = CORRELATION_GROUPS["tech"]
        finance = CORRELATION_GROUPS["finance"]

        if t1 == "TSLA" or t2 == "TSLA":
            return TSLA_CORR
        if t1 in tech and t2 in tech:
            return INTRA_TECH_CORR
        if t1 in finance and t2 in finance:
            return INTRA_FINANCE_CORR
        return CROSS_GROUP_CORR
```

### 7.2 SimulatorDataSource — Async Wrapper

```python
# Also in backend/app/market/simulator.py (same file, below GBMSimulator)

class SimulatorDataSource(MarketDataSource):
    """MarketDataSource backed by the GBM simulator.

    Runs a background asyncio task that calls GBMSimulator.step() every
    update_interval seconds and writes results to the PriceCache.
    """

    def __init__(
        self,
        price_cache: PriceCache,
        update_interval: float = 0.5,
        event_probability: float = 0.001,
    ) -> None:
        self._cache = price_cache
        self._interval = update_interval
        self._event_prob = event_probability
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._sim = GBMSimulator(
            tickers=tickers,
            event_probability=self._event_prob,
        )
        # Seed the cache with initial prices so SSE has data immediately
        for ticker in tickers:
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")
        logger.info("Simulator started with %d tickers", len(tickers))

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Simulator stopped")

    async def add_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.add_ticker(ticker)
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
            logger.info("Simulator: added ticker %s", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)
        logger.info("Simulator: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return self._sim.get_tickers() if self._sim else []

    async def _run_loop(self) -> None:
        """Core loop: step the simulation, write to cache, sleep."""
        while True:
            try:
                if self._sim:
                    prices = self._sim.step()
                    for ticker, price in prices.items():
                        self._cache.update(ticker=ticker, price=price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
```

### Simulator behavior notes

- **Prices never go negative**: GBM uses `exp()` which is always positive
- **Sub-cent moves per tick**: The tiny `dt ≈ 8.5e-8` produces realistic small moves that accumulate over time
- **TSLA with `sigma=0.50`**: Produces roughly the right intraday range for a high-volatility stock
- **Random events**: ~0.1% per tick per ticker = one event every ~500s per ticker. With 10 tickers, expect an event roughly every 50 seconds
- **Cholesky rebuild**: O(n²) but n < 50 tickers, so negligible

---

## 8. Massive API Client — `massive_client.py`

Polls the Massive (formerly Polygon.io) REST API snapshot endpoint. The synchronous client runs in `asyncio.to_thread()` to avoid blocking the event loop.

### Massive API reference (endpoints used)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v2/snapshot/locale/us/markets/stocks/tickers` | GET | Batch snapshot — all watched tickers in one call |
| `/v2/aggs/ticker/{ticker}/prev` | GET | Previous close (seed prices) |

### Rate limits

| Tier | Limit | Poll interval |
|------|-------|---------------|
| Free | 5 req/min | 15 seconds |
| Paid | Unlimited | 2-5 seconds |

### Implementation

```python
# backend/app/market/massive_client.py

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


class MassiveDataSource(MarketDataSource):
    """MarketDataSource backed by the Massive (Polygon.io) REST API.

    Polls the snapshot endpoint for all watched tickers in a single API call,
    then writes results to the PriceCache.
    """

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._client: Any = None

    async def start(self, tickers: list[str]) -> None:
        from massive import RESTClient

        self._client = RESTClient(api_key=self._api_key)
        self._tickers = list(tickers)

        # Immediate first poll so the cache has data right away
        await self._poll_once()

        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")
        logger.info(
            "Massive poller started: %d tickers, %.1fs interval",
            len(tickers),
            self._interval,
        )

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None
        logger.info("Massive poller stopped")

    async def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            logger.info("Massive: added ticker %s (will appear on next poll)", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)
        logger.info("Massive: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _poll_loop(self) -> None:
        """Poll on interval. First poll already happened in start()."""
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        """Execute one poll cycle: fetch snapshots, update cache."""
        if not self._tickers or not self._client:
            return

        try:
            snapshots = await asyncio.to_thread(self._fetch_snapshots)
            processed = 0
            for snap in snapshots:
                try:
                    price = snap.last_trade.price
                    # Massive timestamps are Unix milliseconds → convert to seconds
                    timestamp = snap.last_trade.timestamp / 1000.0
                    self._cache.update(
                        ticker=snap.ticker,
                        price=price,
                        timestamp=timestamp,
                    )
                    processed += 1
                except (AttributeError, TypeError) as e:
                    logger.warning(
                        "Skipping snapshot for %s: %s",
                        getattr(snap, "ticker", "???"),
                        e,
                    )
            logger.debug(
                "Massive poll: updated %d/%d tickers", processed, len(self._tickers)
            )
        except Exception as e:
            logger.error("Massive poll failed: %s", e)

    def _fetch_snapshots(self) -> list:
        """Synchronous call to Massive REST API. Runs in a thread."""
        from massive.rest.models import SnapshotMarketType

        return self._client.get_snapshot_all(
            market_type=SnapshotMarketType.STOCKS,
            tickers=self._tickers,
        )
```

### Massive API usage examples

```python
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

client = RESTClient(api_key="your_key")

# --- fetch_prices: Batch snapshot (primary endpoint) ---
snapshots = client.get_snapshot_all(
    market_type=SnapshotMarketType.STOCKS,
    tickers=["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
)
for snap in snapshots:
    print(f"{snap.ticker}: ${snap.last_trade.price}")
    print(f"  Day change: {snap.day.change_percent}%")
    print(f"  OHLC: O={snap.day.open} H={snap.day.high} L={snap.day.low} C={snap.day.close}")
    print(f"  Volume: {snap.day.volume}")

# --- Single ticker snapshot ---
snapshot = client.get_snapshot_ticker(
    market_type=SnapshotMarketType.STOCKS,
    ticker="AAPL",
)
print(f"Price: ${snapshot.last_trade.price}")
print(f"Bid/Ask: ${snapshot.last_quote.bid_price} / ${snapshot.last_quote.ask_price}")

# --- Previous close ---
prev = client.get_previous_close_agg(ticker="AAPL")
for agg in prev:
    print(f"Previous close: ${agg.close}")

# --- Historical bars ---
aggs = list(client.list_aggs(
    ticker="AAPL",
    multiplier=1,
    timespan="day",
    from_="2024-01-01",
    to="2024-01-31",
    limit=50000,
))
```

### Snapshot response structure (per ticker)

```json
{
  "ticker": "AAPL",
  "day": {
    "open": 129.61,
    "high": 130.15,
    "low": 125.07,
    "close": 125.07,
    "volume": 111237700,
    "volume_weighted_average_price": 127.35,
    "previous_close": 129.61,
    "change": -4.54,
    "change_percent": -3.50
  },
  "last_trade": {
    "price": 125.07,
    "size": 100,
    "exchange": "XNYS",
    "timestamp": 1675190399000
  },
  "last_quote": {
    "bid_price": 125.06,
    "ask_price": 125.08,
    "bid_size": 500,
    "ask_size": 1000,
    "spread": 0.02,
    "timestamp": 1675190399500
  }
}
```

### Error handling philosophy

| Error | Behavior |
|-------|----------|
| **401 Unauthorized** | Logged as error. Poller keeps running (user might fix `.env`). |
| **429 Rate Limited** | Logged. Next poll retries after `poll_interval` seconds. |
| **Network timeout** | Logged. Retries automatically on next cycle. |
| **Malformed snapshot** | Individual ticker skipped. Other tickers still processed. |
| **All tickers fail** | Cache retains last-known prices. SSE streams stale data (better than nothing). |

---

## 9. Factory — `factory.py`

Selects the data source at startup based on environment variables.

```python
# backend/app/market/factory.py

from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment.

    - MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
    - Otherwise → SimulatorDataSource (GBM simulation, no dependencies)

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        from .massive_client import MassiveDataSource

        logger.info("Market data source: Massive API (real data)")
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        from .simulator import SimulatorDataSource

        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache)
```

### Usage

```python
from app.market.cache import PriceCache
from app.market.factory import create_market_data_source

cache = PriceCache()
source = create_market_data_source(cache)  # Reads MASSIVE_API_KEY
await source.start(["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
                     "NVDA", "META", "JPM", "V", "NFLX"])
```

---

## 10. SSE Streaming Endpoint — `stream.py`

The SSE endpoint holds open a long-lived HTTP connection and pushes price updates to the client as `text/event-stream`.

```python
# backend/app/market/stream.py

from __future__ import annotations

import asyncio
import json
import logging

from collections.abc import AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .cache import PriceCache

logger = logging.getLogger(__name__)


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Create the SSE streaming router with a reference to the price cache.

    Factory pattern lets us inject PriceCache without globals.
    """
    router = APIRouter(prefix="/api/stream", tags=["streaming"])

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        """SSE endpoint for live price updates.

        Streams all tracked ticker prices every ~500ms when data changes.
        Client connects with EventSource:

            const es = new EventSource('/api/stream/prices');
            es.onmessage = (e) => { const prices = JSON.parse(e.data); };
        """
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    return router


async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
) -> AsyncGenerator[str, None]:
    """Async generator yielding SSE-formatted price events.

    Uses version-based change detection to skip redundant sends.
    Stops when the client disconnects.
    """
    # Tell browser to retry after 1 second on disconnect
    yield "retry: 1000\n\n"

    last_version = -1
    client_ip = request.client.host if request.client else "unknown"
    logger.info("SSE client connected: %s", client_ip)

    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected: %s", client_ip)
                break

            current_version = price_cache.version
            if current_version != last_version:
                last_version = current_version
                prices = price_cache.get_all()

                if prices:
                    data = {
                        ticker: update.to_dict()
                        for ticker, update in prices.items()
                    }
                    yield f"data: {json.dumps(data)}\n\n"

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled for: %s", client_ip)
```

### SSE wire format

Each event the client receives:

```
retry: 1000

data: {"AAPL":{"ticker":"AAPL","price":190.50,"previous_price":190.42,"timestamp":1707580800.5,"change":0.08,"change_percent":0.042,"direction":"up"},"GOOGL":{"ticker":"GOOGL","price":175.12,"previous_price":175.05,"timestamp":1707580800.5,"change":0.07,"change_percent":0.04,"direction":"up"}}

```

### Client-side consumption

```javascript
const eventSource = new EventSource('/api/stream/prices');

eventSource.onmessage = (event) => {
    const prices = JSON.parse(event.data);
    // prices = { "AAPL": { ticker, price, previous_price, change, direction, ... }, ... }
    Object.values(prices).forEach(update => {
        updateTickerDisplay(update.ticker, update.price, update.direction);
    });
};

eventSource.onerror = () => {
    // EventSource auto-reconnects using the retry interval (1000ms)
    console.warn('SSE connection lost, reconnecting...');
};
```

---

## 11. Package Init — `__init__.py`

Re-exports the public API so downstream code imports from `app.market` without reaching into submodules.

```python
# backend/app/market/__init__.py

"""Market data subsystem — unified interface for price simulation and real data."""

from .cache import PriceCache
from .factory import create_market_data_source
from .interface import MarketDataSource
from .models import PriceUpdate

__all__ = [
    "PriceCache",
    "PriceUpdate",
    "MarketDataSource",
    "create_market_data_source",
]
```

### Downstream import pattern

```python
from app.market import PriceCache, create_market_data_source, PriceUpdate
```

---

## 12. FastAPI Lifecycle Integration

The market data system starts and stops with the FastAPI application using the `lifespan` context manager.

```python
# backend/app/main.py (relevant sections)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.market import PriceCache, MarketDataSource, create_market_data_source
from app.market.stream import create_stream_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of background services."""

    # --- STARTUP ---

    # 1. Create the shared price cache
    price_cache = PriceCache()
    app.state.price_cache = price_cache

    # 2. Create and start the market data source
    source = create_market_data_source(price_cache)
    app.state.market_source = source

    # 3. Load initial tickers from the database watchlist
    initial_tickers = await load_watchlist_tickers()  # reads from SQLite
    await source.start(initial_tickers)

    # 4. Register the SSE streaming router
    stream_router = create_stream_router(price_cache)
    app.include_router(stream_router)

    yield  # App is running — handle requests

    # --- SHUTDOWN ---
    await source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)


# --- Dependency injection for route handlers ---

def get_price_cache() -> PriceCache:
    """Inject the shared PriceCache into route handlers."""
    return app.state.price_cache


def get_market_source() -> MarketDataSource:
    """Inject the active MarketDataSource into route handlers."""
    return app.state.market_source


async def load_watchlist_tickers(user_id: str = "default") -> list[str]:
    """Load the watchlist from SQLite. Returns ticker symbols.

    Falls back to default tickers if the database is empty or missing.
    """
    default_tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
                       "NVDA", "META", "JPM", "V", "NFLX"]
    try:
        # Query the watchlist table
        # db = get_database()
        # rows = await db.fetch_all(
        #     "SELECT ticker FROM watchlist WHERE user_id = ?", (user_id,)
        # )
        # return [row["ticker"] for row in rows] if rows else default_tickers
        return default_tickers  # Placeholder until DB layer is built
    except Exception:
        return default_tickers
```

---

## 13. REST API Endpoints for Market Data

In addition to the SSE stream, the backend exposes REST endpoints for on-demand price queries.

### `fetch_prices` — Get all current prices

```python
# backend/app/routes/market.py

from fastapi import APIRouter, Depends
from app.market import PriceCache
from app.main import get_price_cache

router = APIRouter(prefix="/api", tags=["market-data"])


@router.get("/prices")
async def fetch_prices(
    price_cache: PriceCache = Depends(get_price_cache),
) -> dict:
    """Return current prices for all tracked tickers.

    Response:
    {
        "prices": {
            "AAPL": {
                "ticker": "AAPL",
                "price": 190.50,
                "previous_price": 190.42,
                "timestamp": 1707580800.5,
                "change": 0.08,
                "change_percent": 0.042,
                "direction": "up"
            },
            ...
        },
        "count": 10
    }
    """
    all_prices = price_cache.get_all()
    return {
        "prices": {ticker: update.to_dict() for ticker, update in all_prices.items()},
        "count": len(all_prices),
    }
```

### `fetch_price` — Get single ticker price

```python
@router.get("/prices/{ticker}")
async def fetch_price(
    ticker: str,
    price_cache: PriceCache = Depends(get_price_cache),
) -> dict:
    """Return the current price for a single ticker.

    Response:
    {
        "ticker": "AAPL",
        "price": 190.50,
        "previous_price": 190.42,
        "timestamp": 1707580800.5,
        "change": 0.08,
        "change_percent": 0.042,
        "direction": "up"
    }

    Returns 404 if the ticker is not currently tracked.
    """
    ticker = ticker.upper().strip()
    update = price_cache.get(ticker)
    if update is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"No price data available for {ticker}. "
                   f"Add it to the watchlist first.",
        )
    return update.to_dict()
```

### `GET /api/watchlist` — Watchlist with live prices

```python
@router.get("/watchlist")
async def get_watchlist(
    price_cache: PriceCache = Depends(get_price_cache),
) -> dict:
    """Return watchlist tickers enriched with latest prices.

    Response:
    {
        "tickers": [
            {
                "ticker": "AAPL",
                "price": 190.50,
                "previous_price": 190.42,
                "change": 0.08,
                "change_percent": 0.042,
                "direction": "up",
                "timestamp": 1707580800.5
            },
            ...
        ]
    }
    """
    # In practice, query the watchlist table and join with cache:
    # watchlist_tickers = await db.get_watchlist(user_id="default")
    # For now, return all cached prices as the watchlist
    all_prices = price_cache.get_all()
    return {
        "tickers": [update.to_dict() for update in all_prices.values()],
    }
```

### `POST /api/watchlist` — Add ticker to watchlist

```python
from pydantic import BaseModel


class WatchlistAddRequest(BaseModel):
    ticker: str


@router.post("/watchlist", status_code=201)
async def add_to_watchlist(
    payload: WatchlistAddRequest,
    price_cache: PriceCache = Depends(get_price_cache),
    source: MarketDataSource = Depends(get_market_source),
) -> dict:
    """Add a ticker to the watchlist.

    1. Insert into watchlist table (SQLite)
    2. Tell the data source to start tracking it
    3. Return the ticker with its current price (if available)

    Response:
    {
        "status": "added",
        "ticker": "PYPL",
        "price": null  // or price if already known
    }
    """
    ticker = payload.ticker.upper().strip()

    # Insert into database (idempotent — UNIQUE constraint)
    # await db.add_watchlist_entry(user_id="default", ticker=ticker)

    # Tell data source to start tracking
    await source.add_ticker(ticker)

    # Return current price if available
    update = price_cache.get(ticker)
    return {
        "status": "added",
        "ticker": ticker,
        "price": update.to_dict() if update else None,
    }
```

### `DELETE /api/watchlist/{ticker}` — Remove ticker from watchlist

```python
from app.main import get_market_source


@router.delete("/watchlist/{ticker}")
async def remove_from_watchlist(
    ticker: str,
    source: MarketDataSource = Depends(get_market_source),
) -> dict:
    """Remove a ticker from the watchlist.

    Does NOT remove from data source if the user holds a position
    (needed for portfolio valuation).

    Response: {"status": "removed", "ticker": "PYPL"}
    """
    ticker = ticker.upper().strip()

    # Remove from watchlist table
    # await db.delete_watchlist_entry(user_id="default", ticker=ticker)

    # Only stop tracking if no open position
    # position = await db.get_position(user_id="default", ticker=ticker)
    # if position is None or position.quantity == 0:
    await source.remove_ticker(ticker)

    return {"status": "removed", "ticker": ticker}
```

### `GET /api/stream/prices` — SSE stream (covered in Section 10)

Already implemented via `create_stream_router()` — see Section 10.

### `GET /api/health` — Health check

```python
@router.get("/health")
async def health_check(
    price_cache: PriceCache = Depends(get_price_cache),
) -> dict:
    """Health check endpoint for Docker/deployment.

    Response:
    {
        "status": "ok",
        "market_data": true,
        "tickers_tracked": 10,
        "cache_version": 42
    }
    """
    return {
        "status": "ok",
        "market_data": len(price_cache) > 0,
        "tickers_tracked": len(price_cache),
        "cache_version": price_cache.version,
    }
```

---

## 14. Watchlist Coordination

When the watchlist changes (via REST API or LLM chat action), the market data source must be notified.

### Flow: Adding a ticker

```
User (or LLM) → POST /api/watchlist {"ticker": "PYPL"}
  → Insert into watchlist table (SQLite, UNIQUE constraint)
  → await source.add_ticker("PYPL")
      Simulator: adds to GBMSimulator, rebuilds Cholesky, seeds cache
      Massive: appends to ticker list, appears on next poll cycle
  → Return success with current price (if available)
  → SSE stream automatically picks up the new ticker on next tick
```

### Flow: Removing a ticker

```
User (or LLM) → DELETE /api/watchlist/PYPL
  → Delete from watchlist table (SQLite)
  → Check if user has open position in PYPL
      If yes: keep tracking (needed for portfolio valuation)
      If no: await source.remove_ticker("PYPL")
          Simulator: removes from GBMSimulator, rebuilds Cholesky
          Massive: removes from ticker list
          Both: removes from PriceCache
  → Return success
  → SSE stream stops including PYPL on next tick
```

### Flow: LLM-initiated watchlist change

```python
# In the chat handler, after parsing LLM structured output:

for wl_change in llm_response.watchlist_changes:
    if wl_change["action"] == "add":
        await source.add_ticker(wl_change["ticker"])
        # await db.add_watchlist_entry("default", wl_change["ticker"])
    elif wl_change["action"] == "remove":
        await source.remove_ticker(wl_change["ticker"])
        # await db.delete_watchlist_entry("default", wl_change["ticker"])
```

---

## 15. Portfolio & Trade Integration

The market data layer integrates with portfolio management through the PriceCache.

### Trade execution — `POST /api/portfolio/trade`

```python
from pydantic import BaseModel
from fastapi import HTTPException


class TradeRequest(BaseModel):
    ticker: str
    quantity: float  # Fractional shares supported
    side: str        # "buy" or "sell"


@router.post("/portfolio/trade")
async def execute_trade(
    trade: TradeRequest,
    price_cache: PriceCache = Depends(get_price_cache),
) -> dict:
    """Execute a market order at the current price.

    Reads the current price from PriceCache. No order book, no limit orders,
    no fees, instant fill.

    Response:
    {
        "status": "filled",
        "ticker": "AAPL",
        "side": "buy",
        "quantity": 10,
        "price": 190.50,
        "total": 1905.00
    }
    """
    ticker = trade.ticker.upper().strip()
    current_price = price_cache.get_price(ticker)

    if current_price is None:
        raise HTTPException(
            status_code=404,
            detail=f"No price available for {ticker}. Cannot execute trade.",
        )

    total = current_price * trade.quantity

    if trade.side == "buy":
        # Check cash balance
        # user = await db.get_user("default")
        # if user.cash_balance < total:
        #     raise HTTPException(400, "Insufficient cash")
        # await db.update_cash(user_id, user.cash_balance - total)
        # await db.upsert_position(user_id, ticker, trade.quantity, current_price)
        pass
    elif trade.side == "sell":
        # Check position
        # position = await db.get_position("default", ticker)
        # if not position or position.quantity < trade.quantity:
        #     raise HTTPException(400, "Insufficient shares")
        # await db.update_cash(user_id, user.cash_balance + total)
        # await db.reduce_position(user_id, ticker, trade.quantity)
        pass
    else:
        raise HTTPException(400, f"Invalid side: {trade.side}. Use 'buy' or 'sell'.")

    # Record the trade
    # await db.insert_trade(user_id, ticker, trade.side, trade.quantity, current_price)

    # Snapshot portfolio value immediately after trade
    # await record_portfolio_snapshot(user_id, price_cache)

    return {
        "status": "filled",
        "ticker": ticker,
        "side": trade.side,
        "quantity": trade.quantity,
        "price": current_price,
        "total": round(total, 2),
    }
```

### Portfolio valuation — `GET /api/portfolio`

```python
@router.get("/portfolio")
async def get_portfolio(
    price_cache: PriceCache = Depends(get_price_cache),
) -> dict:
    """Return portfolio with live valuations from PriceCache.

    Response:
    {
        "cash_balance": 8095.00,
        "positions": [
            {
                "ticker": "AAPL",
                "quantity": 10,
                "avg_cost": 190.50,
                "current_price": 192.00,
                "market_value": 1920.00,
                "unrealized_pnl": 15.00,
                "unrealized_pnl_percent": 0.79
            }
        ],
        "total_value": 10015.00,
        "total_pnl": 15.00,
        "total_pnl_percent": 0.15
    }
    """
    # user = await db.get_user("default")
    # positions = await db.get_positions("default")
    cash_balance = 10000.0  # Placeholder
    positions = []          # Placeholder

    total_market_value = 0.0
    total_cost_basis = 0.0
    enriched_positions = []

    for pos in positions:
        current_price = price_cache.get_price(pos["ticker"]) or pos["avg_cost"]
        market_value = current_price * pos["quantity"]
        cost_basis = pos["avg_cost"] * pos["quantity"]
        unrealized_pnl = market_value - cost_basis

        enriched_positions.append({
            "ticker": pos["ticker"],
            "quantity": pos["quantity"],
            "avg_cost": pos["avg_cost"],
            "current_price": current_price,
            "market_value": round(market_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_percent": round(
                (unrealized_pnl / cost_basis * 100) if cost_basis else 0, 2
            ),
        })

        total_market_value += market_value
        total_cost_basis += cost_basis

    total_value = cash_balance + total_market_value
    total_pnl = total_value - 10000.0  # Initial balance

    return {
        "cash_balance": cash_balance,
        "positions": enriched_positions,
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_percent": round(total_pnl / 10000.0 * 100, 2),
    }
```

### Portfolio snapshots — background task

```python
async def portfolio_snapshot_task(price_cache: PriceCache, interval: float = 30.0):
    """Record portfolio value every 30 seconds for the P&L chart.

    Also called immediately after each trade execution.
    """
    while True:
        try:
            await record_portfolio_snapshot("default", price_cache)
        except Exception as e:
            logger.error("Portfolio snapshot failed: %s", e)
        await asyncio.sleep(interval)


async def record_portfolio_snapshot(user_id: str, price_cache: PriceCache):
    """Calculate and store current portfolio total value."""
    # user = await db.get_user(user_id)
    # positions = await db.get_positions(user_id)
    # total = user.cash_balance
    # for pos in positions:
    #     price = price_cache.get_price(pos.ticker) or pos.avg_cost
    #     total += price * pos.quantity
    # await db.insert_portfolio_snapshot(user_id, total)
    pass
```

---

## 16. Error Handling & Edge Cases

### Price not available

When `PriceCache.get()` returns `None`, it means the ticker hasn't received any price data yet. This can happen:
- Immediately after adding a ticker (before the next poll/simulation tick)
- If the Massive API doesn't recognize the ticker symbol

```python
price = price_cache.get_price("INVALID_TICKER")
if price is None:
    # Return 404 for trade execution
    # Use avg_cost as fallback for portfolio valuation
    # Skip in SSE output (it will appear once data arrives)
    pass
```

### SSE client disconnect

The SSE generator checks `request.is_disconnected()` on every loop iteration. When the client disconnects:
- The generator exits cleanly
- No cleanup needed — the PriceCache and data source are unaffected

### Simulator exception in step()

The simulator loop catches all exceptions per-step:

```python
try:
    prices = self._sim.step()
    for ticker, price in prices.items():
        self._cache.update(ticker=ticker, price=price)
except Exception:
    logger.exception("Simulator step failed")
# Loop continues — one bad tick doesn't kill the feed
```

### Massive API failures

The poller logs errors and continues. The cache retains last-known prices. SSE continues streaming stale data, which is better than no data. The frontend's connection status indicator should remain green (the SSE connection is fine — it's the upstream data that's stale).

### Race condition: add_ticker during poll

For the Massive client, `add_ticker()` appends to the ticker list. The next `_poll_once()` call will include it. There's no lock on the ticker list because:
- Only one writer (the event loop thread via `add_ticker`/`remove_ticker`)
- The poller reads a snapshot (`list(self._tickers)`) before each poll
- Worst case: a ticker is missed on one poll cycle and caught on the next

---

## 17. Testing Strategy

### 17.1 Unit Tests — `test_models.py`

```python
import time
from app.market.models import PriceUpdate


class TestPriceUpdate:

    def test_direction_up(self):
        u = PriceUpdate(ticker="AAPL", price=191.0, previous_price=190.0)
        assert u.direction == "up"

    def test_direction_down(self):
        u = PriceUpdate(ticker="AAPL", price=189.0, previous_price=190.0)
        assert u.direction == "down"

    def test_direction_flat(self):
        u = PriceUpdate(ticker="AAPL", price=190.0, previous_price=190.0)
        assert u.direction == "flat"

    def test_change(self):
        u = PriceUpdate(ticker="AAPL", price=191.5, previous_price=190.0)
        assert u.change == 1.5

    def test_change_percent(self):
        u = PriceUpdate(ticker="AAPL", price=200.0, previous_price=100.0)
        assert u.change_percent == 100.0

    def test_change_percent_zero_previous(self):
        u = PriceUpdate(ticker="AAPL", price=100.0, previous_price=0.0)
        assert u.change_percent == 0.0

    def test_to_dict(self):
        u = PriceUpdate(ticker="AAPL", price=191.0, previous_price=190.0, timestamp=1000.0)
        d = u.to_dict()
        assert d["ticker"] == "AAPL"
        assert d["price"] == 191.0
        assert d["direction"] == "up"
        assert "change_percent" in d

    def test_frozen(self):
        u = PriceUpdate(ticker="AAPL", price=190.0, previous_price=190.0)
        import pytest
        with pytest.raises(AttributeError):
            u.price = 200.0  # type: ignore

    def test_default_timestamp(self):
        before = time.time()
        u = PriceUpdate(ticker="AAPL", price=190.0, previous_price=190.0)
        after = time.time()
        assert before <= u.timestamp <= after
```

### 17.2 Unit Tests — `test_cache.py`

```python
from app.market.cache import PriceCache


class TestPriceCache:

    def test_update_and_get(self):
        cache = PriceCache()
        update = cache.update("AAPL", 190.50)
        assert cache.get("AAPL") == update
        assert update.price == 190.50

    def test_first_update_is_flat(self):
        cache = PriceCache()
        update = cache.update("AAPL", 190.50)
        assert update.direction == "flat"
        assert update.previous_price == 190.50

    def test_direction_tracking(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        up = cache.update("AAPL", 191.00)
        assert up.direction == "up"
        down = cache.update("AAPL", 189.00)
        assert down.direction == "down"

    def test_version_increments(self):
        cache = PriceCache()
        assert cache.version == 0
        cache.update("AAPL", 190.00)
        assert cache.version == 1
        cache.update("GOOGL", 175.00)
        assert cache.version == 2

    def test_get_all(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("GOOGL", 175.00)
        all_prices = cache.get_all()
        assert set(all_prices.keys()) == {"AAPL", "GOOGL"}

    def test_get_price(self):
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        assert cache.get_price("AAPL") == 190.50
        assert cache.get_price("NOPE") is None

    def test_remove(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.remove("AAPL")
        assert cache.get("AAPL") is None

    def test_remove_nonexistent(self):
        cache = PriceCache()
        cache.remove("NOPE")  # Should not raise

    def test_len(self):
        cache = PriceCache()
        assert len(cache) == 0
        cache.update("AAPL", 190.00)
        assert len(cache) == 1

    def test_contains(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        assert "AAPL" in cache
        assert "NOPE" not in cache

    def test_prices_rounded(self):
        cache = PriceCache()
        update = cache.update("AAPL", 190.5678)
        assert update.price == 190.57
```

### 17.3 Unit Tests — `test_simulator.py`

```python
from app.market.simulator import GBMSimulator
from app.market.seed_prices import SEED_PRICES


class TestGBMSimulator:

    def test_step_returns_all_tickers(self):
        sim = GBMSimulator(tickers=["AAPL", "GOOGL"])
        result = sim.step()
        assert set(result.keys()) == {"AAPL", "GOOGL"}

    def test_prices_always_positive(self):
        sim = GBMSimulator(tickers=["AAPL"])
        for _ in range(10_000):
            prices = sim.step()
            assert prices["AAPL"] > 0

    def test_initial_prices_match_seeds(self):
        sim = GBMSimulator(tickers=["AAPL"])
        assert sim.get_price("AAPL") == SEED_PRICES["AAPL"]

    def test_unknown_ticker_random_seed(self):
        sim = GBMSimulator(tickers=["ZZZZ"])
        price = sim.get_price("ZZZZ")
        assert 50.0 <= price <= 300.0

    def test_add_and_remove_ticker(self):
        sim = GBMSimulator(tickers=["AAPL"])
        sim.add_ticker("TSLA")
        assert "TSLA" in sim.step()
        sim.remove_ticker("TSLA")
        assert "TSLA" not in sim.step()

    def test_empty_step(self):
        sim = GBMSimulator(tickers=[])
        assert sim.step() == {}

    def test_cholesky_with_two_tickers(self):
        sim = GBMSimulator(tickers=["AAPL", "GOOGL"])
        assert sim._cholesky is not None
        assert sim._cholesky.shape == (2, 2)

    def test_cholesky_none_with_one_ticker(self):
        sim = GBMSimulator(tickers=["AAPL"])
        assert sim._cholesky is None
```

### 17.4 Integration Tests — `test_simulator_source.py`

```python
import asyncio
import pytest
from app.market.cache import PriceCache
from app.market.simulator import SimulatorDataSource


class TestSimulatorDataSource:

    @pytest.mark.asyncio
    async def test_start_seeds_cache(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        await source.start(["AAPL", "GOOGL"])
        assert cache.get("AAPL") is not None
        assert cache.get("GOOGL") is not None
        await source.stop()

    @pytest.mark.asyncio
    async def test_prices_update_over_time(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL"])
        initial_version = cache.version
        await asyncio.sleep(0.5)
        assert cache.version > initial_version
        await source.stop()

    @pytest.mark.asyncio
    async def test_add_ticker_runtime(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        await source.start(["AAPL"])
        await source.add_ticker("TSLA")
        assert cache.get("TSLA") is not None
        await source.stop()

    @pytest.mark.asyncio
    async def test_remove_ticker_runtime(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        await source.start(["AAPL", "GOOGL"])
        await source.remove_ticker("GOOGL")
        assert cache.get("GOOGL") is None
        await source.stop()

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        await source.start(["AAPL"])
        await source.stop()
        await source.stop()  # Should not raise
```

### 17.5 Unit Tests — `test_factory.py`

```python
import os
import pytest
from unittest.mock import patch
from app.market.cache import PriceCache
from app.market.factory import create_market_data_source
from app.market.simulator import SimulatorDataSource


class TestFactory:

    def test_default_returns_simulator(self):
        cache = PriceCache()
        with patch.dict(os.environ, {}, clear=True):
            source = create_market_data_source(cache)
            assert isinstance(source, SimulatorDataSource)

    def test_empty_key_returns_simulator(self):
        cache = PriceCache()
        with patch.dict(os.environ, {"MASSIVE_API_KEY": ""}):
            source = create_market_data_source(cache)
            assert isinstance(source, SimulatorDataSource)

    def test_whitespace_key_returns_simulator(self):
        cache = PriceCache()
        with patch.dict(os.environ, {"MASSIVE_API_KEY": "  "}):
            source = create_market_data_source(cache)
            assert isinstance(source, SimulatorDataSource)

    def test_valid_key_returns_massive(self):
        cache = PriceCache()
        with patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key_123"}):
            source = create_market_data_source(cache)
            from app.market.massive_client import MassiveDataSource
            assert isinstance(source, MassiveDataSource)
```

### 17.6 Unit Tests — `test_massive.py` (mocked API)

```python
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.market.cache import PriceCache
from app.market.massive_client import MassiveDataSource


def _make_snapshot(ticker: str, price: float, timestamp_ms: int):
    """Create a mock snapshot object matching the Massive API shape."""
    snap = MagicMock()
    snap.ticker = ticker
    snap.last_trade.price = price
    snap.last_trade.timestamp = timestamp_ms
    return snap


class TestMassiveDataSource:

    @pytest.mark.asyncio
    async def test_poll_updates_cache(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)

        mock_client = MagicMock()
        mock_client.get_snapshot_all.return_value = [
            _make_snapshot("AAPL", 190.50, 1707580800000),
            _make_snapshot("GOOGL", 175.25, 1707580800000),
        ]
        source._client = mock_client
        source._tickers = ["AAPL", "GOOGL"]

        await source._poll_once()

        assert cache.get_price("AAPL") == 190.50
        assert cache.get_price("GOOGL") == 175.25

    @pytest.mark.asyncio
    async def test_poll_converts_timestamp(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)

        mock_client = MagicMock()
        mock_client.get_snapshot_all.return_value = [
            _make_snapshot("AAPL", 190.50, 1707580800000),
        ]
        source._client = mock_client
        source._tickers = ["AAPL"]

        await source._poll_once()

        update = cache.get("AAPL")
        assert update.timestamp == 1707580800.0  # ms → seconds

    @pytest.mark.asyncio
    async def test_poll_handles_api_error(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)

        mock_client = MagicMock()
        mock_client.get_snapshot_all.side_effect = Exception("Network error")
        source._client = mock_client
        source._tickers = ["AAPL"]

        await source._poll_once()  # Should not raise
        assert cache.get("AAPL") is None

    @pytest.mark.asyncio
    async def test_poll_skips_malformed_snapshot(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)

        good = _make_snapshot("AAPL", 190.50, 1707580800000)
        bad = MagicMock()
        bad.ticker = "BAD"
        bad.last_trade.price = None  # Will cause TypeError

        mock_client = MagicMock()
        mock_client.get_snapshot_all.return_value = [good, bad]
        source._client = mock_client
        source._tickers = ["AAPL", "BAD"]

        await source._poll_once()

        assert cache.get_price("AAPL") == 190.50
        # BAD ticker was skipped, no crash

    @pytest.mark.asyncio
    async def test_add_ticker(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        source._tickers = ["AAPL"]
        await source.add_ticker("TSLA")
        assert "TSLA" in source.get_tickers()

    @pytest.mark.asyncio
    async def test_remove_ticker(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        cache.update("AAPL", 190.0)
        source._tickers = ["AAPL"]
        await source.remove_ticker("AAPL")
        assert "AAPL" not in source.get_tickers()
        assert cache.get("AAPL") is None
```

### Running the test suite

```bash
cd backend
uv run pytest tests/market/ -v --tb=short
```

---

## 18. Configuration Reference

| Setting | Source | Default | Description |
|---------|--------|---------|-------------|
| `MASSIVE_API_KEY` | Environment variable | `""` (empty) | Massive/Polygon.io API key. If set, uses real market data. |
| Simulator update interval | `SimulatorDataSource.__init__` | `0.5` seconds | How often the GBM simulator ticks |
| Simulator dt | `GBMSimulator.DEFAULT_DT` | `~8.48e-8` | GBM time step as fraction of a trading year |
| Simulator event probability | `GBMSimulator.__init__` | `0.001` | Chance of a random shock per tick per ticker |
| Massive poll interval | `MassiveDataSource.__init__` | `15.0` seconds | How often to poll the Massive API (free tier safe) |
| SSE push interval | `_generate_events` | `0.5` seconds | How often the SSE endpoint checks for changes |
| SSE retry directive | `_generate_events` | `1000` ms | Browser reconnection delay on SSE disconnect |
| Portfolio snapshot interval | `portfolio_snapshot_task` | `30.0` seconds | How often portfolio value is recorded for P&L chart |

### Dependency summary

| Package | Required for | Notes |
|---------|-------------|-------|
| `fastapi` | All endpoints | Core web framework |
| `uvicorn` | Server | ASGI server |
| `numpy` | Simulator | Cholesky decomposition, random number generation |
| `massive` | Real market data only | Optional — only imported when `MASSIVE_API_KEY` is set |
