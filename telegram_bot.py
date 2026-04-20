"""
ESP32 Telegram Bot — Webhook Mode (Render-ready)
-------------------------------------------------
Runs as a Flask web service. Telegram pushes updates to /webhook.

Environment variables (set on Render dashboard):
    TELEGRAM_BOT_TOKEN  — your bot token from @BotFather
    ESP32_URL           — full URL to ESP32 (e.g. https://xxxx.trycloudflare.com)
    WEBHOOK_URL         — your Render service URL (e.g. https://chatbot-xyz.onrender.com)
    PORT                — auto-set by Render (default 10000)

Local development:
    Copy .env.example → .env, fill in values, then:
        pip install python-dotenv
        python telegram_bot.py
"""

import asyncio
import logging
import os

from flask import Flask, Response, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from esp32_api import ESP32API

# =========================================================
# Load .env in local development (ignored on Render)
# =========================================================
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =========================================================
# Configuration — all from environment variables
# =========================================================

BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
ESP32_URL   = os.getenv("ESP32_URL", "http://10.24.66.145")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")           # e.g. https://chatbot-xyz.onrender.com
PORT        = int(os.getenv("PORT", 10000))

# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =========================================================
# ESP32 API client
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
    status_text = "✅ *Connected* to ESP32" if connected else "❌ *Cannot reach ESP32* — check tunnel or power"
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
        "`/ip <address>` — Change ESP32 URL at runtime\n\n"
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
        await update.message.reply_text(f"❌ Failed to turn on Relay {ch}. Is the tunnel running?")


async def cmd_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ch = parse_channel(context.args)
    if ch is None:
        await update.message.reply_text("⚠️ Usage: /off <1-4>\nExample: /off 2")
        return
    if ctrl.toggle_relay(ch, "off"):
        await update.message.reply_markdown(f"🔴 *Relay {ch} turned OFF*")
    else:
        await update.message.reply_text(f"❌ Failed to turn off Relay {ch}. Is the tunnel running?")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = ctrl.get_status()
    if data:
        await update.message.reply_markdown(f"📊 *Relay Status*\n\n{relay_bar(data['relay'])}")
    else:
        await update.message.reply_text("❌ Could not get relay status. Check tunnel/ESP32 connection.")


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
        await update.message.reply_text("❌ Could not read sensors. Is the tunnel running?")


async def cmd_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ctrl
    if not context.args:
        await update.message.reply_markdown(
            f"⚙️ Current ESP32 URL: `{ctrl.base_url}`\n"
            f"Usage: `/ip https://xxxx.trycloudflare.com`"
        )
        return
    new_url = context.args[0].strip()
    ctrl    = ESP32API(new_url)
    connected = ctrl.test_connection()
    if connected:
        await update.message.reply_markdown(f"✅ ESP32 URL updated to `{new_url}` — *reachable*!")
    else:
        await update.message.reply_markdown(
            f"⚠️ URL updated to `{new_url}` but ESP32 is *not responding*.\n"
            "Check the tunnel is running."
        )

# =========================================================
# Build PTB Application & register handlers
# =========================================================

ptb_app = ApplicationBuilder().token(BOT_TOKEN).build()

ptb_app.add_handler(CommandHandler("start",    cmd_start))
ptb_app.add_handler(CommandHandler("help",     cmd_help))
ptb_app.add_handler(CommandHandler("on",       cmd_on))
ptb_app.add_handler(CommandHandler("off",      cmd_off))
ptb_app.add_handler(CommandHandler("status",   cmd_status))
ptb_app.add_handler(CommandHandler("temp",     cmd_temp))
ptb_app.add_handler(CommandHandler("humidity", cmd_humidity))
ptb_app.add_handler(CommandHandler("sensors",  cmd_sensors))
ptb_app.add_handler(CommandHandler("ip",       cmd_ip))

# Initialize PTB and register webhook at startup
_init_loop = asyncio.new_event_loop()
_init_loop.run_until_complete(ptb_app.initialize())

if WEBHOOK_URL:
    _webhook_full = f"{WEBHOOK_URL.rstrip('/')}/webhook"
    _init_loop.run_until_complete(ptb_app.bot.set_webhook(_webhook_full))
    logger.info(f"Webhook registered: {_webhook_full}")
else:
    logger.warning("WEBHOOK_URL not set — webhook not registered with Telegram.")

_init_loop.close()

# =========================================================
# Flask App
# =========================================================

flask_app = Flask(__name__)


@flask_app.route("/")
def health():
    """Health check — keeps Render service alive."""
    return "ESP32 Bot is running! 🤖", 200


@flask_app.route("/webhook", methods=["POST"])
def webhook():
    """Receive Telegram updates and dispatch to handlers."""
    data   = request.get_json(force=True)
    update = Update.de_json(data, ptb_app.bot)
    loop   = asyncio.new_event_loop()
    loop.run_until_complete(ptb_app.process_update(update))
    loop.close()
    return Response(status=200)


# =========================================================
# Entry Point (local dev)
# =========================================================

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("\n❌ ERROR: TELEGRAM_BOT_TOKEN not set. Copy .env.example → .env and fill in values.\n")
    else:
        logger.info(f"Starting Flask on port {PORT}")
        flask_app.run(host="0.0.0.0", port=PORT, debug=False)
