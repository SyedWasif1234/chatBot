"""
ESP32 Telegram Chatbot — Natural Language + Commands
-----------------------------------------------------
Users can type naturally OR use slash commands.

Natural language examples:
    "turn on relay 1"         "switch off the fan"
    "turn on the light"       "what's the temperature?"
    "read sensors"            "what's the status?"
    "turn off everything"     "relay 2 on"

Slash commands also work:
    /start  /help  /on 2  /off 3  /status  /sensors  /temp  /humidity

Usage:
    python telegram_bot.py

Requirements:
    pip install -r requirements.txt
"""

import asyncio
import logging
import os
import re

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

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
# Relay Labels — customise these for your hardware
# =========================================================

RELAY_LABELS = {
    1: "Relay 1",   # e.g. "Fan", "Light", "Pump", "Heater"
    2: "Relay 2",
    3: "Relay 3",
    4: "Relay 4",
}

# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.WARNING,
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
        label = RELAY_LABELS.get(i, f"Relay {i}")
        state = "ON " if s else "OFF"
        bars.append(f"{icon} {label}: *{state}*")
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


def natural_language_parse(text: str) -> dict:
    """
    Parse a plain-text message into an intent dict.

    Returns one of:
        {"intent": "relay",   "channel": 1-4, "state": "on"|"off"}
        {"intent": "relay_all", "state": "on"|"off"}
        {"intent": "sensors"}
        {"intent": "temperature"}
        {"intent": "humidity"}
        {"intent": "status"}
        {"intent": "help"}
        {"intent": "unknown"}
    """
    t = text.lower().strip()

    # --- ON / OFF keywords ---
    on_words  = ["turn on", "switch on", "enable", "activate",
                 "start", "power on", " on "]
    off_words = ["turn off", "switch off", "disable", "deactivate",
                 "stop", "power off", " off "]

    wants_on  = any(w in t for w in on_words) or t.endswith(" on")
    wants_off = any(w in t for w in off_words) or t.endswith(" off")

    # --- All relays ---
    if any(w in t for w in ["everything", "all relay", "all off", "all on"]):
        if wants_on:
            return {"intent": "relay_all", "state": "on"}
        if wants_off:
            return {"intent": "relay_all", "state": "off"}

    # --- Channel number ---
    channel_map = {
        "one": 1, "1": 1, "first": 1,
        "two": 2, "2": 2, "second": 2,
        "three": 3, "3": 3, "third": 3,
        "four": 4, "4": 4, "fourth": 4,
    }

    # Also match relay labels (e.g. "Fan" if user customised them)
    label_map = {v.lower(): k for k, v in RELAY_LABELS.items()}

    found_channel = None

    # Match "relay X" pattern first
    relay_num = re.search(r"relay\s*([1-4]|one|two|three|four)", t)
    if relay_num:
        found_channel = channel_map.get(relay_num.group(1))

    # Match bare numbers / words
    if not found_channel:
        for word, ch in channel_map.items():
            if re.search(rf"\b{word}\b", t):
                found_channel = ch
                break

    # Match label names
    if not found_channel:
        for label, ch in label_map.items():
            if label in t:
                found_channel = ch
                break

    if found_channel:
        if wants_on:
            return {"intent": "relay", "channel": found_channel, "state": "on"}
        if wants_off:
            return {"intent": "relay", "channel": found_channel, "state": "off"}
        # Channel mentioned but no on/off — ask for status
        return {"intent": "status"}

    # --- Sensors ---
    if any(w in t for w in ["sensor", "reading", "read", "data"]):
        return {"intent": "sensors"}

    if any(w in t for w in ["temperature", "temp", "hot", "cold", "heat"]):
        return {"intent": "temperature"}

    if any(w in t for w in ["humidity", "humid", "moisture", "wet"]):
        return {"intent": "humidity"}

    # --- Status ---
    if any(w in t for w in ["status", "state", "what's on", "whats on",
                             "which relay", "relay status"]):
        return {"intent": "status"}

    # --- Help ---
    if any(w in t for w in ["help", "command", "what can you do", "how to"]):
        return {"intent": "help"}

    return {"intent": "unknown"}


async def handle_relay(update: Update, channel: int, state: str):
    label = RELAY_LABELS.get(channel, f"Relay {channel}")
    if ctrl.toggle_relay(channel, state):
        icon = "🟢" if state == "on" else "🔴"
        await update.message.reply_markdown(f"{icon} *{label} turned {state.upper()}*")
    else:
        await update.message.reply_text(f"❌ Could not reach ESP32. Is it powered on and on the same WiFi?")

