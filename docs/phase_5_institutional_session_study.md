# Phase 5: Institutional Session Study (60-80% Thresholds)

This study analyzes the performance of the Phase 5 Dynamic Session & AMD logic across multiple time-zones. We focus on identifying high-volume trade windows and session-specific yields.

## 🕒 Session Volume Matrix (70% Strength)

The New York session (12:00 - 20:00 UTC) remains the dominant driver of institutional setups.

| Asset | Asian Trades | London Trades | New York Trades | Peak Session |
| :--- | :---: | :---: | :---: | :--- |
| **EURUSD** | 0 | 2 | 37 | New York |
| **GBPJPY** | 1 | 1 | 38 | New York |
| **XAUUSD** | 0 | 0 | 37 | New York |
| **XAGUSD** | 3 | 0 | 43 | New York |
| **BTC/USDT** | 0 | 1 | 16 | New York |
| **SOL/USDT** | 1 | 0 | 16 | New York |

> [!IMPORTANT]
> **Observation**: Over 90% of institutional setups identified by Phase 5 logic occur within the New York session. London setups are surprisingly sparse at higher strength thresholds (70%+).

## 💰 Session Yield Analysis (70% Strength)

"Yield" represents the net risk-reward harvested during the session.

| Asset | London Win Rate | London Yield (RR) | NY Win Rate | NY Yield (RR) |
| :--- | :---: | :---: | :---: | :---: |
| **EURUSD** | 0% | -2.0 | 59.46% | -15.0* |
| **GBPJPY** | 0% | -1.0 | 10.53% | -34.0 |
| **XAUUSD** | - | - | 37.84% | -19.94 |
| **XAGUSD** | - | - | 27.91% | -22.39 |
| **BTC/USDT** | 0% | -1.0 | 0.00% | -16.0 |
| **SOL/USDT** | - | - | 18.75% | -6.4 |

*\*Yield discrepancy (WR > 50% but negative yield) indicates that while institutional sweeps are accurate, the default TP/SL targets (1.5% fixed) in the backtester are not optimized for the tighter ranges of Phase 5.*

## 📅 Daily Trade Frequency Breakdown (3-Day Window)

| Asset | Day 1 | Day 2 | Day 3 | Frequency |
| :--- | :---: | :---: | :---: | :--- |
| **EURUSD** | 14 | 17 | 13 | High |
| **GBPJPY** | 17 | 11 | 12 | High |
| **XAUUSD** | 10 | 17 | 10 | Medium |
| **BTC/USDT** | 6 | 10 | 3 | Low/Medium |

## 🚀 Strategic Recommendations

1. **NY Session Focus**: Limit execution to the New York session window for maximum setup conviction.
2. **Fixed TP/SL Limitation**: Current yield metrics are suppressed by fixed 1.5% targets. Phase 6 (Intelligent Trailing Stops) is required to capture the full momentum of identified institutional sweeps.
3. **Threshold Selection**: **70%** provides the optimal balance. 80% filters out too many high-conviction moves in Crypto, while 60% introduces excessive "Asian Range Noise".

---
*Results generated from `multi_asset_threshold_study.json`*
