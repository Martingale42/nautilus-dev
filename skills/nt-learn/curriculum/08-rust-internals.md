# Stage 08: Rust Internals

## Goal

Understand NautilusTrader's Rust architecture, crate structure, and how Rust and Python interact via PyO3/FFI.

## Prerequisites

- Stage 07 complete (understand the full Python API)
- Basic Rust knowledge (ownership, traits, enums, modules)

## Why Rust?

NT's core is Rust for:
- **Performance** — zero-cost abstractions, no GC pauses
- **Safety** — ownership system prevents data races, null pointers, buffer overflows
- **Determinism** — predictable execution timing, critical for trading

The Python API is a thin wrapper over this Rust core.

## Crate Structure

The Rust workspace lives in `nautilus_core/` (or `crates/` in newer layouts). Key crates:

| Crate | Purpose |
|-------|---------|
| `core` | Primitives — UUID, DateTime, nanos timestamps |
| `model` | Domain model — instruments, orders, positions, data types, events |
| `common` | Shared utilities — clock, timer, logging, MessageBus, Cache |
| `data` | DataEngine, data clients, aggregation |
| `execution` | ExecutionEngine, execution clients, OMS logic |
| `trading` | Strategy, Actor traits and state machines |
| `backtest` | SimulatedExchange, MatchingEngine, fill models |
| `persistence` | Parquet/Arrow serialization, data catalog |
| `serialization` | msgpack/JSON encoding/decoding |
| `system` | NautilusKernel, boot sequence |
| `network` | HTTP/WebSocket clients |
| `infrastructure` | Redis integration, database backends |
| `adapters` | Exchange-specific adapter implementations |

### Dependency Flow

```
core → model → common → data / execution → trading → backtest / system
                  ↓
           persistence / serialization
                  ↓
            infrastructure
                  ↓
              adapters
```

Lower crates know nothing about higher ones. `core` and `model` are foundational — everything depends on them.

## Key Rust Patterns

### Domain Model (model crate)

The domain model uses Rust enums and structs extensively:

```rust
// Value types — fixed-point integers, not floats
pub struct Price {
    raw: i64,       // or i128 in high-precision mode
    precision: u8,
}

// Orders — enum with variants for each type
pub enum OrderAny {
    Market(MarketOrder),
    Limit(LimitOrder),
    StopMarket(StopMarketOrder),
    // ...
}

// Events — enum with variants
pub enum OrderEventAny {
    Submitted(OrderSubmitted),
    Accepted(OrderAccepted),
    Filled(OrderFilled),
    // ...
}
```

### Traits: Actor and Component

Two key traits define component behavior:

```rust
// Actor — message dispatch
pub trait Actor {
    fn handle(&mut self, msg: &dyn Any);
}

// Component — lifecycle management
pub trait Component {
    fn start(&mut self);
    fn stop(&mut self);
    fn reset(&mut self);
    fn dispose(&mut self);
    fn state(&self) -> ComponentState;
}
```

### ComponentState (Finite State Machine)

```
PRE_INITIALIZED → READY → STARTING → RUNNING → STOPPING → STOPPED → DISPOSED
                                         ↓
                                    DEGRADED ←→ RUNNING
                                         ↓
                                      FAULTED
```

### MessageBus

The Rust MessageBus uses handlers registered to topic strings:

```rust
// Publish
bus.publish(topic, &message);

// Subscribe
bus.subscribe(topic, handler);
```

All dispatch happens on the single main thread for deterministic ordering.

## PyO3 Bindings

### How Rust Becomes Python

NT uses PyO3 to expose Rust types to Python:

```rust
#[pyclass]
pub struct Price {
    raw: i64,
    precision: u8,
}

#[pymethods]
impl Price {
    #[new]
    fn new(value: f64, precision: u8) -> Self { ... }

    fn as_double(&self) -> f64 { ... }

    fn __repr__(&self) -> String { ... }
    fn __eq__(&self, other: &Self) -> bool { ... }
    fn __hash__(&self) -> u64 { ... }
}
```

The `#[pyclass]` attribute makes the struct available in Python. `#[pymethods]` exposes methods. Magic methods like `__repr__`, `__eq__`, `__hash__` make it feel native.

### FFI (Foreign Function Interface)

Some bindings use C FFI via Cython instead of direct PyO3:

```rust
// Rust side — C-compatible function
#[no_mangle]
pub extern "C" fn price_new(value: f64, precision: u8) -> Price { ... }
```

```cython
# Cython side — calls the C function
cdef extern from "nautilus.h":
    Price price_new(double value, uint8_t precision)
```

This dual-path (PyO3 + Cython/FFI) exists for historical reasons. Newer code tends toward direct PyO3.

### Navigating the Bindings

To trace a Python class to its Rust implementation:

1. Find the Python import: `from nautilus_trader.model.objects import Price`
2. Look for the Rust source: `nautilus_core/model/src/types/price.rs`
3. The `#[pyclass]` and `#[pymethods]` blocks show what's exposed

## Exploring the Source

### Recommended Exploration Order

1. **`model/src/types/`** — Price, Quantity, Money (simplest, self-contained)
2. **`model/src/identifiers/`** — InstrumentId, Venue, Symbol (simple newtype wrappers)
3. **`model/src/data/`** — Bar, QuoteTick, TradeTick (data structures you already know from Python)
4. **`model/src/orders/`** — Order types, state machine, validation
5. **`common/src/cache/`** — Cache implementation
6. **`common/src/msgbus/`** — MessageBus implementation
7. **`backtest/src/`** — SimulatedExchange, MatchingEngine (if interested in fill simulation)

### Key Files to Read

| File | What You'll Learn |
|------|------------------|
| `model/src/types/price.rs` | Fixed-point arithmetic, precision handling |
| `model/src/orders/market.rs` | Order struct, creation, validation |
| `model/src/events/order/filled.rs` | Event structure, what data fills carry |
| `common/src/msgbus/mod.rs` | How pub/sub works internally |
| `backtest/src/matching_engine/mod.rs` | How orders get matched against book data |

## Build and Test

```bash
# Build Rust only (debug)
make build-debug

# Run Rust tests
make cargo-test

# Run a specific crate's tests
cd nautilus_core
cargo test -p nautilus-model

# Run with output
cargo test -p nautilus-model -- --nocapture
```

## Exercises

1. **Trace a type**: Find `Price` in the Python API, then locate its Rust implementation. Read the `new()` constructor and `as_double()` method.

2. **Read an order**: Open `model/src/orders/market.rs`. What fields does a MarketOrder have? How does it validate on creation?

3. **Explore the MatchingEngine**: Open `backtest/src/matching_engine/`. How does it process incoming bars vs ticks?

4. **Find a PyO3 binding**: Locate a `#[pyclass]` struct and trace how it appears in the Python test suite.

## Checkpoint

You're ready for Stage 09 when:
- [ ] You can navigate the crate structure and find relevant source files
- [ ] You understand how PyO3 `#[pyclass]` and `#[pymethods]` expose Rust to Python
- [ ] You can build and test individual Rust crates
- [ ] You've read at least 3 Rust source files and understand their structure
- [ ] You know the dependency flow between crates
