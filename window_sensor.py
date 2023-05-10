import paho.mqtt.client as mqtt
import threading
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

mqtt_broker = os.getenv('MQTT_BROKER_ADDRESS')
port_one = os.getenv('MQTT_PORT_ONE')
port_two = os.getenv('MQTT_PORT_TWO')

temperature = None
humidity = None
sleep_state = None
wakeup_reason = None
state = None
motion = None

recent_readings = []

# Connect to SQLite database
conn = sqlite3.connect('sensor_data.db')
cursor = conn.cursor()

# Create a table for the readings
cursor.execute('''
    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sensor_name TEXT,
        temperature REAL,
        humidity REAL,
        sleep_state TEXT,
        wakeup_reason TEXT,
        state TEXT,
        motion TEXT,
        timestamp TEXT
    )
''')
conn.commit()

def setup_window_sensor():
    def on_connect(client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        client.subscribe("Window_Sensor")
        client.subscribe("Temperature")
        client.subscribe("Humidity")
        client.subscribe("Sleep_State")
        client.subscribe("Wakeup_Reason")
        client.subscribe("State")
        client.subscribe("Motion")

    def on_message(client, userdata, msg):
        global temperature, humidity, sleep_state, wakeup_reason, state, motion, recent_readings

        topic = msg.topic
        payload = msg.payload.decode()
        sensor_name = ""  # Initialize the variable with a default value

        if topic == "Window_Sensor":
            sensor_name = "Window Sensor"
        elif topic == "Temperature":
            sensor_name = "Temperature Sensor"
            temperature = float(payload)
        elif topic == "Humidity":
            sensor_name = "Humidity Sensor"
            humidity = float(payload)
        elif topic == "Sleep_State":
            sensor_name = "Sleep State Sensor"
            sleep_state = payload
        elif topic == "Wakeup_Reason":
            sensor_name = "Wakeup Reason Sensor"
            wakeup_reason = payload
        elif topic == "State":
            sensor_name = "State Sensor"
            state = payload
        elif topic == "Motion":
            sensor_name = "Motion Sensor"
            motion = payload

        timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")  # Assign timestamp before appending to recent_readings

        recent_readings.append({
            'sensor_name': sensor_name,
            'temperature': temperature,
            'humidity': humidity,
            'sleep_state': sleep_state,
            'wakeup_reason': wakeup_reason,
            'state': state,
            'motion': motion,
            'timestamp': timestamp  # Include the timestamp in the dictionary
        })

        # Keep only the most recent readings
        max_readings = 10
        if len(recent_readings) > max_readings:
            recent_readings.pop(0)

        # Create a new connection and cursor object
        conn = sqlite3.connect('sensor_data.db')
        cursor = conn.cursor()

        # Store readings in the database
        cursor.execute('''
            INSERT INTO readings (sensor_name, temperature, humidity, sleep_state, wakeup_reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (sensor_name, temperature, humidity, sleep_state, wakeup_reason, timestamp))
        conn.commit()

        # Close the connection
        conn.close()

        print("Received packet from {}: {}".format(sensor_name, payload))

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(mqtt_broker, int(port_one), int(port_two))

    client.loop_forever()

def get_recent_readings():
    global recent_readings
    return recent_readings


if __name__ == "__main__":
    setup_window_sensor()
