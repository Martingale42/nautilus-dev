---
name: nt-adapters
description: "Use when working with exchange or data provider adapters, HTTP/WebSocket clients, instrument providers, or venue integration in NautilusTrader."
---

# nt-adapters

## What This Skill Covers

NautilusTrader **adapter domain** — exchange/data provider integrations, HTTP/WebSocket clients, and instrument providers.

**Python modules**: `adapters/*` (16 adapters), `adapters/_template/`
**Rust crates**: All 16 `adapters/*` crates, `nautilus_network`, `nautilus_cryptography`

**Supported adapters**: Binance, Bybit, OKX, Kraken, Deribit, dYdX, Hyperliquid, BitMEX, Interactive Brokers, Databento, Tardis, Betfair, Polymarket, Architect (AX), Blockchain, Shioaji

## When To Use

- Configuring an existing adapter for live trading
- Building a new exchange or data provider adapter
- Customizing instrument providers
- Working with HTTP/WebSocket client patterns
- Understanding adapter testing specifications
- Venue-specific data parsing or execution logic

## When NOT To Use

- **Live node system config** → use `nt-live`
- **Strategy logic** → use `nt-trading`
- **Data persistence** → use `nt-data`
- **Domain model types** → use `nt-model`

## Python Usage

### Configure Existing Adapter

```python
from nautilus_trader.adapters.binance.config import BinanceDataClientConfig, BinanceExecClientConfig
from nautilus_trader.adapters.binance.factories import BinanceLiveDataClientFactory, BinanceLiveExecClientFactory

data_config = BinanceDataClientConfig(
    api_key="...",
    api_secret="...",
    account_type=BinanceAccountType.USDT_FUTURE,
)

exec_config = BinanceExecClientConfig(
    api_key="...",
    api_secret="...",
    account_type=BinanceAccountType.USDT_FUTURE,
)
```

### Use InstrumentProvider

```python
# Instrument discovery happens automatically when adapter connects
# Access instruments via cache:
instruments = self.cache.instruments(venue=Venue("BINANCE"))
instrument = self.cache.instrument(InstrumentId.from_str("ETHUSDT-PERP.BINANCE"))
```

### Adapter Configuration Pattern

Each adapter follows the same config pattern:
- `{Adapter}DataClientConfig` — data feed configuration
- `{Adapter}ExecClientConfig` — execution configuration
- `{Adapter}InstrumentProviderConfig` — instrument discovery settings

## Python Extension

### Customize Instrument Provider

```python
from nautilus_trader.adapters.binance.providers import BinanceInstrumentProvider

class MyInstrumentProvider(BinanceInstrumentProvider):
    async def load_all_async(self, filters=None):
        await super().load_all_async(filters)
        # Add custom instrument filtering/transformation
```

### Add Venue-Specific Parsing

Extend data/exec clients to handle venue-specific message formats or additional endpoints.

## Rust Usage

### Using Adapters with Rust LiveNode

Each Rust adapter provides factory and config types for wiring into a `LiveNode`. The pattern is the same across all adapters:

```rust
use nautilus_live::node::LiveNode;
use nautilus_model::identifiers::{AccountId, TraderId};
use nautilus_common::enums::Environment;

// Import adapter-specific types
use nautilus_binance::{
    common::enums::BinanceProductType,
    config::{BinanceDataClientConfig, BinanceExecClientConfig},
    factories::{BinanceDataClientFactory, BinanceExecutionClientFactory},
};

let data_config = BinanceDataClientConfig {
    product_types: vec![BinanceProductType::UsdM],
    ..Default::default()
};

let exec_config = BinanceExecClientConfig {
    trader_id: TraderId::from("TRADER-001"),
    account_id: AccountId::from("BINANCE-001"),
    product_types: vec![BinanceProductType::UsdM],
    ..Default::default()
};

let mut node = LiveNode::builder(trader_id, Environment::Live)?
    .add_data_client(
        None,
        Box::new(BinanceDataClientFactory::new()),
        Box::new(data_config),
    )?
    .add_exec_client(
        None,
        Box::new(BinanceExecutionClientFactory::new()),
        Box::new(exec_config),
    )?
    .build()?;
```

### Adapter Factory Pattern (Rust)

Each adapter exposes:
- `{Adapter}DataClientConfig` — data feed configuration
- `{Adapter}ExecClientConfig` — execution configuration
- `{Adapter}DataClientFactory` — creates data client instances
- `{Adapter}ExecutionClientFactory` — creates execution client instances

### Available Rust Adapters

