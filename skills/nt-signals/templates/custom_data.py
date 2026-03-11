# -------------------------------------------------------------------------------------------------
#  NautilusTrader Custom Data Template
#
#  Use @customdataclass to define custom data types for signal pipelines,
#  market features, or any structured data flowing through the system.
#
#  The decorator auto-generates:
#  - to_dict() / from_dict()
#  - to_bytes() / from_bytes()
#  - to_arrow() / from_arrow()
#  - ts_event and ts_init fields (auto-prepended to __init__)
# -------------------------------------------------------------------------------------------------

from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model.identifiers import InstrumentId


@customdataclass
class MySignalData:
    """
    TODO: Describe what this data represents.

    Fields
    ------
    instrument_id : InstrumentId
        The instrument this signal relates to.
    signal_value : float
        TODO: Describe the signal value.
    confidence : float
        TODO: Describe the confidence metric.

    Notes
    -----
    - ts_event and ts_init are auto-provided (do NOT define them)
    - InstrumentId fields are auto-serialized to/from strings
    - All fields need type annotations
    """

    instrument_id: InstrumentId
    signal_value: float
    confidence: float
    # TODO: Add additional fields as needed


# Usage:
#
# Creating:
#   signal = MySignalData(
#       ts_event=self.clock.timestamp_ns(),
#       ts_init=self.clock.timestamp_ns(),
#       instrument_id=self.instrument_id,
#       signal_value=1.5,
#       confidence=0.85,
#   )
#
# Publishing (from Actor/Strategy):
#   self.publish_data(data_type=DataType(MySignalData), data=signal)
#
# Subscribing (in on_start):
#   self.subscribe_data(data_type=DataType(MySignalData))
#
# Receiving (in on_data):
#   def on_data(self, data):
#       if isinstance(data, MySignalData):
#           print(data.signal_value)
#
# Serialization (automatic):
#   d = signal.to_dict()
#   restored = MySignalData.from_dict(d)
