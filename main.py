import asyncio
import time
from datetime import datetime
import config
import strategy
import discord_utils
import pandas as pd
from data_provider import AsyncDataProvider
from correlation_engine import CorrelationEngine
from trailing_engine import PositionManager
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Global State for Tracking
last_signals = {}
in_extreme_zones = {}

def fmt_age(td):
    """Formats a timedelta into a short string (e.g. 2h, 45m)."""
    seconds = td.total_seconds()
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0: return f"{int(hours)}h"
    return f"{int(minutes)}m"

async def scan_asset(provider, symbol, asset_type, alerter):
    """Asynchronously processes a single asset and returns snapshot data."""
    try:
        data_tasks = []
        for tf in config.TIMEFRAMES:
            if asset_type == "CRYPTO":
                data_tasks.append(provider.fetch_crypto_ohlcv(symbol, tf))
            else:
                data_tasks.append(provider.fetch_mt5_ohlcv(symbol, tf))
        
        results = await asyncio.gather(*data_tasks)
        
        dfs = {}
        contexts = {}
        for i, tf in enumerate(config.TIMEFRAMES):
            df = results[i]
            if df is not None and not df.empty:
                dfs[tf] = df
                contexts[tf] = strategy.get_signal_context(df)

        # Initialize snapshot_data with default values
        snapshot_data = {
            "symbol": symbol,
            "price": dfs["1m"]['close'].iloc[-1] if "1m" in dfs else 0,
            "rsi": contexts["1m"]['rsi'] if "1m" in contexts else "N/A",
            "score": "0%",
            "signal": "NEUTRAL",
            "tp_rsi": None,
            "sl_price": None,
            "is_hunting": False,
            "zones": {},
            "status": "NEUTRAL",
            "liquidity": "NORMAL",
            "bias": "NEUTRAL",
            "magnet_5m": "None",
            "magnet_15m": "None",
            "tf_signals": {tf: "N/A" for tf in config.TIMEFRAMES}
        }

        # 1. Zone Alerts
        for tf in config.TIMEFRAMES:
            if tf in dfs:
                zone_alert, rsi_val = strategy.check_zone_alerts(dfs[tf])
                if zone_alert and not in_extreme_zones.get(f"{symbol}_{tf}_zone", False):
                    mtf_context = {t: contexts[t] for t in contexts if t != tf}
                    alerter.send_zone_alert(symbol, tf, zone_alert, rsi_val, contexts[tf], mtf_context)
                    in_extreme_zones[f"{symbol}_{tf}_zone"] = True
                elif not zone_alert:
                    in_extreme_zones[f"{symbol}_{tf}_zone"] = False

        # 2. Collect Signals and Status across all timeframes
        all_statuses = {}
        for tf in config.TIMEFRAMES:
            if tf in dfs:
                # Upgrade 6: Pass higher timeframe context to 1m check
                mtf_p = contexts if tf == "1m" else None
                sig, info, _ = strategy.check_signals_advanced(dfs[tf], mtf_contexts=mtf_p)
                snapshot_data["tf_signals"][tf] = sig if sig else "NEUTRAL"
                
                # Capture status for this TF
                tf_smc = contexts[tf].get('smc', {})
                all_statuses[tf] = tf_smc.get('status', 'NEUTRAL')

                # If it's 1m, update primary dashboard metrics (except status)
                if tf == "1m":
                    snapshot_data["signal"] = sig if sig else "NEUTRAL"
                    snapshot_data["score"] = info['score'] if sig else info.get('score', "0%")
                    snapshot_data["tp_rsi"] = info.get('tp_rsi') 
                    snapshot_data["sl_price"] = info.get('sl_price')
                    snapshot_data["is_hunting"] = info.get('is_hunting', False)
                    snapshot_data["zones"] = tf_smc.get('zones', {})
                    snapshot_data["liquidity"] = tf_smc.get('liquidity', "NORMAL")
                    snapshot_data["bias"] = tf_smc.get('bias', "NEUTRAL")
                    
                    # Macro Anchor Logic (1m Entry -> 15m Structural SL/TP)
                    if sig and "15m" in dfs:
                        # 15m Macro TP
                        macro_tp = strategy.get_dynamic_rsi_target(dfs["15m"], sig)
                        if macro_tp:
                            snapshot_data["tp_rsi"] = f"{macro_tp} (15m)"
                            info["tp_rsi"] = macro_tp # Update info for Discord
                        
                        # 15m Macro SL
                        macro_sl = strategy.calculate_structural_sl(dfs["15m"], sig, contexts["15m"])
                        if macro_sl:
                            snapshot_data["sl_price"] = macro_sl
                            info["sl_price"] = macro_sl # Update info for Discord
                
                # Fetch Magnets (Scalp: 5m, Intraday: 15m)
                if tf in ["5m", "15m"]:
                    mags = []
                    tf_df = dfs[tf]
                    current_time = tf_df['timestamp'].iloc[-1] if 'timestamp' in tf_df.columns else tf_df.index[-1]
                    
                    ssl_data = tf_smc.get('magnets', {}).get('ssl', [])
                    if ssl_data:
                        latest_ssl = ssl_data[-1]
                        mag_time = latest_ssl['time']
                        age = current_time - mag_time
                        mags.append(f"SSL({fmt_age(age)})")
                    
                    bsl_data = tf_smc.get('magnets', {}).get('bsl', [])
                    if bsl_data:
                        latest_bsl = bsl_data[-1]
                        mag_time = latest_bsl['time']
                        age = current_time - mag_time
                        mags.append(f"BSL({fmt_age(age)})")
                    
                    key = "magnet_5m" if tf == "5m" else "magnet_15m"
                    snapshot_data[key] = ",".join(mags) if mags else "None"

                # Specialized Hunting Alerts
                if info.get('is_hunting') and sig.startswith("HUNTING_"):
                    current_time = dfs[tf]['timestamp'].iloc[-1] if 'timestamp' in dfs[tf].columns else dfs[tf].index[-1]
                    hunt_key = f"{symbol}_{tf}_hunt"
                    if last_signals.get(hunt_key) != current_time:
                        alerter.send_hunting_alert(symbol, tf, dfs[tf]['close'].iloc[-1], contexts[tf]['rsi'], sig, contexts[tf])
                        last_signals[hunt_key] = current_time

                # 4. Filter Candidate Signals (Upgrade 7)
                # Instead of auto-alerting, we prepare them for the Batch Filter.
                if tf in ["1m", "3m"] and sig and info['strength'] >= config.MIN_SIGNAL_STRENGTH:
                    mtf_context = {t: contexts[t] for t in contexts if t != tf}
                    snapshot_data["signal_payload"] = {
                        "symbol": symbol,
                        "tf": tf,
                        "sig": sig,
                        "info": info,
                        "context": contexts[tf],
                        "mtf_context": mtf_context,
                        "score": info['strength']
                    }

        # 3. Master Status Aggregator (MTF Priority)
        # Priority: IN_ZONE (15m > 5m > 1m) then NEAR_ZONE (15m > 5m > 1m)
        final_status = "NEUTRAL"
        
        # Check for any "IN" status first
        for tf in ["15m", "5m", "1m"]:
            stat = all_statuses.get(tf, "NEUTRAL")
            if "IN_" in stat:
                final_status = f"{tf} {stat}"
                break
        
        # If still neutral, check for "NEAR"
        if final_status == "NEUTRAL":
            for tf in ["15m", "5m", "1m"]:
                stat = all_statuses.get(tf, "NEUTRAL")
                if "NEAR_" in stat:
                    final_status = f"{tf} {stat}"
                    break
        
        snapshot_data["status"] = final_status
        snapshot_data["df_1m"] = dfs.get("1m") # Return for trailing engine
        return snapshot_data

    except Exception as e:
        print(f"Error scanning {symbol}: {e}")
        return None

