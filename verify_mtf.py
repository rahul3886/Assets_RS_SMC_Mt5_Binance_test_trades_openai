import pandas as pd
import strategy
import numpy as np

def mock_df(price_start, length=200):
    data = {
        'timestamp': pd.date_range(start='2026-02-13', periods=length, freq='1min'),
        'open': np.linspace(price_start, price_start + 10, length),
        'high': np.linspace(price_start + 1, price_start + 11, length),
        'low': np.linspace(price_start - 1, price_start + 9, length),
        'close': np.linspace(price_start + 0.5, price_start + 10.5, length),
        'volume': np.random.randint(100, 1000, length)
    }
    df = pd.DataFrame(data)
    df = strategy.calculate_rsi(df)
    # df = strategy.calculate_rsi_ema(df)  # Removed: EMA is now inside calculate_rsi
    return df

def test_mtf_logic():
    print("--- Verifying Upgrade 6: Weighted MTF Confluence ---")
    
    # 1. Create Mock 1m Data (Primary)
    df_1m = mock_df(100)
    
    # Scenario: 1m is BULLISH (Force some criteria)
    # We'll manually override some values in ctx via mock smc if needed, 
    # but easiest is to just set RSI low in the last row.
    df_1m.iloc[-1, df_1m.columns.get_loc('RSI')] = 25 # Oversold
    df_1m.iloc[-2, df_1m.columns.get_loc('RSI')] = 20 # Previous RSI
    
    # We need to mock a Demand Zone for a major trigger
    # Or just wait for the scoring to pick it up.
    # Let's mock the ctx['smc'] inside check_signals_advanced by overriding its behavior
    # Actually, check_signals_advanced calls get_signal_context.
    # Let's just make the test data extreme.
    
    print("[TEST] Running 1m signal check WITH MTF context (Bullish Alignment)...")
    # We'll pass mtf_contexts where 15m is BULLISH
    mtf_contexts = {
        "5m": {"direction": "UP", "slope": 5, "rsi": 60},
        "15m": {
            "direction": "UP",
            "smc": {"bias": "BULLISH LIFTING", "status": "IN_DEMAND"}
        }
    }
    
    sig, info, ctx = strategy.check_signals_advanced(df_1m, mtf_contexts=mtf_contexts)
    
    print(f"Signal: {sig}")
    print(f"Strength: {info['strength']}%")
    print(f"Breakdown: {info['breakdown']}")
    
    # Check if MTF bonuses are present
    has_bonus = any("MTF Conviction" in k for k in info['breakdown'].keys())
    if has_bonus:
        print("✅ SUCCESS: MTF Conviction applied.")
    else:
        # If it's still Neutral, let's see why
        print("❌ Still Neutral. Let's force a major trigger.")
        # Manual trigger: sweep_ssl is checked in check_signals_advanced
        # We can't strictly force it without mocking smc_logic.detect_pivots etc.
        # But we can see if calculate_mtf_conviction works standalone.
        conv = strategy.calculate_mtf_conviction(mtf_contexts, "UP")
        print(f"Standalone Conviction: {conv}")
        if conv > 0: print("✅ Helper function works.")

    # Scenario: 1m is BULLISH, 15m is BEARISH (Headwind)
    mtf_contexts_bear = {
        "15m": {
            "direction": "DOWN",
            "smc": {"bias": "BEARISH HEAVY", "status": "IN_SUPPLY"}
        }
    }
    print("\n[TEST] Running 1m signal check WITH Bearish MTF Headwind...")
    sig2, info2, ctx2 = strategy.check_signals_advanced(df_1m, mtf_contexts=mtf_contexts_bear)
    print(f"Signal: {sig2}")
    print(f"Strength: {info2['strength']}%")
    print(f"Breakdown: {info2['breakdown']}")
    
    has_penalty = any("MTF Headwind" in k for k in info2['breakdown'].keys())
    if has_penalty:
        print("✅ SUCCESS: MTF Headwind penalized total strength.")
    else:
        print("❌ FAILURE: MTF Headwind not found in breakdown.")

if __name__ == "__main__":
    test_mtf_logic()
