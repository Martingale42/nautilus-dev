#!/usr/bin/env python3
"""
Example: Shioaji data client tester.

Subscribes to trade ticks and/or quote ticks for Taiwan instruments
using the Shioaji gateway adapter.

Prerequisites:
    1. Shioaji gateway running: ``uvicorn shioaji_server.main:app --port 8000``
    2. Gateway logged in: ``curl -X POST http://localhost:8000/auth/login -d '...'``
"""

from nautilus_trader.adapters.shioaji.config import ShioajiDataClientConfig
from nautilus_trader.adapters.shioaji.constants import SINOPAC
from nautilus_trader.adapters.shioaji.factories import ShioajiLiveDataClientFactory
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.test_kit.strategies.tester_data import DataTester
from nautilus_trader.test_kit.strategies.tester_data import DataTesterConfig


# Configuration
gateway_host = "localhost"
gateway_port = 8000

config_node = TradingNodeConfig(
    trader_id=TraderId("TESTER-001"),
    logging=LoggingConfig(log_level="INFO", use_pyo3=True),
    data_clients={
        SINOPAC: ShioajiDataClientConfig(
            gateway_host=gateway_host,
            gateway_port=gateway_port,
            instrument_provider=InstrumentProviderConfig(load_all=True),
        ),
    },
    timeout_connection=30.0,
    timeout_disconnection=5.0,
    timeout_post_stop=5.0,
)

node = TradingNode(config=config_node)

# Configure instruments to test
instrument_ids = [
    InstrumentId.from_str("2330.SINOPAC"),  # TSMC
    # InstrumentId.from_str("2317.SINOPAC"),  # Hon Hai
]

config_tester = DataTesterConfig(
    instrument_ids=instrument_ids,
    subscribe_trades=True,
    subscribe_quotes=True,
    log_data=True,
)
data_tester = DataTester(config=config_tester)
node.trader.add_actor(data_tester)

node.add_data_client_factory(SINOPAC, ShioajiLiveDataClientFactory)
node.build()

if __name__ == "__main__":
    try:
        node.run()
    finally:
        node.dispose()
