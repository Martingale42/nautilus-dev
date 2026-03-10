---
name: nt-review
description: "Use when reviewing nautilus_trader implementations. Validates conventions, trading correctness, performance, testability, live trading readiness, FFI/Rust code, and benchmarking before deployment."
---

# Nautilus Trader Code Review

## Overview

Validate nautilus_trader implementations against conventions, trading correctness, performance, and testability. Includes specialized review sections for:

- **Backtesting**: Strategy logic, fill model configuration, data handling
- **Live Trading**: Reconciliation, network resilience, order management
- **Rust/FFI Code**: Memory safety, style conventions, PyO3 bindings
- **Performance**: Benchmarking, profiling, optimization verification

## When to Use

- After implementing components (via nt-implement)
- Before merging to main branch
- When reviewing existing code for issues
- Before deploying to paper/live trading
- When reviewing Rust core implementations or FFI bindings
- When validating performance-critical code

## Review Dimensions

### 1. Nautilus Conventions

#### Lifecycle Methods

Check that lifecycle methods are correctly implemented:

```python
# REQUIRED: Always call super().__init__()
def __init__(self, config: MyConfig) -> None:
    super().__init__(config)  # Must be first

# REQUIRED: Initialize state in on_start, not __init__
def on_start(self) -> None:
    self.instrument = self.cache.instrument(self.config.instrument_id)
    self.request_bars(self.config.bar_type)  # Historical first
    self.subscribe_bars(self.config.bar_type)  # Then live

# REQUIRED: Cleanup in on_stop
def on_stop(self) -> None:
    self.cancel_all_orders(self.config.instrument_id)
    self.unsubscribe_bars(self.config.bar_type)

# REQUIRED: Reset state for reuse
def on_reset(self) -> None:
    self.instrument = None
```

**Red flags:**
- Using `clock`, `logger`, or `cache` in `__init__` (not yet available)
- Missing null checks on cached instruments
- Subscribing before requesting historical data
- Not cleaning up in `on_stop`

#### API Usage

Check for correct API patterns:

```python
# CORRECT: Use order factory
order = self.order_factory.market(...)
self.submit_order(order)

# CORRECT: Access cache properly
instrument = self.cache.instrument(instrument_id)
if instrument is None:
    self.log.error("Instrument not found")
    return

# CORRECT: Use clock for timestamps
ts = self.clock.timestamp_ns()

# WRONG: Direct construction
order = MarketOrder(...)  # Don't do this

# WRONG: Assuming cache has data
instrument = self.cache.instrument(instrument_id)
price = instrument.make_price(100)  # Crashes if None
```

#### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Config class | `{Component}Config` | `TrendStrategyConfig` |
| Instrument ID | `{symbol}.{venue}` | `BTCUSDT-PERP.BINANCE` |
| Strategy ID | `{Class}-{tag}` | `TrendStrategy-001` |
| Bar type | `{id}-{step}-{agg}-{price}-{source}` | `BTCUSDT-PERP.BINANCE-5-MINUTE-LAST-EXTERNAL` |
| Custom data | `{Purpose}Data` | `RegimeData`, `FeatureData` |

### 2. Trading Correctness

#### Position Sizing

Check for proper position sizing:

```python
# CORRECT: Use instrument methods for precision
quantity = self.instrument.make_qty(calculated_size)
price = self.instrument.make_price(calculated_price)

# CORRECT: Respect instrument limits
min_qty = float(self.instrument.min_quantity)
max_qty = float(self.instrument.max_quantity or 1e9)
final_size = max(min_qty, min(calculated_size, max_qty))

# WRONG: Raw floats
quantity = Quantity.from_str("1.5")  # May violate precision
```

**Red flags:**
- Hardcoded position sizes without instrument validation
- No min/max quantity checks
- Missing precision handling

#### Order Management

Check for proper order handling:

