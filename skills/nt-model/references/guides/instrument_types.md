# Instrument Types Reference Guide

Complete catalog of all instrument types in NautilusTrader with fields, creation patterns,
and Rust equivalents.

## Instrument Hierarchy

```
Data (core base)
 +-- Instrument (base class for all tradable instruments)
 |    +-- Equity
 |    +-- CurrencyPair
 |    +-- Commodity
 |    +-- IndexInstrument
 |    +-- FuturesContract
 |    +-- FuturesSpread
 |    +-- CryptoFuture
 |    +-- CryptoPerpetual
 |    +-- PerpetualContract
 |    +-- OptionContract
 |    +-- OptionSpread
 |    +-- CryptoOption
 |    +-- BinaryOption
 |    +-- Cfd
 |    +-- BettingInstrument
 +-- SyntheticInstrument (separate from Instrument, derives from Data directly)
```

`SyntheticInstrument` is **not** a subclass of `Instrument`. It extends `Data` directly
and has its own formula-based pricing model backed by a Rust core.

## Base Instrument Fields

All `Instrument` subclasses inherit these from the base class
(`nautilus_trader.model.instruments.base.Instrument`):

### Required fields

| Field               | Type            | Description                                              |
|---------------------|-----------------|----------------------------------------------------------|
| `instrument_id`     | `InstrumentId`  | Unique ID in `{SYMBOL}.{VENUE}` format                  |
| `raw_symbol`        | `Symbol`        | Native/local symbol assigned by the venue                |
| `asset_class`       | `AssetClass`    | EQUITY, FX, CRYPTOCURRENCY, COMMODITY, INDEX, etc.       |
| `instrument_class`  | `InstrumentClass` | SPOT, FUTURE, FUTURES_SPREAD, OPTION, OPTION_SPREAD, SWAP |
| `quote_currency`    | `Currency`      | The quote currency                                       |
| `is_inverse`        | `bool`          | Quantity expressed in quote currency units                |
| `price_precision`   | `int`           | Decimal precision for prices                             |
| `size_precision`    | `int`           | Decimal precision for trade sizes                        |
| `size_increment`    | `Quantity`      | Minimum size increment                                   |
| `multiplier`        | `Quantity`      | Contract value multiplier (determines tick value)        |
| `margin_init`       | `Decimal`       | Initial margin requirement (% of order value)            |
| `margin_maint`      | `Decimal`       | Maintenance margin (% of position value)                 |
| `maker_fee`         | `Decimal`       | Fee rate for liquidity makers (% of order value)         |
| `taker_fee`         | `Decimal`       | Fee rate for liquidity takers (% of order value)         |
| `ts_event`          | `uint64`        | UNIX timestamp (nanoseconds) when event occurred         |
| `ts_init`           | `uint64`        | UNIX timestamp (nanoseconds) when object initialized     |

### Optional fields (base)

| Field              | Type       | Description                         |
|--------------------|------------|-------------------------------------|
| `price_increment`  | `Price`    | Minimum price increment (tick size) |
| `lot_size`         | `Quantity` | Standard/board lot unit size        |
| `max_quantity`     | `Quantity` | Maximum allowable order quantity    |
| `min_quantity`     | `Quantity` | Minimum allowable order quantity    |
| `max_notional`     | `Money`    | Maximum order notional value        |
| `min_notional`     | `Money`    | Minimum order notional value        |
| `max_price`        | `Price`    | Maximum allowable quoted price      |
| `min_price`        | `Price`    | Minimum allowable quoted price      |
| `tick_scheme_name` | `str`      | Name of a registered tick scheme    |
| `info`             | `dict`     | Additional instrument information   |

### Key base properties and methods

- `symbol` -- the ticker symbol portion of the instrument ID
- `venue` -- the venue portion of the instrument ID
- `make_price(value)` -- round a value to the instrument's price precision
- `make_qty(value, round_down=False)` -- round a value to the instrument's size precision
- `notional_value(quantity, price)` -- calculate notional value
- `is_spread()` -- whether the instrument has multiple legs
- `get_base_currency()` -- base currency (if applicable, e.g., CurrencyPair)
- `get_settlement_currency()` -- currency used to settle trades
- `get_cost_currency()` -- currency used for PnL calculations
- `next_bid_price(value, num_ticks)` / `next_ask_price(value, num_ticks)` -- tick-scheme aware price stepping

