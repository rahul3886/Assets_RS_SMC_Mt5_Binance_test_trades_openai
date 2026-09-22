import pandas as pd
import strategy

def test_advanced_logic():
    print("Testing Advanced RSI Signal Logic...")
    
    # Mock data
    data = {
        'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='1min'),
        'open': [100]*100,
        'high': [105]*100,
        'low': [95]*100,
        'close': [100]*100
    }
    df = pd.DataFrame(data)
    
    # Simulate a Bullish Divergence scenario:
    # Price makes a lower low, RSI makes a higher low
    df.loc[80, 'low'] = 90
    df.loc[95, 'low'] = 85 # Lower Low in Price
    
    # We will manually set RSI values to mock the behavior
    # We need to fill columns that strategy uses
    df = strategy.calculate_rsi(df)
    
    # Overwrite RSI to force a signal and divergence
    # Previous RSI <= 30, Current RSI > 30 (BUY Signal)
    df.loc[98, 'RSI'] = 25
    df.loc[99, 'RSI'] = 35
    
    # Logic for Divergence in strategy.py uses find_pivots which looks for peaks/valleys
    # It needs a few candles of history to find a "valley"
    # Let's simplify and just check if the function runs and detects the base signal first
    
    signal, strength_info, ctx = strategy.check_signals_advanced(df)
    
    print(f"Detected Signal: {signal}")
    print(f"Strength: {strength_info['strength']}%")
    print(f"Breakdown: {strength_info['breakdown']}")
    print(f"RSI Structure: {ctx['structure']}")
    
    assert signal == "BUY"
    assert strength_info['strength'] >= 25 # Base crossover should be 25
    
    print("✅ Advanced RSI logic tests passed!")

if __name__ == "__main__":
    test_advanced_logic()
