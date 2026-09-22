import asyncio
from data_provider import AsyncDataProvider
import config

async def test_fetch():
    print("Initializing Provider...")
    provider = AsyncDataProvider(config.EXCHANGE)
    
    symbol = "USDJPY"
    print(f"\n--- Testing {symbol} (MT5/YF) ---")
    
    # Test MT5
    print("Fetching via MT5...")
    df_mt5 = await provider.fetch_mt5_ohlcv(symbol, "1m", 5)
    if df_mt5 is not None and not df_mt5.empty:
        print(f"✅ MT5 Success: {len(df_mt5)} rows. Last Close: {df_mt5['close'].iloc[-1]}")
    else:
        print("❌ MT5 Failed or Empty.")
        
    # Force Test YF (by temporarily breaking MT5 flag or calling directly if accessible)
    # create a new provider to force YF if MT5 failed above, but provider logic already falls back.
    # We can explicitly call the yfinance method.
    
    print("\nFetching via YFinance explicit call...")
    df_yf = await provider.fetch_yfinance_ohlcv(symbol, "1m", 5)
    if df_yf is not None and not df_yf.empty:
        print(f"✅ YF Success: {len(df_yf)} rows. Last Close: {df_yf['close'].iloc[-1]}")
    else:
        print("❌ YF Failed or Empty.")
        
    await provider.close()

if __name__ == "__main__":
    asyncio.run(test_fetch())
