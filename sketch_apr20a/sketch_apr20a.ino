#include <WiFi.h>
#include <WebServer.h>
#include "DHT.h"

// ================= WIFI =================
const char* ssid = "realme C33";
const char* password = "00000000";

// ================= DHT =================
#define DHTPIN 13
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ================= RELAYS =================
// Use proper relay module IN1-IN4
int relayPins[4] = {33, 32, 26, 27};  // GPIOs

// ================= SERVER =================
WebServer server(80);

// ================= SENSOR CACHE =================
float lastTemp = 0;
float lastHum = 0;
unsigned long lastReadTime = 0;
const unsigned long minInterval = 2000;

// ================= CORS =================
void enableCORS() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "*");
}

// ================= /data =================
void handleData() {
  enableCORS();

  unsigned long now = millis();

  if (now - lastReadTime > minInterval) {
    float h = dht.readHumidity();
    float t = dht.readTemperature();

    if (!isnan(h) && !isnan(t)) {
      lastHum = h;
      lastTemp = t;
      lastReadTime = now;
    }
  }

  String json = "{";
  json += "\"temperature\":" + String(lastTemp) + ",";
  json += "\"humidity\":" + String(lastHum);
  json += "}";

  server.send(200, "application/json", json);
}

// ================= /status =================
void handleStatus() {
  enableCORS();

  String json = "{\"relay\":[";
  for (int i = 0; i < 4; i++) {
    int state = digitalRead(relayPins[i]) == LOW ? 1 : 0;
    json += String(state);
    if (i < 3) json += ",";
  }
  json += "]}";

  server.send(200, "application/json", json);
}

// ================= /relay =================
// Example: /relay?ch=1&state=on
void handleRelay() {
  enableCORS();

  if (!server.hasArg("ch") || !server.hasArg("state")) {
    server.send(400, "application/json", "{\"error\":\"Missing params\"}");
    return;
  }

  int ch = server.arg("ch").toInt();
  String state = server.arg("state");

  if (ch < 1 || ch > 4) {
    server.send(400, "application/json", "{\"error\":\"Invalid channel\"}");
    return;
  }

  int pin = relayPins[ch - 1];

  if (state == "on") {
    digitalWrite(pin, LOW);   // ACTIVE LOW
  } else if (state == "off") {
    digitalWrite(pin, HIGH);
  } else {
    server.send(400, "application/json", "{\"error\":\"Invalid state\"}");
    return;
  }

  String json = "{";
  json += "\"channel\":" + String(ch) + ",";
  json += "\"state\":\"" + state + "\"";
  json += "}";

  server.send(200, "application/json", json);
}

// ================= OPTIONS =================
void handleOptions() {
  enableCORS();
  server.send(204);
}

// ================= SETUP =================
void setup() {
  Serial.begin(115200);

  dht.begin();

  // Init relays OFF
  for (int i = 0; i < 4; i++) {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], HIGH);
  }

  // WiFi connect
  WiFi.begin(ssid, password);
  Serial.print("Connecting");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  // Routes
  server.on("/data", HTTP_GET, handleData);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/relay", HTTP_GET, handleRelay);

  // OPTIONS (CORS)
  server.on("/data", HTTP_OPTIONS, handleOptions);
  server.on("/status", HTTP_OPTIONS, handleOptions);
  server.on("/relay", HTTP_OPTIONS, handleOptions);

  server.onNotFound([]() {
    if (server.method() == HTTP_OPTIONS) {
      handleOptions();
    } else {
      enableCORS();
      server.send(404, "application/json", "{\"error\":\"Not found\"}");
    }
  });

  server.begin();
  Serial.println("Server started");
}

// ================= LOOP =================
void loop() {
  server.handleClient();
}