```python
# CORRECT: Handle all order states
def on_order_rejected(self, event: OrderRejected) -> None:
    self.log.warning(f"Order rejected: {event.reason}")
    self._handle_rejection()

def on_order_canceled(self, event: OrderCanceled) -> None:
    self.log.info(f"Order canceled: {event.client_order_id}")

def on_order_filled(self, event: OrderFilled) -> None:
    self.log.info(f"Filled: {event.last_qty} @ {event.last_px}")

# CORRECT: Cancel before closing
def _close_position(self) -> None:
    self.cancel_all_orders(self.instrument.id)
    self.close_position(self.instrument.id)
```

**Red flags:**
- No rejection handling
- Assuming orders always fill
- Not canceling orders before closing positions
- Not handling partial fills

#### Risk Checks

Verify risk controls are present:

```python
# REQUIRED: Pre-trade validation
def _validate_trade(self) -> bool:
    # Check position limits
    net_pos = self.portfolio.net_position(self.instrument.id)
    if abs(net_pos) >= self.config.max_position:
        return False

    # Check exposure limits
    exposure = self.portfolio.net_exposure(self.instrument.id)
    if exposure and float(exposure) > self.config.max_exposure:
        return False

    return True
```

**Red flags:**
- No position size limits
- No loss limits
- No exposure checks
- Trading without checking portfolio state

#### Edge Cases

Check for handling of:

- [ ] First bar after start (indicators not initialized)
- [ ] Gap in data (missing bars)
- [ ] Market close/open transitions
- [ ] Instrument not found in cache
- [ ] Account with insufficient balance
- [ ] Order rejected by venue
- [ ] Partial fills
- [ ] Network reconnection

### 3. Performance

#### Blocking Calls

**Never block in handlers.** Check for:

```python
# WRONG: Blocking I/O in handler
def on_bar(self, bar: Bar) -> None:
    data = requests.get("http://api.example.com")  # BLOCKS!
    model = pickle.load(open("model.pkl", "rb"))  # BLOCKS!

# CORRECT: Load in on_start, use cached
def on_start(self) -> None:
    self.model = self._load_model()

def on_bar(self, bar: Bar) -> None:
    result = self.model.predict(features)  # Uses preloaded model
```

**Red flags:**
- HTTP requests in `on_bar`, `on_quote_tick`, etc.
- File I/O in hot paths
- Database queries in handlers
- `time.sleep()` anywhere

#### Memory Management

Check for memory leaks:

```python
# CORRECT: Bounded buffer
self.bar_buffer: deque[Bar] = deque(maxlen=100)

# WRONG: Unbounded growth
self.all_bars: list[Bar] = []  # Grows forever!

# CORRECT: Clear on reset
def on_reset(self) -> None:
    self.bar_buffer.clear()
    self.feature_cache.clear()
```

**Red flags:**
- Unbounded lists/dicts that grow with data
- No cleanup in `on_reset`
- Storing references to large objects unnecessarily

#### Efficient Data Handling

```python
# CORRECT: Use numpy for vectorized operations
import numpy as np
closes = np.array([float(b.close) for b in self.bars])
mean = np.mean(closes)

# LESS EFFICIENT: Python loops
total = 0
for bar in self.bars:
    total += float(bar.close)
mean = total / len(self.bars)
```

### 4. Testability

#### Backtest Compatibility

Check that components work in backtest:

```python
# CORRECT: Use self.clock for time (works in backtest and live)
current_time = self.clock.utc_now()

# WRONG: System time (breaks backtest determinism)
import datetime
current_time = datetime.datetime.utcnow()

# CORRECT: Deterministic behavior
def _calculate_signal(self, bar: Bar) -> float:
    return self.ema.value - self.sma.value

# WRONG: Non-deterministic
import random
def _calculate_signal(self, bar: Bar) -> float:
    return random.random()  # Different each run!
```

#### Isolation

Check components can be tested independently:

