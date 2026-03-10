# Stage 05: Backtesting Deep Dive

## Goal

Master both backtesting APIs, load data from various sources, understand fill simulation, and generate analysis reports.

## Prerequisites

- Stage 04 complete (can write and run a strategy)

## Two Backtesting APIs

### BacktestEngine (Low-Level)

**Imperative** — you call methods on the engine directly.

Best for: interactive exploration, debugging, fine-grained control.

```python
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig

engine = BacktestEngine(config=BacktestEngineConfig())

# 1. Add venue
engine.add_venue(
    venue=Venue("SIM"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.CASH,
    base_currency=USD,
    starting_balances=[Money(100_000, USD)],
)

# 2. Add instrument
engine.add_instrument(instrument)

# 3. Add data
engine.add_data(bars)  # or ticks, order book deltas

# 4. Add strategy
engine.add_strategy(strategy)

# 5. Run
engine.run()
```

After running: generate reports, inspect state, then `engine.reset()` to run again (data persists, must re-add strategies).

### BacktestNode (High-Level)

**Declarative** — everything specified via serializable config objects.

Best for: batch runs, parameter sweeps, reproducible configs.

```python
from nautilus_trader.backtest.node import BacktestNode

config = BacktestRunConfig(
    engine=BacktestEngineConfig(),
    venues=[BacktestVenueConfig(
        name="SIM",
        oms_type="NETTING",
        account_type="CASH",
        base_currency="USD",
        starting_balances=["100000 USD"],
    )],
    data=[BacktestDataConfig(
        catalog_path=str(catalog.path),
        data_cls="nautilus_trader.model.data:Bar",
        instrument_id=str(instrument.id),
        bar_types=[str(bar_type)],
    )],
    strategies=[ImportableStrategyConfig(
        strategy_path="my_module:MyStrategy",
        config_path="my_module:MyConfig",
        config={"instrument_id": str(instrument.id), ...},
    )],
)

node = BacktestNode(configs=[config])
results = node.run()
```

Key difference: strategies are referenced by **import path strings**, not instantiated objects.

### Comparison

| Aspect | BacktestEngine | BacktestNode |
|--------|---------------|--------------|
| Config style | Imperative (method calls) | Declarative (config objects) |
| Data source | In-memory (`add_data()`) | ParquetDataCatalog |
| Strategy | Instantiated objects | Import path strings |
| Best for | Interactive, debugging | Batch runs, parameter sweeps |
| Repeated runs | `engine.reset()` | New config per run |

## Data Loading

### From CSV (Manual Wrangling)

```python
import pandas as pd
from nautilus_trader.persistence.wranglers import BarDataWrangler, QuoteTickDataWrangler, TradeTickDataWrangler

# Bars
df = pd.read_csv("data.csv", index_col="timestamp", parse_dates=True)
wrangler = BarDataWrangler(bar_type, instrument)
bars = wrangler.process(df)  # Returns list[Bar]

# Quote ticks
wrangler = QuoteTickDataWrangler(instrument)
ticks = wrangler.process(df)  # Expects bid_price, ask_price, bid_size, ask_size columns

# Trade ticks
wrangler = TradeTickDataWrangler(instrument)
ticks = wrangler.process(df)  # Expects price, quantity columns
```

### From ParquetDataCatalog

```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog

# Write data
catalog = ParquetDataCatalog("./my_catalog")
catalog.write_data(instrument)
catalog.write_data(bars)

# Read data
instruments = catalog.instruments()
bars = catalog.bars(bar_types=[bar_type], start=start_dt, end=end_dt)

# List available data types
catalog.list_data_types()
```

### Test Data (For Learning)

NT bundles test data for quick experiments:

```python
from nautilus_trader.test_kit.providers import TestDataProvider, TestInstrumentProvider

# Instruments
instrument = TestInstrumentProvider.default_fx_ccy("EUR/USD")
instrument = TestInstrumentProvider.ethusdt_binance()

# Data
provider = TestDataProvider()
df = provider.read_csv_ticks("truefx/eurusd-ticks.csv")
df = provider.read_csv_ticks("binance/ethusdt-trades.csv")
```

## Venue Configuration

### OMS Types

| OMS Type | Behavior | Use Case |
|----------|----------|----------|
| `NETTING` | One position per instrument | Crypto spot, most FX |
| `HEDGING` | Multiple positions per instrument | FX ECN, CFDs |

### Account Types

| Account Type | Behavior |
|-------------|----------|
| `CASH` | No shorting, balance checks enforced |
| `MARGIN` | Leverage allowed, margin calculations |

### Fill Simulation

The backtesting engine simulates fills based on your data granularity:

**Data hierarchy** (most → least realistic):
1. **L3 order book** — individual order matching
2. **L2 order book** — price-level matching
3. **L1 quotes** — top-of-book matching
4. **Trade ticks** — last-price matching
5. **Bars** — reduced precision (stop orders fill at trigger price, not market price)

**Important**: The venue's `book_type` must match your data:
- `L1_MBP` (default) — uses quotes/ticks, ignores order book deltas
- `L2_MBP` — requires order book deltas, ignores quotes/bars
- `L3_MBO` — requires order book deltas with order IDs

```python
engine.add_venue(
    venue=Venue("SIM"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.CASH,
    base_currency=USD,
    starting_balances=[Money(100_000, USD)],
    fill_model=FillModel(prob_slippage=0.1),
    book_type=BookType.L1_MBP,
)
```

### Performance Tip

When loading multi-instrument data:
```python
# DON'T: sort on every add
engine.add_data(instrument_a_bars)  # sorts
engine.add_data(instrument_b_bars)  # sorts again

# DO: defer sorting
engine.add_data(instrument_a_bars, sort=False)
engine.add_data(instrument_b_bars, sort=False)
engine.sort_data()  # sort once at the end
```

## Post-Run Analysis

### Reports

```python
# After engine.run()
account_report = engine.trader.generate_account_report(Venue("SIM"))
order_fills = engine.trader.generate_order_fills_report()
positions = engine.trader.generate_positions_report()
```

### Tearsheets

```python
from nautilus_trader.analysis.tearsheet import create_tearsheet

create_tearsheet(engine=engine, output_path="results.html")
```

Requires the `visualization` extra: `uv pip install "nautilus_trader[visualization]"`

### Portfolio Statistics

```python
# Access the analyzer
analyzer = engine.portfolio.analyzer

# Register custom statistics
from nautilus_trader.analysis.statistic import PortfolioStatistic
analyzer.register_statistic(MyCustomStat())
```

## Exercises

1. **BacktestEngine workflow**: Load test FX data, set up a HEDGING venue with MARGIN account, run your EMA cross strategy, generate all three reports.

2. **ParquetDataCatalog**: Write test data to a catalog, then set up a BacktestNode config that reads from it. Compare the workflow to BacktestEngine.

3. **Fill model experiment**: Run the same strategy twice — once with `prob_slippage=0.0` and once with `prob_slippage=0.5`. Compare results.

4. **Multi-currency**: Set up a crypto backtest with starting balances in both USDT and ETH. Observe how the account report handles multiple currencies.

## Checkpoint

You're ready for Stage 06 when:
- [ ] You can set up both BacktestEngine and BacktestNode backtests
- [ ] You understand the difference between NETTING and HEDGING OMS
- [ ] You can load data from CSV and from ParquetDataCatalog
- [ ] You know how `book_type` affects fill simulation
- [ ] You can generate reports and tearsheets after a backtest run
