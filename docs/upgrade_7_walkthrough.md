# Walkthrough: Upgrade 7 - Cross-Asset Correlation

The Cross-Asset Correlation Module (Upgrade 7) transforms the bot from a "signal scanner" into a "portfolio manager." It intelligently identifies market-wide themes and prevents over-exposure.

## 🏛️ Institutional Exposure Management

Instead of taking every signaled trade, the system now uses **Cluster Filtering**. It groups assets into macro themes and only executes the **Strongest Link** in each cluster.

### Predefined Macro Clusters

1. **USD Nexus**: EURUSD, GBPUSD, XAUUSD, XAGUSD, BTC/USDT.
2. **Yen Carry**: GBPJPY, CADJPY, USDJPY.
3. **Metal Sync**: XAUUSD, XAGUSD.
4. **Crypto Beta**: BTC/USDT, ETH/USDT, SOL/USDT.

## 🛠️ Implementation Details

### Correlation Engine

The new [correlation_engine.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/correlation_engine.py) handles the clustering and winning-signal logic.

```python
# snippet of filter logic
def filter_signals(self, signals):
    # Priorities the signal with the highest strength score within each cluster.
    # Returns a list of 'unique winners'.
```

### Integrated Scanner Loop

In [main.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/main.py), the `scan_asset` function was decoupled from immediate alerting. The batch loop now:

1. Fetches data for all 22+ assets in parallel.
2. Collects all candidate signals (Multi-Frame Confluence applied).
3. Passes candidates to the `CorrelationEngine`.
4. Only sends Discord alerts for the assets that survive the correlation filter.

## ✅ Validation Results

The system was tested against a simulated "USD Dominance" event where 3 USD-based pairs signaled simultaneously.

| Asset | Signal | Strength | Filter Result |
| :--- | :--- | :---: | :--- |
| **GBPUSD** | SELL | 55% | Filtered |
| **EURUSD** | SELL | **72%** | **Winner** (Dispatched) |
| **XAUUSD** | SELL | 60% | Filtered |

**Result**: We avoided taking 3 correlated trades (which would have tripled risk on one macro theme) and automatically selected the highest-conviction SMC setup (EURUSD).

## 📊 Summary of Upgrades 6 & 7

- **Upgrade 6 (MTF)**: Boosted accuracy by using 5m/15m trends to 'bless' 1m entries.
- **Upgrade 7 (Correlation)**: Reduced portfolio risk by filtering redundant macro moves.

---
**Next Step**: Ready for live forward-testing with Phase 5/6/7 logic combined.
