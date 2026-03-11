# -------------------------------------------------------------------------------------------------
#  NautilusTrader Strategy Template
#
#  Subclass Strategy for components that submit orders and manage positions.
#  For data-only components (no trading), use Actor instead.
# -------------------------------------------------------------------------------------------------

from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.events.order import OrderFilled
from nautilus_trader.model.events.position import PositionChanged
from nautilus_trader.model.events.position import PositionClosed
from nautilus_trader.model.events.position import PositionOpened
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.config import StrategyConfig
from nautilus_trader.trading.strategy import Strategy


class MyStrategyConfig(StrategyConfig, frozen=True):
    """Configuration for MyStrategy."""

    instrument_id: str = None  # e.g. "ETHUSDT-PERP.BINANCE"
    bar_type: str = None  # e.g. "ETHUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL"
    # TODO: Add strategy-specific config parameters


class MyStrategy(Strategy):
    """
    TODO: Describe strategy logic.
    """

    def __init__(self, config: MyStrategyConfig):
        super().__init__(config)
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.bar_type = BarType.from_str(config.bar_type)
        # TODO: Initialize indicators and state

    def on_start(self):
        """Called once when the strategy starts."""
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            self.log.error(f"Instrument {self.instrument_id} not found")
            self.stop()
            return

        self.subscribe_bars(self.bar_type)
        # TODO: Subscribe to additional data, register indicators
        # self.register_indicator_for_bars(self.bar_type, self.ema)

    def on_bar(self, bar: Bar):
        """Called on each bar update."""
        # TODO: Implement core trading logic
        #
        # Example order submission:
        #   order = self.order_factory.market(
        #       instrument_id=self.instrument_id,
        #       order_side=OrderSide.BUY,
        #       quantity=self.instrument.make_qty(1.0),
        #   )
        #   self.submit_order(order)
        pass

    def on_quote_tick(self, tick: QuoteTick):
        """Called on each quote tick update."""
        pass

    def on_trade_tick(self, tick: TradeTick):
        """Called on each trade tick update."""
        pass

    def on_order_filled(self, event: OrderFilled):
        """Called when an order is filled."""
        pass

    def on_position_opened(self, event: PositionOpened):
        """Called when a new position is opened."""
        pass

    def on_position_changed(self, event: PositionChanged):
        """Called when a position's quantity or side changes."""
        pass

    def on_position_closed(self, event: PositionClosed):
        """Called when a position is fully closed."""
        pass

    def on_stop(self):
        """Called when the strategy stops. Clean up resources."""
        # TODO: Cancel open orders, optionally close positions
        # self.cancel_all_orders(self.instrument_id)
        # self.close_all_positions(self.instrument_id)
        pass

    def on_reset(self):
        """Called when the strategy is reset. Clear state."""
        # TODO: Reset indicators and state
        pass

    def on_save(self) -> dict[str, bytes]:
        """Return state to persist across restarts."""
        return {}

    def on_load(self, state: dict[str, bytes]) -> None:
        """Restore persisted state."""
        pass
