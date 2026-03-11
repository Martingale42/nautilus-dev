# -------------------------------------------------------------------------------------------------
#  NautilusTrader Actor Template
#
#  Subclass Actor for non-trading components: data processing, signal publishing,
#  monitoring, or any component that does NOT submit orders.
#  For components that trade, use Strategy instead.
# -------------------------------------------------------------------------------------------------

from nautilus_trader.common.actor import Actor
from nautilus_trader.common.config import ActorConfig
from nautilus_trader.core.data import Data
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType


class MyActorConfig(ActorConfig, frozen=True):
    """Configuration for MyActor."""

    bar_type: str = None
    # TODO: Add actor-specific config parameters


class MyActor(Actor):
    """
    TODO: Describe actor purpose (data processing, signal generation, monitoring, etc.)
    """

    def __init__(self, config: MyActorConfig):
        super().__init__(config)
        self.bar_type = BarType.from_str(config.bar_type)
        # TODO: Initialize state

    def on_start(self):
        """Called once when the actor starts."""
        self.subscribe_bars(self.bar_type)
        # TODO: Subscribe to data sources

    def on_bar(self, bar: Bar):
        """Called on each bar update."""
        # TODO: Process data, compute signals
        #
        # Publish signals to other actors/strategies via msgbus:
        #   self.publish_signal(name="my_signal", value=computed_value)
        pass

    def on_data(self, data: Data):
        """Called on generic data updates (CustomData, etc.)."""
        pass

    def on_signal(self, signal: Data):
        """Called when receiving signals from other actors."""
        pass

    def on_stop(self):
        """Called when the actor stops."""
        pass

    def on_reset(self):
        """Called when the actor is reset."""
        pass

    def on_save(self) -> dict[str, bytes]:
        """Return state to persist."""
        return {}

    def on_load(self, state: dict[str, bytes]) -> None:
        """Restore persisted state."""
        pass
