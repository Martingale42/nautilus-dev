---
name: nt-live
description: "Use when working with live trading nodes, system boot, NautilusKernel, engine configuration, component lifecycle, or deployment in NautilusTrader."
---

# nt-live

## What This Skill Covers

NautilusTrader **live infrastructure domain** — live trading nodes, system kernel, configuration, component lifecycle, and deployment.

**Python modules**: `live/`, `system/`, `config/`, `common/`, `core/`
**Rust crates**: `nautilus_system`, `nautilus_live`, `nautilus_common`, `nautilus_core`

## When To Use

- Configuring and launching live trading nodes
- `NautilusKernel` boot sequence and system setup
- Engine configuration (`TradingNodeConfig`)
- Component lifecycle management (INITIALIZED → RUNNING → STOPPED → DISPOSED)
- Logging setup and monitoring
- Clock configuration and timer management
- Deployment and production readiness
- Reconciliation and state recovery

## When NOT To Use

- **Adapter-specific configuration** → use `nt-adapters`
- **Strategy logic** → use `nt-trading`
- **Backtest setup** → use `nt-backtest`
- **Data persistence** → use `nt-data`

## Python Usage

### TradingNode Configuration

```python
from nautilus_trader.live.node import TradingNode
from nautilus_trader.config import TradingNodeConfig, LiveExecEngineConfig, LiveRiskEngineConfig

config = TradingNodeConfig(
    trader_id="TRADER-001",
    log_level="INFO",
    exec_engine=LiveExecEngineConfig(
        reconciliation=True,
        reconciliation_lookback_mins=1440,
    ),
    risk_engine=LiveRiskEngineConfig(
        bypass=False,
        max_order_submit_rate="100/00:00:01",
    ),
    data_clients={
        "BINANCE": BinanceDataClientConfig(...),
    },
    exec_clients={
        "BINANCE": BinanceExecClientConfig(...),
    },
)

node = TradingNode(config=config)
```

### Node Lifecycle

```python
# Build node
node = TradingNode(config=config)

# Add strategies
node.trader.add_strategy(my_strategy)

# Build (connects adapters, initializes components)
node.build()

# Run (starts event loop)
node.run()

# Stop (graceful shutdown)
node.stop()

# Dispose (cleanup resources)
node.dispose()
```

### Logging Configuration

```python
from nautilus_trader.config import LoggingConfig

logging_config = LoggingConfig(
    log_level="INFO",
    log_level_file="DEBUG",
    log_directory="/var/log/nautilus/",
    log_file_format="{trader_id}_{instance_id}",
    log_colors=True,
)
```

### Clock & Timers

```python
# In Strategy/Actor:
self.clock.set_timer(
    name="my_timer",
    interval=timedelta(seconds=60),
    callback=self.on_timer,
)

# Cancel timer
self.clock.cancel_timer("my_timer")

# Check active timers
active = self.clock.timer_names
```

### Component Lifecycle

All components follow: `INITIALIZED → RUNNING → STOPPED → DISPOSED`

```python
from nautilus_trader.common.component import Component

# Component states
component.state  # ComponentState enum
component.is_initialized
component.is_running
component.is_stopped
component.is_disposed
```

## Python Extension

### Custom Component

```python
from nautilus_trader.common.component import Component

class MyComponent(Component):
    def __init__(self, ...):
        super().__init__(...)

    def _start(self):
        # Called during component start
        pass

    def _stop(self):
        # Called during component stop
        pass

    def _reset(self):
        # Called during component reset
        pass

    def _dispose(self):
        # Called during component disposal
        pass
```

## Rust Usage

The `LiveNode` connects to real venues through adapter clients. It uses a builder pattern and runs as a standalone Rust binary — no Python runtime needed.

### Dependencies

```toml
[dependencies]
nautilus-common = "0.55"
nautilus-live = "0.55"
nautilus-model = "0.55"
nautilus-okx = "0.55"          # or any venue adapter
nautilus-trading = { version = "0.55", features = ["examples"] }

anyhow = "1"
dotenvy = "0.15"
log = "0.4"
tokio = { version = "1", features = ["full"] }
```

### LiveNode Builder

