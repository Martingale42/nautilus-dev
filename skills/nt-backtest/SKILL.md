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

NautilusTrader provides two Rust APIs for backtesting: `BacktestEngine` (low-level) and `BacktestNode` (high-level with catalog streaming). Both run without Python.

### Dependencies

Add to your `Cargo.toml`:

```toml
[dependencies]
nautilus-backtest = { version = "0.55", features = ["streaming"] }
nautilus-execution = "0.55"
nautilus-model = { version = "0.55", features = ["stubs"] }
nautilus-persistence = "0.55"
nautilus-trading = { version = "0.55", features = ["examples"] }

ahash = "0.8"
anyhow = "1"
tempfile = "3"
ustr = "1"
```

Drop `streaming`, `nautilus-persistence`, `tempfile`, `ustr` if only using the low-level `BacktestEngine`.

**Feature flags:**

| Flag | Crate | Effect |
|---|---|---|
| `high-precision` | `nautilus-model` | 16-digit fixed precision (default 9). Required for crypto. |
| `stubs` | `nautilus-model` | Test instrument stubs (`audusd_sim`, etc.) |
| `examples` | `nautilus-trading` | Example strategies (`EmaCross`, `GridMarketMaker`) |
| `streaming` | `nautilus-backtest` | Catalog-based data streaming via `BacktestNode` |

### BacktestEngine (Low-Level API)

Direct control: build engine, add venues/instruments, load data in memory, register strategies, run.

```rust
use ahash::AHashMap;
use nautilus_backtest::{config::BacktestEngineConfig, engine::BacktestEngine};
use nautilus_execution::models::{fee::FeeModelAny, fill::FillModelAny};
use nautilus_model::{
    enums::{AccountType, BookType, OmsType},
    identifiers::Venue,
    instruments::{Instrument, InstrumentAny, stubs::audusd_sim},
    types::{Money, Quantity},
};
use nautilus_trading::examples::strategies::EmaCross;

// 1. Create engine
let mut engine = BacktestEngine::new(BacktestEngineConfig::default())?;

// 2. Add venue (31 args — most are Option with None defaults)
engine.add_venue(
    Venue::from("SIM"),
    OmsType::Hedging,
    AccountType::Margin,
    BookType::L1_MBP,
    vec![Money::from("1_000_000 USD")],
    None,            // base_currency
    None,            // default_leverage
    AHashMap::new(), // per-instrument leverages
    None,            // margin_model
    vec![],          // simulation modules
    FillModelAny::default(),
    FeeModelAny::default(),
    None, // latency_model
    None, // routing
    None, // reject_stop_orders
    None, // support_gtd_orders
    None, // support_contingent_orders
    None, // use_position_ids
    None, // use_random_ids
    None, // use_reduce_only
    None, // use_message_queue
    None, // use_market_order_acks
    None, // bar_execution
    None, // bar_adaptive_high_low_ordering
    None, // trade_execution
    None, // liquidity_consumption
    None, // allow_cash_borrowing
    None, // frozen_account
    None, // queue_position
    None, // oto_full_trigger
    None, // price_protection_points
)?;

// 3. Add instrument and data
let instrument = InstrumentAny::CurrencyPair(audusd_sim());
let instrument_id = instrument.id();
engine.add_instrument(&instrument)?;
let quotes = generate_quotes(instrument_id);
engine.add_data(quotes, None, true, true);

// 4. Register strategy and run
let strategy = EmaCross::new(instrument_id, Quantity::from("100000"), 10, 20);
engine.add_strategy(strategy)?;
engine.run(None, None, None, false)?;
```

Run the example: `cargo run -p nautilus-backtest --features examples --example engine-ema-cross`

### BacktestNode (High-Level API)

Loads data from `ParquetDataCatalog` and streams in configurable chunks. Requires `streaming` feature.

```rust
use nautilus_backtest::{
    config::{BacktestDataConfig, BacktestEngineConfig, BacktestRunConfig, BacktestVenueConfig, NautilusDataType},
    node::BacktestNode,
};
use nautilus_model::enums::{AccountType, BookType, OmsType};
use nautilus_persistence::backend::catalog::ParquetDataCatalog;
use ustr::Ustr;

// 1. Write data to catalog
let catalog = ParquetDataCatalog::new(catalog_path, None, None, None, None);
catalog.write_instruments(vec![instrument])?;
catalog.write_to_parquet(quotes, None, None, None)?;

// 2. Configure the run (configs use builder pattern)
let venue_config = BacktestVenueConfig::builder()
    .name(Ustr::from("SIM"))
    .oms_type(OmsType::Hedging)
    .account_type(AccountType::Margin)
    .book_type(BookType::L1_MBP)
    .starting_balances(vec!["1_000_000 USD".to_string()])
    .build();

let data_config = BacktestDataConfig::builder()
    .data_type(NautilusDataType::QuoteTick)
    .catalog_path(catalog_path.to_string())
    .instrument_id(instrument_id)
    .build();

let run_config = BacktestRunConfig::builder()
    .venues(vec![venue_config])
    .data(vec![data_config])
    .maybe_chunk_size(Some(100))
    .build();

// 3. Build, add strategies, run
let mut node = BacktestNode::new(vec![run_config])?;
node.build()?;

let engine = node.get_engine_mut("ema-cross-run").context("engine not found")?;
engine.add_strategy(EmaCross::new(instrument_id, Quantity::from("100000"), 10, 20))?;

node.run()?;
```

Run the example: `cargo run -p nautilus-backtest --features examples,streaming --example node-ema-cross`

### Registering Actors

Actors register with `add_actor` (same pattern as strategies):

```rust
let actor = SpreadMonitor::new(instrument_id);
engine.add_actor(actor)?;
```

## Rust Extension (PyO3 Path)

### Performance-Optimized Fill Models

Rust fill models for complex matching logic (order book simulation, market impact):

```rust
use nautilus_model::types::Price;

pub struct MyFillModel {
    prob_fill_on_limit: f64,
    prob_slippage: f64,
}

impl MyFillModel {
    pub fn is_limit_filled(&self) -> bool { /* ... */ }
    pub fn is_slipped(&self) -> bool { /* ... */ }
}
```

### Custom Matching Logic

The matching engine core lives in `crates/execution/src/matching_core/`. Extend it for custom matching behavior.

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
- `references/guides/` — benchmarking practices, benchmarking review checklist, run_rust_backtest
- `references/examples/` — clock timer, portfolio, cache usage, Rust backtests (engine_ema_cross, node_ema_cross), model configs
- `templates/` — fill_model.py
