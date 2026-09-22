import pandas as pd
import numpy as np
import smc_logic

def calculate_rsi(df, length=14):
    """Calculates RSI using vanilla pandas/numpy with Wilders smoothing."""
    # Optimization: Skip if already calculated
    if 'RSI' in df.columns and 'RSI_EMA' in df.columns:
        return df

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    avg_gain = gain.rolling(window=length, min_periods=length).mean()
    avg_loss = loss.rolling(window=length, min_periods=length).mean()

    # Wilders smoothing
    avg_gain_vals = avg_gain.values.copy()
    avg_loss_vals = avg_loss.values.copy()
    gain_vals = gain.values
    loss_vals = loss.values

    for i in range(length, len(df)):
        if not np.isnan(avg_gain_vals[i-1]):
            avg_gain_vals[i] = (avg_gain_vals[i-1] * (length - 1) + gain_vals[i]) / length
            avg_loss_vals[i] = (avg_loss_vals[i-1] * (length - 1) + loss_vals[i]) / length

    df = df.copy() # Avoid SettingWithCopy warning if slice
    df['avg_gain'] = avg_gain_vals
    df['avg_loss'] = avg_loss_vals
    
    rs = df['avg_gain'] / df['avg_loss']
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # RSI EMA (Signal Line)
    df['RSI_EMA'] = df['RSI'].ewm(span=length, adjust=False).mean()
    
    return df

def calculate_ema(series, length):
    """Calculates EMA."""
    return series.ewm(span=length, adjust=False).mean()

def get_rsi_slope(df, lookback=3):
    """Calculates the velocity/slope of RSI."""
    if len(df) < lookback:
        return 0
    rsi_change = df['RSI'].iloc[-1] - df['RSI'].iloc[-lookback]
    return round(rsi_change, 2)

def find_pivots(series, left_bars=2, right_bars=2, min_swing=None):
    """
    Standard Pivot Detection (Phase 2 Baseline).
    Detects peaks and valleys with optional minimum swing filter.
    Returns list of (index, value, type) tuples.
    """
    pivots = []
    
    for i in range(left_bars, len(series) - right_bars):
        val = series.iloc[i]
        is_peak = True
        is_valley = True
        
        # Check surrounding bars
        max_depth_peak = 0
        max_depth_valley = 0
        
        for j in range(1, left_bars + 1):
            if series.iloc[i-j] >= val: is_peak = False
            if series.iloc[i-j] <= val: is_valley = False
            max_depth_peak = max(max_depth_peak, val - series.iloc[i-j])
            max_depth_valley = max(max_depth_valley, series.iloc[i-j] - val)
            
        for j in range(1, right_bars + 1):
            if series.iloc[i+j] >= val: is_peak = False
            if series.iloc[i+j] <= val: is_valley = False
            max_depth_peak = max(max_depth_peak, val - series.iloc[i+j])
            max_depth_valley = max(max_depth_valley, series.iloc[i+j] - val)
        
        if is_peak:
            depth = max_depth_peak
            if min_swing is None or depth >= min_swing:
                pivots.append((i, val, "peak"))
        if is_valley:
            depth = max_depth_valley
            if min_swing is None or depth >= min_swing:
                pivots.append((i, val, "valley"))

    return pivots

# REMOVED: get_adaptive_pivot_params (Phase 3 feature)

def detect_structure(pivots):
    """
    Identifies HH, HL, LL, LH in RSI.
    Phase 2 Baseline (No significance filter).
    """
    if len(pivots) < 2:
        return "Unknown"
    
    # Phase 2: Use all pivots found
    peaks = [p for p in pivots if p[2] == "peak"]
    valleys = [p for p in pivots if p[2] == "valley"]
    
    structure = []
    if len(peaks) >= 2:
        if peaks[-1][1] > peaks[-2][1]: structure.append("HH")
        else: structure.append("LH")
        
    if len(valleys) >= 2:
        if valleys[-1][1] > valleys[-2][1]: structure.append("HL")
        else: structure.append("LL")
        
    return structure

def check_divergence(df, pivots):
    """
    Detects regular Bullish and Bearish Divergence.
    Phase 2 Baseline (No significance filter).
    """
    if len(pivots) < 2: return None
    
    # Phase 2: Use all pivots
    peaks = [p for p in pivots if p[2] == "peak"]
    valleys = [p for p in pivots if p[2] == "valley"]
    
    # Bullish Divergence: Price LL, RSI HL
    if len(valleys) >= 2:
        v1, v2 = valleys[-2], valleys[-1]
        if v1[0] < len(df) and v2[0] < len(df):
            price_v1 = df['low'].iloc[v1[0]]
            price_v2 = df['low'].iloc[v2[0]]
            
            if price_v2 < price_v1 and v2[1] > v1[1]:
                return "Bullish Divergence"
            
    # Bearish Divergence: Price HH, RSI LH
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if p1[0] < len(df) and p2[0] < len(df):
            price_p1 = df['high'].iloc[p1[0]]
            price_p2 = df['high'].iloc[p2[0]]
            
            if price_p2 > price_p1 and p2[1] < p1[1]:
                return "Bearish Divergence"
            
    return None

