#!/usr/bin/env python3
"""
Example: Shioaji execution client tester.

Tests order submission, modification, and cancellation for Taiwan instruments
using the Shioaji gateway adapter.

Prerequisites:
    1. Shioaji gateway running: ``uvicorn shioaji_server.main:app --port 8000``
    2. Gateway logged in with CA activated for order placement
    3. Use simulation=True in gateway for testing

CAUTION: Set dry_run=True to prevent actual order placement.
"""

from decimal import Decimal

from nautilus_trader.adapters.shioaji.config import ShioajiDataClientConfig
from nautilus_trader.adapters.shioaji.config import ShioajiExecClientConfig
from nautilus_trader.adapters.shioaji.constants import SINOPAC
from nautilus_trader.adapters.shioaji.factories import ShioajiLiveDataClientFactory
from nautilus_trader.adapters.shioaji.factories import ShioajiLiveExecClientFactory
from nautilus_trader.cache.config import CacheConfig
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import LiveExecEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.test_kit.strategies.tester_exec import ExecTester
from nautilus_trader.test_kit.strategies.tester_exec import ExecTesterConfig


# Test configuration
instrument_id = InstrumentId.from_str("2330.SINOPAC")  # TSMC
trade_size = Decimal(1)  # 1 lot (= 1000 shares for common stocks)
offset_ticks = 10  # Offset from market price for limit orders
shioaji_account_id = None  # Set to your account ID, or use SHIOAJI_ACCOUNT_ID env var
gateway_host = "localhost"
gateway_port = 8000
dry_run = True  # Set to False to enable actual order placement (CAUTION!)

config_node = TradingNodeConfig(
    trader_id=TraderId("TESTER-001"),
    logging=LoggingConfig(log_level="INFO", use_pyo3=True),
    exec_engine=LiveExecEngineConfig(
        reconciliation=True,
    ),
    cache=CacheConfig(
        encoding="msgpack",
        timestamps_as_iso8601=True,
        buffer_interval_ms=100,
    ),
    data_clients={
        SINOPAC: ShioajiDataClientConfig(
            gateway_host=gateway_host,
            gateway_port=gateway_port,
            instrument_provider=InstrumentProviderConfig(load_all=True),
        ),
    },
    exec_clients={
        SINOPAC: ShioajiExecClientConfig(
            gateway_host=gateway_host,
            gateway_port=gateway_port,
            account_id=shioaji_account_id,
            instrument_provider=InstrumentProviderConfig(load_all=True),
        ),
    },
    timeout_connection=30.0,
    timeout_reconciliation=20.0,
    timeout_portfolio=10.0,
    timeout_disconnection=5.0,
    timeout_post_stop=5.0,
)

node = TradingNode(config=config_node)

config_tester = ExecTesterConfig(
    instrument_id=instrument_id,
    external_order_claims=[instrument_id],
    order_qty=trade_size,
    tob_offset_ticks=offset_ticks,
    subscribe_quotes=True,
    subscribe_trades=True,
    enable_stop_buys=False,   # Shioaji doesn't support stop orders natively
    enable_stop_sells=False,
    enable_brackets=False,     # Shioaji doesn't support bracket orders
    use_post_only=False,       # Not applicable to Taiwan exchange
    close_positions_time_in_force=TimeInForce.DAY,  # Taiwan uses ROD (rest of day)
    dry_run=dry_run,
    log_data=True,
)
strategy = ExecTester(config=config_tester)
node.trader.add_strategy(strategy)

node.add_data_client_factory(SINOPAC, ShioajiLiveDataClientFactory)
node.add_exec_client_factory(SINOPAC, ShioajiLiveExecClientFactory)
node.build()

if __name__ == "__main__":
    try:
        node.run()
    finally:
        node.dispose()
