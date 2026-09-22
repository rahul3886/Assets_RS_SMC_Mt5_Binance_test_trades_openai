import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_provider import AsyncDataProvider
import strategy
from trailing_engine_v2 import TrailingEngineV2

# Configuration
ASSETS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
DAYS = 3
RISK_AMOUNT = 1000

def generate_s15_map(df_1m):
    """
    Resamples 1m data to 15m and calculates signal strength for each 15m bar.
    Returns dict: timestamp -> strength_score
    """
    # Resample
    df_15m = df_1m.resample('15min', on='timestamp').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    # Pre-calc indicators for 15m
    df_15m, all_pivots, p_params, pivots_h, pivots_l = strategy.prepare_data(df_15m)
    
    s15_map = {}
    
    # Calculate strength for each candle
    # We need to scan from index 50 onwards
    for i in range(50, len(df_15m)):
        res = strategy.check_signals_optimized(df_15m, i, all_pivots, p_params, pivots_h, pivots_l)
        if res and res[1]:
            strength = res[1]['strength']
            ts = df_15m['timestamp'].iloc[i]
            s15_map[ts] = strength
            
    return s15_map

class TrailingBacktesterV2:
    def simulate_trade_v2(self, engine, df, start_idx, signal, entry_price, sl_price, tp_price, s15_map):
        """
        Simulates a trade using TrailingEngineV2.
        """
        symbol = "TEST_ASSET"
        direction = "BUY" if "BUY" in signal else "SELL"
        start_time = df['timestamp'].iloc[start_idx]
        
        # Register position
        engine.add_position(symbol, direction, entry_price, sl_price, tp_price, start_time)
        
        max_bars = 200
        exit_reason = "TIMEOUT"
        exit_price = df['close'].iloc[min(start_idx + max_bars, len(df)-1)]
        bars_held = 0
        
        # Step forward
        for i in range(1, max_bars + 1):
            curr_idx = start_idx + i
            if curr_idx >= len(df): break
            
            curr_row = df.iloc[curr_idx]
            curr_high = curr_row['high']
            curr_low = curr_row['low']
            curr_close = curr_row['close']
            
            # 1. Intra-candle Hard Check (SL/TP)
            pos = engine.active_positions.get(symbol)
            if not pos: break
            
            current_sl = pos['current_sl']
            target_tp = pos['target_tp']
            
            # Simple check
            if direction == "BUY":
                if curr_low <= current_sl:
                    exit_price = current_sl
                    exit_reason = "SL_HIT" # Or dynamic SL hit
                    if "Adjusted" in pos.get('logs', [])[-1] if pos.get('logs') else False: 
                        exit_reason = "DYNAMIC_SL_HIT"
                    break
            else: # SELL
                if curr_high >= current_sl:
                    exit_price = current_sl
                    exit_reason = "SL_HIT"
                    break
            
            # 2. Engine Update
            # Get S1 score for current candle (needed for G calculation)
            # We assume S1 is roughly the entry strength or re-calculated?
            # User requirement: "Update Metrics... Recalculate S1"
            # This is expensive. For backtest, let's approximation:
            # S1 = Entry Strength? No, that defeats "Signal Flip".
            # We need S1 for *this* candle.
            
            # Re-running check_signals_optimized for current candle?
            # Since we have pre-calced pivots/indicators in 'df', it is fast O(1).
            # We need to pass the pre-calced structures from main loop?
            # For simplicity, let's assume S1 is available or re-calc it.
            # We can re-calc quickly using `strategy.check_signals_optimized`
            # But we need 'all_pivots' etc.
            # Let's pass `strategy` and `data params` to simulate_trade? 
            # Or just assume S1 decays/persists?
            # Correct approach: Re-calculate S1.
            
            # Hack: We need access to the data structures prepared in run() method.
            # Let's attach them to `engine` or calculate in `run()` and pass.
            pass 
            
            bars_held = i
            
        return {
            "exit_reason": "NOT_IMPLEMENTED" 
        }

    # Redefine logic to simpler flow
    async def run(self):
        provider = AsyncDataProvider()
        try:
            print(f"\n🚀 TRAILING V2 BACKTEST (3 Days) | Risk ${RISK_AMOUNT} | Assets: {ASSETS}")
            print("="*100)
            
            total_pnl = 0
            
            for symbol in ASSETS:
                print(f"\n[ANALYZING] {symbol}...")
                
                # Fetch
                since = int((datetime.now() - timedelta(days=DAYS)).timestamp() * 1000)
                ohlcv = await provider.exchange.fetch_ohlcv(symbol, '1m', since=since, limit=DAYS*1440)
                if not ohlcv: continue
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric)
                
                # 1. Generate S15 Map
                print("  Generating 15m Strength Map...")
                s15_map = generate_s15_map(df)
                
                # 2. Pre-calc 1m
                df, all_pivots, p_params, pivots_h, pivots_l = strategy.prepare_data(df)
                
                # Engine
                engine = TrailingEngineV2(s15_map)
                
                asset_trades = []
                threshold_map = {"BTC/USDT": 80, "ETH/USDT": 70, "SOL/USDT": 65}
                min_strength = threshold_map.get(symbol, 60)
                
                i = 200
                print(f"  [DEBUG] Starting scan for {symbol} at idx {i}. Min Strength: {min_strength}")
                while i < len(df) - 10:
                    # Check Signal (S1)
                    res = strategy.check_signals_optimized(df, i, all_pivots, p_params, pivots_h, pivots_l)
                    if not res or not res[0] or res[0] == "NEUTRAL":
                        i += 1
                        continue
                        
                    signal, info, ctx = res
                    s1_entry = info['strength']
                    
                    # print(f"  [DEBUG] Found {signal} at {df['timestamp'].iloc[i]} strength={s1_entry}")
                    
                    if s1_entry < min_strength:
                        i += 1
                        continue
                        
                    print(f"  [SIGNAL] {signal} at {df['timestamp'].iloc[i]} (Str {s1_entry}%)")
                    
                    # TRADE START
                    entry_price = df['close'].iloc[i]
                    sl_price = info.get('sl_price')
                    tp_price = 0 # V2 uses trailing mostly, but keep strategy TP as reference?
                    # The V2 spec doesn't mention Fixed TP, only "Exit Matrix".
                    # Let's set high TP to rely on Matrix/Trailing.
                    tp_price = entry_price * 1.5 if "BUY" in signal else entry_price * 0.5
                    
                    engine.add_position(symbol, "BUY" if "BUY" in signal else "SELL", entry_price, sl_price, tp_price, df['timestamp'].iloc[i])
                    
                    # SIMULATE FORWARD
                    exit_price = df['close'].iloc[i]
                    exit_reason = "TIMEOUT"
                    bars_held = 0
                    
                    for j in range(1, 200): # Max hold
                        curr_idx = i + j
                        if curr_idx >= len(df): break
                        
                        curr_row = df.iloc[curr_idx]
                        hist_slice = df.iloc[max(0, curr_idx-50):curr_idx+1]
                        
                        # Recalculate S1 for this candle (needed for G-Score)
                        s1_now = 50
                        res_now = strategy.check_signals_optimized(df, curr_idx, all_pivots, p_params, pivots_h, pivots_l)
                        if res_now and res_now[1]:
                             s1_now = res_now[1]['strength']
                        ctx_now = res_now[2] if res_now else {}
                        
                        updates = engine.process_update(symbol, curr_row, hist_slice, s1_now, ctx_now)
                        
                        # Intra-candle SL check (simplified to Close for cleanliness, or Low/High)
                        pos = engine.active_positions[symbol]
                        
                        # Check Hard SL Hit (Low/High)
                        if pos['direction'] == "BUY":
                             if curr_row['low'] <= pos['current_sl']:
                                 exit_price = pos['current_sl']
                                 exit_reason = "SL_HIT"
                                 # Determine if it was Dynamic or Base
                                 if pos['current_sl'] != sl_price: exit_reason = "DYNAMIC_SL_HIT"
                                 break
                        else:
                             if curr_row['high'] >= pos['current_sl']:
                                 exit_price = pos['current_sl']
                                 exit_reason = "SL_HIT"
                                 if pos['current_sl'] != sl_price: exit_reason = "DYNAMIC_SL_HIT"
                                 break
                        
                        # Engines Updates
                        if updates:
                            if updates.get('exit'):
                                exit_price = curr_row['close']
                                exit_reason = updates.get('status')
                                break
                                
                        bars_held = j
                    
                    # Record
                    qty = RISK_AMOUNT / entry_price
                    pnl = (exit_price - entry_price) * qty if "BUY" in signal else (entry_price - exit_price) * qty
                    pnl_pct = (pnl / RISK_AMOUNT) * 100
                    
                    asset_trades.append({
                        "timestamp": df['timestamp'].iloc[i],
                        "symbol": symbol,
                        "direction": "BUY" if "BUY" in signal else "SELL",
                        "exit_reason": exit_reason,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "bars_held": bars_held
                    })
                    
                    # Cleanup
                    if symbol in engine.active_positions: del engine.active_positions[symbol]
                    i += bars_held + 1
                    
                # Result
                net_pnl = sum(t['pnl'] for t in asset_trades)
                wr = (len([t for t in asset_trades if t['pnl'] > 0]) / len(asset_trades) * 100) if asset_trades else 0
                
                total_pnl += net_pnl
                print(f"  👉 V2 Results for {symbol}:")
                print(f"     Trades: {len(asset_trades)} | WR: {wr:.1f}% | Net PnL: ${net_pnl:.2f}")
                for t in asset_trades:
                    icon = "✅" if t['pnl'] > 0 else "❌"
                    print(f"     {icon} {t['timestamp']} {t['direction']} | Exit: {t['exit_reason']} | PnL: ${t['pnl']:.2f}")

            print("\n" + "="*100)
            print(f"💰 TOTAL PORTFOLIO PnL (V2): ${total_pnl:.2f}")
            print("="*100)

        finally:
            await provider.close()

if __name__ == "__main__":
    try:
        asyncio.run(TrailingBacktesterV2().run())
    except KeyboardInterrupt:
        pass
