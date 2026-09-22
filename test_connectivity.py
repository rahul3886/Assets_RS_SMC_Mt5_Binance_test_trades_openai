import asyncio
from data_provider import AsyncDataProvider
import config

async def test_connectivity():
    print("--- Async Connectivity Test ---")
    provider = AsyncDataProvider(config.EXCHANGE)
    
    # 1. Test Crypto (CCXT Async)
    print("\nTesting Crypto (Binance/CCXT)...")
    df_eth = await provider.fetch_crypto_ohlcv("ETH/USDT", timeframe='1m', limit=5)
    if df_eth is not None and not df_eth.empty:
        print(f"✅ CCXT Connected. Latest ETH/USDT: {df_eth['close'].iloc[-1]}")
    else:
        print("❌ CCXT Failed to fetch data.")

    # 2. Test MT5
    print("\nTesting Forex/Gold (MT5)...")
    if provider.mt5_initialized:
        df_gold = await provider.fetch_mt5_ohlcv("XAUUSD", timeframe='1m', limit=5)
        if df_gold is not None and not df_gold.empty:
            print(f"✅ MT5 Connected. Latest XAUUSD: {df_gold['close'].iloc[-1]}")
        else:
            print("❌ MT5 connected but failed to fetch XAUUSD rates.")
    else:
        print("❌ MT5 not initialized (Make sure terminal is open).")

    # 3. Test YFinance Fallback
    print("\nTesting Parallel Fetch (Speed Test)...")
    start = asyncio.get_event_loop().time()
    tasks = [provider.fetch_crypto_ohlcv(s, '1m', 5) for s in config.CRYPTO_WATCHLIST[:3]]
    await asyncio.gather(*tasks)
    end = asyncio.get_event_loop().time()
    print(f"⚡ Parallel Fetch Test for 3 assets took {round(end - start, 2)}s.")

    await provider.close()

if __name__ == "__main__":
    asyncio.run(test_connectivity())
