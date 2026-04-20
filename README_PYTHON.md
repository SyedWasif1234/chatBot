# ESP32 IoT Controller - Python Voice Control

Control your ESP32 IoT device with Python and voice commands!

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `requests` - HTTP client for ESP32 API
- `SpeechRecognition` - Voice command recognition (uses Google Speech API)
- `pyttsx3` - Text-to-speech feedback

### 2. System Requirements

- **Microphone** - For voice input
- **Speakers/Audio** - For voice feedback
- **Python 3.7+**
- **Internet connection** - For Google Speech Recognition API

> **Note:** If you're on Windows, you may need to install additional audio libraries. If audio issues occur, install:
> ```bash
> pip install pyaudio
> ```

## Usage

### Quick Start

```bash
python esp32_controller.py
```

It will prompt for your ESP32 IP address. Or pass it directly:

```bash
python esp32_controller.py 192.168.1.100
```

### Voice Commands

Once connected, you can use these commands:

| Command | Example |
|---------|---------|
| **Control Relays** | "Turn on relay 1", "Switch off relay 2" |
| **Read Sensors** | "Read temperature", "Read humidity", "Read sensors" |
| **Check Status** | "Relay status", "Check status" |
| **Help** | "Help" or "Commands" |
| **Exit** | "Exit", "Quit", or Ctrl+C |

### Examples

```
You: "Turn on relay 1"
Controller: Sets relay 1 to ON

You: "Read temperature"
Controller: Reads and reports current temperature

You: "Relay status"
Controller: Reports state of all 4 relays

You: "Turn off relay 3"
Controller: Sets relay 3 to OFF
```

## Python API Usage

You can also use the controller programmatically:

```python
from esp32_controller import ESP32Controller

# Initialize
controller = ESP32Controller("192.168.1.100")

# Test connection
if controller.test_connection():
    # Read sensors
    data = controller.get_data()
    print(f"Temperature: {data['temperature']}°C")
    
    # Control relay
    controller.toggle_relay(1, "on")  # Turn on relay 1
    controller.toggle_relay(1, "off") # Turn off relay 1
    
    # Get relay status
    status = controller.get_status()
    print(f"Relay states: {status['relay']}")
```

## Troubleshooting

### Microphone Issues
- Check that your microphone is connected and set as default
- Test microphone in Windows Sound settings
- Try: `pip install pyaudio`

### Speech Recognition Errors
- Ensure internet connection (uses Google API)
- Speak clearly and at normal volume
- Reduce background noise
- The recognizer has a 5-second timeout

### ESP32 Connection Issues
- Verify ESP32 IP address (check router or ESP32 serial console)
- Ensure ESP32 and computer are on same network
- Check ESP32 is powered and running
- Test connection in browser: `http://192.168.1.100/status`

### Audio Output Issues
- Check system volume
- Verify speakers are working
- Try different audio output device in system settings
- Text will still print to console even if audio fails

## Features

✅ Real-time voice command recognition  
✅ Text-to-speech feedback  
✅ Control 4 relays independently  
✅ Read temperature and humidity sensors  
✅ Connection status monitoring  
✅ Error handling and reconnection  
✅ Interactive command loop  
✅ Programmable Python API  

## File Structure

```
d:\iot\
├── index.html              # Original web dashboard
├── esp32_controller.py     # Python controller with voice commands
├── requirements.txt        # Python dependencies
└── README_PYTHON.md        # This file
```

## Advanced Usage

### Custom Commands

Edit the `process_command()` method in `esp32_controller.py` to add your own voice commands:

```python
def process_command(self, command: str):
    # Add your custom logic here
    if "custom" in command:
        self.speak("Executing custom command")
```

### Automation

Use the controller in scripts for automation:

```python
controller = ESP32Controller("192.168.1.100")

# Turn on heating
controller.toggle_relay(1, "on")
time.sleep(60)

# Check temperature
data = controller.get_data()
if data['temperature'] > 30:
    controller.toggle_relay(1, "off")
```

## Architecture

```
┌─────────────────────────────────────────────┐
│     Voice Input (Microphone)                │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  SpeechRecognition (Google API)             │
│  Converts audio to text                     │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  ESP32Controller.process_command()          │
│  Parses and interprets voice commands       │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  HTTP Requests to ESP32 API                 │
│  /relay?ch=X&state=Y                        │
│  /data, /status                             │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  ESP32 Device                               │
│  Executes relay control & sensor reads      │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  Text-to-Speech (pyttsx3)                   │
│  Provides voice feedback                    │
└─────────────────────────────────────────────┘
```

## License

MIT License - Feel free to use and modify!
