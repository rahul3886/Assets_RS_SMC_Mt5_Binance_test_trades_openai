import pandas as pd
import numpy as np

def calculate_atr(df, period=14):
    """Calculate Average True Range."""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

def detect_pivots(df, length=10):
    """Detect pivot highs and lows (swing points)."""
    df = df.copy()
    df['pivot_h'] = df['high'].rolling(window=length*2+1, center=True).apply(lambda x: x[length] == max(x), raw=True)
    df['pivot_l'] = df['low'].rolling(window=length*2+1, center=True).apply(lambda x: x[length] == min(x), raw=True)
    return df

def get_smc_metrics(df):
    """
    Extracts SMC metrics: S/D Zones, FVGs, and PVSRA Liquidity.
    Returns a dictionary of current market structure.
    """
    if len(df) < 50:
        return {}

    # 1. PVSRA (Liquidity) - Premium high-volume detection
    avg_vol = df['volume'].rolling(10).mean().iloc[-1]
    curr_vol = df['volume'].iloc[-1]
    val2 = df['volume'] * (df['high'] - df['low'])
    highest_val2 = val2.rolling(10).max().iloc[-1]
    curr_val2 = val2.iloc[-1]

    is_vector_200 = curr_vol >= avg_vol * 2.0 or curr_val2 >= highest_val2
    is_vector_150 = curr_vol >= avg_vol * 1.5 and not is_vector_200
    
    liquidity_status = "NORMAL"
    if is_vector_200:
        liquidity_status = "EXTREME (200%)"
    elif is_vector_150:
        liquidity_status = "HIGH (150%)"

    # 2. Fair Value Gaps (FVG) - Enhanced with Quality Scoring
    fvg_bull = []
    fvg_bear = []
    
    # Check last 30 candles for unmitigated FVGs (Extended Lookback)
    for i in range(-30, -1):
        # Bearish FVG (Gap Down)
        if df['high'].iloc[i] < df['low'].iloc[i-2]:
            top = df['low'].iloc[i-2]
            bottom = df['high'].iloc[i]
            ce = (top + bottom) / 2
            
            # Mitigation Check: Only ACTIVE if current price is BELOW top
            if df['close'].iloc[-1] < top:
                # QUALITY SCORING
                quality = 0
                gap_pct = abs(top - bottom) / bottom * 100
                
                # A. Magnitude (Max 30 pts)
                quality += min(30, int(gap_pct * 50)) # 0.6% gap = 30 pts
                
                # B. Volume Confirmation (Max 30 pts)
                gap_candle_vol = df['volume'].iloc[i-1] # The candle forming the gap
                gap_candle_avg = df['volume'].rolling(10).mean().iloc[i-1]
                if gap_candle_vol > gap_candle_avg * 1.5:
                    quality += 30
                
                # C. Institutional Vector (Max 40 pts) - PVSRA vector candle confirmation
                # Check if gap candle was a vector candle
                is_gap_vector = gap_candle_vol >= gap_candle_avg * 2.0
                if is_gap_vector:
                    quality += 40
                
                fvg_bear.append({
                    "top": top, 
                    "bottom": bottom, 
                    "ce": ce, 
                    "status": "ACTIVE",
                    "quality": quality,
                    "size_pct": round(gap_pct, 4)
                })
        
        # Bullish FVG (Gap Up)
        if df['low'].iloc[i] > df['high'].iloc[i-2]:
            top = df['low'].iloc[i]
            bottom = df['high'].iloc[i-2]
            ce = (top + bottom) / 2
            
            # Mitigation Check: Only ACTIVE if current price is ABOVE bottom
            if df['close'].iloc[-1] > bottom:
                # QUALITY SCORING
                quality = 0
                gap_pct = abs(top - bottom) / bottom * 100
                
                # A. Magnitude (Max 30 pts)
                quality += min(30, int(gap_pct * 50))
                
                # B. Volume Confirmation (Max 30 pts)
                gap_candle_vol = df['volume'].iloc[i-1]
                gap_candle_avg = df['volume'].rolling(10).mean().iloc[i-1]
                if gap_candle_vol > gap_candle_avg * 1.5:
                    quality += 30
                
                # C. Institutional Vector (Max 40 pts)
                is_gap_vector = gap_candle_vol >= gap_candle_avg * 2.0
                if is_gap_vector:
                    quality += 40
                    
                fvg_bull.append({
                    "top": top, 
                    "bottom": bottom, 
                    "ce": ce, 
                    "status": "ACTIVE",
                    "quality": quality,
                    "size_pct": round(gap_pct, 4)
                })

    # 3. Supply & Demand (Pivot-based)
    df_pivots = detect_pivots(df, length=10)
    atr = calculate_atr(df).iloc[-1]
    box_width = atr * 0.25 # Equivalent to PineScript box_width 2.5/10
    
    zones = {"supply": [], "demand": []}
    
    # Find last 3 pivot points for zones
    recent_pivots_h = df_pivots[df_pivots['pivot_h'] == 1].tail(3)
    recent_pivots_l = df_pivots[df_pivots['pivot_l'] == 1].tail(3)
    
    for _, row in recent_pivots_h.iterrows():
        top = row['high']
        bottom = top - box_width
        if df['close'].iloc[-1] < top: # Unmitigated
            zones["supply"].append({"top": top, "bottom": bottom})
            
    for _, row in recent_pivots_l.iterrows():
        bottom = row['low']
        top = bottom + box_width
        if df['close'].iloc[-1] > bottom: # Unmitigated
            zones["demand"].append({"top": top, "bottom": bottom})

    # 4. Liquidity Magnets (SSL/BSL - Equal Highs/Lows)
    # 4. Liquidity Magnets (SSL/BSL - Equal Highs/Lows)
    # SSL: Cluster of lows within ATR threshold
    # Capture values AND timestamps
    pivots_l_series = df_pivots[df_pivots['pivot_l'] == 1]['low'].tail(15) 
    ssl_magnets = []
    current_price = df['close'].iloc[-1]
    
    if len(pivots_l_series) >= 2:
        threshold = atr * 0.15
        values = pivots_l_series.values
        indices = pivots_l_series.index
        # ROBUST TIMESTAMP EXTRACTION
        if 'timestamp' in df.columns:
            times = df['timestamp'].loc[indices].values
        else:
            times = df.index[indices]
            
        for i in range(len(values)):
            cluster = [values[i]]
            cluster_times = [times[i]]
            for j in range(i + 1, len(values)):
                if abs(values[i] - values[j]) < threshold:
                    cluster.append(values[j])
                    cluster_times.append(times[j])
            
            if len(cluster) >= 2:
                level = np.mean(cluster)
                if current_price > level:
                    dist = abs(current_price - level) / current_price
                    if dist < 0.08:
                        # Institutional Pool: 3+ touches
                        is_pool = len(cluster) >= 3
                        magnet_data = {
                            "level": level, 
                            "time": pd.Timestamp(cluster_times[-1]),
                            "touches": len(cluster),
                            "is_pool": is_pool
                        }
                        if not any(abs(m['level'] - level) < 1e-4 for m in ssl_magnets):
                            ssl_magnets.append(magnet_data)

    # BSL: Cluster of highs within ATR threshold
    pivots_h_series = df_pivots[df_pivots['pivot_h'] == 1]['high'].tail(15)
    bsl_magnets = []
    
    if len(pivots_h_series) >= 2:
        threshold = atr * 0.15
        values = pivots_h_series.values
        indices = pivots_h_series.index
        if 'timestamp' in df.columns:
            times = df['timestamp'].loc[indices].values
        else:
            times = df.index[indices]

        for i in range(len(values)):
            cluster = [values[i]]
            cluster_times = [times[i]]
            for j in range(i + 1, len(values)):
                if abs(values[i] - values[j]) < threshold:
                    cluster.append(values[j])
                    cluster_times.append(times[j])
            
            if len(cluster) >= 2:
                level = np.mean(cluster)
                if current_price < level:
                    if abs(current_price - level) / current_price < 0.08:
                        is_pool = len(cluster) >= 3
                        magnet_data = {
                            "level": level, 
                            "time": pd.Timestamp(cluster_times[-1]),
                            "touches": len(cluster),
                            "is_pool": is_pool
                        }
                        if not any(abs(m['level'] - level) < 1e-4 for m in bsl_magnets): 
                            bsl_magnets.append(magnet_data)

    # 5. Market Bias (Heavy/Lifting)
    # HEAVY: Lower Highs stepping into Demand
    # LIFTING: Higher Lows stepping into Supply
    bias = "NEUTRAL"
    current_price = df['close'].iloc[-1]
    
    last_two_h = df_pivots[df_pivots['pivot_h'] == 1]['high'].tail(2).tolist()
    last_two_l = df_pivots[df_pivots['pivot_l'] == 1]['low'].tail(2).tolist()
    
    in_demand = any(z['bottom'] <= current_price <= z['top'] for z in zones['demand'])
    in_supply = any(z['bottom'] <= current_price <= z['top'] for z in zones['supply'])

    if len(last_two_h) == 2 and last_two_h[1] < last_two_h[0] and in_demand:
        bias = "HEAVY (LH)"
    elif len(last_two_l) == 2 and last_two_l[1] > last_two_l[0] and in_supply:
        bias = "LIFTING (HL)"

    # 6. Stickiness & Zone Status Check
    status = check_zone_status(current_price, zones, atr)
    
    # 7. Session Context (Phase 5)
    session_ctx = get_session_context(df)
    
    return {
        "liquidity": liquidity_status,
        "fvg_bull": fvg_bull,
        "fvg_bear": fvg_bear,
        "zones": zones,
        "magnets": {"ssl": ssl_magnets, "bsl": bsl_magnets},
        "bias": bias,
        "status": status,
        "session": session_ctx
    }

