#!/usr/bin/python3
# coding=utf8
import sys
sys.path.append('/home/pi/TurboPi/')
import time
import signal
import threading
import subprocess
import HiwonderSDK.Board as Board
import HiwonderSDK.mecanum as mecanum
import os
from collections import Counter
import select
import numpy as np

os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"  # Usually this path for 'pi' user
os.environ["PULSE_SERVER"] = "/run/user/1000/pulse/native"
os.environ["HOME"] = "/home/pi"

# Path to Python binary inside your virtual environment
venv_python = "/home/pi/TurboPi/FlaskFunctions/deepface_venv/bin/python3.9"
ml_script_path = "/home/pi/TurboPi/FlaskFunctions/facedetect_emotion.py"

car = mecanum.MecanumChassis()

# Verify Python version
if sys.version_info.major == 2:
    print('Please run this program with python3!')
    sys.exit(0)

# Global variables
servo1 = 1500
servo2 = 1500
stop_st = False
servo_data = None
__isRunning = False
ml_process = None
results_lock = False  # Added: Lock to prevent new actions while one is executing
emotion_list = []     # Added: List to collect multiple emotion readings
ml_error_count = 0    # Added: Counter to track ML process errors

def load_config():
    global servo_data
    
    try:
        import yaml_handle
        servo_data = yaml_handle.get_yaml_data(yaml_handle.servo_file_path)
    except Exception as e:
        print(f"Error loading config: {e}")
        # Set default values if config can't be loaded
        servo_data = {'servo1': 1600, 'servo2': 1500}

def initMove():
    Board.setPWMServoPulse(1, servo1, 1000)
    Board.setPWMServoPulse(2, servo2, 1000)

def reset(): 
    global stop_st, results_lock, emotion_list
    global servo1, servo2
    
    stop_st = False
    results_lock = False  # Reset the results lock
    emotion_list = []     # Clear the emotion list
    servo1 = servo_data['servo1'] - 100
    servo2 = servo_data['servo2']

def init():
    print("EmotionDetection Init")
    load_config()
    reset()
    initMove()
    start_ml_process()

def check_ml_process():
    """Check if ML process is running and restart if needed"""
    global ml_process, ml_error_count
    
    if ml_process is None or ml_process.poll() is not None:
        ml_error_count += 1
        print(f"ML process not running, restarting... (attempt {ml_error_count})")
        
        # Kill existing process if it's hanging
        if ml_process:
            try:
                ml_process.kill()
            except:
                pass
                
        start_ml_process()
        time.sleep(1)  # Give it time to initialize
        
        # Reset error count if too many consecutive errors
        if ml_error_count > 5:
            print("Too many ML process failures, resetting...")
            time.sleep(5)
            ml_error_count = 0
            
        return False
    return True

