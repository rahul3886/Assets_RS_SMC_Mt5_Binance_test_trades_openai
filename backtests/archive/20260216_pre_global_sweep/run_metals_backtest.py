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

async def run_metals_redo():
    """
    Runs a 3-day backtest on XAUUSD, XAGUSD, and XAUEUR on 1m and 5m.
    Organizes results into a dedicated top-level metals folder.
    """
    metals = ["XAUUSD", "XAGUSD", "XAUEUR"]
    timeframes = ["1m", "5m"]
    days = 3
    
    # Create a Master Metals Results Folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    master_parent = os.path.join("backtests", f"metals_redo_{timestamp}")
    os.makedirs(master_parent, exist_ok=True)
    
    print("\n" + "="*80)
    print(f"🥇 METALS 3-DAY BACKTEST REDO")
    print(f"Assets: {metals}")
    print(f"TFs: {timeframes}")
    print(f"Root: {master_parent}")
    print("="*80)
    
    for tf in timeframes:
        print(f"\n🚀 STARTING {tf} BATCH...")
        tf_folder = os.path.join(master_parent, f"TF_{tf}")
        os.makedirs(tf_folder, exist_ok=True)
        
        for symbol in metals:
            print(f"\n--- Testing {symbol} ({tf}) ---")
            try:
                # We use the existing run_single_backtest but point it to our organized folder structure
                await run_single_backtest(
                    symbol=symbol, 
                    timeframe=tf, 
                    days=days, 
                    min_strength=50, 
                    output_parent=tf_folder
                )
            except Exception as e:
                print(f"[ERROR] Failed {symbol} {tf}: {e}")

    print("\n" + "="*80)
    print(f"🏁 ALL METAL BACKTESTS COMPLETE")
    print(f"Results organized in: {master_parent}")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_metals_redo())
