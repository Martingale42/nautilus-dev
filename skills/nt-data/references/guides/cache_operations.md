# Cache Operations Reference

## Overview

The `Cache` class (`nautilus_trader.cache.cache.Cache`) is the central in-memory store for all
market and execution data in NautilusTrader. Strategies and actors access it through the read-only
`CacheFacade` base class, which is available as `self.cache` in any strategy or actor.

The cache holds instruments, orders, positions, accounts, ticks, bars, order books, greeks, yield
curves, and arbitrary key-value pairs. It maintains a rich set of indexes that enable fast filtering
by venue, instrument, strategy, account, and order/position status.

---

## Cache Configuration (CacheConfig)

**Module**: `nautilus_trader.cache.config`

```python
from nautilus_trader.cache.config import CacheConfig

config = CacheConfig(
    database=None,                    # DatabaseConfig | None -- backing database config
    encoding="msgpack",               # "msgpack" | "json" -- serialization encoding
    timestamps_as_iso8601=False,      # True -> ISO 8601 strings; False -> UNIX nanos
    persist_account_events=True,      # write account events to database
    buffer_interval_ms=None,          # ms between pipelined/batched transactions (10-1000 recommended)
    bulk_read_batch_size=None,        # chunk size for MGET (helps with Redis provider limits)
    use_trader_prefix=True,           # prefix keys with "trader-"
    use_instance_id=False,            # include trader instance ID in keys
    flush_on_start=False,             # flush database on startup
    drop_instruments_on_reset=True,   # clear instrument cache on reset
    tick_capacity=10_000,             # max deque length for quote/trade ticks per instrument
    bar_capacity=10_000,              # max deque length for bars per bar type
)
```

Key points:
- `tick_capacity` / `bar_capacity` control how many recent ticks or bars are kept in memory per
  instrument or bar type. Older entries are automatically evicted from the front of the deque.
- Setting `buffer_interval_ms` enables pipelined/batched writes to the database adapter, reducing
  I/O overhead at the cost of slightly delayed persistence.
- `flush_on_start=True` wipes all data in the backing store on each startup -- useful for
  development but dangerous in production.

---

## Instrument Queries

```python
# Single instrument by ID
instrument = self.cache.instrument(instrument_id)

# All instrument IDs, optionally filtered by venue
ids = self.cache.instrument_ids(venue=None)

# All instruments, optionally filtered by venue and/or underlying
instruments = self.cache.instruments(venue=None, underlying=None)

# Synthetic instruments
synthetic = self.cache.synthetic(instrument_id)
synthetics = self.cache.synthetics()
synthetic_ids = self.cache.synthetic_ids()
```

---

## Market Data Queries

### Ticks

```python
# Latest quote tick (index=0 is most recent, negative indexes go back)
tick = self.cache.quote_tick(instrument_id, index=0)
ticks = self.cache.quote_ticks(instrument_id)        # full deque as list
count = self.cache.quote_tick_count(instrument_id)
has = self.cache.has_quote_ticks(instrument_id)

# Trade ticks -- same pattern
tick = self.cache.trade_tick(instrument_id, index=0)
ticks = self.cache.trade_ticks(instrument_id)
count = self.cache.trade_tick_count(instrument_id)
has = self.cache.has_trade_ticks(instrument_id)
```

### Bars

```python
bar = self.cache.bar(bar_type, index=0)
bars_list = self.cache.bars(bar_type)
count = self.cache.bar_count(bar_type)
has = self.cache.has_bars(bar_type)
```

### Order Books

```python
book = self.cache.order_book(instrument_id)
own_book = self.cache.own_order_book(instrument_id)
update_count = self.cache.book_update_count(instrument_id)
has = self.cache.has_order_book(instrument_id)
```

### Prices and Cross Rates

