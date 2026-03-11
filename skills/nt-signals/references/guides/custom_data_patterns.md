# Custom Data Patterns in NautilusTrader

## Overview

NautilusTrader provides the `@customdataclass` decorator (`nautilus_trader.model.custom`) for
defining user data types that integrate with the full serialization, persistence, and messaging
stack. Custom data classes automatically get dict, bytes (msgpack), and Arrow (Parquet)
serialization, plus registration with the message bus and data catalog.

---

## The `@customdataclass` Decorator

**Location**: `nautilus_trader/model/custom.py`

The decorator wraps a standard Python `@dataclass` and adds NautilusTrader infrastructure.
It can be used with or without parentheses:

```python
from nautilus_trader.core.data import Data
from nautilus_trader.model.custom import customdataclass

@customdataclass
class MySignal(Data):
    instrument_id: InstrumentId = InstrumentId.from_str("ES.GLBX")
    signal_value: float = 0.0
    confidence: float = 0.0
```

### What it generates

The decorator applies `@dataclass` to the class, then conditionally generates the following
(each is skipped if the class already defines its own version):

1. **`__init__`**: Wraps the dataclass init so `ts_event` and `ts_init` are the first two
   positional args (stored as `_ts_event` / `_ts_init`). Field args follow.
2. **`__repr__`**: Appends ISO-8601-formatted `ts_event` and `ts_init` to the dataclass repr.
3. **`ts_event` property**: Returns `self._ts_event` (int, nanosecond Unix timestamp).
4. **`ts_init` property**: Returns `self._ts_init` (int, nanosecond Unix timestamp).
5. **`to_dict() -> dict`**: Serializes all annotated fields plus `type`, `ts_event`, `ts_init`.
   If the class has an `instrument_id` field, its `.value` string form is used.
6. **`from_dict(data) -> cls`**: Class method that reconstructs from a dict. Pops `type` key,
   converts `instrument_id` strings back to `InstrumentId` objects.
7. **`to_bytes() -> bytes`**: msgpack-encodes the dict form via `msgspec.msgpack.encode`.
8. **`from_bytes(data) -> cls`**: Class method to decode from msgpack bytes.
9. **`to_arrow() -> pa.RecordBatch`**: Converts to a single-row Arrow RecordBatch using `_schema`.
10. **`from_arrow(table) -> list[cls]`**: Class method to reconstruct from an Arrow Table.
11. **`_schema`**: Auto-generated `pyarrow.Schema` based on field type annotations.

Finally, the decorator calls:
- `register_serializable_type(cls, cls.to_dict, cls.from_dict)` -- for the serialization registry
- `register_arrow(cls, cls._schema, cls.to_arrow, cls.from_arrow)` -- for Arrow/catalog support

---

## Supported Field Types and Arrow Schema Mappings

The decorator maps Python type annotations to PyArrow types:

| Python Type | Arrow Type |
|---|---|
| `str` | `pa.string()` |
| `int` | `pa.int64()` |
| `float` | `pa.float64()` |
| `bool` | `pa.bool_()` |
| `bytes` | `pa.binary()` |
| `ndarray` | `pa.binary()` |
| `InstrumentId` | `pa.string()` |

The schema always appends three additional columns:
- `type` -- `pa.string()` (the class name)
- `ts_event` -- `pa.int64()`
- `ts_init` -- `pa.int64()`

**Important**: All field types must have a `__name__` attribute that matches one of the keys
above. Using `Optional`, `Union`, or generic types is not supported.

---

## Serialization Formats

### Dict (JSON-compatible)

```python
data = MySignal(
    ts_event=1_000_000_000,
    ts_init=1_000_000_000,
    instrument_id=InstrumentId.from_str("ES.GLBX"),
    signal_value=0.75,
    confidence=0.9,
)

d = data.to_dict()
# {
#     "instrument_id": "ES.GLBX",
#     "signal_value": 0.75,
#     "confidence": 0.9,
#     "type": "MySignal",
#     "ts_event": 1000000000,
#     "ts_init": 1000000000,
# }

restored = MySignal.from_dict(d)
assert restored == data
```

### Bytes (msgpack)

```python
raw = data.to_bytes()       # msgspec.msgpack.encode(data.to_dict())
restored = MySignal.from_bytes(raw)
assert restored == data
```

### Arrow / Parquet

```python
batch = data.to_arrow()     # pa.RecordBatch with cls._schema
restored_list = MySignal.from_arrow(batch)  # Returns list[MySignal]
assert restored_list[0] == data

# The schema is available as a class attribute:
print(MySignal._schema)
```

Arrow support means custom data types work automatically with the Nautilus data catalog
(`ParquetDataCatalog`) for persistence and backtesting.

---

## Publishing Custom Data via MessageBus

Actors and strategies can publish custom data to the internal message bus, which routes
messages to subscribers via topic-based pattern matching.

```python
from nautilus_trader.core.data import Data
from nautilus_trader.model.data import DataType

class SignalProducer(Actor):
    def on_bar(self, bar: Bar):
        signal = MySignal(
            ts_event=bar.ts_event,
            ts_init=self.clock.timestamp_ns(),
            instrument_id=bar.bar_type.instrument_id,
            signal_value=self._compute_signal(bar),
            confidence=0.85,
        )
        self.publish_data(
            data_type=DataType(MySignal),
            data=signal,
        )
```