def find_rsi_structural_levels(df, lookback=150):
    """
    Identifies horizontal RSI support/resistance levels based on pivot clusters.
    Returns a list of significant RSI levels.
    """
    if len(df) < lookback:
        df_slice = df
    else:
        df_slice = df.tail(lookback)
        
    pivots = find_pivots(df_slice['RSI'], 2, 2)
    pivot_values = [p[1] for p in pivots]
    
    if not pivot_values:
        return [30, 40, 50, 60, 70] # Default fallback levels
        
    # Group levels within 2.5 RSI points
    levels = []
    threshold = 2.5
    
    for val in pivot_values:
        added = False
        for i, cluster in enumerate(levels):
            # If value is close to an existing cluster average
            if abs(val - np.mean(cluster)) < threshold:
                levels[i].append(val)
                added = True
                break
        if not added:
            levels.append([val])
            
    # Calculate average of each cluster and sort by 'strength' (number of hits)
    significant_levels = []
    for cluster in levels:
        if len(cluster) >= 1:
            significant_levels.append(round(float(np.mean(cluster)), 1))
            
    return sorted(significant_levels)

def get_dynamic_rsi_target(df, signal):
    """
    Finds the best RSI structural level to act as a Take Profit target.
    """
    curr_rsi = df['RSI'].iloc[-1]
    levels = find_rsi_structural_levels(df)
    
    if signal == "BUY":
        # Target Resistance: Significant levels ABOVE current RSI
        targets = [l for l in levels if l > curr_rsi + 5]
        return min(targets) if targets else 60.0 # Default TP for Buy
    elif signal == "SELL":
        # Target Support: Significant levels BELOW current RSI
        targets = [l for l in levels if l < curr_rsi - 5]
        return max(targets) if targets else 40.0 # Default TP for Sell
    
    return None

def calculate_structural_sl(df, signal, ctx):
    """
    Calculates a PURE structural Stop Loss based on Market Geometry.
    Sets SL exactly at the DISTAL EDGE of the originating SMC zone.
    No ATR buffer is added, ensuring the trade is invalidated if structure breaks.
    """
    current_price = df['close'].iloc[-1]
    
    smc = ctx.get('smc', {})
    zones = smc.get('zones', {})
    magnets = smc.get('magnets', {})
    
    if signal == "BUY":
        # Base Level: Nearest Demand Bottom (Distal Edge) or SSL Level below price
        levels = [z['bottom'] for z in zones.get('demand', []) if z['bottom'] < current_price]
        levels += [m['level'] for m in magnets.get('ssl', []) if m['level'] < current_price]
        
        if levels:
            base_sl = min(levels) # Deepest structural support (Hard Boundary)
            return round(base_sl, 5)
        else:
            # Fallback: Recent Swing Low (Hard Bottom)
            recent_low = df['low'].tail(20).min()
            return round(recent_low, 5)
            
    elif signal == "SELL":
        # Base Level: Nearest Supply Top (Distal Edge) or BSL Level above price
        levels = [z['top'] for z in zones.get('supply', []) if z['top'] > current_price]
        levels += [m['level'] for m in magnets.get('bsl', []) if m['level'] > current_price]
        
        if levels:
            base_sl = max(levels) # Highest structural resistance (Hard Boundary)
            return round(base_sl, 5)
        else:
            # Fallback: Recent Swing High (Hard Top)
            recent_high = df['high'].tail(20).max()
            return round(recent_high, 5)
            
    return None

def calculate_volume_metrics(df, period=20):
    """
    Calculates institutional order flow metrics (Scalar version for real-time/last candle).
    """
    if len(df) < period:
        return {"delta": 0, "is_climax": False, "is_absorption": False, "vol_ratio": 1.0}

    # ... (Keep existing scalar implementation for reference or compatibility)
    # Using the optimized scalar version we made earlier:
    
    # 1. Volume Delta Approximation
    df_vol = df.tail(period).copy()
    mid_price = (df_vol['high'] + df_vol['low']) / 2
    # Vectorized within the small extraction
    buy_vol = df_vol[df_vol['close'] > mid_price]['volume'].sum()
    sell_vol = df_vol[df_vol['close'] <= mid_price]['volume'].sum()
    
    total_vol = buy_vol + sell_vol
    delta_pct = ((buy_vol - sell_vol) / total_vol * 100) if total_vol > 0 else 0
    
    # 2. Relative Volume & Climax
    avg_vol = df_vol['volume'].mean()
    curr_vol = df_vol['volume'].iloc[-1]
    vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
    is_climax = vol_ratio > 2.0
    
    # 3. Absorption
    avg_range = (df_vol['high'] - df_vol['low']).mean()
    curr_range = df_vol['high'].iloc[-1] - df_vol['low'].iloc[-1]
    is_absorption = (vol_ratio > 1.5) and (curr_range < avg_range * 0.5) if avg_range > 0 else False
    
    return {
        "delta": round(delta_pct, 2),
        "is_climax": is_climax,
        "is_absorption": is_absorption,
        "vol_ratio": round(vol_ratio, 2)
    }