def get_session_context(df):
    """
    Identifies Global Trading Sessions and verifies Accumulation (Asian Range).
    Assumes df['timestamp'] is in UTC.
    """
    if 'timestamp' not in df.columns or len(df) < 500:
        return {"session": "UNKNOWN", "is_accumulation": False, "asian_range": None}

    current_time = df['timestamp'].iloc[-1]
    current_hour = current_time.hour
    
    # 1. Identify Current Session
    session = "OTHER"
    if 0 <= current_hour < 8: session = "ASIAN"
    elif 8 <= current_hour < 12: session = "LONDON"
    elif 12 <= current_hour < 20: session = "NEW_YORK"
    
    # 2. Extract Asian Range (Accumulation Phase)
    # Get data for the most recent 00:00-08:00 window
    # Search backwards for the last Asian session completion
    today_asian_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if current_hour < 0: # If we're mid-session or earlier
        today_asian_start -= pd.Timedelta(days=1)
        
    asian_data = df[(df['timestamp'] >= today_asian_start) & (df['timestamp'] < today_asian_start + pd.Timedelta(hours=8))]
    
    if asian_data.empty:
        return {"session": session, "is_accumulation": False, "asian_range": None}
    
    asian_h = asian_data['high'].max()
    asian_l = asian_data['low'].min()
    asian_range_size = asian_h - asian_l
    
    # 3. Verify Accumulation (Is it a tight range?)
    # Compare Asian Range to ATR
    atr = calculate_atr(df).iloc[-1]
    # If range is less than 3x ATR, it's considered an accumulation range
    is_accumulation = (asian_range_size / atr) < 3.0 if atr > 0 else False
    
    return {
        "session": session,
        "current_hour": current_hour,
        "is_accumulation": is_accumulation,
        "asian_range": {"high": asian_h, "low": asian_l, "mid": (asian_h + asian_l)/2}
    }

