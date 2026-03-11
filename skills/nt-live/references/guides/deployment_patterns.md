# Deployment Patterns for NautilusTrader Live Trading

## TradingNode Lifecycle

The `TradingNode` class (in `nautilus_trader/live/node.py`) is the top-level entry
point for live trading. Its lifecycle follows four distinct phases:

### Phase 1: Build

```python
node = TradingNode(config=config)
node.add_data_client_factory("BINANCE", BinanceLiveDataClientFactory)
node.add_exec_client_factory("BINANCE", BinanceLiveExecClientFactory)
node.build()
```

During build:
1. The `NautilusKernel` is created with all core engines (data, risk, execution).
2. A `TradingNodeBuilder` is instantiated, holding references to all engines.
3. Client factories are registered by name.
4. `build()` calls `build_data_clients()` and `build_exec_clients()` on the builder,
   which instantiates each client from its factory and registers it with the
   corresponding engine. Venue routing is configured at this stage.
5. The `_is_built` flag is set to `True`. Calling `build()` again raises `RuntimeError`.

### Phase 2: Run

```python
node.run()
```

The `run()` method either creates an async task (if the loop is already running) or
calls `loop.run_until_complete(run_async())`. The async flow:

1. Validates that `build()` was called.
2. Calls `kernel.start_async()`, which connects all clients, runs reconciliation,
   initializes portfolio, and starts all strategies.
3. Creates queue processing tasks for all engines:
   - DataEngine: cmd, req, res, data queues
   - RiskEngine: cmd, evt queues
   - ExecEngine: cmd, evt queues
4. If external message streaming is configured, starts the streaming task.
5. Awaits `asyncio.gather(*tasks)` -- the node stays alive as long as queues process.

### Phase 3: Stop

```python
node.stop()
```

Calls `kernel.stop_async()` which:
- Stops all strategies (optionally saving state if `save_state=True`).
- Disconnects all data and execution clients.
- Waits for engine queues to drain.

### Phase 4: Dispose

```python
node.dispose()
```

Final cleanup:
1. Waits up to `timeout_disconnection` seconds for the kernel to stop running.
2. If timeout expires, logs disconnection status of DataEngine and ExecEngine.
3. Cancels the streaming task if active.
4. Calls `kernel.dispose()` to release all resources.
5. Shuts down the thread pool executor.
6. Stops or closes the event loop.
7. Logs final loop state (`is_running`, `is_closed`).

### Signal Handling

The node registers `_loop_sig_handler` as the signal callback. On receiving SIGINT
or SIGTERM, it logs a warning and calls `stop()`, triggering graceful shutdown.

## TradingNodeConfig Options

`TradingNodeConfig` extends `NautilusKernelConfig` with live-specific defaults.

### Identity and Environment

| Field         | Type          | Default        | Description                           |
|---------------|---------------|----------------|---------------------------------------|
| `environment` | `Environment` | `LIVE`         | Context: `BACKTEST`, `SANDBOX`, `LIVE`|
| `trader_id`   | `TraderId`    | `"TRADER-001"` | Unique trader identity (NAME-TAG)     |
| `instance_id` | `UUID4`       | `None`         | Unique kernel instance ID (auto-gen)  |

### Engine Configurations

| Field          | Type                    | Description                         |
|----------------|-------------------------|-------------------------------------|
| `data_engine`  | `LiveDataEngineConfig`  | Queue sizes, shutdown behavior      |
| `risk_engine`  | `LiveRiskEngineConfig`  | Queue sizes, shutdown behavior      |
| `exec_engine`  | `LiveExecEngineConfig`  | Reconciliation, in-flight checks    |

Each engine config has `qsize` (default 100,000) for internal queue buffers and
`graceful_shutdown_on_exception` (default `False`) for controlled shutdown on
unexpected queue processing errors.

### Client Configuration

| Field          | Type                                           | Description                |
|----------------|------------------------------------------------|----------------------------|
| `data_clients` | `dict[str, LiveDataClientConfig]`              | Data client configs by name|
| `exec_clients` | `dict[str, LiveExecClientConfig]`              | Exec client configs by name|