```python
from nautilus_trader.model.enums import PriceType

price = self.cache.price(instrument_id, PriceType.MID)
prices_dict = self.cache.prices(PriceType.BID)  # {InstrumentId: Price}

xrate = self.cache.get_xrate(venue, from_currency, to_currency, PriceType.MID)
```

### Crypto-Specific Data

```python
mark = self.cache.mark_price(instrument_id, index=0)
marks = self.cache.mark_prices(instrument_id)

idx = self.cache.index_price(instrument_id, index=0)
idxs = self.cache.index_prices(instrument_id)

fr = self.cache.funding_rate(instrument_id, index=0)
frs = self.cache.funding_rates(instrument_id)
```

---

## Account Queries

```python
account = self.cache.account(account_id)
account = self.cache.account_for_venue(venue)
aid = self.cache.account_id(venue)
all_accounts = self.cache.accounts()

# Map a venue to an account (e.g. for multi-venue brokers like IB)
self.cache.set_account_id_for_venue(venue, account_id)
```

---

## Order Queries

All order query methods accept optional filters: `venue`, `instrument_id`, `strategy_id`, `side`, `account_id`.

```python
order = self.cache.order(client_order_id)
orders = self.cache.orders(venue=None, instrument_id=None, strategy_id=None, side=OrderSide.NO_ORDER_SIDE)
open_orders = self.cache.orders_open(...)
closed = self.cache.orders_closed(...)
emulated = self.cache.orders_emulated(...)
inflight = self.cache.orders_inflight(...)
for_position = self.cache.orders_for_position(position_id)

# Counts
self.cache.orders_open_count(...)
self.cache.orders_closed_count(...)
self.cache.orders_emulated_count(...)
self.cache.orders_inflight_count(...)
self.cache.orders_total_count(...)

# Status checks
self.cache.order_exists(client_order_id)
self.cache.is_order_open(client_order_id)
self.cache.is_order_closed(client_order_id)
self.cache.is_order_emulated(client_order_id)
self.cache.is_order_inflight(client_order_id)
self.cache.is_order_pending_cancel_local(client_order_id)

# ID lookups
self.cache.client_order_id(venue_order_id)
self.cache.venue_order_id(client_order_id)
self.cache.client_id(client_order_id)
```

### Order Lists

```python
order_list = self.cache.order_list(order_list_id)
order_lists = self.cache.order_lists(venue=None, instrument_id=None, strategy_id=None)
exists = self.cache.order_list_exists(order_list_id)
```

### Exec Algorithm Queries

```python
orders = self.cache.orders_for_exec_algorithm(exec_algorithm_id, ...)
spawn_orders = self.cache.orders_for_exec_spawn(exec_spawn_id)
total_qty = self.cache.exec_spawn_total_quantity(exec_spawn_id)
filled_qty = self.cache.exec_spawn_total_filled_qty(exec_spawn_id)
leaves_qty = self.cache.exec_spawn_total_leaves_qty(exec_spawn_id)
```

---

## Position Queries

All position query methods accept optional filters: `venue`, `instrument_id`, `strategy_id`, `side`, `account_id`.

```python
position = self.cache.position(position_id)
position = self.cache.position_for_order(client_order_id)
pid = self.cache.position_id(client_order_id)

positions = self.cache.positions(...)
open_positions = self.cache.positions_open(...)
closed_positions = self.cache.positions_closed(...)

self.cache.positions_open_count(...)
self.cache.positions_closed_count(...)
self.cache.positions_total_count(...)

self.cache.position_exists(position_id)
self.cache.is_position_open(position_id)
self.cache.is_position_closed(position_id)

# Snapshots
snapshot_ids = self.cache.position_snapshot_ids(instrument_id=None, account_id=None)
snapshots = self.cache.position_snapshots(position_id=None, account_id=None)
```

---

## General Key-Value Store

The cache provides an arbitrary bytes key-value store for persisting custom strategy/actor state:

```python
self.cache.add("my_key", b"serialized_value")
value: bytes = self.cache.get("my_key")
```

