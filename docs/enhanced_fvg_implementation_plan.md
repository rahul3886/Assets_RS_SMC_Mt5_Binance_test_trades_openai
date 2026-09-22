# Phase 4: Enhanced FVG Quality Scoring (Upgrade #4)

## Goal

Implement a sophisticated quality scoring system for Fair Value Gaps (FVG) to distinguish between minor market noise and significant institutional imbalances. High-quality FVGs will be weighted more heavily in the signal confluence engine, aiming to improve overall win rate and profitability.

## Proposed Changes

### [smc_logic.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/smc_logic.py)

#### [MODIFY] `get_smc_metrics`

- Extend the FVG search lookback from 5 bars to 30 bars.
- For each detected FVG, calculate a `quality` score (0-100):
  - **Gap Magnitude (30%):** Score based on the percentage size of the gap relative to price.
  - **Volume Confirmation (30%):** Bonus if the gap candle's volume is > 1.5x of its 10-period moving average.
  - **Institutional Vector (40%):** Bonus if the gap candle is a PVSRA "Climax" candle (200% volume).
- Return the `quality` score in the FVG objects.

### [strategy.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/strategy.py)

#### [MODIFY] `check_signals_advanced` & `check_signals_optimized`

- Update the FVG scoring logic:
  - **Premium FVG (+20 pts):** Awarded if an active FVG has `quality >= 70`.
  - **Normal FVG (+15 pts):** Awarded for standard FVGs (current baseline).
- This ensures the strategy prioritizes entries near high-conviction institutional gaps.

## Verification Plan

### Automated Tests

- Run `run_3day_backtest.py` to compare restored Phase 2 baseline (24.27% WR on current data) with the new Enhanced FVG logic.
- Target: Improvement in Win Rate and Profit Factor.

### Manual Verification

- Review the generated `backtest_results.json` to see if "Premium FVG" is correctly triggered and contributing to profitable trades.
