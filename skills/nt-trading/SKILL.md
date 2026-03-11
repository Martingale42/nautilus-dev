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

```rust
use nautilus_trading::strategy::Strategy;
use nautilus_execution::engine::ExecutionEngine;
```

Strategy trait implementation in Rust follows the same lifecycle pattern: `on_start()`, `on_stop()`, `on_bar()`, etc.

See `crates/trading/examples/strategies/` for Rust strategy examples (EMA cross, grid market maker).

## Rust Extension

### Implementing Strategies in Rust

Rust strategies follow the same lifecycle as Python but implement traits directly:

```rust
use pyo3::prelude::*;
use nautilus_trading::strategy::Strategy;

#[pyclass(extends=Strategy)]
pub struct MyRustStrategy {
    // Strategy state
}

#[pymethods]
impl MyRustStrategy {
    #[new]
    fn new(config: MyRustStrategyConfig) -> Self { ... }

    fn on_start(&mut self) { ... }
    fn on_bar(&mut self, bar: &Bar) { ... }
    fn on_order_filled(&mut self, event: &OrderFilled) { ... }
    fn on_stop(&mut self) { ... }
}
```

See `crates/trading/examples/strategies/ema_cross.rs` and `grid_mm.rs` for working Rust strategy examples.

### PyO3 Binding Conventions

- Use `#[pyclass]` and `#[pymethods]` for Python-visible types
- Register new modules in `crates/pyo3/src/lib.rs`
- Use `Python::attach(|py| { ... })` for callbacks that need the GIL
- Wrap FFI functions in `abort_on_panic(|| { ... })` — Rust panics must never unwind across FFI

### Build Integration

New Rust code integrates via `build.py` which compiles static libraries and links them through Cython. The build sequence: `cargo build` → static lib → Cython `.pyx` imports → `pip install -e .`

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

- `references/concepts/` — strategies, actors, execution, orders, positions, portfolio
- `references/api/` — trading, execution, risk, portfolio, accounting, orders, position, events
- `references/guides/` — testing patterns
- `references/examples/` — backtest examples (EMA cross, actor data/signals, msgbus), Rust strategies
- `templates/` — strategy.py, actor.py, exec_algorithm.py