Client configs include:
- `instrument_provider`: `InstrumentProviderConfig` for instrument loading.
- `routing`: `RoutingConfig` with `default: bool` and `venues: frozenset[str]`.

### Infrastructure

| Field         | Type               | Description                                       |
|---------------|--------------------|---------------------------------------------------|
| `cache`       | `CacheConfig`      | Database backing for cache persistence             |
| `message_bus` | `MessageBusConfig` | External streams, database backing for message bus |
| `portfolio`   | `PortfolioConfig`  | Portfolio configuration                            |
| `emulator`    | `OrderEmulatorConfig` | Client-side order emulation                     |
| `streaming`   | `StreamingConfig`  | Feather file streaming for analysis                |
| `catalogs`    | `list[DataCatalogConfig]` | Data catalog sources                        |

### Strategy and Actor Loading

| Field             | Type                               | Description                       |
|-------------------|------------------------------------|-----------------------------------|
| `actors`          | `list[ImportableActorConfig]`      | Actor configurations              |
| `strategies`      | `list[ImportableStrategyConfig]`   | Strategy configurations           |
| `exec_algorithms` | `list[ImportableExecAlgorithmConfig]` | Execution algorithm configs    |
| `controller`      | `ImportableControllerConfig`       | Trader controller                 |

### State Management

| Field        | Type   | Default | Description                                 |
|--------------|--------|---------|---------------------------------------------|
| `load_state` | `bool` | `False` | Load strategy state from database on start  |
| `save_state` | `bool` | `False` | Save strategy state to database on stop     |
| `loop_debug` | `bool` | `False` | Enable asyncio event loop debug mode        |

### Timeouts

| Field                      | Default  | Description                                      |
|----------------------------|----------|--------------------------------------------------|
| `timeout_connection`       | `120.0`  | Max wait for all clients to connect/initialize   |
| `timeout_reconciliation`   | `30.0`   | Max wait for execution state reconciliation      |
| `timeout_portfolio`        | `10.0`   | Max wait for portfolio margin/PnL initialization |
| `timeout_disconnection`    | `10.0`   | Max wait for all clients to disconnect           |
| `timeout_post_stop`        | `10.0`   | Wait for residual events after stop              |
| `timeout_shutdown`         | `5.0`    | Wait for pending task cancellation               |

### Logging

The `logging` field accepts a `LoggingConfig` object. Configure log level, format,
and output targets here. The node logs cache/msgbus backing status at startup:

```
has_cache_backing=True
has_msgbus_backing=False
```

## Multi-Adapter Setup

NautilusTrader supports multiple data and execution clients simultaneously. The
naming convention uses the dict key format `"NAME"` or `"NAME-suffix"` where the
prefix before the first hyphen identifies the factory.

### Example: Two Exchanges

```python
config = TradingNodeConfig(
    data_clients={
        "BINANCE": BinanceLiveDataClientConfig(
            routing=RoutingConfig(venues=frozenset({"BINANCE"})),
        ),
        "BYBIT": BybitLiveDataClientConfig(
            routing=RoutingConfig(venues=frozenset({"BYBIT"})),
        ),
    },
    exec_clients={
        "BINANCE": BinanceLiveExecClientConfig(
            routing=RoutingConfig(venues=frozenset({"BINANCE"})),
        ),
        "BYBIT": BybitLiveExecClientConfig(
            routing=RoutingConfig(venues=frozenset({"BYBIT"})),
        ),
    },
)
```

### Routing Rules

Each client config has a `RoutingConfig`:
- `default: bool` -- register as the default client when no venue-specific routing
  matches. Only one client should be the default.
- `venues: frozenset[str]` -- explicit venue-to-client routing. When a request or
  command targets a specific venue, the engine routes it to the registered client.

The builder calls `register_venue_routing(client, venue)` for each venue in the set,
and `register_default_client(client)` if `default=True`.

### Multiple Clients per Adapter

Use the `"NAME-suffix"` key format for multiple clients from the same adapter:

```python
data_clients={
    "BINANCE-spot": BinanceLiveDataClientConfig(...),
    "BINANCE-futures": BinanceLiveDataClientConfig(...),
}
```

