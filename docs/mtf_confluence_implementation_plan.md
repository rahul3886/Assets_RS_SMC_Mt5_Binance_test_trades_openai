# Upgrade 6: True Multi-Frame Confluence (MTF)

This upgrade implements a sophisticated Multi-Frame Confluence (MTF) engine. Instead of a restrictive "all-or-nothing" filter, it uses a **Weighted Confluence Scoring** model. This ensures we don't miss high-probability scalps on the 1m timeframe while benefiting from the structural conviction of the 5m and 15m timeframes.

## User Review Required

> [!IMPORTANT]
> **Trade Frequency Confirmation**: To address your concern about missing trades, the system will **NOT** require all timeframes to be in perfect agreement. Instead:
>
> - **1m** remains the main entry trigger.
> - **5m/15m** provide "Conviction Bonuses" to the signal strength.
> - If 15m is in a strong counter-trend, the 1m signal will be penalized but not necessarily discarded if the 1m setup is extremely high quality (e.g., Liquidity Sweep + FVG).

## Proposed Changes

### [Engine] Core Strategy & SMC

#### [MODIFY] [strategy.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/strategy.py)

- Update `check_signals_advanced` to accept optional `mtf_data` (3m, 5m, 15m).
- Implement `calculate_mtf_conviction()` helper to score higher timeframe bias:
  - **15m Structure**: Identify Major BoS (Break of Structure) and Supply/Demand zones.
  - **5m Momentum**: Check RSI direction and Slope on the mid-timeframe.
- Integrate MTF score into the final signal strength.

#### [MODIFY] [smc_logic.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/smc_logic.py)

- Ensure `get_smc_metrics` can be run efficiently across multiple dataframes in parallel.

### [Runner] Real-time Scanner & Backtester

#### [MODIFY] [main.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/main.py)

- Upgrade the scanner loop to fetch 1m, 5m, and 15m data in a single async batch per asset.
- Pass the MTF dictionary to the strategy engine.

## Verification Plan

### Automated Tests

- **MTF Latency Test**: Verify that fetching 3 timeframes per asset doesn't slow down the scanner beyond the 60s window.
- **Backtest Comparison**: Compare 1w results of "1m Only" vs "1m + MTF Weighted" to verify accuracy boost vs frequency loss.

### Manual Verification

- Observe the scanner dashboard to confirm the "MTF Bias" indicator (e.g., "15m: BEARISH | 5m: BULLISH | 1m: ENTRY") displays correctly for active setups.
