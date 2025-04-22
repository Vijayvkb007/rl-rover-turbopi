from flask import Flask, make_response, render_template
import subprocess
import os
import psutil
import threading
import sys
sys.path.append('/home/pi/TurboPi/')

os.environ['FLASK_APP'] = 'FlaskApp'
os.environ['FLASK_ENV'] = 'development'

app = Flask(__name__)

active_process = {}

def terminate_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass

# Function to handle subprocess in a separate thread
def run_gesture_script():
    with open("/home/pi/gesture_output.log", "w") as f:
        process = subprocess.Popen(['sudo', 'python', 'TurboPi/FlaskFunctions/GestureRecognition.py'], stdout=f, stderr=subprocess.STDOUT)
    active_process['gesture'] = process
    process.wait()  # Wait for process to finish, blocking the thread until done
    
def run_lightfollower_script():
    process = subprocess.Popen(['sudo', 'python', 'TurboPi/FlaskFunctions/LightFollower.py'])
    active_process['lightfollower'] = process
    process.wait()
    
def run_facetracking_script():
    process = subprocess.Popen(['sudo', 'python', 'TurboPi/FlaskFunctions/FaceTracking.py'])
    active_process['facetracking'] = process
    process.wait()
    
def run_emotiondetector_script():
    with open("/home/pi/emotion_output.log", "w") as f:
        process = subprocess.Popen(['sudo', 'python', 'TurboPi/FlaskFunctions/emotion_recognition_final.py'], stdout=f, stderr=subprocess.STDOUT)
    active_process['emotiondetector'] = process
    process.wait()
    
def run_trafficmodel_script():
    process = subprocess.Popen(['sudo', 'python', 'TurboPi/FlaskFunctions/TrafficModel.py'])
    active_process['trafficmodel'] = process
    process.wait()

@app.route('/')
def index():
    # Kill any active process related to gesture
    processes_to_terminate = list(active_process.items())
    for name, process in processes_to_terminate:
        if process.poll() is None:  # If process is still running
            terminate_process_tree(process.pid)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
            if name in active_process: del active_process[name]

    subprocess.call(['sudo', 'python', 'TurboPi/FlaskFunctions/CleanMotors.py'])
    # Render index template
    response = make_response(render_template('index.html'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/gesture')
def gesture():
    # Check if gesture process is already running
    if 'gesture' in active_process and active_process['gesture'].poll() is None:
        # Stop the gesture process if it's running
        active_process['gesture'].terminate()
        try:
            active_process['gesture'].wait(timeout=3)
        except subprocess.TimeoutExpired:
            active_process['gesture'].kill()

    # Start the gesture recognition in a separate thread
    gesture_thread = threading.Thread(target=run_gesture_script)
    gesture_thread.start()

    # Render gesture template
    return render_template('gesture.html')

@app.route('/gesture/log')
def gesture_log():
    try:
        with open("/home/pi/gesture_output.log", "r") as f:
            return f.read()[-2000:]  # return last few lines
    except:
        return "Log unavailable"

@app.route('/emotion/log')
def emotion_log():
    try:
        with open("/home/pi/emotion_output.log", "r") as f:
            return f.read()[-2000:]  # return last few lines
    except:
        return "Log unavailable"

@app.route('/lightfollower')
def lightfollower():
    # Check if lightfollower process is already running
    if 'lightfollower' in active_process and active_process['lightfollower'].poll() is None:
        # Stop the lightfollower process if it's running
        active_process['lightfollower'].terminate()
        try:
            active_process['lightfollower'].wait(timeout=3)
        except subprocess.TimeoutExpired:
            active_process['lightfollower'].kill()

    # Start the lightfollower recognition in a separate thread
    lightfollower_thread = threading.Thread(target=run_lightfollower_script)
    lightfollower_thread.start()

    # Render lightfollower template
    return render_template('lightfollower.html')

@app.route('/facetracking')
def facetracking():
    # Check if gesture process is already running
    if 'facetracking' in active_process and active_process['facetracking'].poll() is None:
        # Stop the facetracking process if it's running
        active_process['facetracking'].terminate()
        try:
            active_process['facetracking'].wait(timeout=3)
        except subprocess.TimeoutExpired:
            active_process['facetracking'].kill()

    # Start the facetracking recognition in a separate thread
    facetracking_thread = threading.Thread(target=run_facetracking_script)
    facetracking_thread.start()

    # Render facetracking template
    return render_template('facetracking.html')

@app.route('/emotiondetector')
def emotiondetector():
    # Check if gesture process is already running
    if 'emotiondetector' in active_process and active_process['emotiondetector'].poll() is None:
        # Stop the emotiondetector process if it's running
        active_process['emotiondetector'].terminate()
        try:
            active_process['emotiondetector'].wait(timeout=3)
        except subprocess.TimeoutExpired:
            active_process['emotiondetector'].kill()

    # Start the emotiondetector recognition in a separate thread
    emotiondetector_thread = threading.Thread(target=run_emotiondetector_script)
    emotiondetector_thread.start()

    # Render emotiondetector template
    return render_template('emotiondetector.html')

@app.route('/trafficmodel')
def trafficmodel():
    # Check if gesture process is already running
    if 'trafficmodel' in active_process and active_process['trafficmodel'].poll() is None:
        # Stop the trafficmodel process if it's running
        active_process['trafficmodel'].terminate()
        try:
            active_process['trafficmodel'].wait(timeout=3)
        except subprocess.TimeoutExpired:
            active_process['trafficmodel'].kill()

    # Start the trafficmodel recognition in a separate thread
    trafficmodel_thread = threading.Thread(target=run_trafficmodel_script)
    trafficmodel_thread.start()

    # Render trafficmodel template
    return render_template('trafficmodel.html')
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)