def calculate_volume_metrics_vectorized(df, period=20):
    """
    Calculates institutional order flow metrics as Series (Vectorized for Backtesting).
    """
    # 1. Volume Delta (Approximation per candle)
    # If Close > (High+Low)/2 => Buy Vol, else Sell Vol
    mid = (df['high'] + df['low']) / 2
    
    # This is per-candle classification. To get 'Delta' over a period, we need rolling sum.
    # Let's define candle delta: +Vol if Green, -Vol if Red (simplified for vectorization speed)
    # Or strict: +Vol if Close > Mid, -Vol else
    
    is_buy = df['close'] > mid
    vol_signed = df['volume'].where(is_buy, -df['volume'])
    
    # Net Buy-Sell Volume over period
    net_vol = vol_signed.rolling(period).sum()
    total_vol = df['volume'].rolling(period).sum()
    
    df['vol_delta_pct'] = (net_vol / total_vol * 100).fillna(0)
    
    # 2. Relative Volume
    avg_vol = df['volume'].rolling(period).mean()
    df['vol_ratio'] = (df['volume'] / avg_vol).fillna(0)
    df['is_climax'] = df['vol_ratio'] > 2.0
    
    # 3. Absorption
    # High vol, Low range
    high_low_range = df['high'] - df['low']
    avg_range = high_low_range.rolling(period).mean()
    
    df['is_absorption'] = (df['vol_ratio'] > 1.5) & (high_low_range < avg_range * 0.5)
    
    return df



    return df, all_pivots, (2, 2)

def prepare_data(df):
    """
    Pre-calculates all indicators for optimized backtesting (Phase 2).
    Returns df (with indicators) and all_pivots list.
    """
    # 1. RSI
    df = calculate_rsi(df)
    
    # 2. Vectorized Volume
    df = calculate_volume_metrics_vectorized(df)
    
    # 3. Pivots (find all) - Phase 2 Fixed Parameters
    left_b = 2
    right_b = 2
    min_sw = 0 
    raw_pivots = find_pivots(df['RSI'], left_bars=left_b, right_bars=right_b, min_swing=min_sw)
    
    # 4. SMC Optimized Components (SMC Upgrade #5)
    df['atr'] = smc_logic.calculate_atr(df)
    
    # PVSRA Series (pre-calculate status for speed)
    avg_vol = df['volume'].rolling(10).mean()
    val2 = df['volume'] * (df['high'] - df['low'])
    highest_val2 = val2.rolling(10).max()
    
    df['pvsra'] = "NORMAL"
    df.loc[df['volume'] >= avg_vol * 2.0, 'pvsra'] = "EXTREME (200%)"
    df.loc[(df['volume'] >= avg_vol * 1.5) & (df['pvsra'] != "EXTREME (200%)"), 'pvsra'] = "HIGH (150%)"

    # 5. Extract Pivot Prices for S/D Zones
    df_smc_pivots = smc_logic.detect_pivots(df, length=10)
    pivots_h = df_smc_pivots[df_smc_pivots['pivot_h'] == 1]['high']
    pivots_l = df_smc_pivots[df_smc_pivots['pivot_l'] == 1]['low']
    
    return df, raw_pivots, (left_b, right_b), pivots_h, pivots_l

