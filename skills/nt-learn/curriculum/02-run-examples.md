# Stage 02: Running Examples

## Goal

Run existing backtest examples to see NautilusTrader in action and understand the basic workflow.

## Prerequisites

- Stage 01 complete (NT installed, `import nautilus_trader` works)

## Concepts

NautilusTrader ships with two categories of examples:
- **Numbered examples** (`example_01` through `example_11`) — teach specific concepts progressively
- **Standalone scripts** — complete backtest scenarios for different asset classes (FX, crypto)

All examples use **test data bundled with NT** in `tests/test_data/`. You don't need external data to run them.

## Steps

### 1. Run Your First Example

Start with the simplest — loading bars from a CSV:

```bash
cd nautilus_trader
python examples/backtest/example_01_load_bars_from_custom_csv/run_example.py
```

**What happens:**
- A custom CSV file is read into a pandas DataFrame
- Bars are created via `BarDataWrangler`
- A `BacktestEngine` is configured with a simulated venue
- A minimal strategy subscribes to bars and counts them
- The engine runs through the data and logs results

### 2. Understand the Example Structure

Each numbered example has two files:

| File | Purpose |
|------|---------|
| `run_example.py` | Engine setup, data loading, venue config, run |
| `strategy.py` | Strategy class with trading/analysis logic |

This separation is a pattern you'll use in your own work: **infrastructure** (engine setup) vs **logic** (strategy behavior).

### 3. Run Progressive Examples

Work through these in order — each builds on the previous:

| Example | What It Teaches |
|---------|----------------|
| `example_01` | Load CSV data, create bars, run a backtest |
| `example_02` | Use `clock.set_timer()` for periodic actions |
| `example_03` | Aggregate bars (5-min from 1-min) using `@` syntax |
| `example_04` | Persist data with `ParquetDataCatalog` |
| `example_05` | Access `Portfolio` for positions, P&L, margins |
| `example_06` | Query the `Cache` for data, orders, positions |
| `example_07` | Register and use built-in indicators (EMA) |
| `example_08` | Chain indicators (EMA of EMA) |
| `example_09` | Publish/subscribe custom Events via MessageBus |
| `example_10` | Publish/subscribe custom Data via `publish_data` |
| `example_11` | Lightweight signals via `publish_signal` |

### 4. Run a Standalone Backtest

Try a complete FX backtest:

```bash
python examples/backtest/fx_ema_cross_audusd_bars_from_ticks.py
```

This demonstrates:
- Quote tick data → internal bar aggregation
- Built-in `EMACross` strategy
- FX rollover interest simulation
- Post-backtest reporting (account, order fills, positions)

Then try a crypto backtest:

```bash
python examples/backtest/crypto_ema_cross_ethusdt_trade_ticks.py
```

This adds:
- Trade tick data (vs quote ticks)
- TWAP execution algorithm for order slicing
- Multi-currency account (USDT + ETH)
- HTML tearsheet generation

### 5. Read the Strategy Code

Open `examples/backtest/example_01_load_bars_from_custom_csv/strategy.py` and note the pattern:

```python
class MyStrategy(Strategy):
    def on_start(self) -> None:
        # Subscribe to data, initialize state
        self.subscribe_bars(...)

    def on_bar(self, bar: Bar) -> None:
        # React to each new bar
        ...

    def on_stop(self) -> None:
        # Clean up, log summary
        ...
```

Every NT strategy follows this lifecycle: `on_start` → data handlers → `on_stop`.

## Key Patterns Learned

1. **Data wranglers** convert DataFrames to NT data types (`BarDataWrangler`, `QuoteTickDataWrangler`, `TradeTickDataWrangler`)
2. **BacktestEngine** is configured imperatively: add venue → add instrument → add data → add strategy → run
3. **Strategies** react to data via `on_*` handlers, not polling
4. **Bar aggregation** uses the `@` syntax: `"INSTRUMENT-5-MINUTE-LAST-INTERNAL@1-MINUTE-EXTERNAL"`
5. **Test data** lives in `tests/test_data/` — use `TestDataProvider` and `TestInstrumentProvider` for quick experiments

## Checkpoint

You're ready for Stage 03 when:
- [ ] You've run at least 3 examples successfully
- [ ] You can explain the difference between `run_example.py` and `strategy.py`
- [ ] You understand that strategies react to data via event handlers (`on_bar`, `on_start`, `on_stop`)
- [ ] You know what `BarDataWrangler` and `BacktestEngine` do at a high level
