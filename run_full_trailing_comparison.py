"""
Full Trailing Engine Comparison: Baseline vs V2
Outputs every single trade metric for BTC, ETH, SOL over 3 days.
$1000 per trade position size.
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_provider import AsyncDataProvider
import strategy
from trailing_engine import PositionManager
from trailing_engine_v2 import TrailingEngineV2
import os
import json

ASSETS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
DAYS = 3
RISK_AMOUNT = 1000
THRESHOLD_MAP = {"BTC/USDT": 80, "ETH/USDT": 70, "SOL/USDT": 65}

# ─── BASELINE ENGINE SIMULATION ───────────────────────────────────────
def simulate_baseline(df, start_idx, signal, entry_price, sl_price, tp_price):
    """Simulate using the EXISTING PositionManager (Breakeven + Pivot Trailing)."""
    pm = PositionManager()
    symbol = "TEST"
    direction = "BUY" if "BUY" in signal else "SELL"
    pm.add_position(symbol, direction, entry_price, sl_price, tp_price)
    
    trail_log = []
    max_bars = 200
    exit_price = entry_price
    exit_reason = "TIMEOUT"
    bars_held = 0
    max_favorable = 0
    max_adverse = 0
    
    for j in range(1, max_bars + 1):
        ci = start_idx + j
        if ci >= len(df): break
        
        curr_high = df['high'].iloc[ci]
        curr_low = df['low'].iloc[ci]
        curr_close = df['close'].iloc[ci]
        
        pos = pm.active_positions.get(symbol)
        if not pos: break
        
        current_sl = pos['current_sl']
        
        # Track max excursion
        if direction == "BUY":
            fav = curr_high - entry_price
            adv = entry_price - curr_low
        else:
            fav = entry_price - curr_low
            adv = curr_high - entry_price
        max_favorable = max(max_favorable, fav)
        max_adverse = max(max_adverse, adv)
        
        # Check SL
        if direction == "BUY" and curr_low <= current_sl:
            exit_price = current_sl
            exit_reason = "TRAIL_SL" if pos.get('is_be') or current_sl != sl_price else "INIT_SL"
            break
        elif direction == "SELL" and curr_high >= current_sl:
            exit_price = current_sl
            exit_reason = "TRAIL_SL" if pos.get('is_be') or current_sl != sl_price else "INIT_SL"
            break
            
        # Check TP
        if direction == "BUY" and curr_high >= tp_price:
            exit_price = tp_price
            exit_reason = "TP_HIT"
            break
        elif direction == "SELL" and curr_low <= tp_price:
            exit_price = tp_price
            exit_reason = "TP_HIT"
            break
        
        # Engine update
        hist = df.iloc[max(0, ci-50):ci+1]
        updates = pm.process_update(symbol, curr_close, hist, None)
        if updates:
            if updates.get('exit'):
                exit_price = curr_close
                exit_reason = updates.get('status', 'ENGINE_EXIT')
                break
            if updates.get('sl'):
                trail_log.append(f"Bar+{j}: SL→{updates['sl']:.4f} ({updates.get('status','')})")
                
        bars_held = j
    
    qty = RISK_AMOUNT / entry_price
    pnl = ((exit_price - entry_price) if direction == "BUY" else (entry_price - exit_price)) * qty
    pnl_pct = (pnl / RISK_AMOUNT) * 100
    
    return {
        "exit_price": round(exit_price, 6),
        "exit_reason": exit_reason,
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "bars_held": bars_held,
        "max_favorable_pct": round((max_favorable / entry_price) * 100, 3),
        "max_adverse_pct": round((max_adverse / entry_price) * 100, 3),
        "trail_log": trail_log
    }

# ─── V2 ENGINE SIMULATION ─────────────────────────────────────────────
def simulate_v2(df, start_idx, signal, entry_price, sl_price, s15_map, all_pivots, p_params, pivots_h, pivots_l):
    """Simulate using the NEW TrailingEngineV2 (ATR + Weighted Matrix)."""
    engine = TrailingEngineV2(s15_map)
    symbol = "TEST"
    direction = "BUY" if "BUY" in signal else "SELL"
    tp_price = entry_price * 1.5 if direction == "BUY" else entry_price * 0.5  # Wide TP, rely on trailing
    engine.add_position(symbol, direction, entry_price, sl_price, tp_price, df['timestamp'].iloc[start_idx])
    
    trail_log = []
    max_bars = 200
    exit_price = entry_price
    exit_reason = "TIMEOUT"
    bars_held = 0
    max_favorable = 0
    max_adverse = 0
    
    for j in range(1, max_bars + 1):
        ci = start_idx + j
        if ci >= len(df): break
        
        curr_row = df.iloc[ci]
        curr_high = curr_row['high']
        curr_low = curr_row['low']
        curr_close = curr_row['close']
        
        # Track excursion
        if direction == "BUY":
            max_favorable = max(max_favorable, curr_high - entry_price)
            max_adverse = max(max_adverse, entry_price - curr_low)
        else:
            max_favorable = max(max_favorable, entry_price - curr_low)
            max_adverse = max(max_adverse, curr_high - entry_price)
        
        pos = engine.active_positions.get(symbol)
        if not pos: break
        
        # Check SL
        if direction == "BUY" and curr_low <= pos['current_sl']:
            exit_price = pos['current_sl']
            exit_reason = "DYNAMIC_SL" if pos['current_sl'] != sl_price else "INIT_SL"
            break
        elif direction == "SELL" and curr_high >= pos['current_sl']:
            exit_price = pos['current_sl']
            exit_reason = "DYNAMIC_SL" if pos['current_sl'] != sl_price else "INIT_SL"
            break
        
        # Get S1 for this candle
        s1_now = 50
        try:
            res_now = strategy.check_signals_optimized(df, ci, all_pivots, p_params, pivots_h, pivots_l)
            if res_now and res_now[1]:
                s1_now = res_now[1]['strength']
        except:
            pass
        ctx_now = res_now[2] if res_now else {}
        
        hist = df.iloc[max(0, ci-50):ci+1]
        updates = engine.process_update(symbol, curr_row, hist, s1_now, ctx_now)
        
        if updates:
            if updates.get('exit'):
                exit_price = curr_close
                exit_reason = updates.get('status', 'MATRIX_EXIT')
                break
            if updates.get('sl'):
                trail_log.append(f"Bar+{j}: SL→{updates['sl']:.4f} ({updates.get('status','')})")
                
        bars_held = j
    
    qty = RISK_AMOUNT / entry_price
    pnl = ((exit_price - entry_price) if direction == "BUY" else (entry_price - exit_price)) * qty
    pnl_pct = (pnl / RISK_AMOUNT) * 100
    
    return {
        "exit_price": round(exit_price, 6),
        "exit_reason": exit_reason,
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "bars_held": bars_held,
        "max_favorable_pct": round((max_favorable / entry_price) * 100, 3),
        "max_adverse_pct": round((max_adverse / entry_price) * 100, 3),
        "trail_log": trail_log
    }

# ─── S15 MAP GENERATOR ────────────────────────────────────────────────
def generate_s15_map(df_1m):
    # Use ONLY clean OHLCV columns for resampling
    df_clean = df_1m[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
    df_15m = df_clean.resample('15min', on='timestamp').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    print(f"    [S15] Resampled to {len(df_15m)} bars (15m)")
    
    if len(df_15m) < 55:
        print(f"    [S15] Not enough 15m bars (<55), using defaults")
        return {}
    
    df_15m, pivots, params, ph, pl = strategy.prepare_data(df_15m)
    s15_map = {}
    for i in range(50, len(df_15m)):
        try:
            res = strategy.check_signals_optimized(df_15m, i, pivots, params, ph, pl)
            if res and res[1]:
                s15_map[df_15m['timestamp'].iloc[i]] = res[1]['strength']
        except:
            pass
    return s15_map

# ─── MAIN ──────────────────────────────────────────────────────────────
async def run():
    provider = AsyncDataProvider()
    
    all_baseline = []
    all_v2 = []
    report_lines = []
    
    report_lines.append("# 📊 Full Trailing Engine Comparison Report")
    report_lines.append(f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report_lines.append(f"**Period:** {DAYS} Days | **Risk:** ${RISK_AMOUNT}/trade")
    report_lines.append("")
    
    try:
        for symbol in ASSETS:
            min_strength = THRESHOLD_MAP.get(symbol, 60)
            report_lines.append(f"\n---\n## {symbol} (Threshold: {min_strength}%)\n")
            
            print(f"\n{'='*80}")
            print(f"  ANALYZING {symbol} (Thr {min_strength}%)")
            print(f"{'='*80}")
            
            # Fetch data
            since = int((datetime.now() - timedelta(days=DAYS)).timestamp() * 1000)
            ohlcv = await provider.exchange.fetch_ohlcv(symbol, '1m', since=since, limit=DAYS*1440)
            if not ohlcv:
                print(f"  [SKIP] No data for {symbol}")
                continue
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric)
            
            print(f"  Fetched {len(df)} candles")
            
            # Prepare indicators
            df, all_pivots, p_params, pivots_h, pivots_l = strategy.prepare_data(df)
            
            # Generate S15 map for V2
            print(f"  Generating 15m Strength Map...")
            s15_map = generate_s15_map(df)
            print(f"  S15 Map: {len(s15_map)} entries")
            
            # Scan for signals
            baseline_trades = []
            v2_trades = []
            
            i = 200
            trade_num = 0
            while i < len(df) - 10:
                res = strategy.check_signals_optimized(df, i, all_pivots, p_params, pivots_h, pivots_l)
                if not res or not res[0] or res[0] == "NEUTRAL":
                    i += 1
                    continue
                
                signal, info, ctx = res
                if info['strength'] < min_strength:
                    i += 1
                    continue
                
                trade_num += 1
                entry_price = df['close'].iloc[i]
                sl_price = info.get('sl_price')
                if not sl_price or sl_price == entry_price:
                    i += 1
                    continue
                
                # TP for baseline: 1.5R
                dist = abs(entry_price - sl_price)
                if "BUY" in signal:
                    tp_price = entry_price + dist * 1.5
                else:
                    tp_price = entry_price - dist * 1.5
                
                ts = df['timestamp'].iloc[i]
                direction = "BUY" if "BUY" in signal else "SELL"
                
                print(f"\n  Trade #{trade_num}: {direction} @ {entry_price:.4f} | SL {sl_price:.4f} | Str {info['strength']}% | {ts}")
                
                # Run Baseline
                b_res = simulate_baseline(df, i, signal, entry_price, sl_price, tp_price)
                b_res.update({"trade_num": trade_num, "symbol": symbol, "direction": direction,
                              "entry_price": entry_price, "timestamp": str(ts), "strength": info['strength'],
                              "engine": "BASELINE"})
                baseline_trades.append(b_res)
                
                # Run V2
                v2_res = simulate_v2(df, i, signal, entry_price, sl_price, s15_map, all_pivots, p_params, pivots_h, pivots_l)
                v2_res.update({"trade_num": trade_num, "symbol": symbol, "direction": direction,
                               "entry_price": entry_price, "timestamp": str(ts), "strength": info['strength'],
                               "engine": "V2"})
                v2_trades.append(v2_res)
                
                b_icon = "✅" if b_res['pnl'] > 0 else "❌"
                v2_icon = "✅" if v2_res['pnl'] > 0 else "❌"
                print(f"    BASELINE: {b_icon} ${b_res['pnl']:+.2f} ({b_res['pnl_pct']:+.2f}%) | Exit: {b_res['exit_reason']} | Bars: {b_res['bars_held']}")
                print(f"    V2:       {v2_icon} ${v2_res['pnl']:+.2f} ({v2_res['pnl_pct']:+.2f}%) | Exit: {v2_res['exit_reason']} | Bars: {v2_res['bars_held']}")
                
                # Skip ahead
                skip = max(b_res['bars_held'], v2_res['bars_held']) + 1
                i += skip
            
            # Per-asset summary
            b_net = sum(t['pnl'] for t in baseline_trades)
            v2_net = sum(t['pnl'] for t in v2_trades)
            b_wins = len([t for t in baseline_trades if t['pnl'] > 0])
            v2_wins = len([t for t in v2_trades if t['pnl'] > 0])
            b_wr = (b_wins / len(baseline_trades) * 100) if baseline_trades else 0
            v2_wr = (v2_wins / len(v2_trades) * 100) if v2_trades else 0
            
            print(f"\n  {'─'*60}")
            print(f"  {symbol} SUMMARY:")
            print(f"    BASELINE: {len(baseline_trades)} trades | WR {b_wr:.1f}% | Net ${b_net:+.2f}")
            print(f"    V2:       {len(v2_trades)} trades | WR {v2_wr:.1f}% | Net ${v2_net:+.2f}")
            
            # Write to report
            report_lines.append(f"### Summary\n")
            report_lines.append(f"| Metric | Baseline | V2 (New) |")
            report_lines.append(f"| :--- | :--- | :--- |")
            report_lines.append(f"| Trades | {len(baseline_trades)} | {len(v2_trades)} |")
            report_lines.append(f"| Win Rate | {b_wr:.1f}% | {v2_wr:.1f}% |")
            report_lines.append(f"| Net PnL | ${b_net:+.2f} | ${v2_net:+.2f} |")
            report_lines.append("")
            
            report_lines.append(f"### Trade-by-Trade Detail\n")
            report_lines.append(f"| # | Time | Dir | Entry | Str | B.Exit | B.PnL | B.Reason | V2.Exit | V2.PnL | V2.Reason |")
            report_lines.append(f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            
            for idx_t in range(len(baseline_trades)):
                b = baseline_trades[idx_t]
                v = v2_trades[idx_t]
                b_icon = "✅" if b['pnl'] > 0 else "❌"
                v_icon = "✅" if v['pnl'] > 0 else "❌"
                report_lines.append(
                    f"| {b['trade_num']} | {b['timestamp'][:16]} | {b['direction']} | "
                    f"{b['entry_price']:.2f} | {b['strength']}% | "
                    f"{b['exit_price']:.2f} | {b_icon} ${b['pnl']:+.2f} | {b['exit_reason']} | "
                    f"{v['exit_price']:.2f} | {v_icon} ${v['pnl']:+.2f} | {v['exit_reason']} |"
                )
            report_lines.append("")
            
            # Excursion Analysis
            report_lines.append(f"### Excursion Analysis\n")
            report_lines.append(f"| # | Max Favorable (%) | Max Adverse (%) | B.Captured | V2.Captured |")
            report_lines.append(f"| :--- | :--- | :--- | :--- | :--- |")
            for idx_t in range(len(baseline_trades)):
                b = baseline_trades[idx_t]
                v = v2_trades[idx_t]
                b_cap = f"{b['pnl_pct']:+.2f}% of {b['max_favorable_pct']:.2f}%"
                v_cap = f"{v['pnl_pct']:+.2f}% of {v['max_favorable_pct']:.2f}%"
                report_lines.append(f"| {b['trade_num']} | {b['max_favorable_pct']:.3f}% | {b['max_adverse_pct']:.3f}% | {b_cap} | {v_cap} |")
            
            all_baseline.extend(baseline_trades)
            all_v2.extend(v2_trades)
            
            await asyncio.sleep(1)
        
        # ─── GRAND TOTALS ──────────────────────────────────────────────
        total_b = sum(t['pnl'] for t in all_baseline)
        total_v2 = sum(t['pnl'] for t in all_v2)
        total_b_wr = (len([t for t in all_baseline if t['pnl'] > 0]) / len(all_baseline) * 100) if all_baseline else 0
        total_v2_wr = (len([t for t in all_v2 if t['pnl'] > 0]) / len(all_v2) * 100) if all_v2 else 0
        
        report_lines.append(f"\n---\n## 🏆 Grand Total\n")
        report_lines.append(f"| Metric | Baseline | V2 (New) | Delta |")
        report_lines.append(f"| :--- | :--- | :--- | :--- |")
        report_lines.append(f"| Total Trades | {len(all_baseline)} | {len(all_v2)} | — |")
        report_lines.append(f"| Win Rate | {total_b_wr:.1f}% | {total_v2_wr:.1f}% | {total_v2_wr - total_b_wr:+.1f}% |")
        report_lines.append(f"| Net PnL | ${total_b:+.2f} | ${total_v2:+.2f} | ${total_v2 - total_b:+.2f} |")
        report_lines.append(f"| Avg PnL/Trade | ${total_b/len(all_baseline) if all_baseline else 0:.2f} | ${total_v2/len(all_v2) if all_v2 else 0:.2f} | — |")
        
        print(f"\n{'='*80}")
        print(f"  GRAND TOTAL")
        print(f"  BASELINE: {len(all_baseline)} trades | WR {total_b_wr:.1f}% | Net ${total_b:+.2f}")
        print(f"  V2:       {len(all_v2)} trades | WR {total_v2_wr:.1f}% | Net ${total_v2:+.2f}")
        print(f"{'='*80}")
        
        # Save report
        docs_dir = r"C:\BILLIONAIRE RAHUL BOGI\Assets_RS_SMC_Mt5_Binance_test_trades\docs"
        os.makedirs(docs_dir, exist_ok=True)
        
        report_path = os.path.join(docs_dir, "trailing_engine_comparison_report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        print(f"\n📄 Report saved to: {report_path}")
        
        # Save raw data as JSON
        json_path = os.path.join(docs_dir, "trailing_trades_raw.json")
        with open(json_path, 'w') as f:
            json.dump({"baseline": all_baseline, "v2": all_v2}, f, indent=2, default=str)
        print(f"📄 Raw data saved to: {json_path}")
        
    finally:
        await provider.close()

if __name__ == "__main__":
    asyncio.run(run())
