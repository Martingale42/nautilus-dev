# Stage 04: First Strategy

## Goal

Write a trading strategy from scratch that submits orders, manages positions, and uses indicators.

## Prerequisites

- Stage 03 complete (understand architecture, data model, cache, messaging)

## Concepts

### Strategy Lifecycle

A `Strategy` extends `Actor` with order management. The lifecycle is:

```
__init__() → on_start() → [on_bar / on_quote_tick / on_trade_tick / ...] → on_stop()
```

**Critical rule**: Do NOT use `self.clock`, `self.log`, or `self.cache` in `__init__()`. These are injected later during registration. Use `on_start()` for initialization.

### StrategyConfig

Strategies use a frozen config object for parameters:

```python
from nautilus_trader.trading import Strategy, StrategyConfig

class MyConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    ema_period: int = 20

class MyStrategy(Strategy):
    def __init__(self, config: MyConfig) -> None:
        super().__init__(config)
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type
        self.ema_period = config.ema_period
```

### Handler Hierarchy

When an order event occurs, handlers fire in sequence (most specific → most general):
1. `on_order_filled(event)` — specific handler
2. `on_order_event(event)` — catch-all order handler
3. `on_event(event)` — catch-all event handler

Same for positions: `on_position_opened` → `on_position_event` → `on_event`.

## Building a Simple EMA Cross Strategy

### Step 1: Define Config

```python
from nautilus_trader.model import InstrumentId
from nautilus_trader.model.data import BarType
from nautilus_trader.trading import StrategyConfig

class EMACrossConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    fast_period: int = 10
    slow_period: int = 20
    trade_size: float = 1.0
```

### Step 2: Write the Strategy

```python
from nautilus_trader.indicators.average.ema import ExponentialMovingAverage
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.trading import Strategy

class EMACross(Strategy):
    def __init__(self, config: EMACrossConfig) -> None:
        super().__init__(config)
        # Store config values (OK in __init__)
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type
        self.trade_size = config.trade_size

        # Create indicators (OK in __init__ — they don't need system access)
        self.fast_ema = ExponentialMovingAverage(config.fast_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_period)

    def on_start(self) -> None:
        # Load instrument from cache
        self.instrument = self.cache.instrument(self.instrument_id)

        # Register indicators for automatic bar updates
        self.register_indicator_for_bars(self.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.bar_type, self.slow_ema)

        # Request historical data (goes to on_historical_data, NOT on_bar)
        self.request_bars(self.bar_type)

        # Subscribe to live/streaming data (goes to on_bar)
        self.subscribe_bars(self.bar_type)

    def on_bar(self, bar) -> None:
        # Wait for both EMAs to be initialized
        if not self.fast_ema.initialized or not self.slow_ema.initialized:
            return

        # Check if flat (no position)
        if self.portfolio.is_flat(self.instrument_id):
            if self.fast_ema.value > self.slow_ema.value:
                self._buy()
            elif self.fast_ema.value < self.slow_ema.value:
                self._sell()

    def _buy(self) -> None:
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(self.trade_size),
        )
        self.submit_order(order)

    def _sell(self) -> None:
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.SELL,
            quantity=self.instrument.make_qty(self.trade_size),
        )
        self.submit_order(order)

    def on_stop(self) -> None:
        # Flatten all positions on stop
        self.close_all_positions(self.instrument_id)
```

### Step 3: Key Patterns

1. **`instrument.make_qty()` / `instrument.make_price()`** — Always use these. The RiskEngine rejects orders with wrong precision.

2. **`register_indicator_for_bars()`** — Indicators auto-update before `on_bar()` is called. No manual `indicator.update()` needed.

3. **`request_bars()` vs `subscribe_bars()`** — Request gets historical data (for warmup). Subscribe gets live/streaming data. Both are typically called in `on_start()`.

4. **`self.order_factory`** — Built-in factory for creating orders. Handles ID generation. Multiple strategy instances must use unique `order_id_tag` values.

5. **`self.portfolio.is_flat()`** — Check position state through Portfolio, not by tracking your own boolean.

## Order Types

```python
# Market order
order = self.order_factory.market(instrument_id, OrderSide.BUY, quantity)

# Limit order
order = self.order_factory.limit(instrument_id, OrderSide.BUY, quantity, price)

# Stop market
order = self.order_factory.stop_market(instrument_id, OrderSide.SELL, quantity, trigger_price)

# Bracket order (entry + take-profit + stop-loss)
bracket = self.order_factory.bracket(
    instrument_id=instrument_id,
    order_side=OrderSide.BUY,
    quantity=quantity,
    entry_trigger_price=entry_price,   # or entry_price for limit entry
    sl_trigger_price=stop_price,
    tp_price=take_profit_price,
)
self.submit_order_list(bracket)
```

## Exercises

1. **Build the EMA cross strategy** above and run it with `example_01`'s engine setup pattern, using test data.

2. **Add position tracking**: Override `on_position_opened()` and `on_position_closed()` to log position details.

3. **Add a bracket order variant**: Instead of a plain market order, submit a bracket order with take-profit and stop-loss.

4. **Try multiple order_id_tags**: Run two instances of your strategy with different parameters and unique `order_id_tag` values.

## Checkpoint

You're ready for Stage 05 when:
- [ ] You can write a strategy that submits orders and reacts to fills
- [ ] You understand `on_start()` vs `__init__()` initialization
- [ ] You know why `instrument.make_price()` / `instrument.make_qty()` are required
- [ ] You can register indicators and check `indicator.initialized` before using values
- [ ] You understand the difference between `request_bars()` (historical) and `subscribe_bars()` (live)