async def validate_symbols(provider):
    """Checks which symbols are actually available on the providers."""
    print("[SCAN] Validating Watchlists...")
    valid_crypto = []
    valid_forex = []
    valid_commodities = []

    # Crypto Check
    crypto_tasks = [provider.fetch_crypto_ohlcv(s, '1m', 5) for s in config.CRYPTO_WATCHLIST]
    crypto_results = await asyncio.gather(*crypto_tasks)
    for i, res in enumerate(crypto_results):
        if res is not None: valid_crypto.append(config.CRYPTO_WATCHLIST[i])
        else: print(f"[SKIP] Invalid Crypto: {config.CRYPTO_WATCHLIST[i]}")

    # Forex Check
    forex_tasks = [provider.fetch_mt5_ohlcv(s, '1m', 5) for s in config.FOREX_WATCHLIST]
    forex_results = await asyncio.gather(*forex_tasks)
    for i, res in enumerate(forex_results):
        if res is not None: valid_forex.append(config.FOREX_WATCHLIST[i])
        else: print(f"[SKIP] Invalid Forex: {config.FOREX_WATCHLIST[i]}")

    # Commodities Check
    comm_tasks = [provider.fetch_mt5_ohlcv(s, '1m', 5) for s in config.COMMODITIES_WATCHLIST]
    comm_results = await asyncio.gather(*comm_tasks)
    for i, res in enumerate(comm_results):
        if res is not None: valid_commodities.append(config.COMMODITIES_WATCHLIST[i])
        else: print(f"[SKIP] Invalid Commodity: {config.COMMODITIES_WATCHLIST[i]}")

    return valid_crypto, valid_forex, valid_commodities

