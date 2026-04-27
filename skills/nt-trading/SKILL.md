---
name: nt-trading
description: "Use when working with strategy logic, order execution, risk management, position/portfolio tracking, or exec algorithms in NautilusTrader."
---

# nt-trading

## What This Skill Covers

NautilusTrader **trading domain** — strategy logic, order execution, risk management, and portfolio/position tracking.

**Python modules**: `trading/`, `execution/`, `risk/`, `accounting/`, `portfolio/`
**Rust crates**: `nautilus_trading`, `nautilus_execution`, `nautilus_risk`, `nautilus_portfolio`

## When To Use

- Writing or modifying a `Strategy` or `Actor`
- Configuring order execution (order types, time-in-force, exec algorithms)
- Setting up risk management (risk engine config, margin models)
- Working with positions, portfolio queries, or accounting
- Building custom execution algorithms (`ExecAlgorithm`)
- Order lifecycle handling (`submit_order`, `cancel_order`, `modify_order`)

## When NOT To Use

- **Custom indicators or signal generation** → use `nt-signals`
- **Fill models or simulated exchange** → use `nt-backtest`
- **Adapter configuration** → use `nt-adapters`
- **Domain model types (instruments, identifiers)** → use `nt-model`
- **Data persistence or catalog** → use `nt-data`
- **Live node system setup** → use `nt-live`

## Python Usage

### Strategy

Subclass `Strategy` from `nautilus_trader.trading.strategy`:

```python
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.config import StrategyConfig

class MyStrategyConfig(StrategyConfig, frozen=True):
    instrument_id: str = None
    bar_type: str = None

class MyStrategy(Strategy):
    def __init__(self, config: MyStrategyConfig):
        super().__init__(config)
        # Store config, initialize state

    def on_start(self):
        # Subscribe to data, register indicators
        self.subscribe_bars(self.bar_type)

    def on_bar(self, bar):
        # Core trading logic
        pass

    def on_quote_tick(self, tick):
        pass

    def on_trade_tick(self, tick):
        pass

    def on_order_filled(self, event):
        # Post-fill logic
        pass

    def on_position_changed(self, event):
        pass

    def on_stop(self):
        # Cleanup
        pass
```

**Key order methods** (inherited from `Actor` → `Strategy`):
- `self.submit_order(order)` — submit to execution
- `self.cancel_order(order)` — cancel open order
- `self.modify_order(order, quantity=None, price=None, trigger_price=None)` — modify open order
- `self.cancel_all_orders(instrument_id)` — cancel all for instrument
- `self.close_position(position)` — close position with market order
- `self.close_all_positions(instrument_id)` — close all for instrument

**Order creation** (via `OrderFactory` on `self.order_factory`):
- `self.order_factory.market(instrument_id, side, quantity)`
- `self.order_factory.limit(instrument_id, side, quantity, price)`
- `self.order_factory.stop_market(instrument_id, side, quantity, trigger_price)`
- `self.order_factory.stop_limit(instrument_id, side, quantity, price, trigger_price)`
- `self.order_factory.trailing_stop_market(instrument_id, side, quantity, trailing_offset, ...)`

### Actor

Subclass `Actor` from `nautilus_trader.trading.actor` for non-trading components (data processing, signal publishing, monitoring):

```python
from nautilus_trader.trading.actor import Actor
from nautilus_trader.config import ActorConfig

class MyActor(Actor):
    def __init__(self, config: ActorConfig):
        super().__init__(config)

    def on_start(self):
        self.subscribe_data(...)

    def on_bar(self, bar):
        # Process data, publish signals via msgbus
        self.publish_signal(name="my_signal", value=signal_value)
```

### Risk & Execution Configuration

```python
from nautilus_trader.config import ExecEngineConfig, RiskEngineConfig

exec_config = ExecEngineConfig(
    load_cache=True,
    allow_cash_positions=True,
)

risk_config = RiskEngineConfig(
    bypass=False,
    max_order_submit_rate="100/00:00:01",  # 100 per second
    max_order_modify_rate="100/00:00:01",
    max_notional_per_order={"GBP/USD.SIM": 1_000_000},
)
```

## Python Extension

### Custom ExecAlgorithm

Subclass `ExecAlgorithm` from `nautilus_trader.execution.algorithm`:

```python
from nautilus_trader.execution.algorithm import ExecAlgorithm

class MyExecAlgorithm(ExecAlgorithm):
    def on_start(self):
        pass

    def on_order(self, order):
        # Custom execution logic — split, time-slice, etc.
        self.submit_order(order)

    def on_stop(self):
        pass
```

Register in config:
```python
exec_algorithms=[MyExecAlgorithm.fully_qualified_name()]
```

### Custom Margin/Position Sizing

Extend risk calculations by subclassing margin models or implementing custom position sizing logic in your Strategy.

