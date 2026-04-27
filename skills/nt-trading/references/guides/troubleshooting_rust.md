# Troubleshooting Rust Strategies

NT's Rust API is under active development; signatures change between
releases and the official docs lag the source. When something fails, the
fastest path to a fix is **read the source, not the docs**. This guide
captures real failure modes and the diagnostic workflow that resolves them.

## Diagnostic workflow

When a build, test, or run fails, work through these steps in order before
trying speculative fixes.

### 1. Read the failure verbatim

`cargo build` errors point to exact line numbers. Compiler errors are
trustworthy — read the trait, the missing method, the lifetime. Don't
"interpret" them.

### 2. Find the source

NT's docs lag the code. The truth is in the crates:

```bash
# If you cloned NT locally:
grep -rn "fn submit_order" /path/to/nautilus_trader/crates/

# If using the published crate:
cargo doc --open --package nautilus-trading
```

Read the function signature, then read 50 lines around it for context. The
arg order, default values, and error variants are all there.

### 3. Verify your assumption with a tool

Don't guess. Use:

| Question | Tool |
|----------|------|
| Does this method exist on this version? | `grep -rn "pub fn <name>" crates/` |
| Why does the macro expand this way? | `cargo expand -p <your-crate>` |
| What features are active? | `cargo tree -p <your-crate> --features` |
| Why is this trait not satisfied? | `cargo build 2>&1 \| grep -A 30 "trait bound"` |

### 4. Check the version

NT crates are tightly coupled. If you mix `0.55` and `0.54`, types from
`nautilus-model` won't satisfy traits in `nautilus-trading`. Run:

```bash
cargo tree -p <your-crate> | grep nautilus
```

All `nautilus-*` crates must be the same version (or all the same git rev).

### 5. Reproduce minimally

If the failure is in a strategy, copy the failing handler into the smallest
possible binary that compiles. Most "this doesn't work" reports vanish when
the surrounding context is stripped.

## Common errors and fixes

### Build / macro errors

#### `the trait bound MyStrategy: Debug is not satisfied`

**Cause:** `DataActor` requires `Debug` (via the blanket `Component` impl).
The `nautilus_strategy!` / `nautilus_actor!` macros do not derive it for you.

**Fix:** Implement `Debug` manually or derive it:

```rust
impl std::fmt::Debug for MyStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MyStrategy").finish()
    }
}
```

#### `cannot find macro nautilus_strategy in this scope`

**Cause:** The macro lives in `nautilus_trading`, not `nautilus_common`.

**Fix:**

```rust
use nautilus_trading::{nautilus_strategy, strategy::{Strategy, StrategyConfig, StrategyCore}};
```

#### `expected fn pointer, found Fn` in macro override block

**Cause:** The `nautilus_strategy!` second-argument block expects normal
`fn` signatures, not closures. You can't capture state from outside the
function in the block — only `self` is in scope.

**Fix:** Move state-capturing logic into a method on `MyStrategy` and call
it from the override:

```rust
impl MyStrategy {
    fn handle_rejection(&mut self, event: &OrderRejected) { /* ... */ }
}

nautilus_strategy!(MyStrategy, {
    fn on_order_rejected(&mut self, event: OrderRejected) {
        self.handle_rejection(&event);
    }
});
```

#### `method not found in &Self` for `submit_order` / `subscribe_quotes`

