import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, time
import os
import sys

# --- IMPORT FIX FOR RELOCATED SCRIPT ---
# Add project root to path so we can find config, strategy, etc.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import config
from data_provider import AsyncDataProvider
import strategy
from trailing_engine import PositionManager

# --- SESSION CONFIGURATION ---
INVESTMENT_PER_TRADE = 100000  # $100,000
SWEET_SPOT_THRESHOLDS = {
    "BTC/USDT": 80, "ETH/USDT": 70, "BNB/USDT": 65,
    "DOGE/USDT": 75, "LTC/USDT": 70, "SOL/USDT": 65,
    "XAUUSD": 60, "XAGUSD": 75, "USDJPY": 60,
    "EURUSD": 60, "XAUEUR": 60, "ATOM/USDT": 60,
    "GBPUSD": 60, "GBPJPY": 60, "CADJPY": 60,
    "EURAUD": 60, "USDCHF": 60, "TRUMP/USDT": 60,
    "SHIB/USDT": 60, "PUMP/USDT": 60
}

DOCS_DIR = r"C:\BILLIONAIRE RAHUL BOGI\Assets_RS_SMC_Mt5_Binance_test_trades\docs\live_demo_trades"
# Generate a dynamic session filename: session_YYYYMMDD_HHMM.md
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M")
LOG_FILE = os.path.join(DOCS_DIR, f"session_{SESSION_ID}.md")

