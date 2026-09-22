# Option 5 Validation Results (Failed)

## Strategy Tested

**Fixed Pivots + Strict Order Flow Filter**

- Fixed lookback (2 bars)
- **Constraint**: Pivots ONLY valid if volume climax/absorption within ±3 bars

## Backtest Results (BTC/USDT 1m, 3 Days)

| Threshold | Win Rate | Profit Factor | Total Return |
|:---------:|:--------:|:-------------:|:------------:|
| 40%       | 25.24%   | 1.47          | -5.06%       |
| 50%       | 25.24%   | 1.47          | -5.06%       |
| **60%**   | **5.88%** ❌| **0.21** ❌    | **-16.0%** ❌ |

## Analysis

**Why it failed:**

1. **Broken Structure Sequences**: By deleting pivots without volume climaxes, we broke the "Higher High / Higher Low" logic. A trend needs *all* pivots to be identified to see the structure.
2. **catching Falling Knives**: Climaxes often happen at the *end* of a violent move. Using *only* these as pivots might be selecting for instability.

## Next Step: Option 1 (Recommended)

**Volume-Weighted Significance (Additive)**

- Detect **ALL** pivots (restore trend structure)
- **Boost Score** of pivots with volume confirmation (+20 points)
- Does NOT remove pivots, just prioritizes signals aligned with order flow.
