---
name: nt-backtest
description: "Use when working with backtesting engine, fill models, matching engine, simulated exchange, or backtest configuration in NautilusTrader."
---

# nt-backtest

## What This Skill Covers

NautilusTrader **backtesting domain** — backtest engine, simulated exchange, fill models, and matching logic.

**Python modules**: `backtest/`, `backtest/models/`, `execution/matching_core` (simulated exchange context)
**Rust crates**: `nautilus_backtest`, `nautilus_execution` (matching subset)

## When To Use

- Setting up and running backtests (`BacktestNode`, `BacktestEngine`)
- Configuring simulated exchanges and venues
- Customizing fill models, latency models, fee models
- Backtest configuration (`BacktestRunConfig`, `BacktestVenueConfig`)
- Understanding matching engine behavior
- Benchmarking backtest performance

## When NOT To Use

- **Strategy/order logic** → use `nt-trading`
- **Data loading/catalog** → use `nt-data`
- **Live deployment** → use `nt-live`
- **Indicator logic** → use `nt-signals`

## Python Usage

### BacktestNode (Recommended)

`BacktestNode` is the high-level API for running backtests with configuration:

```python
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import (
    BacktestRunConfig,
    BacktestDataConfig,
    BacktestVenueConfig,
    BacktestEngineConfig,
)

config = BacktestRunConfig(
    engine=BacktestEngineConfig(
        strategies=[
            ImportableStrategyConfig(
                strategy_path="my_module:MyStrategy",
                config_path="my_module:MyStrategyConfig",
                config={"instrument_id": "ETHUSDT-PERP.BINANCE", ...},
            ),
        ],
    ),
    data=[
        BacktestDataConfig(
            catalog_path="/path/to/data",
            data_cls="nautilus_trader.model.data:Bar",
            instrument_id="ETHUSDT-PERP.BINANCE",
            bar_type="ETHUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
        ),
    ],
    venues=[
        BacktestVenueConfig(
            name="BINANCE",
            oms_type="NETTING",
            account_type="MARGIN",
            base_currency=None,
            starting_balances=["10_000 USDT"],
        ),
    ],
)

node = BacktestNode(configs=[config])
results = node.run()
```

### BacktestEngine (Direct API)

`BacktestEngine` provides lower-level control, useful for strategy testing:

```python
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig

engine = BacktestEngine(config=BacktestEngineConfig())

# Add venue
engine.add_venue(
    venue=Venue("SIM"),
    oms_type=OmsType.HEDGING,
    account_type=AccountType.MARGIN,
    base_currency=USD,
    starting_balances=[Money(1_000_000, USD)],
)

# Add data
engine.add_data(bars)
engine.add_instrument(instrument)

# Add strategy
engine.add_strategy(strategy)

# Run
engine.run()

# Get results
engine.trader.generate_order_fills_report()
engine.trader.generate_positions_report()
```

### Venue Configuration

```python
BacktestVenueConfig(
    name="SIM",
    oms_type="HEDGING",       # HEDGING or NETTING
    account_type="MARGIN",     # CASH or MARGIN
    base_currency="USD",
    starting_balances=["1_000_000 USD"],
    fill_model=FillModel(),    # Optional custom fill model
    # latency_model=LatencyModel(), # Optional latency simulation
)
```

## Python Extension

### Custom FillModel

```python
from nautilus_trader.backtest.models import FillModel

class MyFillModel(FillModel):
    def __init__(self, ...):
        super().__init__()
        # TODO: Initialize model parameters

    # Override fill probability/slippage methods as needed
```

See `templates/fill_model.py` for full template.

### Custom Fee Models

Configure fee structures per venue:

```python
from nautilus_trader.model.objects import Money

# Via BacktestVenueConfig
BacktestVenueConfig(
    ...,
    fee_model=MakerTakerFeeModel(
        maker_fee=Decimal("0.0002"),
        taker_fee=Decimal("0.0004"),
    ),
)
```

## Rust Usage

```rust
use nautilus_backtest::engine::BacktestEngine;
use nautilus_backtest::config::BacktestRunConfig;
```

See `references/examples/rust_backtest/` for Rust backtest examples.

## Rust Extension

### Performance-Optimized Fill Models

Rust fill models are valuable for complex matching logic (e.g., order book simulation, market impact models) where Python overhead matters:

```rust
use pyo3::prelude::*;
use nautilus_model::instruments::InstrumentAny;
use nautilus_model::orders::OrderAny;
use nautilus_model::types::Price;

#[pyclass]
pub struct MyRustFillModel {
    prob_fill_on_limit: f64,
    prob_slippage: f64,
}

#[pymethods]
impl MyRustFillModel {
    #[new]
    fn new(prob_fill_on_limit: f64, prob_slippage: f64) -> Self {
        Self { prob_fill_on_limit, prob_slippage }
    }

    fn is_limit_filled(&self) -> bool { ... }
    fn is_slipped(&self) -> bool { ... }
}
```

### Custom Matching Logic

The matching engine core lives in `crates/execution/src/matching_core/`. For custom matching behavior, extend the Rust matching engine and expose via PyO3. See `crates/backtest/` for the backtest engine Rust implementation.

### PyO3 Binding Conventions

- Use `#[pyclass]` and `#[pymethods]` for Python-visible types
- Register in `crates/pyo3/src/lib.rs`
- Wrap FFI functions in `abort_on_panic(|| { ... })`
- Use workspace dependency inheritance (`serde = { workspace = true }`)

## Key Conventions

### BacktestNode vs BacktestEngine

- **BacktestNode**: Configuration-driven, supports multiple runs, recommended for most use cases
- **BacktestEngine**: Direct API, better for strategy unit tests and programmatic control

### Benchmarking Practices

- Use `BacktestEngine` timing for consistent benchmarks
- Profile with `py-spy` or `cProfile` for hotspot identification
- Compare against baseline runs with same data
- See `references/guides/benchmarking.md` for detailed practices

### Backtest Reproducibility

- Same data + same config = same results (deterministic)
- Set `random_seed` in fill model for stochastic fills
- Log all configuration for reproducibility

### Time Advancement

- Backtest engine advances time event-by-event
- Clock timers fire at their scheduled times during replay
- `ts_event` on data determines processing order

## References

- `references/concepts/` — backtesting, order book
- `references/api/` — backtest API
- `references/guides/` — benchmarking practices, benchmarking review checklist
- `references/examples/` — clock timer, portfolio, cache usage, Rust backtests, model configs
- `templates/` — fill_model.py
