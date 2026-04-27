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

NautilusTrader's data persistence and catalog APIs are fully available in
Rust. Backtest data flows through `ParquetDataCatalog`; live strategies
read from the cache and request historical windows via the actor API.

### Dependencies

```toml
[dependencies]
nautilus-common = "0.55"
nautilus-model = { version = "0.55", features = ["high-precision"] }
nautilus-persistence = "0.55"

anyhow = "1"
```

### ParquetDataCatalog

The catalog is the canonical on-disk format for backtest data. Layout
follows NT v1.226+ conventions:

```
{catalog_root}/
└── data/
    ├── instruments/{INSTRUMENT_ID}/instrument.parquet
    ├── order_book_deltas/{INSTRUMENT_ID}/*.parquet
    ├── quote_ticks/{INSTRUMENT_ID}/*.parquet
    └── trade_ticks/{INSTRUMENT_ID}/*.parquet
```

**Construction** — five positional arguments, most defaulted:

```rust
use nautilus_persistence::backend::catalog::ParquetDataCatalog;
use std::path::Path;

let catalog = ParquetDataCatalog::new(
    Path::new("/var/lib/nautilus/catalog/data"),
    None,  // fs_protocol (None = local filesystem)
    None,  // fs_storage_options
    None,  // batch_size override
    None,  // compression override
);
```

**Writing** instruments and data:

```rust
use nautilus_model::instruments::InstrumentAny;

// Instruments must be written before any data referencing them.
catalog.write_instruments(vec![instrument])?;

// Quote/trade/delta writes go through write_to_parquet.
catalog.write_to_parquet(quote_ticks, None, None, None)?;
catalog.write_to_parquet(trade_ticks, None, None, None)?;
catalog.write_to_parquet(order_book_deltas, None, None, None)?;
```

**Reading** for backtest setup or analysis:

```rust
use nautilus_model::identifiers::InstrumentId;

let instrument_id = InstrumentId::from("ETHUSDT-LINEAR.BYBIT");
let instruments = catalog.query_instruments(Some(vec![instrument_id]))?;
let quotes = catalog.query_quote_ticks(Some(vec![instrument_id]), None, None)?;
let trades = catalog.query_trade_ticks(Some(vec![instrument_id]), None, None)?;
```

**Idempotency.** By default the catalog skips partitions that already
exist on disk. Pass `--overwrite` (in your CLI) or delete the partition
manually to re-write.

### Custom ingest pipeline pattern

External venue archives (NDJSON, CSV.gz, etc.) usually need a small Rust
binary to convert into NT domain types and write to the catalog. The
canonical structure:

```rust
mod source {
    // Streaming readers — yield one event at a time, low memory.
    pub fn iter_orderbook_events(zip_path: &Path)
        -> impl Iterator<Item=Result<VendorEvent>>;
    pub fn iter_trades(csvgz_path: &Path)
        -> impl Iterator<Item=Result<VendorTrade>>;
}

mod decoder {
    // Pure functions: vendor format → NT domain types.
    pub fn to_book_deltas(evt: &VendorEvent, inst: &InstrumentAny) -> Vec<OrderBookDelta>;
    pub fn to_quote_tick(evt: &VendorEvent, inst: &InstrumentAny) -> Option<QuoteTick>;
    pub fn to_trade_tick(t: &VendorTrade, inst: &InstrumentAny) -> TradeTick;
}

mod writer {
    // Batches with flush boundaries.
    pub struct CatalogWriter { /* ... */ }
}
```

Key decoder rules:

- `ts_event = vendor_ts_ms * 1_000_000` (NT uses nanoseconds throughout).
- For backtest data, `ts_init = ts_event` (the strategy receives the
  event at the time it was emitted).
- L1 derived `QuoteTick`s should only be emitted when top-of-book price
  or size **changes** — emitting on every L2 delta produces millions of
  redundant rows per day.

Validation at the end of ingest is mandatory:

```rust
// Per partition: row count + first/last ts_event.
// Hard fail on L1 invariant violations (bid > ask).
for q in &batch {
    anyhow::ensure!(
        q.bid_price <= q.ask_price,
        "L1 invariant violated at ts {}", q.ts_event
    );
}
```

A crossed L1 row corrupts every backtest that touches that partition —
refuse to publish, don't warn.

### Instrument provider for live ingest

When ingesting from a live venue archive, fetch the canonical instrument
specs via the adapter's `InstrumentProvider` rather than hardcoding:

```rust
use nautilus_bybit::common::credential::Credential;
use nautilus_bybit::providers::BybitInstrumentProvider;

// Run in a tokio runtime (provider methods are async).
let provider = BybitInstrumentProvider::new(
    /* http_client */, /* credential */, None,
);
let instruments = provider.fetch_filtered(
    &["ETHUSDT", "LTCUSDT", "SUIUSDT"],
).await?;
catalog.write_instruments(instruments)?;
```

The same `InstrumentProvider` runs at live-node startup, so the
backtest and live paths share the canonical instrument definitions.

### Cache access from Rust

Strategies and actors access the cache via `self.cache()`:

```rust
fn on_start(&mut self) -> anyhow::Result<()> {
    let inst = self.cache().instrument(&self.cfg.instrument_id)
        .ok_or_else(|| anyhow::anyhow!("instrument not in cache"))?;
    let tick_size = inst.price_increment().as_f64();
    // ...
    Ok(())
}
```

Other cache queries (mirrors the Python API):

| Method | Returns |
|--------|---------|
| `cache.instrument(id)` | `Option<&InstrumentAny>` |
| `cache.instruments(venue)` | `Vec<InstrumentAny>` |
| `cache.order(client_order_id)` | `Option<&OrderAny>` |
| `cache.orders(...)` | `Vec<OrderAny>` |
| `cache.position(position_id)` | `Option<&Position>` |
| `cache.positions(...)` | `Vec<Position>` |
| `cache.account(account_id)` | `Option<AccountAny>` |
| `cache.quote_tick(id)` | `Option<&QuoteTick>` |
| `cache.trade_tick(id)` | `Option<&TradeTick>` |

### Historical data via the actor API

The cache is intentionally a thin recent-window store. For longer
windows, use the actor API's request methods — see `nt-trading` for the
warmup pattern (`request_quotes` + `on_historical_quotes`).

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
