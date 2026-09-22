import asyncio
import ccxt.async_support as ccxt
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# --- IMPORT FIX FOR RELOCATED SCRIPT ---
# Add project root to path so we can find strategy, smc_logic, etc.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from backtest_engine import BacktestEngine

from data_provider import AsyncDataProvider

async def fetch_historical_data(symbol="BTC/USDT", timeframe="1m", days=30):
    """
    Fetches historical OHLCV data using the project's AsyncDataProvider.
    Supports both Crypto (CCXT) and Metals/FX (MT5).
    """
    print(f"\n[DATA] Fetching {days} days of {timeframe} data for {symbol}...")
    
    provider = AsyncDataProvider()
    try:
        # Determine if it's a crypto or metal/fx asset
        is_crypto = "/USDT" in symbol
        
        # Calculate limit based on days and timeframe
        # 1m = 1440 candles/day
        # 5m = 288 candles/day
        multiplier = 1440 if timeframe == "1m" else 288
        limit = int(days * multiplier) + 100 # buffer
        
        if is_crypto:
            df = await provider.fetch_crypto_ohlcv(symbol, timeframe, limit=limit)
        else:
            df = await provider.fetch_mt5_ohlcv(symbol, timeframe, limit=limit)
            
        if df is not None:
            print(f"[DATA] ✓ Loaded {len(df)} candles from {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
            return df
        return None
    finally:
        await provider.close()

async def run_single_backtest(symbol="BTC/USDT", timeframe="1m", days=7, min_strength=50, output_parent="backtests"):
    """
    Runs a single backtest on one asset/timeframe and saves results to a session folder.
    """
    # Create session folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"bt_{symbol.replace('/', '_')}_{timeframe}_{timestamp}"
    output_dir = os.path.join(output_parent, session_name)
    os.makedirs(output_dir, exist_ok=True)

    # Fetch data
    df = await fetch_historical_data(symbol, timeframe, days)
    
    if df is None or len(df) < 100:
        print("[ERROR] Insufficient data")
        return
    
    # Run backtest
    engine = BacktestEngine(initial_capital=10000, risk_per_trade=100)
    results = engine.run_backtest(df, timeframe=timeframe, min_strength=min_strength)
    
    # Print results
    engine.print_summary(results)
    
    # Export to session folder
    filename = f"summary.json"
    engine.export_results(filename, output_dir=output_dir)
    
    print(f"\n[SYSTEM] Backtest complete. All data saved to: {output_dir}")
    return results, engine

async def run_threshold_optimization(symbol="BTC/USDT", timeframe="1m", days=7, output_parent="backtests"):
    """
    Tests different MIN_SIGNAL_STRENGTH thresholds to find optimal.
    """
    # Create optimization folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root_dir = os.path.join(output_parent, f"opt_{symbol.replace('/', '_')}_{timestamp}")
    os.makedirs(root_dir, exist_ok=True)
    
    print("\n" + "="*80)
    print(f"THRESHOLD OPTIMIZATION: {symbol} {timeframe} ({days} days)")
    print(f"Saving to: {root_dir}")
    print("="*80)
    
    # Fetch data once
    df = await fetch_historical_data(symbol, timeframe, days)
    
    if df is None or len(df) < 100:
        print("[ERROR] Insufficient data")
        return
    
    thresholds = [40, 50, 60, 70, 80]
    results_summary = []
    
    for threshold in thresholds:
        print(f"\n{'─'*80}")
        print(f"Testing MIN_SIGNAL_STRENGTH = {threshold}%")
        
        engine = BacktestEngine(initial_capital=10000, risk_per_trade=100)
        results = engine.run_backtest(df, timeframe=timeframe, min_strength=threshold)
        
        if 'error' not in results:
            results_summary.append({
                'threshold': threshold,
                'win_rate': results['win_rate'],
                'total_trades': results['total_trades'],
                'profit_factor': results['profit_factor'],
                'total_return': results['total_return_pct']
            })
            
            # Export each threshold run to its own subfolder
            sub_dir = os.path.join(root_dir, f"thresh_{threshold}")
            engine.export_results(f"results_{threshold}.json", output_dir=sub_dir)
    
    # Print comparison table
    print("\n" + "="*80)
    print("THRESHOLD COMPARISON")
    print("="*80)
    print(f"{'Threshold':<15} {'Trades':<10} {'Win Rate':<12} {'P.Factor':<12} {'Return':<10}")
    print("-"*80)
    
    for r in results_summary:
        print(f"{r['threshold']}%{'':<12} {r['total_trades']:<10} {r['win_rate']}%{'':<9} {r['profit_factor']:<12} {r['total_return']}%")
    
    print("="*80)
    
    # Find optimal
    if results_summary:
        best = max(results_summary, key=lambda x: x['win_rate'])
        print(f"\n🏆 OPTIMAL THRESHOLD: {best['threshold']}% (Win Rate: {best['win_rate']}%)")

async def run_multi_asset_backtest(timeframe="1m", days=7, min_strength=50, output_parent="backtests"):
    """
    Runs backtests on multiple assets.
    """
    assets = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    
    # Create multi-asset folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root_dir = os.path.join(output_parent, f"multi_{timestamp}")
    os.makedirs(root_dir, exist_ok=True)

    print("\n" + "="*80)
    print(f"MULTI-ASSET BACKTEST ({len(assets)} assets)")
    print(f"Saving to: {root_dir}")
    print("="*80)
    
    all_results = []
    
    for symbol in assets:
        print(f"\n{'='*80}")
        print(f"Testing: {symbol}")
        
        try:
            # We call run_single_backtest but point it to our root_dir
            results, engine = await run_single_backtest(symbol, timeframe, days, min_strength, output_parent=root_dir)
            
            if results and 'error' not in results:
                all_results.append({
                    'symbol': symbol,
                    'win_rate': results['win_rate'],
                    'total_trades': results['total_trades'],
                    'profit_factor': results['profit_factor'],
                    'total_return': results['total_return_pct']
                })
        except Exception as e:
            print(f"[ERROR] Failed to backtest {symbol}: {e}")
    
    # Summary comparison
    if all_results:
        print("\n" + "="*80)
        print("ASSET COMPARISON")
        print("="*80)
        print(f"{'Asset':<15} {'Trades':<10} {'Win Rate':<12} {'P.Factor':<12} {'Return':<10}")
        print("-"*80)
        
        for r in all_results:
            print(f"{r['symbol']:<15} {r['total_trades']:<10} {r['win_rate']}%{'':<9} {r['profit_factor']:<12} {r['total_return']}%")
        
        print("="*80)

def main():
    """
    Main entry point with CLI options.
    """
    print("\n" + "="*80)
    print("BACKTESTING SYSTEM")
    print("="*80)
    print("\nOptions:")
    print("1. Single Asset Backtest (BTC/USDT, 7 days, 1m)")
    print("2. Threshold Optimization (BTC/USDT, 7 days, 1m)")
    print("3. Multi-Asset Backtest (BTC/ETH/SOL, 7 days, 1m)")
    print("4. Extended Backtest (BTC/USDT, 30 days, 1m)")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        asyncio.run(run_single_backtest("BTC/USDT", "1m", 7, 50))
    elif choice == "2":
        asyncio.run(run_threshold_optimization("BTC/USDT", "1m", 7))
    elif choice == "3":
        asyncio.run(run_multi_asset_backtest("1m", 7, 50))
    elif choice == "4":
        asyncio.run(run_single_backtest("BTC/USDT", "1m", 30, 50))
    else:
        print("Invalid option!")

if __name__ == "__main__":
    main()
