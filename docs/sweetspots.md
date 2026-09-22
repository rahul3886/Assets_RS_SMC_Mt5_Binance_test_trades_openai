# 🎯 Market Geometry Sweet Spot Repository

This document tracks the "Institutional Edge" for every asset in the watchlist. A "Sweet Spot" is defined as an asset/timeframe combination where **Market Geometry Stop Losses (Distal Edge)** produce a positive expectancy and high win rate.

---

## 💎 Identified Sweet Spots (Verified)

These assets have proven profitability in the latest live demo sessions using **1m Market Geometry**.

| Asset | Timeframe | Conf. | Edge Notes |
| :--- | :--- | :--- | :--- |
| **BTC/USDT** | 1m | 95% | Clinical respect for institutional levels. Tight zones. |
| **SOL/USDT** | 1m | 90% | High scalp frequency. Strong adherence to liquidity sweeps. |
| **SHIB/USDT** | 1m | 80% | Highly technical micro-structure behavior. |
| **XAUUSD** | 1m | 85% | Gold thrives on low-latency structural invalidations. |

---

## 🔬 Search in Progress (Rest of Assets)

We are currently analyzing the following assets to find their optimal timeframe and structural buffers.

### 🟡 High Priority (Forex Major Pairs)

* **EURUSD / GBPUSD**: Testing 1m vs 3m. Current hypothesis: 1m is too noisy for FX; 3m might be the structural sweet spot.
* **USDJPY**: Testing session-specific volatility.

### 🔴 High Priority (Speculative Crypto)

* **TRUMP / PUMP / DOGE**: **FAILED 5m**. Testing 1m only with a "Liquidity Sweep" filter to avoid being hunted.

### ⚪ Background Analysis (Metals & Minor FX)

* XAGUSD, CADJPY, GBJPY, ATOM, BNB.

---

## 🛠️ The "Sweet Spot" Criteria

To qualify as a Sweet Spot, an asset must meet these criteria in backtesting or live demo:

1. **Win Rate > 55%** using Hard Distal Edge SL.
2. **Average RR > 1:1.5**
3. **Low Invalidation Drag**: Price should not frequently dip past the distal edge only to reverse (hunting).

---

## 📂 Version History

* **v1.0 (Current)**: Identified 1m Sniper dominance on BTC/SOL. Marked 5m as "High Risk" for current logic.
