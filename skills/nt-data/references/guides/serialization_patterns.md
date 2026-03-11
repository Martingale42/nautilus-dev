# Serialization Patterns Reference

## Overview

NautilusTrader uses Apache Arrow as its primary serialization format for market data and events.
This enables zero-copy reads, columnar storage in Parquet files, and efficient IPC between Python
and Rust. The serialization layer lives in `nautilus_trader.serialization.arrow` and works closely
with the persistence wranglers in `nautilus_trader.persistence`.

The system has two serialization paths:
1. **Rust-native** -- Core data types (ticks, bars, book deltas) are serialized/deserialized
   entirely in Rust via pyo3 bindings for maximum performance.
2. **Python dict-based** -- Order events, account state, position events, and other complex types
   use a Python `to_dict`/`from_dict` pattern with Arrow RecordBatches.

---

## Built-in Arrow Schemas

**Module**: `nautilus_trader.serialization.arrow.schema`

The `NAUTILUS_ARROW_SCHEMA` dictionary maps data types to their `pyarrow.Schema` definitions.
Schemas for Rust-native types are derived from each type's `get_fields()` classmethod, while
Python-side types have schemas defined explicitly.

### Rust-Native Data Types (via `get_fields()`)

| Type | Key Fields |
|------|-----------|
| `OrderBookDelta` | action, side, price (fixed binary), size (fixed binary), order_id, flags, sequence, ts_event, ts_init |
| `OrderBookDepth10` | bid_price_0..9, ask_price_0..9, bid_size_0..9, ask_size_0..9, bid_count_0..9, ask_count_0..9, flags, sequence, ts_event, ts_init |
| `QuoteTick` | bid_price, ask_price, bid_size, ask_size (all fixed binary), ts_event, ts_init |
| `TradeTick` | price, size (fixed binary), aggressor_side, trade_id, ts_event, ts_init |
| `Bar` | open, high, low, close, volume (all fixed binary), ts_event, ts_init |
| `MarkPriceUpdate` | derived from `get_fields()` |
| `IndexPriceUpdate` | derived from `get_fields()` |

Prices and sizes use a fixed-precision binary representation (`pa.binary(PRECISION_BYTES)`) to
avoid floating-point errors. The constant `PRECISION_BYTES` comes from `nautilus_pyo3.PRECISION_BYTES`.

### Python-Defined Schemas (explicit)

| Type | Notable Fields |
|------|---------------|
| `FundingRateUpdate` | rate (binary), next_funding_ns (uint64, nullable), ts_event, ts_init |
| `InstrumentClose` | instrument_id (dict), close_type (dict), close_price (string), ts_event, ts_init |
| `InstrumentStatus` | instrument_id (dict), action (dict), reason, trading_event, is_trading, is_quoting, ts_event, ts_init |
| `OrderInitialized` | Full order spec: trader_id, strategy_id, instrument_id, client_order_id, order_side, order_type, quantity, time_in_force, plus optional price/trigger fields |
| `OrderFilled` | trade_id, position_id, last_qty, last_px, currency, commission, liquidity_side, info (binary) |
| Other `Order*` events | `OrderDenied`, `OrderSubmitted`, `OrderAccepted`, `OrderRejected`, `OrderCanceled`, `OrderExpired`, `OrderTriggered`, `OrderUpdated`, `OrderPendingCancel`, `OrderPendingUpdate`, `OrderReleased`, `OrderEmulated`, `OrderCancelRejected`, `OrderModifyRejected` |
| `ComponentStateChanged` | trader_id, component_id, component_type, state, config (binary), event_id, ts_event, ts_init |
| `TradingStateChanged` | trader_id, state, config (binary), event_id, ts_event, ts_init |
| `ShutdownSystem` | trader_id, component_id, reason, command_id, ts_init |

Many identifier fields use dictionary encoding (`pa.dictionary(pa.int16(), pa.string())`) for
compression efficiency, since values like trader_id and strategy_id repeat across many rows.

---

## Serialization API

**Module**: `nautilus_trader.serialization.arrow.serializer`

### ArrowSerializer

```python
from nautilus_trader.serialization.arrow.serializer import ArrowSerializer

# Single object -> RecordBatch
batch = ArrowSerializer.serialize(data_object, data_cls=type(data_object))

# List of objects -> Table
table = ArrowSerializer.serialize_batch(data_list, data_cls=QuoteTick)

# RecordBatch or Table -> list of objects
objects = ArrowSerializer.deserialize(data_cls=QuoteTick, batch=table)
```