| Adapter | Crate | Data | Execution |
|---|---|---|---|
| Architect AX | `nautilus-architect-ax` | Yes | Yes |
| Betfair | `nautilus-betfair` | Yes | Yes |
| Binance | `nautilus-binance` | Yes | Yes |
| BitMEX | `nautilus-bitmex` | Yes | Yes |
| Bybit | `nautilus-bybit` | Yes | Yes |
| Databento | `nautilus-databento` | Yes | No |
| Deribit | `nautilus-deribit` | Yes | Yes |
| dYdX | `nautilus-dydx` | Yes | Yes |
| Hyperliquid | `nautilus-hyperliquid` | Yes | Yes |
| Kraken | `nautilus-kraken` | Yes | Yes |
| OKX | `nautilus-okx` | Yes | Yes |
| Polymarket | `nautilus-polymarket` | Yes | Yes |
| Sandbox | `nautilus-sandbox` | Yes | Yes |
| Tardis | `nautilus-tardis` | Yes | No |

### Adapter Runnable Examples

Most adapters include `node_data_tester.rs` and `node_exec_tester.rs`:

```bash
# Run a data tester
cargo run -p nautilus-binance --example node-data-tester-futures

# Run an execution tester
cargo run -p nautilus-okx --example node-exec-tester
```

See `references/examples/rust_adapters/` for all adapter examples.

### Environment Variables

Adapters read credentials from environment variables. Common pattern with `dotenvy`:

```rust
dotenvy::dotenv().ok();
// Adapter reads OKX_API_KEY, OKX_API_SECRET, etc. automatically
```

Each adapter's integration guide documents its required variables.

## Rust Extension

### Build New Adapter in Rust

A new adapter requires these components:

1. **HTTP Client** — for REST API calls
2. **WebSocket Client** — for streaming data
3. **InstrumentProvider** — instrument discovery
4. **DataClient** — market data feed
5. **ExecutionClient** — order execution (if exchange)
6. **Factory** — client instantiation for `LiveNode` builder

```rust
use nautilus_network::http::HttpClient;
use nautilus_network::websocket::WebSocketClient;

pub struct MyExchangeDataClient {
    http_client: HttpClient,
    ws_client: WebSocketClient,
}

impl MyExchangeDataClient {
    pub fn new(config: MyExchangeConfig) -> Self { /* ... */ }
    pub fn connect(&mut self) -> anyhow::Result<()> { /* ... */ }
    pub fn subscribe_trade_ticks(&mut self, instrument_id: InstrumentId) -> anyhow::Result<()> { /* ... */ }
}
```

### Factory Implementation

Implement the factory trait so `LiveNode::builder().add_data_client()` can construct your client:

```rust
pub struct MyDataClientFactory;

impl MyDataClientFactory {
    pub fn new() -> Self { Self }
}
```

### PyO3 Bindings (Optional)

For Python access, add `#[pyclass]` configs with dispatch in `add_native_strategy`:
- Use `#[pyclass]` and `#[pymethods]` for Python-visible types
- Register in `crates/pyo3/src/lib.rs`
- GIL management: use `Python::attach()` for callback forwarding
- See `references/guides/ffi.md` for detailed FFI patterns
- See `references/guides/rust.md` for Rust coding standards

## Key Conventions

### Adapter Testing Specifications

Data client testing (TC-D01 to TC-D72):
- Instrument loading, data subscription, historical data requests
- See `references/guides/spec_data_testing.md`

Execution client testing (TC-E01+):
- Order submission, cancellation, modification, account queries
- See `references/guides/spec_exec_testing.md`

### Adapter Naming

- Module: `nautilus_trader/adapters/{name}/`
- Config: `{Name}DataClientConfig`, `{Name}ExecClientConfig`
- Factory: `{Name}LiveDataClientFactory`, `{Name}LiveExecClientFactory`
- Provider: `{Name}InstrumentProvider`

### Factory Pattern

Adapters use factory pattern for client instantiation:
```python
class MyAdapterLiveDataClientFactory(LiveDataClientFactory):
    @staticmethod
    def create(loop, name, config, msgbus, cache, clock):
        return MyDataClient(...)
```

### Integration Docs

Each supported venue has detailed integration documentation covering:
- Authentication setup
- Supported instruments and data types
- Rate limits and API specifics
- Known limitations
- See `references/integrations/` for per-venue docs

## References

- `references/concepts/` — adapters, live trading
- `references/api/` — adapter APIs (per-venue), live API
- `references/integrations/` — per-venue integration guides (16 venues)
- `references/guides/` — adapter development, data/exec testing specs, FFI, Rust, coding standards
- `references/examples/` — live adapter examples (per-venue), Rust adapter examples
- `templates/` — data_provider.py, exchange.py
