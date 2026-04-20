"""
ESP32 IoT Voice Controller
--------------------------
Controls ESP32 relays and reads sensors via voice commands.
Uses Google Speech Recognition + pyttsx3 TTS for feedback.

Usage:
    python esp32_controller.py
    python esp32_controller.py 192.168.1.100
"""

import sys
import time
import requests
import speech_recognition as sr
import pyttsx3


class ESP32Controller:
    """Main controller class for the ESP32 IoT device."""

    def __init__(self, ip: str, tts: bool = True):
        self.base_url = f"http://{ip}"
        self.relay_states = [0, 0, 0, 0]
        self._tts_enabled = tts

        # --- Text-to-Speech (optional) ---
        self.engine = None
        if tts:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 160)
            self.engine.setProperty("volume", 1.0)

        # --- Speech Recognition ---
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8   # seconds of silence = end of phrase

    # =========================================================
    # TTS
    # =========================================================

    def speak(self, text: str):
        """Say text aloud and print it to console. Skips TTS if disabled."""
        print(f"[Controller] {text}")
        if self._tts_enabled and self.engine:
            self.engine.say(text)
            self.engine.runAndWait()

    # =========================================================
    # API Calls
    # =========================================================

    def test_connection(self) -> bool:
        """Return True if ESP32 is reachable."""
        try:
            r = requests.get(f"{self.base_url}/status", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def get_data(self) -> dict | None:
        """Fetch temperature and humidity from /data."""
        try:
            r = requests.get(f"{self.base_url}/data", timeout=3)
            return r.json()   # {"temperature": X, "humidity": Y}
        except Exception as e:
            print(f"[Error] get_data failed: {e}")
            return None

    def get_status(self) -> dict | None:
        """Fetch relay states from /status."""
        try:
            r = requests.get(f"{self.base_url}/status", timeout=3)
            data = r.json()   # {"relay": [1,0,1,0]}
            self.relay_states = data.get("relay", self.relay_states)
            return data
        except Exception as e:
            print(f"[Error] get_status failed: {e}")
            return None

    def toggle_relay(self, channel: int, state: str) -> bool:
        """
        Set relay channel (1-4) to 'on' or 'off'.
        Returns True on success.
        """
        try:
            url = f"{self.base_url}/relay?ch={channel}&state={state}"
            r = requests.get(url, timeout=3)
            print(f"[HTTP] {url}  →  {r.status_code}")
            if r.status_code == 200:
                self.relay_states[channel - 1] = 1 if state == "on" else 0
                return True
        except Exception as e:
            print(f"[Error] toggle_relay failed: {e}")
        return False

    # =========================================================
    # Command Parser
    # =========================================================

    def process_command(self, command: str):
        """Parse and execute a voice command string."""
        command = command.lower().strip()
        print(f"[You said] {command}")

        # --- Help ---
        if any(w in command for w in ["help", "commands"]):
            self.speak(
                "Available commands: "
                "Turn on relay one to four. "
                "Turn off relay one to four. "
                "Read temperature. "
                "Read humidity. "
                "Read sensors. "
                "Relay status. "
                "Exit."
            )
            return

        # --- Exit ---
        if any(w in command for w in ["exit", "quit", "stop", "bye"]):
            self.speak("Shutting down. Goodbye!")
            sys.exit(0)

        # --- Sensor reads ---
        if "temperature" in command:
            data = self.get_data()
            if data:
                self.speak(f"Current temperature is {data['temperature']:.1f} degrees Celsius.")
            else:
                self.speak("Could not read temperature. Check ESP32 connection.")
            return

        if "humidity" in command:
            data = self.get_data()
            if data:
                self.speak(f"Current humidity is {data['humidity']:.1f} percent.")
            else:
                self.speak("Could not read humidity. Check ESP32 connection.")
            return

        if "sensor" in command or ("read" in command and "relay" not in command):
            data = self.get_data()
            if data:
                self.speak(
                    f"Temperature is {data['temperature']:.1f} degrees Celsius. "
                    f"Humidity is {data['humidity']:.1f} percent."
                )
            else:
                self.speak("Sensor read failed.")
            return

        # --- Relay status ---
        if "status" in command:
            status = self.get_status()
            if status:
                states = status["relay"]
                msg = "Relay status: "
                for i, s in enumerate(states, 1):
                    msg += f"Relay {i} is {'on' if s else 'off'}. "
                self.speak(msg)
            else:
                self.speak("Could not retrieve relay status.")
            return

        # --- Relay control ---
        channel_map = {
            "one": 1, "1": 1,
            "two": 2, "2": 2,
            "three": 3, "3": 3,
            "four": 4, "4": 4,
        }

        found_channel = None
        for word, ch in channel_map.items():
            if word in command:
                found_channel = ch
                break

        if found_channel:
            if "on" in command:
                success = self.toggle_relay(found_channel, "on")
                if success:
                    self.speak(f"Relay {found_channel} turned on.")
                else:
                    self.speak(f"Failed to turn on relay {found_channel}.")
            elif "off" in command:
                success = self.toggle_relay(found_channel, "off")
                if success:
                    self.speak(f"Relay {found_channel} turned off.")
                else:
                    self.speak(f"Failed to turn off relay {found_channel}.")
            else:
                self.speak(f"Say 'on' or 'off' for relay {found_channel}.")
            return

        # --- Unrecognised ---
        self.speak("Command not recognised. Say 'help' for available commands.")

    # =========================================================
    # Voice Listener
    # =========================================================

    def listen_once(self) -> str | None:
        """
        Listen for one voice command.
        Returns the recognised text, or None on failure.
        """
        with sr.Microphone() as source:
            print("\n[Listening...] Speak now.")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
            except sr.WaitTimeoutError:
                print("[Timeout] No speech detected.")
                return None

        try:
            text = self.recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            print("[Error] Could not understand audio.")
        except sr.RequestError as e:
            print(f"[Error] Speech service error: {e}")
        return None

    # =========================================================
    # Main Loop
    # =========================================================

    def run(self):
        """Start the interactive voice command loop."""
        self.speak("Connecting to ESP32 at " + self.base_url.replace("http://", ""))

        if self.test_connection():
            self.speak("Connected! Ready for voice commands. Say 'help' for commands.")
        else:
            self.speak(
                "Warning: Could not reach ESP32. "
                "Check the IP address and make sure the device is powered on."
            )

        while True:
            text = self.listen_once()
            if text:
                self.process_command(text)
            else:
                # Brief pause before next listen cycle
                time.sleep(0.3)


# =========================================================
# Entry Point
# =========================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        esp_ip = sys.argv[1]
    else:
        esp_ip = input("Enter ESP32 IP address (e.g. 192.168.1.100): ").strip()
        if not esp_ip:
            esp_ip = "10.24.66.145"   # fallback default

    controller = ESP32Controller(esp_ip)

    try:
        controller.run()
    except KeyboardInterrupt:
        print("\n[Exiting] Keyboard interrupt received.")
        controller.speak("Goodbye!")