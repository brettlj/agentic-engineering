import os
from unittest.mock import patch

from app.market.cache import PriceCache
from app.market.factory import create_market_data_source
from app.market.simulator import SimulatorDataSource


class TestFactory:

    def test_default_returns_simulator(self):
        cache = PriceCache()
        env = {k: v for k, v in os.environ.items() if k != "MASSIVE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            source = create_market_data_source(cache)
            assert isinstance(source, SimulatorDataSource)

    def test_empty_key_returns_simulator(self):
        cache = PriceCache()
        with patch.dict(os.environ, {"MASSIVE_API_KEY": ""}):
            source = create_market_data_source(cache)
            assert isinstance(source, SimulatorDataSource)

    def test_whitespace_key_returns_simulator(self):
        cache = PriceCache()
        with patch.dict(os.environ, {"MASSIVE_API_KEY": "   "}):
            source = create_market_data_source(cache)
            assert isinstance(source, SimulatorDataSource)

    def test_whitespace_only_key_returns_simulator(self):
        cache = PriceCache()
        with patch.dict(os.environ, {"MASSIVE_API_KEY": "\t\n"}):
            source = create_market_data_source(cache)
            assert isinstance(source, SimulatorDataSource)

    def test_valid_key_returns_massive(self):
        cache = PriceCache()
        with patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key_123"}):
            source = create_market_data_source(cache)
            from app.market.massive_client import MassiveDataSource
            assert isinstance(source, MassiveDataSource)

    def test_massive_source_has_correct_api_key(self):
        cache = PriceCache()
        with patch.dict(os.environ, {"MASSIVE_API_KEY": "my_secret_key"}):
            source = create_market_data_source(cache)
            from app.market.massive_client import MassiveDataSource
            assert isinstance(source, MassiveDataSource)
            assert source._api_key == "my_secret_key"

    def test_massive_source_has_correct_cache(self):
        cache = PriceCache()
        with patch.dict(os.environ, {"MASSIVE_API_KEY": "test_key"}):
            source = create_market_data_source(cache)
            from app.market.massive_client import MassiveDataSource
            assert isinstance(source, MassiveDataSource)
            assert source._cache is cache

    def test_simulator_source_has_correct_cache(self):
        cache = PriceCache()
        env = {k: v for k, v in os.environ.items() if k != "MASSIVE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            source = create_market_data_source(cache)
            assert isinstance(source, SimulatorDataSource)
            assert source._cache is cache

    def test_returns_market_data_source_interface(self):
        from app.market.interface import MarketDataSource
        cache = PriceCache()
        env = {k: v for k, v in os.environ.items() if k != "MASSIVE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            source = create_market_data_source(cache)
            assert isinstance(source, MarketDataSource)
