import time

import pytest

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

    def test_change_negative(self):
        u = PriceUpdate(ticker="AAPL", price=188.0, previous_price=190.0)
        assert u.change == -2.0

    def test_change_percent(self):
        u = PriceUpdate(ticker="AAPL", price=200.0, previous_price=100.0)
        assert u.change_percent == 100.0

    def test_change_percent_down(self):
        u = PriceUpdate(ticker="AAPL", price=90.0, previous_price=100.0)
        assert u.change_percent == -10.0

    def test_change_percent_zero_previous(self):
        u = PriceUpdate(ticker="AAPL", price=100.0, previous_price=0.0)
        assert u.change_percent == 0.0

    def test_to_dict_keys(self):
        u = PriceUpdate(ticker="AAPL", price=191.0, previous_price=190.0, timestamp=1000.0)
        d = u.to_dict()
        assert d["ticker"] == "AAPL"
        assert d["price"] == 191.0
        assert d["previous_price"] == 190.0
        assert d["timestamp"] == 1000.0
        assert d["direction"] == "up"
        assert "change" in d
        assert "change_percent" in d

    def test_to_dict_direction_up(self):
        u = PriceUpdate(ticker="AAPL", price=191.0, previous_price=190.0, timestamp=1000.0)
        assert u.to_dict()["direction"] == "up"

    def test_to_dict_direction_down(self):
        u = PriceUpdate(ticker="AAPL", price=189.0, previous_price=190.0, timestamp=1000.0)
        assert u.to_dict()["direction"] == "down"

    def test_frozen(self):
        u = PriceUpdate(ticker="AAPL", price=190.0, previous_price=190.0)
        with pytest.raises((AttributeError, TypeError)):
            u.price = 200.0  # type: ignore

    def test_default_timestamp(self):
        before = time.time()
        u = PriceUpdate(ticker="AAPL", price=190.0, previous_price=190.0)
        after = time.time()
        assert before <= u.timestamp <= after

    def test_explicit_timestamp(self):
        u = PriceUpdate(ticker="AAPL", price=190.0, previous_price=190.0, timestamp=12345.0)
        assert u.timestamp == 12345.0

    def test_change_rounded(self):
        u = PriceUpdate(ticker="AAPL", price=190.1234567, previous_price=190.0)
        # change is rounded to 4 decimal places
        assert len(str(u.change).split(".")[-1]) <= 4

    def test_ticker_preserved(self):
        u = PriceUpdate(ticker="MSFT", price=420.0, previous_price=420.0)
        assert u.ticker == "MSFT"
