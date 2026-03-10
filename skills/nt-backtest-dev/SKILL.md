---
name: nt-backtest-dev
description: "Use when working with NT backtesting internals: SimulatedExchange, fill models, matching engine, time advancement, data replay, or backtest performance. Guides source exploration for the backtesting engine."
---

# NT Backtest Development

## Overview

Build and extend NautilusTrader's backtesting engine: SimulatedExchange (virtual venue), fill models (execution simulation), matching engine (order matching logic), time advancement (event-driven clock), and data replay (feeding historical data through the system).

## Exploration Sequence

1. **Read bundled references/** — backtesting concepts for engine architecture, API reference for configuration
2. **Check cached/** — look for annotated excerpts from previous exploration sessions
3. **Explore NT source** — ask user: "Where is your local NautilusTrader repo?" If no local path, browse via `gh api repos/nautechsystems/nautilus_trader/contents/<path>`
4. **context7** — supplementary docs if gaps remain

## Concept Docs

- `references/concepts/backtesting.md` — BacktestEngine vs BacktestNode, high-level vs low-level APIs, setup patterns, data handling, result analysis
- `references/concepts/order_book.md` — L1/L2/L3 order book, own order tracking, filtered views, binary market support

## Developer Guide

- `references/developer_guide/benchmarking.md` — Criterion (statistical) and iai (instruction counting) benchmarks, flamegraph generation

## API Reference

- `references/api_reference/backtest.md` — BacktestEngine, BacktestNode, SimulatedExchange, FillModel, FeeModel configuration

## Source Entry Points

Explore these paths (local or via GitHub):

- `crates/backtest/` — Rust backtesting engine, simulated exchange, matching engine
- `crates/backtest/examples/` — Rust backtest examples:
  - `engine_ema_cross.rs` — BacktestEngine (low-level) example
  - `node_ema_cross.rs` — BacktestNode (high-level) example
- `nautilus_trader/backtest/` — Python-side backtest engine, node, exchange

## Key Types

Find and understand these before implementing:

- `BacktestEngine` — low-level API: manual venue/data/strategy wiring, full control
- `BacktestNode` — high-level API: config-driven, automatic wiring
- `SimulatedExchange` — virtual venue that processes orders against market data
- `MatchingEngine` — order matching logic within SimulatedExchange
- `FillModel` — controls fill probability, slippage, queue position simulation
- `FeeModel` — calculates trading fees
- `OrderBook` — maintains simulated order book state

## Patterns to Study

- **BacktestEngine vs BacktestNode:** Compare `engine_ema_cross.rs` (manual wiring) vs `node_ema_cross.rs` (config-driven) — same result, different control levels
- **SimulatedExchange internals:** How orders are received, matched against book/quotes, and filled
- **Time advancement:** How the backtest clock advances event-by-event through historical data
- **Fill model customization:** How FillModel controls whether limit orders fill, queue position, slippage
- **Data replay:** How historical data is fed through DataEngine to strategies in timestamp order

## Relationships

- **Depends on:** nt-core-dev (data model, execution pipeline), nt-kernel-dev (Kernel configuration)
- **Uses:** nt-persistence-dev for loading data from catalog
- **See also:** nt-analysis-dev for post-backtest result analysis
- **See also:** nt-strategy-dev for building strategies to backtest

## Known Gotchas

- BacktestEngine requires explicit venue configuration (exchange name, account type, fees)
- FillModel defaults may not match real venue behavior — customize for realistic simulation
- Order book simulation requires L2/L3 data — L1 quotes use simplified matching
- Time advancement is deterministic — same data + same strategy = same results
- Large backtests benefit from Rust-side strategies for performance

## Cached Knowledge

See `cached/` for annotated source excerpts from previous exploration sessions.