## Rust Usage

NautilusTrader has a complete Rust implementation (v2 Rust) that runs without Python. Strategies and actors are written in pure Rust, compiled to standalone binaries.

### Rust Strategy

A strategy owns a `StrategyCore` and implements `DataActor` for data handling. The `nautilus_strategy!` macro wires up `Deref`/`DerefMut` and the `Strategy` trait.

```rust
use nautilus_common::actor::DataActor;
use nautilus_model::{
    data::QuoteTick,
    enums::OrderSide,
    identifiers::{InstrumentId, StrategyId},
    types::Quantity,
};
use nautilus_trading::{nautilus_strategy, strategy::{Strategy, StrategyConfig, StrategyCore}};

pub struct MyStrategy {
    core: StrategyCore,
    instrument_id: InstrumentId,
    trade_size: Quantity,
}

impl MyStrategy {
    pub fn new(instrument_id: InstrumentId) -> Self {
        let config = StrategyConfig {
            strategy_id: Some(StrategyId::from("MY_STRAT-001")),
            order_id_tag: Some("001".to_string()),
            ..Default::default()
        };
        Self {
            core: StrategyCore::new(config),
            instrument_id,
            trade_size: Quantity::from("1.0"),
        }
    }
}

// Generates Deref<Target = DataActorCore>, DerefMut, and Strategy trait impl
nautilus_strategy!(MyStrategy);

impl std::fmt::Debug for MyStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MyStrategy").finish()
    }
}

impl DataActor for MyStrategy {
    fn on_start(&mut self) -> anyhow::Result<()> {
        self.subscribe_quotes(self.instrument_id, None, None);
        Ok(())
    }

    fn on_quote(&mut self, quote: &QuoteTick) -> anyhow::Result<()> {
        let order = self.core.order_factory().market(
            self.instrument_id,
            OrderSide::Buy,
            self.trade_size,
            None, None, None, None, None, None, None,
        );
        self.submit_order(order, None, None)?;
        Ok(())
    }
}
```

**Override Strategy hooks** (order/position event handlers) by passing a block to the macro. The block can override multiple handlers — keep heavy logic in methods on the impl block, not inside the macro:

```rust
use nautilus_model::events::{OrderRejected, OrderFilled, OrderCanceled};

nautilus_strategy!(MyStrategy, {
    fn on_order_rejected(&mut self, event: OrderRejected) {
        let reason = event.reason.to_string();
        if reason.contains("POST_ONLY") {
            log::info!("post-only reject (expected): {reason}");
        } else {
            log::warn!("order rejected: {reason}");
        }
    }

    fn on_order_filled(&mut self, event: OrderFilled) {
        if let Err(e) = self.handle_fill(&event) {
            log::error!("handle_fill failed: {e}");
        }
    }

    fn on_order_canceled(&mut self, event: OrderCanceled) {
        // ...
    }
});
```

Inside the block: `&mut self` and the event by value. Do not redefine
`core()` / `core_mut()` — the macro already generates them.

### Warmup pattern (`request_quotes` + `on_historical_*`)

When a strategy needs historical data before quoting (e.g. for indicator
seeding or calibration), use the request/historical-handler pair:

```rust
fn on_start(&mut self) -> anyhow::Result<()> {
    self.subscribe_quotes(self.cfg.instrument_id, None, None);
    self.subscribe_trades(self.cfg.instrument_id, None, None);

    let now_ns: u64 = self.core.clock().timestamp_ns().into();
    let start = UnixNanos::from(now_ns - 24 * 3_600_000_000_000); // 24h
    let end = UnixNanos::from(now_ns);

    self.warmup_quotes = Some(Vec::new());
    self.warmup_trades = Some(Vec::new());
    self.request_quotes(self.cfg.instrument_id, Some(start), Some(end), None, None, None)?;
    self.request_trades(self.cfg.instrument_id, Some(start), Some(end), None, None, None)?;
    Ok(())
}

fn on_historical_quotes(&mut self, quotes: &[QuoteTick]) -> anyhow::Result<()> {
    if let Some(buf) = self.warmup_quotes.as_mut() { buf.extend_from_slice(quotes); }
    self.maybe_run_warmup();
    Ok(())
}

fn on_historical_trades(&mut self, trades: &[TradeTick]) -> anyhow::Result<()> {
    if let Some(buf) = self.warmup_trades.as_mut() { buf.extend_from_slice(trades); }
    self.maybe_run_warmup();
    Ok(())
}
```

`maybe_run_warmup()` runs the seeding logic once both buffers have
arrived. **Backtest gotcha**: if the run starts at the catalog's earliest
data, `request_*` returns nothing — keep a rolling buffer in `on_quote` /
`on_trade` as a fallback.

### Daily timer for re-calibration

