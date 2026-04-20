Build a complete, production-ready IoT dashboard for an ESP32 device.

==================================================
### SYSTEM CONTEXT

ESP32 is running locally on WiFi.

Base URL:
http://<ESP32-IP>

API endpoints:

1. GET /data
Returns:
{
  "temperature": number,
  "humidity": number
}

2. GET /relay?ch=1&state=on|off
Controls relay channels 1–4

3. GET /status
Returns:
{
  "relay": [1,0,1,0]
}
(1 = ON, 0 = OFF)

==================================================
### HARDWARE CONTEXT

- ESP32 controls 4 relays
- All relays are ACTIVE LOW
  (LOW = ON, HIGH = OFF)
- Pins are already working and mapped correctly
- Dashboard must control all 4 relays independently

==================================================
### CORE REQUIREMENTS

Create a responsive web dashboard that:

1. Displays live sensor data (temperature + humidity)
2. Controls 4 relay channels independently
3. Syncs relay state from ESP32
4. Handles connection failures gracefully
5. Allows dynamic ESP32 IP configuration

==================================================
### MCP ARCHITECTURE (MANDATORY)

Simulate proper MCP-style modular structure:

1. HTTP MODULE (API Layer)
Create reusable functions:
- getSensorData()
- getRelayStatus()
- setRelay(channel, state)

Use fetch() internally.

----------------------------------------------

2. STATE MODULE
Centralized state object:

{
  temperature: null,
  humidity: null,
  relays: [0,0,0,0],
  connected: true,
  lastUpdated: null
}

Must:
- update automatically from API
- sync UI with backend state

----------------------------------------------

3. STORAGE MODULE
- Save ESP32 IP in localStorage
- Load on startup
- Allow user to change IP dynamically

----------------------------------------------

4. UI MODULE (Stitch-style composition)
- Build UI using modular functions:
  - createSensorCard()
  - createRelayControls()
  - createConfigPanel()
- Keep UI logic separate from API logic

==================================================
### FRONTEND REQUIREMENTS

- Single file: index.html
- Pure HTML + CSS + JavaScript
- NO frameworks (no React, Vue, Angular)
- NO external CDN libraries
- Must run offline
- Clean, readable, well-structured code

==================================================
### FEATURES

#### 1. SENSOR PANEL
- Show Temperature (°C)
- Show Humidity (%)
- Auto-refresh every 2 seconds
- Show last updated timestamp

----------------------------------------------

#### 2. RELAY CONTROL PANEL
- 4 toggle buttons/switches
- Each controls one relay
- Show real-time ON/OFF state
- Prevent rapid repeated clicks (debounce)

----------------------------------------------

#### 3. CONNECTION STATUS
- Detect if ESP32 is unreachable
- Show:
  - "Connected" (green)
  - "Disconnected" (red)
- Retry automatically

----------------------------------------------

#### 4. CONFIG PANEL
- Input field for ESP32 IP
- Save to localStorage
- Reload system after change

==================================================
### UI DESIGN

- Dark theme
- Card-based layout
- Mobile responsive
- Colors:
  - Green = ON
  - Red = OFF
  - Gray = unknown/disconnected
- Smooth transitions (CSS)

==================================================
### ERROR HANDLING

- Handle failed API calls
- Show fallback values
- Do not crash UI
- Display meaningful error states

==================================================
### PERFORMANCE RULES

- Use efficient polling (2 seconds max)
- Avoid blocking UI
- Use async/await properly
- Keep code lightweight (ESP32-friendly)

==================================================
### OUTPUT FORMAT

- Return ONE complete index.html file
- Include:
  - Embedded CSS
  - Embedded JavaScript
- Code must be clean and commented

==================================================
### OPTIONAL (HIGH PRIORITY)

- Loading spinner
- Button animation
- Subtle UI transitions
- Clean typography

==================================================
### STRICT RULES (DO NOT BREAK)

- Do NOT use any frontend frameworks
- Do NOT use external libraries
- Do NOT split into multiple files
- Do NOT fake API responses
- Do NOT invent endpoints

==================================================
### GOAL

A fully working dashboard that:
- Controls all 4 relays reliably
- Displays real-time sensor data
- Works directly in a browser
- Can later be hosted on ESP32 or locally

==================================================