## Individual Instrument Types

### Equity
**Module**: `nautilus_trader.model.instruments.equity`
**Asset class**: `EQUITY` | **Instrument class**: `SPOT`

Additional required: `currency`, `price_increment`, `lot_size`
Additional optional: `isin` (ISIN code), `max_quantity`, `min_quantity`
Fixed: `size_precision=0`, `size_increment=1`, `multiplier=1`, `is_inverse=False`

### CurrencyPair
**Module**: `nautilus_trader.model.instruments.currency_pair`
**Asset class**: auto-detected (`CRYPTOCURRENCY` if either currency is crypto, else `FX`)
**Instrument class**: `SPOT`

Additional required: `base_currency`, `quote_currency`, `price_increment`, `size_increment`
Additional optional: `multiplier`, `lot_size`, all quantity/notional/price limits
Key property: `base_currency` -- the base currency of the pair
Fixed: `is_inverse=False`

### Commodity
**Module**: `nautilus_trader.model.instruments.commodity`
**Asset class**: caller-specified | **Instrument class**: `SPOT`

Additional required: `asset_class`, `quote_currency`, `price_increment`, `size_increment`
Additional optional: `lot_size`, all quantity/notional/price limits
Fixed: `is_inverse=False`

### IndexInstrument
**Module**: `nautilus_trader.model.instruments.index`
**Asset class**: `INDEX` | **Instrument class**: `SPOT`

A spot/cash index. Not directly tradable; used as a reference price.
Additional required: `currency`, `price_increment`, `size_increment`, `size_precision`
Fixed: `is_inverse=False`, `multiplier=1`, `margin_init=0`, `margin_maint=0`

### FuturesContract
**Module**: `nautilus_trader.model.instruments.futures_contract`
**Asset class**: caller-specified | **Instrument class**: `FUTURE`

Additional required: `asset_class`, `currency`, `price_increment`, `multiplier`, `lot_size`, `underlying` (str), `activation_ns`, `expiration_ns`
Additional optional: `exchange` (MIC code)
Properties: `activation_utc`, `expiration_utc` (as `pd.Timestamp`)
Fixed: `size_precision=0`, `size_increment=1`, `is_inverse=False`

### FuturesSpread
**Module**: `nautilus_trader.model.instruments.futures_spread`
**Asset class**: caller-specified | **Instrument class**: `FUTURES_SPREAD`

Additional required: `asset_class`, `currency`, `price_increment`, `multiplier`, `lot_size`, `underlying`, `strategy_type` (str), `activation_ns`, `expiration_ns`
Additional optional: `exchange`
Note: Supports negative prices. Overrides `legs()` to return leg instrument IDs from generic spread ID parsing.

### CryptoPerpetual
**Module**: `nautilus_trader.model.instruments.crypto_perpetual`
**Asset class**: `CRYPTOCURRENCY` | **Instrument class**: `SWAP`

Additional required: `base_currency`, `quote_currency`, `settlement_currency`, `is_inverse`, `price_increment`, `size_increment`
Additional optional: `multiplier`, `lot_size`, all quantity/notional/price limits
Key properties: `is_quanto` (auto-calculated when settlement != base and settlement != quote)
Overrides: `get_settlement_currency()`, `get_cost_currency()`, `notional_value()`

### CryptoFuture
**Module**: `nautilus_trader.model.instruments.crypto_future`
**Asset class**: `CRYPTOCURRENCY` | **Instrument class**: `FUTURE`

Additional required: `underlying` (Currency), `quote_currency`, `settlement_currency`, `is_inverse`, `activation_ns`, `expiration_ns`, `price_increment`, `size_increment`
Additional optional: `multiplier`, `lot_size`, all quantity/notional/price limits
Properties: `activation_utc`, `expiration_utc`

### CryptoOption
**Module**: `nautilus_trader.model.instruments.crypto_option`
**Asset class**: `CRYPTOCURRENCY` | **Instrument class**: `OPTION`