Use `clock().set_timer_ns()` to schedule a repeating timer at UTC
midnight (or any anchor). It fires deterministically in backtest:

```rust
pub const DAILY_TIMER: &str = "my_daily_timer";

fn on_start(&mut self) -> anyhow::Result<()> {
    let now_ns: u64 = self.core.clock().timestamp_ns().into();
    let next_midnight = next_utc_midnight_ns(now_ns);
    self.core.clock_mut().set_timer_ns(
        DAILY_TIMER,
        24 * 3_600_000_000_000,                  // interval
        UnixNanos::from(next_midnight),          // start
        None, None,                              // stop_time, callback
    )?;
    Ok(())
}

// Override on_time_event in DataActor impl, or in nautilus_strategy! block.
fn on_time_event(&mut self, event: &TimeEvent) -> anyhow::Result<()> {
    if event.name.as_str() == DAILY_TIMER {
        // run daily work
    }
    Ok(())
}
```

### Instrument resolution

Hardcoded `tick_size` / `size_precision` is a bug magnet — every
instrument differs. Resolve from the cache in `on_start`:

```rust
fn on_start(&mut self) -> anyhow::Result<()> {
    let inst = self.cache().instrument(&self.cfg.instrument_id)
        .ok_or_else(|| anyhow::anyhow!("instrument not in cache"))?;
    self.tick_size = inst.price_increment().as_f64();
    self.instrument = Some(inst.clone());
    Ok(())
}
```

In backtest: `add_instrument(...)` populates the cache. In live: the
adapter's `InstrumentProvider::initialize()` does it. Either way,
`on_start` is the right hook — it runs after both.

**Order creation** (via `self.core.order_factory()`):
- `market(instrument_id, side, quantity, ...)`
- `limit(instrument_id, side, quantity, price, ...)`
- `stop_market(instrument_id, side, quantity, trigger_price, ...)`
- `stop_limit(instrument_id, side, quantity, price, trigger_price, ...)`
- `market_if_touched(...)`, `limit_if_touched(...)`, `trailing_stop_market(...)`

**Order management** (via `Strategy` trait, available on `self`):

| Method | Action |
|---|---|
| `submit_order` | Submit a new order to the venue |
| `submit_order_list` | Submit a list of contingent orders |
| `modify_order` | Modify price, quantity, or trigger price |
| `cancel_order` | Cancel a specific order |
| `cancel_orders` | Cancel a filtered set of orders |
| `cancel_all_orders` | Cancel all orders for an instrument |
| `close_position` | Close a position with a market order |
| `close_all_positions` | Close all open positions |

### Rust Actor

An actor owns a `DataActorCore` and receives data/events without order management. The `nautilus_actor!` macro wires up `Deref`/`DerefMut`.

```rust
use nautilus_common::{nautilus_actor, actor::{DataActor, DataActorConfig, DataActorCore}};
use nautilus_model::{data::QuoteTick, identifiers::{ActorId, InstrumentId}};

pub struct SpreadMonitor {
    core: DataActorCore,
    instrument_id: InstrumentId,
}

impl SpreadMonitor {
    pub fn new(instrument_id: InstrumentId) -> Self {
        let config = DataActorConfig {
            actor_id: Some(ActorId::from("SPREAD_MON-001")),
            ..Default::default()
        };
        Self {
            core: DataActorCore::new(config),
            instrument_id,
        }
    }
}

nautilus_actor!(SpreadMonitor);

impl std::fmt::Debug for SpreadMonitor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SpreadMonitor").finish()
    }
}

impl DataActor for SpreadMonitor {
    fn on_start(&mut self) -> anyhow::Result<()> {
        self.subscribe_quotes(self.instrument_id, None, None);
        Ok(())
    }

    fn on_quote(&mut self, quote: &QuoteTick) -> anyhow::Result<()> {
        let spread = quote.ask_price.as_f64() - quote.bid_price.as_f64();
        log::info!("Spread: {spread:.5}");
        Ok(())
    }
}
```

### DataActor Handler Table

All handlers have default no-op implementations. Override only what you need:

| Handler | Receives |
|---|---|
| `on_start` | Actor started |
| `on_stop` | Actor stopped |
| `on_quote` | `QuoteTick` |
| `on_trade` | `TradeTick` |
| `on_bar` | `Bar` |
| `on_book_deltas` | `OrderBookDeltas` |
| `on_book` | `OrderBook` (at interval) |
| `on_instrument` | `InstrumentAny` |
| `on_mark_price` | `MarkPriceUpdate` |
| `on_index_price` | `IndexPriceUpdate` |
| `on_funding_rate` | `FundingRateUpdate` |
| `on_option_greeks` | `OptionGreeks` |
| `on_option_chain` | `OptionChainSlice` |
| `on_instrument_status` | `InstrumentStatus` |
| `on_order_filled` | `OrderFilled` |
| `on_order_canceled` | `OrderCanceled` |
| `on_time_event` | `TimeEvent` |

