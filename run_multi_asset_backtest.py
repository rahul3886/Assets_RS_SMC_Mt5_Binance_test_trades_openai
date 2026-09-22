import asyncio
import pandas as pd
from datetime import datetime, timedelta
from data_provider import AsyncDataProvider
from backtest_engine import BacktestEngine
import json

async def run_multi_asset_backtest():
    """
    Backtests Phase 5 across Forex, Gold, and Crypto for thresholds 60, 70, 80.
    """
    assets = [
        {"symbol": "EURUSD", "type": "FX"},
        {"symbol": "GBPJPY", "type": "FX"},
        {"symbol": "XAUUSD", "type": "COMMODITY"},
        {"symbol": "XAGUSD", "type": "COMMODITY"},
        {"symbol": "BTC/USDT", "type": "CRYPTO"},
        {"symbol": "SOL/USDT", "type": "CRYPTO"}
    ]
    
    thresholds = [60, 70, 80]
    provider = AsyncDataProvider()
    all_results = {} # format: {str(threshold): {symbol: metrics}}
    results_file = "multi_asset_threshold_study.json"
    
    # Load existing results to resume
    try:
        with open(results_file, "r") as f:
            all_results = json.load(f)
            print(f"[RESUME] Loaded existing results for thresholds: {list(all_results.keys())}")
    except:
        pass
    
    print("\n" + "="*80)
    print("PHASE 5 MULTI-THRESHOLD VALIDATION (60%, 70%, 80%)")
    print("="*80)
    print("\n" + "="*80, flush=True)
    print("PHASE 5 MULTI-THRESHOLD VALIDATION (60%, 70%, 80%)", flush=True)
    print("="*80, flush=True)
    
    try:
        # 1. Fetch data once per asset
        asset_data = {}
        for asset in assets:
            symbol = asset["symbol"]
            print(f"\n[ASSET] Processing {symbol} ({asset['type']})...", flush=True)
            if asset["type"] == "CRYPTO":
                since = int((datetime.now() - timedelta(days=3)).timestamp() * 1000)
                all_ohlcv = []
                temp_since = since
                while True:
                    ohlcv = await provider.exchange.fetch_ohlcv(symbol, '1m', since=temp_since, limit=1000)
                    if not ohlcv: break
                    all_ohlcv.extend(ohlcv)
                    temp_since = ohlcv[-1][0] + 1
                    if len(all_ohlcv) >= 4320: break
                df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                asset_data[symbol] = df
            else:
                asset_data[symbol] = await provider.fetch_mt5_ohlcv(symbol, '1m', limit=4320)
        
        # 2. Iterate through thresholds
        for threshold in thresholds:
            print(f"\n" + "-"*40)
            print(f"TESTING THRESHOLD: {threshold}%")
            print("-"*40)
            
            threshold_results = {}
            for symbol, df in asset_data.items():
                if df is None or df.empty: continue
                
                # Check if already done
                th_str = str(threshold)
                if th_str in all_results and symbol in all_results[th_str]:
                    print(f"[SKIP] {symbol} already tested at {threshold}%")
                    continue
                
                engine = BacktestEngine()
                metrics = engine.run_backtest(df, min_strength=threshold)

                # Calculate Daily & Session Breakdown
                df_trades = pd.DataFrame(engine.trades)
                daily_counts = {}
                session_metrics = {}
                
                if not df_trades.empty:
                    # 1. Daily Counts
                    df_trades['day'] = df_trades['timestamp'].dt.date
                    daily_counts = df_trades.groupby('day').size().to_dict()
                    
                    # 2. Session Metrics
                    for sess in ['ASIAN', 'LONDON', 'NEW_YORK']:
                        sess_df = df_trades[df_trades['session'] == sess]
                        if not sess_df.empty:
                            s_wins = len(sess_df[sess_df['outcome'] == 'WIN'])
                            s_total = len(sess_df)
                            # Yield: Sum of risk_reward for wins - 1 for losses
                            s_yield = 0
                            for _, t in sess_df.iterrows():
                                if t['outcome'] == 'WIN': s_yield += t['risk_reward']
                                else: s_yield -= 1
                            
                            session_metrics[sess] = {
                                "trades": s_total,
                                "win_rate": round((s_wins / s_total) * 100, 2),
                                "yield_rr": round(s_yield, 2)
                            }
                
                print(f"[RESULT] WR: {metrics.get('win_rate', 0):.2f}% | PF: {metrics.get('profit_factor', 0):.2f} | Trades: {metrics.get('signals_traded', 0)}", flush=True)
                print(f"[DAILY] {daily_counts}", flush=True)
                print(f"[SESSIONS] {session_metrics}", flush=True)
                
                if th_str not in all_results: all_results[th_str] = {}
                all_results[th_str][symbol] = {
                    "win_rate": metrics.get('win_rate', 0),
                    "profit_factor": metrics.get('profit_factor', 0),
                    "total_trades": metrics.get('signals_traded', 0),
                    "total_return": metrics.get('total_return_pct', 0),
                    "daily_trades": {str(k): int(v) for k, v in daily_counts.items()},
                    "session_metrics": session_metrics
                }
            
            # intermediate save
            with open(results_file, "w") as f:
                json.dump(all_results, f, indent=2)
                
    finally:
        await provider.close()
    
    # Final Summary Table
    print("\n" + "="*80)
    print("FINAL PERFORMANCE MATRIX")
    print("="*80)
    print(f"{'Asset':10} | {'60% WR':8} | {'70% WR':8} | {'80% WR':8}")
    print("-"*80)
    for asset in assets:
        sym = asset["symbol"]
        r60 = all_results.get(60, {}).get(sym, {}).get('win_rate', 0)
        r70 = all_results.get(70, {}).get(sym, {}).get('win_rate', 0)
        r80 = all_results.get(80, {}).get(sym, {}).get('win_rate', 0)
        print(f"{sym:10} | {r60:7.2f}% | {r70:7.2f}% | {r80:7.2f}%")

if __name__ == "__main__":
    asyncio.run(run_multi_asset_backtest())
