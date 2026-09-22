import pandas as pd
import numpy as np
from datetime import datetime

class TrailingEngineV2:
    """
    Upgrade 9: Dynamic Position Management V2.
    Implements:
    - Global Strength G = S1 * (S15/100)
    - PVSRA Climax Detection
    - Dynamic ATR Trailing (K=0.5/1.5/2.0)
    - Weighted Exit Matrix
    """
    def __init__(self, s15_map=None):
        self.active_positions = {}
        self.s15_map = s15_map if s15_map else {} # Timestamp -> Strength Score
        
    def add_position(self, symbol, direction, entry_price, sl_price, tp_price, start_time):
        self.active_positions[symbol] = {
            "direction": direction,
            "entry_price": entry_price,
            "current_sl": sl_price,
            "target_tp": tp_price,
            "start_time": start_time,
            "highest_g": 0,
            "exit_score": 0,
            "logs": []
        }
        
    def _calculate_atr(self, df, period=14):
        # Optimized rolling ATR for the last candle
        if len(df) < period + 1: return df['close'].iloc[-1] * 0.01 # Fallback
        
        # We need true range series
        high = df['high']
        low = df['low']
        close = df['close']
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        return atr
        
    def _get_s15(self, timestamp):
        # Find nearest 15m timestamp <= current timestamp
        # Round down to nearest 15m
        ts = pd.Timestamp(timestamp)
        minute = (ts.minute // 15) * 15
        s15_key = ts.replace(minute=minute, second=0, microsecond=0)
        
        # Look up
        return self.s15_map.get(s15_key, 50) # Default to neutral 50
        
    def process_update(self, symbol, current_row, historical_df, s1_score, ctx):
        if symbol not in self.active_positions: return None
        
        pos = self.active_positions[symbol]
        direction = pos['direction']
        current_price = current_row['close']
        timestamp = current_row['timestamp']
        
        # 1. Update Metrics
        atr = self._calculate_atr(historical_df)
        s15_score = self._get_s15(timestamp)
        
        # Module A: Global Strength (G)
        g_score = s1_score * (s15_score / 100.0)
        pos['highest_g'] = max(pos['highest_g'], g_score)
        
        # Module C: Dynamic Multiplier (K)
        k = 1.5 # Standard
        if g_score > 75: k = 2.0
        elif g_score < 50: k = 0.5
        
        # Update Adaptive SL
        current_sl = pos['current_sl']
        buffer = atr * k
        
        new_sl = current_sl
        sl_updated = False
        
        if direction == "BUY":
            potential_sl = current_price - buffer
            if potential_sl > current_sl:
                new_sl = potential_sl
                sl_updated = True
        else: # SELL
            potential_sl = current_price + buffer
            if potential_sl < current_sl:
                new_sl = potential_sl
                sl_updated = True
                
        pos['current_sl'] = new_sl
        
        # Module B: PVSRA Climax
        # Need V_ma and Spread_ma
        vol = historical_df['volume']
        spread = historical_df['high'] - historical_df['low']
        v_ma = vol.rolling(20).mean().iloc[-1]
        spread_ma = spread.rolling(20).mean().iloc[-1]
        
        is_climax = False
        if current_row['volume'] > 2 * v_ma and (current_row['high'] - current_row['low']) > 1.5 * spread_ma:
            if direction == "BUY" and current_row['close'] > current_row['open']: # Buying Climax
                 pass # Buying into trend is ok? Or exhaustion?
                 # Assuming Climax against trade -> Reversal signal
            elif direction == "BUY" and current_row['close'] < current_row['open']:
                 is_climax = True # Bearish Climax
            elif direction == "SELL" and current_row['close'] > current_row['open']:
                 is_climax = True # Bullish Climax in downtrend
                 
        # 3. Weighted Exit Matrix
        exit_score = 0
        reasons = []
        
        # Point 1: PVSRA (5 pts)
        if is_climax:
            exit_score += 5
            reasons.append("PVSRA Climax")
            
        # Point 2: SMC CHoCH (4 pts)
        # Check if price broke last structural pivot OPPOSITE to trade
        # Simplified: Check if price crossed below Moving Average or Pivot
        # Let's use Pivot Break from context if available, else simple MA break
        if direction == "BUY" and current_price < historical_df['close'].rolling(20).mean().iloc[-1]:
             # Weak proxy for CHoCH
             # Better: Use ctx['structure']?
             pass 
        elif direction == "BUY" and ctx.get('direction') == "DOWN":
             # Signals flipped structure
             exit_score += 4
             reasons.append("Structure Break")
             
        # Point 3: RSI Hook (3 pts)
        rsi = ctx.get('rsi', 50)
        slope = ctx.get('slope', 0)
        if direction == "BUY" and rsi > 70 and slope < -2:
            exit_score += 3
            reasons.append("RSI Hook")
        elif direction == "SELL" and rsi < 30 and slope > 2:
            exit_score += 3
            reasons.append("RSI Hook")
            
        # Point 4: Macro Decay (2 pts)
        # Need previous S15... simplified: if current S15 < 40 or dropped?
        if direction == "BUY" and s15_score < 40:
             exit_score += 2
             reasons.append("Macro Decay")
        elif direction == "SELL" and s15_score > 60:
             exit_score += 2
             reasons.append("Macro Decay")
             
        # Point 5: Signal Flip (5 pts)
        if g_score < 30:
            exit_score += 5
            reasons.append("Signal Flip")
            
        # EXECUTION
        updates = {}
        if sl_updated:
            updates['sl'] = new_sl
            updates['status'] = f"Adjusted (G={g_score:.0f}, K={k})"
            
        if exit_score >= 7:
            updates['exit'] = True
            updates['status'] = f"HARD EXIT (Score {exit_score}: {','.join(reasons)})"
        elif exit_score >= 4:
            # Partial Exit simulated by tightening SL to Price (Force BE+)
            updates['sl'] = current_price
            updates['status'] = f"PARTIAL EXIT/TIGHTEN (Score {exit_score})"
            pos['current_sl'] = current_price
            
        return updates
