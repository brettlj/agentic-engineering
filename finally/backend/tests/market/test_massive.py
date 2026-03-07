import asyncio
from unittest.mock import MagicMock, patch

import pytest

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
    async def test_poll_converts_timestamp_ms_to_seconds(self):
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
    async def test_poll_handles_api_error_gracefully(self):
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
        bad.last_trade.price = None  # Will cause TypeError when multiplied
        bad.last_trade.timestamp = 1707580800000

        # Make bad.last_trade.price cause an AttributeError
        bad_snap = MagicMock()
        bad_snap.ticker = "BAD"
        type(bad_snap).last_trade = property(lambda self: (_ for _ in ()).throw(AttributeError("no last_trade")))

        mock_client = MagicMock()
        mock_client.get_snapshot_all.return_value = [good, bad_snap]
        source._client = mock_client
        source._tickers = ["AAPL", "BAD"]

        await source._poll_once()

        assert cache.get_price("AAPL") == 190.50
        # BAD ticker was skipped, no crash

    @pytest.mark.asyncio
    async def test_poll_skips_snapshot_with_none_price(self):
        """Snapshot where last_trade.price is None should be skipped."""
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)

        good = _make_snapshot("AAPL", 190.50, 1707580800000)
        bad = MagicMock()
        bad.ticker = "BAD"
        bad.last_trade.price = None
        bad.last_trade.timestamp = 1707580800000

        mock_client = MagicMock()
        mock_client.get_snapshot_all.return_value = [good, bad]
        source._client = mock_client
        source._tickers = ["AAPL", "BAD"]

        # Should not raise even with None price causing TypeError
        await source._poll_once()
        assert cache.get_price("AAPL") == 190.50

    @pytest.mark.asyncio
    async def test_poll_skips_empty_tickers(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        source._tickers = []

        mock_client = MagicMock()
        source._client = mock_client

        await source._poll_once()
        mock_client.get_snapshot_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_skips_no_client(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        source._tickers = ["AAPL"]
        source._client = None

        await source._poll_once()  # Should not raise

    @pytest.mark.asyncio
    async def test_add_ticker(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        source._tickers = ["AAPL"]
        await source.add_ticker("TSLA")
        assert "TSLA" in source.get_tickers()

    @pytest.mark.asyncio
    async def test_add_ticker_uppercase(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        source._tickers = []
        await source.add_ticker("aapl")
        assert "AAPL" in source.get_tickers()

    @pytest.mark.asyncio
    async def test_add_ticker_duplicate_is_noop(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        source._tickers = ["AAPL"]
        await source.add_ticker("AAPL")
        assert source.get_tickers().count("AAPL") == 1

    @pytest.mark.asyncio
    async def test_remove_ticker(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        cache.update("AAPL", 190.0)
        source._tickers = ["AAPL"]
        await source.remove_ticker("AAPL")
        assert "AAPL" not in source.get_tickers()
        assert cache.get("AAPL") is None

    @pytest.mark.asyncio
    async def test_remove_ticker_clears_cache(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        cache.update("GOOGL", 175.0)
        source._tickers = ["AAPL", "GOOGL"]
        await source.remove_ticker("GOOGL")
        assert cache.get("GOOGL") is None
        assert "AAPL" in source.get_tickers()

    @pytest.mark.asyncio
    async def test_remove_ticker_lowercase(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        source._tickers = ["AAPL"]
        await source.remove_ticker("aapl")
        assert "AAPL" not in source.get_tickers()

    @pytest.mark.asyncio
    async def test_remove_nonexistent_ticker_is_noop(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        source._tickers = ["AAPL"]
        await source.remove_ticker("NOPE")  # Should not raise
        assert "AAPL" in source.get_tickers()

    def test_get_tickers_returns_copy(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        source._tickers = ["AAPL", "GOOGL"]
        tickers = source.get_tickers()
        tickers.append("HACKED")
        assert "HACKED" not in source._tickers

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache, poll_interval=100.0)

        # Mock start without actual API call
        source._tickers = ["AAPL"]
        source._client = MagicMock()
        source._task = asyncio.create_task(asyncio.sleep(1000), name="test-task")

        await source.stop()
        assert source._task is None
        assert source._client is None

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)
        await source.stop()  # Should not raise even without start
        await source.stop()  # Second call also safe

    @pytest.mark.asyncio
    async def test_multiple_polls_accumulate_updates(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test", price_cache=cache)

        mock_client = MagicMock()
        mock_client.get_snapshot_all.return_value = [
            _make_snapshot("AAPL", 190.50, 1707580800000),
        ]
        source._client = mock_client
        source._tickers = ["AAPL"]

        await source._poll_once()
        v1 = cache.version

        mock_client.get_snapshot_all.return_value = [
            _make_snapshot("AAPL", 192.00, 1707580815000),
        ]
        await source._poll_once()
        v2 = cache.version

        assert v2 > v1
        assert cache.get_price("AAPL") == 192.00
