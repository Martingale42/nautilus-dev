# NautilusTrader Indicators Reference Guide

## Overview

All indicators live in `nautilus_trader.indicators` and inherit from the `Indicator` base class
(`nautilus_trader.indicators.base.Indicator`). Indicators are Cython-compiled for performance.
Every indicator exposes:

- `has_inputs: bool` -- whether any data has been received
- `initialized: bool` -- whether the warmup period is satisfied
- `handle_bar(bar)` / `handle_quote_tick(tick)` / `handle_trade_tick(tick)` -- typed update methods
- `update_raw(...)` -- direct numeric update (no data object required)
- `reset()` -- reset all state

---

## Averages (`nautilus_trader.indicators.averages`)

All moving averages extend `MovingAverage(Indicator)` and share: `period`, `value`, `price_type`.

| Class | Params | Description | Rust crate path |
|---|---|---|---|
| `SimpleMovingAverage` | `period` | Arithmetic mean over rolling window | `average::sma` |
| `ExponentialMovingAverage` | `period` | EMA with alpha = 2/(period+1) | `average::ema` |
| `DoubleExponentialMovingAverage` | `period` | DEMA: 2*EMA1 - EMA2 for reduced lag | `average::dema` |
| `WeightedMovingAverage` | `period, weights=None` | Weighted average with custom or linear weights | `average::wma` |
| `HullMovingAverage` | `period` | Alan Hull's fast smooth MA using nested WMAs | `average::hma` |
| `AdaptiveMovingAverage` | `period_er, period_alpha_fast, period_alpha_slow` | Kaufman AMA adapting to noise via EfficiencyRatio | `average::ama` |
| `WilderMovingAverage` | `period` | EMA variant with alpha = 1/period (Wilder smoothing) | `average::rma` |
| `VariableIndexDynamicAverage` | `period, cmo_ma_type=SIMPLE` | VIDYA: EMA with dynamic alpha from Chande Momentum Oscillator | `average::vidya` |

**Factory**: `MovingAverageFactory.create(period, ma_type, **kwargs)` returns the correct MA subclass
given a `MovingAverageType` enum value (`SIMPLE`, `EXPONENTIAL`, `WEIGHTED`, `HULL`, `WILDER`,
`DOUBLE_EXPONENTIAL`, `VARIABLE_INDEX_DYNAMIC`).

Additional Rust-only averages: `average::lr` (linear regression MA), `average::vwap`.

---

## Momentum (`nautilus_trader.indicators.momentum`)

| Class | Params | Output | Description | Rust path |
|---|---|---|---|---|
| `RelativeStrengthIndex` | `period, ma_type=EXP` | `value` (0-1) | RSI via average gain/loss ratio | `momentum::rsi` |
| `RateOfChange` | `period, use_log=False` | `value` | Price ROC: simple or log returns | `momentum::roc` |
| `ChandeMomentumOscillator` | `period, ma_type=WILDER` | `value` (-100..100) | CMO: momentum with overbought/oversold at +/-50 | `momentum::cmo` |
| `Stochastics` | `period_k, period_d, slowing=1, ma_type=EXP, d_method="ratio"` | `value_k, value_d` | %K/%D oscillator; supports "ratio" and "moving_average" D methods | `momentum::stochastics` |
| `CommodityChannelIndex` | `period, scalar=0.015, ma_type=SIMPLE` | `value` | CCI: deviation of typical price from its MA | `momentum::cci` |
| `EfficiencyRatio` | `period` | `value` (0-1) | Kaufman ER: net price change / sum of absolute changes | `ratio::efficiency_ratio` |
| `RelativeVolatilityIndex` | `period, scalar=100, ma_type=EXP` | `value` (0-100) | RVI: standard deviation direction tracker | `momentum::rvi` (volatility crate) |
| `PsychologicalLine` | `period, ma_type=SIMPLE` | `value` (0-100) | Percentage of bars closing above prior close | `momentum::psl` |

---

## Trend (`nautilus_trader.indicators.trend`)

