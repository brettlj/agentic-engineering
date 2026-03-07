import time
import threading

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

    def test_direction_tracking_up(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        up = cache.update("AAPL", 191.00)
        assert up.direction == "up"

    def test_direction_tracking_down(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        down = cache.update("AAPL", 189.00)
        assert down.direction == "down"

    def test_direction_tracking_flat(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        flat = cache.update("AAPL", 190.00)
        assert flat.direction == "flat"

    def test_version_starts_at_zero(self):
        cache = PriceCache()
        assert cache.version == 0

    def test_version_increments_on_update(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        assert cache.version == 1
        cache.update("GOOGL", 175.00)
        assert cache.version == 2

    def test_version_increments_on_same_ticker(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("AAPL", 191.00)
        assert cache.version == 2

    def test_get_all(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("GOOGL", 175.00)
        all_prices = cache.get_all()
        assert set(all_prices.keys()) == {"AAPL", "GOOGL"}

    def test_get_all_is_copy(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        snapshot1 = cache.get_all()
        cache.update("GOOGL", 175.00)
        snapshot2 = cache.get_all()
        assert "GOOGL" not in snapshot1
        assert "GOOGL" in snapshot2

    def test_get_price(self):
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        assert cache.get_price("AAPL") == 190.50

    def test_get_price_missing(self):
        cache = PriceCache()
        assert cache.get_price("NOPE") is None

    def test_get_missing(self):
        cache = PriceCache()
        assert cache.get("NOPE") is None

    def test_remove(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.remove("AAPL")
        assert cache.get("AAPL") is None

    def test_remove_nonexistent_no_raise(self):
        cache = PriceCache()
        cache.remove("NOPE")  # Should not raise

    def test_len_empty(self):
        cache = PriceCache()
        assert len(cache) == 0

    def test_len_after_update(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        assert len(cache) == 1

    def test_len_multiple(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("GOOGL", 175.00)
        assert len(cache) == 2

    def test_len_after_remove(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.remove("AAPL")
        assert len(cache) == 0

    def test_contains_true(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        assert "AAPL" in cache

    def test_contains_false(self):
        cache = PriceCache()
        assert "NOPE" not in cache

    def test_prices_rounded_to_two_decimals(self):
        cache = PriceCache()
        update = cache.update("AAPL", 190.5678)
        assert update.price == 190.57

    def test_prices_rounded_down(self):
        cache = PriceCache()
        update = cache.update("AAPL", 190.5612)
        assert update.price == 190.56

    def test_custom_timestamp(self):
        cache = PriceCache()
        ts = 1707580800.0
        update = cache.update("AAPL", 190.00, timestamp=ts)
        assert update.timestamp == ts

    def test_default_timestamp_used_when_none(self):
        cache = PriceCache()
        before = time.time()
        update = cache.update("AAPL", 190.00)
        after = time.time()
        assert before <= update.timestamp <= after

    def test_thread_safety(self):
        """Concurrent writes should not corrupt the cache."""
        cache = PriceCache()
        errors = []

        def writer(ticker: str, price: float):
            try:
                for i in range(100):
                    cache.update(ticker, price + i)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=("AAPL", 190.0)),
            threading.Thread(target=writer, args=("GOOGL", 175.0)),
            threading.Thread(target=writer, args=("MSFT", 420.0)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread safety errors: {errors}"
        assert len(cache) == 3

    def test_previous_price_tracks_correctly(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        update = cache.update("AAPL", 195.00)
        assert update.previous_price == 190.00
        update2 = cache.update("AAPL", 192.00)
        assert update2.previous_price == 195.00
