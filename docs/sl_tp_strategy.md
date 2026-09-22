# Current Risk Management Strategy (Confirmed)

## 1. Stop Loss (SL) Strategy: Structural Support

- **For BUY:** Nearest Demand Zone Bottom or SSL Level below price + 0.5*ATR buffer.
- **For SELL:** Nearest Supply Zone Top or BSL Level above price + 0.5*ATR buffer.
- **Fallback:** 20-candle Swing High/Low.

## 2. Take Profit (TP) Strategy: RSI Pulse Clusters

- **Strategy:** Exit when RSI reaches historical reversal clusters detected in the lookback period.
- **Targets:** Dynamically calculated based on RSI history.

This setup ensures a high Risk:Reward ratio by placing exits at structural points of failure/exhaustion.
