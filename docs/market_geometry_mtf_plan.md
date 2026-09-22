# Market Geometry & MTF Upgrade Implementation Plan

Transition the trading engine from volatility-based "guessing" (ATR) to pure Market Geometry and introduce 5m timeframe scanning for higher reliability.

## Proposed Changes

### [MODIFY] [strategy.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/strategy.py)

* Update `calculate_structural_sl`:
  * Remove the `atr_mult` parameter and the `buffer` calculation.
  * Set SL exactly at the distal edge (top for Supply, bottom for Demand) of the identified SMC zone.
  * Ensure fallback structural levels (recent high/low) also don't use ATR buffers.

### [MODIFY] [live_demo_session.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/live_demo_session.py)

* Update `LiveDemoSession.scan_asset`:
  * accepts a `timeframe` parameter.
  * Updates state to track trades by `(symbol, timeframe)` pair.
* Update `run_session` loop:
  * Iterate through both `1m` and `5m` for each asset.
* Update Log Format:
  * Add a `TF` column to `live_demo_trades.md`.
  * Mention timeframe in console logs (e.g., `🚀 [ENTRY] BTC/USDT (5m)...`).

### [MODIFY] [trailing_engine.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/trailing_engine.py)

* Update `PositionManager.add_position` and `process_update`:
  * Store the timeframe of the entry.
  * For 5m trades, use structural trailing that respects 5m pivots rather than the tight 1m pivots.

## Verification Plan

### Automated Verification

- Run a short 1-hour backtest simulation on SOL/USDT comparing 1m vs 5m signals.
* Verify that SL values generated for 5m trades match the zone boundaries exactly.

### Manual Verification

- Start the upgraded `live_demo_session.py`.
* Observe the console to ensure parallel scanning of 1m/5m is working without `KeyErrors`.
* Monitor `docs/live_demo_trades.md` to confirm the new `TF` column is populating.
