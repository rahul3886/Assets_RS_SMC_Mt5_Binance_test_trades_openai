# 📉 Baseline Trailing Engine Performance (Control Group)

This report documents the performance of the **Existing Trailing Setup** (Breakeven + Fixed Pivot Trailing) over the last 3 days.

**Configuration:**

- **Risk Per Trade:** $1000 (Position Size)
- **Assets:** BTC/USDT, ETH/USDT, SOL/USDT
- **Thresholds:** Optimized Sweet Spots (BTC 80%, ETH 70%, SOL 65%)

## 📊 Summary Metrics

| Asset | Trades | Win Rate | Net PnL ($) | Return on Capital |
| :--- | :--- | :--- | :--- | :--- |
| **SOL/USDT** | 8 | 62.5% | **-$7.89** | -0.8% |
| **BTC/USDT** | 4 | 75.0% | **+$13.50** | +1.4% |
| **ETH/USDT** | 9 | 66.7% | **+$5.62** | +0.6% |
| **TOTAL** | **21** | **66.6%** | **+$11.23** | **+0.4%** |

## 🔍 Trade-by-Trade Performance

### SOL/USDT (Thr 65%)

- ❌ LOSS: -$18.19 (-1.8%) - Exit: SL_HIT
- ✅ WIN: +$8.81 (+0.9%) - Exit: TP_HIT
- ✅ WIN: +$8.57 (+0.9%) - Exit: TP_HIT

### Analysis of Current Logic

1. **Strengths:** The current Pivot Trailing achieves a high win rate (66%) but struggles to capture large runners due to tight pivot stops.
2. **Weaknesses:** **SOL/USDT** volatility caused deeper pullbacks that hit the pivot stops before the trend resumed, leading to a net loss despite a good win rate.

---
**Status:** Baseline Established. Ready to compare with V2.