async def startup_report(provider, crypto, forex, comm, alerter):
    """Sends a summary of all active assets to Discord."""
    print("[INFO] Generating Startup Dashboard...")
    all_summary = []
    
    # Choose representative assets for the dashboard to avoid spamming 22 alerts
    # We will send 3 key reports (one for each class)
    for cat, assets in [("CRYPTO", crypto[:3]), ("FOREX", forex[:3]), ("COMMODITY", comm[:3])]:
        if assets:
            symbol = assets[0]
            df = await (provider.fetch_crypto_ohlcv(symbol) if cat == "CRYPTO" else provider.fetch_mt5_ohlcv(symbol))
            if df is not None:
                market_data = strategy.get_market_situation(df)
                alerter.send_market_report(symbol, "Scanner Active", market_data)

def print_premium_dashboard(results):
    """Renders a premium table in the console using rich."""
    if not RICH_AVAILABLE:
        print("\n--- Market Snapshot ---")
        for res in results:
            if res: print(f"{res['symbol']}: {res['price']} | RSI: {res['rsi']} | Grade: {res['grade']}")
        return

    console = Console()
    table = Table(title="--- Market Snapshot at a Glance ---", box=box.ASCII, header_style="bold magenta")
    
    table.add_column("Symbol", style="cyan", justify="left")
    table.add_column("Price", style="white")
    table.add_column("RSI", style="yellow")
    table.add_column("Score", justify="center")
    table.add_column("Market Bias", justify="center")
    table.add_column("Scalp Liq", justify="center")
    table.add_column("Intraday Liq", justify="center")
    table.add_column("SMC Status", style="green")
    table.add_column("Liquidity", style="bold blue")
    table.add_column("1m", justify="center")
    table.add_column("3m", justify="center")
    table.add_column("5m", justify="center")
    table.add_column("15m", justify="center")

    for res in results:
        if not res: continue
        
        # Color signal/score
        sig_color = "red" if res['signal'] == "SELL" else "green" if res['signal'] == "BUY" else "white"
        
        # Grading colors based on percentage
        score_val = int(res['score'].replace('%', ''))
        if score_val >= 70:
            score_color = "bold green"
        elif score_val <= 40:
            score_color = "red"
        else:
            score_color = "yellow"
        
        # Determine SMC Status
        # Determine SMC Status (Actionable & Sticky)
        full_status = res.get('status', 'NEUTRAL')
        bias = res['bias']
        
        # Split prefix if exists (e.g. "5m IN_DEMAND")
        parts = full_status.split(" ")
        tf_prefix = f"{parts[0]} " if len(parts) > 1 else ""
        raw_status = parts[1] if len(parts) > 1 else parts[0]
        
        smc_status = "Neutral"
        
        if "DEMAND" in raw_status:
            if "IN_DEMAND" in raw_status:
                if "HEAVY" in bias:
                    smc_status = f"[bold red]{tf_prefix}DEMAND: Risk![/]"
                else:
                    smc_status = f"[bold green]{tf_prefix}DEMAND: Wait Buy[/]"
            elif "NEAR_DEMAND" in raw_status:
                smc_status = f"[green]{tf_prefix}NEAR DEMAND[/]"
                
        elif "SUPPLY" in raw_status:
            if "IN_SUPPLY" in raw_status:
                if "LIFTING" in bias:
                    smc_status = f"[bold green]{tf_prefix}SUPPLY: Risk![/]"
                else:
                    smc_status = f"[bold red]{tf_prefix}SUPPLY: Wait Sell[/]"
            elif "NEAR_SUPPLY" in raw_status:
                smc_status = f"[red]{tf_prefix}NEAR SUPPLY[/]"
        
        # Add Stop Loss info to status column
        sl_price = res.get('sl_price')
        if sl_price:
            smc_status += f"\n[dim white]🛡️SL: {sl_price}[/]"
        
        # Hunting Decorator for Signal
        sig_str = res['signal']
        if res.get('is_hunting'):
            sig_str = f"[bold orange1]![/] {sig_str} [bold orange1]![/]"
        if sig_str == "BUY": sig_str = f"[bold green]{sig_str}[/]"
        elif sig_str == "SELL": sig_str = f"[bold red]{sig_str}[/]"
        elif "HUNTING" in sig_str: sig_str = f"[bold orange1]{sig_str}[/]"
        
        # Market Bias Formatting
        bias_str = res['bias']
        if "HEAVY" in bias_str: bias_str = f"[bold red]{bias_str}[/]"
        elif "LIFTING" in bias_str: bias_str = f"[bold green]{bias_str}[/]"
        
        # Helper to format magnet strings
        def fmt_mag(mag_str):
            if mag_str == "None": return "[dim]None[/]"
            parts = mag_str.split(",")
            formatted = []
            for p in parts:
                if "SSL" in p: formatted.append(f"[bold green]{p}[/]")
                elif "BSL" in p: formatted.append(f"[bold red]{p}[/]")
                else: formatted.append(p)
            return "\n".join(formatted)

        mag_5m = fmt_mag(res.get('magnet_5m', 'None'))
        mag_15m = fmt_mag(res.get('magnet_15m', 'None'))

        def fmt_tf(tf_sig):
            if tf_sig == "BUY": return "[bold green]BUY[/]"
            if tf_sig == "SELL": return "[bold red]SELL[/]"
            return "[dim]--[/]"

        # RSI Color Logic
        rsi_raw = res.get('rsi', 'N/A')
        tp_rsi = res.get('tp_rsi')
        rsi_str = str(rsi_raw)
        
        if isinstance(rsi_raw, (int, float)):
            if rsi_raw >= 70: rsi_str = f"[bold red]{rsi_raw:.2f}[/]"
            elif rsi_raw <= 30: rsi_str = f"[bold green]{rsi_raw:.2f}[/]"
            elif (60 <= rsi_raw < 70) or (30 < rsi_raw <= 40): rsi_str = f"[yellow]{rsi_raw:.2f}[/]"
            else: rsi_str = f"{rsi_raw:.2f}"
            
        # Append TP Target if available
        if tp_rsi:
            rsi_str += f"\n[dim italic]🎯TP: {tp_rsi}[/]"

        table.add_row(
            res['symbol'],
            f"{res['price']:.4f}" if res['price'] < 1 else f"{res['price']:.2f}",
            rsi_str,
            f"[{score_color}]{res['score']}[/]",
            bias_str,
            mag_5m,
            mag_15m,
            smc_status,
            res['liquidity'],
            fmt_tf(res['tf_signals'].get("1m")),
            fmt_tf(res['tf_signals'].get("3m")),
            fmt_tf(res['tf_signals'].get("5m")),
            fmt_tf(res['tf_signals'].get("15m"))
        )

    console.print("\n", table)

