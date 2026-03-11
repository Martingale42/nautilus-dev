---
name: nt-data
description: "Use when working with market data pipelines, data storage, ParquetDataCatalog, serialization, or cache operations in NautilusTrader."
---

# nt-data

## What This Skill Covers

NautilusTrader **data infrastructure domain** — data engines, persistence, serialization, and caching.

**Python modules**: `data/` (engine, client, messages), `persistence/`, `serialization/`, `cache/`
**Rust crates**: `nautilus_data`, `nautilus_persistence`, `nautilus_serialization`

## When To Use

- Loading market data from `ParquetDataCatalog`
- Configuring data subscriptions and data engine
- Persisting data to Parquet files
- Arrow serialization and custom schema registration
- Cache queries (instruments, orders, positions, accounts)
- Data wranglers for external data sources
- Integrating Databento or Tardis data

## When NOT To Use

- **Bar aggregation or indicators** → use `nt-signals`
- **Backtest data loading** → use `nt-backtest` (which uses nt-data references)
- **Data model types (instruments, identifiers)** → use `nt-model`
- **Adapter-specific data clients** → use `nt-adapters`

## Python Usage

### ParquetDataCatalog

```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog

# Initialize catalog
catalog = ParquetDataCatalog("/path/to/data")

# Query instruments
instruments = catalog.instruments()

# Query bars
bars = catalog.bars(
    instrument_ids=["ETHUSDT-PERP.BINANCE"],
    bar_type="ETHUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
)

# Query trade ticks
trades = catalog.trade_ticks(instrument_ids=["ETHUSDT-PERP.BINANCE"])

# Query quote ticks
quotes = catalog.quote_ticks(instrument_ids=["ETHUSDT-PERP.BINANCE"])

# Write data
catalog.write_data(bars)
catalog.write_data(trade_ticks)
```

### Data Engine Subscriptions

```python
# In Strategy/Actor on_start():
self.subscribe_bars(bar_type)
self.subscribe_quote_ticks(instrument_id)
self.subscribe_trade_ticks(instrument_id)
self.subscribe_order_book_deltas(instrument_id)
self.subscribe_order_book_snapshots(instrument_id, depth=10)
```

### Cache Queries

```python
# Access via self.cache in Strategy/Actor:
instrument = self.cache.instrument(instrument_id)
instruments = self.cache.instruments(venue=venue)
order = self.cache.order(client_order_id)
orders = self.cache.orders(instrument_id=instrument_id)
position = self.cache.position(position_id)
positions = self.cache.positions(instrument_id=instrument_id)
account = self.cache.account(account_id)
bar = self.cache.bar(bar_type)
quote = self.cache.quote_tick(instrument_id)
trade = self.cache.trade_tick(instrument_id)
```

### Data Wranglers

```python
from nautilus_trader.persistence.wranglers import BarDataWrangler

wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
bars = wrangler.process(df)  # pandas DataFrame → NautilusTrader Bar objects
```

## Python Extension

### Custom DataClient

```python
from nautilus_trader.data.client import MarketDataClient

class MyDataClient(MarketDataClient):
    def __init__(self, ...):
        super().__init__(...)

    async def _connect(self):
        # Establish connection to data source
        pass

    async def _disconnect(self):
        # Clean up connection
        pass

    async def _subscribe_trade_ticks(self, instrument_id):
        # Subscribe to trade feed
        pass

    def _handle_trade_tick(self, tick):
        # Forward tick to data engine
        self._handle_data(tick)
```

### Custom Arrow Serializers

Register custom Arrow schemas for custom data types:

```python
import pyarrow as pa
from nautilus_trader.serialization.arrow.serializer import register_arrow

# If using @customdataclass, serialization is auto-generated
# For manual registration:
register_arrow(
    data_cls=MyCustomData,
    schema=pa.schema([...]),
    serializer=my_serializer_func,
    deserializer=my_deserializer_func,
)
```

## Rust Usage

```rust
use nautilus_data::engine::DataEngine;
use nautilus_persistence::catalog::ParquetDataCatalog;
use nautilus_serialization::arrow::ArrowSerializer;
```

## Rust Extension

### Custom Persistence Backend

The persistence layer uses Arrow as its intermediate format. Custom backends implement reading/writing Arrow RecordBatches:

```rust
use pyo3::prelude::*;
use arrow::record_batch::RecordBatch;

#[pyclass]
pub struct MyStorageBackend {
    // Backend state (connection pool, file handles, etc.)
}

#[pymethods]
impl MyStorageBackend {
    #[new]
    fn new(connection_str: &str) -> PyResult<Self> { ... }

    fn write_batch(&self, batch: &RecordBatch) -> PyResult<()> { ... }
    fn read_batches(&self, query: &str) -> PyResult<Vec<RecordBatch>> { ... }
}
```

### Custom Arrow Schemas in Rust

For performance-critical serialization, implement Arrow schema conversion in Rust rather than Python. See `crates/serialization/src/arrow/` for the built-in schema implementations.

### PyO3 Binding Conventions

- Use `#[pyclass]` and `#[pymethods]` for Python-visible types
- Register in `crates/pyo3/src/lib.rs`
- Arrow types cross the FFI boundary via PyArrow's C Data Interface
- Wrap FFI functions in `abort_on_panic(|| { ... })`

## Key Conventions

### Catalog Query Patterns

- Always filter by `instrument_ids` for efficient queries
- Use `start` and `end` timestamps to bound time range
- Catalog returns data sorted by `ts_event`

### Arrow Schema Registration

- Custom data types using `@customdataclass` auto-register schemas
- Manual registration needed for custom serialization logic
- Schemas define the Parquet column layout

### Data Wrangler Conventions

- Wranglers convert external DataFrames to NT data types
- Input DataFrames should have timestamp index or column
- Use `BarDataWrangler`, `QuoteTickDataWrangler`, `TradeTickDataWrangler`

### Cache Configuration

```python
from nautilus_trader.config import CacheConfig

cache_config = CacheConfig(
    tick_capacity=10_000,
    bar_capacity=10_000,
)
```

## References

- `references/concepts/` — data, cache
- `references/api/` — data, persistence, serialization, cache
- `references/guides/` — test datasets, Databento integration, Tardis integration
- `references/examples/` — data catalog usage
