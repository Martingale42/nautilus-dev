---
name: nt-implement
description: "Use when implementing nautilus_trader components. Provides real examples for Strategy, Actor, Indicator, Adapters, and custom models in both Python and Rust. Includes backtest, live, and sandbox examples."
---

# Nautilus Trader Implementation

## Overview

Implement nautilus_trader components using real examples from the NT codebase. This skill provides actual working examples (not templates) for all component types in both Python and Rust.

## When to Use

- After architecture is defined (via nt-architect)
- When implementing any Nautilus component
- When needing correct method signatures and patterns
- When implementing in Rust with PyO3 bindings

## Examples

### Python Examples

Located in `references/examples/`:

| Directory | Contents |
|-----------|----------|
| `backtest/` | Backtest examples: EMA cross, order book imbalance, grid MM, custom CSV loading, timers, bar aggregation, data catalog, portfolio, cache, indicators |
| `live/` | Live trading examples per adapter: binance, bybit, okx, databento, interactive_brokers, betfair, etc. |
| `sandbox/` | Sandbox/testnet examples for safe testing |
| `utils/` | Utility helpers (data provider) |
| `other/` | Debugging, minimal reproducible examples, state machine |

### Rust Examples

Located in `references/examples/rust/`:

| Directory | Contents |
|-----------|----------|
| `trading/` | Strategy examples: EMA cross, grid market maker |
| `common/` | Actor examples: greeks calculation actor |
| `backtest/` | Backtest examples: engine_ema_cross (low-level), node_ema_cross (high-level) |
| `adapters/` | Per-adapter node testers: data_tester, exec_tester for each adapter |

## Implementation Workflow

1. Start from architecture document (via nt-architect)
2. Find the closest example to your use case
3. Study the example — understand the pattern
4. Implement your component following the same patterns
5. Validate with nt-review

## API Reference

Full API reference in `references/api_reference/` for type signatures and class documentation.

## Domain Skill Handoff

If implementation requires NT internals knowledge:

- Building an adapter → **REQUIRED SUB-SKILL:** Use nautilus-dev:nt-adapter-dev
- Building in Rust → **REQUIRED SUB-SKILL:** Use nautilus-dev:nt-strategy-dev
- Custom persistence → **REQUIRED SUB-SKILL:** Use nautilus-dev:nt-persistence-dev
- Custom backtest behavior → **REQUIRED SUB-SKILL:** Use nautilus-dev:nt-backtest-dev
- Custom analysis/statistics → **REQUIRED SUB-SKILL:** Use nautilus-dev:nt-analysis-dev
