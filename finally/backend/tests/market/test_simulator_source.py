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
    async def test_start_seeds_all_tickers(self):
        cache = PriceCache()
        tickers = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        source = SimulatorDataSource(price_cache=cache)
        await source.start(tickers)
        for ticker in tickers:
            assert cache.get(ticker) is not None
        await source.stop()

    @pytest.mark.asyncio
    async def test_prices_update_over_time(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.05)
        await source.start(["AAPL"])
        initial_version = cache.version
        await asyncio.sleep(0.3)
        assert cache.version > initial_version
        await source.stop()

    @pytest.mark.asyncio
    async def test_add_ticker_runtime(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        await source.start(["AAPL"])
        await source.add_ticker("TSLA")
        assert cache.get("TSLA") is not None
        assert "TSLA" in source.get_tickers()
        await source.stop()

    @pytest.mark.asyncio
    async def test_remove_ticker_runtime(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        await source.start(["AAPL", "GOOGL"])
        await source.remove_ticker("GOOGL")
        assert cache.get("GOOGL") is None
        assert "GOOGL" not in source.get_tickers()
        await source.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.05)
        await source.start(["AAPL"])
        await source.stop()
        # After stop, no more version increments
        version_after_stop = cache.version
        await asyncio.sleep(0.2)
        assert cache.version == version_after_stop

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        await source.start(["AAPL"])
        await source.stop()
        await source.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_get_tickers_before_start(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        assert source.get_tickers() == []

    @pytest.mark.asyncio
    async def test_get_tickers_after_start(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        await source.start(["AAPL", "GOOGL"])
        assert set(source.get_tickers()) == {"AAPL", "GOOGL"}
        await source.stop()

    @pytest.mark.asyncio
    async def test_add_duplicate_ticker_is_noop(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        await source.start(["AAPL"])
        await source.add_ticker("AAPL")
        assert source.get_tickers().count("AAPL") == 1
        await source.stop()

    @pytest.mark.asyncio
    async def test_remove_nonexistent_ticker_is_noop(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache)
        await source.start(["AAPL"])
        await source.remove_ticker("NOPE")  # Should not raise
        assert cache.get("AAPL") is not None
        await source.stop()

    @pytest.mark.asyncio
    async def test_prices_are_positive(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.01)
        await source.start(["AAPL", "TSLA"])
        await asyncio.sleep(0.2)
        for ticker in ["AAPL", "TSLA"]:
            price = cache.get_price(ticker)
            assert price is not None
            assert price > 0
        await source.stop()