```python
# GOOD: Dependencies are injected via config
class MyStrategy(Strategy):
    def __init__(self, config: MyConfig) -> None:
        super().__init__(config)
        # No hardcoded dependencies

# BAD: Hardcoded dependencies
class MyStrategy(Strategy):
    def __init__(self, config: MyConfig) -> None:
        super().__init__(config)
        self.external_api = ExternalAPI("hardcoded-key")
```

#### Logging

Check for appropriate logging:

```python
# GOOD: Appropriate levels
self.log.debug(f"Processing bar: {bar}")  # Debug for verbose
self.log.info(f"Order submitted: {order.client_order_id}")  # Info for actions
self.log.warning(f"Unusual spread: {spread}")  # Warning for concerns
self.log.error(f"Failed to load model: {e}")  # Error for failures

# BAD: Wrong levels
self.log.info(f"Bar received: {bar}")  # Too verbose for info
self.log.error(f"No signal")  # Not an error
```

## Review Checklist

### Quick Check (< 5 min)

- [ ] All lifecycle methods call `super()`
- [ ] `on_start` fetches instrument from cache with null check
- [ ] `request_bars` before `subscribe_bars`
- [ ] `on_stop` cancels orders and unsubscribes
- [ ] Type hints on all methods
- [ ] No blocking calls in handlers

### Full Review (15-30 min)

**Conventions:**
- [ ] Config class follows naming convention
- [ ] All parameters typed and documented
- [ ] Lifecycle methods correctly implemented
- [ ] Proper use of order factory and cache

**Trading Correctness:**
- [ ] Position sizing uses instrument methods
- [ ] Min/max quantity respected
- [ ] Order rejection handled
- [ ] Position limits enforced
- [ ] Warmup period handled

**Performance:**
- [ ] No blocking I/O in handlers
- [ ] Bounded data structures
- [ ] Cleanup in `on_reset`
- [ ] Efficient calculations

**Testability:**
- [ ] Uses `self.clock` not system time
- [ ] Deterministic behavior
- [ ] Dependencies injectable
- [ ] Appropriate logging levels

## Common Issues by Component

### Strategy
- Missing order rejection handling
- No position limits
- Blocking in `on_bar`
- Not canceling orders on stop

### Actor
- Model loading in handler instead of `on_start`
- Unbounded signal history
- No warmup handling
- Missing `on_reset` cleanup

### Indicator
- Not implementing `initialized` property
- Missing `reset` method
- Wrong handler signature

### Adapter
- Blocking HTTP in data handlers
- No reconnection logic
- Missing error handling
- Not validating responses

## 5. Live Trading Review

When reviewing code for live trading deployment, check these additional dimensions:

### Configuration Review

```python
# CORRECT: Proper timeout configuration
config = TradingNodeConfig(
    timeout_connection=30.0,      # Allow time for venue connection
    timeout_reconciliation=10.0,  # Allow time for state sync
    timeout_portfolio=10.0,       # Allow time for portfolio init
    timeout_disconnection=10.0,   # Allow time for graceful shutdown
)

# CORRECT: Execution engine configured for resilience
exec_engine=LiveExecEngineConfig(
    reconciliation=True,                     # Enable startup reconciliation
    inflight_check_interval_ms=2000,         # Check in-flight orders
    open_check_interval_secs=10.0,           # Poll open orders
    open_check_lookback_mins=60,             # Don't reduce below 60
    reconciliation_startup_delay_secs=10.0,  # Don't reduce below 10
)
```

**Red flags:**
- `reconciliation=False` without explicit justification
- `open_check_lookback_mins` < 60 (causes false "missing order" resolutions)
- Missing timeout configurations
- No database config for state persistence

### Execution Reconciliation

Check for proper handling of execution state:

