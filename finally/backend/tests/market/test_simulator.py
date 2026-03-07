import pytest

from app.market.simulator import GBMSimulator
from app.market.seed_prices import SEED_PRICES


class TestGBMSimulator:

    def test_step_returns_all_tickers(self):
        sim = GBMSimulator(tickers=["AAPL", "GOOGL"])
        result = sim.step()
        assert set(result.keys()) == {"AAPL", "GOOGL"}

    def test_prices_always_positive(self):
        sim = GBMSimulator(tickers=["AAPL"], event_probability=0.0)
        for _ in range(1000):
            prices = sim.step()
            assert prices["AAPL"] > 0

    def test_prices_always_positive_with_high_volatility(self):
        # TSLA has sigma=0.50, test many steps
        sim = GBMSimulator(tickers=["TSLA"], event_probability=0.0)
        for _ in range(1000):
            prices = sim.step()
            assert prices["TSLA"] > 0

    def test_initial_prices_match_seeds(self):
        sim = GBMSimulator(tickers=["AAPL"])
        assert sim.get_price("AAPL") == SEED_PRICES["AAPL"]

    def test_initial_prices_all_seeds(self):
        tickers = list(SEED_PRICES.keys())
        sim = GBMSimulator(tickers=tickers)
        for ticker in tickers:
            assert sim.get_price(ticker) == SEED_PRICES[ticker]

    def test_unknown_ticker_random_seed(self):
        sim = GBMSimulator(tickers=["ZZZZ"])
        price = sim.get_price("ZZZZ")
        assert price is not None
        assert 50.0 <= price <= 300.0

    def test_get_price_missing_ticker(self):
        sim = GBMSimulator(tickers=["AAPL"])
        assert sim.get_price("NOPE") is None

    def test_add_ticker_appears_in_step(self):
        sim = GBMSimulator(tickers=["AAPL"])
        sim.add_ticker("TSLA")
        result = sim.step()
        assert "TSLA" in result

    def test_remove_ticker_disappears_from_step(self):
        sim = GBMSimulator(tickers=["AAPL", "TSLA"])
        sim.remove_ticker("TSLA")
        result = sim.step()
        assert "TSLA" not in result

    def test_add_existing_ticker_is_noop(self):
        sim = GBMSimulator(tickers=["AAPL"])
        original_price = sim.get_price("AAPL")
        sim.add_ticker("AAPL")
        assert sim.get_price("AAPL") == original_price
        assert sim.get_tickers().count("AAPL") == 1

    def test_remove_nonexistent_ticker_is_noop(self):
        sim = GBMSimulator(tickers=["AAPL"])
        sim.remove_ticker("NOPE")  # Should not raise
        assert "AAPL" in sim.step()

    def test_empty_step_returns_empty_dict(self):
        sim = GBMSimulator(tickers=[])
        assert sim.step() == {}

    def test_empty_initial_tickers(self):
        sim = GBMSimulator(tickers=[])
        assert sim.get_tickers() == []

    def test_cholesky_with_two_tickers(self):
        sim = GBMSimulator(tickers=["AAPL", "GOOGL"])
        assert sim._cholesky is not None
        assert sim._cholesky.shape == (2, 2)

    def test_cholesky_none_with_one_ticker(self):
        sim = GBMSimulator(tickers=["AAPL"])
        assert sim._cholesky is None

    def test_cholesky_none_with_zero_tickers(self):
        sim = GBMSimulator(tickers=[])
        assert sim._cholesky is None

    def test_cholesky_rebuilt_after_add(self):
        sim = GBMSimulator(tickers=["AAPL"])
        assert sim._cholesky is None
        sim.add_ticker("GOOGL")
        assert sim._cholesky is not None

    def test_cholesky_rebuilt_after_remove(self):
        sim = GBMSimulator(tickers=["AAPL", "GOOGL"])
        assert sim._cholesky is not None
        sim.remove_ticker("GOOGL")
        assert sim._cholesky is None

    def test_get_tickers(self):
        sim = GBMSimulator(tickers=["AAPL", "GOOGL"])
        assert set(sim.get_tickers()) == {"AAPL", "GOOGL"}

    def test_step_returns_rounded_prices(self):
        sim = GBMSimulator(tickers=["AAPL"])
        result = sim.step()
        price = result["AAPL"]
        # Price should be rounded to 2 decimal places
        assert price == round(price, 2)

    def test_pairwise_correlation_tech(self):
        rho = GBMSimulator._pairwise_correlation("AAPL", "GOOGL")
        assert rho == 0.6

    def test_pairwise_correlation_finance(self):
        rho = GBMSimulator._pairwise_correlation("JPM", "V")
        assert rho == 0.5

    def test_pairwise_correlation_cross_sector(self):
        rho = GBMSimulator._pairwise_correlation("AAPL", "JPM")
        assert rho == 0.3

    def test_pairwise_correlation_tsla(self):
        rho = GBMSimulator._pairwise_correlation("TSLA", "AAPL")
        assert rho == 0.3
        rho2 = GBMSimulator._pairwise_correlation("AAPL", "TSLA")
        assert rho2 == 0.3

    def test_many_tickers_correlation_matrix_valid(self):
        """Cholesky decomposition requires a positive definite matrix."""
        import numpy as np
        tickers = list(SEED_PRICES.keys())
        sim = GBMSimulator(tickers=tickers)
        assert sim._cholesky is not None
        # If Cholesky succeeded, the matrix is positive definite
        assert sim._cholesky.shape == (len(tickers), len(tickers))

    def test_step_accumulates_over_time(self):
        """Prices should drift over many steps (not stay identical)."""
        sim = GBMSimulator(tickers=["AAPL"], event_probability=0.0)
        initial_price = sim.get_price("AAPL")
        for _ in range(100):
            result = sim.step()
        # Price should have changed from initial (very unlikely to be identical)
        assert result["AAPL"] != initial_price