def check_signals_optimized(df, i, all_pivots, pivot_params, pivots_h=None, pivots_l=None):
    """
    Optimized signal check for backtesting.
    Uses pre-calculated columns and filtered pivot list.
    """
    # Create a minimal context for scoring
    row = df.iloc[i]
    if i < 50: return "NEUTRAL", {}, {}
    
    current_price = row['close']
    current_rsi = row['RSI']
    previous_rsi = df['RSI'].iloc[i-1]
    rsi_ema = row['RSI_EMA']
    slope = 0 if i < 3 else round(df['RSI'].iloc[i] - df['RSI'].iloc[i-3], 2)
    
    # Volume Metrics (from columns)
    delta = row.get('vol_delta_pct', 0)
    is_climax = row.get('is_climax', False)
    is_absorption = row.get('is_absorption', False)
    
    # Filter pivots visible at time i
    left_b, right_b = pivot_params
    visible_pivots = [p for p in all_pivots if p[0] <= i - right_b]
    
    structure = detect_structure(visible_pivots)
    divergence = _check_divergence_internal(df, visible_pivots) 
    
    # SMC Optimized Lookup (Upgrade #5)
    # uses cached ATR and PVSRA from rows
    smc = smc_logic.get_smc_metrics_optimized(
        df, i, df['atr'], pivots_h, pivots_l, df['pvsra']
    )
    
    # --- Upgrade 8: Enhanced Hunting (Displacement) ---
    is_displaced, displacement_score = smc_logic.detect_displacement(df.iloc[i-10:i+1])
    
    # Construct Context
    ctx = {
        "rsi": round(current_rsi, 2),
        "rsi_ema": round(rsi_ema, 2),
        "slope": slope,
        "structure": structure,
        "divergence": divergence,
        "direction": "UP" if current_rsi > rsi_ema else "DOWN",
        "smc": smc,
        "volume": { 
            "delta": round(delta, 2),
            "is_climax": is_climax,
            "is_absorption": is_absorption
        }
    }
    
    # --- SCORING LOGIC (Mirrors check_signals_advanced) ---
    oversold, overbought = 30, 70
    
    # BUY Conditions
    rsi_cross_up = current_rsi > oversold and previous_rsi <= oversold
    rsi_oversold = current_rsi <= oversold + 5
    demand_zones = smc.get('zones', {}).get('demand', [])
    in_demand = any(z['bottom'] <= current_price <= z['top'] for z in demand_zones)
    
    ssl_magnets = smc.get('magnets', {}).get('ssl', [])
    sweep_ssl = any(current_price <= m['level'] for m in ssl_magnets)
    is_ssl_pool = any(current_price <= m['level'] and m.get('is_pool') for m in ssl_magnets)
    
    bull_div = ctx['divergence'] == "Bullish Divergence"
    bull_momentum = ctx['direction'] == "UP" and ctx['slope'] > 0
    near_bull_fvg = any(f['bottom'] <= current_price <= f['top'] for f in smc.get('fvg_bull', []))

    # SELL Conditions
    rsi_cross_down = current_rsi < overbought and previous_rsi >= overbought
    rsi_overbought = current_rsi >= overbought - 5
    supply_zones = smc.get('zones', {}).get('supply', [])
    in_supply = any(z['bottom'] <= current_price <= z['top'] for z in supply_zones)
    
    bsl_magnets = smc.get('magnets', {}).get('bsl', [])
    sweep_bsl = any(current_price >= m['level'] for m in bsl_magnets)
    is_bsl_pool = any(current_price >= m['level'] and m.get('is_pool') for m in bsl_magnets)
    
    bear_div = ctx['divergence'] == "Bearish Divergence"
    bear_momentum = ctx['direction'] == "DOWN" and ctx['slope'] < 0
    near_bear_fvg = any(f['bottom'] <= current_price <= f['top'] for f in smc.get('fvg_bear', []))

    # Weighted Scoring
    buy_scores = {}
    sell_scores = {}

    # BUY scoring
    if in_demand: buy_scores["Demand Zone"] = 25
    if rsi_cross_up: buy_scores["RSI Cross Up"] = 25
    elif rsi_oversold: buy_scores["RSI Oversold"] = 15
    if bull_div: buy_scores["Bullish Divergence"] = 10 
    if sweep_ssl: buy_scores["Liquidity Sweep (SSL)"] = 20
    # FVG Check (Enhanced Phase 4)
    bull_fvg_list = smc.get('fvg_bull', [])
    near_bull_fvg = any(f['bottom'] <= current_price <= f['top'] for f in bull_fvg_list)
    premium_bull_fvg = any(f['bottom'] <= current_price <= f['top'] and f.get('quality', 0) >= 70 for f in bull_fvg_list)
    
    if premium_bull_fvg: buy_scores["Premium FVG Support"] = 20
    elif near_bull_fvg: buy_scores["FVG Support"] = 15
    
    if bull_momentum: buy_scores["Bull Momentum"] = 15
    
    # Volume Bonus
    if delta > 10: buy_scores["Order Flow (+)"] = 15
    if is_climax and (rsi_oversold or in_demand or sweep_ssl): buy_scores["Vol Climax (+)"] = 15
    if is_absorption and in_demand: buy_scores["Absorption (+)"] = 15
    
    # Upgrade 8: Liquidity Pool & Displacement BONUS
    if is_ssl_pool: buy_scores["Liquidity Pool Sweep (High Value)"] = 25
    if displacement_score > 0 and (sweep_ssl or in_demand):
        buy_scores["Institutional Displacement (+)"] = displacement_score // 2

    # SELL scoring
    if in_supply: sell_scores["Supply Zone"] = 25
    if rsi_cross_down: sell_scores["RSI Cross Down"] = 25
    elif rsi_overbought: sell_scores["RSI Overbought"] = 15
    if bear_div: sell_scores["Bearish Divergence"] = 10
    if sweep_bsl: sell_scores["Liquidity Sweep (BSL)"] = 20
    # FVG Check (Enhanced Phase 4)
    bear_fvg_list = smc.get('fvg_bear', [])
    near_bear_fvg = any(f['bottom'] <= current_price <= f['top'] for f in bear_fvg_list)
    premium_bear_fvg = any(f['bottom'] <= current_price <= f['top'] and f.get('quality', 0) >= 70 for f in bear_fvg_list)
    
    if premium_bear_fvg: sell_scores["Premium FVG Resistance"] = 20
    elif near_bear_fvg: sell_scores["FVG Resistance"] = 15
    
    if bear_momentum: sell_scores["Bear Momentum"] = 15

    # Volume Bonus
    if delta < -10: sell_scores["Order Flow (-)"] = 15
    if is_climax and (rsi_overbought or in_supply or sweep_bsl): sell_scores["Vol Climax (-)"] = 15
    if is_absorption and in_supply: sell_scores["Absorption (-)"] = 15
    
    # Upgrade 8: Liquidity Pool & Displacement BONUS
    if is_bsl_pool: sell_scores["Liquidity Pool Sweep (High Value)"] = 25
    if displacement_score > 0 and (sweep_bsl or in_supply):
        sell_scores["Institutional Displacement (-)"] = displacement_score // 2

    # --- Phase 5: Dynamic Session & AMD Scoring ---
    session_ctx = smc.get('session', {})
    session_name = session_ctx.get('session', 'UNKNOWN')
    is_accum = session_ctx.get('is_accumulation', False)
    asian_range = session_ctx.get('asian_range')
    
    # 1. Asian Range Sweep (Manipulation)
    if session_name == "LONDON" and is_accum and asian_range:
        asian_h = asian_range['high']
        asian_l = asian_range['low']
        
        # BUY: Sweep below Asian Low
        if current_price <= asian_l:
            buy_scores["Asian Low Sweep"] = 25
        # SELL: Sweep above Asian High
        if current_price >= asian_h:
            sell_scores["Asian High Sweep"] = 25
            
    # 2. Asian Noisy Filter (Penalize ranging inside)
    if session_name == "ASIAN" and asian_range:
        if asian_range['low'] < current_price < asian_range['high']:
            buy_scores["Asian Range Noise"] = -15
            sell_scores["Asian Range Noise"] = -15
            
    # 3. New York Expansion Bonus
    if session_name == "NEW_YORK":
        if bull_momentum: buy_scores["NY Expansion"] = 15
        if bear_momentum: sell_scores["NY Expansion"] = 15

    # Decision Logic
    buy_total = sum(buy_scores.values())
    sell_total = sum(sell_scores.values())
    
    final_signal = "NEUTRAL"
    total_strength = 0
    active_scores = {}
    
    major_buy = in_demand or rsi_cross_up or sweep_ssl or bull_div
    major_sell = in_supply or rsi_cross_down or sweep_bsl or bear_div

    if buy_total >= sell_total and buy_total >= 50 and major_buy:
        final_signal = "BUY"
        total_strength = buy_total
        active_scores = buy_scores
    elif sell_total > buy_total and sell_total >= 50 and major_sell:
        final_signal = "SELL"
        total_strength = sell_total
        active_scores = sell_scores
    else:
        # Check for Hunting override even if major trigger didn't hit 50%
        # Upgrade 8 FIX: Hunting REQUIREMENT = Sweep + Displacement
        if current_rsi < 25 and sweep_ssl and is_displaced:
            final_signal = "HUNTING_BUY"
            total_strength = max(buy_total, 45)
            active_scores = buy_scores
        elif current_rsi > 75 and sweep_bsl and is_displaced:
            final_signal = "HUNTING_SELL"
            total_strength = max(sell_total, 45)
            active_scores = sell_scores

    strength_info = {
        "strength": total_strength,
        "score": f"{min(total_strength, 100)}%",
        "breakdown": active_scores,
        "tp_rsi": None, 
        "sl_price": calculate_structural_sl(df.iloc[:i+1], final_signal, ctx), 
        "is_hunting": "HUNTING" in final_signal
    }
    
    # RSI TP target
    if final_signal != "NEUTRAL":
         strength_info['tp_rsi'] = get_dynamic_rsi_target(df.iloc[:i+1], final_signal)

    return final_signal, strength_info, ctx