### Running Rust Components

Three paths to run Rust strategies/actors:

1. **Pure Rust** — standalone binary, no Python runtime:
   ```rust
   let strategy = MyStrategy::new(instrument_id);
   node.add_strategy(strategy)?;
   node.run().await?;
   ```

2. **Native config from Python** — register built-in Rust strategies from Python:
   ```python
   from nautilus_trader.core.nautilus_pyo3.trading import GridMarketMakerConfig
   config = GridMarketMakerConfig(instrument_id=..., trade_size=...)
   node.add_native_strategy(config)
   ```

3. **Plugin loading** (planned) — load compiled `cdylib` crates at runtime.

### Guard Safety

When accessing other actors in callbacks:
- Look up actors by ID each time; do not cache an `ActorRef`
- Drop the guard before scope ends; never store in a field
- Never hold a guard across an `.await` point

## Rust Extension (PyO3 Path)

### Exposing Rust Strategies to Python

Use `#[pyclass]` configs with `add_native_strategy`/`add_native_actor` dispatch:

| Config | Strategy |
|---|---|
| `EmaCrossConfig` | `EmaCross` |
| `GridMarketMakerConfig` | `GridMarketMaker` |
| `DeltaNeutralVolConfig` | `DeltaNeutralVol` |

| Config | Actor |
|---|---|
| `BookImbalanceActorConfig` | `BookImbalanceActor` |

To add custom components to this path: add a `#[pyclass]` config and dispatch arm in `add_native_strategy` or `add_native_actor`.

### PyO3 Binding Conventions

- Use `#[pyclass]` and `#[pymethods]` for Python-visible types
- Register new modules in `crates/pyo3/src/lib.rs`
- Use `Python::attach(|py| { ... })` for callbacks that need the GIL
- Wrap FFI functions in `abort_on_panic(|| { ... })` — Rust panics must never unwind across FFI

## Key Conventions

### Order Lifecycle

Orders follow a strict state machine: `INITIALIZED → SUBMITTED → ACCEPTED → [PARTIALLY_FILLED] → FILLED | CANCELED | EXPIRED | REJECTED`. Never assume order state — always check via events.

### Position State

Positions transition: `OPENING → OPEN → CLOSING → CLOSED`. A position's `side` is determined by its net quantity. Hedge mode vs netting mode affects how fills create/modify positions.

### Live-Readiness Checklist

- Handle all order events (not just fills — also rejects, cancels, expirations)
- Implement `on_stop()` cleanup (cancel open orders, optionally close positions)
- Use `self.clock.timer_names` for timer management
- Check `self.portfolio.is_net_long()` / `is_net_short()` for position awareness
- Log state transitions at appropriate levels

### Testing

- Use `BacktestEngine` for strategy unit tests
- Verify order submission counts, fill events, position states
- Test edge cases: partial fills, rejects, disconnections
- See `references/guides/testing.md` for patterns

## References

- `references/concepts/` — strategies, actors, execution, orders, positions, portfolio, rust
- `references/api/` — trading, execution, risk, portfolio, accounting, orders, position, events
- `references/architecture_patterns.md` — **Cross-skill production reference**. Full strategy lifecycle (ingest → backtest → live), three-binary layout, onion architecture, atomic state, fail-fast philosophy. Load this first for any non-trivial Rust strategy work.
- `references/guides/` — testing patterns, write_rust_strategy, write_rust_actor, **rust_patterns** (architectural patterns from production Rust strategies), **troubleshooting_rust** (common Rust failure modes + diagnostic workflow)
- `references/examples/` — backtest examples (EMA cross, actor data/signals, msgbus), Rust strategies (ema_cross, grid_mm), Rust actors (imbalance)
- `templates/` — strategy.py, actor.py, exec_algorithm.py

### When to load which guide

- **Architectural decisions** (new strategy, refactor, lifecycle question) → `architecture_patterns.md` first.
- Building a new Rust strategy → `architecture_patterns.md` §10 build sequence, then `write_rust_strategy.md`, then `rust_patterns.md` for production patterns.
- Build/runtime errors, unexpected behavior → `troubleshooting_rust.md` (read the diagnostic workflow before guessing).
- Need to handle order events (rejects, fills, cancels) → `rust_patterns.md` §5 (override block).
- Need historical warmup or daily re-calibration → `rust_patterns.md` §2 and §3.
- Splitting a strategy into ingest / backtest / live binaries → `rust_patterns.md` §6 or `architecture_patterns.md` §1.
- Cross-skill troubleshooting (which skill / file owns this symptom) → `architecture_patterns.md` §8.