def check_zone_status(price, zones, atr):
    """
    Determines if price is inside or near a key zone.
    Stickiness: Prioritizes 'IN' status. If 'NEAR' both, chooses the closest one.
    """
    buffer = atr * 2.0
    
    # 1. Priority: Are we INSIDE a zone?
    for z in zones['supply']:
        if z['bottom'] <= price <= z['top']:
            return "IN_SUPPLY"
    for z in zones['demand']:
        if z['bottom'] <= price <= z['top']:
            return "IN_DEMAND"
            
    # 2. Proximity: Are we NEAR a zone? (Check both and pick closest)
    min_dist_demand = float('inf')
    min_dist_supply = float('inf')
    
    for z in zones['demand']:
        if price > z['top']:
            dist = price - z['top']
            if dist < min_dist_demand: min_dist_demand = dist
            
    for z in zones['supply']:
        if price < z['bottom']:
            dist = z['bottom'] - price
            if dist < min_dist_supply: min_dist_supply = dist
            
    # If both within buffer, pick the one we are physically closer to
    if min_dist_demand <= buffer or min_dist_supply <= buffer:
        if min_dist_demand < min_dist_supply:
            return "NEAR_DEMAND"
        else:
            return "NEAR_SUPPLY"
            
    return "NEUTRAL"
