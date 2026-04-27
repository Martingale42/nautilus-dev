# NT Strategy Architecture Patterns

A cross-skill reference for building production-grade NautilusTrader
strategies in Rust. Where the per-skill SKILL.md files cover individual
APIs, this document covers **how the pieces fit together** across the
strategy lifecycle: ingest → backtest → live.

The patterns below are abstracted from real strategies that ship and run.
They are not theoretical recommendations — each one has been load-bearing
in production code.

## The strategy lifecycle

A real NT strategy lives in three phases:

```
┌──────────┐   ┌──────────┐   ┌──────────┐
│  Ingest  │ → │ Backtest │ → │   Live   │
│ (offline)│   │ (offline)│   │ (online) │
└──────────┘   └──────────┘   └──────────┘
     │              │              │
     ↓              ↓              ↓
   Catalog     Reports +     Live PnL +
   on disk     PnL series    monitoring
```

Each phase has different inputs, outputs, and failure modes. The
**strategy logic itself is identical** across backtest and live — same
struct, same handlers, same arithmetic. Only the host engine differs.

## 1. Three-binary repo layout

The single most important architectural decision for a real strategy:
**three binaries, one strategy.**

```
strategies/my-strat/
├── Cargo.toml
├── src/
│   ├── lib.rs              ← re-exports the strategy + its modules
│   ├── strategy.rs         ← the NT-facing struct (used by both backtest and live)
│   ├── model/              ← pure math (closed-form formulas, indicators)
│   ├── calibration/        ← pure parameter estimation
│   ├── risk/               ← pure state machines (inventory, breakers)
│   ├── quoting/            ← pure planners (Submit/Amend/Cancel decisions)
│   ├── ingest/             ← shared decode helpers (used by bin/ingest.rs only)
│   └── reporting.rs        ← Parquet writers (used by bin/backtest.rs and live.rs)
├── bin/
│   ├── ingest.rs           ← venue archive → ParquetDataCatalog
│   ├── backtest.rs         ← BacktestEngine + strategy
│   └── live.rs             ← LiveNode + strategy + adapter config
├── configs/
│   ├── default.toml        ← backtest config
│   └── live.toml           ← live config (testnet by default)
├── tests/
│   ├── model_tests.rs
│   ├── calibration_tests.rs
│   ├── ingest_tests.rs     ← integration with fixture data
│   └── backtest_smoke.rs   ← 1-day backtest end-to-end
└── reports/                ← gitignored; output target
```

```toml
# Cargo.toml
[package]
name = "my-strat"
edition = "2024"

[[bin]]
name = "my-strat-ingest"
path = "bin/ingest.rs"

[[bin]]
name = "my-strat-backtest"
path = "bin/backtest.rs"

[[bin]]
name = "my-strat-live"
path = "bin/live.rs"
```

**Why three binaries:**

- **Ingest** is offline, often slow, often run once and forgotten. It
  needs vendor-specific decoders that have nothing to do with the
  strategy. Putting it in the same binary as backtest pollutes
  dependencies.
- **Backtest** needs `BacktestEngine`, `BacktestNode`, `streaming` feature.
- **Live** needs `LiveNode`, the venue adapter, async runtime, env vars.

A single binary accumulates feature flags and dependencies it doesn't
need at any given time. Three binaries keep each one minimal.

**The strategy struct is shared.** `bin/backtest.rs` and `bin/live.rs`
both `use my_strat::strategy::MyStrategy;` — no `#[cfg(backtest)]`
branches inside the strategy itself.

## 2. Onion architecture

Push everything that doesn't need NT into pure functions or state
machines. The Strategy struct is the only thing that touches NT.

