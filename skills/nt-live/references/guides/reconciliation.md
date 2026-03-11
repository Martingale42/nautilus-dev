# Reconciliation in NautilusTrader Live Trading

## What Reconciliation Does

Reconciliation is the process of synchronizing the internal execution state (orders,
fills, positions) with the actual state reported by the venue. In live trading, state
can diverge due to network interruptions, missed WebSocket messages, process restarts,
or venue-side changes that occur while the system is offline.

Without reconciliation, the system could hold stale order states (e.g., believing an
order is open when the venue has already filled or canceled it), leading to incorrect
position tracking and potentially dangerous duplicate orders.

## Reconciliation Flow

The reconciliation process follows a four-phase sequence:

### Phase 1: Connect

All execution clients connect to their respective venues. The system waits up to
`timeout_connection` seconds (default 120s) for all clients to establish connections
and load instruments.

### Phase 2: Fetch Reports (ExecutionMassStatus)

Each execution client generates an `ExecutionMassStatus` containing:

- **OrderStatusReport**: Current state of each order at the venue (status, filled qty,
  avg price, timestamps for accepted/triggered/last update).
- **FillReport**: Individual trade fills with trade ID, last qty, last price,
  commission, and liquidity side.
- **PositionStatusReport**: Net position per instrument at the venue.

The lookback window is controlled by `reconciliation_lookback_mins`. When set to
`None` or `0`, the adapter uses the maximum lookback available from the venue.

### Phase 3: Compare (State Diffing)

The engine compares each venue report against the cached internal state:

- **Orders in cache but not at venue**: May need cancellation or rejection events.
- **Orders at venue but not in cache**: External orders that need to be ingested.
- **State mismatches**: An order cached as "open" but reported as "filled" or "canceled"
  requires bridging events to bring the internal state machine to the correct state.

The function `adjust_fills_for_partial_window` handles the case where a position
lifecycle started before the lookback window. It simulates fills forward to ensure
the reconstructed position matches the venue-reported position, discarding fills from
older lifecycles that crossed zero.

### Phase 4: Resolve (Generate Reconciliation Events)

The reconciliation module provides factory functions for every order lifecycle event,
each tagged with `reconciliation=True`:

| Function                            | Event Generated   | When Used                                    |
|-------------------------------------|-------------------|----------------------------------------------|
| `create_order_accepted_event`       | `OrderAccepted`   | Order at venue but not yet accepted in cache  |
| `create_order_rejected_event`       | `OrderRejected`   | Order rejected; supports report or reason str |
| `create_order_canceled_event`       | `OrderCanceled`   | Venue reports order canceled                  |
| `create_order_expired_event`        | `OrderExpired`    | Venue reports order expired (GTD/GTT)         |
| `create_order_triggered_event`      | `OrderTriggered`  | Stop order triggered at venue                 |
| `create_order_updated_event`        | `OrderUpdated`    | Qty/price/trigger modified at venue           |
| `create_order_filled_event`         | `OrderFilled`     | Direct fill from a `FillReport`               |
| `create_inferred_order_filled_event`| `OrderFilled`     | Fill inferred from `OrderStatusReport` qty    |

**Inferred fills** are generated when the venue reports a filled quantity larger than
what the cache knows, but no individual `FillReport` exists. The function:

1. Computes `fill_qty = report.filled_qty - order.filled_qty` (the missing quantity).
2. Derives the fill price by solving the weighted average equation:
   `fill_price = (report.avg_px * report.filled_qty - order.avg_px * order.filled_qty) / fill_qty`.
   If `order.filled_qty == 0` (first fill), `fill_price = report.avg_px` directly.
3. Infers liquidity side from order type (`MARKET`/`STOP_MARKET` → `TAKER`, else `MAKER`).
4. Estimates commission as `fill_qty * fill_price * instrument.taker_fee * instrument.multiplier`.

