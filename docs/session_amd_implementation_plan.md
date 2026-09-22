# Phase 5: Session & AMD Logic Implementation Plan (Refined)

## Goal

Implement **Upgrade #5: Session & Time Filtering** using a **Dynamic Verification** approach. The bot will not just assume session roles based on the clock, but will **confirm** the actual market behavior (Accumulation/Manipulation) before applying the AMD confluence boost on top of existing logic.

## 1. Dynamic Market Confirmation (The "Verification" Layer)

Instead of hard-coded assumptions, we will implement a validation check:

- **Verification A (Accumulation):** Was the Asian Session (00:00-08:00 UTC) actually a range?
  - *Logic:* (Asian_High - Asian_Low) / ATR < Threshold (e.g., 2.5).
  - *Outcome:* If it trends too hard (high volatility), we skip the AMD bonus for that day because the "Accumulation" condition wasn't met.
- **Verification M (Manipulation):** Did a sweep actually occur?
  - *Logic:* Price must pierce the Asian_High/Low and then show a reversal (Rejection wick or RSI divergence).
  - *Outcome:* The bonus is only applied if the sweep is active.

## 2. Layered Confluence (Additive Logic)

The AMD setup will **not replace** the current logic. It acts as a **High-Probability Filter**:

1. **Calculate Phase 4 Score:** (RSI + Zones + Premium FVG + Order Flow).
2. **Apply AMD Bonus (+25 pts):** Only if **Verification A** and **Verification M** are both met during the London Open window.
3. **Filter Asian Noise (-15 pts):** If we are in the Asian session and price is just "ping-ponging" inside the established range.

---

## Proposed Changes

### [smc_logic.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/smc_logic.py)

- **[NEW] `get_session_context(df)`**:
  - Identifies Asian High/Low.
  - Calculates "Trendiness Score" for the session to confirm if it was truly an **Accumulation**.
- **[MODIFY] `get_smc_metrics`**:
  - Include the verified `is_accumulation_confirmed` flag.

### [strategy.py](file:///c:/BILLIONAIRE%20RAHUL%20BOGI/Assets_RS_SMC_Mt5_Binance_test_trades/strategy.py)

- **[MODIFY] `check_signals_advanced` & `check_signals_optimized`**:
  - Add logic to check for **Asian Range Sweeps**.
  - Apply the +25 bonus *only* if the sweep happens during the 08:00-11:00 UTC window (London Open).

---

## 3. Workflow Example (A-M-D Trade)

1. Existing logic sees a **BUY** signal at a Demand Zone (Score: 55%).
2. Bot checks: "Are we in London Open?" → Yes.
3. Bot checks: "Was Asian session an accumulation?" → Yes (it was a tight range).
4. Bot checks: "Did we just sweep the Asian Low?" → Yes.
5. **Action:** Signal gets +25 points (Total Score: 80%).
6. **Result:** A "Good" trade becomes an "Excellent" high-conviction trade.
