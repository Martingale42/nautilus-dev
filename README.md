# Nautilus Trader Development Skills

Skills for building with and building on NautilusTrader.

## Architecture

Domain skills provide NT-specific knowledge to generic workflow skills:

```
┌─────────────────────────────────────────────────┐
│              Generic Workflow Skills             │
│  brainstorming → writing-plans → executing-plans │
│  code-review, pragmatic-testing                  │
└──────────────────────┬──────────────────────────┘
                       │ domain knowledge injected by
┌──────────────────────▼──────────────────────────┐
│              NT Domain Skills (7)                │
│  nt-trading   nt-signals   nt-data              │
│  nt-backtest  nt-live      nt-adapters          │
│  nt-model                                       │
└──────────────────────┬──────────────────────────┘
                       │ separate concern
┌──────────────────────▼──────────────────────────┐
│              NT Learning (1)                     │
│  nt-learn (structured curriculum)               │
└─────────────────────────────────────────────────┘
```

Each domain skill covers four dimensions: Python usage, Python extension, Rust usage, Rust extension.

## Setup

For best results, clone NautilusTrader locally:

```bash
git clone https://github.com/nautechsystems/nautilus_trader.git
```

When a domain skill activates, it will ask for your local NT path.
If you don't have a local clone, it falls back to browsing the official
repo on GitHub.

## Skills

### Domain Skills

| Skill | Trigger | Covers |
|-------|---------|--------|
| nt-trading | Strategy logic, order execution, risk management | `trading/`, `execution/`, `risk/`, `accounting/`, `portfolio/` |
| nt-signals | Indicators, signal generation, bar aggregation, analysis | `indicators/`, `analysis/`, `model/data`, `model/book` |
| nt-data | Data pipelines, catalog, serialization, cache | `data/`, `persistence/`, `serialization/`, `cache/` |
| nt-backtest | Backtesting engine, fill models, simulated exchange | `backtest/`, `execution/matching_core` |
| nt-live | Live trading nodes, system boot, deployment | `live/`, `system/`, `config/`, `common/`, `core/` |
| nt-adapters | Exchange/data adapters, venue integration | `adapters/*` (16 venues), `network/` |
| nt-model | Domain types, instruments, identifiers, value types | `model/` (instruments, identifiers, types, enums) |

### Learning Pathway

| Skill | Purpose |
|-------|---------|
| nt-learn | Structured curriculum from beginner to NT developer |

### Multi-Skill Invocation

Some tasks need multiple skills. One is **primary** (loads fully), others are **supporting** (SKILL.md only):

| User intent | Primary | Supporting |
|-------------|---------|------------|
| Build an EMA crossover strategy | nt-trading | nt-signals |
| Configure live node for Binance | nt-live | nt-adapters |
| Load data for my backtest | nt-backtest | nt-data |
| Build indicator that reads order book | nt-signals | nt-model |

## Design Reference

See `docs/plans/2026-03-11-nautilus-skills-v3-design.md` for the full v3 architecture design.
