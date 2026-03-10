---
name: nt-strategy-dev
description: "Use when building NT Actors or Strategies in Python or Rust. Guides implementation patterns for trading logic, signal publishing, data subscriptions, and lifecycle management."
---

# NT Strategy Development

## Overview

Build Actors and Strategies in both Python and Rust. Actors handle data processing, model inference, and signal publishing without trading. Strategies extend Actor with order management capabilities. Both follow the same lifecycle and can be implemented in Python or Rust.

## Exploration Sequence

1. **Read bundled references/** — concept docs for Actor/Strategy patterns, API reference for method signatures
2. **Check cached/** — look for annotated excerpts from previous exploration sessions
3. **Explore NT source** — ask user: "Where is your local NautilusTrader repo?" If no local path, browse via `gh api repos/nautechsystems/nautilus_trader/contents/<path>`
4. **context7** — supplementary docs if gaps remain

## Concept Docs

Read these first:

- `references/concepts/strategies.md` — Strategy class, lifecycle (on_start/on_stop/on_bar), order submission, position management, configuration
- `references/concepts/actors.md` — Actor base class, data subscriptions (historical + real-time), event handlers, timers, signal publishing

## API Reference

- `references/api_reference/trading.md` — Strategy, Trader, StrategyConfig class APIs and method signatures

## Developer Guide

- `references/developer_guide/testing.md` — testing framework, pytest patterns, Rust test conventions, async testing helpers

## Source Entry Points

Explore these paths (local or via GitHub):

- `crates/trading/src/` — Rust Strategy and Trader implementation
- `crates/trading/src/examples/strategies/` — Rust example strategies:
  - `ema_cross.rs` — EMA crossover strategy in Rust
  - `grid_mm.rs` — Grid market maker strategy in Rust
- `crates/common/` — Actor base class in Rust
- `crates/common/examples/` — Rust actor examples:
  - `greeks_actor_example.rs` — Options greeks calculation actor
- `nautilus_trader/trading/` — Python Strategy and Trader
- `nautilus_trader/common/` — Python Actor base class

## Key Types

Find and understand these before implementing:

**Strategy lifecycle methods:**
- `on_start()` — initialize state, subscribe to data, request history
- `on_stop()` — cleanup, cancel orders, unsubscribe
- `on_reset()` — reset state for reuse
- `on_bar()`, `on_quote_tick()`, `on_trade_tick()` — data handlers
- `on_order_event()` — order lifecycle handlers

**Actor-specific:**
- `publish_data()` — publish custom data to message bus
- `publish_signal()` — publish named signals
- `subscribe_data()` — subscribe to custom data types

**Order management (Strategy only):**
- `submit_order()`, `cancel_order()`, `modify_order()`
- `OrderFactory` — create orders with proper identifiers
- Position management via `self.cache` and `self.portfolio`

**Configuration:**
- `StrategyConfig` / `ActorConfig` — typed configuration with `order_id_tag`, `oms_type`

## Patterns to Study

- **Python vs Rust Strategy:** Compare `examples/backtest/` Python strategies with `crates/trading/src/examples/strategies/ema_cross.rs` — same logic, different language
- **Actor vs Strategy:** Compare Actor (publish signals, no orders) vs Strategy (receive signals, manage orders)
- **Multi-timeframe:** How strategies subscribe to multiple bar types and synchronize
- **Model inference Actor:** Pattern for loading ML models and publishing predictions as custom data

## Relationships

- **Depends on:** nt-core-dev for data model, message bus, order types
- **Used by:** nt-implement for strategy/actor templates
- **See also:** nt-backtest-dev for testing strategies in backtest
- **See also:** nt-analysis-dev for analyzing strategy performance

## Known Gotchas

- `Clock`, `Logger`, `Cache` are NOT available in `__init__` — use them only in `on_start()` and later
- Always call `super().__init__(config)` first in `__init__`
- Request historical data BEFORE subscribing to live data (warmup)
- Check `self.instrument` is not None before trading (may not be cached yet)
- In Rust: Strategy must be `Send + Sync` for multi-threaded runtime
- Order ID tags must be unique per strategy instance

## Cached Knowledge

See `cached/` for annotated source excerpts from previous exploration sessions.