def _check_divergence_internal(df, pivots):
    """Internal helper for divergence using pivots list (Phase 2 logic)."""
    if len(pivots) < 2: return None
    
    peaks = [p for p in pivots if p[2] == "peak"]
    valleys = [p for p in pivots if p[2] == "valley"]
    
    if len(valleys) >= 2:
        v1, v2 = valleys[-2], valleys[-1]
        price_v1 = df['low'].iloc[v1[0]]
        price_v2 = df['low'].iloc[v2[0]]
        if price_v2 < price_v1 and v2[1] > v1[1]: return "Bullish Divergence"
            
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        price_p1 = df['high'].iloc[p1[0]]
        price_p2 = df['high'].iloc[p2[0]]
        if price_p2 > price_p1 and p2[1] < p1[1]: return "Bearish Divergence"
            
    return None

def get_signal_context(df):
    """Compiles all advanced data for a timeframe including SMC."""
    df = calculate_rsi(df)
    
    # Phase 2 Fixed Parameters (Restored)
    left_b, right_b = 2, 2
    pivots = find_pivots(df['RSI'], left_bars=left_b, right_bars=right_b, min_swing=0)
    
    structure = detect_structure(pivots)
    divergence = check_divergence(df, pivots)
    slope = get_rsi_slope(df)
    
    curr_rsi = df['RSI'].iloc[-1]
    rsi_ema = df['RSI_EMA'].iloc[-1]
    
    # SMC Metrics Extraction
    smc = smc_logic.get_smc_metrics(df)
    
    # Volume Metrics Extraction (Upgrade #2)
    volume = calculate_volume_metrics(df)
    
    # RSI structural levels
    rsi_levels = find_rsi_structural_levels(df)
    
    return {
        "rsi": round(curr_rsi, 2),
        "rsi_ema": round(rsi_ema, 2),
        "slope": slope,
        "structure": structure,
        "divergence": divergence,
        "direction": "UP" if curr_rsi > rsi_ema else "DOWN",
        "smc": smc,
        "volume": volume,
        "rsi_levels": rsi_levels
    }

