"""
ESP32 Telegram Bot — Polling Mode (Demo-ready)
-----------------------------------------------
Run this on your laptop during a demo.
Both this script and the ESP32 must be on the same WiFi network.

Usage:
    python telegram_bot.py

Requirements:
    pip install -r requirements.txt

Bot Commands:
    /start          - Welcome + connection test
    /help           - List all commands
    /on <1-4>       - Turn on relay  (e.g. /on 2)
    /off <1-4>      - Turn off relay (e.g. /off 3)
    /status         - Show all 4 relay states
    /temp           - Read temperature
    /humidity       - Read humidity
    /sensors        - Read temperature + humidity
    /ip <url>       - Change ESP32 IP/URL at runtime
"""

import asyncio
import logging
import os

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from esp32_api import ESP32API

# =========================================================
# Load .env in local development
# =========================================================
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =========================================================
# Configuration
# =========================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8612598583:AAF-UbFiFlPT9U8XC3JkJ8tpFJU3rT8Aw_A")
ESP32_URL = os.getenv("ESP32_URL", "http://10.24.66.145")

# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.WARNING,      # keep output clean during demo
)

# =========================================================
# ESP32 client
# =========================================================

ctrl = ESP32API(ESP32_URL)

# =========================================================
# Helpers
# =========================================================

def relay_bar(states: list) -> str:
    bars = []
    for i, s in enumerate(states, 1):
        icon  = "🟢" if s else "🔴"
        label = "ON " if s else "OFF"
        bars.append(f"{icon} Relay {i}: *{label}*")
    return "\n".join(bars)


def parse_channel(args: tuple) -> int | None:
    if not args:
        return None
    try:
        ch = int(args[0])
        if 1 <= ch <= 4:
            return ch
    except ValueError:
        pass
    return None

# =========================================================
# Command Handlers
# =========================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    connected   = ctrl.test_connection()
    status_text = "✅ *Connected* to ESP32" if connected else "❌ *Cannot reach ESP32* — check WiFi"
    await update.message.reply_markdown(
        f"👋 *ESP32 IoT Controller Bot*\n\n"
        f"{status_text}\n"
        f"📡 Device: `{ctrl.base_url}`\n\n"
        f"Use /help to see all commands."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown(
        "*📋 Available Commands*\n\n"
        "🔌 *Relay Control*\n"
        "`/on <1-4>` — Turn on a relay\n"
        "`/off <1-4>` — Turn off a relay\n"
        "`/status` — Show all relay states\n\n"
        "🌡️ *Sensors*\n"
        "`/temp` — Read temperature\n"
        "`/humidity` — Read humidity\n"
        "`/sensors` — Read both\n\n"
        "⚙️ *Settings*\n"
        "`/ip <address>` — Change ESP32 URL\n\n"
        "_Example: /on 1   /off 3   /sensors_"
    )


async def cmd_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ch = parse_channel(context.args)
    if ch is None:
        await update.message.reply_text("⚠️ Usage: /on <1-4>\nExample: /on 2")
        return
    if ctrl.toggle_relay(ch, "on"):
        await update.message.reply_markdown(f"🟢 *Relay {ch} turned ON*")
    else:
        await update.message.reply_text(f"❌ Failed to reach ESP32. Check WiFi connection.")


async def cmd_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ch = parse_channel(context.args)
    if ch is None:
        await update.message.reply_text("⚠️ Usage: /off <1-4>\nExample: /off 2")
        return
    if ctrl.toggle_relay(ch, "off"):
        await update.message.reply_markdown(f"🔴 *Relay {ch} turned OFF*")
    else:
        await update.message.reply_text(f"❌ Failed to reach ESP32. Check WiFi connection.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = ctrl.get_status()
    if data:
        await update.message.reply_markdown(f"📊 *Relay Status*\n\n{relay_bar(data['relay'])}")
    else:
        await update.message.reply_text("❌ Could not reach ESP32. Check WiFi.")


async def cmd_temp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = ctrl.get_data()
    if data:
        await update.message.reply_markdown(f"🌡️ *Temperature*: `{data['temperature']:.1f} °C`")
    else:
        await update.message.reply_text("❌ Could not read temperature.")


async def cmd_humidity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = ctrl.get_data()
    if data:
        await update.message.reply_markdown(f"💧 *Humidity*: `{data['humidity']:.1f} %`")
    else:
        await update.message.reply_text("❌ Could not read humidity.")


async def cmd_sensors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = ctrl.get_data()
    if data:
        await update.message.reply_markdown(
            f"🌡️ *Temperature*: `{data['temperature']:.1f} °C`\n"
            f"💧 *Humidity*:    `{data['humidity']:.1f} %`"
        )
    else:
        await update.message.reply_text("❌ Could not read sensors. Check WiFi.")


async def cmd_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ctrl
    if not context.args:
        await update.message.reply_markdown(
            f"⚙️ Current ESP32 URL: `{ctrl.base_url}`\n"
            f"Usage: `/ip 192.168.1.100`"
        )
        return
    ctrl = ESP32API(context.args[0].strip())
    connected = ctrl.test_connection()
    if connected:
        await update.message.reply_markdown(f"✅ ESP32 updated — *reachable!*")
    else:
        await update.message.reply_markdown(f"⚠️ Updated but ESP32 *not responding*. Check address.")

# =========================================================
# Main
# =========================================================

async def main():
    print(f"✅ Bot starting — ESP32 at {ctrl.base_url}")
    print(f"✅ Connecting to Telegram...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("on",       cmd_on))
    app.add_handler(CommandHandler("off",      cmd_off))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("temp",     cmd_temp))
    app.add_handler(CommandHandler("humidity", cmd_humidity))
    app.add_handler(CommandHandler("sensors",  cmd_sensors))
    app.add_handler(CommandHandler("ip",       cmd_ip))

    print("✅ Bot is running! Open Telegram and send /start")
    print("   Press Ctrl+C to stop.\n")

    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()   # run forever until Ctrl+C
        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped.")
