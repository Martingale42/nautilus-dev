# Stage 10: Building NT

## Goal

Extend NautilusTrader itself — build adapters, custom data types, execution algorithms, fill models, and contribute to the platform.

## Prerequisites

- Stage 09 complete (can write full Rust strategies/actors, run backtests and live trading in Rust)

## What Can You Build?

| Extension | Where It Lives | Language |
|-----------|---------------|----------|
| New exchange adapter | `nautilus_trader/adapters/` | Python + optional Rust |
| Custom data type | Your project or NT source | Python (with `@customdataclass`) |
| Execution algorithm | `nautilus_trader/execution/` | Python (extends `ExecAlgorithm`) |
| Custom fill model | Backtest config | Python (extends `FillModel`) |
| Custom statistics | Analysis config | Python (extends `PortfolioStatistic`) |
| New Rust data type | `nautilus_core/model/` | Rust + PyO3 |
| Kernel extension | `nautilus_core/system/` | Rust |

## Building an Adapter

An adapter integrates NT with an external venue. Study existing adapters as reference:

### Adapter Components

```
my_adapter/
├── __init__.py
├── config.py           # XxxDataClientConfig, XxxExecClientConfig
├── http/
│   └── client.py       # REST API wrapper
├── websocket/
│   └── client.py       # WebSocket streaming
├── providers/
│   └── instrument.py   # InstrumentProvider — instrument discovery
├── data.py             # DataClient — market data subscriptions
├── execution.py        # ExecutionClient — order management
├── factories.py        # LiveDataClientFactory, LiveExecClientFactory
├── enums.py            # Venue-specific enums
└── parsing.py          # Data transformation (venue format → NT types)
```

### Key Interfaces

**DataClient** must implement:
- `subscribe_*()` / `unsubscribe_*()` for each data type
- `request_*()` for historical data requests
- Parse venue-specific formats into NT types (`QuoteTick`, `TradeTick`, `Bar`, `OrderBookDelta`)

**ExecutionClient** must implement:
- `submit_order()` / `modify_order()` / `cancel_order()`
- Parse venue execution reports into NT events (`OrderAccepted`, `OrderFilled`, etc.)
- Generate position/account state reports for reconciliation

### Reference Adapters

Study these in order of complexity:

1. **Databento** — data-only adapter (no execution), cleanest example
2. **Bybit** — full adapter with REST + WebSocket, moderate complexity
3. **Binance** — most complete, handles spot/futures/options, complex but comprehensive
4. **Interactive Brokers** — unique patterns (TWS gateway, Docker integration)

### Testing Adapters

NT has specification-based testing for adapters:

```python
# Data adapter tests
from nautilus_trader.test_kit.stubs.data import TestDataStubs

# Execution adapter tests
from nautilus_trader.test_kit.stubs.execution import TestExecStubs
```

See `developer_guide/spec_data_testing.md` and `developer_guide/spec_exec_testing.md` in the nt-adapters skill references.

## Building Execution Algorithms

Execution algorithms split orders into smaller pieces:

```python
from nautilus_trader.execution.algorithm import ExecAlgorithm

class MyAlgorithm(ExecAlgorithm):
    def on_order(self, order) -> None:
        # Split order into child orders
        child = self.spawn_market(
            primary=order,
            quantity=order.quantity / 4,
            time_in_force=TimeInForce.IOC,
        )
        self.submit_order(child)
```

**Rules:**
- Spawned order quantity must not exceed primary order's `leaves_qty`
- Spawned orders get IDs like `{original_id}-E{sequence}`
- Strategy cannot modify orders under an exec algorithm — only cancel

The built-in `TWAPExecAlgorithm` is a good reference.

## Building Custom Fill Models

For backtesting simulation:

```python
from nautilus_trader.backtest.models import FillModel

class MyFillModel(FillModel):
    def is_limit_filled(self, order, price) -> bool:
        # Custom logic for limit order fill probability
        ...

    def is_stop_filled(self, order, price) -> bool:
        # Custom logic for stop order fill probability
        ...
```

## Building Custom Portfolio Statistics

```python
from nautilus_trader.analysis.statistic import PortfolioStatistic

class SharpeRatio(PortfolioStatistic):
    def calculate_from_returns(self, returns: pd.Series) -> float:
        if returns.empty or returns.std() == 0:
            return 0.0
        return returns.mean() / returns.std() * (252 ** 0.5)
```

Register with: `engine.portfolio.analyzer.register_statistic(SharpeRatio())`

## Contributing to NT Core (Rust)

### Development Workflow

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/nautilus_trader.git
cd nautilus_trader

# 2. Set up dev environment
make install-debug

# 3. Make changes to Rust code

# 4. Build and test
make build-debug
make cargo-test
make pytest

# 5. Format and lint
cargo fmt --all
cargo clippy --all-targets
```

### Coding Standards

- Follow existing patterns in the crate you're modifying
- All public items need documentation
- Tests go in `#[cfg(test)] mod tests` within the same file
- Use `Result<T, E>` for fallible operations, not panics (except for data corruption — NT uses fail-fast for invalid data)

### Adding a New Rust Type with Python Bindings

1. Define the struct in the appropriate crate:
   ```rust
   // nautilus_core/model/src/types/my_type.rs
   #[repr(C)]
   #[derive(Clone, Debug, PartialEq)]
   #[pyclass]
   pub struct MyType {
       pub value: f64,
   }
   ```

2. Implement methods:
   ```rust
   #[pymethods]
   impl MyType {
       #[new]
       fn new(value: f64) -> Self { Self { value } }
   }
   ```

3. Register in the module's `lib.rs` or `mod.rs`

4. Add Python tests in `tests/unit_tests/`

## Domain Skills Reference

For deeper work in specific areas, use the appropriate nautilus-dev skill:

| Area | Skill |
|------|-------|
| Strategy logic, order execution, risk | `nt-trading` |
| Indicators, signals, analysis | `nt-signals` |
| Data pipelines, catalog, serialization | `nt-data` |
| Backtesting, fill models | `nt-backtest` |
| Live nodes, system boot, deployment | `nt-live` |
| Adapter development, venue integration | `nt-adapters` |
| Domain model types, instruments, identifiers | `nt-model` |

Each skill has bundled reference docs and exploration guides for its domain.

## Exercises

1. **Study an adapter**: Pick an adapter (e.g., Databento) and trace how market data flows from WebSocket → parsing → DataClient → DataEngine. Identify each transformation.

2. **Build a simple exec algorithm**: Create an algorithm that splits market orders into 3 equal parts, 5 seconds apart.

3. **Custom statistic**: Implement a max drawdown duration statistic and register it with the portfolio analyzer.

4. **Rust exploration**: Add a simple method to an existing Rust type (e.g., add `is_positive()` to `Price`). Build, test, verify it's accessible from Python.

## Checkpoint

You've completed the curriculum when:
- [ ] You can build an adapter (or understand the structure well enough to start)
- [ ] You can write execution algorithms that spawn child orders
- [ ] You can extend the backtest engine with custom fill models
- [ ] You can add custom portfolio statistics
- [ ] You know which domain skill to use for each area of NT development
- [ ] You can modify Rust code, build, and test changes
