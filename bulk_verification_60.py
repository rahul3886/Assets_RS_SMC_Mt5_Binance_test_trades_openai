import asyncio
import pandas as pd
from datetime import datetime, timedelta
from data_provider import AsyncDataProvider
from backtest_engine import BacktestEngine
import json

async def run_requested_backtest():
    """
    Requested Backtest: 3 Days, 60% Strength, Multi-Asset Portfolio.
    Assets: BTC/USDT, EURUSD, XAUUSD, SOL/USDT, USDJPY, XAGUSD.
    """
    assets = [
        {"symbol": "BTC/USDT", "type": "CRYPTO"},
        {"symbol": "EURUSD", "type": "FX"},
        {"symbol": "XAUUSD", "type": "COMMODITY"},
        {"symbol": "SOL/USDT", "type": "CRYPTO"},
        {"symbol": "USDJPY", "type": "FX"},
        {"symbol": "XAGUSD", "type": "COMMODITY"}
    ]
    
    threshold = 60
    days = 3
    provider = AsyncDataProvider()
    final_report = {}
    
    print("\n" + "="*80)
    print(f"SPECIAL VERIFICATION: {days}-DAY PORTFOLIO BACKTEST ({threshold}% Threshold)")
    print("="*80)
    
    try:
        for asset in assets:
            symbol = asset["symbol"]
            print(f"\n[ASSET] {symbol} ({asset['type']})...")
            
            # Fetch 1m data for 3 days (~4320 bars)
            if asset["type"] == "CRYPTO":
                since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                all_ohlcv = []
                temp_since = since
                while True:
                    ohlcv = await provider.exchange.fetch_ohlcv(symbol, '1m', since=temp_since, limit=1000)
                    if not ohlcv: break
                    all_ohlcv.extend(ohlcv)
                    temp_since = ohlcv[-1][0] + 1
                    if len(all_ohlcv) >= (days * 1440): break
                df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            else:
                # MT5 Data
                df = await provider.fetch_mt5_ohlcv(symbol, '1m', limit=(days * 1440))
            
            if df is None or df.empty:
                print(f"[ERROR] No data found for {symbol}")
                continue
                
            # Run Backtest
            engine = BacktestEngine()
            metrics = engine.run_backtest(df, min_strength=threshold)
            
            # Breakdown by Session
            df_trades = pd.DataFrame(engine.trades)
            session_stats = {}
            if not df_trades.empty:
                for sess in ['ASIAN', 'LONDON', 'NEW_YORK']:
                    sdf = df_trades[df_trades['session'] == sess]
                    if not sdf.empty:
                        session_stats[sess] = {
                            "trades": len(sdf),
                            "win_rate": round((len(sdf[sdf['outcome']=='WIN']) / len(sdf)) * 100, 2),
                            "rr_yield": round(sum([t['risk_reward'] if t['outcome']=='WIN' else -1 for _, t in sdf.iterrows()]), 2)
                        }
            
            print(f"[RESULT] {symbol} | WR: {metrics.get('win_rate', 0):.2f}% | Trades: {metrics.get('signals_traded', 0)} | Yield: {metrics.get('total_return_pct', 0):.2f}%")
            if session_stats:
                print(f"  > Sessions: {session_stats}")
                
            final_report[symbol] = {
                "win_rate": metrics.get('win_rate', 0),
                "trades": metrics.get('signals_traded', 0),
                "profit_factor": metrics.get('profit_factor', 0),
                "sessions": session_stats
            }
            
    finally:
        await provider.close()
        
    # Final Table
    print("\n" + "="*80)
    print(f"{'Asset':12} | {'Win Rate':10} | {'Trades':8} | {'Yield (RR)':8}")
    print("-"*80)
    for sym, data in final_report.items():
        total_rr = sum([s['rr_yield'] for s in data['sessions'].values()]) if data['sessions'] else 0
        print(f"{sym:12} | {data['win_rate']:9.2f}% | {data['trades']:8} | {total_rr:8.2f}")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_requested_backtest())
