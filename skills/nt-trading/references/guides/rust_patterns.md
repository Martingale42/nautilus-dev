# Rust Strategy Patterns

Patterns distilled from production Rust strategies on NT v1.226+. Each
pattern names a problem, a working solution, and the reason behind it.
Skip the patterns that don't apply to your strategy — these are not all
mandatory.

## 1. Onion architecture: pure modules + thin orchestrator

**Problem.** A strategy that mixes math, state machines, and NT IO becomes
impossible to test. Unit tests need an `Engine`, fixtures, and a clock —
overkill for verifying a formula.

**Pattern.** Push everything that doesn't need NT into pure functions or
state machines. The Strategy struct is the only thing that touches NT.

```
src/
├── model/      ← pure: (mid, q, params, tick) → quotes
├── calibration/← pure: (data) → params
├── risk/       ← pure state machine: (equity, q) → Sides
├── quoting/    ← pure planner: (target, working, sides) → Vec<Action>
└── strategy.rs ← only layer with side effects
```

Every internal module is a `cargo test -p <crate>` away from full coverage
without booting an engine. The Strategy file becomes a thin glue layer
that translates `Vec<QuoteAction>` into `submit_order` / `modify_order` /
`cancel_order` calls.

**Why this works.** NT's runtime model assumes the strategy is small and
stateless-ish. The pure layers can evolve independently of NT version
bumps.

## 2. Warmup via `request_quotes` + `on_historical_*`

**Problem.** Calibration needs N hours of history. The strategy doesn't
have it on first tick.

**Pattern.** In `on_start`, request the historical window. Buffer the
arrivals in `on_historical_quotes` / `on_historical_trades`. Run
calibration when **both** buffers have arrived.

```rust
fn on_start(&mut self) -> anyhow::Result<()> {
    self.subscribe_quotes(self.cfg.instrument_id, None, None);
    self.subscribe_trades(self.cfg.instrument_id, None, None);

    let now_ns: u64 = self.core.clock().timestamp_ns().into();
    let start = UnixNanos::from(now_ns - 24 * 3_600_000_000_000);
    let end = UnixNanos::from(now_ns);

    self.warmup_quotes = Some(Vec::new());
    self.warmup_trades = Some(Vec::new());

    self.request_quotes(self.cfg.instrument_id, Some(start), Some(end), None, None, None)?;
    self.request_trades(self.cfg.instrument_id, Some(start), Some(end), None, None, None)?;
    Ok(())
}

fn on_historical_quotes(&mut self, quotes: &[QuoteTick]) -> anyhow::Result<()> {
    if let Some(buf) = self.warmup_quotes.as_mut() {
        buf.extend_from_slice(quotes);
    }
    self.maybe_run_warmup_calibration();
    Ok(())
}

fn on_historical_trades(&mut self, trades: &[TradeTick]) -> anyhow::Result<()> {
    if let Some(buf) = self.warmup_trades.as_mut() {
        buf.extend_from_slice(trades);
    }
    self.maybe_run_warmup_calibration();
    Ok(())
}

fn maybe_run_warmup_calibration(&mut self) {
    let (Some(quotes), Some(trades)) = (self.warmup_quotes.as_ref(), self.warmup_trades.as_ref())
    else { return; };
    if quotes.is_empty() || trades.is_empty() { return; }
    // ... run calibration, atomic-swap params, free buffers ...
}
```

**Backtest gotcha.** If your backtest range starts at the catalog's
earliest data, `request_*` returns nothing because there's no history
older than the start. Maintain a rolling live-stream buffer
(`VecDeque<QuoteTick>`) capped at the calibration window as a fallback,
and run calibration on it once enough live data has accumulated.

## 3. Daily timer for re-calibration

**Problem.** Daily UTC-00:00 re-calibration with no drift over weeks.

**Pattern.** Schedule a repeating timer anchored on the next UTC midnight,
with `NS_PER_DAY` cadence:

```rust
pub const DAILY_RECAL_TIMER: &str = "as_mm_rs_daily_recal";

fn on_start(&mut self) -> anyhow::Result<()> {
    let now_ns: u64 = self.core.clock().timestamp_ns().into();
    let next_midnight = next_utc_midnight_ns(now_ns);
    self.core.clock_mut().set_timer_ns(
        DAILY_RECAL_TIMER,
        NS_PER_DAY,           // interval
        UnixNanos::from(next_midnight),  // start
        None,                 // stop_time (None = infinite)
        None,                 // callback (uses on_time_event)
    )?;
    Ok(())
}

fn on_time_event(&mut self, event: &TimeEvent) -> anyhow::Result<()> {
    if event.name.as_str() == DAILY_RECAL_TIMER {
        self.daily_recal_pending = true;
        // Refresh warmup buffers, re-request data, run calibration.
    }
    Ok(())
}
```