The publish call sends the data object to the msgbus topic `data.MySignal`.

---

## Subscribing and Receiving Custom Data

### In an Actor

```python
class SignalConsumer(Actor):
    def on_start(self):
        # Subscribe to all MySignal data
        self.subscribe_data(DataType(MySignal))

    def on_data(self, data: Data):
        if isinstance(data, MySignal):
            self.log.info(f"Received signal: {data.signal_value}")
```

### With metadata filters

`DataType` accepts a metadata dict that becomes part of the topic for more specific routing:

```python
# Producer
self.publish_data(
    data_type=DataType(MySignal, metadata={"source": "model_v2"}),
    data=signal,
)

# Consumer
self.subscribe_data(
    DataType(MySignal, metadata={"source": "model_v2"})
)
```

The topic becomes `data.MySignal.source=model_v2`.

### With an external data client

When data comes from an external source (adapter), specify a `ClientId`:

```python
self.subscribe_data(
    DataType(MySignal),
    ClientId("MY_ADAPTER"),
)
```

This sends a subscribe command to the data engine, which routes it to the named client.

### Unsubscribing

```python
self.unsubscribe_data(DataType(MySignal))
```

---

## Constructor Argument Order

The `@customdataclass` __init__ places `ts_event` and `ts_init` as the first two positional
arguments, followed by the class fields in declaration order:

```python
@customdataclass
class GreeksData(Data):
    instrument_id: InstrumentId = InstrumentId.from_str("ES.GLBX")
    delta: float = 0.0

# All of these work:
d1 = GreeksData(ts_event=1, ts_init=2)
d2 = GreeksData(1, 2, InstrumentId.from_str("ES.GLBX"), 0.5)
d3 = GreeksData(ts_event=1, ts_init=2, delta=0.5)
```

---

## Complete Example: Signal Pipeline

```python
from nautilus_trader.core.data import Data
from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model.data import DataType
from nautilus_trader.model.identifiers import InstrumentId

# 1. Define the custom data type
@customdataclass
class MomentumSignal(Data):
    instrument_id: InstrumentId = InstrumentId.from_str("AAPL.XNAS")
    score: float = 0.0
    regime: str = "neutral"

# 2. Producer actor computes and publishes
class MomentumProducer(Actor):
    def on_bar(self, bar: Bar):
        signal = MomentumSignal(
            ts_event=bar.ts_event,
            ts_init=self.clock.timestamp_ns(),
            instrument_id=bar.bar_type.instrument_id,
            score=self._calculate_momentum(bar),
            regime="trending" if abs(self._calculate_momentum(bar)) > 0.5 else "neutral",
        )
        self.publish_data(data_type=DataType(MomentumSignal), data=signal)

# 3. Consumer strategy reacts to signals
class MomentumStrategy(Strategy):
    def on_start(self):
        self.subscribe_data(DataType(MomentumSignal))

    def on_data(self, data: Data):
        if isinstance(data, MomentumSignal):
            if data.score > 0.7 and data.regime == "trending":
                # Enter long...
                pass

# 4. Data persists to Parquet catalog automatically if catalog is configured
```

---

## Overriding Generated Methods

If you need custom serialization logic, define your own `to_dict`, `from_dict`, `to_bytes`,
`from_bytes`, `to_arrow`, or `from_arrow` on the class. The decorator checks for each
method's existence before generating it:

```python
@customdataclass
class CustomSerialized(Data):
    values: bytes = b""

    def to_dict(self) -> dict:
        # Custom logic, e.g., base64-encode binary data
        import base64
        return {
            "values": base64.b64encode(self.values).decode(),
            "type": "CustomSerialized",
            "ts_event": self._ts_event,
            "ts_init": self._ts_init,
        }
```

---

## Rust Custom Data Types

Custom data types are a **Python-only** feature. The `@customdataclass` decorator relies on
Python's `dataclass` machinery and PyArrow for schema generation, which have no Rust equivalent.

However, Rust code can work with custom data through the FFI boundary:

- **Consuming in Rust**: Custom data objects arriving via the message bus are `Data` trait objects.
  Rust components receive them as opaque `PyObject` references and must call back into Python
  to access fields.
- **Defining data types in Rust**: For performance-critical data types, define a Rust struct with
  `#[pyclass]` and implement the `Data` trait manually. You must also manually implement
  `to_dict`/`from_dict` and register Arrow schemas via `register_arrow()` on the Python side.
  This is advanced — prefer Python `@customdataclass` unless profiling shows a bottleneck.

---

## Key Caveats

1. **Inherit from `Data`**: Custom data classes should inherit from `nautilus_trader.core.data.Data`
   to be compatible with the data engine and message bus.
2. **Type annotations required**: Every field must have a type annotation for the Arrow schema
   generation to work. The type must be one of the supported types listed above.
3. **Default values**: Fields should have defaults so the class works with `from_dict` round-trips.
4. **`InstrumentId` special handling**: If a field is named `instrument_id`, `to_dict` serializes
   it as `.value` (string) and `from_dict` reconstructs it via `InstrumentId.from_str`.
5. **Registration is automatic**: The decorator calls `register_serializable_type` and
   `register_arrow` at class definition time -- no manual registration needed.
6. **Class name uniqueness**: The `type` field in dicts uses the class `__name__`, so avoid
   name collisions across different custom data types.
