# Phase 3 Tuning Results — BTC/USDT 1m (3 Days)

## Tuning Applied

- **+25% min_swing** thresholds (6.25, 3.75, 1.9 vs 5.0, 3.0, 1.5)
- **Lowered significance filter** from 25-30 → 20
- **Goal:** Improve selectivity to recover Phase 2 win rate (36.9%)

---

## Tuned Results

| Threshold | Trades | Win Rate | Profit Factor | Return |
|:---------:|:------:|:--------:|:-------------:|:------:|
| **40%**   | **107**| **26.17%**| **1.48**     | **-0.1%** |
| 50%       | 107    | 26.17%   | 1.48          | -0.1%  |
| 60%       | 16     | 25.0%    | 1.58          | -4.83% |
| 70%       | 6      | 16.67%   | 0.64          | -5.0%  |

---

## Phase Comparison Summary

| Version | WR (40%) | PF | Trades | Return |
|:--------|:--------:|:--:|:------:|:------:|
| **Phase 2 (Baseline)** | **36.9%** | **1.53** | **84** | **+16.32%** ✅ |
| Phase 3 (Untuned) | 30.61% | 1.63 | 98 | +10.9% |
| **Phase 3 (Tuned)** | **26.17%** ❌ | **1.48** | **107** | **-0.1%** ❌ |

---

## Analysis

### What Went Wrong

1. **Tighter filters excluded valid pivots** — Increasing min_swing by 25% filtered out legitimate structural points
2. **Lower significance (30→20) didn't help** — More pivots qualified but they were lower quality
3. **Trade count increased but quality tanked** — 107 trades vs 84, but WR dropped 10.73%

### Root Cause

Adaptive pivot detection is **fighting against the base strategy**. The Phase 2 Order Flow logic (Volume Delta, Climax, Absorption) already provides strong confluence. Adding pivot significance scoring creates conflicting signals.

---

## Recommendation

**Revert to Phase 2 baseline** (36.9% WR, +16.32% return, PF 1.53)

Adaptive pivots were a **failed experiment**. The Phase 2 configuration is the strongest performer. Future upgrades should:

- Keep Phase 2 as base
- Explore MTF (multi-timeframe) confirms
- Add regime filters (trending vs ranging)
- Implement session-based logic (Asian/London/NY)

---

Asset: **BTC/USDT 1m** | Period: **3 days** | Engine: **Binance**
