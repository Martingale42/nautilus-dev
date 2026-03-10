---
name: nt-adapter-dev
description: "Use when building or modifying NT exchange/data adapters. Guides source exploration for adapter architecture, HTTP/WebSocket clients, instrument providers, data/execution clients, and testing."
---

# NT Adapter Development

## Overview

Build and extend NautilusTrader exchange and data provider adapters: Rust core networking (HTTP/WebSocket clients), instrument providers, data clients, execution clients, factory classes, and Python bindings. Covers adapter architecture patterns, venue-specific normalization, rate limiting, reconnection, and testing against the data/execution spec matrices.

## Exploration Sequence

1. **Read bundled references/** — concept docs first for understanding, then integration docs for venue-specific patterns, then API reference for type signatures
2. **Check cached/** — look for annotated excerpts from previous exploration sessions
3. **Explore NT source** — ask user: "Where is your local NautilusTrader repo?" If no local path, browse via `gh api repos/nautechsystems/nautilus_trader/contents/<path>`
4. **context7** — supplementary docs if gaps remain

## Concept Docs

Read these first for conceptual understanding:

- `references/concepts/adapters.md` — adapter architecture, component diagram, instrument providers, data/execution clients
- `references/concepts/live.md` — live trading configuration, TradingNodeConfig, execution reconciliation, continuous reconciliation, memory management

## Integration Docs

Read these for venue-specific adapter patterns and capabilities:

- `references/integrations/index.md` — integration listing, status, implementation goals
- `references/integrations/binance.md` — Binance spot/futures, symbology, order types, rate limiting, configuration
- `references/integrations/bybit.md` — Bybit products, symbology, order types, batch operations, configuration
- `references/integrations/databento.md` — Databento data provider, DBN format, schemas, historical loading
- `references/integrations/betfair.md` — Betfair betting exchange, tick scheme, order modification, streaming
- `references/integrations/dydx.md` — dYdX v4 Cosmos chain, gRPC, block-based settlement, order classification
- `references/integrations/blockchain.md` — blockchain/DeFi primitives, ERC20, Multicall3
- `references/integrations/deribit.md` — Deribit options/futures, JSON-RPC, order book feeds, credit-based rate limiting
- `references/integrations/architect_ax.md` — AX Exchange perpetuals on traditional assets
- `references/integrations/hyperliquid.md` — Hyperliquid DEX, price normalization, vault trading
- `references/integrations/kraken.md` — Kraken crypto exchange
- `references/integrations/okx.md` — OKX crypto exchange
- `references/integrations/tardis.md` — Tardis crypto data provider
- `references/integrations/polymarket.md` — Polymarket prediction market, binary options, wallet signing
- `references/integrations/ib.md` — Interactive Brokers multi-asset, TWS API, Docker gateway
- `references/integrations/bitmex.md` — BitMEX derivatives

## Developer Guide

For adapter implementation patterns and testing:

- `references/developer_guide/adapters.md` — full adapter development spec: Rust core structure, Python layer, HTTP/WebSocket clients, parsing, instrument providers, data/execution clients, factory classes, testing
- `references/developer_guide/spec_data_testing.md` — data testing spec TC-D01 to TC-D72: instruments, order book, quotes, trades, bars, derivatives data, lifecycle
- `references/developer_guide/spec_exec_testing.md` — execution testing spec TC-E01+: order types, modifications, cancellations, reconciliation, position management

## API Reference

For type signatures and class APIs:

- `references/api_reference/live.md` — LiveDataClient, LiveExecutionClient, LiveDataEngine, LiveExecEngine, TradingNode
- `references/api_reference/adapters/index.md` — adapters module index
- `references/api_reference/adapters/binance.md` — Binance adapter API (config, factories, enums, types, data, execution, providers)
- `references/api_reference/adapters/bybit.md` — Bybit adapter API
- `references/api_reference/adapters/databento.md` — Databento adapter API
- `references/api_reference/adapters/betfair.md` — Betfair adapter API
- `references/api_reference/adapters/polymarket.md` — Polymarket adapter API
- `references/api_reference/adapters/okx.md` — OKX adapter API
- `references/api_reference/adapters/tardis.md` — Tardis adapter API
- `references/api_reference/adapters/interactive_brokers.md` — Interactive Brokers adapter API
- `references/api_reference/adapters/dydx.md` — dYdX adapter API

## Source Entry Points

Explore these paths (local or via GitHub):

- `crates/adapters/` — Rust adapter implementations (HTTP/WebSocket clients, parsing, Python bindings)
- `crates/network/` — Rust networking primitives (HttpClient, WebSocketClient, rate limiting)
- `nautilus_trader/adapters/` — Python-side adapter implementations
- `nautilus_trader/live/` — Python-side live trading infrastructure (LiveDataClient, LiveExecutionClient, TradingNode)

## Key Types

Find and understand these before implementing:

**Rust crates/network:**
- `HttpClient` — async HTTP client with rate limiting
- `WebSocketClient` — async WebSocket client with reconnection

**Python nautilus_trader/live:**
- `LiveDataClient` — base class for live data feed clients
- `LiveExecutionClient` — base class for live execution clients
- `LiveDataEngine` — manages live data clients
- `LiveExecutionEngine` — manages live execution clients

**Python nautilus_trader/adapters (per adapter):**
- `DataClientAdapter` — adapter-specific data client implementation
- `ExecutionClientAdapter` — adapter-specific execution client implementation
- `InstrumentProvider` — loads and parses venue instrument definitions
- `LiveDataClientFactory` — factory for creating data clients
- `LiveExecClientFactory` — factory for creating execution clients

## Patterns to Study

- **Adapter architecture:** Compare Binance vs Bybit vs OKX for the layered pattern: Rust HTTP/WebSocket core → Python data/execution clients → Factory classes
- **WebSocket lifecycle:** Study how adapters manage connection, authentication, subscription, heartbeat, reconnection, and resubscription
- **Symbol normalization:** Compare how different adapters map venue-native symbols to Nautilus InstrumentId (e.g., Binance `-PERP` suffix, Bybit `-LINEAR`/`-SPOT` suffixes)
- **Rate limiting:** Compare token bucket implementations across adapters — Binance weight-based, Bybit global+endpoint, Deribit credit-based
- **Reconnection:** Study exponential backoff and resubscription patterns in Databento, Deribit, Hyperliquid
- **Order type mapping:** Compare how adapters map Nautilus order types to venue-specific API calls (e.g., dYdX market orders as aggressive IOC limits)
- **Reconciliation:** Study how execution clients implement `generate_order_status_reports`, `generate_fill_reports`, `generate_position_status_reports`

## Relationships

- **Depends on:** `nt-core-dev` for data model types, message bus, execution pipeline
- **See also:** `nt-kernel-dev` for how adapters are wired into the trading node at boot

## Known Gotchas

- Rust adapter must implement `Drop` for cleanup of WebSocket connections and background tasks
- Reconciliation on connect is critical — missing it causes position drift that compounds
- Rate limiting varies significantly per venue — study the specific venue's docs carefully
- Test with both the data testing spec (TC-D01 to TC-D72) and execution testing spec (TC-E01+)
- WebSocket reconnection must resubscribe to all active streams — missed resubscriptions cause silent data gaps
- Symbol normalization must be bidirectional — Nautilus ID to venue symbol and back
- Factory classes must be registered with the TradingNode builder before `node.build()` is called
- Some venues (dYdX, Hyperliquid) require blockchain transaction signing — different auth model than API key/secret

## Cached Knowledge

See `cached/` for annotated source excerpts from previous exploration sessions. Save useful findings here for future sessions.
