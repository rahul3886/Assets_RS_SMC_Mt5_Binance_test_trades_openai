import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

def debug_mt5():
    print("Attempting to initialize MT5...")
    if not mt5.initialize():
        print(f"FAILED: {mt5.last_error()}")
        return
        
    print("SUCCESS: MT5 Initialized")
    print(f"Terminal Info: {mt5.terminal_info()}")
    print(f"Account: {mt5.account_info().login}")
    
    symbol = "EURUSD"
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 100)
    if rates is None:
        print(f"FAILED to fetch rates for {symbol}: {mt5.last_error()}")
    else:
        print(f"Fetched {len(rates)} bars for {symbol}")
        
    mt5.shutdown()
    print("MT5 Shutdown completed.")

if __name__ == "__main__":
    debug_mt5()
