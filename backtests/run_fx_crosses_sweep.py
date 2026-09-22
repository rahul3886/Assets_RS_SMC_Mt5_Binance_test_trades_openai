import asyncio
import os
import json
from datetime import datetime
from run_backtest import run_single_backtest

async def run_fx_crosses_sweep():
    """
    Runs a 3-day backtest on CADJPY, GBPJPY, USDCHF, and EURAUD.
    Sweeps Timeframes (1m, 5m) and Signal Strengths (60, 70, 80).
    Goal: Find configurations with >1.5 Profit Factor and healthy trade volume.
    """
    pairs = ["CADJPY", "GBPJPY", "USDCHF", "EURAUD"]
    timeframes = ["1m", "5m"]
    strengths = [60, 70, 80]
    days = 3
    
    # Create a Master Sweep Folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    master_parent = os.path.join("backtests", f"fx_crosses_sweep_{timestamp}")
    os.makedirs(master_parent, exist_ok=True)
    
    print(f"🚀 Starting Forex Crosses Sweep: {', '.join(pairs)}")
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

    print("\n✅ Forex Crosses Sweep Completed!")
    print(f"Final results are in {master_parent}")

if __name__ == "__main__":
    asyncio.run(run_fx_crosses_sweep())
