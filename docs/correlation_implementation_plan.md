# Upgrade 7: Cross-Asset Correlation Module

This upgrade implements an intelligent Correlation Filter. Its purpose is to quantify the relationship between assets and prevent the bot from taking multiple redundant trades that are driven by the same macro theme (e.g., a sudden USD move triggering 5 different Forex pairs simultaneously).

## User Review Required

> [!IMPORTANT]
> **Exposure Management**: The correlation module will prioritize the **highest-scoring** asset in a correlated cluster. For example, if EURUSD and GBPUSD both show BUY signals but are 90% correlated, the asset with the best SMC structure (highest strength score) will be traded, while the other is filtered out.

## Proposed Changes

### [Engine] Correlation & Clustering

#### [NEW] [correlation_engine.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/correlation_engine.py)

- Implement `CorrelationEngine` class.
- Functions to calculate Pearson Correlation coefficients for the last 24 hours of 1m/5m data.
- logic to group assets into clusters:
  - **USD Cluster**: (EURUSD, GBPUSD, XAUUSD, XAGUSD, etc.)
  - **Yen Cluster**: (GBPJPY, USDJPY, CADJPY, etc.)
  - **Crypto Cluster**: (BTC, ETH, SOL, etc.)

### [Integration] Scanner Filter

#### [MODIFY] [main.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/main.py)

- Use the `CorrelationEngine` to filter the aggregate signal list before sending to Discord/Execution.
- Add a "Correlation Warning" to the dashboard if the entire market is high-risk/high-correlation.

## Verification Plan

### Automated Tests

- **Correlation Accuracy**: Mock a high-correlation move (all USD pairs dropping) and verify that the filter only allows the strongest setup.
- **Computation Overhead**: Ensure the O(N^2) correlation matrix calculation doesn't lag the scanner loop.

### Manual Verification

- Check the dashboard for "Cluster Exposure" stats (e.g., "USD Net Exposure: +25%").
