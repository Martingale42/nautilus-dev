---
name: nt-kernel-dev
description: "Use when working with NT Kernel, Engine, Controller, system boot sequence, component registration, or infrastructure (clock, logging, cache wiring). Guides source exploration for the system layer."
---

# NT Kernel Development

## Overview

Build and extend NautilusTrader's system infrastructure: NautilusKernel (the central coordinator), Controller (component lifecycle), Environment contexts (backtest/sandbox/live), and infrastructure services (clock, logging, cache, message bus wiring).

## Exploration Sequence

1. **Read bundled references/** — architecture docs for system design, API reference for Kernel/Controller APIs
2. **Check cached/** — look for annotated excerpts from previous exploration sessions
3. **Explore NT source** — ask user: "Where is your local NautilusTrader repo?" If no local path, browse via `gh api repos/nautechsystems/nautilus_trader/contents/<path>`
4. **context7** — supplementary docs if gaps remain

## Concept Docs

- `references/concepts/architecture.md` — system design philosophy, DDD, crash-only design, NautilusKernel, component state management, environment contexts
- `references/concepts/logging.md` — Rust-backed MPSC logging, tracing integration, log rotation, component filtering
- `references/concepts/cache.md` — in-memory state store, configuration, querying patterns

## Developer Guide

- `references/developer_guide/environment_setup.md` — development environment, Python/Rust toolchain, build processes, Docker services

## API Reference

- `references/api_reference/system.md` — NautilusKernel, Controller, system-level APIs
- `references/api_reference/core.md` — core types, utilities

## Source Entry Points

Explore these paths (local or via GitHub):

- `crates/system/` — NautilusKernel, Controller implementation
- `crates/common/` — Clock, Timer, Logger, Cache, MessageBus (infrastructure components)
- `crates/infrastructure/` — Redis, database backends, external service integrations
- `nautilus_trader/system/` — Python-side Kernel and Controller
- `nautilus_trader/live/` — LiveNode (Kernel configuration for live trading)
- `nautilus_trader/backtest/` — BacktestNode/BacktestEngine (Kernel configuration for backtesting)

## Key Types

Find and understand these before implementing:

- `NautilusKernel` — central coordinator, owns all engines and infrastructure
- `Controller` — manages component lifecycle (add, start, stop, dispose)
- `Environment` — enum: Backtest, Sandbox, Live
- `LiveNode` — configures Kernel for live trading with adapters
- `BacktestNode` — configures Kernel for backtesting with simulated exchange
- `TradingNodeConfig` / `BacktestRunConfig` — configuration objects for node setup

## Patterns to Study

- **Boot sequence:** Trace how LiveNode initializes: creates Kernel → registers engines → registers adapters → starts Controller
- **LiveNode vs BacktestNode:** How the same Kernel is configured differently for live vs backtest
- **Component registration:** How strategies, actors, and adapters register with the Kernel and receive clock/cache/msgbus
- **Environment contexts:** How the Environment enum affects behavior (e.g., live clock vs test clock)

## Relationships

- **Depends on:** nt-core-dev for message bus, clock, cache types
- **Used by:** nt-adapter-dev (adapters register with LiveNode), nt-backtest-dev (BacktestNode/Engine)
- **See also:** nt-strategy-dev for how strategies register with the Kernel

## Known Gotchas

- Components receive clock/cache/msgbus only AFTER registration — not in constructors
- LiveNode requires adapter factories to be registered before start
- BacktestEngine allows more manual control than BacktestNode but requires explicit wiring
- Logger initialization happens early — logging config must be set before Kernel creation
- Redis infrastructure is optional — Cache works in-memory by default

## Cached Knowledge

See `cached/` for annotated source excerpts from previous exploration sessions.