```python
# CORRECT: Strategy claims external orders
config = StrategyConfig(
    external_order_claims=["BTCUSDT-PERP.BINANCE"],  # Claim orders for this instrument
    manage_contingent_orders=True,                   # Auto-manage OCO/OUO
    manage_gtd_expiry=True,                          # Handle GTD expirations
)

# CORRECT: Handle reconciliation scenarios in strategy
def on_start(self) -> None:
    # Check for existing positions from reconciliation
    position = self.cache.position(self.instrument.id)
    if position and not position.is_flat:
        self.log.info(f"Resuming with existing position: {position}")
        self._sync_with_position(position)
```

**Red flags:**
- No `external_order_claims` when strategy should resume managing orders
- Missing logic to handle pre-existing positions
- No handling for `INTERNAL-DIFF` reconciliation orders

### Network Resilience

```python
# CORRECT: Adapter with reconnection logic
class MyDataClient(LiveDataClient):
    def __init__(self, ...):
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay_secs = 5.0

    async def _reconnect(self) -> None:
        while self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                await self._connect()
                self._reconnect_attempts = 0
                return
            except Exception as e:
                self._reconnect_attempts += 1
                self.log.warning(f"Reconnect attempt {self._reconnect_attempts} failed: {e}")
                await asyncio.sleep(self._reconnect_delay_secs)

# WRONG: No reconnection handling
async def _on_disconnect(self) -> None:
    pass  # Connection lost, no recovery
```

**Red flags:**
- No reconnection logic in adapters
- Missing error handling for network failures
- No exponential backoff for retries
- Blocking calls in async handlers

### Order State Management

```python
# CORRECT: Handle all order lifecycle states
def on_order_rejected(self, event: OrderRejected) -> None:
    self.log.warning(f"Order rejected: {event.reason}")
    self._handle_rejection(event)

def on_order_canceled(self, event: OrderCanceled) -> None:
    self._pending_orders.discard(event.client_order_id)

def on_order_expired(self, event: OrderExpired) -> None:
    self.log.info(f"Order expired: {event.client_order_id}")
    self._evaluate_resubmission(event)

def on_order_filled(self, event: OrderFilled) -> None:
    if event.is_partial:
        self.log.debug(f"Partial fill: {event.last_qty} of {event.order.quantity}")
    else:
        self.log.info(f"Order filled: {event.client_order_id}")
```

**Red flags:**
- Missing rejection handling
- No partial fill handling
- Not tracking in-flight orders
- Assuming orders always fill

### Live Trading Checklist

- [ ] Reconciliation enabled with appropriate lookback
- [ ] Timeouts configured for all connection phases
- [ ] External order claims configured if resuming
- [ ] All order lifecycle events handled
- [ ] Reconnection logic in adapters
- [ ] State persistence to database configured
- [ ] Graceful shutdown with order cancellation
- [ ] Position sync on startup
- [ ] Windows signal handling if applicable

## 6. Rust/FFI Code Review

### Rust Style Conventions

Check adherence to NautilusTrader Rust style:

```rust
// CORRECT: File header
// -------------------------------------------------------------------------------------------------
//  Copyright (C) 2015-2025 Nautech Systems Pty Ltd. All rights reserved.
//  https://nautechsystems.io
//
//  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
//  ...
// -------------------------------------------------------------------------------------------------

// CORRECT: Module documentation
//! Custom indicator implementation for momentum calculation.
//!
//! # Feature flags
//!
//! - `python`: Enables Python bindings via PyO3.

// CORRECT: Error handling pattern
pub fn new_checked(period: usize) -> anyhow::Result<Self> {
    if period == 0 {
        anyhow::bail!("Period must be positive, was {period}");
    }
    Ok(Self { period, ..Default::default() })
}

pub fn new(period: usize) -> Self {
    Self::new_checked(period).expect(FAILED)
}

// CORRECT: Fully qualify anyhow and tokio
anyhow::bail!("Error message");
anyhow::Result<T>
tokio::spawn(async move { ... });
```

**Red flags:**
- Missing copyright header
- Using `Err(anyhow::anyhow!(...))` instead of `anyhow::bail!`
- Not importing FAILED constant for `.expect()`
- Using `HashMap` instead of `AHashMap` for non-security-critical code
- Missing module-level documentation