```rust
use log::LevelFilter;
use nautilus_common::{enums::Environment, logging::logger::LoggerConfig};
use nautilus_live::node::LiveNode;
use nautilus_model::identifiers::{AccountId, TraderId};
use nautilus_okx::{
    common::enums::OKXInstrumentType,
    config::{OKXDataClientConfig, OKXExecClientConfig},
    factories::{OKXDataClientFactory, OKXExecutionClientFactory},
};

let trader_id = TraderId::from("TESTER-001");
let account_id = AccountId::from("OKX-001");

let data_config = OKXDataClientConfig {
    instrument_types: vec![OKXInstrumentType::Swap],
    ..Default::default()
};

let exec_config = OKXExecClientConfig {
    trader_id,
    account_id,
    instrument_types: vec![OKXInstrumentType::Swap],
    ..Default::default()
};

let log_config = LoggerConfig {
    stdout_level: LevelFilter::Info,
    ..Default::default()
};

let mut node = LiveNode::builder(trader_id, Environment::Live)?
    .with_name("MY-NODE-001".to_string())
    .with_logging(log_config)
    .add_data_client(
        None,
        Box::new(OKXDataClientFactory::new()),
        Box::new(data_config),
    )?
    .add_exec_client(
        None,
        Box::new(OKXExecutionClientFactory::new()),
        Box::new(exec_config),
    )?
    .with_reconciliation(false)  // Enable in production!
    .with_delay_post_stop_secs(5)
    .build()?;
```

### Add Strategies and Run

```rust
use nautilus_model::{identifiers::InstrumentId, types::Quantity};
use nautilus_trading::examples::strategies::{GridMarketMaker, GridMarketMakerConfig};

let mut config = GridMarketMakerConfig::new(
    InstrumentId::from("ETH-USDT-SWAP.OKX"),
    Quantity::from("10.0"),  // max_position (hard cap on net exposure)
)
    .with_trade_size(Quantity::from("0.10"))  // per-order quantity
    .with_num_levels(3)
    .with_grid_step_bps(100)
    .with_skew_factor(0.5)
    .with_requote_threshold_bps(10)
    .with_expire_time_secs(8)
    .with_on_cancel_resubmit(true);

config.base.use_hyphens_in_client_order_ids = false; // OKX requirement

let strategy = GridMarketMaker::new(config);
node.add_strategy(strategy)?;
node.run().await?;
```

### Async Runtime

`LiveNode::run()` is async and requires a Tokio runtime:

```rust
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    dotenvy::dotenv().ok();
    // ... node setup ...
    node.run().await?;
    Ok(())
}
```

The node runs until interrupted (Ctrl+C) or shut down programmatically.

### Environment Variables

Adapters read API credentials from environment variables. Use `.env` + `dotenvy`:

```bash
export OKX_API_KEY="your_api_key"
export OKX_API_SECRET="your_api_secret"
export OKX_API_PASSPHRASE="your_passphrase"
```

Each adapter documents required variables in its integration guide.

### Adapter Examples

Most adapters include runnable `node_data_tester.rs` and `node_exec_tester.rs` examples:

| Adapter | Example directory |
|---|---|
| Architect AX | `crates/adapters/architect_ax/examples/` |
| Betfair | `crates/adapters/betfair/examples/` |
| Binance | `crates/adapters/binance/examples/` |
| BitMEX | `crates/adapters/bitmex/examples/` |
| Bybit | `crates/adapters/bybit/examples/` |
| Databento | `crates/adapters/databento/examples/` |
| Deribit | `crates/adapters/deribit/examples/` |
| dYdX | `crates/adapters/dydx/examples/` |
| Hyperliquid | `crates/adapters/hyperliquid/examples/` |
| Kraken | `crates/adapters/kraken/examples/` |
| OKX | `crates/adapters/okx/examples/` |
| Polymarket | `crates/adapters/polymarket/examples/` |
| Sandbox | `crates/adapters/sandbox/examples/` |
| Tardis | `crates/adapters/tardis/examples/` |

### Reconciliation

In production, enable reconciliation so the engine aligns cached state with the venue on startup:
- Remove `.with_reconciliation(false)` from the builder
- See `references/concepts/live.md` for reconciliation details

### Environment-based testnet/mainnet toggle

Most adapters distinguish testnet from mainnet via a `testnet` flag on
the config. Encode this in your CLI as an env-driven enum so the same
binary runs against either:

```rust
#[derive(Debug, Clone, Copy)]
pub enum BybitEnv { Testnet, Mainnet }

impl BybitEnv {
    pub fn from_env() -> anyhow::Result<Self> {
        let raw = std::env::var("BYBIT_ENV")
            .unwrap_or_else(|_| "testnet".to_string());
        match raw.to_lowercase().as_str() {
            "testnet" => Ok(Self::Testnet),
            "mainnet" => Ok(Self::Mainnet),
            other => anyhow::bail!(
                "BYBIT_ENV must be 'testnet' or 'mainnet', got '{other}'"
            ),
        }
    }

    pub fn is_testnet(&self) -> bool { matches!(self, Self::Testnet) }
}

// In main:
let env = BybitEnv::from_env()?;
let data_config = BybitDataClientConfig {
    testnet: env.is_testnet(),
    ..Default::default()
};
```

