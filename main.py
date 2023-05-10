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
import sys
import serial
from dotenv import load_dotenv
import json
from flask import Flask, render_template
import window_sensor
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

pi_camera = VideoCamera(flip=False) # flip pi camera if upside down.

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
    recent_readings = window_sensor.get_recent_readings()
    return render_template('sensor_data.html', readings=recent_readings)

if __name__ == '__main__':
    # device USB name e.g. /dev/ttyACM0 or /dev/ttyUSB0 if connected
    try:
        ser = serial.Serial('/dev/ttyUSB0', 57600, timeout=1)
        ser.reset_input_buffer()
        
        if ser:
            # Create a thread for parallel processing/ multithreading (camera stream and PIR Sensor trigger)
            arduino_comms_thread = threading.Thread(target=arduino_pi_comms, args=(ser, sensitivity_timer, current_time, pi_email, pi_app_password, pi_port, pi_host, gen_capture(pi_camera)))
            arduino_comms_thread.daemon = True
            arduino_comms_thread.start()
    except:
        print("Arduino not recognized")

    try:
        # Create a thread for running the data_collection
        window_sensor_thread = threading.Thread(target=window_sensor.setup_window_sensor)
        window_sensor_thread.daemon = True
        window_sensor_thread.start()
    except Exception as e: 
        print(e)

    app.run(host='0.0.0.0', debug=False)
