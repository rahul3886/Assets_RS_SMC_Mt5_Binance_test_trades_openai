import os

# --- Discord Settings ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1469679382699446464/DSzz6hPC0eEAQOr8SjBLrf_S3emn-XVm5i2p90MkEMtT1cga_PZf0D071FeMh6ETRViN"
DISCORD_EXTREME_WEBHOOK_URL = "https://discord.com/api/webhooks/1469750588047757405/wzOcZu5FFNd0qb_PQdRM_la1Ayur5ZdZJarcoW0FM6lajnk7yM-FULZJIYUdNzTTZoKl"

# --- Watchlists ---
CRYPTO_WATCHLIST = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "TRUMP/USDT", 
    "SHIB/USDT", "PUMP/USDT", "BNB/USDT", 
    "LTC/USDT", "ATOM/USDT"
]

FOREX_WATCHLIST = [
    "EURUSD", "USDJPY", "GBPUSD", "CADJPY", "GBPJPY", "USDCHF", "EURAUD"
]

COMMODITIES_WATCHLIST = [
    "XAUUSD", "XAGUSD", "XAUEUR"
]

# --- Exchange Settings ---
EXCHANGE = "binance"
TIMEFRAMES = ["1m", "3m", "5m", "15m"]

# --- Strategy Parameters ---
RSI_LENGTH = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MIN_SIGNAL_STRENGTH = 50  # Only send signals >= 50% to Discord

# --- General Settings ---
POLLING_INTERVAL = 30  # Seconds between full market scans
SCAN_TIMEOUT = 10      # Max seconds for an async scan batch