**Cause:** Either the macro didn't expand (forgot to invoke
`nautilus_strategy!(MyStrategy);`), or you're calling from a non-`&mut
self` context.

**Fix:** Verify the macro line exists. `submit_order` requires `&mut
self`. If you're inside a closure/callback, this is a re-entrancy bug —
look up the actor by ID each time.

### Runtime errors

#### `Order rejected: POST_ONLY_WOULD_CROSS`

**Cause:** Your bid was set ≥ best ask (or ask ≤ best bid) at the moment
the venue evaluated it. This is **expected behavior** for an aggressive
post-only re-quote, not a bug.

**Fix:** Log at INFO level and let the next tick retry naturally. Do not
build a retry loop:

```rust
nautilus_strategy!(MyStrategy, {
    fn on_order_rejected(&mut self, event: OrderRejected) {
        let reason = event.reason.to_string();
        if reason.contains("POST_ONLY") {
            log::info!("post-only reject (expected): {reason}");
        } else {
            log::warn!("order rejected: {reason}");
        }
        // Clear tracked working state for this client_order_id.
    }
});
```

#### `LimitOrder::new` panics with quantity error

**Cause:** Your `cfg.quote_size` is smaller than the instrument's
`min_quantity` after rounding to `size_precision`. Coarse-precision
instruments (e.g. `size_precision = 0` and `min_quantity = 10`) panic
when given `0.1`.

**Fix:** Resolve `min_quantity` from the instrument and clamp:

```rust
let min_qty = instrument.min_quantity().map(|q| q.as_f64()).unwrap_or(0.0);
let effective_qty = qty_f64.max(min_qty);
let qty = Quantity::new(effective_qty, instrument.size_precision());
```

#### `inventory exceeds q_max` from your own model

**Cause:** A fill arrived between two re-quote cycles and pushed inventory
past the cap. Your model's input validator is correctly refusing — the
problem is upstream.

**Fix:** Clamp inventory **into the model**, but let the risk gate enforce
single-side quoting separately:

```rust
let q_clamped = self.inventory
    .max(-params.q_max + f64::EPSILON)
    .min(params.q_max - f64::EPSILON);
let target = optimal_quotes(mid, q_clamped, &params, tick_size)?;
// Risk gate (separate state machine) decides which sides may quote.
let sides = risk.allowed_sides(self.inventory);
```

#### `request_quotes` / `request_trades` returns nothing

**Cause:** In backtest, the requested time range is at or before the
catalog's earliest data. The historical data engine has no rows to
deliver, so `on_historical_quotes` never fires.

**Fix:** Maintain a rolling buffer from `on_quote` / `on_trade` as a
fallback for live calibration. Only use `request_*` for the initial
warmup, after the first live tick has anchored the time:

```rust
fn on_quote(&mut self, quote: &QuoteTick) -> anyhow::Result<()> {
    self.live_quotes.push_back(*quote);
    self.trim_live_buffers(quote.ts_event.into());  // cap at window
    // ... rest of handler
}
```

#### Realized PnL is zero in backtest reports despite many fills

**Cause:** NT's portfolio reports realized PnL only on **closed**
positions. If you stop with open inventory, those fills look unrealized.

**Fix:** Close all positions in `on_stop`:

```rust
fn on_stop(&mut self) -> anyhow::Result<()> {
    self.close_all_positions(self.cfg.instrument_id, None, None)?;
    Ok(())
}
```

#### Calibration silently uses fallback parameters

**Cause:** Your `calibrate()` returned `Err`, but you caught it and used
hardcoded defaults. Now the strategy quotes happily on parameters that
don't reflect the market — the worst kind of silent failure.

**Fix:** Fail fast. Failed calibration should stop the strategy, not
mask itself:

```rust
match calibrate(quotes, trades, tick_size, window, &cfg, mid, intent) {
    Ok(out) => self.apply_calibration(out.params, out.r_squared, intent),
    Err(e) => {
        log::error!("calibration failed: {e} — stopping strategy");
        self.stop();
    }
}
```

Use a fallback only when you can prove the fallback is harmless (e.g.
"keep yesterday's params"), and log it loudly enough that you'll notice.

#### Unit conversion off by `tick_size`

**Cause:** Calibration regresses intensity in **ticks** for numerical
stability, but the model consumes `k` in **price units**. Forgetting the
`k_price = k_tick / tick_size` conversion produces spreads that are
`100×` too wide or too narrow at typical tick sizes.

**Fix:** Make the conversion explicit and unit-tested. Document the units
in the type:

```rust
pub struct IntensityFit {
    pub a: f64,           // per second
    pub k: f64,           // per price unit (already divided by tick_size)
    pub r_squared: f64,
}
```

#### Quote tick stream explodes from L2 deltas

**Cause:** Subscribing to `order_book_deltas` and emitting a derived
`QuoteTick` on every delta produces millions of ticks per day even when
top-of-book is unchanged.

**Fix:** Maintain top-of-book in memory and emit a `QuoteTick` only when
best-bid/ask price or size actually changes.

### Data / ingest errors

#### `cargo run --bin ingest` fails with `instrument not found`

**Cause:** The catalog doesn't have an instrument file written for the
target `InstrumentId`. `query_*` returns no rows because there's no
instrument to anchor the partition.

**Fix:** Write instruments first, before any data:

```rust
let provider = BybitInstrumentProvider::new(...);
let instruments = provider.fetch().await?;
catalog.write_instruments(instruments)?;
// Now write quotes/trades.
```

#### `quote_ticks` partition has `bid > ask` rows

**Cause:** Your decoder built a `QuoteTick` from a deep-level delta where
the new top-of-book momentarily crossed because two updates landed
out-of-order.

**Fix:** Validate at write time. Refuse to commit a partition that
violates the invariant:

```rust
for q in &batch {
    anyhow::ensure!(
        q.bid_price <= q.ask_price,
        "L1 invariant violated at ts {}", q.ts_event
    );
}
```

This is a hard fail, not a warning. Crossed L1 corrupts every downstream
backtest.

### LiveNode / runtime errors

#### `BybitEnv::from_env()` panics on missing variable

**Cause:** Adapter configs read API credentials at construction time. If
the var is unset, the panic happens deep inside the factory.

**Fix:** Validate explicitly at startup with a clear message:

```rust
let env = std::env::var("BYBIT_ENV").unwrap_or_else(|_| "testnet".to_string());
match env.as_str() {
    "testnet" | "mainnet" => {}
    other => anyhow::bail!("BYBIT_ENV must be testnet or mainnet, got '{other}'"),
}
```

#### `LiveNode::run().await` returns immediately

**Cause:** Either you forgot `#[tokio::main]`, or the runtime is single-
threaded and a task is blocking the executor.

