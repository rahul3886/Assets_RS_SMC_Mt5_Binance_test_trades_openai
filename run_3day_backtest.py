import asyncio
import ccxt.async_support as ccxt
import pandas as pd
from datetime import datetime, timedelta
from backtest_engine import BacktestEngine

async def run_3day_optimization():
    """
    Faster 3-day threshold optimization
    """
    symbol = "BTC/USDT"
    timeframe = "1m"
    days = 3
    
    print("\n" + "="*80)
    print(f"3-DAY THRESHOLD OPTIMIZATION: {symbol} {timeframe}")
    print("="*80)
    
    # Fetch data
    print(f"\n[DATA] Fetching {days} days of {timeframe} data for {symbol}...")
    exchange = ccxt.binance({'enableRateLimit': True})
    
    try:
        since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        all_ohlcv = []
        
        while True:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            if len(ohlcv) < 1000:
                break
            print(f"[DATA] Fetched {len(all_ohlcv)} candles so far...")
        
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        print(f"[DATA] ✓ Loaded {len(df)} candles from {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
        
    finally:
        await exchange.close()
    
    # Test thresholds
    thresholds = [40, 50, 60, 70, 80]
    results_summary = []
    
    for threshold in thresholds:
        print(f"\n{'─'*80}")
        print(f"Testing MIN_SIGNAL_STRENGTH = {threshold}%")
        print(f"{'─'*80}")
        
        engine = BacktestEngine(initial_capital=10000, risk_per_trade=100)
        # Modified run_backtest to optionally print progress would be good, 
        # but let's just print here after each one
        results = engine.run_backtest(df, timeframe=timeframe, min_strength=threshold)
        
        if 'error' not in results:
            results_summary.append({
                'threshold': threshold,
                'win_rate': results['win_rate'],
                'total_trades': results['total_trades'],
                'profit_factor': results['profit_factor'],
                'total_return': results['total_return_pct']
            })
            
            # Save intermediate results
            with open("phase_5_amd_results.json", "w") as f:
                import json
                json.dump(results_summary, f, indent=2)

            print(f"\n📊 Quick Summary:")
            print(f"   Win Rate: {results['win_rate']}%")
            print(f"   Total Trades: {results['total_trades']}")
            print(f"   Total Return: {results['total_return_pct']}%")
    
    # Print comparison
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

if __name__ == "__main__":
    asyncio.run(run_3day_optimization())