```
┌────────────────────────────────────────────────┐
│  bin/{ingest,backtest,live}.rs                 │  ← NT engine setup
├────────────────────────────────────────────────┤
│  src/strategy.rs                               │  ← NT IO (subscribe, submit_order)
├────────────────────────────────────────────────┤
│  src/quoting/manager.rs                        │  ← pure planner
│  src/risk/policy.rs                            │  ← pure state machine
├────────────────────────────────────────────────┤
│  src/model/glft.rs                             │  ← pure math
│  src/calibration/{sigma,intensity}.rs          │  ← pure estimators
└────────────────────────────────────────────────┘
       Each layer has zero NT dependencies.
       Test each in isolation with cargo test -p my-strat.
```

**Test cost** scales linearly with module count, not with the cube of
NT engine state. A unit test for `model::glft::optimal_quotes` constructs
a `GlftParams` and checks invariants — no engine, no fixtures, no clock.

The Strategy struct becomes a thin glue layer:

```rust
fn on_quote(&mut self, quote: &QuoteTick) -> anyhow::Result<()> {
    // 1. Update local mid
    let mid = 0.5 * (quote.bid_price.as_f64() + quote.ask_price.as_f64());
    self.last_mid = Some(mid);

    // 2. Read pure params snapshot
    let Some(params) = self.params else { return Ok(()); };

    // 3. Pure: model computes target
    let target = optimal_quotes(mid, self.inventory, &params, self.tick_size)?;

    // 4. Pure: risk gate decides allowed sides
    let sides = self.risk.allowed_sides(self.inventory);

    // 5. Pure: planner emits actions
    let actions = self.quote_manager.plan(&target, sides, self.cfg.quote_size.as_f64());

    // 6. Side-effect only: dispatch via NT
    for action in actions {
        match action {
            QuoteAction::Submit { side, price, qty } => self.submit_post_only(...)?,
            QuoteAction::Amend  { ... } => self.amend_working(...)?,
            QuoteAction::Cancel { ... } => self.cancel_working(...)?,
            QuoteAction::NoChange { .. } => {}
        }
    }
    Ok(())
}
```

Every step except the last is pure and tested separately.

## 3. Data flow across the lifecycle

```
                   ┌────────────────┐
   Vendor archive  │ bin/ingest.rs  │
   (NDJSON, CSV)→  │ ─ decode       │ → ParquetDataCatalog
                   │ ─ validate L1  │   (instruments + ticks)
                   └────────────────┘
                         │
        ┌────────────────┴───────────┐
        ↓                            ↓
   ┌──────────────┐         ┌──────────────┐
   │ bin/backtest │         │  bin/live    │
   │  ─ catalog   │         │  ─ adapter   │
   │  ─ engine    │         │  ─ live node │
   │  ─ strategy  │         │  ─ strategy  │
   └──────────────┘         └──────────────┘
         │                         │
         ↓                         ↓
   reports/{run_id}/        reports/{run_id}/
   ├─ fills.parquet         ├─ fills.parquet  (also live writes these!)
   ├─ quotes.parquet        ├─ quotes.parquet
   ├─ params.parquet        ├─ params.parquet
   └─ equity.parquet        └─ equity.parquet
         │                         │
         └────────────┬────────────┘
                      ↓
              scripts/viz.ipynb
              (compare backtest vs live)
```

**Reports schema is identical** between backtest and live. Same Parquet
columns, same notebook reads both. This lets you visually overlay
backtest predictions vs live executions on the same axes — the most
honest sanity check available.

## 4. Atomic state transitions

NT processes events serially per actor (single-threaded message bus
with workstealing across actors). Within one actor, you don't need
locks. But you do need **atomic transitions** — either the new
parameter set is fully visible or the old one is.

The simplest pattern:

```rust
// In calibration completion:
self.params = Some(new_params);  // single assignment — atomic from the actor's view.

// In hot path:
let Some(params) = self.params else { return Ok(()); };
// `params` is now a local f64-tuple snapshot. Even if the next event
// re-assigns self.params, our local is unchanged.
```

For cross-thread sharing (e.g. a Rust worker thread that publishes
parameters from outside the actor), use `arc_swap::ArcSwap<Option<T>>`.
But within a single actor's handlers, the simple swap is enough.

