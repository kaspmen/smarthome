#include <arduino_secrets_red.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

const char* ssid = SECRET_SSID;
const char* password = SECRET_SSID_PASSWORD;
const char* mqtt_server = SECRET_MQTT_SERVER;
const int mqtt_port = SECRET_MQTT_PORT;
const char* mqtt_username = SECRET_MQTT_USERNAME;
const char* mqtt_password = SECRET_MQTT_PASSWORD;
const char* mqtt_topic = SECRET_MQTT_TOPIC;

const int ledPin = 18;
const int buzzerPin = 5;
const int pirPin = 27;
int pirVal = 0;
int prevPirVal = 0;
int hallEffectVal = 0;
int prevHallEffectVal = 0;
int state = LOW;

WiFiClient espClient;
PubSubClient client(espClient);

#define uS_TO_S_FACTOR 1000000 // Conversion factor for microseconds to seconds
#define TIME_TO_SLEEP 1800     // 30 minutes
#define DHTPIN 15
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

const int analogPin = 32;  // ADC pin number
const float resistorRatio = 56000.0 / 10000.0;  // Resistor voltage divider ratio
const float referenceVoltage = 1.1;  // Reference voltage (in volts)

unsigned long previousCheckMillis = 0;
const unsigned long checkInterval = 500; // 0.5 seconds

unsigned long previousDHTMillis = 0;
const unsigned long dhtInterval = 60000; // 1 minute

void print_wakeup_reason() {
  esp_sleep_wakeup_cause_t wakeup_reason;

  wakeup_reason = esp_sleep_get_wakeup_cause();

  switch (wakeup_reason) {
    case ESP_SLEEP_WAKEUP_EXT0:
      Serial.println("Wakeup caused by PIR sensor");
      client.publish(mqtt_topic,"Wakeup_Reason: Wakeup caused by PIR sensor");
      break;
    case ESP_SLEEP_WAKEUP_TIMER:
      Serial.println("Wakeup caused by transmitting data (30 min cycle)");
      client.publish(mqtt_topic,"Wakeup_Reason: Wakeup caused by transmitting data (cycle)");
      break;
    default:
      Serial.printf("Wakeup was not caused by deep sleep: %d\n", wakeup_reason);
      client.publish(mqtt_topic,"Wakeup_Reason: Wakeup was not caused by deep sleep");
      break;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(buzzerPin, OUTPUT);  // set the buzzer pin as an output
  pinMode(ledPin, OUTPUT);     // set the buzzer pin as an output
  pinMode(pirPin, INPUT);

  dht.begin();
  analogReadResolution(12);  // Set ADC resolution to 12 bits (0-4095)

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }

  // Connect to MQTT broker
  client.setServer(mqtt_server, mqtt_port);
  client.setClient(espClient);  // set the client object
  while (!client.connected()) {
    Serial.println("Connecting to MQTT broker...");
    if (client.connect("ESP32Client", mqtt_username, mqtt_password)) {  // connect with username and password
      Serial.println("Connected to MQTT broker");
    } else {
      delay(1000);
    }
  }
  print_wakeup_reason();  // print wakeup reason

  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
}

void loop() {
  unsigned long currentMillis = millis();

  float measuredVoltage = ((analogRead(analogPin) / 4095.0) * 7.4) * 3.7;

  // Check PIR sensor every 0.5 seconds
  if (currentMillis - previousCheckMillis >= checkInterval) {
    previousCheckMillis = currentMillis;


    pirVal = digitalRead(pirPin);  // read sensor value
    Serial.print("PIR value: ");
    Serial.println(pirVal);

    if (pirVal != prevPirVal) {
      prevPirVal = pirVal;
      if (pirVal == HIGH) {          // check if the sensor is HIGH
        digitalWrite(ledPin, HIGH);  // turn LED ON
        if (state == LOW) {
          Serial.println("Motion detected!");
          client.publish(mqtt_topic, "Motion: Motion Detected!");
          state = HIGH;  // update variable state to HIGH
        }
      } else {
        digitalWrite(ledPin, LOW);  // turn LED OFF
        if (state == HIGH) {
          Serial.println("Motion stopped!");
          client.publish(mqtt_topic, "Motion: No Motion");
          state = LOW;  // update variable state to LOW
        }
      }
    }

    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();

    if (isnan(temperature) || isnan(humidity)) {
      Serial.println("Failed to read from DHT sensor!");
      return;
    }

    Serial.print("Temperature: ");
    Serial.print(temperature);
    Serial.print(" °C\t");
    Serial.print("Humidity: ");
    Serial.print(humidity);
    Serial.println(" %");

    // Read the Hall Effect sensor value
    hallEffectVal = hallRead();

    if (hallEffectVal != prevHallEffectVal) {
      prevHallEffectVal = hallEffectVal;
      if (hallEffectVal > 60) {
        digitalWrite(buzzerPin, HIGH);  // turn on the buzzer
        Serial.println(hallEffectVal);
        client.publish("State", "Opened");
      } else {
        digitalWrite(buzzerPin, LOW);  // turn off the buzzer
        Serial.println(hallEffectVal);
        client.publish("State", "Closed");
      }
    }
  }

  // Send DHT data every 1 minute
  if (currentMillis - previousDHTMillis >= dhtInterval) {
    previousDHTMillis = currentMillis;

    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();

    if (isnan(temperature) || isnan(humidity)) {
      Serial.println("Failed to read from DHT sensor!");
      return;
    }

    // Create a string variable to store the combined data payload
    String payload = "";

    // Concatenate all the data values to the payload string
    payload += "Temperature: " + String(temperature) + " °C\t";
    payload += "Humidity: " + String(humidity) + " %\t";
    payload += "Voltage: " + String(measuredVoltage) + "\t";
    payload += "Wakeup_Reason: ";
    payload += (pirVal == HIGH) ? String("Wakeup caused by PIR sensor") : String("Wakeup caused by transmitting data (cycle)");
    payload += "\t";
    payload += "Motion: " + String((state == HIGH) ? "Motion Detected!" : "No Motion") + "\t";
    payload += "State: " + String((hallEffectVal > 60) ? "Opened" : "Closed") + "\t";
    payload += "Sleep_State: Awake and alert!";

    // Publish the payload to the MQTT topic
    client.publish(mqtt_topic, payload.c_str(), true);
  }

  delay(100);  // Add a small delay for stability

/*
  // Check if both conditions are met for entering deep sleep
  if (pirVal == 0 && hallEffectVal < 30) {
    // Put the ESP32 into deep sleep mode
    client.publish("Sleep_State", "Sleeping. ZzZz.");
    Serial.println("Going into deep sleep. ZzZz.");
    delay(3000);
    esp_sleep_enable_ext0_wakeup(GPIO_NUM_27, 1);
    esp_deep_sleep_start();
  } else {
    client.publish("Sleep_State", "Awake and alert!"); // Update Sleep_State to "Awake"
  }
  */
}
