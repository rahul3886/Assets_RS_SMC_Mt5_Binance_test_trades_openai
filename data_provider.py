import ccxt.async_support as ccxt
import pandas as pd
import MetaTrader5 as mt5
import yfinance as yf
from datetime import datetime
import asyncio
import concurrent.futures

class AsyncDataProvider:
    def __init__(self, exchange_id='binance'):
        # Initialize CCXT Async
        try:
            exchange_class = getattr(ccxt, exchange_id)
            self.exchange = exchange_class({
                'enableRateLimit': True,
            })
        except Exception as e:
            print(f"Error initializing CCXT ({exchange_id}): {e}")
            self.exchange = None

        # Initialize MT5
        self.mt5_initialized = False
        try:
            if not mt5.initialize():
                print(f"MT5 initialization failed during async setup.")
            else:
                self.mt5_initialized = True
        except Exception as e:
            print(f"MT5 could not be initialized: {e}")

        # Thread pool for synchronous calls (MT5/YFinance)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    async def fetch_crypto_ohlcv(self, symbol, timeframe='1m', limit=100):
        """Fetches OHLCV data for Crypto via CCXT Async."""
        if not self.exchange:
            return None
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            # Silencing common symbol errors for the scanner
            if "market symbol" not in str(e).lower():
                print(f"Async CCXT Error ({symbol}): {e}")
            return None

    async def fetch_mt5_ohlcv(self, symbol, timeframe='1m', limit=100):
        """Fetches OHLCV data for Forex/Commodities via MT5 (using thread pool)."""
        if not self.mt5_initialized:
            return await self.fetch_yfinance_ohlcv(symbol, timeframe, limit)

        loop = asyncio.get_event_loop()
        try:
            rates = await loop.run_in_executor(self.executor, self._sync_fetch_mt5, symbol, timeframe, limit)
            if rates is None or len(rates) == 0:
                return await self.fetch_yfinance_ohlcv(symbol, timeframe, limit)
                
            df = pd.DataFrame(rates)
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            df.rename(columns={'tick_volume': 'volume'}, inplace=True)
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            return await self.fetch_yfinance_ohlcv(symbol, timeframe, limit)

    def _sync_fetch_mt5(self, symbol, timeframe, limit):
        """Synchronous wrapper for MT5 library calls."""
        tf_map = {
            '1m': mt5.TIMEFRAME_M1, '3m': mt5.TIMEFRAME_M3, 
            '5m': mt5.TIMEFRAME_M5, '15m': mt5.TIMEFRAME_M15
        }
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_M1)
        return mt5.copy_rates_from_pos(symbol, mt5_tf, 0, limit)

    async def fetch_yfinance_ohlcv(self, symbol, timeframe='1m', limit=100):
        """Fallback data provider using Yahoo Finance (using thread pool)."""
        loop = asyncio.get_event_loop()
        try:
            # print(f"[DEBUG] Fetching YF for {symbol}...")
            df = await loop.run_in_executor(self.executor, self._sync_fetch_yfinance, symbol, timeframe, limit)
            if df is None or df.empty:
                print(f"[WARN] YF failed for {symbol}")
            return df
        except Exception as e:
            print(f"[ERR] YF Exception for {symbol}: {e}")
            return None

    def _sync_fetch_yfinance(self, symbol, timeframe, limit):
        """Synchronous wrapper for yfinance calls."""
        yf_symbol = symbol
        mapping = {
            "XAUUSD": "GC=F", "XAGUSD": "SI=F", "EURUSD": "EURUSD=X",
            "USDJPY": "USDJPY=X", "GBPUSD": "GBPUSD=X", "CADJPY": "CADJPY=X",
            "GBPJPY": "GBPJPY=X", "USDCHF": "USDCHF=X", "EURAUD": "EURAUD=X",
            "XAUEUR": "EUR=X"
        }
        yf_symbol = mapping.get(symbol, symbol)
        tf_map = {'1m': '1m', '3m': '2m', '5m': '5m'}
        yf_tf = tf_map.get(timeframe, '1m')
        
        data = yf.download(yf_symbol, period='1d', interval=yf_tf, progress=False)
        if data.empty: return None
        
        # Handle recent yfinance multi-index columns
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        df = data.reset_index()
        df.columns = [str(c).lower() for c in df.columns] # Ensure string columns
        
        if 'datetime' in df.columns: df.rename(columns={'datetime': 'timestamp'}, inplace=True)
        elif 'date' in df.columns: df.rename(columns={'date': 'timestamp'}, inplace=True)
        
        # Cleanup column indices if exists
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        # Add volume if missing (yfinance sometimes omits for FX)
        if 'volume' not in df.columns:
            df['volume'] = 0
            
        return df[required_cols].tail(limit)

    async def close(self):
        if self.exchange:
            await self.exchange.close()
        if self.mt5_initialized:
            mt5.shutdown()
        self.executor.shutdown()
