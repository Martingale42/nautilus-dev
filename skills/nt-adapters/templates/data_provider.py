# -------------------------------------------------------------------------------------------------
#  NautilusTrader Data Provider Adapter Template
#
#  Use this template for data-only adapters (no execution).
#  Components: DataClient + InstrumentProvider + Factory + Config
# -------------------------------------------------------------------------------------------------

from nautilus_trader.common.config import NautilusConfig
from nautilus_trader.live.data_client import LiveDataClient
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.live.factories import LiveDataClientFactory
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Venue


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class MyProviderDataClientConfig(NautilusConfig, frozen=True):
    """
    Configuration for MyProvider data client.

    Parameters
    ----------
    api_key : str
        The API key for authentication.
    base_url : str, optional
        The base URL for the API.
    """

    api_key: str = ""
    base_url: str = "https://api.myprovider.com"
    # TODO: Add provider-specific config fields


# ---------------------------------------------------------------------------
# Instrument Provider
# ---------------------------------------------------------------------------

from nautilus_trader.common.providers import InstrumentProvider


class MyProviderInstrumentProvider(InstrumentProvider):
    """
    Provides instrument definitions from MyProvider.
    """

    def __init__(self, client, config=None):
        super().__init__(config=config)
        self._client = client
        # TODO: Initialize provider state

    async def load_all_async(self, filters=None):
        """Load all available instruments."""
        # TODO: Fetch instruments from API
        # instruments = await self._client.get_instruments()
        # for instrument in instruments:
        #     self.add(instrument)
        pass

    async def load_ids_async(self, instrument_ids: list[InstrumentId], filters=None):
        """Load specific instruments by ID."""
        # TODO: Fetch specific instruments
        pass


# ---------------------------------------------------------------------------
# Data Client
# ---------------------------------------------------------------------------

class MyProviderDataClient(LiveMarketDataClient):
    """
    Market data client for MyProvider.
    """

    def __init__(
        self,
        loop,
        client,
        msgbus,
        cache,
        clock,
        instrument_provider: MyProviderInstrumentProvider,
        config: MyProviderDataClientConfig,
    ):
        super().__init__(
            loop=loop,
            client_id=None,  # Auto-generated
            venue=Venue("MYPROVIDER"),
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
            config=config,
        )
        self._client = client
        # TODO: Initialize data client state

    async def _connect(self):
        """Connect to data source."""
        # TODO: Establish connection (HTTP session, WebSocket, etc.)
        await self._instrument_provider.load_all_async()

    async def _disconnect(self):
        """Disconnect from data source."""
        # TODO: Clean up connections
        pass

    async def _subscribe_trade_ticks(self, instrument_id: InstrumentId):
        """Subscribe to trade tick stream."""
        # TODO: Subscribe via WebSocket or polling
        pass

    async def _subscribe_quote_ticks(self, instrument_id: InstrumentId):
        """Subscribe to quote tick stream."""
        # TODO: Subscribe via WebSocket or polling
        pass

    async def _subscribe_bars(self, bar_type):
        """Subscribe to bar stream."""
        # TODO: Subscribe to bar updates
        pass

    async def _unsubscribe_trade_ticks(self, instrument_id: InstrumentId):
        """Unsubscribe from trade tick stream."""
        pass

    async def _unsubscribe_quote_ticks(self, instrument_id: InstrumentId):
        """Unsubscribe from quote tick stream."""
        pass

    # Forward received data to the engine:
    #   self._handle_data(trade_tick)
    #   self._handle_data(quote_tick)
    #   self._handle_data(bar)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class MyProviderLiveDataClientFactory(LiveDataClientFactory):
    """Factory for creating MyProvider data clients."""

    @staticmethod
    def create(
        loop,
        name: str,
        config: MyProviderDataClientConfig,
        msgbus,
        cache,
        clock,
    ) -> MyProviderDataClient:
        # TODO: Create HTTP/WS client
        client = None  # MyProviderHttpClient(config.api_key, config.base_url)
        provider = MyProviderInstrumentProvider(client=client)

        return MyProviderDataClient(
            loop=loop,
            client=client,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=provider,
            config=config,
        )
