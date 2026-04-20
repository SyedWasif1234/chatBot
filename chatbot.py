"""
ESP32 Local Chatbot — Natural Language + TTS
--------------------------------------------
A local voice/text chatbot that controls the ESP32 in natural language.
Type a command OR speak — the bot understands both and talks back.

Modes:
    1 → Text mode  (type commands, bot speaks + prints replies)
    2 → Voice mode (speak, bot speaks + prints replies)

Usage:
    python chatbot.py
    python chatbot.py 192.168.1.100      # with custom IP

Requirements:
    pip install pyttsx3 SpeechRecognition requests pyaudio

Commands (natural language — say or type):
    "turn on relay 1"           "switch off relay 3"
    "turn on everything"        "turn off all relays"
    "what's the temperature?"   "how humid is it?"
    "read sensors"              "relay status"
    "diagnose" / "health check" "help"      "exit"
"""

import re
import sys
import time

import pyttsx3
import requests

# ── optional microphone / STT ─────────────────────────────────────────────────
try:
    import speech_recognition as sr
    MIC_AVAILABLE = True
except ImportError:
    MIC_AVAILABLE = False

from esp32_api import ESP32API

# =========================================================
# Configuration
# =========================================================

DEFAULT_IP = "10.24.66.145"

RELAY_LABELS = {
    1: "Relay 1",
    2: "Relay 2",
    3: "Relay 3",
    4: "Relay 4",
}

# =========================================================
# TTS Engine
# =========================================================

def make_engine():
    engine = pyttsx3.init()
    engine.setProperty("rate", 155)
    engine.setProperty("volume", 1.0)
    # Pick a natural-sounding voice if available
    voices = engine.getProperty("voices")
    for v in voices:
        if "zira" in v.name.lower() or "david" in v.name.lower():
            engine.setProperty("voice", v.id)
            break
    return engine

# =========================================================
# Helpers
# =========================================================

def format_uptime(ms: int) -> str:
    s = ms // 1000; m = s // 60; h = m // 60; d = h // 24
    if d:  return f"{d} days, {h%24} hours"
    if h:  return f"{h} hours and {m%60} minutes"
    if m:  return f"{m} minutes"
    return f"{s} seconds"

def format_rssi(rssi: int) -> str:
    if rssi >= -50:  return f"excellent ({rssi} dBm)"
    if rssi >= -65:  return f"good ({rssi} dBm)"
    if rssi >= -80:  return f"fair ({rssi} dBm)"
    return           f"weak ({rssi} dBm)"

def natural_language_parse(text: str) -> dict:
    t = text.lower().strip()

    on_words  = ["turn on", "switch on", "enable", "activate", "power on", " on "]
    off_words = ["turn off", "switch off", "disable", "deactivate", "power off", " off "]

    wants_on  = any(w in t for w in on_words) or t.endswith(" on")
    wants_off = any(w in t for w in off_words) or t.endswith(" off")

    # All relays
    if any(w in t for w in ["everything", "all relay", "all off", "all on"]):
        if wants_on:  return {"intent": "relay_all", "state": "on"}
        if wants_off: return {"intent": "relay_all", "state": "off"}

    # Channel detection
    channel_map = {
        "one": 1, "1": 1, "first": 1,
        "two": 2, "2": 2, "second": 2,
        "three": 3, "3": 3, "third": 3,
        "four": 4, "4": 4, "fourth": 4,
    }
    label_map = {v.lower(): k for k, v in RELAY_LABELS.items()}

    found_channel = None
    relay_num = re.search(r"relay\s*([1-4]|one|two|three|four)", t)
    if relay_num:
        found_channel = channel_map.get(relay_num.group(1))
    if not found_channel:
        for word, ch in channel_map.items():
            if re.search(rf"\b{word}\b", t):
                found_channel = ch; break
    if not found_channel:
        for label, ch in label_map.items():
            if label in t:
                found_channel = ch; break

    if found_channel:
        if wants_on:  return {"intent": "relay", "channel": found_channel, "state": "on"}
        if wants_off: return {"intent": "relay", "channel": found_channel, "state": "off"}
        return {"intent": "status"}

    if any(w in t for w in ["sensor", "reading", "read"]):
        return {"intent": "sensors"}
    if any(w in t for w in ["temperature", "temp", "hot", "cold"]):
        return {"intent": "temperature"}
    if any(w in t for w in ["humidity", "humid", "moisture"]):
        return {"intent": "humidity"}
    if any(w in t for w in ["status", "state", "which relay"]):
        return {"intent": "status"}
    if any(w in t for w in ["diagnose", "diagnosis", "health", "health check", "check device"]):
        return {"intent": "diagnose"}
    if any(w in t for w in ["help", "commands", "what can you"]):
        return {"intent": "help"}
    if any(w in t for w in ["exit", "quit", "bye", "goodbye", "stop"]):
        return {"intent": "exit"}

    return {"intent": "unknown"}

# =========================================================
# Chatbot Class
# =========================================================