def check_signals_advanced(df, mtf_contexts=None, oversold=30, overbought=70):
    """
    Multi-Condition Entry System (Upgrade Phase 1).
    Decouples entry from strict RSI crossovers.
    Uses weighted confluence: SMC Zones, RSI Extremes, Liquidity, FVG, Momentum.
    MTF Upgrade: Incorporates weighted conviction from higher timeframes.
    """
    ctx = get_signal_context(df)
    current_rsi = ctx['rsi']
    current_price = df['close'].iloc[-1]
    previous_rsi = df['RSI'].iloc[-2] if len(df) > 1 else current_rsi
    
    smc = ctx.get('smc', {})
    smc_status = smc.get('status', 'NEUTRAL')
    
    # --- Upgrade 8: Enhanced Hunting (Displacement) ---
    is_displaced, displacement_score = smc_logic.detect_displacement(df)
    
    # Volume - Order Flow BONUS (Upgrade #2)
    vol = ctx.get('volume', {})
    delta = vol.get('delta', 0)
    is_climax = vol.get('is_climax', False)
    is_absorption = vol.get('is_absorption', False)

    # 1. Define Primary Conditions (Boolean Triggers)
    # --- BUY Conditions ---
    rsi_cross_up = current_rsi > oversold and previous_rsi <= oversold
    rsi_oversold = current_rsi <= oversold + 5 # Extra buffer
    demand_zones = smc.get('zones', {}).get('demand', [])
    in_demand = any(z['bottom'] <= current_price <= z['top'] for z in demand_zones)
    
    ssl_magnets = smc.get('magnets', {}).get('ssl', [])
    sweep_ssl = any(current_price <= m['level'] for m in ssl_magnets)
    is_ssl_pool = any(current_price <= m['level'] and m.get('is_pool') for m in ssl_magnets)
    
    bull_div = ctx['divergence'] == "Bullish Divergence"
    bull_momentum = ctx['direction'] == "UP" and ctx['slope'] > 0
    near_bull_fvg = any(f['bottom'] <= current_price <= f['top'] for f in smc.get('fvg_bull', []))

    # --- SELL Conditions ---
    rsi_cross_down = current_rsi < overbought and previous_rsi >= overbought
    rsi_overbought = current_rsi >= overbought - 5
    supply_zones = smc.get('zones', {}).get('supply', [])
    in_supply = any(z['bottom'] <= current_price <= z['top'] for z in supply_zones)
    
    bsl_magnets = smc.get('magnets', {}).get('bsl', [])
    sweep_bsl = any(current_price >= m['level'] for m in bsl_magnets)
    is_bsl_pool = any(current_price >= m['level'] and m.get('is_pool') for m in bsl_magnets)
    
    bear_div = ctx['divergence'] == "Bearish Divergence"
    bear_momentum = ctx['direction'] == "DOWN" and ctx['slope'] < 0
    near_bear_fvg = any(f['bottom'] <= current_price <= f['top'] for f in smc.get('fvg_bear', []))

    # 2. Weighted Scoring (Institutional Grade)
    buy_scores = {}
    sell_scores = {}

    # BASE Weights (Same as Phase 1, total 100)
    # SMC(25), RSI(25), Magnets(20), FVG(15), Momentum(15)
    
    vol = ctx.get('volume', {})
    delta = vol.get('delta', 0)
    is_climax = vol.get('is_climax', False)
    is_absorption = vol.get('is_absorption', False)

    # BUY scoring
    if in_demand: buy_scores["Demand Zone"] = 25
    if rsi_cross_up: buy_scores["RSI Cross Up"] = 25
    elif rsi_oversold: buy_scores["RSI Oversold"] = 15
    if bull_div: buy_scores["Bullish Divergence"] = 10 
    if sweep_ssl: buy_scores["Liquidity Sweep (SSL)"] = 20
    if near_bull_fvg: buy_scores["FVG Support"] = 15
    if bull_momentum: buy_scores["Bull Momentum"] = 15
    
    # Volume - Order Flow BONUS (Upgrade #2)
    if delta > 10: buy_scores["Order Flow (+)"] = 15
    if is_climax and (rsi_oversold or in_demand or sweep_ssl): buy_scores["Vol Climax (+)"] = 15
    if is_absorption and in_demand: buy_scores["Absorption (+)"] = 15
    
    # Upgrade 8: Liquidity Pool & Displacement BONUS
    if is_ssl_pool: buy_scores["Liquidity Pool Sweep (High Value)"] = 25
    if displacement_score > 0 and (sweep_ssl or in_demand):
        buy_scores["Institutional Displacement (+)"] = displacement_score // 2

    # SELL scoring
    if in_supply: sell_scores["Supply Zone"] = 25
    if rsi_cross_down: sell_scores["RSI Cross Down"] = 25
    elif rsi_overbought: sell_scores["RSI Overbought"] = 15
    if bear_div: sell_scores["Bearish Divergence"] = 10
    if sweep_bsl: sell_scores["Liquidity Sweep (BSL)"] = 20
    
    # FVG Check (Enhanced Phase 4)
    bear_fvg_list = smc.get('fvg_bear', [])
    near_bear_fvg = any(f['bottom'] <= current_price <= f['top'] for f in bear_fvg_list)
    premium_bear_fvg = any(f['bottom'] <= current_price <= f['top'] and f.get('quality', 0) >= 70 for f in bear_fvg_list)
    
    if premium_bear_fvg: sell_scores["Premium FVG Resistance"] = 20
    elif near_bear_fvg: sell_scores["FVG Resistance"] = 15
    
    if bear_momentum: sell_scores["Bear Momentum"] = 15

    # --- Phase 5: Dynamic Session & AMD Scoring ---
    session_ctx = smc.get('session', {})
    session_name = session_ctx.get('session', 'UNKNOWN')
    is_accum = session_ctx.get('is_accumulation', False)
    asian_range = session_ctx.get('asian_range')
    
    # 1. Asian Range Sweep (Manipulation)
    if session_name == "LONDON" and is_accum and asian_range:
        asian_h = asian_range['high']
        asian_l = asian_range['low']
        
        # BUY: Sweep below Asian Low
        if current_price <= asian_l:
            buy_scores["Asian Low Sweep"] = 25
        # SELL: Sweep above Asian High
        if current_price >= asian_h:
            sell_scores["Asian High Sweep"] = 25
            
    # 2. Asian Noisy Filter (Penalize ranging inside)
    if session_name == "ASIAN" and asian_range:
        if asian_range['low'] < current_price < asian_range['high']:
            buy_scores["Asian Range Noise"] = -15
            sell_scores["Asian Range Noise"] = -15
            
    # 3. New York Expansion Bonus
    if session_name == "NEW_YORK":
        if bull_momentum: buy_scores["NY Expansion"] = 15
        if bear_momentum: sell_scores["NY Expansion"] = 15

    # Volume - Order Flow BONUS (Upgrade #2)
    if delta < -10: sell_scores["Order Flow (-)"] = 15
    if is_climax and (rsi_overbought or in_supply or sweep_bsl): sell_scores["Vol Climax (-)"] = 15
    if is_absorption and in_supply: sell_scores["Absorption (-)"] = 15
    
    # Upgrade 8: Liquidity Pool & Displacement BONUS
    if is_bsl_pool: sell_scores["Liquidity Pool Sweep (High Value)"] = 25
    if displacement_score > 0 and (sweep_bsl or in_supply):
        sell_scores["Institutional Displacement (-)"] = displacement_score // 2

    # --- Upgrade 6: Multi-Frame Confluence (Weighted) ---
    if mtf_contexts:
        mtf_conviction = calculate_mtf_conviction(mtf_contexts, ctx['direction'])
        if ctx['direction'] == "UP":
            if mtf_conviction > 0:
                buy_scores["MTF Conviction (+)"] = mtf_conviction
            elif mtf_conviction < 0:
                buy_scores["MTF Headwind (-)"] = mtf_conviction
        elif ctx['direction'] == "DOWN":
            if mtf_conviction > 0:
                sell_scores["MTF Conviction (+)"] = mtf_conviction
            elif mtf_conviction < 0:
                sell_scores["MTF Headwind (-)"] = mtf_conviction

    # 3. Decision Logic
    buy_total = sum(buy_scores.values())
    sell_total = sum(sell_scores.values())
    
    final_signal = "NEUTRAL"
    total_strength = 0
    active_scores = {}

    # Entry Criteria: 
    # Must have at least ONE major trigger (Zone, RSI Cross, or Sweep) 
    # AND total strength >= 55%
    
    major_buy = in_demand or rsi_cross_up or sweep_ssl or bull_div
    major_sell = in_supply or rsi_cross_down or sweep_bsl or bear_div

    if buy_total >= sell_total and buy_total >= 50 and major_buy:
        final_signal = "BUY"
        total_strength = buy_total
        active_scores = buy_scores
    elif sell_total > buy_total and sell_total >= 50 and major_sell:
        final_signal = "SELL"
        total_strength = sell_total
        active_scores = sell_scores
    else:
        # Check for Hunting override even if major trigger didn't hit 50%
        # Upgrade 8 FIX: Hunting REQUIREMENT = Sweep + Displacement
        if current_rsi < 25 and sweep_ssl and is_displaced:
            final_signal = "HUNTING_BUY"
            total_strength = max(buy_total, 45)
            active_scores = buy_scores
        elif current_rsi > 75 and sweep_bsl and is_displaced:
            final_signal = "HUNTING_SELL"
            total_strength = max(sell_total, 45)
            active_scores = sell_scores

    # 4. Supplemental Data
    sl_price = calculate_structural_sl(df, final_signal, ctx)
    tp_rsi = get_dynamic_rsi_target(df, final_signal) if final_signal != "NEUTRAL" else None
    
    strength_info = {
        "strength": total_strength,
        "score": f"{min(total_strength, 100)}%",
        "breakdown": active_scores,
        "tp_rsi": tp_rsi,
        "sl_price": sl_price,
        "is_hunting": "HUNTING" in final_signal
    }
    
    return final_signal, strength_info, ctx