The clock is mocked in backtests, so timers fire deterministically at the
simulated UTC-00:00 with no real-time wait.

## 4. Atomic parameter swap

**Problem.** Calibration produces a new `(σ, A, k, q_max)`. The hot path
(`on_quote`) reads these every tick. A torn read mixing fields from two
different calibrations breaks invariants.

**Pattern A (single-threaded NT).** Replace the entire `Option<Params>` in
one assignment. Reads in `on_quote` snapshot to a local before use:

```rust
// Apply
self.params = Some(new_params);

// Hot path
let Some(params) = self.params else { return Ok(()); };
let target = optimal_quotes(mid, q, &params, self.tick_size)?;
```

Because NT processes events serially per actor, there is no torn-read
race. The `Option<Params>` swap is sufficient.

**Pattern B (cross-thread sharing).** If you need a Rust thread outside
the actor (e.g. a side calibration thread) to publish params, use
`ArcSwap<Option<Params>>`:

```rust
use arc_swap::ArcSwap;
use std::sync::Arc;

pub struct AsMmStrategy {
    params: Arc<ArcSwap<Option<GlftParams>>>,
}

// Calibration thread:
self.params.store(Arc::new(Some(new_params)));

// Hot path:
let snapshot = self.params.load_full();
let Some(params) = *snapshot else { return Ok(()); };
```

`ArcSwap::load_full` is lock-free; `store` is one atomic pointer swap.

## 5. Override block on `nautilus_strategy!`

**Problem.** You need to react to `OrderRejected`, `OrderFilled`,
`OrderCanceled`, etc. — but the default `Strategy` trait impl is no-op.

**Pattern.** Pass a block to the macro. The macro generates the trait
impl, you provide the bodies:

```rust
nautilus_strategy!(AsMmStrategy, {
    fn on_order_rejected(&mut self, event: OrderRejected) {
        let reason = event.reason.to_string();
        if reason.contains("POST_ONLY") {
            log::info!("post-only reject (expected): {reason}");
        } else {
            log::warn!("order rejected: {reason}");
        }
        // Clear tracked working state
        if let Some(w) = self.quote_manager.working_bid {
            if w.order_id == event.client_order_id {
                self.quote_manager.on_cancel(QuoteSide::Bid);
            }
        }
    }

    fn on_order_filled(&mut self, event: OrderFilled) {
        // delegate to a method that does the heavy lifting
        if let Err(e) = self.handle_fill(&event) {
            log::error!("handle_fill failed: {e}");
        }
    }

    fn on_order_canceled(&mut self, event: OrderCanceled) {
        // ...
    }
});
```

**Inside the block** you have `&mut self` and the event by value. Do not
re-define `core()` / `core_mut()` — the macro already generates them.

**Heavy logic** belongs in a method on the impl block, not inside the
macro:

```rust
impl AsMmStrategy {
    fn handle_fill(&mut self, event: &OrderFilled) -> anyhow::Result<()> {
        // 30-line position accounting / risk gate update / report write
        Ok(())
    }
}
```

This keeps the macro readable and lets `handle_fill` be unit tested
directly.

## 6. Three-binary pattern: ingest / backtest / live

**Problem.** A real strategy needs (a) a way to convert venue archives to
the catalog, (b) a way to backtest, (c) a way to run live. Stuffing all
three into one binary is hostile.

**Pattern.** Three small `bin/` files, one shared `src/strategy.rs`:

```
strategies/my-strat/
├── src/strategy.rs   ← AsMmStrategy — used by both backtest and live
├── bin/
│   ├── ingest.rs     ← venue archive → ParquetDataCatalog
│   ├── backtest.rs   ← BacktestEngine + AsMmStrategy
│   └── live.rs       ← LiveNode + AsMmStrategy + adapter config
└── Cargo.toml        ← [[bin]] entries for each
```

```toml
[[bin]]
name = "as-mm-ingest"
path = "bin/ingest.rs"

[[bin]]
name = "as-mm-backtest"
path = "bin/backtest.rs"

[[bin]]
name = "as-mm-live"
path = "bin/live.rs"
```

The strategy is **identical** in backtest and live: zero conditional
compilation, zero `#[cfg(backtest)]`. The only difference is which engine
hosts it.

## 7. Pure state machine for risk

**Problem.** Risk policy (inventory caps, daily loss circuit breaker)
mixed into the strategy makes it impossible to test the policy in
isolation, and easy to introduce bugs that only surface in production.

**Pattern.** A `RiskGate` struct that takes inputs, returns decisions,
mutates only its own state. The strategy translates decisions into NT
calls:

```rust
pub enum Sides { Both, AskOnly, BidOnly, None }

pub struct RiskGate {
    q_max: f64,
    daily_loss_limit_bps: i64,
    day_start_equity: f64,
    halted: bool,
}

impl RiskGate {
    pub fn allowed_sides(&self, inventory: f64) -> Sides { ... }
    pub fn update_on_fill(&mut self, current_equity: f64) -> bool { ... }
    pub fn reset_daily(&mut self, new_equity: f64) { ... }
}
```

In the strategy:

```rust
fn on_order_filled(&mut self, event: &OrderFilled) -> anyhow::Result<()> {
    // ... update inventory, realized PnL, equity ...
    if self.risk.update_on_fill(equity) {
        log::warn!("circuit breaker tripped");
        self.cancel_all_orders(self.cfg.instrument_id, None, None)?;
    }
    Ok(())
}
```

Tests for `RiskGate` are pure: construct, call `update_on_fill`, assert.
No engine, no fixtures, no mocks.

## 8. Re-quote rate limiting

**Problem.** A market with 1000 quote ticks per second runs your model
1000 times per second. You don't need that — venue throttles alone make
sub-millisecond re-quotes useless.

**Pattern.** Track the last re-quote timestamp and short-circuit
`on_quote` if it's too soon:

```rust
fn on_quote(&mut self, quote: &QuoteTick) -> anyhow::Result<()> {
    self.last_mid = Some(0.5 * (quote.bid_price.as_f64() + quote.ask_price.as_f64()));
    let now_ns: u64 = quote.ts_event.into();

    let interval_ns = self.cfg.requote_interval_ms * 1_000_000;
    if now_ns < self.last_requote_ns.saturating_add(interval_ns) {
        return Ok(());  // too soon — skip the heavy cycle
    }
    self.last_requote_ns = now_ns;

    // ... heavy: model, risk gate, dispatch ...
    Ok(())
}
```

Rule of thumb: 50–500 ms is plenty for most venues. Below 50 ms you're
just creating message-bus pressure.

## 9. Order action planner separated from dispatcher

**Problem.** Deciding *what* to do (Submit/Amend/Cancel/NoChange) and
*executing* it (calling NT methods) tangled together makes both harder to
test and reason about.

**Pattern.** A `QuoteManager` that returns `Vec<QuoteAction>`. The
strategy executes them:

```rust
pub enum QuoteAction {
    Submit { side, price, qty },
    Amend  { side, order_id, new_price },
    Cancel { side, order_id },
    NoChange { side },
}

impl QuoteManager {
    pub fn plan(&self, target: &OptimalQuotes, sides: Sides, qty: f64)
        -> Vec<QuoteAction>;
}
```

Decision matrix per side (for `θ = threshold_ticks * tick_size`):

| State | Action |
|---|---|
| No working quote, allowed | `Submit` |
| `\|Δpx\| ≤ θ` | `NoChange` |
| `θ < \|Δpx\| ≤ 2θ` | `Amend` (preserves queue priority) |
| `\|Δpx\| > 2θ` | `Cancel` (next tick re-submits) |
| Side disallowed | `Cancel` if working, else `NoChange` |

Why three thresholds? `Amend` keeps queue position (faster fills);
`Cancel` is for moves too large for the venue to amend. `NoChange` avoids
amend-spam that fills the rate limit budget for nothing.

## 10. Instrument resolution from cache

**Problem.** `tick_size`, `size_precision`, `min_quantity`, `multiplier`
are instrument-specific. Hardcoding them is fragile (they change between
venues) and wrong (each adapter pulls them at runtime).

**Pattern.** Resolve in `on_start` from the cache, store on the struct:

```rust
fn on_start(&mut self) -> anyhow::Result<()> {
    let inst = self.cache().instrument(&self.cfg.instrument_id)
        .ok_or_else(|| anyhow::anyhow!(
            "instrument {} not in cache — did you forget add_instrument?",
            self.cfg.instrument_id
        ))?;
    self.tick_size = inst.price_increment().as_f64();
    self.instrument = Some(inst.clone());

    // Update QuoteManager with the real tick_size now that we have it.
    self.quote_manager = QuoteManager::new(
        self.cfg.requote_price_threshold_ticks,
        self.tick_size,
    );
    // ...
    Ok(())
}
```

In **backtest**, the catalog supplies the instrument via `add_instrument`
or `BacktestDataConfig`. In **live**, the adapter's
`InstrumentProvider::initialize()` pre-loads them into the cache. Either
way, `on_start` is the right hook.

## 11. Position accounting that handles flips

**Problem.** A naive PnL update breaks when a fill flips the position
sign (long 3 → sell 5 → short 2). You need to realize the closed leg at
the old VWAP entry, then open the new leg at the fill price.

