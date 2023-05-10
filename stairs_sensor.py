import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("Stairs_Sensor")
    client.subscribe("Temperature")
    client.subscribe("Humidity")

def on_message(client, userdata, msg):
    print(msg.payload.decode())

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("192.168.137.254", 1883, 60)

client.loop_forever()