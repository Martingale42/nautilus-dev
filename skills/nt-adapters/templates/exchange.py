# -------------------------------------------------------------------------------------------------
#  NautilusTrader Exchange Adapter Template
#
#  Use this template for full exchange adapters (data + execution).
#  Components: DataClient + ExecClient + InstrumentProvider + Factories + Config
# -------------------------------------------------------------------------------------------------

from nautilus_trader.common.config import NautilusConfig
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.live.factories import LiveDataClientFactory
from nautilus_trader.live.factories import LiveExecClientFactory
from nautilus_trader.model.identifiers import AccountId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Venue


VENUE = Venue("MYEXCHANGE")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class MyExchangeDataClientConfig(NautilusConfig, frozen=True):
    """Configuration for MyExchange data client."""

    api_key: str = ""
    api_secret: str = ""
    base_url: str = "https://api.myexchange.com"
    ws_url: str = "wss://stream.myexchange.com"
    # TODO: Add exchange-specific config fields


class MyExchangeExecClientConfig(NautilusConfig, frozen=True):
    """Configuration for MyExchange execution client."""

    api_key: str = ""
    api_secret: str = ""
    base_url: str = "https://api.myexchange.com"
    ws_url: str = "wss://stream.myexchange.com"
    # TODO: Add exchange-specific config fields


# ---------------------------------------------------------------------------
# Instrument Provider (shared by data + exec clients)
# ---------------------------------------------------------------------------

from nautilus_trader.common.providers import InstrumentProvider


class MyExchangeInstrumentProvider(InstrumentProvider):
    """Provides instrument definitions from MyExchange."""

    def __init__(self, client, config=None):
        super().__init__(config=config)
        self._client = client

    async def load_all_async(self, filters=None):
        """Load all tradable instruments from exchange."""
        # TODO: Fetch instrument info from exchange API
        # Parse into NT instrument types (CryptoPerpetual, CurrencyPair, etc.)
        # self.add(instrument)
        pass

    async def load_ids_async(self, instrument_ids: list[InstrumentId], filters=None):
        """Load specific instruments by ID."""
        pass


# ---------------------------------------------------------------------------
# Data Client
# ---------------------------------------------------------------------------

class MyExchangeDataClient(LiveMarketDataClient):
    """Market data client for MyExchange."""

    def __init__(self, loop, client, msgbus, cache, clock, instrument_provider, config):
        super().__init__(
            loop=loop,
            client_id=None,
            venue=VENUE,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
            config=config,
        )
        self._client = client

    async def _connect(self):
        await self._instrument_provider.load_all_async()
        # TODO: Connect WebSocket for streaming data

    async def _disconnect(self):
        # TODO: Close WebSocket connections
        pass

    async def _subscribe_trade_ticks(self, instrument_id: InstrumentId):
        # TODO: Subscribe to trade stream via WebSocket
        pass

    async def _subscribe_quote_ticks(self, instrument_id: InstrumentId):
        # TODO: Subscribe to orderbook/quote stream
        pass

    async def _subscribe_order_book_deltas(self, instrument_id: InstrumentId, **kwargs):
        # TODO: Subscribe to order book delta stream
        pass

    async def _unsubscribe_trade_ticks(self, instrument_id: InstrumentId):
        pass

    async def _unsubscribe_quote_ticks(self, instrument_id: InstrumentId):
        pass


# ---------------------------------------------------------------------------
# Execution Client
# ---------------------------------------------------------------------------

class MyExchangeExecClient(LiveExecutionClient):
    """Execution client for MyExchange."""

    def __init__(self, loop, client, msgbus, cache, clock, instrument_provider, config):
        super().__init__(
            loop=loop,
            client_id=None,
            venue=VENUE,
            oms_type=None,  # Set from venue config
            account_type=None,  # Set from venue config
            base_currency=None,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
            config=config,
        )
        self._client = client

    async def _connect(self):
        # TODO: Connect to execution WebSocket, authenticate
        # Fetch account state:
        #   self._handle_account_state(account_state)
        pass

    async def _disconnect(self):
        # TODO: Close execution connections
        pass

    async def _submit_order(self, command):
        """Submit order to exchange."""
        order = command.order
        # TODO: Convert NT order to exchange format
        # TODO: Send via HTTP API
        # TODO: Handle response, generate OrderAccepted/OrderRejected event
        #   self._handle_event(order_accepted_event)
        pass

    async def _cancel_order(self, command):
        """Cancel order on exchange."""
        # TODO: Send cancel request
        # TODO: Handle response, generate OrderCanceled event
        pass

    async def _modify_order(self, command):
        """Modify order on exchange."""
        # TODO: Send modify request (if exchange supports)
        pass

    async def generate_order_status_report(self, instrument_id, client_order_id, venue_order_id):
        """Generate order status report for reconciliation."""
        # TODO: Query exchange for order status
        pass

    async def generate_fill_reports(self, instrument_id, venue_order_id, start=None):
        """Generate fill reports for reconciliation."""
        # TODO: Query exchange for fill history
        pass

    async def generate_position_status_reports(self, instrument_id=None, start=None):
        """Generate position reports for reconciliation."""
        # TODO: Query exchange for positions
        pass


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

class MyExchangeLiveDataClientFactory(LiveDataClientFactory):
    """Factory for creating MyExchange data clients."""

    @staticmethod
    def create(loop, name, config, msgbus, cache, clock):
        client = None  # TODO: Create HTTP/WS client
        provider = MyExchangeInstrumentProvider(client=client)
        return MyExchangeDataClient(
            loop=loop, client=client, msgbus=msgbus, cache=cache,
            clock=clock, instrument_provider=provider, config=config,
        )


class MyExchangeLiveExecClientFactory(LiveExecClientFactory):
    """Factory for creating MyExchange execution clients."""

    @staticmethod
    def create(loop, name, config, msgbus, cache, clock):
        client = None  # TODO: Create HTTP/WS client
        provider = MyExchangeInstrumentProvider(client=client)
        return MyExchangeExecClient(
            loop=loop, client=client, msgbus=msgbus, cache=cache,
            clock=clock, instrument_provider=provider, config=config,
        )
