# -------------------------------------------------------------------------------------------------
#  NautilusTrader Indicator Template
#
#  Subclass Indicator for custom technical analysis calculations.
#  Indicators auto-update when registered via register_indicator_for_bars() etc.
# -------------------------------------------------------------------------------------------------

from nautilus_trader.indicators import Indicator
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import PriceType


class MyIndicator(Indicator):
    """
    TODO: Describe indicator purpose and calculation.

    Parameters
    ----------
    period : int
        The lookback period for the calculation.
    price_type : PriceType, default PriceType.LAST
        The price type to extract from ticks.
    """

    def __init__(self, period: int, price_type: PriceType = PriceType.LAST):
        super().__init__(params=[period])
        self.period = period
        self.price_type = price_type

        # TODO: Initialize stateful values
        self.value = 0.0
        self._count = 0
        self._buffer: list[float] = []

    def handle_quote_tick(self, tick: QuoteTick):
        """Extract price from quote tick and update."""
        self.update_raw(tick.extract_price(self.price_type).as_double())

    def handle_trade_tick(self, tick: TradeTick):
        """Extract price from trade tick and update."""
        self.update_raw(tick.price.as_double())

    def handle_bar(self, bar: Bar):
        """Extract close price from bar and update."""
        self.update_raw(bar.close.as_double())

    def update_raw(self, value: float):
        """
        Core calculation logic. Called by all handle_* methods.

        Parameters
        ----------
        value : float
            The raw input value.
        """
        if not self.has_inputs:
            self._set_has_inputs(True)

        # TODO: Implement your calculation
        self._buffer.append(value)
        if len(self._buffer) > self.period:
            self._buffer.pop(0)

        self._count += 1

        # Example: simple moving average
        if len(self._buffer) == self.period:
            self.value = sum(self._buffer) / self.period

        # Set initialized when enough data collected
        if not self.initialized and self._count >= self.period:
            self._set_initialized(True)

    def _reset(self):
        """Reset all stateful values to initial state."""
        self.value = 0.0
        self._count = 0
        self._buffer.clear()