For Rust-native types, `serialize_batch` calls functions like
`nautilus_pyo3.quotes_to_arrow_record_batch_bytes()` and reads the result back with
`pa.ipc.open_stream()`. For Python types, it delegates to registered encoder/decoder callables.

### Rust Serializer Functions

These pyo3 functions handle the high-performance path:

| Function | Data Type |
|----------|-----------|
| `nautilus_pyo3.book_deltas_to_arrow_record_batch_bytes()` | OrderBookDelta |
| `nautilus_pyo3.book_depth10_to_arrow_record_batch_bytes()` | OrderBookDepth10 |
| `nautilus_pyo3.quotes_to_arrow_record_batch_bytes()` | QuoteTick |
| `nautilus_pyo3.trades_to_arrow_record_batch_bytes()` | TradeTick |
| `nautilus_pyo3.bars_to_arrow_record_batch_bytes()` | Bar |
| `nautilus_pyo3.mark_prices_to_arrow_record_batch_bytes()` | MarkPriceUpdate |
| `nautilus_pyo3.index_prices_to_arrow_record_batch_bytes()` | IndexPriceUpdate |

---

## Registering Custom Arrow Schemas

Use `register_arrow()` to add serialization support for custom data types:

```python
from nautilus_trader.serialization.arrow.serializer import register_arrow
import pyarrow as pa

# Define schema
my_schema = pa.schema({
    "instrument_id": pa.dictionary(pa.int64(), pa.string()),
    "value": pa.float64(),
    "ts_event": pa.uint64(),
    "ts_init": pa.uint64(),
})

# Define encoder: object -> pa.RecordBatch
def my_encoder(data):
    if not isinstance(data, list):
        data = [data]
    dicts = [d.to_dict(d) for d in data]
    return pa.RecordBatch.from_pylist(dicts, schema=my_schema)

# Define decoder: pa.Table -> list[MyType]
def my_decoder(table):
    return [MyType.from_dict(d) for d in table.to_pylist()]

# Register
register_arrow(
    data_cls=MyType,
    schema=my_schema,
    encoder=my_encoder,
    decoder=my_decoder,
)
```

After registration, `ArrowSerializer.serialize()` and `ArrowSerializer.deserialize()` will handle
your custom type. The data catalog and Parquet writer will also use the registered schema.

Helper factories are available for types that implement `to_dict`/`from_dict`:

```python
from nautilus_trader.serialization.arrow.serializer import (
    make_dict_serializer,
    make_dict_deserializer,
)

register_arrow(
    data_cls=MyType,
    schema=my_schema,
    encoder=make_dict_serializer(my_schema),
    decoder=make_dict_deserializer(MyType),
)
```

### Auto-Registration at Import Time

When `nautilus_trader.serialization.arrow.serializer` is imported, it automatically registers:
- All types in `NAUTILUS_ARROW_SCHEMA` (Rust types get schema only; Python types get dict-based encoder/decoder)
- All `Instrument` subclasses (via `instruments.serialize`/`instruments.deserialize`)
- `AccountState`, `OrderInitialized`, `OrderFilled` (custom implementations)
- `ComponentStateChanged`, `TradingStateChanged`, `ShutdownSystem`
- All `PositionEvent` subclasses
- `FundingRateUpdate`

---

## Data Wranglers

Wranglers convert external data (pandas DataFrames, Arrow tables) into NautilusTrader domain
objects. There are two generations:

### Legacy Wranglers (Cython)

**Module**: `nautilus_trader.persistence.wranglers` (`.pyx`)

These produce Cython-based objects and accept an `Instrument` instance directly.

| Wrangler | Output Type | Input |
|----------|------------|-------|
| `OrderBookDeltaDataWrangler(instrument)` | `list[OrderBookDelta]` | DataFrame with action, side, price, size, order_id, flags, sequence |
| `QuoteTickDataWrangler(instrument)` | `list[QuoteTick]` | DataFrame with bid_price, ask_price (bid_size/ask_size optional) |
| `TradeTickDataWrangler(instrument)` | `list[TradeTick]` | DataFrame with price, quantity, trade_id (side optional) |
| `BarDataWrangler(bar_type, instrument)` | `list[Bar]` | DataFrame with open, high, low, close (volume optional) |

