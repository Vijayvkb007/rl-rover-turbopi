#!/usr/bin/python3
# coding=utf8
import sys
sys.path.append('/home/pi/TurboPi/')
import cv2
import time
import math
import signal
import Camera
import argparse
import threading
import numpy as np
import yaml_handle
import mediapipe as mp
import HiwonderSDK.PID as PID
import HiwonderSDK.Misc as Misc
import HiwonderSDK.Board as Board
import HiwonderSDK.mecanum as mecanum
import os

# Setup environment
os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
os.environ["PULSE_SERVER"] = "/run/user/1000/pulse/native"
os.environ["HOME"] = "/home/pi"

if sys.version_info.major == 2:
    print('Please run this program with python3!')
    sys.exit(0)

# Hardware & AI setup
car = mecanum.MecanumChassis()
Face = mp.solutions.face_detection
faceDetection = Face.FaceDetection(min_detection_confidence=0.6)

# Image and servo tracking
size = (640, 480)
__isRunning = False
center_x, center_y, area = -1, -1, 0

servo1 = 1500
servo2 = 1500
servo_x = servo2
servo_y = servo1

car_x_pid = PID.PID(P=0.150, I=0.001, D=0.0001)
car_y_pid = PID.PID(P=0.002, I=0.001, D=0.0001)
servo_x_pid = PID.PID(P=0.05, I=0.0001, D=0.0005)
servo_y_pid = PID.PID(P=0.05, I=0.0001, D=0.0005)

servo_data = None
car_en = False
audio_played = False
no_face_count = 0
cooldown_frames = 10

# Load servo calibration
def load_config():
    global servo_data
    servo_data = yaml_handle.get_yaml_data(yaml_handle.servo_file_path)

def initMove():
    Board.setPWMServoPulse(1, servo1, 1000)
    Board.setPWMServoPulse(2, servo2, 1000)

def setBuzzer(timer):
    Board.setBuzzer(0)
    Board.setBuzzer(1)
    time.sleep(timer)
    Board.setBuzzer(0)

def car_stop():
    car.set_velocity(0, 90, 0)

def reset():
    global servo1, servo2
    global servo_x, servo_y
    global center_x, center_y, area
    servo1 = servo_data['servo1'] - 350
    servo2 = servo_data['servo2']
    servo_x = servo2
    servo_y = servo1
    car_x_pid.clear()
    car_y_pid.clear()
    servo_x_pid.clear()
    servo_y_pid.clear()
    center_x, center_y, area = -1, -1, 0

def init():
    print("FaceTracking Init")
    load_config()
    reset()
    initMove()

def start():
    global __isRunning
    reset()
    __isRunning = True
    print("FaceTracking Start")

def stop():
    global __isRunning
    reset()
    initMove()
    car_stop()
    __isRunning = False
    print("FaceTracking Stop")

def exit():
    global __isRunning
    reset()
    initMove()
    car_stop()
    __isRunning = False
    print("FaceTracking Exit")

def play_audio():
    os.system("mpg321 /home/pi/TurboPi/FlaskFunctions/voices/face.mp3")

# Movement control thread
def move():
    global __isRunning, car_en
    global servo_x, servo_y
    global center_x, center_y, area

    img_w, img_h = size[0], size[1]

    while True:
        if __isRunning:
            if center_x != -1 and center_y != -1:
                # Servo X control
                if abs(center_x - img_w / 2.0) < 15:
                    center_x = img_w / 2.0
                servo_x_pid.SetPoint = img_w / 2.0
                servo_x_pid.update(center_x)
                servo_x += int(servo_x_pid.output)
                servo_x = max(800, min(servo_x, 2200))

                # Servo Y control
                if abs(center_y - img_h / 2.0) < 10:
                    center_y = img_h / 2.0
                servo_y_pid.SetPoint = img_h / 2.0
                servo_y_pid.update(center_y)
                servo_y -= int(servo_y_pid.output)
                servo_y = max(1000, min(servo_y, 1900))

                # Apply servo movement
                Board.setPWMServoPulse(1, servo_y, 20)
                Board.setPWMServoPulse(2, servo_x, 20)

                # Car motion control
                if abs(area - 30000) < 2000 or servo_y < 1100:
                    car_y_pid.SetPoint = area
                else:
                    car_y_pid.SetPoint = 30000
                car_y_pid.update(area)
                dy = car_y_pid.output
                dy = 0 if abs(dy) < 20 else dy

                if abs(servo_x - servo2) < 15:
                    car_x_pid.SetPoint = servo_x
                else:
                    car_x_pid.SetPoint = servo2
                car_x_pid.update(servo_x)
                dx = car_x_pid.output
                dx = 0 if abs(dx) < 20 else dx

                car.translation(dx, dy)
                car_en = True
            else:
                if car_en:
                    car_stop()
                    car_en = False
                time.sleep(0.01)
        else:
            if car_en:
                car_stop()
                car_en = False
            time.sleep(0.01)

# Face detection and update logic
def run(img, flag):
    global __isRunning, area, center_x, center_y
    global audio_played, no_face_count

    if not __isRunning:
        return img

    img_copy = img.copy()
    img_h, img_w = img.shape[:2]
    imgRGB = cv2.cvtColor(img_copy, cv2.COLOR_BGR2RGB)
    results = faceDetection.process(imgRGB)

    if results.detections:
        no_face_count = 0
        if not audio_played:
            threading.Thread(target=play_audio, daemon=True).start()
            audio_played = True

        detection = results.detections[0]
        bboxC = detection.location_data.relative_bounding_box
        x = int(bboxC.xmin * img_w)
        y = int(bboxC.ymin * img_h)
        w = int(bboxC.width * img_w)
        h = int(bboxC.height * img_h)
        bbox = (x, y, w, h)

        cv2.rectangle(img, bbox, (0, 255, 0), 2)
        center_x = x + w // 2
        center_y = y + h // 2
        area = w * h
    else:
        no_face_count += 1
        if no_face_count >= cooldown_frames:
            audio_played = False
        center_x, center_y, area = -1, -1, 0

    return img

# Exit on Ctrl+C
def manual_stop(signum, frame):
    global __isRunning
    print('Shutting down...')
    __isRunning = False
    car_stop()
    initMove()

# Main loop
if __name__ == '__main__':
    init()
    start()
    camera = Camera.Camera()
    camera.camera_open(correction=True)
    signal.signal(signal.SIGINT, manual_stop)

    # Start movement thread
    move_thread = threading.Thread(target=move)
    move_thread.daemon = True
    move_thread.start()

    flag = 0
    while __isRunning:
        img = camera.frame
        if img is not None:
            frame = img.copy()
            Frame = run(frame, flag)
            frame_resize = cv2.resize(Frame, (320, 240))
            # cv2.imshow('frame', frame_resize)
            # key = cv2.waitKey(1)
            # if key == 27:  # Esc to exit
            #     break
        else:
            time.sleep(0.01)

    camera.camera_close()
    # cv2.destroyAllWindows()
