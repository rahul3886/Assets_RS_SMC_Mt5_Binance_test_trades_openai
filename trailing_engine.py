import pandas as pd
import numpy as np
from datetime import datetime

class PositionManager:
    """
    Upgrade 9.1: MTF-Enabled Adaptive Position Management.
    Supports parallel trades on different timeframes (e.g., 1m and 5m).
    """
    def __init__(self):
        self.active_positions = {} # (symbol, timeframe) -> position_data

    def process_update(self, symbol, timeframe, current_price, df, signal_info):
        """
        Processes a price update for an active position.
        """
        key = (symbol, timeframe)
        if key not in self.active_positions:
            return None
            
        pos = self.active_positions[key]
        direction = pos['direction']
        entry_price = pos['entry_price']
        
        # 1. Calculate Current Risk/Reward
        risk = abs(entry_price - pos['initial_sl'])
        if risk == 0: risk = entry_price * 0.001
        
        current_profit = (current_price - entry_price) if direction == 'BUY' else (entry_price - current_price)
        rr = current_profit / risk
        
        updates = {}
        
        # --- PHASE 1: Breakeven (BE) at 1:1 RR ---
        if rr >= 1.0 and not pos.get('is_be'):
            new_sl = entry_price + (entry_price * 0.0001 if direction == 'BUY' else -entry_price * 0.0001)
            updates['sl'] = new_sl
            updates['status'] = f"🛡️ BE (RR 1:1) [{timeframe}]"
            pos['is_be'] = True
            pos['current_sl'] = new_sl

        # --- PHASE 2: Structural Trailing (Pivot-Based) ---
        # 5m trades use wider structural pivots (length=10)
        # 1m trades use tighter structural pivots (length=5)
        pivot_len = 10 if timeframe == '5m' else 5
        
        if rr >= 0.5:
            from smc_logic import detect_pivots
            df_pivots = detect_pivots(df, length=pivot_len)
            
            if direction == 'BUY':
                recent_lows = df_pivots[df_pivots['pivot_l'] == 1]['low'].tail(2).tolist()
                if recent_lows:
                    new_struct_sl = max(recent_lows)
                    if new_struct_sl > pos['current_sl']:
                        updates['sl'] = new_struct_sl
                        updates['status'] = f"📈 TRAIL PIVOT [{timeframe}]"
                        pos['current_sl'] = new_struct_sl
            else:
                recent_highs = df_pivots[df_pivots['pivot_h'] == 1]['high'].tail(2).tolist()
                if recent_highs:
                    new_struct_sl = min(recent_highs)
                    if new_struct_sl < pos['current_sl']:
                        updates['sl'] = new_struct_sl
                        updates['status'] = f"📉 TRAIL PIVOT [{timeframe}]"
                        pos['current_sl'] = new_struct_sl

        # --- PHASE 3: RSI Exhaustion Exit ---
        if 'RSI' in df.columns:
            rsi_val = df['RSI'].iloc[-1]
            slope = df['RSI'].iloc[-1] - df['RSI'].iloc[-3] if len(df) > 3 else 0
            
            if direction == 'BUY' and rsi_val >= 80 and slope < -2:
                updates['exit'] = True
                updates['status'] = f"🏁 RSI EXH [{timeframe}]"
            elif direction == 'SELL' and rsi_val <= 20 and slope > 2:
                updates['exit'] = True
                updates['status'] = f"🏁 RSI EXH [{timeframe}]"

        return updates if updates else None

    def add_position(self, symbol, timeframe, direction, entry_price, sl_price, tp_price):
        """Registers a new trade for tracking."""
        self.active_positions[(symbol, timeframe)] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": direction,
            "entry_price": entry_price,
            "initial_sl": sl_price,
            "current_sl": sl_price,
            "target_tp": tp_price,
            "is_be": False,
            "start_time": datetime.now()
        }

    def remove_position(self, symbol, timeframe):
        """Removes a finished trade."""
        key = (symbol, timeframe)
        if key in self.active_positions:
            del self.active_positions[key]