| Class | Params | Output | Description | Rust path |
|---|---|---|---|---|
| `ArcherMovingAveragesTrends` | `fast_period, slow_period, signal_period, ma_type=EXP` | `long_run, short_run` | Detects trend runs from fast/slow MA divergence | `momentum::amat` |
| `AroonOscillator` | `period` | `aroon_up, aroon_down, value` | Measures periods since highest high / lowest low | `momentum::aroon` |
| `DirectionalMovement` | `period, ma_type=EXP` | `pos, neg` | +DI / -DI directional movement lines | `momentum::dm` |
| `MovingAverageConvergenceDivergence` | `fast_period, slow_period, ma_type=EXP` | `value` | MACD: difference of fast and slow MAs | `momentum::macd` |
| `IchimokuCloud` | `tenkan=9, kijun=26, senkou=52, displacement=26` | `tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span` | Full Ichimoku Kinko Hyo with 5 components | `momentum::ichimoku` |
| `LinearRegression` | `period` | `value, slope, intercept, degree, cfo, R2` | OLS regression over rolling window | `average::lr` |
| `Bias` | `period, ma_type=SIMPLE` | `value` | Rate of change between price and its MA: (price/MA) - 1 | `momentum::bias` |
| `Swings` | `period` | `direction, changed, high_price, low_price, length, duration` | Swing high/low detection with timing metrics | `momentum::swings` |

---

## Volatility (`nautilus_trader.indicators.volatility`)

| Class | Params | Output | Description | Rust path |
|---|---|---|---|---|
| `AverageTrueRange` | `period, ma_type=SIMPLE, use_previous=True, value_floor=0` | `value` | ATR: smoothed true range | `volatility::atr` |
| `BollingerBands` | `period, k, ma_type=SIMPLE` | `upper, middle, lower` | Bands at k standard deviations from MA | `momentum::bb` |
| `DonchianChannel` | `period` | `upper, middle, lower` | Highest high / lowest low channel | `volatility::dc` |
| `KeltnerChannel` | `period, k_multiplier, ma_type=EXP, ma_type_atr=SIMPLE, use_previous=True, atr_floor=0` | `upper, middle, lower` | ATR-based envelope around MA of typical price | `volatility::kc` |
| `KeltnerPosition` | `period, k_multiplier, ...` | `value` | Relative position within Keltner channel (-1..+1 range, unbounded) | `volatility::kp` |
| `VerticalHorizontalFilter` | `period, ma_type=SIMPLE` | `value` | VHF: highest-lowest range / sum of changes (trending vs ranging) | `momentum::vhf` |
| `VolatilityRatio` | `fast_period, slow_period, ma_type=SIMPLE, use_previous=True, value_floor=0` | `value` | Ratio of slow ATR to fast ATR | `volatility::vr` |

---

## Volume (`nautilus_trader.indicators.volume`)

| Class | Params | Output | Description | Rust path |
|---|---|---|---|---|
| `OnBalanceVolume` | `period=0` | `value` | Cumulative positive/negative volume momentum | `momentum::obv` |
| `VolumeWeightedAveragePrice` | (none) | `value` | Intraday VWAP, auto-resets on new day | `average::vwap` |
| `KlingerVolumeOscillator` | `fast_period, slow_period, signal_period, ma_type=EXP` | `value` | Compares volume to price movement for reversal prediction | `momentum::kvo` |
| `Pressure` | `period, ma_type=EXP, atr_floor=0` | `value, value_cumulative` | Relative volume needed to move price across ATR | `momentum::pressure` |

---

## Other

| Class | Module | Description | Rust path |
|---|---|---|---|
| `FuzzyCandlesticks` | `fuzzy_candlesticks` | Fuzzifies OHLC bars into categorical direction/size/body/wick descriptors | `volatility::fuzzy` |
| `SpreadAnalyzer` | `spread_analyzer` | Tracks current and average bid-ask spread for an instrument | `ratio::spread_analyzer` |

---

## Building a Custom Indicator

