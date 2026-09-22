# Upgrade 8 & 9: Enhanced Hunting & Adaptive Position Management (Trailing Engine)

This upgrade implements surgical liquidity detection and a professional-grade dynamic exit architecture to maximize winner retention and minimize 'gave back' profits.

## User Review Required

> [!IMPORTANT]
> **Adaptive Position Management**: The trailing logic will prioritize **Structural Pivots** over fixed pips. This means the stop-loss will "staircase" behind the price move, providing maximum breathing room during trends but tightening rapidly if the trend exhausts.

## Proposed Changes

### [Upgrade 8] Enhanced Hunting Detection

#### [MODIFY] [smc_logic.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/smc_logic.py)

- Implement `detect_displacement`: Checks if price moves rapidly (high volume + large body) after a sweep.
- Enhance `get_smc_metrics`: Add "Liquidity Clusters" (areas where multiple old highs/lows overlap).

#### [MODIFY] [strategy.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/strategy.py)

- Update `check_signals_advanced`: Only trigger `HUNTING_BUY/SELL` if `detect_displacement` is TRUE.

---

### [Upgrade 9] Adaptive Position Management (Trailing Engine)

#### [NEW] [trailing_engine.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/trailing_engine.py)

- Implement `PositionManager` class.
- **Breakeven Logic**: Move SL to `entry_price + buffer` once price reaches 1:1 Risk/Reward.
- **Structural Trailing**:
  - For LONG: Move SL to the most recent 1m Pivot Low (HL).
  - For SHORT: Move SL to the most recent 1m Pivot High (LH).
- **RSI Exhaustion Exit**: Premature exit if RSI hits 80+ (Long) or 20- (Short) with a negative slope on the 1m.

#### [MODIFY] [main.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/main.py)

- Integrate the `PositionManager` into the scanner loop to update active trade alerts on Discord when a "Trail Update" occurs.

## Verification Plan

### Automated Tests

- **Sweep + Displacement Test**: Verify that a 'slow' sweep without rejection does NOT trigger a signal.
- **Trailing Step Test**: Mock price moving up 3 structural steps and verify the SL follows correctly.

### Manual Verification

- Monitor Discord for "🛡️ **SL ADJUSTED: TRAILING BEHIND PIVOT**" notifications.
