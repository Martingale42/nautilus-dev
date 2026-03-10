---
name: nt-core-dev
description: "Use when working with NT core internals: data model, message bus, execution pipeline, order lifecycle, value types, or FFI bindings. Guides source exploration for foundational NT components."
---

# NT Core Development

## Overview

Build and extend NautilusTrader's foundational components: the data model (instruments, orders, positions, events), message bus (pub/sub, request/response), execution pipeline (Strategy → ExecutionEngine → Client), value types (Price, Quantity, Money), and Rust↔Python FFI bindings.

## Exploration Sequence

1. **Read bundled references/** — concept docs first for understanding, then API reference for type signatures
2. **Check cached/** — look for annotated excerpts from previous exploration sessions
3. **Explore NT source** — ask user: "Where is your local NautilusTrader repo?" If no local path, browse via `gh api repos/nautechsystems/nautilus_trader/contents/<path>`
4. **context7** — supplementary docs if gaps remain

## Concept Docs

Read these first for conceptual understanding:

- `references/concepts/architecture.md` — system design, DDD, core components (Kernel, MessageBus, Cache, engines)
- `references/concepts/overview.md` — platform features, supported asset classes, key concepts
- `references/concepts/message_bus.md` — pub/sub, request/response, point-to-point messaging, Redis streaming
- `references/concepts/execution.md` — order flow: Strategy → OrderEmulator → ExecAlgorithm → RiskEngine → ExecutionEngine → Client
- `references/concepts/orders.md` — all order types, lifecycle, execution instructions, emulated orders
- `references/concepts/positions.md` — position lifecycle, PnL calculations, OMS types
- `references/concepts/instruments.md` — instrument types, symbology, precision, fee models
- `references/concepts/data.md` — built-in data types, order book levels, bar aggregations
- `references/concepts/value_types.md` — Price, Quantity, Money, fixed-point arithmetic
- `references/concepts/cache.md` — in-memory state store, querying patterns

## API Reference

For type signatures and class APIs:

- `references/api_reference/core.md` — core types and utilities
- `references/api_reference/common.md` — common base classes
- `references/api_reference/execution.md` — ExecutionEngine, ExecutionClient
- `references/api_reference/data.md` — DataEngine, DataClient
- `references/api_reference/trading.md` — Strategy, Trader
- `references/api_reference/model/` — all model types (identifiers, instruments, orders, positions, events, data, book)

## Developer Guide

For coding standards and FFI patterns:

- `references/developer_guide/coding_standards.md` — style rules, naming, formatting
- `references/developer_guide/rust.md` — Rust conventions, Cargo, async patterns
- `references/developer_guide/python.md` — Python style, type hints, docstrings
- `references/developer_guide/ffi.md` — memory safety, CVec, Capsules, ownership rules

## Source Entry Points

Explore these paths (local or via GitHub):

- `crates/core/` — core types, UUID, timestamps, nanos, serialization traits
- `crates/model/` — all domain model types (instruments, orders, positions, events, data, identifiers)
- `crates/common/` — message bus, clock, timer, logging, cache, common actors
- `crates/execution/` — execution engine, execution client traits
- `crates/data/` — data engine, data client traits, aggregation
- `nautilus_trader/core/` — Python-side core wrappers
- `nautilus_trader/model/` — Python-side model wrappers
- `nautilus_trader/common/` — Python-side common components
- `nautilus_trader/execution/` — Python-side execution
- `nautilus_trader/data/` — Python-side data

## Key Types

Find and understand these before implementing:

**Rust crates/model:**
- `InstrumentAny` — enum over all instrument types
- `OrderAny` — enum over all order types
- `Position` — position state and PnL tracking
- `OrderBook` — L1/L2/L3 order book
- `QuoteTick`, `TradeTick`, `Bar` — market data types
- `OrderEvent` variants — order lifecycle events
- `Price`, `Quantity`, `Money` — fixed-point value types

**Rust crates/common:**
- `MessageBus` — central pub/sub + request/response hub
- `Clock` / `LiveClock` / `TestClock` — time management
- `Cache` — in-memory state store

**Rust crates/execution:**
- `ExecutionEngine` — processes execution commands and events
- `ExecutionClient` trait — interface for venue connectivity

## Patterns to Study

- **Order lifecycle:** Trace how a `SubmitOrder` command flows from Strategy → RiskEngine → ExecutionEngine → ExecutionClient → venue, and how `OrderFilled` events flow back
- **Message bus pub/sub:** Compare topic-based publishing vs Actor data publishing vs Signal publishing
- **FFI bindings:** Study how any model type (e.g., `QuoteTick`) is exposed via PyO3 — look at the `#[pymethods]` impl blocks

## Relationships

- **Used by:** All other domain skills depend on core types and patterns
- **See also:** `nt-kernel-dev` for how core components are wired together at boot

## Known Gotchas

- Value types (`Price`, `Quantity`, `Money`) use fixed-point arithmetic — don't use `f64` directly
- `Clock`, `Logger`, `Cache` are not available in `__init__` — only after component registration
- Message bus topics are strings with dot-separated hierarchy — use existing patterns
- FFI types have strict ownership rules — read `ffi.md` before passing types across boundary

## Cached Knowledge

See `cached/` for annotated source excerpts from previous exploration sessions. Save useful findings here for future sessions.