The builder extracts the factory name by splitting on the first hyphen:
`parts.partition("-")[0]`.

## Logging and Monitoring Configuration

### LoggingConfig

Pass a `LoggingConfig` to `TradingNodeConfig.logging` to control:
- Log level (DEBUG, INFO, WARNING, ERROR)
- Output format
- File or stdout targets

### Cache and Message Bus Backing

For production deployments, enable database backing:

```python
config = TradingNodeConfig(
    cache=CacheConfig(database=DatabaseConfig(...)),
    message_bus=MessageBusConfig(database=DatabaseConfig(...)),
)
```

The node logs whether backing is enabled at startup for quick verification.

### External Message Streaming

When `message_bus.external_streams` is configured, the node starts a streaming task
that listens to external bus messages, deserializes them, processes them through any
registered stream processors, and publishes them on the internal message bus.

Add custom stream processors via `node.add_stream_processor(callback)`.

## Graceful Shutdown Patterns

### Signal-Based Shutdown

The node registers a signal handler that calls `stop()` on SIGINT/SIGTERM. This is
the primary mechanism for production shutdown.

### Programmatic Shutdown

```python
node.stop()       # Async stop: disconnects clients, drains queues
node.dispose()    # Final cleanup: executor, event loop, resources
```

### Timeout Protection in Dispose

The `dispose()` method has layered timeout protection:

1. Polls `kernel.is_running()` every 100ms up to `timeout_disconnection` seconds.
2. If the kernel is still running after timeout, logs a warning with disconnection
   status for both DataEngine and ExecEngine, then continues with disposal anyway.
3. Cancels the streaming task if it exists.
4. Shuts down the thread pool executor with `wait=True, cancel_futures=True`.
5. Handles both `asyncio.CancelledError` and `RuntimeError` during disposal.

### Task Cancellation

The cancellation module (`nautilus_trader/live/cancellation.py`) provides
`cancel_tasks_with_timeout`:

- Takes a strong snapshot of tasks from a `WeakSet` to prevent GC during cancellation.
- Cancels all pending tasks and awaits completion with configurable timeout.
- Default timeouts: 5s for tasks, 2s for futures (external connections).
- Logs warnings for any tasks that fail to complete within the timeout window.

### RetryManagerPool Shutdown

On component stop, `RetryManagerPool.shutdown()` cancels all active retry managers
and clears the active set, preventing orphaned retry loops.

## Health Check Patterns

NautilusTrader does not expose a dedicated HTTP health endpoint, but provides
several internal mechanisms for monitoring system health:

### Engine Disconnection Checks

During shutdown, the node queries:
- `data_engine.check_disconnected()` -- returns `True` if all data clients are
  disconnected.
- `exec_engine.check_disconnected()` -- returns `True` if all exec clients are
  disconnected.

These are logged during timeout scenarios in `dispose()`.

### Continuous Reconciliation as Health Monitoring

The `LiveExecEngineConfig` continuous reconciliation settings serve as an implicit
health check system:

- **In-flight order checks** (every 2s by default): detect stuck orders.
- **Open order checks** (configurable, recommend 5-10s): detect order state drift.
- **Position checks** (configurable, recommend 30-60s): detect fill loss.

### Own Book Auditing

Setting `own_books_audit_interval_secs` enables periodic auditing of internal order
books against public order book data. Discrepancies are logged as errors.

### Queue Task Monitoring

The `run_async()` method monitors engine queue tasks. If any queue task completes
unexpectedly, the `_handle_run_task_result` callback logs the exception. The
streaming task has its own `_handle_streaming_exception` callback.

### Recommended Production Configuration

```python
exec_engine=LiveExecEngineConfig(
    reconciliation=True,
    reconciliation_lookback_mins=120,
    open_check_interval_secs=10.0,
    open_check_missing_retries=5,
    position_check_interval_secs=30.0,
    position_check_retries=3,
    inflight_check_interval_ms=2_000,
    inflight_check_threshold_ms=5_000,
)
```

This provides three layers of continuous health monitoring alongside the startup
reconciliation.