See `nautilus_trader/live/reconciliation.py::create_inferred_order_filled_event` for the
exact implementation.

The helper `is_within_single_unit_tolerance` handles rounding discrepancies from venues
(e.g., OKX `fillSz` vs `accFillSz`) by allowing a single-unit tolerance at the
instrument's quantity precision.

## Configuration Options

All reconciliation settings live on `LiveExecEngineConfig`:

### Startup Reconciliation

| Field                              | Default      | Description                                                |
|------------------------------------|--------------|------------------------------------------------------------|
| `reconciliation`                   | `True`       | Enable/disable startup reconciliation                      |
| `reconciliation_lookback_mins`     | `None`       | Lookback window; `None`/`0` = max available from venue     |
| `reconciliation_instrument_ids`    | `None`       | Restrict reconciliation to specific instruments             |
| `filter_unclaimed_external_orders` | `False`      | Drop events for external-strategy orders                   |
| `filter_position_reports`          | `False`      | Ignore position reports (useful with multi-node accounts)  |
| `filtered_client_order_ids`        | `None`       | Explicitly exclude specific client order IDs               |
| `generate_missing_orders`          | `True`       | Auto-generate MARKET orders to align position discrepancy  |
| `reconciliation_startup_delay_secs`| `10.0`       | Delay after startup recon before continuous recon begins   |

### Continuous Reconciliation: In-Flight Checks

| Field                         | Default | Description                                              |
|-------------------------------|---------|----------------------------------------------------------|
| `inflight_check_interval_ms`  | `2000`  | Polling interval for in-flight order status checks       |
| `inflight_check_threshold_ms` | `5000`  | Time before an in-flight order triggers a venue query    |
| `inflight_check_retries`      | `5`     | Max retries for an in-flight order status query          |

### Continuous Reconciliation: Open Order Checks

| Field                                  | Default | Description                                          |
|----------------------------------------|---------|------------------------------------------------------|
| `open_check_interval_secs`             | `None`  | Polling interval; `None` = disabled. Recommend 5-10s |
| `open_check_open_only`                 | `True`  | Only query open orders (lighter API call)            |
| `open_check_lookback_mins`             | `60`    | Window for order history polling                     |
| `open_check_threshold_ms`              | `5000`  | Min time since last event before acting              |
| `open_check_missing_retries`           | `5`     | Retries before resolving missing-at-venue orders     |
| `max_single_order_queries_per_cycle`   | `10`    | Cap on individual order queries per cycle            |
| `single_order_query_delay_ms`          | `100`   | Delay between individual queries (rate limiting)     |

### Continuous Reconciliation: Position Checks

| Field                           | Default | Description                                            |
|---------------------------------|---------|--------------------------------------------------------|
| `position_check_interval_secs`  | `None`  | Polling interval; `None` = disabled. Recommend 30-60s  |
| `position_check_lookback_mins`  | `60`    | Fill report lookback on discrepancy                    |
| `position_check_threshold_ms`   | `5000`  | Min time since last activity before acting             |
| `position_check_retries`        | `3`     | Max retries per instrument before giving up            |

### Timeouts (on NautilusKernelConfig)

| Field                      | Default | Description                                |
|----------------------------|---------|--------------------------------------------|
| `timeout_connection`       | `120.0` | Max seconds to wait for client connections |
| `timeout_reconciliation`   | `30.0`  | Max seconds for reconciliation to complete |

## Retry Patterns for Failed Operations

Source: `nautilus_trader/live/retry.py`

### Exponential Backoff

The `get_exponential_backoff` function computes delay with:
- `delay_initial_ms` (default 500ms): base delay for the first attempt.
- `delay_max_ms` (default 2000ms): ceiling on computed delay.
- `backoff_factor` (default 2): exponential multiplier per attempt.
- `jitter` (default True): randomizes delay between `delay_initial_ms` and the
  computed delay to prevent thundering herd effects. Based on AWS best practices.

### RetryManager