Additional required: `underlying` (Currency), `quote_currency`, `settlement_currency`, `is_inverse`, `option_kind` (PUT/CALL), `strike_price`, `activation_ns`, `expiration_ns`, `price_increment`, `size_increment`
Additional optional: `multiplier`, `lot_size`, all limits

### PerpetualContract
**Module**: `nautilus_trader.model.instruments.perpetual_contract`
**Asset class**: caller-specified (any) | **Instrument class**: `SWAP`

Asset-class agnostic perpetual swap (FX, equities, commodities, indexes, crypto).
Additional required: `underlying` (str), `asset_class`, `quote_currency`, `settlement_currency`, `is_inverse`, `price_increment`, `size_increment`
Additional optional: `base_currency`, `multiplier`, `lot_size`, all limits

### OptionContract
**Module**: `nautilus_trader.model.instruments.option_contract`
**Asset class**: caller-specified | **Instrument class**: `OPTION`

Additional required: `asset_class`, `currency`, `price_increment`, `multiplier`, `lot_size`, `underlying`, `option_kind` (PUT/CALL), `strike_price`, `activation_ns`, `expiration_ns`
Additional optional: `exchange`
Note: Supports negative prices.

### OptionSpread
**Module**: `nautilus_trader.model.instruments.option_spread`
**Asset class**: caller-specified | **Instrument class**: `OPTION_SPREAD`

Additional required: `asset_class`, `currency`, `price_increment`, `multiplier`, `lot_size`, `underlying`, `strategy_type`, `activation_ns`, `expiration_ns`
Additional optional: `exchange`
Note: Supports negative prices. Overrides `legs()` for generic spread ID parsing.

### BinaryOption
**Module**: `nautilus_trader.model.instruments.binary_option`
**Asset class**: caller-specified | **Instrument class**: `OPTION`

Additional required: `asset_class`, `currency`, `price_increment`, `size_increment`, `activation_ns`, `expiration_ns`
Additional optional: `outcome` (str), `description` (str), `max_quantity`, `min_quantity`

### Cfd
**Module**: `nautilus_trader.model.instruments.cfd`
**Asset class**: auto-detected (like CurrencyPair) | **Instrument class**: `CFD`

Additional required: `quote_currency`, `price_increment`, `size_increment`
Additional optional: `base_currency`, `lot_size`, all limits

### BettingInstrument
**Module**: `nautilus_trader.model.instruments.betting`
**Asset class**: `ALTERNATIVE` | **Instrument class**: `SPORTS_BETTING`

Unique fields: `venue_name`, `event_type_id`, `event_type_name`, `competition_id`, `competition_name`, `event_id`, `event_name`, `event_country_code`, `event_open_date`, `betting_type`, `market_id`, `market_name`, `market_start_time`, `market_type`, `selection_id`, `selection_name`, `selection_handicap`
The instrument ID is auto-generated from venue + market/selection data.

## SyntheticInstrument (Special)

**Module**: `nautilus_trader.model.instruments.synthetic`
**Extends**: `Data` (NOT `Instrument`)

Derives prices from component instruments using a mathematical formula.
The ID is always `{symbol}.SYNTH`.

### Required fields

| Field             | Type                 | Description                             |
|-------------------|----------------------|-----------------------------------------|
| `symbol`          | `Symbol`             | The synthetic's symbol                  |
| `price_precision` | `uint8`              | Max 9                                   |
| `components`      | `list[InstrumentId]` | At least 2 component instrument IDs     |
| `formula`         | `str`                | Mathematical expression using components|
| `ts_event`        | `uint64`             | UNIX timestamp (nanoseconds)            |
| `ts_init`         | `uint64`             | UNIX timestamp (nanoseconds)            |

### Key methods

- `calculate(inputs: list[float]) -> Price` -- compute synthetic price from component prices
- `change_formula(formula: str)` -- update the derivation formula at runtime
- `components` (property) -- list of component InstrumentId values
- `formula` (property) -- the current formula string

### Constraints

- `price_precision` must be <= 9
- Must have at least 2 component instruments
- Formula is validated against components at creation time
- Components should already exist in the cache before defining the synthetic
- Currently not safe for serialization via the standard library serializer

