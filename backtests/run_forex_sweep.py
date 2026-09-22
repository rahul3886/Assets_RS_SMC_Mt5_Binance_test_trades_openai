import asyncio
import pandas as pd
from datetime import datetime
import os
import sys

# --- IMPORT FIX ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from run_backtest import run_single_backtest

async def run_forex_sweep():
    """
    Runs a 3-day backtest on EURUSD, USDJPY, and GBPUSD.
    Sweeps Timeframes (1m, 5m) and Signal Strengths (60, 70, 80).
    Goal: Find configurations with >55% Win Rate and >1.5 Profit Factor.
    """
    pairs = ["EURUSD", "USDJPY", "GBPUSD"]
    timeframes = ["1m", "5m"]
    strengths = [60, 70, 80]
    days = 3
    
    # Create a Master Sweep Folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    master_parent = os.path.join("backtests", f"forex_sweep_{timestamp}")
    os.makedirs(master_parent, exist_ok=True)
    
    print("\n" + "="*80)
    print(f"🌍 FOREX STRENGTH SWEEP (60-80%)")
    print(f"Assets: {pairs}")
    print(f"Strengths: {strengths}")
    print(f"Root: {master_parent}")
    print("="*80)
    
    for strength in strengths:
        print(f"\n🔥 TESTING STRENGTH: {strength}%")
        strength_folder = os.path.join(master_parent, f"Strength_{strength}")
        os.makedirs(strength_folder, exist_ok=True)
        
        for tf in timeframes:
            print(f"\n🚀 TF: {tf} batch starting...")
            tf_folder = os.path.join(strength_folder, f"TF_{tf}")
            os.makedirs(tf_folder, exist_ok=True)
            
            for symbol in pairs:
                print(f"\n--- {symbol} | {tf} | S:{strength} ---")
                try:
                    await run_single_backtest(
                        symbol=symbol, 
                        timeframe=tf, 
                        days=days, 
                        min_strength=strength, 
                        output_parent=tf_folder
                    )
                except Exception as e:
                    print(f"[ERROR] Failed {symbol} {tf} S:{strength}: {e}")

    print("\n" + "="*80)
    print(f"🏁 SWEEP COMPLETE")
    print(f"Results organized in: {master_parent}")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_forex_sweep())
