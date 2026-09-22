# Current Risk Management Strategy (Confirmed)

## 1. Stop Loss (SL) Strategy: Structural Support

Our SL is designed to hide behind "Institutional Protection" rather than a fixed percentage.

- **Base Level:** The system finds the nearest structural support/resistance:
  - **For BUY:** Nearest **Demand Zone Bottom** or **SSL (Sell-Side Liquidity)** level below price.
  - **For SELL:** Nearest **Supply Zone Top** or **BSL (Buy-Side Liquidity)** level above price.
- **Volatility Buffer:** We add a `0.5 * ATR` (Average True Range) buffer. This prevents "stop hunts" where the price wick just barely touches the structural level before reversing.
- **Fallback:** If no SMC zones are nearby, it uses the **Swing High/Low** of the last 20 candles.

**Why this gives high R:R:** We are only risking enough to get below the last "Line of Defense," allowing for very tight stops relative to the overall market move.

## 2. Take Profit (TP) Strategy: RSI Pulse Clusters

Our TP aims to exit when momentum reaches a "Crowded" area.

- **Primary Target:** RSI Structural Levels. Specifically, it searches for **Pivot Clusters** in RSI history (where RSI has bounced or reversed multiple times).
- **Logic:** "Sell when RSI reaches a known historical resistance cluster" (for Buy trades).
- **Fallback:** Fixed RSI targets of **60** (for Buy) or **40** (for Sell).
- **Simulation Note:** In our 3-day backtest, we used a conservative **1.5% fixed target** to approximate these RSI hits, which is why the Profit Factor reached 1.6 despite the 29% win rate.

---

## Documentation Status

All existing MD files are preserved in the brain directory:

1. [Project Analysis](file:///C:/Users/rahul/.gemini/antigravity/brain/a11bae71-2657-4957-8511-f3cd26548bbe/project_analysis.md)
2. [Backtesting Plan](file:///C:/Users/rahul/.gemini/antigravity/brain/a11bae71-2657-4957-8511-f3cd26548bbe/backtesting_plan.md)
3. [Baseline Validation](file:///C:/Users/rahul/.gemini/antigravity/brain/a11bae71-2657-4957-8511-f3cd26548bbe/validation_walkthrough.md)
4. [Phase 1 Implementation Plan](file:///C:/Users/rahul/.gemini/antigravity/brain/a11bae71-2657-4957-8511-f3cd26548bbe/multi_condition_implementation_plan.md)
5. [Phase 1 Results](file:///C:/Users/rahul/.gemini/antigravity/brain/a11bae71-2657-4957-8511-f3cd26548bbe/phase_1_results.md)

I will continue creating these for every subsequent upgrade.

---

## Looking Ahead: Upgrade #2 (Order Flow & Volume)

We will focus on **Volume Delta** and **Climax Volume** to filter out the low-probability 1m signals. This should help push that 29% win rate higher by ensuring we only enter when there is "Size" behind the move.
