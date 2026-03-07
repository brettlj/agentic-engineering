from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.market import PriceCache, MarketDataSource, create_market_data_source
from app.market.stream import create_stream_router

logger = logging.getLogger(__name__)

DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]


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

    # 3. Load initial tickers (from DB watchlist in a full implementation)
    initial_tickers = await _load_watchlist_tickers()
    await source.start(initial_tickers)

    # 4. Register the SSE streaming router
    stream_router = create_stream_router(price_cache)
    app.include_router(stream_router)

    logger.info("FinAlly backend started")

    yield  # App is running — handle requests

    # --- SHUTDOWN ---
    await source.stop()
    logger.info("FinAlly backend stopped")


app = FastAPI(title="FinAlly", lifespan=lifespan)


# --- Dependency injection for route handlers ---

def get_price_cache() -> PriceCache:
    """Inject the shared PriceCache into route handlers."""
    return app.state.price_cache


def get_market_source() -> MarketDataSource:
    """Inject the active MarketDataSource into route handlers."""
    return app.state.market_source


async def _load_watchlist_tickers(user_id: str = "default") -> list[str]:
    """Load the watchlist from SQLite. Returns ticker symbols.

    Falls back to default tickers if the database is empty or missing.
    """
    try:
        # Placeholder until DB layer is built
        return DEFAULT_TICKERS
    except Exception:
        return DEFAULT_TICKERS


# --- Market Data REST Endpoints ---

@app.get("/api/prices")
async def fetch_prices(
    price_cache: PriceCache = Depends(get_price_cache),
) -> dict:
    """Return current prices for all tracked tickers."""
    all_prices = price_cache.get_all()
    return {
        "prices": {ticker: update.to_dict() for ticker, update in all_prices.items()},
        "count": len(all_prices),
    }


@app.get("/api/prices/{ticker}")
async def fetch_price(
    ticker: str,
    price_cache: PriceCache = Depends(get_price_cache),
) -> dict:
    """Return the current price for a single ticker."""
    ticker = ticker.upper().strip()
    update = price_cache.get(ticker)
    if update is None:
        raise HTTPException(
            status_code=404,
            detail=f"No price data available for {ticker}. Add it to the watchlist first.",
        )
    return update.to_dict()


# --- Watchlist REST Endpoints ---

class WatchlistAddRequest(BaseModel):
    ticker: str


@app.get("/api/watchlist")
async def get_watchlist(
    price_cache: PriceCache = Depends(get_price_cache),
) -> dict:
    """Return watchlist tickers enriched with latest prices."""
    all_prices = price_cache.get_all()
    return {
        "tickers": [update.to_dict() for update in all_prices.values()],
    }


@app.post("/api/watchlist", status_code=201)
async def add_to_watchlist(
    payload: WatchlistAddRequest,
    price_cache: PriceCache = Depends(get_price_cache),
    source: MarketDataSource = Depends(get_market_source),
) -> dict:
    """Add a ticker to the watchlist."""
    ticker = payload.ticker.upper().strip()

    # Tell data source to start tracking
    await source.add_ticker(ticker)

    # Return current price if available
    update = price_cache.get(ticker)
    return {
        "status": "added",
        "ticker": ticker,
        "price": update.to_dict() if update else None,
    }


@app.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(
    ticker: str,
    source: MarketDataSource = Depends(get_market_source),
) -> dict:
    """Remove a ticker from the watchlist."""
    ticker = ticker.upper().strip()
    await source.remove_ticker(ticker)
    return {"status": "removed", "ticker": ticker}


# --- Health Check ---

@app.get("/api/health")
async def health_check(
    price_cache: PriceCache = Depends(get_price_cache),
) -> dict:
    """Health check endpoint for Docker/deployment."""
    return {
        "status": "ok",
        "market_data": len(price_cache) > 0,
        "tickers_tracked": len(price_cache),
        "cache_version": price_cache.version,
    }
