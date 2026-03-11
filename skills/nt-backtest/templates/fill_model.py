# -------------------------------------------------------------------------------------------------
#  NautilusTrader FillModel Template
#
#  Subclass FillModel to customize how simulated orders are filled in backtests.
#  Controls fill probability, slippage, and order book simulation.
#
#  Built-in models: BestPriceFillModel, OneTickSlippageFillModel, TwoTierFillModel,
#  ThreeTierFillModel, ProbabilisticFillModel, SizeAwareFillModel, etc.
# -------------------------------------------------------------------------------------------------

from nautilus_trader.backtest.models import FillModel
from nautilus_trader.model.book import OrderBook
from nautilus_trader.model.instruments.base import Instrument
from nautilus_trader.model.objects import Price
from nautilus_trader.model.orders.base import Order


class MyFillModel(FillModel):
    """
    TODO: Describe custom fill model behavior.

    Parameters
    ----------
    prob_fill_on_limit : float, default 1.0
        Probability of limit orders filling at limit price (0.0–1.0).
    prob_slippage : float, default 0.0
        Probability of aggressive order execution slipping (0.0–1.0).
    random_seed : int, optional
        Random seed for reproducibility.
    """

    def __init__(
        self,
        prob_fill_on_limit: float = 1.0,
        prob_slippage: float = 0.0,
        random_seed: int | None = None,
    ):
        super().__init__(
            prob_fill_on_limit=prob_fill_on_limit,
            prob_slippage=prob_slippage,
            random_seed=random_seed,
        )
        # TODO: Initialize custom model parameters

    def fill_limit_inside_spread(self) -> bool:
        """
        Whether limit orders at/inside the spread can fill.

        Return True if your model provides liquidity inside bid-ask spread.
        Default False: limit orders only fill when price crosses them.
        """
        return False

    def get_orderbook_for_fill_simulation(
        self,
        instrument: Instrument,
        order: Order,
        best_bid: Price,
        best_ask: Price,
    ) -> OrderBook | None:
        """
        Return a simulated OrderBook for fill simulation.

        This is the primary extension point. Return:
        - OrderBook: custom liquidity levels to define fill prices/sizes
        - None: use default fill logic (prob_fill_on_limit, prob_slippage)

        Parameters
        ----------
        instrument : Instrument
            The instrument being traded.
        order : Order
            The order to simulate fills for.
        best_bid : Price
            Current best bid price.
        best_ask : Price
            Current best ask price.

        Returns
        -------
        OrderBook or None
            Custom simulated order book, or None for default behavior.
        """
        # TODO: Implement custom fill simulation logic
        #
        # Example: create a synthetic order book with custom liquidity:
        #   book = OrderBook(instrument_id=instrument.id, book_type=BookType.L2_MBP)
        #   book.add(BookOrder(price=best_bid, size=1000, side=OrderSide.BUY))
        #   book.add(BookOrder(price=best_ask, size=1000, side=OrderSide.SELL))
        #   return book
        return None  # Use default fill behavior


# Usage in backtest config:
#
# BacktestVenueConfig(
#     name="SIM",
#     oms_type="NETTING",
#     account_type="MARGIN",
#     base_currency="USD",
#     starting_balances=["1_000_000 USD"],
#     fill_model=MyFillModel(prob_fill_on_limit=0.95, prob_slippage=0.1),
# )
#
# LatencyModel (built-in, no subclass needed):
#
# from nautilus_trader.backtest.models import LatencyModel
#
# latency = LatencyModel(
#     base_latency_nanos=1_000_000,     # 1ms base
#     insert_latency_nanos=5_000_000,   # 5ms for new orders
#     update_latency_nanos=2_000_000,   # 2ms for modifications
#     cancel_latency_nanos=1_000_000,   # 1ms for cancellations
# )
