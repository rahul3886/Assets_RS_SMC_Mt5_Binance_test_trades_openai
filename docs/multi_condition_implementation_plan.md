# Implementation Plan: Multi-Condition Entry System

## Goal

Decouple signal generation from strict RSI crossovers and move to a weighted confluence trigger system to catch higher-quality setups even if RSI hasn't crossed 30/70.

## Proposed Changes

### 1. `strategy.py`

- Modify `check_signals_advanced()` to support non-RSI triggers.
- Implement "Major Triggers" logic:
  - **Trigger A: SMC Zone + Volatility/Volume** (Strongest)
  - **Trigger B: RSI Extreme/Divergence** (Momentum)
  - **Trigger C: Liquidity Sweep (BSL/SSL)** (Institutional)
- Require at least 2 major triggers AND a total confluence score >= target threshold (e.g., 60%).

### 2. Signal Scoring Weights

Adjust weights to favor high-conviction institutional setups:

- **SMC Zone Entry:** 25% (Increased from 20%)
- **RSI Extreme/Divergence:** 25% (Weighted together)
- **Liquidity Magnet Proximity:** 20%
- **FVG Confluence:** 15%
- **Momentum/Speed:** 15%

## Verification Plan

### Automated Backtest

- Run `run_3day_backtest.py` on the updated logic.
- Compare with baseline:
  - **Baseline WR:** 43.75% (at 60% threshold)
  - **Baseline PF:** 1.97
  - **Target WR:** >55% for Phase 1
  - **Target PF:** >2.5

### Success Criteria

- Higher win rate on high-conviction signals.
- More actionable signals during trending markets where RSI may not reach extreme levels.