### FFI Memory Safety

```rust
// CORRECT: Box-backed API wrapper
#[repr(C)]
pub struct MyType_API(Box<MyType>);

// CORRECT: Constructor with matching drop
#[unsafe(no_mangle)]
pub extern "C" fn mytype_new(...) -> MyType_API {
    abort_on_panic(|| {
        MyType_API(Box::new(MyType::new(...)))
    })
}

#[unsafe(no_mangle)]
pub extern "C" fn mytype_drop(obj: MyType_API) {
    drop(obj);  // Box frees memory
}

// CORRECT: abort_on_panic wrapper for all FFI functions
#[unsafe(no_mangle)]
pub extern "C" fn mytype_process(obj: &mut MyType_API, data: f64) {
    abort_on_panic(|| {
        obj.0.process(data);
    })
}
```

**Red flags:**
- Missing `abort_on_panic` wrapper (panics across FFI are UB)
- Constructor without matching drop function
- Not using `#[repr(C)]` on FFI types
- Missing `#[unsafe(no_mangle)]` on exported functions
- Using generic `cvec_drop` (removed - use type-specific drops)

### CVec Memory Contract

```rust
// CORRECT: Type-specific drop for CVec
#[unsafe(no_mangle)]
pub extern "C" fn vec_drop_my_items(v: CVec) {
    let CVec { ptr, len, cap } = v;
    // SAFETY: CVec was created from Vec<MyItem>::into()
    let _ = unsafe {
        Vec::from_raw_parts(ptr as *mut MyItem, len, cap)
    };
    // Vec drops and frees memory
}
```

**CVec lifecycle:**
1. Rust builds `Vec<T>` and converts with `into()` (leaks memory)
2. Foreign code uses data (DO NOT modify ptr/len/cap)
3. Foreign code calls type-specific drop EXACTLY ONCE

**Red flags:**
- No matching drop function for CVec types
- Modifying CVec fields in foreign code
- Calling drop multiple times
- Using generic drop for non-u8 element types

### PyO3 Bindings

```rust
// CORRECT: Naming convention for PyO3 functions
#[pyo3(name = "do_something")]
pub fn py_do_something() -> PyResult<()> { ... }

// CORRECT: Python memory management
struct Config {
    handler: Option<PyObject>,  // No Arc wrapper
}

impl Clone for Config {
    fn clone(&self) -> Self {
        Self {
            handler: self.handler.as_ref().map(clone_py_object),
        }
    }
}

// WRONG: Arc wrapper causes reference cycles
handler: Option<Arc<PyObject>>,  // Memory leak!
```

**Red flags:**
- `Arc<PyObject>` anywhere (causes reference cycles)
- `#[derive(Clone)]` on structs with PyObject (use manual Clone)
- Function not prefixed with `py_` in Rust
- Missing `#[pyo3(name = "...")]` for clean Python API

### Rust/FFI Checklist

- [ ] Copyright header present
- [ ] Module documentation with feature flags
- [ ] `new_checked()` + `new()` constructor pattern
- [ ] `anyhow::bail!` for early returns
- [ ] `FAILED` constant in `.expect()` calls
- [ ] `AHashMap`/`AHashSet` for non-security collections
- [ ] `abort_on_panic` on all FFI functions
- [ ] Matching drop for every constructor
- [ ] Type-specific CVec drops
- [ ] No `Arc<PyObject>` (use plain `PyObject` with `clone_py_object`)
- [ ] `py_*` prefix on Rust function names
- [ ] SAFETY comments on all unsafe blocks
- [ ] `#[repr(C)]` on FFI types

## 7. Benchmarking Review

### Benchmark Structure

