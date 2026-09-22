import config
from discord_utils import DiscordAlerter

print("Testing Discord Webhooks...")
alerter = DiscordAlerter(config.DISCORD_WEBHOOK_URL, config.DISCORD_EXTREME_WEBHOOK_URL)

try:
    print(f"Sending to Main Webhook: {config.DISCORD_WEBHOOK_URL[:20]}...")
    alerter._send_payload({"content": "🧪 **Test Message**: Verification from the Bot Debugger."}, config.DISCORD_WEBHOOK_URL)
    print("✅ Main Webhook Sent Successfully.")
except Exception as e:
    print(f"❌ Main Webhook Failed: {e}")

try:
    print(f"Sending to Extreme Webhook: {config.DISCORD_EXTREME_WEBHOOK_URL[:20]}...")
    alerter._send_payload({"content": "🧪 **Test Message**: Extreme Alert Channel Verification."}, config.DISCORD_EXTREME_WEBHOOK_URL)
    print("✅ Extreme Webhook Sent Successfully.")
except Exception as e:
    print(f"❌ Extreme Webhook Failed: {e}")
