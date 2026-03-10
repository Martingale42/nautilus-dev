# Stage 07: Live Trading

## Goal

Deploy a backtested strategy to live markets using TradingNode, understand adapters, reconciliation, and production considerations.

## Prerequisites

- Stage 06 complete (can build strategies with actors and indicators)

## Concepts

### Same Code, Different Context

The same strategy runs unchanged across backtest, sandbox, and live. The engine swaps adapters and venues — your `on_bar()`, `on_order_filled()`, etc. remain identical.

### TradingNode

`TradingNode` is the live trading runtime. It manages:
- Async event loop for network I/O
- Adapter connections to exchanges
- State reconciliation on startup
- Graceful shutdown

```python
from nautilus_trader.live.node import TradingNode, TradingNodeConfig

config = TradingNodeConfig(
    trader_id="TRADER-001",
    data_clients={"BINANCE": BinanceDataClientConfig(...)},
    exec_clients={"BINANCE": BinanceExecClientConfig(...)},
    strategies=[ImportableStrategyConfig(...)],
)

node = TradingNode(config=config)
node.run()  # Blocks — runs until Ctrl+C or node.stop()
```

### Important Constraints

1. **One TradingNode per process** — singleton state, no concurrent instances
2. **Do NOT use Jupyter notebooks** — event loop conflicts with the async runtime
3. **Never block in callbacks** — no `time.sleep()`, no synchronous HTTP, no heavy computation in `on_bar()` or `on_order_filled()`
4. **Windows**: Wrap `node.run()` in `try/except KeyboardInterrupt` (limited signal handling)

## Adapters

Adapters connect NT to external venues. Each adapter has up to five components:

| Component | Purpose |
|-----------|---------|
| `HttpClient` | REST API calls |
| `WebSocketClient` | Real-time streaming |
| `InstrumentProvider` | Instrument discovery |
| `DataClient` | Market data subscriptions |
| `ExecutionClient` | Order management |

### Supported Integrations

NT has adapters for Binance (spot/futures/options), Interactive Brokers, Bybit, dYdX, Databento, Polymarket, Betfair, and more. Check the `nautilus_trader/adapters/` directory for the full list.

### InstrumentProvider (Standalone Usage)

You can use an InstrumentProvider outside of a TradingNode for research:

```python
provider = BinanceSpotInstrumentProvider(client=client, config=config)
await provider.load_all()
instruments = provider.list_all()
```

Or selectively:
```python
provider = BinanceSpotInstrumentProvider(
    client=client,
    config=InstrumentProviderConfig(load_ids=["BTCUSDT.BINANCE", "ETHUSDT.BINANCE"]),
)
```

## Reconciliation

When a TradingNode starts, it reconciles internal state with the venue's reality.

### Startup Reconciliation

1. Node connects to venue
2. Queries open orders and positions from venue
3. Compares with internal cache state
4. Resolves discrepancies (e.g., fills that occurred while offline)

### Continuous Reconciliation

During runtime, the execution engine monitors in-flight and open orders:

```python
config = TradingNodeConfig(
    exec_engine=LiveExecEngineConfig(
        reconciliation=True,
        reconciliation_lookback_mins=60,  # How far back to check
    ),
)
```

**Pitfall**: Setting `reconciliation_lookback_mins` too small can miss fills that happened while offline. Too large increases startup time.

## State Persistence

### Redis-Backed Cache

For surviving restarts, configure Redis:

```python
config = TradingNodeConfig(
    cache=CacheConfig(
        database=DatabaseConfig(type="redis", host="localhost", port=6379),
    ),
)
```

This persists orders, positions, and account state to Redis. On restart, state is recovered before reconciliation.

### External MessageBus

For multi-node architectures, the MessageBus can publish to Redis streams:

```python
config = TradingNodeConfig(
    message_bus=MessageBusConfig(
        database=DatabaseConfig(type="redis", host="localhost", port=6379),
        encoding="msgpack",  # or "json" for debugging
        types_filter=["QuoteTick"],  # Exclude high-frequency types
    ),
)
```

## Production Considerations

### Logging

```python
from nautilus_trader.config import LoggingConfig

config = TradingNodeConfig(
    logging=LoggingConfig(
        log_level="INFO",           # Console level
        log_level_file="DEBUG",     # File level (more verbose)
        log_directory="./logs",
        log_file_format="{trader_id}_{instance_id}",
    ),
)
```

NT logging is Rust-based — high-performance, runs on a separate thread via MPSC channel.

### Graceful Shutdown

```python
# Linux/macOS: Ctrl+C sends SIGINT → node.stop()
# Windows: wrap in try/except
try:
    node.run()
except KeyboardInterrupt:
    node.stop()
```

`on_stop()` is called on all strategies during shutdown. Use it to cancel timers, flatten positions if needed.

### Risk Management

The RiskEngine validates every order in live trading too:

- Price/quantity precision checks
- Max notional limits
- Min/max quantity limits
- Reduce-only validation

Trading state can be set to `HALTED` or `REDUCING` for emergency stops:

```python
# From within a strategy
self.msgbus.publish("RiskEngine.set_trading_state", TradingState.HALTED)
```

## Sandbox Mode

For paper trading with real-time data but simulated execution:

```python
# Same as live, but use simulated venue
config = TradingNodeConfig(
    # Real data adapter
    data_clients={"BINANCE": BinanceDataClientConfig(...)},
    # Simulated execution (no real exec client)
    # Strategies execute against simulated venue
)
```

This lets you validate real-time behavior without risking capital.

## Exercises

1. **Read adapter configs**: Look at the configuration classes for an adapter you plan to use (e.g., `BinanceSpotDataClientConfig`). What parameters are required?

2. **InstrumentProvider**: Use a provider standalone to list available instruments from an exchange.

3. **Compare backtest vs live config**: Take your backtest from Stage 05 and write the equivalent `TradingNodeConfig` for live trading. What changes?

4. **Logging exploration**: Run a backtest with different log levels (`DEBUG` vs `INFO`). How does the output differ?

## Checkpoint

You're ready for Stage 08 when:
- [ ] You understand how TradingNode differs from BacktestEngine
- [ ] You know what adapters do and their five components
- [ ] You understand reconciliation (startup and continuous)
- [ ] You know the production constraints (one node, no blocking, no Jupyter)
- [ ] You can explain how Redis-backed cache and message bus enable state persistence