```rust
// CORRECT: Criterion benchmark structure
use std::hint::black_box;
use criterion::{Criterion, criterion_group, criterion_main};

fn bench_my_algo(c: &mut Criterion) {
    // Setup OUTSIDE timing loop
    let data = prepare_expensive_data();

    c.bench_function("my_algo", |b| {
        b.iter(|| my_algo(black_box(&data)));
    });
}

criterion_group!(benches, bench_my_algo);
criterion_main!(benches);

// CORRECT: iai micro-benchmark
fn bench_fast_operation() -> i64 {
    let a = black_box(123);
    let b = black_box(456);
    a + b
}

iai::main!(bench_fast_operation);
```

**Red flags:**
- Expensive setup inside `b.iter()` loop
- Missing `black_box` wrappers
- No `harness = false` in Cargo.toml
- Mixing Criterion and iai in same file

### Benchmark File Organization

```
crates/<crate_name>/
└── benches/
    ├── foo_criterion.rs   # Wall-clock benchmarks
    └── foo_iai.rs         # Instruction count benchmarks
```

```toml
# Cargo.toml
[[bench]]
name = "foo_criterion"
path = "benches/foo_criterion.rs"
harness = false
```

### Performance Profiling

```bash
# Run benchmarks
cargo bench -p nautilus-core --bench time

# Generate flamegraph (Linux)
cargo flamegraph --bench matching -p nautilus-common --profile bench

# Generate flamegraph (macOS - requires sudo)
sudo cargo flamegraph --bench matching -p nautilus-common --profile bench
```

**When to add benchmarks:**
- New hot-path code (called per tick/bar)
- Changes to matching engine
- Changes to order book processing
- New indicators or calculations
- FFI boundary functions

### Performance Checklist

- [ ] Criterion for end-to-end scenarios (> 100ns)
- [ ] iai for micro-benchmarks (exact instruction counts)
- [ ] Setup outside timing loops
- [ ] `black_box` on inputs and outputs
- [ ] `harness = false` in Cargo.toml
- [ ] Benchmarks in `benches/` directory
- [ ] Flamegraph generated for optimization work
- [ ] Before/after comparison documented

## Adapter-Specific Review

When reviewing adapter implementations, additionally validate against:

- `references/developer_guide/adapters.md` — adapter development spec (if available)
- `references/developer_guide/spec_data_testing.md` — data test matrix (TC-D01 to TC-D72)
- `references/developer_guide/spec_exec_testing.md` — execution test matrix (TC-E01+)

### Data Client Review Checklist

- [ ] All TC-D test cases from spec_data_testing.md addressed
- [ ] Instrument provider loads and normalizes correctly
- [ ] WebSocket reconnection handled
- [ ] Rate limiting implemented per venue spec

### Execution Client Review Checklist

- [ ] All TC-E test cases from spec_exec_testing.md addressed
- [ ] Order reconciliation on connect
- [ ] All supported order types tested
- [ ] Error/rejection handling for unsupported operations

## Domain Skill Handoff

For deeper review of specific domains:

- Adapter internals → **REQUIRED SUB-SKILL:** Use nautilus-dev:nt-adapter-dev
- Core type changes → **REQUIRED SUB-SKILL:** Use nautilus-dev:nt-core-dev
- Persistence changes → **REQUIRED SUB-SKILL:** Use nautilus-dev:nt-persistence-dev
- Backtest engine changes → **REQUIRED SUB-SKILL:** Use nautilus-dev:nt-backtest-dev

## References

For detailed standards (relative to this skill folder):
- `references/developer_guide/coding_standards.md`
- `references/developer_guide/testing.md`
- `references/developer_guide/rust.md` - Rust style conventions
- `references/developer_guide/python.md` - Python style conventions
- `references/developer_guide/ffi.md` - FFI memory contract
- `references/developer_guide/benchmarking.md` - Benchmarking guide
- `references/developer_guide/adapters.md` - Adapter development spec
- `references/developer_guide/spec_data_testing.md` - Data test matrix
- `references/developer_guide/spec_exec_testing.md` - Execution test matrix
- `references/concepts/backtesting.md`
- `references/concepts/live.md` - Live trading configuration
