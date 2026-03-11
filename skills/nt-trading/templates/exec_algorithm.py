# -------------------------------------------------------------------------------------------------
#  NautilusTrader ExecAlgorithm Template
#
#  Subclass ExecAlgorithm for custom execution logic: TWAP, VWAP, iceberg,
#  or any order splitting/scheduling algorithm.
# -------------------------------------------------------------------------------------------------

from nautilus_trader.execution.algorithm import ExecAlgorithm
from nautilus_trader.execution.config import ExecAlgorithmConfig
from nautilus_trader.model.orders.base import Order
from nautilus_trader.model.orders.list import OrderList


class MyExecAlgorithmConfig(ExecAlgorithmConfig, frozen=True):
    """Configuration for MyExecAlgorithm."""

    # TODO: Add algorithm-specific config parameters
    pass


class MyExecAlgorithm(ExecAlgorithm):
    """
    TODO: Describe execution algorithm logic (e.g., TWAP, iceberg, etc.)
    """

    def __init__(self, config: MyExecAlgorithmConfig | None = None):
        super().__init__(config)
        # TODO: Initialize algorithm state

    def on_start(self):
        """Called when the algorithm starts."""
        pass

    def on_order(self, order: Order):
        """
        Called when a primary order is received for execution.

        Implement custom execution logic here:
        - Split into child orders
        - Schedule over time intervals
        - React to market conditions
        """
        # TODO: Implement execution logic
        #
        # Simple passthrough example:
        #   self.submit_order(order)
        #
        # TWAP example:
        #   slices = self._split_order(order, num_slices=10)
        #   for slice_order in slices:
        #       self.submit_order(slice_order)
        pass

    def on_order_list(self, order_list: OrderList):
        """Called when an order list is received for execution."""
        # TODO: Handle order list execution
        pass

    def on_order_filled(self, event):
        """Called when a child order is filled."""
        # TODO: Track fill progress, submit next slice if needed
        pass

    def on_order_canceled(self, event):
        """Called when a child order is canceled."""
        pass

    def on_order_rejected(self, event):
        """Called when a child order is rejected."""
        pass

    def on_stop(self):
        """Called when the algorithm stops."""
        # TODO: Cancel any pending child orders
        pass
