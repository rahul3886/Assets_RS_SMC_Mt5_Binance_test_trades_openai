import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_provider import AsyncDataProvider
import strategy
import MetaTrader5 as mt5

def fast_simulate(df, entry_idx, signal, sl_price, tp_price):
    """Ultra-fast look-ahead for trade simulation."""
    max_bars = 100
    end_idx = min(entry_idx + max_bars, len(df))
    
    for i in range(entry_idx + 1, end_idx):
        h = df['high'].iloc[i]
        l = df['low'].iloc[i]
        
        if "BUY" in signal:
            if l <= sl_price: return "LOSS", i - entry_idx
            if h >= tp_price: return "WIN", i - entry_idx
        else:
            if h >= sl_price: return "LOSS", i - entry_idx
            if l <= tp_price: return "WIN", i - entry_idx
            
    # Timeout
    return "TIMEOUT", max_bars

async def run_portfolio_optimization_v2():
    import config
    assets = []
    for s in config.CRYPTO_WATCHLIST: assets.append({"symbol": s, "type": "CRYPTO"})
    for s in config.FOREX_WATCHLIST: assets.append({"symbol": s, "type": "FX"})
    for s in config.COMMODITIES_WATCHLIST: assets.append({"symbol": s, "type": "COMMODITY"})
    
    thresholds = [60, 65, 70, 75, 80]
    days = 3
    provider = AsyncDataProvider()
    
    if provider.exchange:
        print("[INIT] Pre-loading exchange markets...")
        await provider.exchange.load_markets()
    
    try: mt5.shutdown()
    except: pass
        
    final_report = {}

    print(f"\nFAST PORTFOLIO OPTIMIZATION ({days} DAYS) | 20 Assets | {thresholds} Thr")
    print("="*80)
    
    try:
        for asset in assets:
            symbol = asset["symbol"]
            print(f"\n[ASSET] {symbol}...")
            
            # 1. Fetch
            df = None
            if asset["type"] == "CRYPTO":
                since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                ohlcv = await provider.exchange.fetch_ohlcv(symbol, '1m', since=since, limit=days*1440)
                if ohlcv:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric)
                await asyncio.sleep(1) # Chill
            else:
                df = await provider.fetch_mt5_ohlcv(symbol, '1m', limit=days*1440)
            
            if df is None or df.empty or len(df) < 200:
                print(f"  [SKIP] No data")
                continue
                
            # 2. Prepare Indicators once
            print(f"  [MATH] Pre-calculating indicators...")
            df, all_pivots, p_params, pivots_h, pivots_l = strategy.prepare_data(df.copy())
            
            # 3. Single Pass Scan
            print(f"  [SCAN] Running parallel-threshold evaluation...")
            # Track stats for each threshold
            stats = {th: {"wins": 0, "losses": 0, "total": 0, "rr_sum": 0} for th in thresholds}
            
            total_candles = len(df) - 301
            for i in range(200, len(df) - 101):
                # Heartbeat every 1000 candles to prevent timeout
                if i % 1000 == 0:
                    prog = ((i - 200) / total_candles) * 100
                    print(f"    [SCAN] {prog:.1f}% complete...")

                res = strategy.check_signals_optimized(df, i, all_pivots, p_params, pivots_h, pivots_l)
                if not res or not res[0] or res[0] == "NEUTRAL":
                    continue
                
                signal, info, ctx = res
                strength = info.get('strength', 0)
                sl = info.get('sl_price')
                
                # Simple TP: 1.5R default
                entry_price = df['close'].iloc[i]
                if "BUY" in signal:
                    tp = entry_price + (entry_price - sl) * 1.5 if sl < entry_price else entry_price * 1.015
                else:
                    tp = entry_price - (sl - entry_price) * 1.5 if sl > entry_price else entry_price * 0.985
                
                # Check outcome once per signal
                outcome, duration = fast_simulate(df, i, signal, sl, tp)
                
                # Update all applicable thresholds
                for th in thresholds:
                    if strength >= th:
                        stats[th]["total"] += 1
                        if outcome == "WIN":
                            stats[th]["wins"] += 1
                            stats[th]["rr_sum"] += 1.5
                        elif outcome == "LOSS" or outcome == "TIMEOUT":
                            stats[th]["losses"] += 1
                            stats[th]["rr_sum"] -= 1.0
            
            # 4. Analyze results
            asset_results = {}
            for th in thresholds:
                s = stats[th]
                wr = (s['wins'] / s['total'] * 100) if s['total'] > 0 else 0
                asset_results[th] = {"wr": wr, "trades": s['total'], "yield": s['rr_sum']}
            
            final_report[symbol] = asset_results
            
    finally:
        await provider.close()
        
    # Print Final Recommendations
    print("\n" + "="*100)
    print(f"{'Asset':12} | {'Sweet Spot':10} | {'Win Rate':8} | {'Trades':6} | {'Yield (R)'}")
    print("-"*100)
    for sym, res in final_report.items():
        # Choose best: WR > 50% with most trades, or highest yield
        best_th = 60
        best_score = -999
        for th, m in res.items():
            if m['trades'] < 3: continue
            score = (m['wr'] * 1.5) + m['yield'] 
            if score > best_score:
                best_score = score
                best_th = th
        
        m = res[best_th]
        print(f"{sym:12} | {best_th}%        | {m['wr']:6.1f}% | {m['trades']:6} | {m['yield']:8.1f}")

if __name__ == "__main__":
    asyncio.run(run_portfolio_optimization_v2())
