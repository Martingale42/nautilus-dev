# Stage 06: Indicators & Actors

## Goal

Use built-in indicators, cascade indicators, build custom actors for data processing and signal generation.

## Prerequisites

- Stage 05 complete (can run backtests, understand data flow)

## Indicators

### Built-In Indicators

NT ships many indicators: EMA, SMA, RSI, MACD, Bollinger Bands, ATR, and more. All follow the same pattern:

```python
from nautilus_trader.indicators.average.ema import ExponentialMovingAverage

ema = ExponentialMovingAverage(period=20)
```

### Registration Pattern

Register an indicator for automatic updates:

```python
def on_start(self) -> None:
    self.ema = ExponentialMovingAverage(20)
    self.register_indicator_for_bars(self.bar_type, self.ema)
    self.subscribe_bars(self.bar_type)
```

When a bar arrives, the indicator updates **before** `on_bar()` is called. You can use `self.ema.value` immediately.

### Warmup Check

Indicators need N bars before they produce valid output:

```python
def on_bar(self, bar) -> None:
    if not self.ema.initialized:
        return  # Not enough data yet
    # Safe to use self.ema.value here
```

### Cascading Indicators (EMA of EMA)

Feed one indicator's output into another manually:

```python
def on_start(self) -> None:
    self.primary_ema = ExponentialMovingAverage(10)
    self.secondary_ema = ExponentialMovingAverage(20)

    # Only register the primary for auto bar updates
    self.register_indicator_for_bars(self.bar_type, self.primary_ema)
    self.subscribe_bars(self.bar_type)

def on_bar(self, bar) -> None:
    if not self.primary_ema.initialized:
        return

    # Manually feed primary output to secondary
    self.secondary_ema.update_raw(self.primary_ema.value)

    if not self.secondary_ema.initialized:
        return

    # Both are ready — total warmup is primary_period + secondary_period bars
```

### Keeping Indicator History

Indicators only expose the current value. Track history with a deque:

```python
from collections import deque

def on_start(self) -> None:
    self.ema = ExponentialMovingAverage(10)
    self.ema_history = deque(maxlen=100)
    self.register_indicator_for_bars(self.bar_type, self.ema)

def on_bar(self, bar) -> None:
    if self.ema.initialized:
        self.ema_history.append(self.ema.value)
```

## Actors

### What Is an Actor?

An `Actor` is a component that receives data and manages state but **does NOT submit orders**. Use actors for:

- ML model inference
- Feature computation
- Signal aggregation
- Data monitoring/logging

Strategies extend Actor with order management. If your component doesn't trade, make it an Actor.

### Actor Lifecycle

Same state machine as Strategy:
```
PRE_INITIALIZED → READY → STARTING → RUNNING → STOPPING → STOPPED
```

With branches to `DEGRADED` and `FAULTED`.

### Historical vs Real-Time Data

**Critical distinction** that causes frequent confusion:

| Method | Handler | Purpose |
|--------|---------|---------|
| `request_bars()` | `on_historical_data()` | Fetch historical data for warmup |
| `subscribe_bars()` | `on_bar()` | Subscribe to live/streaming bars |

These are **different code paths**. Historical data does NOT go to `on_bar()`.

## Three Messaging Patterns

### 1. Signals (Simplest)

Lightweight notifications with a single primitive value (str, int, float). No custom classes needed.

```python
# Publisher (Actor or Strategy)
self.publish_signal(name="regime", value="trending", ts_event=self.clock.timestamp_ns())

# Subscriber (Strategy)
def on_start(self) -> None:
    self.subscribe_signal("regime")

def on_signal(self, signal) -> None:
    match signal.value:
        case "trending":
            self.enable_trend_following()
        case "mean_reverting":
            self.enable_mean_reversion()
```

**Caveat**: In `on_signal()`, you match on `signal.value`, not `signal.name`.

### 2. Custom Data (Structured)

For complex data with multiple fields. Use `@customdataclass` for serialization support.

```python
from nautilus_trader.core.data import Data
from nautilus_trader.model.custom import customdataclass

@customdataclass
class RegimeData(Data):
    regime: str
    confidence: float
    transition_prob: float

# Publisher
self.publish_data(DataType(RegimeData), data)

# Subscriber
def on_start(self) -> None:
    self.subscribe_data(DataType(RegimeData))

def on_data(self, data) -> None:
    if isinstance(data, RegimeData):
        self.handle_regime(data)
```

`@customdataclass` adds `ts_event`/`ts_init` timestamps and serialization methods (`to_dict`, `to_bytes`, `to_arrow`).

### 3. Raw MessageBus (Low-Level)

Any Python object to any topic string.

```python
from nautilus_trader.common.events import Event
from dataclasses import dataclass

@dataclass
class MyEvent(Event):
    value: float
    TOPIC: str = "my.custom.topic"

# Publisher
self.msgbus.publish("my.custom.topic", event)

# Subscriber
self.msgbus.subscribe("my.custom.topic", self.on_my_event)
```

### When to Use Which

| Pattern | When | Example |
|---------|------|---------|
| Signal | Simple state changes, one value | Regime state ("trending"/"ranging") |
| Custom Data | Structured data, multiple fields | Feature vectors, model predictions |
| Raw MessageBus | Custom events, non-data messages | Timer events, system notifications |

## Actor Example: Regime Detector

```python
from nautilus_trader.trading import Actor, ActorConfig

class RegimeDetectorConfig(ActorConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    lookback: int = 50

class RegimeDetector(Actor):
    def __init__(self, config: RegimeDetectorConfig) -> None:
        super().__init__(config)
        self.bar_type = config.bar_type
        self.lookback = config.lookback
        self.closes = deque(maxlen=config.lookback)

    def on_start(self) -> None:
        self.subscribe_bars(self.bar_type)

    def on_bar(self, bar) -> None:
        self.closes.append(float(bar.close))

        if len(self.closes) < self.lookback:
            return

        # Simple regime detection: compare recent vs historical volatility
        recent_vol = self._volatility(list(self.closes)[-10:])
        full_vol = self._volatility(list(self.closes))

        regime = "high_vol" if recent_vol > full_vol * 1.5 else "low_vol"
        self.publish_signal("regime", regime, ts_event=bar.ts_event)

    def on_stop(self) -> None:
        self.unsubscribe_bars(self.bar_type)
```

Then in your strategy:
```python
def on_start(self) -> None:
    self.subscribe_signal("regime")

def on_signal(self, signal) -> None:
    if signal.value == "high_vol":
        self.reduce_position_size()
```

## Exercises

1. **Cascaded indicator**: Build a strategy with a smoothed RSI (RSI → EMA). How many bars until both are initialized?

2. **Actor + Signal**: Create an actor that detects new highs/lows and publishes signals. Subscribe from a strategy.

3. **Custom Data**: Define a `@customdataclass` with multiple fields (e.g., feature vector). Publish from an actor, consume in a strategy.

4. **Compare patterns**: Implement the same communication using all three patterns (signal, custom data, raw msgbus). Note the trade-offs.

## Checkpoint

You're ready for Stage 07 when:
- [ ] You can register and cascade indicators
- [ ] You understand the Actor vs Strategy distinction (no orders vs orders)
- [ ] You know when to use signals vs custom data vs raw MessageBus
- [ ] You can build an Actor that publishes signals consumed by a Strategy
- [ ] You understand `request_bars()` → `on_historical_data()` vs `subscribe_bars()` → `on_bar()`