**Pattern.** A pure function that's exhaustively unit-tested:

```rust
pub(crate) fn update_position_accounting(
    inventory: &mut f64,
    entry_price_avg: &mut f64,
    realized_pnl: &mut f64,
    signed_qty: f64,   // > 0 = buy, < 0 = sell
    price: f64,
) {
    let old_inv = *inventory;
    let new_inv = old_inv + signed_qty;

    if old_inv == 0.0 {
        *entry_price_avg = price;                // open from flat
    } else if old_inv.signum() == signed_qty.signum() {
        // same side — VWAP accumulate
        let abs_old = old_inv.abs();
        let abs_add = signed_qty.abs();
        *entry_price_avg = (*entry_price_avg * abs_old + price * abs_add)
                            / (abs_old + abs_add);
    } else if old_inv.signum() == new_inv.signum() || new_inv == 0.0 {
        // partial close — realize closed leg, entry unchanged
        let closed = signed_qty.abs().min(old_inv.abs());
        let sign = old_inv.signum();
        *realized_pnl += sign * closed * (price - *entry_price_avg);
        if new_inv == 0.0 { *entry_price_avg = 0.0; }
    } else {
        // flip through zero — realize full old, open new at fill price
        let sign = old_inv.signum();
        *realized_pnl += sign * old_inv.abs() * (price - *entry_price_avg);
        *entry_price_avg = price;
    }
    *inventory = new_inv;
}
```

The four branches (open-from-flat, same-side accumulate, partial close,
flip-through-zero) are individually unit-testable.

## 12. Reporting via Parquet writers

**Problem.** Backtest analysis (PnL, fill rates, parameter drift) needs
structured output. Logging to stdout is unparseable.

**Pattern.** A `Reporter` that owns Parquet writers per output file. The
strategy calls `reporter.record_*` at the relevant events:

```rust
pub struct Reporter {
    fills_writer: ArrowWriter<File>,
    quotes_writer: ArrowWriter<File>,
    params_writer: ArrowWriter<File>,
    equity_writer: ArrowWriter<File>,
}

impl Reporter {
    pub fn new(reports_path: &Path, run_id: &str, instrument_id: &InstrumentId)
        -> anyhow::Result<Self>;

    pub fn record_fill(&mut self, row: FillRow) -> anyhow::Result<()>;
    pub fn record_quote(&mut self, row: QuoteRow) -> anyhow::Result<()>;
    pub fn record_params(&mut self, row: ParamRow) -> anyhow::Result<()>;
    pub fn record_equity(&mut self, row: EquityRow) -> anyhow::Result<()>;
}
```

Per-run directory layout:

```
reports/{run_id}/{instrument_id}/
├── fills.parquet     ← per OrderFilled event
├── quotes.parquet    ← per re-quote decision
├── params.parquet    ← per calibration epoch
└── equity.parquet    ← hourly equity snapshots
```

Hourly equity snapshots come from a second timer (separate from the
daily one):

```rust
const EQUITY_SNAPSHOT_TIMER: &str = "as_mm_rs_equity_snapshot";

fn on_time_event(&mut self, event: &TimeEvent) -> anyhow::Result<()> {
    match event.name.as_str() {
        DAILY_RECAL_TIMER => self.handle_daily_recal(event),
        EQUITY_SNAPSHOT_TIMER => self.record_equity_snapshot(event.ts_event.into()),
        _ => Ok(()),
    }
}
```

## 13. Graceful `on_stop`

**Problem.** Stopping a strategy mid-position leaves NT's portfolio with
unrealized PnL only — backtest reports look broken.

**Pattern.** Close all positions before NT shuts down:

```rust
fn on_stop(&mut self) -> anyhow::Result<()> {
    self.cancel_all_orders(self.cfg.instrument_id, None, None)?;
    self.close_all_positions(self.cfg.instrument_id, None, None)?;

    if let Some(reporter) = self.reporter.as_mut() {
        reporter.flush()?;
    }
    Ok(())
}
```

In **live**, manual operator intervention may be safer than auto-flatten
(market orders during a halted session can move price). For live, just
cancel orders and let the operator decide:

```rust
fn on_stop(&mut self) -> anyhow::Result<()> {
    self.cancel_all_orders(self.cfg.instrument_id, None, None)?;
    if let Some(reporter) = self.reporter.as_mut() {
        reporter.flush()?;
    }
    log::warn!("strategy stopped — manual position flatten required");
    Ok(())
}
```

## See also

- [`troubleshooting_rust.md`](troubleshooting_rust.md) — common errors and the diagnostic workflow.
- [`write_rust_strategy.md`](write_rust_strategy.md) — minimal walkthrough.
- [`write_rust_actor.md`](write_rust_actor.md) — actor (no order management) walkthrough.
