"""
Quick validation script to test current strategy performance
Uses recent data for faster results
"""
import asyncio
import ccxt.async_support as ccxt
import pandas as pd
from backtest_engine import BacktestEngine

async def quick_test():
    """
    Quick 24-hour backtest for rapid validation
    """
    print("\n" + "=" * 70)
    print("QUICK VALIDATION TEST (Last 24 hours)")
    print("=" * 70)
    
    # Fetch recent data
    exchange = ccxt.binance({'enableRateLimit': True})
    
    try:
        print("\n[1/3] Fetching BTC/USDT 1m data (last 24 hours)...")
        ohlcv = await exchange.fetch_ohlcv("BTC/USDT", "1m", limit=1440)  # 24 hours
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        print(f"✓ Loaded {len(df)} candles")
        print(f"  Period: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
        
        # Run backtest
        print("\n[2/3] Running backtest simulation...")
        engine = BacktestEngine(initial_capital=10000, risk_per_trade=100)
        results = engine.run_backtest(df, timeframe="1m", min_strength=50)
        
        #Print results
        print("\n[3/3] Results:")
        engine.print_summary(results)
        
        # Quick interpretation
        print("\n" + "=" * 70)
        print("INTERPRETATION")
        print("=" * 70)
        
        if results.get('win_rate', 0) >= 70:
            print("✅ EXCELLENT: Win rate >= 70% - Strategy performing well!")
        elif results.get('win_rate', 0) >= 60:
            print("✓ GOOD: Win rate 60-70% - Above average performance")
        elif results.get('win_rate', 0) >= 50:
            print("⚠️  AVERAGE: Win rate 50-60% - Room for improvement")
        else:
            print("❌ BELOW TARGET: Win rate < 50% - Needs optimization")
            
        if results.get('total_trades', 0) < 5:
            print("\n⚠️  Note: Low trade count. Consider extending test period.")
            
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(quick_test())