def get_smc_metrics_optimized(df, i, atr_series, pivots_h, pivots_l, pvsra_series):
    """
    High-speed SMC metrics for backtesting (Upgrade #5).
    Uses pre-calculated series to avoid O(N) rolling scans in loops.
    """
    if i < 50: return {}

    # 1. PVSRA (Liquidity) - Pre-calculated
    liquidity_status = pvsra_series.iloc[i]
    current_price = df['close'].iloc[i]
    atr = atr_series.iloc[i]

    # 2. Fair Value Gaps (FVG) - Optimized loop
    fvg_bull = []
    fvg_bear = []
    # Check last 30 candles
    for j in range(i-30, i):
        if j < 2: continue
        high_j = df['high'].iloc[j]
        low_j_2 = df['low'].iloc[j-2]
        low_j = df['low'].iloc[j]
        high_j_2 = df['high'].iloc[j-2]

        # Bearish
        if high_j < low_j_2:
            if current_price < low_j_2:
                fvg_bear.append({"top": low_j_2, "bottom": high_j, "quality": 50}) # Simplified quality for speed
        # Bullish
        if low_j > high_j_2:
            if current_price > high_j_2:
                fvg_bull.append({"top": low_j, "bottom": high_j_2, "quality": 50})

    # 3. Supply & Demand (Pre-calculated Pivots)
    zones = {"supply": [], "demand": []}
    box_width = atr * 0.25
    
    # Get recent pivots visible at index i
    visible_h = pivots_h[pivots_h.index <= i].tail(3)
    visible_l = pivots_l[pivots_l.index <= i].tail(3)

    for val in visible_h:
        if current_price < val:
            zones["supply"].append({"top": val, "bottom": val - box_width})
    for val in visible_l:
        if current_price > val:
            zones["demand"].append({"top": val + box_width, "bottom": val})

    # 4. Session Context - Pre-calculate this for speed? 
    # For now, just call it, it's relatively light.
    # But wait, we can pass it if we pre-calculate.
    session_ctx = get_session_context(df.iloc[:i+1])

    return {
        "liquidity": liquidity_status,
        "fvg_bull": fvg_bull,
        "fvg_bear": fvg_bear,
        "zones": zones,
        "magnets": {"ssl": [], "bsl": []}, # Simplified for speed boost
        "bias": "NEUTRAL",
        "status": "NEUTRAL",
        "session": session_ctx
    }

def detect_displacement(df, lookback=3):
    """
    Upgrade 8: Detects institutional displacement (rapid price rejection).
    Checks for:
    1. Large candle bodies (Displaced candles).
    2. High volume during the move.
    """
    if len(df) < lookback + 1:
        return False, 0
        
    recent = df.tail(lookback)
    
    # 1. Body Size vs ATR
    atr = calculate_atr(df).iloc[-1]
    bodies = (recent['close'] - recent['open']).abs()
    
    # Displacement = At least one candle body > 1.2x ATR
    is_displaced = any(bodies > atr * 1.2)
    
    # 2. Volume Check
    avg_vol = df['volume'].rolling(10).mean().iloc[-1]
    is_high_vol = any(recent['volume'] > avg_vol * 1.5)
    
    # Scoring
    score = 0
    if is_displaced: score += 50
    if is_high_vol: score += 50
    
    return score >= 50, score