class LiveDemoSession:
    def __init__(self):
        self.provider = AsyncDataProvider()
        self.pm = PositionManager()
        self.running = True
        self.active_trades = {} # (symbol, timeframe) -> trade_data
        
        os.makedirs(DOCS_DIR, exist_ok=True)
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write("# 📡 Live Demo Session Trade Log\n\n")
                f.write("| Time | Symbol | TF | Dir | Entry | SL | TP | Strength | Status | PnL ($) |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")

    def is_market_open(self, asset_type):
        """Checks if the market is open for the given asset type."""
        if asset_type == "CRYPTO":
            return True
            
        # Forex/Metals: Closed Sat/Sun (UTC approximation)
        now = datetime.utcnow()
        day = now.weekday() # 0=Mon, 4=Fri, 5=Sat, 6=Sun
        
        if day >= 5: # Saturday or Sunday
            return False
            
        # Optional: Add Friday close (22:00 UTC) and Sunday open (21:00 UTC)
        if day == 4 and now.hour >= 22:
            return False
        if day == 6 and now.hour < 21:
            return False
            
        return True

    def log_trade(self, trade_data, status, pnl=0):
        """Logs trade activity to the session-specific markdown file."""
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(f"| {datetime.now().strftime('%H:%M:%S')} | {trade_data['symbol']} | {trade_data['tf']} | "
                        f"{trade_data['direction']} | {trade_data['entry_price']:.4f} | "
                        f"{trade_data.get('current_sl', 0):.4f} | {trade_data.get('target_tp', 0):.4f} | "
                        f"{trade_data['strength']}% | {status} | {pnl:+.2f} |\n")
        except Exception as e:
            print(f"⚠️ Error logging trade: {e}")

    async def scan_asset(self, symbol, asset_type, tf='1m'):
        """Single asset scan logic."""
        if not self.is_market_open(asset_type):
            return

        # Fetch Data
        df = None
        try:
            if asset_type == "CRYPTO":
                df = await self.provider.fetch_crypto_ohlcv(symbol, tf, limit=200)
            else:
                df = await self.provider.fetch_mt5_ohlcv(symbol, tf, limit=200)
        except Exception as e:
            return

        if df is None or df.empty:
            return

        # Pre-calculate Indicators
        try:
            df, pivots, params, ph, pl = strategy.prepare_data(df)
            if 'RSI' not in df.columns:
                df = strategy.calculate_rsi(df)
        except Exception as e:
            return

        key = (symbol, tf)
        # 1. Update Active Position
        if key in self.pm.active_positions:
            curr_price = df['close'].iloc[-1]
            
            # Step forward in Trailing Engine
            try:
                updates = self.pm.process_update(symbol, tf, curr_price, df, None)
            except KeyError as e:
                print(f"  [ERR] {symbol} ({tf}) update failed: Column {e} missing.")
                return
            
            if updates:
                if updates.get('sl'):
                    print(f"  🔄 [TRAILING] {symbol} ({tf}): SL moved to {updates['sl']:.4f} ({updates.get('status')})")
                
                if updates.get('exit'):
                    pnl_vals = self.calculate_pnl(symbol, tf, curr_price)
                    print(f"  🏁 [EXIT] {symbol} ({tf}): {updates.get('status')} | PnL: ${pnl_vals['pnl']:+.2f}")
                    self.log_trade(self.active_trades[key], updates.get('status'), pnl_vals['pnl'])
                    self.pm.remove_position(symbol, tf)
                    del self.active_trades[key]
                    return

            # Hard SL/TP Check
            if self.check_hard_exits(symbol, tf, curr_price):
                return

        # 2. Check for New Entries
        else:
            res = strategy.check_signals_optimized(df, len(df)-1, pivots, params, ph, pl)
            
            if res and res[0] != "NEUTRAL":
                signal, info, ctx = res
                threshold = SWEET_SPOT_THRESHOLDS.get(symbol, 60)
                
                if info['strength'] >= threshold:
                    entry_price = df['close'].iloc[-1]
                    # Logic 9.2: Market Geometry SL (No ATR Buffer)
                    sl_price = strategy.calculate_structural_sl(df, signal, ctx)
                    
                    if not sl_price: return

                    # Target TP (1.5R)
                    dist = abs(entry_price - sl_price)
                    tp_price = entry_price + dist * 1.5 if "BUY" in signal else entry_price - dist * 1.5
                    
                    print(f"  🚀 [ENTRY] {symbol} ({tf}): {signal} @ {entry_price:.4f} (Str {info['strength']}%)")
                    
                    self.pm.add_position(symbol, tf, "BUY" if "BUY" in signal else "SELL", entry_price, sl_price, tp_price)
                    self.active_trades[key] = {
                        "symbol": symbol, "tf": tf, "direction": "BUY" if "BUY" in signal else "SELL",
                        "entry_price": entry_price, "strength": info['strength'],
                        "current_sl": sl_price, "target_tp": tp_price
                    }
                    self.log_trade(self.active_trades[key], "ENTERED")

    def check_hard_exits(self, symbol, tf, curr_price):
        """Fallback hard SL/TP check."""
        key = (symbol, tf)
        pos = self.pm.active_positions[key]
        direction = pos['direction']
        sl = pos['current_sl']
        tp = pos['target_tp']
        
        hit = False
        reason = ""
        
        if direction == "BUY":
            if curr_price <= sl: hit, reason = True, "SL_HIT"
            elif curr_price >= tp: hit, reason = True, "TP_HIT"
        else:
            if curr_price >= sl: hit, reason = True, "SL_HIT"
            elif curr_price <= tp: hit, reason = True, "TP_HIT"
            
        if hit:
            pnl_vals = self.calculate_pnl(symbol, tf, curr_price)
            print(f"  🏁 [EXIT] {symbol} ({tf}): {reason} | PnL: ${pnl_vals['pnl']:+.2f}")
            self.log_trade(self.active_trades[key], reason, pnl_vals['pnl'])
            self.pm.remove_position(symbol, tf)
            del self.active_trades[key]
            return True
        return False

    def calculate_pnl(self, symbol, tf, exit_price):
        key = (symbol, tf)
        trade = self.active_trades[key]
        entry = trade['entry_price']
        qty = INVESTMENT_PER_TRADE / entry
        pnl = (exit_price - entry) * qty if trade['direction'] == "BUY" else (entry - exit_price) * qty
        return {"pnl": pnl, "pnl_pct": (pnl / INVESTMENT_PER_TRADE) * 100}

    async def run_session(self):
        print("\n" + "="*80)
        print("🕯️ LIVE DEMO TRADING SESSION STARTED (TARGETED MTF)")
        print(f"💰 Position Size: ${INVESTMENT_PER_TRADE:,} | Assets: Optimized Selection")
        print(f"📈 5m Targets: BTC, ETH, SOL")
        print(f"📈 1m Targets: BTC, ETH, SOL, XAUUSD")
        print(f"📂 Logging to: {LOG_FILE}")
        print("="*80)
        
        # Build Targeted Asset Matrix
        targets = {
            '5m': [
                {"symbol": "BTC/USDT", "type": "CRYPTO"},
                {"symbol": "ETH/USDT", "type": "CRYPTO"},
                {"symbol": "SOL/USDT", "type": "CRYPTO"}
            ],
            '1m': [
                {"symbol": "BTC/USDT", "type": "CRYPTO"},
                {"symbol": "ETH/USDT", "type": "CRYPTO"},
                {"symbol": "SOL/USDT", "type": "CRYPTO"},
                {"symbol": "XAUUSD", "type": "METAL"}
            ]
        }
        
        try:
            while self.running:
                start_time = datetime.now()
                
                # Heartbeat & Dashboard
                num_active = len(self.pm.active_positions)
                print(f"\n📡 [SCAN] {start_time.strftime('%H:%M:%S')} | Active Trades: {num_active} | Scanning Targets...")
                
                if num_active > 0:
                    pos_list = [f"{k[0]} ({k[1]})" for k in self.pm.active_positions.keys()]
                    print(f"   ∟ Current Positions: {pos_list}")

                tasks = []
                for tf, assets in targets.items():
                    for asset in assets:
                        tasks.append(self.scan_asset(asset['symbol'], asset['type'], tf=tf))
                
                await asyncio.gather(*tasks)
                
                # Dynamic Sleep
                elapsed = (datetime.now() - start_time).total_seconds()
                sleep_time = max(10, 45 - elapsed)
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n🛑 Session stopped by user.")
        finally:
            await self.provider.close()

if __name__ == "__main__":
    session = LiveDemoSession()
    asyncio.run(session.run_session())
