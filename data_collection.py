import paho.mqtt.client as mqtt
import os
from dotenv import load_dotenv
import time
import sqlite3
import threading

load_dotenv()

mqtt_broker = os.getenv('MQTT_BROKER_ADDRESS')
port_one = os.getenv('MQTT_PORT_ONE')
port_two = os.getenv('MQTT_PORT_TWO')

recent_readings = {}
recent_readings_lock = threading.Lock()

class SensorData:
    def __init__(self, sleep_state, wakeup_reason, temp, hum):
        self.sleep_state = sleep_state
        self.wakeup_reason = wakeup_reason
        self.temp = temp
        self.hum = hum

    def __repr__(self):
        return f"SensorData(sleep_state={self.sleep_state}, wakeup_reason={self.wakeup_reason}, temp={self.temp}, hum={self.hum})"

    def save_to_database(self, topic):
        conn = sqlite3.connect('sensor_data.db')
        cursor = conn.cursor()

        # Save the sensor data to the database
        cursor.execute('''
            INSERT INTO sensor_data (topic, sleep_state, wakeup_reason, temperature, humidity)
            VALUES (?, ?, ?, ?, ?)
        ''', (topic, self.sleep_state, self.wakeup_reason, self.temp, self.hum))
        conn.commit()
        conn.close()

def setup_sensors():
    def on_connect(client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        client.subscribe("Window_Sensor")
        client.subscribe("Stairs_Sensor")
        client.subscribe("Door_Sensor")
        client.subscribe("Bedroom_Sensor")
        client.subscribe("Kitchen_Sensor")

    def on_message(client, userdata, msg):
        global recent_readings

        topic = msg.topic
        payload = msg.payload.decode()

        if topic not in recent_readings:
            recent_readings[topic] = []

        # Extract values from the payload
        sleep_state = payload.split("Sleep_State: ")[-1]
        wakeup_reason = payload.split("Wakeup_Reason: ")[-1]
        temp = payload.split("temp: ")[-1]
        hum = payload.split("hum: ")[-1]

        sensor_data = SensorData(sleep_state, wakeup_reason, temp, hum)

        # Acquire a lock before accessing recent_readings and the database
        with recent_readings_lock:
            recent_readings[topic].append(sensor_data)
            sensor_data.save_to_database(topic)  # Save the data to the database

            # Keep only the most recent readings
            max_readings = 10
            if len(recent_readings[topic]) > max_readings:
                recent_readings[topic].pop(0)

        print(f"Received message on topic '{topic}': {payload}")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(mqtt_broker, int(port_one), int(port_two))

    client.loop_forever()


def get_recent_readings(topic):
    conn = sqlite3.connect('sensor_data.db')
    cursor = conn.cursor()
    
    # Retrieve the recent readings for the specified topic from the database
    cursor.execute('''
        SELECT sleep_state, wakeup_reason, temperature, humidity
        FROM sensor_data
        WHERE topic = ?
        ORDER BY timestamp DESC
        LIMIT 10
    ''', (topic,))
    rows = cursor.fetchall()

    readings = []
    for row in rows:
        sleep_state, wakeup_reason, temperature, humidity = row
        sensor_data = SensorData(sleep_state, wakeup_reason, temperature, humidity)
        readings.append(sensor_data)
    
    conn.close()

    return readings


if __name__ == "__main__":
    conn = sqlite3.connect('sensor_data.db')
    cursor = conn.cursor()

    # Create a table to store the sensor data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            sleep_state TEXT,
            wakeup_reason TEXT,
            temperature REAL,
            humidity REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

    setup_sensors_thread = threading.Thread(target=setup_sensors)
    setup_sensors_thread.start()

    while True:
        with recent_readings_lock:
            for topic in recent_readings:
                readings = get_recent_readings(topic)  # Get the list of recent readings for the topic

                if readings:
                    print(f"Recent Readings for topic '{topic}':")
                    for reading in readings:
                        print(reading)

        time.sleep(1)
