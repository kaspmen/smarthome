import paho.mqtt.client as mqtt
import sqlite3
import os
from dotenv import load_dotenv
import datetime


load_dotenv()

mqtt_broker = os.getenv('MQTT_BROKER_ADDRESS')
port_one = os.getenv('MQTT_PORT_ONE')
port_two = os.getenv('MQTT_PORT_TWO')
mqtt_topics = ["Window_Sensor", "Door_Sensor", "Stairs_Sensor"]

# SQLite database file
database_file = "sensor_data.db"

# Connect to the database
conn = sqlite3.connect(database_file)
cursor = conn.cursor()

# Create the table if it doesn't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS sensor_data
                  (topic TEXT, temperature REAL, humidity REAL, voltage REAL, wakeup_reason TEXT, motion TEXT, state TEXT, sleep_state TEXT, timestamp TEXT)''')


# Commit the changes and close the connection
conn.commit()
conn.close()

def data_collection():
    # MQTT callback functions
    def on_connect(client, userdata, flags, rc):
        print("Connected to MQTT broker")
        for topic in mqtt_topics:
            client.subscribe(topic)

    def on_message(client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        print("Received message on topic {}: {}".format(topic, payload))
        process_data(topic, payload)

    def process_data(topic, payload):
        # Parse the payload and extract the required data
        # Modify this section based on the format of your payload
        data = payload.split("\t")
        temperature = ""
        humidity = ""
        voltage = ""
        wakeup_reason = ""
        motion = ""
        state = ""
        sleep_state = ""
        timestamp = datetime.datetime.now()

        for item in data:
            key, value = item.split(": ")
            key = key.strip()
            value = value.strip()

            if key == "Temperature":
                temperature = value.replace("°C", "")
            elif key == "Humidity":
                humidity = value.replace("%", "")
            elif key == "Voltage":
                voltage = value
            elif key == "Wakeup_Reason":
                wakeup_reason = value
            elif key == "Motion":
                motion = value
            elif key == "State":
                state = value
            elif key == "Sleep_State":
                sleep_state = value

        # Store the data in the SQLite database
        conn = sqlite3.connect(database_file)
        cursor = conn.cursor()

        # Modify the table name and column names based on your database structure
        cursor.execute(
            "INSERT INTO sensor_data (topic, temperature, humidity, voltage, wakeup_reason, motion, state, sleep_state, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (topic, temperature, humidity, voltage, wakeup_reason, motion, state, sleep_state, timestamp))


        conn.commit()
        conn.close()

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(mqtt_broker, int(port_one), int(port_two))

    client.loop_forever()

if __name__ == "__main__":
    data_collection()