To create a custom indicator, subclass `Indicator` and implement `handle_bar()` (or
`handle_quote_tick` / `handle_trade_tick`), `update_raw()`, and `_reset()`.

### Step-by-step: Exponential Weighted Momentum

```python
from nautilus_trader.indicators import Indicator
from nautilus_trader.model.data import Bar, QuoteTick, TradeTick
from nautilus_trader.model.enums import PriceType


class ExponentialWeightedMomentum(Indicator):
    """
    Momentum indicator using exponentially weighted price changes.

    Parameters
    ----------
    period : int
        Lookback period for the momentum calculation.
    price_type : PriceType
        Price extraction type for ticks.
    """

    def __init__(self, period: int, price_type: PriceType = PriceType.LAST):
        # Pass params list for serialization — must match constructor args
        super().__init__(params=[period])
        self.period = period
        self.price_type = price_type

        # Stateful values — all must be reset in _reset()
        self.value = 0.0
        self._prev_price = 0.0
        self._alpha = 2.0 / (period + 1)
        self._count = 0

    # --- Typed update methods: extract the price, then delegate to update_raw ---

    def handle_bar(self, bar: Bar):
        self.update_raw(bar.close.as_double())

    def handle_quote_tick(self, tick: QuoteTick):
        self.update_raw(tick.extract_price(self.price_type).as_double())

    def handle_trade_tick(self, tick: TradeTick):
        self.update_raw(tick.price.as_double())

    # --- Core calculation ---

    def update_raw(self, close: float):
        if not self.has_inputs:
            self._set_has_inputs(True)
            self._prev_price = close
            self._count = 1
            return

        # Momentum = current close - previous close
        momentum = close - self._prev_price
        # Exponentially weight it
        self.value = self._alpha * momentum + (1 - self._alpha) * self.value
        self._prev_price = close
        self._count += 1

        if not self.initialized and self._count >= self.period:
            self._set_initialized(True)

    # --- Reset: MUST reset ALL stateful values ---

    def _reset(self):
        self.value = 0.0
        self._prev_price = 0.0
        self._count = 0
```

**Key patterns:**
- `super().__init__(params=[...])` — pass constructor args for indicator serialization
- `_set_has_inputs(True)` — call on first data point
- `_set_initialized(True)` — call once enough data for valid output
- `_reset()` — must reset ALL stateful values (called by `reset()`)
- `update_raw()` — keep calculation here; typed handlers just extract prices and delegate

**Registering your custom indicator** — same as built-in:

```python
def on_start(self):
    self.ewm = ExponentialWeightedMomentum(period=20)
    self.register_indicator_for_bars(bar_type, self.ewm)
    self.subscribe_bars(bar_type)
```

See `templates/indicator.py` for a complete starter template.

---

## Usage Patterns

### Creating and registering indicators in a strategy

```python
from nautilus_trader.indicators import (
    ExponentialMovingAverage,
    RelativeStrengthIndex,
    BollingerBands,
)

class MyStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        self.ema_fast = ExponentialMovingAverage(10)
        self.ema_slow = ExponentialMovingAverage(20)
        self.rsi = RelativeStrengthIndex(14)
        self.bbands = BollingerBands(20, k=2.0)

    def on_start(self):
        bar_type = BarType.from_str("EURUSD.SIM-1-MINUTE-MID-INTERNAL")
        # Auto-feeds bar data to the indicator
        self.register_indicator_for_bars(bar_type, self.ema_fast)
        self.register_indicator_for_bars(bar_type, self.ema_slow)
        self.register_indicator_for_bars(bar_type, self.rsi)
        self.register_indicator_for_bars(bar_type, self.bbands)
        self.subscribe_bars(bar_type)

    def on_bar(self, bar: Bar):
        if not self.ema_slow.initialized:
            return  # Wait for warmup
        # Access computed values
        if self.ema_fast.value > self.ema_slow.value and self.rsi.value < 0.7:
            # Trading logic...
            pass
```

### Registering for quotes or trades

