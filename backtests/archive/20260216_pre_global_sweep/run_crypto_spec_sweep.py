import asyncio
import os
import json
from datetime import datetime
from run_backtest import run_single_backtest

async def run_crypto_spec_sweep():
    """
    Runs a 3-day backtest on Speculative Crypto Assets (DOGE, TRUMP).
    Focus: 1m Timeframe (High Volatility Scalping).
    Strengths: 60, 70, 80.
    Goal: Identify if these assets respect SMC zones or are too noisy.
    """
    # Note: Ensure these symbols match your data source (e.g., CCXT or MT5)
    # If using MT5, they might be "DOGEUSD" or similar. 
    # Based on previous context, user used "BTC/USDT", so we'll try "DOGE/USDT" and "TRUMP/USDT" (or "TRUMP" if on MT5)
    # We will try a mix to be safe or assuming the user knows the symbols.
    # Let's assume standard Binance format for now: DOGE/USDT. 
    # For TRUMP, it might be on specific exchanges, but let's try TRUMP/USDT if supported, or handle errors.
    
    pairs = ["DOGE/USDT", "TRUMP/USDT"] 
    timeframes = ["1m"] # Speculative assets are for high-frequency volatility
    strengths = [60, 70, 80]
    days = 3
    
    # Create a Master Sweep Folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    master_parent = os.path.join("backtests", f"crypto_spec_sweep_{timestamp}")
    os.makedirs(master_parent, exist_ok=True)
    
    print(f"🚀 Starting Crypto Speculative Sweep: {', '.join(pairs)}")
    print(f"📂 Results will be saved to: {master_parent}")
    
    for strength in strengths:
        strength_folder = os.path.join(master_parent, f"Strength_{strength}")
        os.makedirs(strength_folder, exist_ok=True)
        
        for tf in timeframes:
            tf_folder = os.path.join(strength_folder, f"TF_{tf}")
            os.makedirs(tf_folder, exist_ok=True)
            
            for symbol in pairs:
                print(f"--- Testing {symbol} {tf} S:{strength} ---")
                try:
                    # Run backtest - Note: run_single_backtest is async
                    await run_single_backtest(
                        symbol=symbol,
                        timeframe=tf,
                        days=days,
                        min_strength=strength,
                        output_parent=tf_folder
                    )
                except Exception as e:
                    print(f"❌ Error testing {symbol} {tf} S:{strength}: {e}")

    print("\n✅ Crypto Speculative Sweep Completed!")
    print(f"Final results are in {master_parent}")

if __name__ == "__main__":
    asyncio.run(run_crypto_spec_sweep())