async def main():
    console = Console() if RICH_AVAILABLE else None
    if console:
        console.print(Panel.fit("[bold green]Ultra-Fast Async Market Scanner (Premium SMC Edition)[/]", border_style="cyan"))
    else:
        print("Initializing Ultra-Fast Async Market Scanner...")
        
    provider = AsyncDataProvider(config.EXCHANGE)
    alerter = discord_utils.DiscordAlerter(config.DISCORD_WEBHOOK_URL, config.DISCORD_EXTREME_WEBHOOK_URL)
    correlation_engine = CorrelationEngine()
    pos_manager = PositionManager()

    # 1. Validate symbols and cleanup watchlists
    valid_crypto, valid_forex, valid_comm = await validate_symbols(provider)
    
    # 2. Startup Report
    await startup_report(provider, valid_crypto, valid_forex, valid_comm, alerter)

    if console:
        console.print(f"\n[DONE] [bold]Initialization Complete.[/] Monitoring [cyan]{len(valid_crypto) + len(valid_forex) + len(valid_comm)} Assets.[/]")
    else:
        print(f"\n[DONE] Initialization Complete. Monitoring {len(valid_crypto) + len(valid_forex) + len(valid_comm)} Assets.")

    # Create a cache for last valid results to prevent flickering (0.0000)
    last_valid_results = {}

    try:
        while True:
            start_time = time.time()
            
            tasks = []
            for s in valid_crypto: tasks.append(scan_asset(provider, s, "CRYPTO", alerter))
            for s in valid_forex: tasks.append(scan_asset(provider, s, "FOREX", alerter))
            for s in valid_comm: tasks.append(scan_asset(provider, s, "COMMODITY", alerter))
            
            # Execute ALL scans in parallel
            raw_results = await asyncio.gather(*tasks)
            
            # 4. Hybrid Correlation System (Upgrade 7)
            candidate_payloads = []
            for res in patched_results:
                if "signal_payload" in res:
                    candidate_payloads.append(res["signal_payload"])
            
            # Apply Soft Filter (Tagging)
            # Formulate 'signals' list for the engine
            tag_input = [{"symbol": p['symbol'], "strength": p['score']} for p in candidate_payloads]
            tagged_results = correlation_engine.tag_signals(tag_input)
            
            # Map tags back to payloads
            tag_map = {t['symbol']: t for t in tagged_results}
            
            # 5. Execute Alerts (100% Frequency - Hybrid Style)
            for p in candidate_payloads:
                tag_info = tag_map.get(p['symbol'], {})
                cluster_tag = f"[{' | '.join(tag_info.get('clusters', []))}]" if tag_info.get('clusters') else ""
                leader_tag = "👑 [LEADER]" if tag_info.get('is_leader') else "⚠️ [OVERLAP]"
                
                # Logic to prevent duplicate alerts per candle
                sig_key = f"{p['symbol']}_{p['tf']}_signal"
                current_time = datetime.now().strftime("%H:%M") # Approx 
                
                if last_signals.get(sig_key) != current_time:
                    p['info']['macro_tp'] = p.get('info', {}).get('macro_tp')
                    p['info']['cluster_context'] = f"{cluster_tag} {leader_tag}"
                    
                    alerter.send_advanced_signal(p['symbol'], p['tf'], p['sig'], p['info'], p['context'], p['mtf_context'])
                    last_signals[sig_key] = current_time
                    
                    # Track for trailing (Upgrade 9)
                    pos_manager.add_position(
                        p['symbol'], 
                        p['sig'], 
                        p['context']['price'], 
                        p['info'].get('sl_price', p['context']['price'] * 0.99), # Fallback SL
                        p['info'].get('macro_tp', p['context']['price'] * 1.01)  # Fallback TP
                    )

            # Update results for Dashboard display
            for res in patched_results:
                t_info = tag_map.get(res['symbol'], {})
                if t_info.get('clusters'):
                    res['score'] = f"{res['score']} ({t_info['clusters'][0][:3]})"
                    if not t_info.get('is_leader'):
                        res['score'] = f"⚠️ {res['score']}"

            # Render Premium Dashboard
            print_premium_dashboard(patched_results)

            # Render Premium Dashboard
            print_premium_dashboard(patched_results)

            duration = round(time.time() - start_time, 2)
            if console:
                console.print(f"[dim][{datetime.now().strftime('%H:%M:%S')}] Scan Finished in {duration}s. Sleeping {config.POLLING_INTERVAL}s...[/]")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Scan Finished in {duration}s. Sleep {config.POLLING_INTERVAL}s.")
            
            await asyncio.sleep(config.POLLING_INTERVAL)

    except KeyboardInterrupt:
        print("\nScanner stopped by user.")
    finally:
        await provider.close()

if __name__ == "__main__":
    asyncio.run(main())
