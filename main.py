#!/usr/bin/env python3
"""
Modified by smartbuilds.io
Date: 26.07.22

# main.py
Desc: This web application serves a motion JPEG stream and sends an image
notification to your email on motion detected via a PIR sensor

# install the necessary packages
"""
from flask import Flask, render_template, Response, request
from camera import VideoCamera
from arduino_comms import arduino_pi_comms
import time
import threading
import os
import serial
from dotenv import load_dotenv
import sqlite3
from flask import Flask, render_template
from data_collection import data_collection
from flask_socketio import SocketIO

load_dotenv()

current_time = time.time() #initialise current time on run

# How long before ACK motion and sending notification
sensitivity_timer = 10000

# View email_notification for setup
pi_email = os.getenv('PI_EMAIL')
pi_app_password = os.getenv('PI_APP_PASSWORD')
pi_port = int(os.getenv('PI_PORT'))
pi_host = os.getenv('PI_HOST')

pi_camera = VideoCamera(flip=True) # flip pi camera if upside down.

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html') #you can customize index.html here


def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

def gen_capture(camera):
    frame = camera.get_frame()
    return frame
        
@app.route('/video_feed')
def video_feed():
    return Response(gen(pi_camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/sensor_data')
def sensor_data():
    # Connect to the database
    conn = sqlite3.connect('sensor_data.db')
    cursor = conn.cursor()

    # Retrieve the data from the table
    cursor.execute("SELECT * FROM sensor_data")
    data = cursor.fetchall()

    # Close the connection
    conn.close()

    # Pass the data to the template and render the HTML page
    return render_template('sensor_data.html', data=data)

if __name__ == '__main__':
    # Start the data collection thread
    data_collection_thread = threading.Thread(target=data_collection)
    data_collection_thread.daemon = True
    data_collection_thread.start()

    # Start the Flask application
    try:
        ser = serial.Serial('/dev/ttyUSB0', 57600, timeout=1)
        ser.reset_input_buffer()

        if ser:
            # Create a thread for parallel processing (camera stream and PIR Sensor trigger)
            arduino_comms_thread = threading.Thread(target=arduino_pi_comms, args=(ser, sensitivity_timer, current_time, pi_email, pi_app_password, pi_port, pi_host, gen_capture(pi_camera)))
            arduino_comms_thread.daemon = True
            arduino_comms_thread.start()
    except:
        print("Arduino not recognized")

    app.run(host='0.0.0.0', debug=False)