## Common Creation Patterns

### From dict (deserialization)

Every instrument type provides `from_dict()` and `to_dict()` static methods:

```python
values = {
    "id": "AAPL.XNAS",
    "raw_symbol": "AAPL",
    "currency": "USD",
    "price_precision": 2,
    "price_increment": "0.01",
    "lot_size": "1",
    "ts_event": 0,
    "ts_init": 0,
    "info": {},
}
equity = Equity.from_dict(values)
```

### From pyo3 (Rust to Python conversion)

Each instrument has `from_pyo3()` for converting Rust pyo3 objects:

```python
# Typically used internally by the framework
cython_equity = Equity.from_pyo3(pyo3_equity)
```

The conversion uses `from_raw_c` for Price/Quantity to avoid precision loss.

### Manual construction

```python
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.objects import Currency, Price, Quantity

equity = Equity(
    instrument_id=InstrumentId.from_str("AAPL.XNAS"),
    raw_symbol=Symbol("AAPL"),
    currency=Currency.from_str("USD"),
    price_precision=2,
    price_increment=Price.from_str("0.01"),
    lot_size=Quantity.from_int(1),
    ts_event=0,
    ts_init=0,
)
```

### Batch conversion from Rust

```python
from nautilus_trader.model.instruments.base import instruments_from_pyo3

# Convert a list of pyo3 Rust instrument objects to Cython objects
cython_instruments = instruments_from_pyo3(pyo3_instrument_list)
```

This function dispatches based on pyo3 type to the correct `from_pyo3_c()` method.

## Rust Equivalents

Each Python instrument has a corresponding Rust struct in `crates/model/src/instruments/`:

| Python class         | Rust module                         | Rust struct            |
|----------------------|-------------------------------------|------------------------|
| `BettingInstrument`  | `instruments::betting`              | `BettingInstrument`    |
| `BinaryOption`       | `instruments::binary_option`        | `BinaryOption`         |
| `Cfd`                | `instruments::cfd`                  | `Cfd`                  |
| `Commodity`          | `instruments::commodity`            | `Commodity`            |
| `CryptoFuture`       | `instruments::crypto_future`        | `CryptoFuture`         |
| `CryptoOption`       | `instruments::crypto_option`        | `CryptoOption`         |
| `CryptoPerpetual`    | `instruments::crypto_perpetual`     | `CryptoPerpetual`      |
| `CurrencyPair`       | `instruments::currency_pair`        | `CurrencyPair`         |
| `Equity`             | `instruments::equity`               | `Equity`               |
| `FuturesContract`    | `instruments::futures_contract`     | `FuturesContract`      |
| `FuturesSpread`      | `instruments::futures_spread`       | `FuturesSpread`        |
| `IndexInstrument`    | `instruments::index_instrument`     | `IndexInstrument`      |
| `OptionContract`     | `instruments::option_contract`      | `OptionContract`       |
| `OptionSpread`       | `instruments::option_spread`        | `OptionSpread`         |
| `PerpetualContract`  | `instruments::perpetual_contract`   | `PerpetualContract`    |
| `SyntheticInstrument`| `instruments::synthetic`            | `SyntheticInstrument`  |

The Rust side also defines:
- `InstrumentAny` enum (`instruments::any`) -- an `enum_dispatch` wrapper over all instrument types
- `validate_instrument_common()` -- shared validation logic for all instruments
- `TickSchemeRule` trait and `FixedTickScheme` -- tick stepping logic
- Stubs module (`instruments::stubs`) for test fixtures (behind `test` or `stubs` feature flag)

## Expiring Instruments

The base module defines sets of instrument classes that expire:

```python
EXPIRING_INSTRUMENT_CLASSES = {FUTURE, FUTURES_SPREAD, OPTION, OPTION_SPREAD}
ENGINE_EXPIRING_INSTRUMENT_CLASSES = {FUTURE, FUTURES_SPREAD, OPTION, OPTION_SPREAD}
NEGATIVE_PRICE_INSTRUMENT_CLASSES = (OPTION, FUTURES_SPREAD, OPTION_SPREAD)
```

These are used by the backtest engine for automatic contract expiration handling
and to allow negative price validation where appropriate.