**The anti-pattern** is mutating individual fields:

```rust
// BAD
self.sigma = new_sigma;
some_callback();           // ← if this re-enters the actor, mid-update state is visible
self.k = new_k;
```

Always replace whole structs, never field-by-field.

## 5. Daily timer + hourly snapshot

NT's clock supports named timers that fire deterministically in
backtest and on a real wall clock in live. Use timers for periodic
work, not `if now > last_x` checks scattered across handlers.

```rust
const DAILY_RECAL: &str = "my_strat_daily_recal";
const HOURLY_SNAPSHOT: &str = "my_strat_hourly_snapshot";

fn on_start(&mut self) -> anyhow::Result<()> {
    let now_ns: u64 = self.core.clock().timestamp_ns().into();
    let next_midnight = next_utc_midnight_ns(now_ns);

    self.core.clock_mut().set_timer_ns(
        DAILY_RECAL, NS_PER_DAY,
        UnixNanos::from(next_midnight), None, None,
    )?;
    self.core.clock_mut().set_timer_ns(
        HOURLY_SNAPSHOT, NS_PER_HOUR,
        UnixNanos::from(now_ns + NS_PER_HOUR), None, None,
    )?;
    Ok(())
}

fn on_time_event(&mut self, event: &TimeEvent) -> anyhow::Result<()> {
    match event.name.as_str() {
        DAILY_RECAL => self.handle_daily_recal()?,
        HOURLY_SNAPSHOT => self.record_equity_snapshot(event.ts_event.into())?,
        _ => {}
    }
    Ok(())
}
```

**Why named timers, not interval checks**: timers fire on simulated
time in backtest, even if no market events arrive. An `if now > next`
check inside `on_quote` only fires when there's a quote — useless if
the market goes silent.

## 6. Failing fast vs falling back

A strategy that silently uses default parameters when calibration
fails is the worst kind of bug: it runs, it places orders, and the
PnL eventually reveals that the parameters were wrong all along.

**Default to fail-fast.** If calibration produces an `Err`, stop the
strategy:

```rust
match calibrate(...) {
    Ok(out) => self.apply_calibration(out.params, out.r_squared, intent),
    Err(e) => {
        log::error!("calibration failed: {e} — stopping strategy");
        self.stop();
    }
}
```

**Fall back only when the fallback is provably harmless.** "Keep
yesterday's params" is harmless. "Use hardcoded `σ = 1e-4`" is not —
that's pretending to do calibration.

