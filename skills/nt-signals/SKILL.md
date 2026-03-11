---
name: nt-signals
description: "Use when working with indicators, signal generation, bar aggregation, custom data types, analysis statistics, or tearsheets in NautilusTrader."
---

# nt-signals

## What This Skill Covers

NautilusTrader **signals and analysis domain** — indicators, custom data types, bar aggregation, portfolio statistics, and reporting.

**Python modules**: `indicators/`, `data/aggregation`, `model/data`, `model/book`, `model/custom`, `analysis/`
**Rust crates**: `nautilus_indicators`, `nautilus_analysis`, `nautilus_model` (data subset)

## When To Use

- Using or building custom indicators (EMA, RSI, Bollinger Bands, etc.)
- Signal generation and publishing
- Bar aggregation (custom bar types, time/tick/volume bars)
- Defining custom data types (`@customdataclass`)
- Portfolio statistics, tearsheets, and analysis reporting
- Order book data processing

## When NOT To Use

- **Strategy order logic** → use `nt-trading`
- **Data persistence or catalog** → use `nt-data`
- **Domain model types (instruments, identifiers)** → use `nt-model`
- **Backtest engine configuration** → use `nt-backtest`

## Python Usage

### Built-in Indicators

```python
from nautilus_trader.indicators.average.ema import ExponentialMovingAverage
from nautilus_trader.indicators.rsi import RelativeStrengthIndex
from nautilus_trader.indicators.bollinger_bands import BollingerBands

# Create indicators
ema_fast = ExponentialMovingAverage(period=10)
ema_slow = ExponentialMovingAverage(period=20)
rsi = RelativeStrengthIndex(period=14)

# Register in strategy's on_start():
self.register_indicator_for_bars(bar_type, ema_fast)
self.register_indicator_for_bars(bar_type, ema_slow)
```

**Indicator categories:**
- **Averages**: `ExponentialMovingAverage`, `SimpleMovingAverage`, `WeightedMovingAverage`, `AdaptiveMovingAverage`, `HullMovingAverage`, `DoubleExponentialMovingAverage`, `WilderMovingAverage`, `VariableIndexDynamic`
- **Momentum**: `RelativeStrengthIndex`, `Stochastics`, `CommodityChannelIndex`, `RateOfChange`
- **Volatility**: `BollingerBands`, `AverageTrueRange`, `KeltnerChannel`, `DonchianChannel`, `VolatilityRatio`
- **Trend**: `AroonOscillator`, `DirectionalMovement`, `LinearRegression`, `ArcherMovingAveragesTrends`
- **Volume**: `OnBalanceVolume`, `VolumeWeightedAveragePrice`

### Bar Aggregation

```python
from nautilus_trader.model.data import BarType, BarSpecification
from nautilus_trader.model.enums import BarAggregation, PriceType

# Time bars
bar_type = BarType.from_str("ETHUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL")

# Tick bars
tick_bars = BarSpecification(step=100, aggregation=BarAggregation.TICK, price_type=PriceType.LAST)

# Volume bars
vol_bars = BarSpecification(step=1000, aggregation=BarAggregation.VOLUME, price_type=PriceType.LAST)
```

### Custom Data Types

```python
from nautilus_trader.model.custom import customdataclass

@customdataclass
class MySignalData:
    signal_value: float
    signal_strength: int
    # ts_event and ts_init auto-provided by decorator
```

### Analysis & Tearsheets

```python
from nautilus_trader.analysis.analyzer import PortfolioAnalyzer
from nautilus_trader.analysis.reporter import ReportProvider

analyzer = PortfolioAnalyzer()
# analyzer automatically registered in backtest/live node
# Access via node.analyzer after run
```

## Python Extension

### Custom Indicator

Subclass `Indicator` and implement `handle_bar()`, `update_raw()`, `_reset()`:

```python
from nautilus_trader.indicators import Indicator

class MyIndicator(Indicator):
    def __init__(self, period: int):
        super().__init__(params=[period])
        self.period = period
        self.value = 0.0
        self.count = 0

    def handle_bar(self, bar):
        self.update_raw(bar.close.as_double())

    def update_raw(self, value: float):
        if not self.has_inputs:
            self._set_has_inputs(True)
        # TODO: Core calculation
        self.count += 1
        if not self.initialized and self.count >= self.period:
            self._set_initialized(True)

    def _reset(self):
        self.value = 0.0
        self.count = 0
```

See `templates/indicator.py` for full template.

### Custom PortfolioStatistic

```python
from nautilus_trader.analysis.statistic import PortfolioStatistic

class MyStatistic(PortfolioStatistic):
    def calculate_from_returns(self, returns):
        if not self._check_valid_returns(returns):
            return None
        return float(returns.mean())
```

Return values must be JSON-serializable (float, int, str, bool, None).

See `templates/portfolio_statistic.py` for full template.

### Custom Data Types

Use `@customdataclass` decorator — it auto-generates serialization methods (dict, bytes, Arrow). See `templates/custom_data.py`.

## Rust Usage

```rust
use nautilus_indicators::average::ema::ExponentialMovingAverage;
use nautilus_indicators::rsi::RelativeStrengthIndex;
use nautilus_analysis::analyzer::PortfolioAnalyzer;
```

## Rust Extension

### Custom Indicator in Rust

```rust
use pyo3::prelude::*;
use nautilus_indicators::indicator::Indicator;

#[pyclass]
pub struct MyRustIndicator {
    period: usize,
    value: f64,
    initialized: bool,
}

#[pymethods]
impl MyRustIndicator {
    #[new]
    fn new(period: usize) -> Self { ... }

    fn handle_bar(&mut self, bar: &Bar) { ... }
    fn update_raw(&mut self, value: f64) { ... }
}
```

**PyO3 conventions:**
- Use `#[pyclass]` and `#[pymethods]` for Python-visible types
- Register in `crates/pyo3/src/lib.rs`
- Follow Rust edition 2024 conventions

## Key Conventions

### Indicator Naming

- Match NT convention: `ExponentialMovingAverage` not `EMA` (class name)
- Short names used in `name` property (auto-derived)
- Parameters passed to `super().__init__(params=[...])` for serialization

### Registration Pattern

Always register indicators via `self.register_indicator_for_bars()` or `self.register_indicator_for_quote_ticks()` in `on_start()` — never call `handle_bar()` manually.

### Custom Data Serialization

- `@customdataclass` auto-generates Arrow schemas
- `InstrumentId` fields are auto-converted to/from strings
- All fields need type annotations
- `ts_event` and `ts_init` are auto-prepended (don't define them)

## References

- `references/concepts/` — reports, visualization, portfolio, data
- `references/api/` — indicators, analysis, data, book, portfolio
- `references/python/` — analysis source reference (config, tearsheet, statistic, themes)
- `references/rust/` — analysis Rust source reference
- `references/examples/` — indicator usage, cascaded indicators, bar aggregation
- `templates/` — indicator.py, custom_data.py, portfolio_statistic.py