**Validate at startup, not deep in the factory.** Adapter configs read
credentials at build time; an unset env var produces a panic three
frames inside the factory. Validate at the top of `main` with a clear
`anyhow::bail!` so the operator sees what to fix.

### Graceful shutdown via on_stop

`LiveNode::run().await` returns when the runtime receives Ctrl+C or a
programmatic stop. Before NT tears down, your strategy's `on_stop` runs.

**For live, the safe default is cancel-only:**

```rust
fn on_stop(&mut self) -> anyhow::Result<()> {
    self.cancel_all_orders(self.cfg.instrument_id, None, None)?;
    if let Some(reporter) = self.reporter.as_mut() {
        reporter.flush()?;
    }
    log::warn!("strategy stopped — manual position flatten required");
    Ok(())
}
```

Auto-flatten via market orders during a halt can move price against
you in thin markets. Leave the position-close decision to the operator
unless you've validated the venue's liquidity at shutdown windows.

**For backtest, do auto-flatten** so NT records realized PnL for any
open inventory. See `nt-trading/references/guides/rust_patterns.md` §13.

### Structured logging for live

`tracing_subscriber::fmt().json()` emits one JSON record per log call —
parseable by Loki, Vector, Promtail, etc. Include the keys an oncall
operator needs:

```rust
log::info!(
    target: "as_mm",
    inventory = self.inventory,
    params_epoch = self.params_epoch,
    halted = self.risk.as_ref().map(|r| r.halted).unwrap_or(false),
    run_id = self.run_id.as_str(),
    "quote cycle"
);
```

**Don't log on every quote tick.** Even at INFO level this fills disks.
Log on state transitions (calibration, halt, fill, daily reset) and at
a low-frequency heartbeat.

## Rust Extension (PyO3 Path)

### Infrastructure Components in Rust

```rust
use pyo3::prelude::*;

#[pyclass]
pub struct MyInfraComponent {
    // Component state
}

#[pymethods]
impl MyInfraComponent {
    #[new]
    fn new() -> Self { /* ... */ }
}
```

**PyO3 conventions:**
- Use `#[pyclass]` and `#[pymethods]` for Python-visible types
- Register in `crates/pyo3/src/lib.rs`
- GIL management: use `Python::attach()` for callback forwarding
- Tokio integration: use `tokio::runtime::Runtime` for async Rust code
- See `references/guides/ffi.md` for FFI patterns
- See `references/guides/rust.md` for Rust coding standards

## Key Conventions

### Component Lifecycle

Components follow strict state machine: `INITIALIZED → RUNNING → STOPPED → DISPOSED`. State transitions are enforced — calling `start()` on a `RUNNING` component raises an error. Always check state before operations.

### Logging Patterns

- Use `self.log.info()`, `self.log.warning()`, `self.log.error()`, `self.log.debug()`
- Log state transitions and significant events
- Use structured messages: `f"Order submitted: {order.client_order_id}"`
- Set appropriate log levels per component

### Config Validation

- All config classes use `frozen=True` (immutable after creation)
- Validate config before node creation
- Use type hints for config fields
- Secrets should be passed via environment variables, not config files

### Production Readiness

- Enable reconciliation for live trading
- Configure appropriate rate limits
- Set up file logging for production
- Use health checks and monitoring
- Handle graceful shutdown properly

### Coding Standards

See `references/guides/coding_standards.md` for project-wide conventions including:
- Python style (PEP 8, type hints, docstrings)
- Rust style (edition 2024, clippy lints)
- FFI patterns (GIL management, callback forwarding)

## References

- `references/concepts/` — architecture, cache, logging, live, overview, rust
- `references/api/` — system, core, common, config, live
- `references/guides/` — coding standards, FFI, Python conventions, Rust conventions, environment setup, run_rust_live_trading
- `references/examples/live/` — per-adapter live examples (Binance, Bybit, Databento, etc.)
- **Cross-skill**: `nt-trading/references/guides/rust_patterns.md` for strategy-side patterns (warmup, atomic state, override block, graceful on_stop), `nt-trading/references/guides/troubleshooting_rust.md` for live runtime errors (BybitEnv panic, tokio runtime, request_quotes empty).
