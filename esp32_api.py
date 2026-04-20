"""
esp32_api.py
------------
Lightweight HTTP API layer for the ESP32 device.
Shared by both esp32_controller.py (voice) and telegram_bot.py.
No audio dependencies.
"""

import requests


class ESP32API:
    """Pure HTTP client for the ESP32 REST API."""

    def __init__(self, url: str):
        # Accept either "192.168.1.100" or "https://xxxx.trycloudflare.com"
        if url.startswith("http"):
            self.base_url = url.rstrip("/")
        else:
            self.base_url = f"http://{url}"

    def test_connection(self) -> bool:
        """Return True if ESP32 is reachable."""
        try:
            r = requests.get(f"{self.base_url}/status", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def get_data(self) -> dict | None:
        """Fetch temperature and humidity. Returns {"temperature": X, "humidity": Y}."""
        try:
            r = requests.get(f"{self.base_url}/data", timeout=3)
            return r.json()
        except Exception as e:
            print(f"[Error] get_data: {e}")
            return None

    def get_status(self) -> dict | None:
        """Fetch relay states. Returns {"relay": [1,0,1,0]}."""
        try:
            r = requests.get(f"{self.base_url}/status", timeout=3)
            return r.json()
        except Exception as e:
            print(f"[Error] get_status: {e}")
            return None

    def get_diagnostics(self) -> dict | None:
        """
        Fetch full device diagnostics from /diagnostics.
        Returns dict with uptime_ms, wifi_rssi, free_heap,
        sensor_ok, temperature, humidity, ip, relay[]
        """
        try:
            r = requests.get(f"{self.base_url}/diagnostics", timeout=4)
            return r.json()
        except Exception as e:
            print(f"[Error] get_diagnostics: {e}")
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
            return r.status_code == 200
        except Exception as e:
            print(f"[Error] toggle_relay: {e}")
            return False