# =========================================================
# Slash Command Handlers
# =========================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    connected   = ctrl.test_connection()
    status_text = "✅ *Connected* to ESP32" if connected else "❌ *Cannot reach ESP32* — check WiFi"
    name = update.effective_user.first_name or "there"
    await update.message.reply_markdown(
        f"👋 Hey *{name}*! I'm your ESP32 controller bot.\n\n"
        f"{status_text}\n"
        f"📡 Device: `{ctrl.base_url}`\n\n"
        f"Just *talk to me naturally* — for example:\n"
        f'_"Turn on relay 1"_\n'
        f'_"What\'s the temperature?"_\n'
        f'_"Show me the status"_\n\n'
        f"Or use /help for all commands."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    labels = "\n".join(
        f"  • Relay {k}: *{v}*" for k, v in RELAY_LABELS.items()
    )
    await update.message.reply_markdown(
        "*📋 How to talk to me*\n\n"
        "Just type naturally! Examples:\n"
        '_"Turn on relay 1"_\n'
        '_"Switch off relay 3"_\n'
        '_"What\'s the temperature?"_\n'
        '_"Show relay status"_\n'
        '_"Read sensors"_\n\n'
        "Or use slash commands:\n"
        "`/on <1-4>` `/off <1-4>` `/status`\n"
        "`/temp` `/humidity` `/sensors`\n\n"
        f"*Relay Labels*\n{labels}"
    )


async def cmd_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ch = parse_channel(context.args)
    if ch is None:
        await update.message.reply_text("⚠️ Usage: /on <1-4>\nExample: /on 2")
        return
    await handle_relay(update, ch, "on")


async def cmd_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ch = parse_channel(context.args)
    if ch is None:
        await update.message.reply_text("⚠️ Usage: /off <1-4>\nExample: /off 2")
        return
    await handle_relay(update, ch, "off")


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
        await update.message.reply_markdown(f"⚙️ Current ESP32 URL: `{ctrl.base_url}`")
        return
    ctrl = ESP32API(context.args[0].strip())
    connected = ctrl.test_connection()
    await update.message.reply_markdown(
        f"✅ ESP32 updated — *{'reachable' if connected else 'not responding'}*"
    )

# =========================================================
# Natural Language Chat Handler
# =========================================================

async def cmd_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages as natural language commands."""
    text   = update.message.text or ""
    result = natural_language_parse(text)
    intent = result["intent"]

    if intent == "relay":
        await handle_relay(update, result["channel"], result["state"])

    elif intent == "relay_all":
        state   = result["state"]
        success = all(ctrl.toggle_relay(ch, state) for ch in range(1, 5))
        icon    = "🟢" if state == "on" else "🔴"
        if success:
            await update.message.reply_markdown(f"{icon} *All relays turned {state.upper()}*")
        else:
            await update.message.reply_text("❌ Some relays failed. Check ESP32 connection.")

    elif intent == "sensors":
        await cmd_sensors(update, context)

    elif intent == "temperature":
        await cmd_temp(update, context)

    elif intent == "humidity":
        await cmd_humidity(update, context)

    elif intent == "status":
        await cmd_status(update, context)

    elif intent == "help":
        await cmd_help(update, context)

    else:
        await update.message.reply_markdown(
            "🤔 I didn't quite get that. Try something like:\n"
            '_"Turn on relay 1"_\n'
            '_"What\'s the temperature?"_\n'
            '_"Show relay status"_\n\n'
            "Or type /help for all commands."
        )

# =========================================================
# Main
# =========================================================

async def main():
    print(f"[Bot] Starting — ESP32 at {ctrl.base_url}")
    print(f"[Bot] Connecting to Telegram...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Slash commands
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("on",       cmd_on))
    app.add_handler(CommandHandler("off",      cmd_off))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("temp",     cmd_temp))
    app.add_handler(CommandHandler("humidity", cmd_humidity))
    app.add_handler(CommandHandler("sensors",  cmd_sensors))
    app.add_handler(CommandHandler("ip",       cmd_ip))

    # Natural language — catch all plain text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_chat))

    print("[Bot] Running! Open Telegram and just talk to it.")
    print("      Press Ctrl+C to stop.\n")

    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Bot] Stopped.")
