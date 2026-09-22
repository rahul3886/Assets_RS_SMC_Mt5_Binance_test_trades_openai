import asyncio
import pandas as pd
from datetime import datetime, timedelta
from data_provider import AsyncDataProvider
from backtest_engine import BacktestEngine
import json
import MetaTrader5 as mt5

async def run_portfolio_optimization():
    """
    1. Fetches data for ALL assets in config.py.
    2. Runs backtests at thresholds: 60, 65, 70, 75, 80.
    3. Identifies the "Sweet Spot" (highest Yield or WR > 60%).
    """
    import config
    
    # Combine all watchlists
    all_assets = []
    for s in config.CRYPTO_WATCHLIST: all_assets.append({"symbol": s, "type": "CRYPTO"})
    for s in config.FOREX_WATCHLIST: all_assets.append({"symbol": s, "type": "FX"})
    for s in config.COMMODITIES_WATCHLIST: all_assets.append({"symbol": s, "type": "COMMODITY"})
    
    thresholds = [60, 65, 70, 75, 80]
    days = 3
    provider = AsyncDataProvider()
    
    # Pre-load markets to avoid redundant exchangeInfo calls
    if provider.exchange:
        print("[INIT] Pre-loading exchange markets...")
        await provider.exchange.load_markets()
    
    # Force cleanup of any lingering MT5 sessions
    try:
        mt5.shutdown()
        print("[INIT] Force cleaned up previous MT5 session.")
    except:
        pass
        
    final_results = {} # symbol -> {threshold -> metrics}

    print("\n" + "="*80)
    print(f"PORTFOLIO SWEET SPOT ANALYSIS ({days} DAYS)")
    print(f"Testing Thresholds: {thresholds}")
    print(f"Total Assets: {len(all_assets)}")
    print("="*80)
    
    try:
        for asset in all_assets:
            symbol = asset["symbol"]
            print(f"\n[ASSET] Processing {symbol}...")
            
            # Fetch Data
            df = None
            try:
                if asset["type"] == "CRYPTO":
                    since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                    all_ohlcv = []
                    temp_since = since
                    retry_count = 0
                    while True:
                        try:
                            # Rate limit protection
                            await asyncio.sleep(1.0) 
                            ohlcv = await provider.exchange.fetch_ohlcv(symbol, '1m', since=temp_since, limit=1000)
                        except Exception as e:
                            print(f"[WARN] Fetch error {symbol}: {e}")
                            retry_count += 1
                            if retry_count > 3: break
                            await asyncio.sleep(5) # Long backoff
                            continue
                            
                        if not ohlcv: break
                        all_ohlcv.extend(ohlcv)
                        temp_since = ohlcv[-1][0] + 1
                        if len(all_ohlcv) >= (days * 1440): break
                        
                    if all_ohlcv:
                        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        cols = ['open', 'high', 'low', 'close', 'volume']
                        df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')

                else:
                    # MT5 Data
                    retries = 3
                    for _ in range(retries):
                        df = await provider.fetch_mt5_ohlcv(symbol, '1m', limit=(days * 1440))
                        if df is not None and not df.empty:
                            break
                        print(f"[WARN] Retrying MT5 fetch for {symbol}...")
                        await asyncio.sleep(2)
            except Exception as e:
                print(f"[ERROR] Data fetch failed for {symbol}: {e}")
                continue
            
            if df is None or df.empty:
                print(f"[SKIP] No data for {symbol}")
                continue
            
            # Pre-calculate indicators ONCE per asset (Upgrade #3)
            print(f"  [CACHE] Pre-calculating indicators for {symbol}...")
            import strategy
            prepared_data = strategy.prepare_data(df)
            
            # Run Backtests across thresholds
            asset_res = {}
            for th in thresholds:
                engine = BacktestEngine()
                try:
                    # Pass prepared_data to skip redundant calculation
                    metrics = engine.run_backtest(df, min_strength=th, prepared_data=prepared_data)
                    asset_res[th] = {
                        "win_rate": metrics.get('win_rate', 0),
                        "trades": metrics.get('signals_traded', 0),
                        "yield": metrics.get('total_return_pct', 0)
                    }
                    print(f"  > Thr {th}%: WR {metrics.get('win_rate', 0):.1f}% | Trades {metrics.get('signals_traded', 0)} | Yield {metrics.get('total_return_pct', 0):.2f}%")
                except Exception as e:
                    print(f"  > Thr {th}%: CRASH ({e})")
            
            final_results[symbol] = asset_res
            
            # Rate limit protection between assets
            await asyncio.sleep(2.0)
            
    finally:
        await provider.close()
        
    # Final Optimization Table
    print("\n" + "="*100)
    print(f"{'Asset':12} | {'Sweet Spot':10} | {'Win Rate':8} | {'Trades':6} | {'Yield':8} | {'Logic'}")
    print("-"*100)
    
    for fsym, res_map in final_results.items():
        if not res_map: continue
        
        # Find Sweet Spot: Highest Win Rate where Trades > 5 (to avoid low sample size)
        # OR Highest Yield if WRs are similar
        best_th = 60
        best_score = -999
        best_metric = {}
        
        # 1. Filter out low-volume results (< 10 trades per 3 days is too risky for stats)
        valid_res = {th: m for th, m in res_map.items() if m['trades'] >= 5}
        
        if not valid_res:
             # Fallback to pure yield if volume is ultra low
             valid_res = res_map
        
        for th, m in valid_res.items():
            # Scoring: WinRate * 2 + Yield (Preference for Accuracy)
            score = (m['win_rate'] * 2) + m['yield']
            if score > best_score:
                best_score = score
                best_th = th
                best_metric = m
                
        print(f"{fsym:12} | {best_th}%        | {best_metric.get('win_rate', 0):6.2f}% | {best_metric.get('trades', 0):6} | {best_metric.get('yield', 0):8.2f} | Score: {best_score:.1f}")

if __name__ == "__main__":
    asyncio.run(run_portfolio_optimization())