`RetryManager[T]` wraps an async callable with retry logic:

1. Calls the function. On success, returns the result immediately.
2. On exception (if it matches `exc_types`), increments retry count.
3. Optionally runs `retry_check(exception)` -- if it returns `False`, no retry.
4. Sleeps for the computed backoff duration, then retries.
5. After `max_retries` exhausted, logs an error and returns `None`.
6. Supports cancellation via `cancel_event` (checked before each attempt).

Key attributes after execution:
- `result: bool` -- whether the operation succeeded.
- `message: str | None` -- error message on failure.
- `last_exception` -- the last exception encountered.

### RetryManagerPool

`RetryManagerPool[T]` maintains a pool of reusable `RetryManager` instances:

- Pre-allocates `pool_size` managers. If pool is empty, creates new ones on demand.
- `acquire()` returns a cleared manager; `release()` returns it to the pool.
- `shutdown()` cancels all active managers and clears the active set.
- Thread-safe via `asyncio.Lock`.

## Cancellation Handling Patterns

Source: `nautilus_trader/live/cancellation.py`

The `cancel_tasks_with_timeout` function provides structured async task cancellation:

1. Takes a strong snapshot of pending tasks from a `WeakSet` or `set` to prevent
   garbage collection during the cancellation window.
2. Calls `.cancel()` on every pending task.
3. Awaits `asyncio.gather(*tasks, return_exceptions=True)` with a timeout.
4. If the timeout expires (default 5s for tasks, 2s for futures), logs warnings
   identifying each still-pending task by name or ID.

Constants:
- `DEFAULT_FUTURE_CANCELLATION_TIMEOUT = 2.0` -- for external connection futures.
- `DEFAULT_TASK_CANCELLATION_TIMEOUT = 5.0` -- for regular async tasks.

## Error Handling and State Recovery

### Reconciliation Events Are Tagged

Every event created by reconciliation functions carries `reconciliation=True`. This
allows downstream components (strategies, risk engine) to distinguish between
real-time events and synthetic recovery events.

### Dual Reconciliation Paths

Most event factory functions (e.g., `create_order_rejected_event`,
`create_order_canceled_event`) accept an optional `OrderStatusReport`:

- **With report** (startup reconciliation): uses report timestamps and account IDs.
- **Without report** (continuous reconciliation): uses current timestamp and cached
  order data.

### Position Recovery via `calculate_reconciliation_price`

When a position discrepancy is detected, the system calculates what fill price would
move the internal position from its current state to the venue-reported state. This
handles three scenarios:

1. **Flat to position**: fill price = target average price.
2. **Position flip** (sign change): fill price = target average price (value resets).
3. **Accumulation/reduction**: weighted average formula to find the incremental price.

### Partial Window Adjustment

`adjust_fills_for_partial_window` processes an `ExecutionMassStatus` to handle cases
where the position history extends before the lookback window. It:

- Registers all commission currencies encountered.
- Delegates to the Rust core (`nautilus_pyo3.adjust_fills_for_partial_window`) for
  performance-critical simulation.
- Returns adjusted order and fill report dictionaries per instrument, ensuring the
  simulated position after replaying these fills matches the venue-reported position.

### Cache Purging for Long-Running Systems

For HFT or long-running deployments, memory can be managed via purge settings:

| Setting                                | Recommended |
|----------------------------------------|-------------|
| `purge_closed_orders_interval_mins`    | 10-15 min   |
| `purge_closed_orders_buffer_mins`      | 60 min      |
| `purge_closed_positions_interval_mins` | 10-15 min   |
| `purge_closed_positions_buffer_mins`   | 60 min      |
| `purge_account_events_interval_mins`   | 10-15 min   |
| `purge_account_events_lookback_mins`   | 60 min      |
| `purge_from_database`                  | `False`     |

These purge only from in-memory cache by default (`purge_from_database=False`),
preserving the database as the source of truth.
