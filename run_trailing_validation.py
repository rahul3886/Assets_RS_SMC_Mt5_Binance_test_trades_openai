import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_provider import AsyncDataProvider
import strategy
from trailing_engine import PositionManager

# Configuration
ASSETS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
DAYS = 3
RISK_AMOUNT = 1000  # $1000 per trade

class TrailingBacktester:
    def __init__(self):
        self.trades = []
        self.capital = 100000 # Paper capital
        
    def simulate_trade_with_engine(self, df, start_idx, signal, entry_price, sl_price, tp_price):
        """
        Simulates a trade by stepping forward 1 candle at a time and 
        letting PositionManager update the SL/Exit.
        """
        pm = PositionManager()
        symbol = "TEST_ASSET"
        direction = "BUY" if "BUY" in signal else "SELL"
        
        # Register position
        pm.add_position(symbol, direction, entry_price, sl_price, tp_price)
        
        max_bars = 200 # Max hold time
        exit_reason = "TIMEOUT"
        exit_price = df['close'].iloc[min(start_idx + max_bars, len(df)-1)]
        bars_held = 0
        
        # Step forward
        for i in range(1, max_bars + 1):
            curr_idx = start_idx + i
            if curr_idx >= len(df):
                break
                
            curr_row = df.iloc[curr_idx]
            curr_high = curr_row['high']
            curr_low = curr_row['low']
            curr_close = curr_row['close']
            curr_time = curr_idx
            
            # 1. Check Hard SL/TP hits first (Intra-candle)
            pos_data = pm.active_positions.get(symbol)
            if not pos_data: break
            
            current_sl = pos_data['current_sl']
            target_tp = pos_data['target_tp']
            
            if direction == "BUY":
                if curr_low <= current_sl:
                    exit_price = current_sl
                    exit_reason = "SL_HIT"
                    if pos_data.get('is_be'): exit_reason = "BE_HIT"
                    if "PIVOT" in pos_data.get('status', ''): exit_reason = "TRAIL_SL_HIT"
                    break
                if curr_high >= target_tp:
                    exit_price = target_tp
                    exit_reason = "TP_HIT"
                    break
            else: # SELL
                if curr_high >= current_sl:
                    exit_price = current_sl
                    exit_reason = "SL_HIT"
                    if pos_data.get('is_be'): exit_reason = "BE_HIT"
                    if "PIVOT" in pos_data.get('status', ''): exit_reason = "TRAIL_SL_HIT"
                    break
                if curr_low <= target_tp:
                    exit_price = target_tp
                    exit_reason = "TP_HIT"
                    break
            
            # 2. Update Engine (On Close)
            # Pass historical slice for pivot/rsi calculation
            # Optimization: Slice only needed length to avoid copying huge df
            # Engine needs 20-30 candles for pivots/rsi
            hist_slice = df.iloc[max(0, curr_idx-50):curr_idx+1]
            
            updates = pm.process_update(symbol, curr_close, hist_slice, None)
            
            if updates:
                if updates.get('exit'):
                    exit_price = curr_close
                    exit_reason = updates.get('status', "ENGINE_EXIT")
                    break
                
                if updates.get('sl'):
                    # print(f"    🔄 SL Moved to {updates['sl']:.2f} ({updates.get('status')})")
                    pass
            
            bars_held = i
            
        # Calculate Result under "invest $1000 per trade"
        # If Invest $1000, Position Size = 1000 USD value.
        # Qty = 1000 / Entry
        qty = RISK_AMOUNT / entry_price
        
        if direction == "BUY":
            pnl = (exit_price - entry_price) * qty
        else:
            pnl = (entry_price - exit_price) * qty
            
        pnl_pct = (pnl / RISK_AMOUNT) * 100
        
        return {
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "bars_held": bars_held
        }

    async def run(self):
        provider = AsyncDataProvider()
        try:
            print(f"\n🚀 BASELINE TRAILING BACKTEST (3 Days) | Risk ${RISK_AMOUNT} | Assets: {ASSETS}")
            print("="*100)
            
            total_pnl = 0
            
            for symbol in ASSETS:
                print(f"\n[ANALYZING] {symbol}...")
                
                # Fetch 3 days data
                since = int((datetime.now() - timedelta(days=DAYS)).timestamp() * 1000)
                ohlcv = await provider.exchange.fetch_ohlcv(symbol, '1m', since=since, limit=DAYS*1440)
                if not ohlcv:
                    print("  No data.")
                    continue
                    
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric)
                
                # Pre-calc indicators
                df, all_pivots, p_params, pivots_h, pivots_l = strategy.prepare_data(df)
                
                asset_trades = []
                
                # Scan
                print(f"  Scanning {len(df)} candles...")
                start_bar = 200
                
                # We need to jump forward to avoid overlapping trades for clarity? 
                # Or simulates every valid signal? 
                # Let's verify every valid signal but skip if we are "in a trade"? 
                # For simplicity, let's take every signal that meets the Sweet Spot threshold.
                # Thresholds: BTC=80, ETH=70, SOL=65 (From previous result)
                
                threshold_map = {"BTC/USDT": 80, "ETH/USDT": 70, "SOL/USDT": 65}
                min_strength = threshold_map.get(symbol, 60)
                
                i = start_bar
                while i < len(df) - 10:
                    res = strategy.check_signals_optimized(df, i, all_pivots, p_params, pivots_h, pivots_l)
                    if not res or not res[0] or res[0] == "NEUTRAL":
                        i += 1
                        continue
                        
                    signal, info, ctx = res
                    if info['strength'] < min_strength:
                        i += 1
                        continue
                        
                    # Found Signal -> Simulate
                    entry_price = df['close'].iloc[i]
                    sl_price = info.get('sl_price')
                    
                    # Calculate TP (1.5R default used in V2 optimization)
                    # Or rely on dynamic engine? 
                    # The current engine supports TP but let's give it the calculated TP from strategy
                    rr_ratio = 1.5
                    if "BUY" in signal:
                        dist = entry_price - sl_price
                        tp_price = entry_price + (dist * rr_ratio)
                    else:
                        dist = sl_price - entry_price
                        tp_price = entry_price - (dist * rr_ratio)
                        
                    trade_res = self.simulate_trade_with_engine(df, i, signal, entry_price, sl_price, tp_price)
                    
                    # Log 
                    trade_res['timestamp'] = df['timestamp'].iloc[i]
                    trade_res['symbol'] = symbol
                    asset_trades.append(trade_res)
                    
                    # Skip ahead by bars held + 1 to avoid duplicate/spam signals during the trade
                    i += trade_res['bars_held'] + 1
                    
                # Summarize Asset
                wins = [t for t in asset_trades if t['pnl'] > 0]
                losses = [t for t in asset_trades if t['pnl'] <= 0]
                net_pnl = sum(t['pnl'] for t in asset_trades)
                wr = (len(wins) / len(asset_trades) * 100) if asset_trades else 0
                
                total_pnl += net_pnl
                
                print(f"  👉 Results for {symbol} (Thr {min_strength}%):")
                print(f"     Trades: {len(asset_trades)} | WR: {wr:.1f}% | Net PnL: ${net_pnl:.2f}")
                for t in asset_trades:
                    icon = "✅" if t['pnl'] > 0 else "❌"
                    print(f"     {icon} {t['timestamp']} {t['direction']} | Exit: {t['exit_reason']} | PnL: ${t['pnl']:.2f} ({t['pnl_pct']:.1f}%)")

            print("\n" + "="*100)
            print(f"💰 TOTAL PORTFOLIO PnL: ${total_pnl:.2f}")
            print("="*100)

        finally:
            await provider.close()

if __name__ == "__main__":
    asyncio.run(TrailingBacktester().run())