def start_ml_process():
    global ml_process
    if ml_process:
        try:
            ml_process.kill()
        except:
            pass
    # Start the ML subprocess
    print("Starting ML process...")
    try:
        ml_process = subprocess.Popen(
            [venv_python, ml_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        )
        print("ML process started")
    except Exception as e:
        print(f"Failed to start ML process: {e}")
        ml_process = None

def start():
    global __isRunning
    reset()
    __isRunning = True
    print("EmotionDetection Start")

def stop():
    global stop_st
    global __isRunning
    stop_st = True
    __isRunning = False
    print("EmotionDetection Stop")

def exit():
    global stop_st, ml_process
    global __isRunning
    stop_st = True
    __isRunning = False
    
    # Terminate ML process
    if ml_process:
        try:
            ml_process.send_signal(signal.SIGINT)
            ml_process.wait(timeout=3)
        except:
            ml_process.kill()
        print("ML process terminated")
    
    print("EmotionDetection Exit")

def setBuzzer(timer):
    Board.setBuzzer(0)
    Board.setBuzzer(1)
    time.sleep(timer)
    Board.setBuzzer(0)

def car_stop():
    car.set_velocity(0, 90, 0)

def get_latest_emotion():
    """Improved function to get the latest emotion from the ML process"""
    global ml_error_count
    
    # Check if ML process is running properly
    if not check_ml_process():
        return "no face detected"
    
    # Read and discard all previous outputs to get to the latest
    latest_emotion = "no face detected"
    try:
        # Read all available lines without blocking
        while True:
            ready_to_read = select.select([ml_process.stdout], [], [], 0.0)[0]
            if not ready_to_read:
                break
                
            line = ml_process.stdout.readline().strip()
            if line:
                latest_emotion = line  # Keep updating with newer lines
        
        # Reset error count on successful read
        if latest_emotion != "no face detected":
            ml_error_count = 0
            
    except Exception as e:
        ml_error_count += 1
        print(f"Error reading from ML process: {e}")
        
        # Restart process if multiple read errors
        if ml_error_count > 3:
            print("Multiple read errors, restarting ML process")
            start_ml_process()
            time.sleep(1)
            ml_error_count = 0
    
    # print(f"Latest detected emotion: {latest_emotion}")
    return latest_emotion

# Define actions for different emotions
def perform_emotion_action(emotion):
    """Perform action based on detected emotion"""
    global results_lock
    
    if not emotion or emotion == "no face detected":
        print("No face detected or no emotion specified")
        results_lock = False
        return
        
    emotion = emotion.lower()
    print(f"Performing action for emotion: {emotion}")
    
    try:
        if 'happy' in emotion:
            print("Detected: Happy - Starting happy movement")
            os.system("mpg321 /home/pi/TurboPi/FlaskFunctions/voices/happy.mp3")
            # Happy dance - spin around
            car.set_velocity(0, 90, 0.5)
            time.sleep(2)
            car.set_velocity(0, 90, -0.5)
            time.sleep(2)
            car.set_velocity(0, 90, 0)
        elif 'sad' in emotion:
            print("Detected: Sad - Starting sad movement")
            os.system("mpg321 /home/pi/TurboPi/FlaskFunctions/voices/sad.mp3")
            # Slow backward movement
            car.set_velocity(45, 270, 0)
            time.sleep(1)
            car.set_velocity(0, 90, 0)
        elif 'angry' in emotion:
            print("Detected: Angry - Starting angry movement")
            os.system("mpg321 /home/pi/TurboPi/FlaskFunctions/voices/angry.mp3")
            # Quick zigzag movement
            car.set_velocity(40, 45, 0)
            time.sleep(0.5)
            car.set_velocity(40, 135, 0)
            time.sleep(0.5)
            car.set_velocity(40, 45, 0)
            time.sleep(0.5)
            car.set_velocity(0, 90, 0)
        elif 'surprise' in emotion:
            print("Detected: Surprise - Starting surprise movement")
            os.system("mpg321 /home/pi/TurboPi/FlaskFunctions/voices/surprise.mp3")
            # CHANGED: Quick backward then forward (changed from right-left to backward-forward)
            car.set_velocity(40, 270, 0)  # Backward
            time.sleep(0.5)
            car.set_velocity(40, 90, 0)   # Forward
            time.sleep(1)
            car.set_velocity(0, 90, 0)
        elif 'fear' in emotion:
            print("Detected: Fear - Starting fear movement")
            os.system("mpg321 /home/pi/TurboPi/FlaskFunctions/voices/fear.mp3")
            # Trembling movement
            for _ in range(3):
                car.set_velocity(15, 80, 0)
                time.sleep(0.2)
                car.set_velocity(15, 100, 0)
                time.sleep(0.2)
            car.set_velocity(0, 90, 0)
        elif 'disgust' in emotion:
            print("Detected: Disgust - Starting disgust movement")
            # os.system("mpg321 /home/pi/TurboPi/Functions/voices/disgust.mp3")
            # CHANGED: Move away (changed from right to backward)
            car.set_velocity(40, 270, 0)  # Backward movement
            time.sleep(1.5)
            car.set_velocity(0, 90, 0)
        elif 'neutral' in emotion:
            print("Detected: Neutral - Starting neutral movement")
            os.system("mpg321 /home/pi/TurboPi/FlaskFunctions/voices/neutral.mp3")
            # CHANGED: Gentle forward movement (changed from left to forward)
            car.set_velocity(50, 90, 0)  # Forward
            time.sleep(1)
            car.set_velocity(0, 90, 0)
        else:
            print(f"No action for emotion: {emotion}")
            
        print("Action completed")
    except Exception as e:
        print(f"Error performing action: {e}")
    finally:
        # Always release the lock when done
        results_lock = False

def move():
    global __isRunning, stop_st, results_lock, emotion_list
    
    while True:
        if __isRunning:
            try:
                # Only process new emotions when not already performing an action
                if not results_lock:
                    # Get the latest emotion
                    emotion = get_latest_emotion()
                    
                    # If a valid emotion is detected, add it to our list
                    if emotion != "no face detected":
                        emotion_list.append(emotion)
                        print(f"Detected: {emotion}, collected {len(emotion_list)}/5")
                        
                        # Once we have 5 samples, determine most common emotion and act
                        if len(emotion_list) >= 5:
                            # Find most common emotion from the list
                            final_emotion = Counter(emotion_list).most_common(1)[0][0]
                            
                            # Set the lock and clear the list
                            results_lock = True
                            emotion_list = []
                            
                            # Perform action based on most common emotion
                            perform_emotion_action(final_emotion)
                
                # Handle stop requests
                if stop_st:
                    initMove()  
                    car_stop() 
                    stop_st = False
                    time.sleep(0.5)
                
                # Add a small delay before checking for the next emotion
                # Reduced from 0.5s to 0.1s to be more responsive
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in move thread: {e}")
                time.sleep(0.1)
        else:
            if stop_st:
                initMove()  
                car_stop() 
                stop_st = False
                time.sleep(0.5)               
            time.sleep(0.01)

def manual_stop(signum, frame):
    global __isRunning, ml_process
    
    print('Exiting...')
    __isRunning = False
    car_stop()  
    initMove()
    
    # Kill ML process
    if ml_process:
        try:
            ml_process.send_signal(signal.SIGINT)
            ml_process.wait(timeout=3)
        except:
            ml_process.kill()
        print("ML process terminated")

if __name__ == '__main__':
    init()
    start()
    
    # Start movement thread
    move_thread = threading.Thread(target=move)
    move_thread.setDaemon(True)
    move_thread.start()
    
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, manual_stop)
    
    try:
        # Main loop - just keep the process alive
        print("Main program running. Press Ctrl+C to exit.")
        while __isRunning:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received")
    finally:
        manual_stop(None, None)