def check_zone_alerts(df, lower_threshold=30, upper_threshold=65):
    """
    Detects if the RSI has entered an extreme zone.
    Specifically: Crossing below 30 or above 65.
    """
    if len(df) < 2:
        return None, 0
    
    current_rsi = df['RSI'].iloc[-1]
    previous_rsi = df['RSI'].iloc[-2]
    
    if pd.isna(current_rsi) or pd.isna(previous_rsi):
        return None, 0
    
    # Entered BUY Zone (Crossed below 30)
    if current_rsi < lower_threshold and previous_rsi >= lower_threshold:
        return "BUY_ZONE", current_rsi
        
    # Entered SELL Zone (Crossed above 65)
    if current_rsi > upper_threshold and previous_rsi <= upper_threshold:
        return "SELL_ZONE", current_rsi
        
    return None, 0

def get_market_situation(df):
    """Analyzes the market situation for the startup report including SMC."""
    current_price = df['close'].iloc[-1]
    df = calculate_rsi(df)
    current_rsi = df['RSI'].iloc[-1]
    
    ema_50_series = calculate_ema(df['close'], 50)
    ema_200_series = calculate_ema(df['close'], 200)
    
    ema_50 = ema_50_series.iloc[-1]
    ema_200 = ema_200_series.iloc[-1]
    
    # SMC Extra
    smc = smc_logic.get_smc_metrics(df)
    
    if ema_50 > ema_200:
        trend = "Bullish 📈"
    elif ema_50 < ema_200:
        trend = "Bearish 📉"
    else:
        trend = "Ranging ↔️"
        
    rsi_status = "Neutral"
    if not pd.isna(current_rsi):
        if current_rsi > 70:
            rsi_status = "Overbought ⚠️"
        elif current_rsi < 30:
            rsi_status = "Oversold 💎"
            
    # Active Zones
    active_zones = []
    if smc.get('zones'):
        if any(z['bottom'] <= current_price <= z['top'] for z in smc['zones'].get('demand', [])):
            active_zones.append("DEMAND 🏛️")
        if any(z['bottom'] <= current_price <= z['top'] for z in smc['zones'].get('supply', [])):
            active_zones.append("SUPPLY 📦")
        
    return {
        "price": current_price,
        "rsi": round(current_rsi, 2) if not pd.isna(current_rsi) else "Loading...",
        "trend": trend,
        "rsi_status": rsi_status,
        "active_zones": " | ".join(active_zones) if active_zones else "None",
        "liquidity": smc.get('liquidity', 'NORMAL')
    }