class ESP32Chatbot:

    def __init__(self, ip: str):
        self.api   = ESP32API(ip)
        self.tts   = make_engine()
        self.rec   = sr.Recognizer() if MIC_AVAILABLE else None
        if self.rec:
            self.rec.pause_threshold = 0.8

    # ── output ──────────────────────────────────────────────

    def say(self, text: str):
        """Print and speak the response."""
        print(f"\n  Bot: {text}\n")
        self.tts.say(text)
        self.tts.runAndWait()

    # ── input ───────────────────────────────────────────────

    def listen_voice(self) -> str | None:
        """Listen via microphone and return recognised text."""
        with sr.Microphone() as source:
            print("  [Listening... speak now]")
            self.rec.adjust_for_ambient_noise(source, duration=0.4)
            try:
                audio = self.rec.listen(source, timeout=6, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                print("  [No speech detected]")
                return None
        try:
            text = self.rec.recognize_google(audio)
            print(f"\n  You said: {text}")
            return text
        except sr.UnknownValueError:
            print("  [Could not understand]")
        except sr.RequestError as e:
            print(f"  [STT error: {e}]")
        return None

    # ── command execution ────────────────────────────────────

    def execute(self, text: str):
        result = natural_language_parse(text)
        intent = result["intent"]

        if intent == "relay":
            ch    = result["channel"]
            state = result["state"]
            label = RELAY_LABELS.get(ch, f"Relay {ch}")
            self.say(f"Sure! Turning {label} {state}.")
            ok = self.api.toggle_relay(ch, state)
            if ok:
                self.say(f"{label} is now {'on' if state == 'on' else 'off'}.")
            else:
                self.say("Sorry, I couldn't reach the ESP32. Please check the connection.")

        elif intent == "relay_all":
            state = result["state"]
            self.say(f"Turning all relays {state}.")
            ok = all(self.api.toggle_relay(ch, state) for ch in range(1, 5))
            if ok:
                self.say(f"All relays are now {'on' if state == 'on' else 'off'}.")
            else:
                self.say("Some relays failed to respond. Check ESP32.")

        elif intent == "temperature":
            data = self.api.get_data()
            if data:
                self.say(f"The current temperature is {data['temperature']:.1f} degrees Celsius.")
            else:
                self.say("I couldn't read the temperature. Is the ESP32 connected?")

        elif intent == "humidity":
            data = self.api.get_data()
            if data:
                self.say(f"The current humidity is {data['humidity']:.1f} percent.")
            else:
                self.say("I couldn't read the humidity. Check the ESP32.")

        elif intent == "sensors":
            data = self.api.get_data()
            if data:
                self.say(
                    f"The temperature is {data['temperature']:.1f} degrees Celsius "
                    f"and the humidity is {data['humidity']:.1f} percent."
                )
            else:
                self.say("Sensor read failed. Please check the ESP32.")

        elif intent == "status":
            s = self.api.get_status()
            if s:
                parts = []
                for i, state in enumerate(s["relay"], 1):
                    parts.append(f"Relay {i} is {'on' if state else 'off'}")
                self.say(". ".join(parts) + ".")
            else:
                self.say("Couldn't get relay status.")

        elif intent == "diagnose":
            self.say("Running diagnostics. Please wait.")
            d = self.api.get_diagnostics()
            if not d:
                self.say("The ESP32 is unreachable. Cannot run diagnostics.")
                return
            sensor_ok = d.get("sensor_ok", False)
            heap_kb   = d.get("free_heap", 0) // 1024
            uptime    = format_uptime(d.get("uptime_ms", 0))
            signal    = format_rssi(d.get("wifi_rssi", 0))
            self.say(
                f"Device is online. "
                f"IP address is {d.get('ip', 'unknown')}. "
                f"Uptime is {uptime}. "
                f"WiFi signal is {signal}. "
                f"Free memory is {heap_kb} kilobytes. "
                f"Sensor status is {'OK' if sensor_ok else 'failing'}."
            )

        elif intent == "help":
            self.say(
                "Here's what I can do. "
                "Say 'turn on relay one' to control relays. "
                "Say 'turn off everything' to switch all off. "
                "Say 'read sensors' for temperature and humidity. "
                "Say 'relay status' to check all relays. "
                "Say 'diagnose' for a health check. "
                "Say 'exit' to quit."
            )

        elif intent == "exit":
            self.say("Goodbye! Shutting down.")
            sys.exit(0)

        else:
            self.say(
                "Sorry, I didn't quite understand that. "
                "Try saying 'turn on relay one', 'read the temperature', or 'help'."
            )

    # ── main loops ───────────────────────────────────────────

    def run_text_mode(self):
        self.say("Text mode activated. Type your command and press Enter.")
        while True:
            try:
                text = input("  You: ").strip()
            except (EOFError, KeyboardInterrupt):
                self.say("Goodbye!")
                break
            if not text:
                continue
            self.execute(text)

    def run_voice_mode(self):
        self.say("Voice mode activated. Speak your command after the prompt.")
        while True:
            text = self.listen_voice()
            if text:
                self.execute(text)
            else:
                time.sleep(0.3)

# =========================================================
# Entry Point
# =========================================================

if __name__ == "__main__":
    # Resolve IP
    if len(sys.argv) > 1:
        ip = sys.argv[1]
    else:
        ip = input("Enter ESP32 IP [default: 10.24.66.145]: ").strip() or DEFAULT_IP

    bot = ESP32Chatbot(ip)

    print("\n" + "="*50)
    print("  ESP32 Natural Language Chatbot")
    print("="*50)

    bot.say(f"Hello! Connecting to the ESP32 at {ip}.")
    if bot.api.test_connection():
        bot.say("Connected! I'm ready to accept your commands.")
    else:
        bot.say("Warning. Could not reach the ESP32. Check that it is powered on and on the same WiFi.")

    print("\nMode selection:")
    print("  1 → Text mode  (type commands)")
    if MIC_AVAILABLE:
        print("  2 → Voice mode (speak commands)")
    else:
        print("  2 → Voice mode  [unavailable — install pyaudio]")

    choice = input("\nChoose mode (1 or 2): ").strip()

    try:
        if choice == "2" and MIC_AVAILABLE:
            bot.run_voice_mode()
        else:
            bot.run_text_mode()
    except KeyboardInterrupt:
        bot.say("Goodbye!")