**Fix:**

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // ... build node ...
    node.run().await?;
    Ok(())
}
```

If you need blocking work (e.g. heavy calibration), spawn it on a
blocking thread: `tokio::task::spawn_blocking(|| heavy_work())`.

## Anti-patterns to avoid

These compile and run, but bite you in production.

### Catching every error and continuing

```rust
// BAD — masks real bugs
if let Err(e) = critical_operation() {
    log::warn!("oh well: {e}");
}
```

If an operation is critical, fail fast. If it isn't, it shouldn't run on
the hot path at all.

### Storing `ActorRef` in a field

```rust
// BAD — guard outlives the dispatch scope
pub struct MyStrategy {
    other: ActorRef<OtherActor>,
}
```

Always look up by ID at the call site. The registry hands you a
short-lived guard that must drop before the dispatch returns.

### `.await` while holding an actor guard

```rust
// BAD — guard crosses await
let guard = registry.get(other_id);
some_async_call().await;  // ← deadlock or use-after-free risk
guard.do_thing();
```

Drop the guard before any `.await`.

### Hardcoded `tick_size` / `price_precision`

Each instrument has its own. Resolve from the cache in `on_start` and
store on the strategy struct:

```rust
fn on_start(&mut self) -> anyhow::Result<()> {
    let inst = self.cache().instrument(&self.cfg.instrument_id)
        .ok_or_else(|| anyhow::anyhow!("instrument not in cache"))?;
    self.tick_size = inst.price_increment().as_f64();
    // ...
    Ok(())
}
```

## When the workflow stalls

If five steps of the diagnostic workflow haven't surfaced a fix:

1. **List every assumption you've been making.** Especially "this should
   work because the docs say so." Verify each one with a tool.
2. **Reverse one assumption.** If you've been assuming the bug is in your
   strategy, assume it's in the adapter. Look there for ten minutes.
3. **Read the failing site's source from the failing crate, in full.**
   Not summaries. Not your memory. The actual file.
4. **Search GitHub issues by exact error text.** NT is small enough that
   if you've hit it, someone else probably has too.
5. **Compile a minimal reproducer.** Often the bug evaporates as you
   strip context — that itself is a clue about the cause.

If after all that the failure persists, file a structured report: what you
tried, what you ruled out, what tools confirmed which assumptions, and
where the boundary of your investigation is. That's a useful handoff,
not a "I give up."
