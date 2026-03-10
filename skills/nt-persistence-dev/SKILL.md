---
name: nt-persistence-dev
description: "Use when working with NT data persistence, ParquetDataCatalog, Arrow schemas, serialization, or data lake integration. Guides source exploration for the persistence and serialization layer."
---

# NT Persistence Development

## Overview

Build and extend NautilusTrader's data persistence layer: ParquetDataCatalog for storing/querying market data, Arrow schemas for type-safe columnar storage, serialization for data transport, and integration with data providers like Databento and Tardis.

## Exploration Sequence

1. **Read bundled references/** — concept docs for data types, API reference for persistence APIs
2. **Check cached/** — look for annotated excerpts from previous exploration sessions
3. **Explore NT source** — ask user: "Where is your local NautilusTrader repo?" If no local path, browse via `gh api repos/nautechsystems/nautilus_trader/contents/<path>`
4. **context7** — supplementary docs if gaps remain

## Concept Docs

- `references/concepts/data.md` — built-in data types, order book levels, bar aggregations, data streaming

## Integration Docs

These show how data providers integrate with the persistence layer:

- `references/integrations/databento.md` — DBN file loading, catalog integration, streaming, custom data types
- `references/integrations/tardis.md` — CSV streaming, instrument metadata, catalog integration, historical replay

## Developer Guide

- `references/developer_guide/test_datasets.md` — test data curation, Parquet storage format, naming conventions, R2 bucket for large data

## API Reference

- `references/api_reference/persistence.md` — ParquetDataCatalog, data writing/reading APIs
- `references/api_reference/serialization.md` — serialization traits and implementations

## Source Entry Points

Explore these paths (local or via GitHub):

- `crates/persistence/` — Rust persistence layer, Parquet read/write, Arrow schema definitions
- `crates/serialization/` — Rust serialization traits and implementations
- `nautilus_trader/persistence/` — Python-side catalog, writers, readers
- `nautilus_trader/serialization/` — Python-side serialization wrappers

## Key Types

Find and understand these before implementing:

- `ParquetDataCatalog` — main catalog interface for storing and querying data
- `ArrowSchemaProvider` trait — defines Arrow schema for each data type
- `ParquetWriter` / `ParquetReader` — low-level Parquet I/O
- `Serializer` / `Deserializer` traits — data serialization interfaces

## Patterns to Study

- **Arrow schema definitions:** How each data type (QuoteTick, TradeTick, Bar, etc.) defines its Arrow schema
- **Catalog write path:** How data flows from adapter → serialization → Parquet file
- **Catalog query path:** How BacktestNode loads data from catalog for replay
- **Databento integration:** How DBN files are transcoded into NT types and stored in catalog
- **Tardis integration:** How CSV data is streamed and normalized

## Relationships

- **Depends on:** nt-core-dev for data model types (QuoteTick, Bar, etc.)
- **Used by:** nt-backtest-dev for loading data into backtests
- **See also:** nt-adapter-dev for how adapters produce data that gets persisted

## Known Gotchas

- Arrow schemas must match the Rust struct field order exactly
- Parquet files use nanosecond timestamps — ensure consistency with NT's time model
- Large datasets should use partitioned writes (by date or instrument)
- Custom data types need custom Arrow schema implementations
- Test datasets have specific naming conventions — follow test_datasets.md

## Cached Knowledge

See `cached/` for annotated source excerpts from previous exploration sessions.