When a backing database is configured, these values are persisted through the `CacheDatabaseFacade`.

---

## CacheDatabaseFacade (Persistence Layer)

**Module**: `nautilus_trader.cache.facade`

The `CacheDatabaseFacade` is the abstract base class for all cache database adapters. It defines
the contract for load and store operations. The concrete implementation shipped with NautilusTrader
is `CachePostgresAdapter` in `nautilus_trader.cache.adapter`.

### Key abstract methods

| Category | Methods |
|----------|---------|
| Lifecycle | `close()`, `flush()` |
| Load bulk | `load_all()`, `load()`, `load_currencies()`, `load_instruments()`, `load_synthetics()`, `load_accounts()`, `load_orders()`, `load_positions()` |
| Load single | `load_currency(code)`, `load_instrument(id)`, `load_synthetic(id)`, `load_account(id)`, `load_order(id)`, `load_position(id)` |
| Load state | `load_actor(component_id)`, `load_strategy(strategy_id)` |
| Load index | `load_index_order_position()`, `load_index_order_client()` |
| Add | `add(key, value)`, `add_currency()`, `add_instrument()`, `add_synthetic()`, `add_account()`, `add_order()`, `add_position()` |
| Update | `update_account()`, `update_order()`, `update_position()`, `update_actor()`, `update_strategy()` |
| Delete | `delete_order()`, `delete_position()`, `delete_account_event()`, `delete_actor()`, `delete_strategy()` |
| Snapshot | `snapshot_order_state()`, `snapshot_position_state()` |
| Index | `index_venue_order_id()`, `index_order_position()` |

### Postgres Adapter

`CachePostgresAdapter` connects to PostgreSQL via the Rust `PostgresCacheDatabase` (pyo3 binding).
It transforms Cython objects to pyo3 representations before writing, and vice-versa on load. It
supports loading/storing: currencies, instruments, orders, accounts, quotes, trades, bars, signals,
custom data, and order/position snapshots.

---

## Cache Population: Backtest vs Live

### Backtest

During backtesting, the engine populates the cache differently:

1. **Instruments**: Added by the `BacktestEngine` before the run starts. The data engine feeds
   instruments into the cache when processing historical data.
2. **Market data**: Ticks and bars flow through the data engine into the cache as the backtest
   clock advances. The deque capacity (`tick_capacity`, `bar_capacity`) limits memory usage.
3. **Orders/Positions**: Created during the backtest as the strategy submits orders. The simulated
   exchange fills orders and the execution engine updates the cache.
4. **No database backing**: Backtests typically run with `database=None` (no persistence). All
   state lives purely in memory and is discarded after the run.

### Live

In live trading, the cache is populated from two sources:

1. **Database restore**: On startup, `cache_all()` loads currencies, instruments, accounts, orders,
   and positions from the backing database. Then `build_index()` reconstructs all the in-memory
   indexes. Finally `check_integrity()` verifies consistency.
2. **Live data feeds**: As market data and execution events arrive, the cache is updated in real
   time. Changes are simultaneously written through to the `CacheDatabaseFacade` for persistence.
3. **Reconciliation**: The execution engine reconciles cached order/position state against the
   venue's reported state during startup.

### Cache Startup Sequence

```
cache_all()         # Load all data from database
  -> cache_currencies()
  -> cache_instruments()
  -> cache_synthetics()
  -> cache_accounts()
  -> cache_orders()
  -> cache_order_lists()   # Rebuilt from cached orders
  -> cache_positions()
build_index()       # Rebuild all in-memory indexes
check_integrity()   # Validate bidirectional consistency
```

---

## Greeks and Yield Curves

```python
self.cache.add_greeks(greeks_object)
greeks = self.cache.greeks(instrument_id)

self.cache.add_yield_curve(yield_curve_object)
curve = self.cache.yield_curve("curve_name")
```

These are stored as opaque Python objects keyed by instrument ID or curve name.
