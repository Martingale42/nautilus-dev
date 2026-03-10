# Stage 03: Architecture Foundations

## Goal

Understand NautilusTrader's core architecture, data model, and how components communicate.

## Prerequisites

- Stage 02 complete (ran examples, understand basic strategy lifecycle)

## Core Architecture

### Single-Threaded Kernel

NautilusTrader runs all core logic on a **single thread**: message dispatch, strategy callbacks, risk checks, cache reads/writes. This guarantees deterministic ordering of events.

Network I/O, persistence, and adapter communication run on separate threads/async runtimes, but your strategy code always executes on the main thread.

**Implication**: Never block in strategy callbacks. No `time.sleep()`, no synchronous HTTP calls, no heavy computation in `on_bar()`.

### Three Environment Contexts

| Context | Data Source | Venue | Use Case |
|---------|-----------|-------|----------|
| **Backtest** | Historical | Simulated | Strategy development |
| **Sandbox** | Real-time | Simulated | Paper trading |
| **Live** | Real-time | Real | Production trading |

The same strategy code runs unchanged across all three. The engine swaps out adapters and venues.

### Component Architecture

```
DataClient ──► DataEngine ──► Cache ──► MessageBus ──► Actor / Strategy
                                                           │
ExecutionClient ◄── ExecutionEngine ◄── RiskEngine ◄───────┘
```

- **DataEngine** routes market data to subscribers
- **ExecutionEngine** manages order lifecycle, routes commands to venues
- **RiskEngine** validates every order before submission (precision, size limits, notional checks)
- **Cache** stores all state in-memory (instruments, orders, positions, market data)
- **MessageBus** enables pub/sub communication between all components

## Value Types

NT uses **fixed-point integers**, not floating-point, for financial values:

| Type | Purpose | Example |
|------|---------|---------|
| `Price` | Market prices, signed, no currency | `Price(1.2345, precision=4)` |
| `Quantity` | Trade sizes, unsigned | `Quantity(100.0, precision=1)` |
| `Money` | Monetary amounts with currency | `Money(1000.00, USD)` |

**Critical rule**: Always use `instrument.make_price()` and `instrument.make_qty()` to create values with correct precision. The RiskEngine does NOT auto-round — wrong precision causes order rejection.

```python
# WRONG — hardcoded precision may not match instrument
price = Price(1.23, precision=2)

# RIGHT — matches instrument's price_precision
price = instrument.make_price(1.23)
```

## Data Types

Market data flows through NT as typed objects:

| Type | What It Represents |
|------|-------------------|
| `QuoteTick` | Best bid/ask with sizes |
| `TradeTick` | Individual trade execution |
| `Bar` | OHLCV aggregation |
| `OrderBookDelta` | Incremental book update |
| `OrderBookDepth10` | Top 10 levels snapshot |

**Data hierarchy** (most to least detailed): L3 order book → L2 order book → L1 quotes → Trades → Bars

### BarType String Format

```
{instrument_id}-{step}-{aggregation}-{price_type}-{source}
```

Examples:
- `"EUR/USD.SIM-1-MINUTE-BID-EXTERNAL"` — 1-min bid bars from external source
- `"ETHUSDT.BINANCE-250-TICK-LAST-INTERNAL"` — 250-tick bars aggregated internally from trade ticks

The `@` suffix chains aggregation: `"...-5-MINUTE-LAST-INTERNAL@1-MINUTE-EXTERNAL"` builds 5-min bars from 1-min externally-loaded bars.

## Instruments

Every tradable asset is an `Instrument` with:
- `InstrumentId` = `{symbol}.{venue}` (e.g., `ETHUSDT-PERP.BINANCE`)
- `price_precision` / `size_precision` — enforced everywhere
- `price_increment` / `size_increment` — minimum tick size

Instrument types include `Equity`, `CurrencyPair`, `FuturesContract`, `CryptoPerpetual`, `OptionContract`, and more.

## The Cache

The Cache is an **in-memory database** that auto-stores everything as it flows through the system:

```python
# In any strategy or actor:
self.cache.instrument(instrument_id)      # Get instrument
self.cache.bar(bar_type)                  # Most recent bar
self.cache.bars(bar_type)                 # All cached bars (index 0 = newest)
self.cache.orders_open()                  # All open orders
self.cache.positions_open()              # All open positions
self.cache.account_for_venue(venue)      # Account state
```

Data arrives in Cache **before** reaching strategy callbacks. The default capacity is 10,000 bars per bar type.

## The MessageBus

Three messaging patterns:

1. **Signals** — lightweight, single primitive value (str/int/float), no custom classes needed
   ```python
   self.publish_signal("regime", "trending", ts_event=ts)
   ```

2. **Custom Data** — structured data with timestamps, uses `@customdataclass`
   ```python
   self.publish_data(DataType(RegimeData), data)
   ```

3. **Raw Pub/Sub** — any Python object to any topic string
   ```python
   self.msgbus.publish("my.topic", event)
   ```

## Exercises

1. **Trace the data flow**: In `example_01`, follow a bar from CSV → DataFrame → `BarDataWrangler` → `engine.add_data()` → strategy's `on_bar()`. Identify each transformation step.

2. **Explore the Cache**: Run `example_06` and examine the cache query output. How many different query methods are available?

3. **Compare messaging**: Look at examples 09, 10, and 11. When would you use each messaging pattern?

## Checkpoint

You're ready for Stage 04 when:
- [ ] You can draw the component flow: DataClient → DataEngine → Cache → MessageBus → Strategy
- [ ] You understand why `instrument.make_price()` is critical (fixed-point precision)
- [ ] You know the difference between `INTERNAL` and `EXTERNAL` bar sources
- [ ] You can explain what the Cache stores and how to query it
- [ ] You understand the three messaging patterns (signals, custom data, raw pub/sub)
