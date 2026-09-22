# Live Demo Trading Session Implementation Plan

Setup a high-performance, real-time trading simulator that monitors the entire portfolio with institutional-grade logic and market hours awareness.

## Proposed Changes

### [NEW] [live_demo_session.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/live_demo_session.py)

This script will be the main entry point for the demo session.

#### Key Features

1. **Market Hours Awareness**:
    - Full 24/7 scanning for Crypto.
    - Automatic suspension of Forex/Metals on weekends (Sat/Sun).
2. **Portfolio Configuration**:
    - Pre-defined 'Sweet Spot' thresholds for all 20 assets (BTC 80%, ETH 70%, etc.).
    - Fixed $100,000 position size per trade.
3. **Real-time Position Tracking**:
    - Uses the `trailing_engine.py` (Baseline) PositionManager.
    - Updates Stop-Loss based on 1m pivots and 1:1 Breakeven rules.
4. **Institutional Logging**:
    - Generates `docs/live_session_metrics.md` with every entry, SL movement, and exit.
    - Maintains a running PnL dashboard in the console.

### Deployment Workflow

1. Initialize MT5 and CCXT via `AsyncDataProvider`.
2. Fetch initial OHLCV for all assets to warm up indicators.
3. Enter the `while True` loop:
    - Parallel fetch OHLCV for all "active" markets.
    - Detect signals via `check_signals_optimized`.
    - If Entry -> Add to `PositionManager`.
    - If Open Position -> Update with latest price until Exit.
4. Save metrics on every exit.

## Verification Plan

### Manual Verification

- Run the script and observe the console for MT5 initialization and Crypto data flow.
- Verify that FX/Metal symbols show "Market Closed" status (since today is Saturday).
- Trigger a "Mock Signal" (optional) to test the logging into `docs/live_session_metrics.md`.
