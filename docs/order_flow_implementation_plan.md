# Upgrade #2: Order Flow & Volume Analysis

## Goal
Improve signal quality and win rate by ensuring entries are backed by institutional "Smart Money" volume and positive delta.

## Logic Overview
In a 1-minute timeframe, volume is the only reliable "non-lagging" indicator. We will look for:
1. **Volume Delta:** Positive delta (buying pressure) for BUY, negative for SELL.
2. **Volume Climax:** Extremely high relative volume at zones which often indicates reversal or breakout energy.
3. **Absorption:** High volume with small candle bodies, indicating "Whales" are soaking up orders.

## Proposed Changes

### 1. `strategy.py`
- Create `calculate_volume_metrics(df)` to analyze:
    - Relative Volume (RV) vs. Average.
    - Volume Delta (approximation using OHLC geometry).
    - Climax Volume detection.
- Integrate into `check_signals_advanced()`:
    - Add **Order Flow Score** (20% weight).
    - Condition: Only enter if Order Flow alignment is present or Total Strength is very high.

### 2. `config.py`
- Add volume thresholds (e.g., `VOL_AVG_PERIOD = 20`, `VOL_CLIMAX_MULT = 2.0`).

## Verification Plan
- **3-Day Backtest:** Run on upgraded logic.
- **Comparison:**
    - Baseline (Phase 1): 29% WR, +38% Profit.
    - **Target Upgrade #2:** >40% WR, +50%+ Profit.

## Documentation
All MD files for this phase will be mirrored to `c:\BILLIONAIRE RAHUL BOGI\Assets_RS_SMC_Mt5_Binance_test_trades\docs\` for easy access.
