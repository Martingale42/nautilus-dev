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

```rust
use nautilus_system::kernel::NautilusKernel;
use nautilus_live::node::TradingNode;
use nautilus_common::clock::LiveClock;
use nautilus_common::logging::Logger;
use nautilus_core::time::UnixNanos;
```

## Rust Extension

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
    fn new() -> Self { ... }
}
```

**PyO3 conventions:**
- Use `#[pyclass]` and `#[pymethods]` for Python-visible types
- Register in `crates/pyo3/src/lib.rs`
- GIL management: use `Python::attach()` for callback forwarding
- Tokio integration: use `tokio::runtime::Runtime` for async Rust code
- See `references/guides/ffi.md` for FFI patterns
- See `references/guides/rust.md` for Rust coding standards

**Build integration:** New Rust code integrates via `build.py` (static libs + Cython linking).

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

- `references/concepts/` — architecture, cache, logging, live, overview
- `references/api/` — system, core, common, config, live
- `references/guides/` — coding standards, FFI, Python conventions, Rust conventions, environment setup
- `references/examples/live/` — per-adapter live examples (Binance, Bybit, Databento, etc.)
