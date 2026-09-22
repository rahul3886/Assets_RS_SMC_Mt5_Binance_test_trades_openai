import requests
import json
from datetime import datetime

class DiscordAlerter:
    def __init__(self, webhook_url, extreme_webhook_url=None):
        self.webhook_url = webhook_url
        self.extreme_webhook_url = extreme_webhook_url or webhook_url

    def send_market_report(self, symbol, timeframe, data):
        """Sends the initial market situation report."""
        embed = {
            "title": f"🚀 Bot Started: {symbol} ({timeframe})",
            "color": 3447003,  # Blue
            "fields": [
                {"name": "Current Price", "value": f"${data['price']:,}", "inline": True},
                {"name": "RSI Value", "value": f"{data['rsi']}", "inline": True},
                {"name": "Market Trend", "value": data['trend'], "inline": True},
                {"name": "RSI Status", "value": data['rsi_status'], "inline": True},
            ],
            "footer": {"text": f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
        }
        self._send_payload({"embeds": [embed]}, self.webhook_url)

    def send_advanced_signal(self, symbol, timeframe, signal_type, strength_info, ctx, mtf_contexts):
        """Sends a rich signal alert with MTF data and strength breakdown."""
        color = 3066993 if signal_type == "BUY" else 15158332  # Green or Red
        icon = "🟢" if signal_type == "BUY" else "🔴"
        
        strength = strength_info['strength']
        breakdown_text = "\n".join([f"✅ {k}: +{v}%" for k, v in strength_info['breakdown'].items()])
        
        # Structure Formatting
        struct_text = ", ".join(ctx['structure']) if ctx['structure'] else "No distinct structure"
        div_text = f"🔥 {ctx['divergence']}" if ctx['divergence'] else "None detected"
        
        # MTF Formatting
        mtf_rows = []
        for tf, m_ctx in mtf_contexts.items():
            dir_icon = "↗️" if m_ctx['direction'] == "UP" else "↘️"
            mtf_rows.append(f"**{tf}**: RSI {m_ctx['rsi']} {dir_icon}")
        mtf_text = "\n".join(mtf_rows)

        # RSI Target Selection
        tp_rsi = strength_info.get('macro_tp') or strength_info.get('tp_rsi')
        target_text = f"🎯 **RSI {tp_rsi}** (Structural Level)" if tp_rsi else "Standard Momentum Exit"
        
        sl_price = strength_info.get('sl_price')
        sl_text = f"🛡️ **${sl_price:,.5f}** (Structural SL)" if sl_price else "Dynamic Bias SL"

        # Correlation Hybrid Tag
        cluster_info = strength_info.get('cluster_context', "")
        
        embed = {
            "title": f"{icon} {signal_type} SIGNAL [{strength}% STRENGTH]",
            "description": f"**Symbol:** {symbol} | **Timeframe:** {timeframe}\n**Institutional Focus:** {cluster_info if cluster_info else 'Standalone Setup'}",
            "color": color,
            "fields": [
                {"name": "📈 Market Geometry", "value": f"**Structure:** {struct_text}\n**Divergence:** {div_text}\n**RSI Slope:** {ctx['slope']}", "inline": False},
                {"name": "🎯 Take Profit Target", "value": target_text, "inline": True},
                {"name": "🛡️ Stop Loss", "value": sl_text, "inline": True},
                {"name": "🛡️ Confidence Breakdown", "value": breakdown_text if breakdown_text else "Raw Signal", "inline": True},
                {"name": "🌍 Multi-Timeframe Context", "value": mtf_text, "inline": False},
            ],
            "footer": {"text": f"Logic: RSI(14) | Generated at {datetime.now().strftime('%H:%M:%S')}"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        content = f"@here **{icon} {signal_type} at {symbol} ({timeframe}) - {strength}% Strength**"
        self._send_payload({"content": content, "embeds": [embed]}, self.webhook_url)

    def send_hunting_alert(self, symbol, timeframe, price, rsi_val, hunt_type, ctx):
        """Sends a high-urgency alert when price is hunting liquidity."""
        color = 10181046  # Purple
        icon = "🕵️‍♂️"
        
        dir_icon = "↗️" if ctx['direction'] == "UP" else "↘️"
        
        embed = {
            "title": f"🚨 LIQUIDITY HUNT IN PROGRESS: {hunt_type}",
            "description": f"**Symbol:** {symbol} | **Timeframe:** {timeframe}",
            "color": color,
            "fields": [
                {"name": "🔥 Status", "value": f"Price is **Hunting for Liquidity**.\nBe ready for the reversal action!", "inline": False},
                {"name": "📊 Metrics", "value": f"Price: **${price:,.5f}**\nRSI: **{rsi_val}** (Extreme)", "inline": True},
                {"name": "📈 Geometry", "value": f"Struct: {', '.join(ctx['structure'])}\nSlope: {ctx['slope']} {dir_icon}", "inline": True},
            ],
            "footer": {"text": f"Institutional Sniper Logic | {datetime.now().strftime('%H:%M:%S')}"}
        }
        
        content = f"⚠️ **{symbol} ({timeframe}) HUNTING LIQUIDITY - BE READY!**"
        self._send_payload({"content": content, "embeds": [embed]}, self.webhook_url)

    def send_zone_alert(self, symbol, timeframe, zone_type, rsi_val, ctx, mtf_contexts):
        """Sends an early warning when RSI enters an extreme zone."""
        color = 16761095  # Yellow/Orange for Warning
        icon = "⚠️"
        
        dir_icon = "↗️" if ctx['direction'] == "UP" else "↘️"
        zone_name = "BUY OPPORTUNITY" if zone_type == "BUY_ZONE" else "SELL WARNING"
        
        # Structure Formatting
        struct_text = ", ".join(ctx['structure']) if ctx['structure'] else "Normal"
        div_text = f"🔥 {ctx['divergence']}" if ctx['divergence'] else "None"
        
        # MTF Formatting
        mtf_rows = []
        for tf, m_ctx in mtf_contexts.items():
            m_dir_icon = "↗️" if m_ctx['direction'] == "UP" else "↘️"
            mtf_rows.append(f"**{tf}**: RSI {m_ctx['rsi']} {m_dir_icon}")
        mtf_text = "\n".join(mtf_rows)

        embed = {
            "title": f"{icon} EXTREME ZONE ENTRY: {zone_name}",
            "description": f"**Symbol:** {symbol} | **Timeframe:** {timeframe}",
            "color": color,
            "fields": [
                {"name": "📊 Zone Status", "value": f"Current RSI: **{rsi_val}**\nSlope: {ctx['slope']} {dir_icon}", "inline": True},
                {"name": "📈 Geometry", "value": f"Struct: {struct_text}\nDiv: {div_text}", "inline": True},
                {"name": "🌍 MTF Context", "value": mtf_text, "inline": False},
            ],
            "footer": {"text": f"Early Warning System | {datetime.now().strftime('%H:%M:%S')}"}
        }
        
        content = f"**{icon} {symbol} ({timeframe}) Entering {zone_name} Zone**"
        # ROUTE TO EXTREME WEBHOOK
        self._send_payload({"content": content, "embeds": [embed]}, self.extreme_webhook_url)

    def send_trailing_update(self, symbol, status, new_sl, current_price):
        """Sends an update when the Trailing Engine protects capital or locks profit."""
        color = 3447003 # Blue
        icon = "🛡️" if "BREAKEVEN" in status else "📈"
        
        embed = {
            "title": f"{icon} TRAILING UPDATE: {symbol}",
            "description": f"**Status:** {status}",
            "color": color,
            "fields": [
                {"name": "Current Price", "value": f"**${current_price:,.5f}**", "inline": True},
                {"name": "New Stop Loss", "value": f"**${new_sl:,.5f}**" if new_sl else "N/A", "inline": True},
            ],
            "footer": {"text": f"Dynamic Exit Architecture | {datetime.now().strftime('%H:%M:%S')}"}
        }
        
        content = f"**{icon} {symbol} Dynamic Exit Update: {status}**"
        self._send_payload({"content": content, "embeds": [embed]}, self.webhook_url)

    def _send_payload(self, payload, webhook_url):
        try:
            response = requests.post(
                webhook_url, 
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error sending to Discord: {e}")
