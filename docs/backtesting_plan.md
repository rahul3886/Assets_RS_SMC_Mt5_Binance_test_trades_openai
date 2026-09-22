# Backtesting System Implementation Plan

## Goal

Validate current strategy performance with historical data to establish baseline metrics before implementing upgrades.

## Proposed System Architecture

### 1. **Historical Data Collector**

- Fetch OHLCV data from CCXT for crypto pairs
- Support date ranges (last 7 days, 30 days, 90 days)
- Cache data locally to avoid re-fetching

### 2. **Signal Generator (Replay Mode)**

- Process historical candles sequentially
- Generate signals using existing `check_signals_advanced()` logic
- Track signal metadata (strength, SMC status, etc.)

### 3. **Trade Simulator**

- Execute virtual trades based on signals
- Simulate SL/TP hits using historical price action
- Track slippage and realistic fills

### 4. **Performance Analyzer**

- Calculate win rate, profit factor, R:R ratios
- Analyze performance by:
  - Timeframe (1m, 3m, 5m, 15m)
  - Signal strength threshold (50%, 60%, 70%+)
  - Asset type (BTC, ETH, SOL, etc.)
  - SMC setup type (Demand bounce, Supply rejection, etc.)

### 5. **Reporting System**

- Console dashboard with Rich tables
- CSV export for detailed analysis
- Visual charts (optional)

## Implementation Files

### **backtest_engine.py**

Core backtesting logic with trade simulation.

### **signal_logger.py**  

Records all signals for historical analysis.

### **performance_report.py**

Generates comprehensive performance reports.

### **run_backtest.py**

CLI tool to run backtests with various parameters.

## Key Metrics to Track

| Metric | Description | Target |
|--------|-------------|--------|
| **Win Rate** | Winning trades / Total trades | >70% |
| **Profit Factor** | Gross profit / Gross loss | >2.0 |
| **Avg R:R** | Average risk-reward ratio | >2.0 |
| **Max Drawdown** | Largest equity drawdown | <15% |
| **Avg Trade Duration** | Average time in trade | Varies by TF |
| **Sharpe Ratio** | Risk-adjusted returns | >1.5 |

## Validation Plan

### Phase 1: Single Asset Deep Dive

- Asset: **BTC/USDT**
- Period: Last **30 days**
- Timeframes: All (1m, 3m, 5m, 15m)
- Expected: ~200-500 signals

### Phase 2: Multi-Asset Validation

- Assets: **BTC, ETH, SOL** (top 3 by volume)
- Period: Last **14 days**
- Compare performance across assets

### Phase 3: Threshold Optimization

- Test MIN_SIGNAL_STRENGTH at: 40%, 50%, 60%, 70%, 80%
- Find optimal balance between signal count and win rate

## Next Steps

1. Create backtesting engine with trade simulator
2. Run Phase 1 validation on BTC/USDT
3. Generate performance report
4. Review results and decide on upgrades