All legacy wranglers have a `.process(df, ts_init_delta=0, is_raw=False)` method. The quote tick
and trade tick wranglers also provide `.process_bar_data(...)` for generating tick-level data from
bar OHLCV data, with configurable timestamp offsets and random high/low ordering.

### V2 Wranglers (PyO3)

**Module**: `nautilus_trader.persistence.wranglers_v2`

These produce PyO3 (Rust) objects and are parameterized by raw precision values instead of
instrument objects. They work through Arrow IPC internally.

| Wrangler | Output Type | Constructor Args |
|----------|------------|-----------------|
| `OrderBookDeltaDataWranglerV2` | `list[pyo3.OrderBookDelta]` | instrument_id, price_precision, size_precision |
| `OrderBookDepth10DataWranglerV2` | `list[pyo3.OrderBookDepth10]` | instrument_id, price_precision, size_precision |
| `QuoteTickDataWranglerV2` | `list[pyo3.QuoteTick]` | instrument_id, price_precision, size_precision |
| `TradeTickDataWranglerV2` | `list[pyo3.TradeTick]` | instrument_id, price_precision, size_precision |
| `BarDataWranglerV2` | `list[pyo3.Bar]` | bar_type, price_precision, size_precision |

All V2 wranglers support:
- `from_instrument(instrument)` -- class method that extracts precision from an Instrument
- `from_schema(schema)` -- class method that extracts parameters from Arrow schema metadata
- `from_pandas(df, ts_init_delta=0)` -- convert DataFrame to NT objects
- `from_arrow(table)` -- convert Arrow Table to NT objects

### V2 Wrangler Pipeline

The `from_pandas` flow:
1. Rename columns to expected names (e.g. "timestamp" -> "ts_event", "ts_recv" -> "ts_init")
2. Parse timestamps to uint64 nanoseconds
3. Convert prices/sizes to fixed-precision binary representation
4. Build a `pyarrow.Table` with the correct schema
5. Serialize to Arrow IPC bytes via `pa.ipc.new_stream()`
6. Pass bytes to Rust `process_record_batch_bytes()` which returns native objects

### DataFrame Column Conventions

| Wrangler | Required Columns | Optional Columns |
|----------|-----------------|-----------------|
| OrderBookDeltaV2 | ts_event, price, size, order_id, aggressor_side | action, flags, ts_init |
| OrderBookDepth10V2 | ts_event, bid_price_0..9, ask_price_0..9, bid_size_0..9, ask_size_0..9 | bid_count_0..9, ask_count_0..9, flags, sequence, ts_init |
| QuoteTickV2 | ts_event (or timestamp), bid_price (or bid), ask_price (or ask) | bid_size, ask_size, ts_init |
| TradeTickV2 | ts_event (or timestamp), price, size (or quantity), trade_id, aggressor_side | ts_init |
| BarV2 | ts_event (or timestamp), open, high, low, close | volume, ts_init |

---

## Common Patterns

### Loading External CSV Data

```python
import pandas as pd
from nautilus_trader.persistence.wranglers_v2 import QuoteTickDataWranglerV2

wrangler = QuoteTickDataWranglerV2(
    instrument_id="EUR/USD.SIM",
    price_precision=5,
    size_precision=0,
)

df = pd.read_csv("quotes.csv")
# Expects columns: timestamp (or ts_event), bid_price, ask_price
ticks = wrangler.from_pandas(df)
```

### Reading from Parquet via Arrow

```python
import pyarrow.parquet as pq
from nautilus_trader.persistence.wranglers_v2 import BarDataWranglerV2

table = pq.read_table("bars.parquet")
wrangler = BarDataWranglerV2.from_schema(table.schema)
bars = wrangler.from_arrow(table)
```

### Writing Data to Parquet

```python
from nautilus_trader.serialization.arrow.serializer import ArrowSerializer
import pyarrow.parquet as pq

table = ArrowSerializer.serialize_batch(ticks, data_cls=type(ticks[0]))
pq.write_table(table, "output.parquet")
```

### Simulating Latency with ts_init_delta

All wranglers accept `ts_init_delta` (nanoseconds) to offset `ts_init` from `ts_event`. This
simulates network latency between the data source and the trading system:

```python
# 50ms simulated latency
ticks = wrangler.from_pandas(df, ts_init_delta=50_000_000)
```