def calculate_mtf_conviction(mtf_contexts, primary_direction):
    """
    Upgrade 6: Calculates a conviction score based on higher timeframe bias.
    Higher Timeframes (5m, 15m) act as 'Weight' rather than hard filters.
    """
    if not mtf_contexts:
        return 0
        
    conviction = 0
    
    # 1. Check Mid-Timeframe (5m) - Momentum & Bias
    ctx_5m = mtf_contexts.get('5m')
    if ctx_5m:
        # Direction Alignment (+15)
        if ctx_5m['direction'] == primary_direction:
            conviction += 15
        else:
            conviction -= 10
            
        # Slope Alignment (+10)
        p_slope = 1 if primary_direction == "UP" else -1
        if (ctx_5m['slope'] > 0 and p_slope > 0) or (ctx_5m['slope'] < 0 and p_slope < 0):
            conviction += 10

    # 2. Check High-Timeframe (15m) - Structure & Trend
    ctx_15m = mtf_contexts.get('15m')
    if ctx_15m:
        smc_15m = ctx_15m.get('smc', {})
        bias_15m = smc_15m.get('bias', 'NEUTRAL')
        
        # Trend Alignment (+20)
        # Check if 15m direction OR SMC bias matches primary direction
        is_bull_trend = "LIFTING" in bias_15m or ctx_15m['direction'] == "UP"
        is_bear_trend = "HEAVY" in bias_15m or ctx_15m['direction'] == "DOWN"
        
        if primary_direction == "UP" and is_bull_trend:
            conviction += 20
        elif primary_direction == "DOWN" and is_bear_trend:
            conviction += 20
        elif primary_direction != "NEUTRAL":
            conviction -= 15 # Significant structural headwind

        # SMC Zone Confluence (+15)
        status_15m = smc_15m.get('status', 'NEUTRAL')
        if primary_direction == "UP" and "IN_DEMAND" in status_15m:
            conviction += 15
        if primary_direction == "DOWN" and "IN_SUPPLY" in status_15m:
            conviction += 15

    return conviction
