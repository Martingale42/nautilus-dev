---
name: nt-analysis-dev
description: "Use when building NT analysis tools: portfolio statistics, backtest reporting, tearsheets, visualization, or custom performance metrics. Guides source exploration for the analysis layer."
---

# NT Analysis Development

## Overview

Build and extend NautilusTrader's analysis layer: PortfolioStatistic (custom performance metrics), ReportProvider (DataFrame generation from trading data), Portfolio (position/PnL tracking hub), and visualization (Plotly tearsheets for backtest results).

## Exploration Sequence

1. **Read bundled references/** — concept docs for reports/portfolio/visualization, API reference for class signatures
2. **Check cached/** — look for annotated excerpts from previous exploration sessions
3. **Explore NT source** — ask user: "Where is your local NautilusTrader repo?" If no local path, browse via `gh api repos/nautechsystems/nautilus_trader/contents/<path>`
4. **context7** — supplementary docs if gaps remain

## Concept Docs

- `references/concepts/reports.md` — ReportProvider, generating DataFrames from orders/fills/positions, PnL accounting, multi-currency handling
- `references/concepts/portfolio.md` — Portfolio hub, position tracking across strategies, currency conversion, built-in and custom statistics
- `references/concepts/visualization.md` — Plotly tearsheets, configurable charts, themes, custom chart registration, offline analysis

## API Reference

- `references/api_reference/analysis.md` — PortfolioStatistic, PortfolioAnalyzer, ReportProvider APIs
- `references/api_reference/portfolio.md` — Portfolio class, position queries, PnL calculations

## Bundled Source Reference

The full analysis module source is bundled for direct study:

**Python** (`references/python/analysis/`):
- `statistic.py` — `PortfolioStatistic` base class — study this first to understand the interface
- `analyzer.py` — `PortfolioAnalyzer` — aggregates statistics, generates reports
- `reporter.py` — `ReportProvider` — DataFrame generation from orders/fills/positions
- `tearsheet.py` — Plotly tearsheet rendering
- `config.py` — analysis configuration
- `themes.py` — tearsheet themes

**Rust** (`references/rust/analysis/`):
- `src/statistic.rs` — Rust `PortfolioStatistic` trait definition
- `src/analyzer.rs` — Rust `PortfolioAnalyzer` implementation
- `src/statistics/` — all built-in statistics (sharpe, sortino, max_drawdown, etc.) — study any one to see the pattern for building new ones
- `src/python/` — PyO3 bindings exposing Rust statistics to Python

**Reading order for building a custom statistic:**
1. `src/statistic.rs` — understand the trait
2. `src/statistics/sharpe_ratio.rs` — study one concrete implementation
3. `src/python/statistics/sharpe_ratio.rs` — see the PyO3 binding pattern
4. `python/analysis/statistic.py` — see the Python-side base class

## Source Entry Points

For deeper exploration beyond bundled references (local or via GitHub):

- `nautilus_trader/portfolio/` — Python-side Portfolio class (not bundled — explore live)

## Key Types

Find and understand these before implementing:

- `PortfolioStatistic` — base class for custom performance metrics
- `PortfolioAnalyzer` — aggregates statistics, generates analysis reports
- `ReportProvider` — generates pandas DataFrames from trading data (orders, fills, positions, accounts)
- `Portfolio` — central hub for tracking positions, PnL, exposure across all strategies

## Patterns to Study

- **Custom PortfolioStatistic:** Compare any two statistics in `references/rust/analysis/src/statistics/` — they all follow the same trait impl pattern. Then compare with their PyO3 bindings in `src/python/statistics/`
- **ReportProvider usage:** Read `references/python/analysis/reporter.py` for how backtest results generate order/fill/position reports as DataFrames
- **Tearsheet rendering:** Read `references/python/analysis/tearsheet.py` for how Plotly charts are composed from analysis data
- **Multi-currency PnL:** Explore `nautilus_trader/portfolio/` (live) for how Portfolio handles positions across different currencies

## Relationships

- **Depends on:** nt-core-dev for position, order, and event types
- **Used by:** nt-backtest-dev for post-backtest analysis
- **See also:** nt-strategy-dev for strategies that generate the trading data being analyzed

## Known Gotchas

- PortfolioStatistic must handle empty order/position lists gracefully
- Currency conversion requires exchange rates in the cache — may not be available for all pairs
- Tearsheet visualization requires Plotly and related dependencies
- Custom statistics should be deterministic — same input always produces same output
- ReportProvider generates DataFrames lazily — large backtests may need pagination

## Cached Knowledge

See `cached/` for annotated source excerpts from previous exploration sessions.