```python
def on_start(self):
    instrument_id = InstrumentId.from_str("EURUSD.SIM")
    self.register_indicator_for_quote_ticks(instrument_id, self.ema)
    self.subscribe_quote_ticks(instrument_id)
    # OR
    self.register_indicator_for_trade_ticks(instrument_id, self.ema)
    self.subscribe_trade_ticks(instrument_id)
```

### Manual updates with raw values

```python
# When you have numeric values directly (e.g., from a custom source)
ema = ExponentialMovingAverage(20)
ema.update_raw(1.2345)
ema.update_raw(1.2350)
print(ema.value)       # Current EMA value
print(ema.initialized) # True after 20 updates
```

### Using MovingAverageFactory

```python
from nautilus_trader.indicators import MovingAverageFactory, MovingAverageType

# Create any MA type with a uniform interface
ma = MovingAverageFactory.create(20, MovingAverageType.HULL)
```

### Multi-output indicators

Some indicators produce multiple values rather than a single `value`:

```python
stoch = Stochastics(14, 3)
# After warmup:
stoch.value_k  # %K line
stoch.value_d  # %D line

bbands = BollingerBands(20, k=2.0)
bbands.upper   # Upper band
bbands.middle  # Middle band (MA)
bbands.lower   # Lower band

ichimoku = IchimokuCloud()
ichimoku.tenkan_sen
ichimoku.kijun_sen
ichimoku.senkou_span_a
ichimoku.senkou_span_b
ichimoku.chikou_span
```

---

## Cascaded Indicators Pattern

Indicators can feed into other indicators. The framework supports this naturally since
`update_raw()` accepts plain numeric values.

**Built-in cascading examples** from the codebase:

- `DoubleExponentialMovingAverage` internally chains two `ExponentialMovingAverage` instances:
  EMA1 feeds into EMA2, then `value = 2*EMA1 - EMA2`.
- `HullMovingAverage` chains three `WeightedMovingAverage` instances with different periods.
- `AdaptiveMovingAverage` uses an `EfficiencyRatio` to dynamically adjust its smoothing.
- `KeltnerChannel` embeds an `AverageTrueRange` and a `MovingAverage`.
- `KeltnerPosition` wraps a full `KeltnerChannel`.
- `VariableIndexDynamicAverage` embeds a `ChandeMomentumOscillator`.

**Manual cascading in a strategy:**

```python
class CascadedStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        self.rsi = RelativeStrengthIndex(14)
        self.rsi_ema = ExponentialMovingAverage(9)  # Smooth the RSI

    def on_start(self):
        bar_type = BarType.from_str("EURUSD.SIM-1-MINUTE-MID-INTERNAL")
        self.register_indicator_for_bars(bar_type, self.rsi)
        self.subscribe_bars(bar_type)

    def on_bar(self, bar: Bar):
        if self.rsi.has_inputs:
            # Feed RSI output into EMA
            self.rsi_ema.update_raw(self.rsi.value)
        if not self.rsi_ema.initialized:
            return
        # Use smoothed RSI
        smoothed_rsi = self.rsi_ema.value
```

Note: the second indicator (`rsi_ema`) is NOT registered with `register_indicator_for_bars` --
it is updated manually in `on_bar` using the first indicator's output.

---

## Rust Crate Structure

The Rust implementations live in `crates/indicators/src/` and mirror the Python API:

```
crates/indicators/src/
  indicator.rs          # Indicator trait
  lib.rs                # Crate root
  average/              # sma, ema, dema, hma, wma, ama, rma, vidya, vwap, lr
  momentum/             # rsi, roc, cmo, stochastics, cci, macd, aroon, amat,
                        # bb, bias, dm, ichimoku, kvo, obv, pressure, psl, swings, vhf
  ratio/                # efficiency_ratio, spread_analyzer
  volatility/           # atr, dc, kc, kp, rvi, vr, fuzzy
  python/               # PyO3 bindings
```

The Rust crate is `nautilus-indicators` and the Python bindings are generated via PyO3
in the `python/` subdirectory, making both the Cython and Rust versions available.
