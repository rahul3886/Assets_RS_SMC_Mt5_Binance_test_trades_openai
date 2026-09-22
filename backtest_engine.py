import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import strategy
import smc_logic
import json
import os

class BacktestEngine:
    """
    Backtesting engine for validating strategy performance on historical data.
    """
    
    def __init__(self, initial_capital=10000, risk_per_trade=100):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.trades = []
        self.equity_curve = []
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        
    def simulate_trade(self, df, entry_idx, signal, info, ctx):
        """
        Simulates a single trade outcome using subsequent price action.
        
        Returns:
            dict: Trade outcome with PnL, exit reason, duration
        """
        if entry_idx >= len(df) - 1:
            return None  # Not enough data to simulate
            
        entry_price = df['close'].iloc[entry_idx]
        sl_price = info.get('sl_price')
        tp_rsi = info.get('tp_rsi')
        
        # Calculate TP price from RSI target
        tp_price = self._calculate_tp_price(df, entry_idx, signal, tp_rsi)
        
        if not sl_price or not tp_price:
            return None  # Invalid SL/TP
            
        # Validate SL/TP positions
        if "BUY" in signal:
            if sl_price >= entry_price or tp_price <= entry_price:
                return None  # Invalid levels
        elif "SELL" in signal:
            if sl_price <= entry_price or tp_price >= entry_price:
                return None
                
        # Scan forward to find SL or TP hit
        max_bars_forward = min(100, len(df) - entry_idx - 1)  # Max 100 candles
        
        for i in range(1, max_bars_forward + 1):
            idx = entry_idx + i
            candle_high = df['high'].iloc[idx]
            candle_low = df['low'].iloc[idx]
            candle_close = df['close'].iloc[idx]
            
            if "BUY" in signal:
                # Check SL hit first (conservative)
                if candle_low <= sl_price:
                    pnl = sl_price - entry_price
                    pnl_pct = (pnl / entry_price) * 100
                    return {
                        "outcome": "LOSS",
                        "exit_price": sl_price,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "exit_reason": "SL_HIT",
                        "bars_held": i,
                        "risk_reward": abs((tp_price - entry_price) / (entry_price - sl_price))
                    }
                # Check TP hit
                if candle_high >= tp_price:
                    pnl = tp_price - entry_price
                    pnl_pct = (pnl / entry_price) * 100
                    return {
                        "outcome": "WIN",
                        "exit_price": tp_price,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "exit_reason": "TP_HIT",
                        "bars_held": i,
                        "risk_reward": abs((tp_price - entry_price) / (entry_price - sl_price))
                    }
                    
            elif "SELL" in signal:
                # Check SL hit first
                if candle_high >= sl_price:
                    pnl = entry_price - sl_price
                    pnl_pct = (pnl / entry_price) * 100
                    return {
                        "outcome": "LOSS",
                        "exit_price": sl_price,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "exit_reason": "SL_HIT",
                        "bars_held": i,
                        "risk_reward": abs((entry_price - tp_price) / (sl_price - entry_price))
                    }
                # Check TP hit
                if candle_low <= tp_price:
                    pnl = entry_price - tp_price
                    pnl_pct = (pnl / entry_price) * 100
                    return {
                        "outcome": "WIN",
                        "exit_price": tp_price,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "exit_reason": "TP_HIT",
                        "bars_held": i,
                        "risk_reward": abs((entry_price - tp_price) / (sl_price - entry_price))
                    }
        
        # Trade still open after max bars - close at market
        final_price = df['close'].iloc[entry_idx + max_bars_forward]
        if "BUY" in signal:
            pnl = final_price - entry_price
        else:
            pnl = entry_price - final_price
            
        pnl_pct = (pnl / entry_price) * 100
        
        return {
            "outcome": "WIN" if pnl > 0 else "LOSS",
            "exit_price": final_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "exit_reason": "TIMEOUT",
            "bars_held": max_bars_forward,
            "risk_reward": 0
        }
    
    def _calculate_tp_price(self, df, entry_idx, signal, tp_rsi):
        """
        Converts RSI target to price level.
        Simple approximation: find nearest price where RSI hits target.
        """
        if not tp_rsi:
            # Default TP: 2x risk
            entry_price = df['close'].iloc[entry_idx]
            if "BUY" in signal:
                return entry_price * 1.02  # 2% TP
            else:
                return entry_price * 0.98
                
        # Use simplified approach: 2R target
        entry_price = df['close'].iloc[entry_idx]
        if "BUY" in signal:
            return entry_price * 1.015  # 1.5% TP for BUY
        else:
            return entry_price * 0.985  # 1.5% TP for SELL
    
    def run_backtest(self, df, timeframe="1m", min_strength=50, use_optimized=True, prepared_data=None):
        """
        Runs backtest on historical dataframe.
        Args:
            df: Historical OHLCV dataframe
            use_optimized: Use O(N) optimized strategy check (Upgrade #3)
            prepared_data: Optional tuple (df, all_pivots, pivot_params, pivots_h, pivots_l) to skip pre-calculation
        """
        print(f"\n[BACKTEST] Running on {len(df)} candles, timeframe={timeframe}, min_strength={min_strength}%")
        
        if len(df) < 100:
            return {"error": "Insufficient data"}
            
        signals_generated = 0
        signals_traded = 0
        
        # Pre-calculate Data (Upgrade #3 Optimization)
        if use_optimized:
            if prepared_data:
                df, all_pivots, pivot_params, pivots_h, pivots_l = prepared_data
            else:
                print("[BACKTEST] Pre-calculating indicators (Optimized Mode)...")
                df, all_pivots, pivot_params, pivots_h, pivots_l = strategy.prepare_data(df)
        
        # Scan through historical data
        for i in range(200, len(df) - 100):  
            
            if use_optimized:
                # O(1) Signal Check
                signal, info, ctx = strategy.check_signals_optimized(df, i, all_pivots, pivot_params, pivots_h, pivots_l)
            else:
                # Legacy O(N) Check (Slow)
                historical_df = df.iloc[:i+1].copy()
                signal, info, ctx = strategy.check_signals_advanced(historical_df)
            
            if signal and signal not in ["NEUTRAL", None]:
                signals_generated += 1
                
                # Filter by strength
                if info['strength'] < min_strength:
                    continue
                    
                # Simulate this trade
                trade_result = self.simulate_trade(df, i, signal, info, ctx)
                
                if trade_result:
                    signals_traded += 1
                    
                    # Record trade
                    trade_record = {
                        "timestamp": df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                        "timeframe": timeframe,
                        "signal": signal,
                        "entry_price": df['close'].iloc[i],
                        "strength": info['strength'],
                        "smc_status": ctx.get('smc', {}).get('status', 'NEUTRAL'),
                        "session": ctx.get('smc', {}).get('session', {}).get('session', 'UNKNOWN'),
                        "rsi": ctx['rsi'],
                        **trade_result
                    }
                    
                    self.trades.append(trade_record)
                    
                    # Update equity
                    position_size = self.risk_per_trade  # Flat $100 per trade
                    if trade_result['outcome'] == "WIN":
                        profit = position_size * trade_result['risk_reward']
                    else:
                        profit = -position_size
                        
                    self.current_capital += profit
                    self.peak_capital = max(self.peak_capital, self.current_capital)
                    
                    self.equity_curve.append({
                        "timestamp": trade_record["timestamp"],
                        "equity": self.current_capital,
                        "trade_num": len(self.trades)
                    })
        
        # Calculate performance metrics
        results = self._calculate_metrics()
        results['signals_generated'] = signals_generated
        results['signals_traded'] = signals_traded
        results['timeframe'] = timeframe
        results['min_strength'] = min_strength
        
        return results
    
    def _calculate_metrics(self):
        """
        Calculates comprehensive performance metrics.
        """
        if not self.trades:
            return {"error": "No trades executed"}
            
        wins = [t for t in self.trades if t['outcome'] == "WIN"]
        losses = [t for t in self.trades if t['outcome'] == "LOSS"]
        
        total_trades = len(self.trades)
        win_count = len(wins)
        loss_count = len(losses)
        
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        
        gross_profit = sum(t['pnl_pct'] for t in wins)
        gross_loss = abs(sum(t['pnl_pct'] for t in losses))
        
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        avg_win = (sum(t['pnl_pct'] for t in wins) / len(wins)) if wins else 0
        avg_loss = (sum(t['pnl_pct'] for t in losses) / len(losses)) if losses else 0
        
        avg_rr = np.mean([t['risk_reward'] for t in self.trades if t['risk_reward'] > 0])
        
        max_drawdown = ((self.peak_capital - min([e['equity'] for e in self.equity_curve])) / self.peak_capital * 100) if self.equity_curve else 0
        
        total_return = ((self.current_capital - self.initial_capital) / self.initial_capital * 100)
        
        return {
            "total_trades": total_trades,
            "wins": win_count,
            "losses": loss_count,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_win_pct": round(avg_win, 2),
            "avg_loss_pct": round(avg_loss, 2),
            "avg_rr": round(avg_rr, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "total_return_pct": round(total_return, 2),
            "final_capital": round(self.current_capital, 2)
        }
    
    def export_results(self, filename="backtest_results.json", output_dir=None):
        """
        Exports backtest results to JSON file.
        If output_dir is provided, saves all trade details to a separate CSV.
        """
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.join(output_dir, filename)
            
            # Export detailed trade log to CSV for easier analysis
            if hasattr(self, 'trades') and self.trades:
                trades_df = pd.DataFrame(self.trades)
                csv_path = os.path.join(output_dir, "detailed_trades.csv")
                trades_df.to_csv(csv_path, index=False)
                print(f"[EXPORT] Detailed trades saved to {csv_path}")

        results = {
            "metrics": self.metrics if hasattr(self, 'metrics') else self._calculate_metrics(),
            "trades": self.trades,
            "equity_curve": self.equity_curve
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"[EXPORT] Results saved to {filename}")
        except Exception as e:
            print(f"[ERROR] Failed to save results: {e}")
        
    def print_summary(self, metrics):
        """
        Prints a summary of backtest results.
        """
        print("\n" + "="*60)
        print("BACKTEST RESULTS SUMMARY")
        print("="*60)
        print(f"Timeframe: {metrics.get('timeframe', 'N/A')}")
        print(f"Min Strength: {metrics.get('min_strength', 'N/A')}%")
        print(f"Signals Generated: {metrics.get('signals_generated', 'N/A')}")
        print(f"Signals Traded: {metrics.get('signals_traded', 'N/A')}")
        print("-"*60)
        print(f"Total Trades: {metrics['total_trades']}")
        print(f"Wins: {metrics['wins']} | Losses: {metrics['losses']}")
        print(f"Win Rate: {metrics['win_rate']}%")
        print(f"Profit Factor: {metrics['profit_factor']}")
        print(f"Avg Win: +{metrics['avg_win_pct']}% | Avg Loss: {metrics['avg_loss_pct']}%")
        print(f"Avg R:R: {metrics['avg_rr']}")
        print(f"Max Drawdown: {metrics['max_drawdown_pct']}%")
        print(f"Total Return: {metrics['total_return_pct']}%")
        print(f"Final Capital: ${metrics['final_capital']}")
        print("="*60)