The same principle applies to:
- Order rejects (don't retry blindly — log and let the next tick decide)
- Missing instruments (don't substitute defaults — fail with a clear message)
- Crossed L1 ticks during ingest (don't write the partition — refuse)

## 7. Reporting that supports honest analysis

Backtest and live both produce four Parquet files per run:

| File | Row per | Columns |
|------|---------|---------|
| `fills.parquet` | OrderFilled event | ts, side, qty, price, mid_at_fill, inventory_after |
| `quotes.parquet` | re-quote decision | ts, mid, sigma, k, A, reservation, bid_px, ask_px, action, skip_reason |
| `params.parquet` | calibration epoch | ts, sigma, A, k, r2, rows_used, source (warmup\|daily\|live\|fallback) |
| `equity.parquet` | hourly snapshot | ts, mid, inventory, entry_avg, realized_pnl, unrealized_pnl, total_equity |

**Why all four:** Each answers a different question.
- `fills` → what got filled, when, at what price?
- `quotes` → were we quoting competitively or backed off (skip_reason)?
- `params` → are estimates stable or jumping per epoch?
- `equity` → what's the actual PnL trajectory at hourly resolution?

A backtest report without `params.parquet` is a blind PnL number — you
can't tell if the result was driven by good calibration or coincidence.

The Python notebook (`scripts/viz.ipynb`) loads any subset of these and
overlays. Same notebook works on backtest and live runs.

## 8. Cross-cutting troubleshooting

When something fails, the failure crosses skill boundaries. The
top-level diagnostic question is **which phase**:

| Symptom | Phase | First place to look |
|---------|-------|---------------------|
| Compile error | (any) | `nt-trading/references/guides/troubleshooting_rust.md` build errors |
| `query_*` returns empty | Backtest | Did ingest succeed? Are instruments written? |
| Strategy never quotes | Backtest or Live | Warmup completion — see `rust_patterns.md` §2 |
| Order rejected POST_ONLY_WOULD_CROSS | Live | Expected — see `troubleshooting_rust.md` |
| `realized_pnl == 0` despite fills | Backtest | Strategy didn't close on stop — `rust_patterns.md` §13 |
| Adapter panic at startup | Live | env var validation — `nt-live/SKILL.md` |
| `request_quotes` returns nothing | Backtest | First-day-as-warmup — `nt-backtest/SKILL.md` |
| Inventory exceeds q_max | (any) | Clamp inventory into model — `troubleshooting_rust.md` |
| Calibration silent | (any) | Fail-fast policy — `troubleshooting_rust.md` |

## 9. Skill loading guide for Claude

When you (Claude) are asked to build or modify a Rust strategy on NT,
load skills in this order:

1. **`nt-trading`** — primary, for strategy structure and order management.
2. **`nt-data`** — for catalog reads/writes and ingest pipelines.
3. **`nt-backtest`** — when the task involves a backtest run.
4. **`nt-live`** — when the task involves live deployment.
5. **`nt-adapters`** — when configuring a venue (Bybit, OKX, etc.).
6. **`nt-model`** — for instrument/precision/identifier specifics.
7. **`nt-signals`** — for indicators and signal generation.

For **any non-trivial task**, also read:
- `nt-trading/references/guides/rust_patterns.md` once at the start.
- `nt-trading/references/guides/troubleshooting_rust.md` when blocked.

For **architectural decisions** (new strategy, refactor, lifecycle
question), read this document (`docs/architecture_patterns.md`) first.

## 10. The strategy build sequence

A new Rust strategy from zero to running in a sensible order:

| Stage | Goal | Done when |
|-------|------|-----------|
| 0 | Workspace prep | All NT crates pinned to same version. `cargo check --workspace` green. |
| 1 | Scaffold | New crate added to workspace. Empty Strategy compiles. `cargo build -p my-strat`. |
| 2 | Ingest | NDJSON/CSV → catalog. `query_*` returns expected row counts. L1 invariants pass. |
| 3 | Pure modules | Math + calibration + risk gate. Unit tests at synthetic-data tolerance. |
| 4 | Strategy + Backtest | Fill model, reports, viz notebook. Backtest produces all four parquet files. |
| 5 | Live | LiveNode + adapter + env toggle. Testnet run ≥ 1h, no crash, fills written. |
| 6+ | Productionize | Queue-aware fill model, inventory-aware sizing, funding awareness, monitoring. |

Stages 0–5 are MVP. Every stage produces a green `cargo test`. If a
stage doesn't, fix it before moving on.

## See also

- [`skills/nt-trading/references/guides/rust_patterns.md`](../skills/nt-trading/references/guides/rust_patterns.md) — 13 strategy-side patterns with code.
- [`skills/nt-trading/references/guides/troubleshooting_rust.md`](../skills/nt-trading/references/guides/troubleshooting_rust.md) — diagnostic workflow + 12 specific failures.
- [`skills/nt-trading/SKILL.md`](../skills/nt-trading/SKILL.md) — strategy/actor primary reference.
- [`skills/nt-data/SKILL.md`](../skills/nt-data/SKILL.md) — catalog + ingest patterns.
- [`skills/nt-backtest/SKILL.md`](../skills/nt-backtest/SKILL.md) — engine + warmup window.
- [`skills/nt-live/SKILL.md`](../skills/nt-live/SKILL.md) — LiveNode + env toggle + graceful shutdown.
