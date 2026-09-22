# Market Geometry & MTF Upgrade

- [/] Planning & Architecture
  - [x] Analyze current SL logic in `strategy.py`
  - [/] Create implementation plan for Market Geometry & MTF
- [ ] Implement Market Geometry SL in `strategy.py`
  - [ ] Remove ATR buffers from `calculate_structural_sl`
  - [ ] Add explicit "Distal Edge" logic for Supply/Demand zones
- [ ] Upgrade `live_demo_session.py` for MTF
  - [ ] Implement parallel 1m and 5m scanning
  - [ ] Update log format to include Timeframe column
  - [ ] Update `PositionManager` to handle multi-TF trades
- [ ] Verification & Live Session Restart
  - [ ] Verify 5m signal detection
  - [ ] Verify "Hard" SL placement
  - [ ] Start new session and monitor `docs/live_demo_trades.md`
