#!/usr/bin/python3
# coding=utf8
import sys
sys.path.append('/home/pi/TurboPi/')
import cv2
import time
import math
import signal
import Camera
import threading
import numpy as np
import yaml_handle
import HiwonderSDK.PID as PID
import HiwonderSDK.Board as Board
import HiwonderSDK.mecanum as mecanum
import os

# Light Following - Robot follows bright light sources like smartphone flashlights

if sys.version_info.major == 2:
    print('Please run this program with python3!')
    sys.exit(0)

# Initialize the mecanum chassis for movement
car = mecanum.MecanumChassis()

# Servo positions
servo1 = 1500
servo2 = 1500

# Add these near other constants at the top
MIN_LIGHT_THRESHOLD = 240  # Minimum brightness value (0-255) to consider as a valid light
MIN_LIGHT_AREA = 200      # Minimum pixel area to consider as valid light

# PID controllers for smooth movement
x_pid = PID.PID(P=0.5, I=0.01, D=0.008)  # Horizontal position control
y_pid = PID.PID(P=0.5, I=0.01, D=0.001)  # Distance/speed control

# Global variables
light_center_x = -1
light_center_y = -1
light_radius = 0
car_en = False
size = (640, 480)
__isRunning = False
threshold_value = 240  # Default brightness threshold
min_area = 100  # Minimum light source area to track
max_search_iterations = 5  # Number of attempts to find optimal threshold

# Load configuration
servo_data = None
def load_config():
    global servo_data
    servo_data = yaml_handle.get_yaml_data(yaml_handle.servo_file_path)

# Initialize servo positions
def initMove():
    Board.setPWMServoPulse(1, servo1, 1000)
    Board.setPWMServoPulse(2, servo2, 1000)

# Set buzzer for notifications
def setBuzzer(timer):
    Board.setBuzzer(0)
    Board.setBuzzer(1)
    time.sleep(timer)
    Board.setBuzzer(0)

# Stop the car's movement
def car_stop():
    car.set_velocity(0, 90, 0)

# Reset all variables to initial state
def reset():
    global servo1, servo2
    global light_center_x, light_center_y, light_radius, threshold_value
    global car_en
    
    car_en = False
    light_center_x = -1
    light_center_y = -1
    light_radius = 0
    threshold_value = 240
    servo1 = servo_data['servo1']
    servo2 = servo_data['servo2']
    x_pid.clear()
    y_pid.clear()

# App initialization
def init():
    print("LightFollowing Init")
    load_config()
    reset()
    initMove()

# Start the application
def start():
    global __isRunning
    reset()
    __isRunning = True
    print("LightFollowing Start")

# Stop the application
def stop():
    global __isRunning
    reset()
    initMove()
    car_stop()
    __isRunning = False
    print("LightFollowing Stop")

# Exit the application
def exit():
    global __isRunning
    reset()
    initMove()
    car_stop()
    __isRunning = False
    print("LightFollowing Exit")

# Set brightness threshold
def setThreshold(value):
    global threshold_value
    threshold_value = value
    return (True, ())

# Find largest contour in the image
def getAreaMaxContour(contours):
    contour_area_temp = 0
    contour_area_max = 0
    area_max_contour = None

    for c in contours:
        contour_area_temp = math.fabs(cv2.contourArea(c))
        if contour_area_temp > contour_area_max:
            contour_area_max = contour_area_temp
            if contour_area_temp > min_area:  # Filter small contours
                area_max_contour = c

    return area_max_contour, contour_area_max

# Movement control thread
# def move():
#     global __isRunning, car_en
#     global light_center_x, light_center_y, light_radius
#     global servo_x, servo_y, servo1, servo2
    
#     # Add servo tracking variables
#     servo_x = servo2
#     servo_y = servo1
    
#     # Create dedicated servo PID controllers with more aggressive tuning
#     servo_x_pid = PID.PID(P=0.15, I=0.001, D=0.0001)  # Much more aggressive than car control
#     servo_y_pid = PID.PID(P=0.15, I=0.001, D=0.0001)
    
#     img_w, img_h = size[0], size[1]
    
#     while True:
#         if __isRunning:
#             if light_center_x != -1 and light_center_y != -1:
#                 # CAMERA/SERVO TRACKING
#                 # Calculate servo movement based on light position
#                 if abs(light_center_x - img_w/2.0) > 10:  # Only move if error is significant
#                     # X axis servo control (horizontal movement)
#                     servo_x_pid.SetPoint = img_w/2.0  # Target center of image
#                     servo_x_pid.update(light_center_x)
#                     x_output = servo_x_pid.output  # Positive because right is positive error (REVERSED)
                    
#                     # Update servo position - use direct value not incremental
#                     servo_x = servo2 + int(x_output * 3)  # Amplify the movement
#                     servo_x = max(800, min(servo_x, 2200))  # Limit range
                    
#                     # Apply servo movement
#                     Board.setPWMServoPulse(2, servo_x, 20)
#                     print(f"Moving servo X to {servo_x} (base: {servo2}, error: {light_center_x - img_w/2.0})")
                
#                 if abs(light_center_y - img_h/2.0) > 10:  # Only move if error is significant
#                     # Y axis servo control (vertical movement)
#                     servo_y_pid.SetPoint = img_h/2.0  # Target center of image
#                     servo_y_pid.update(light_center_y)
#                     y_output = servo_y_pid.output  # Positive because down is positive error (REVERSED)
                    
#                     # Update servo position - use direct value not incremental
#                     servo_y = servo1 + int(y_output * 3)  # Amplify the movement
#                     servo_y = max(1000, min(servo_y, 2000))  # Limit range
                    
#                     # Apply servo movement
#                     Board.setPWMServoPulse(1, servo_y, 20)
#                     print(f"Moving servo Y to {servo_y} (base: {servo1}, error: {light_center_y - img_h/2.0})")
                
#                 # CAR MOVEMENT
#                 # Calculate movement based on light position relative to center
#                 x_error = light_center_x - img_w/2.0
#                 y_error = light_radius  # Use radius as proxy for distance
                
#                 # Use PID to smooth movement
#                 x_pid.SetPoint = 0  # Target is center of image
#                 x_pid.update(x_error)
#                 x_output = x_pid.output
                
#                 # Distance control based on light size
#                 y_pid.SetPoint = 100  # Target light size
#                 y_pid.update(y_error)
#                 y_output = y_pid.output
                
#                 # Scale outputs for appropriate vehicle movement
#                 turn_factor = -x_output / 300  # Negative because right is positive error
#                 speed_factor = min(40, max(15, 30 - y_output/5))  # Speed inversely proportional to size
                
#                 # Move the car
#                 if abs(turn_factor) > 0.8:  # If very far off-center, turn in place
#                     car.set_velocity(0, 90, turn_factor)
#                 else:  # Otherwise move forward with turning adjustment
#                     car.set_velocity(speed_factor, 90, turn_factor)
                
#                 car_en = True
#             else:
#                 # If no light detected, slowly spin to search
#                 if car_en:
#                     car.set_velocity(0, 90, 0.3)  # Slow turn to search
#                     car_en = True
                
#             time.sleep(0.01)
#         else:
#             if car_en:
#                 car_stop()
#                 car_en = False
#             time.sleep(0.01)

def move():
    global __isRunning, car_en
    global light_center_x, light_center_y, light_radius
    
    img_w, img_h = size[0], size[1]
    
    while True:
        if __isRunning:
            if light_center_x != -1:  # Only if valid light detected
                # Calculate movement (same as before)
                x_error = light_center_x - img_w/2.0
                y_error = light_radius
                
                x_pid.SetPoint = 0
                x_pid.update(x_error)
                x_output = x_pid.output
                
                y_pid.SetPoint = 100
                y_pid.update(y_error)
                y_output = y_pid.output
                
                turn_factor = -x_output / 300
                speed_factor = min(40, max(15, 30 - y_output/5))
                
                # Move toward light
                if abs(turn_factor) > 0.8:
                    car.set_velocity(0, 90, turn_factor)
                else:
                    car.set_velocity(speed_factor, 90, turn_factor)
                
                car_en = True
            else:
                # IMMEDIATELY STOP if no bright light
                if car_en:
                    car_stop()
                    car_en = False
            
            time.sleep(0.01)
        else:
            if car_en:
                car_stop()
                car_en = False
            time.sleep(0.01)

# Start movement thread
move_thread = threading.Thread(target=move)
move_thread.setDaemon(True)
move_thread.start()

# # Auto-adjust threshold based on scene brightness
# def auto_adjust_threshold(img, current_threshold):
#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     avg_brightness = np.mean(gray)
    
#     # Adjust threshold based on overall scene brightness
#     if avg_brightness > 200:  # Very bright scene
#         return min(current_threshold + 20, 250)
#     elif avg_brightness > 150:  # Moderately bright
#         return min(current_threshold + 10, 240)
#     elif avg_brightness < 80:  # Dark scene
#         return max(current_threshold - 10, 180)
#     else:  # Normal lighting
#         return current_threshold

# Main image processing function
# def run(img):
#     global __isRunning
#     global light_center_x, light_center_y, light_radius, threshold_value
    
#     if not __isRunning:
#         return img
    
#     img_copy = img.copy()
#     img_h, img_w = img.shape[:2]
    
#     # Auto-adjust threshold based on ambient light
#     if np.random.randint(0, 30) == 0:
#         threshold_value = auto_adjust_threshold(img_copy, threshold_value)
    
#     # Convert to grayscale
#     gray = cv2.cvtColor(img_copy, cv2.COLOR_BGR2GRAY)
    
#     # Apply Gaussian blur to reduce noise
#     blurred = cv2.GaussianBlur(gray, (15, 15), 0)
    
#     # Compute histogram to analyze brightness distribution
#     hist = cv2.calcHist([blurred], [0], None, [256], [0, 256])
    
#     # Calculate brightness differential - looking for significant bright spots
#     # rather than overall brightness
#     total_pixels = img_h * img_w
#     very_bright_pixels = sum(hist[int(threshold_value):])
#     bright_pixel_ratio = very_bright_pixels / total_pixels
    
#     # If too many pixels are bright, we're probably in a well-lit room with no distinct light source
#     # Adjust threshold dynamically to look for significantly brighter spots
#     if bright_pixel_ratio > 0.25:  # More than 25% of the image is considered "bright"
#         dynamic_threshold = int(min(threshold_value + 30, 250))
#     else:
#         dynamic_threshold = threshold_value
    
#     # Find the brightest spots through adaptive thresholding
#     found_light = False
#     best_contour = None
#     best_area = 0
    
#     # Try different thresholds to find the best one for current conditions
#     attempts = 0
#     test_threshold = dynamic_threshold
    
#     while not found_light and attempts < max_search_iterations:
#         _, thresh = cv2.threshold(blurred, test_threshold, 255, cv2.THRESH_BINARY)
#         contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
#         # Find largest contour
#         max_contour, max_area = getAreaMaxContour(contours)
        
#         # A valid light source should be a compact bright spot
#         if max_contour is not None and max_area > min_area:
#             # Calculate compactness (circularity) of the contour
#             perimeter = cv2.arcLength(max_contour, True)
#             if perimeter > 0:
#                 circularity = 4 * math.pi * max_area / (perimeter * perimeter)
                
#                 # More circular contours are more likely to be light sources
#                 if circularity > 0.4:  # A perfect circle has circularity of 1.0
#                     found_light = True
#                     best_contour = max_contour
#                     best_area = max_area
        
#         if not found_light:
#             # Lower threshold if no suitable contour found
#             test_threshold -= 15
#             attempts += 1
    
#     # Process found light
#     if found_light:
#         # Get moment to find center
#         M = cv2.moments(best_contour)
        
#         if M["m00"] > 0:
#             # Calculate center and radius
#             center_x = int(M["m10"] / M["m00"])
#             center_y = int(M["m01"] / M["m00"])
            
#             # Map to original image coordinates
#             light_center_x = center_x
#             light_center_y = center_y
            
#             # Calculate approximate radius based on area
#             light_radius = int(math.sqrt(best_area / math.pi))
            
#             # Draw circle around light
#             cv2.circle(img, (light_center_x, light_center_y), light_radius, (0, 255, 0), 2)
#             cv2.circle(img, (light_center_x, light_center_y), 5, (0, 0, 255), -1)
            
#             # Display info
#             cv2.putText(img, f"Light: ({light_center_x}, {light_center_y})", 
#                       (10, img_h - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
#             cv2.putText(img, f"Size: {light_radius}", 
#                       (10, img_h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
#         else:
#             light_center_x = -1
#             light_center_y = -1
#             light_radius = 0
#     else:
#         light_center_x = -1
#         light_center_y = -1
#         light_radius = 0
#         cv2.putText(img, "No light detected", (10, img_h - 30), 
#                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
#     # Display threshold info
#     cv2.putText(img, f"Threshold: {dynamic_threshold}", 
#               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
#     return img

def run(img):
    global __isRunning
    global light_center_x, light_center_y, light_radius, threshold_value
    
    if not __isRunning:
        return img
    
    img_copy = img.copy()
    img_h, img_w = img.shape[:2]
    
    # Reset light detection
    light_center_x = -1
    light_center_y = -1
    light_radius = 0
    
    # Convert to grayscale and get brightest pixel
    gray = cv2.cvtColor(img_copy, cv2.COLOR_BGR2GRAY)
    _, max_val, _, max_loc = cv2.minMaxLoc(gray)
    
    # Only proceed if we have a sufficiently bright pixel
    if max_val >= MIN_LIGHT_THRESHOLD:
        # Create binary mask of bright areas
        _, thresh = cv2.threshold(gray, MIN_LIGHT_THRESHOLD, 255, cv2.THRESH_BINARY)
        
        # Find contours of bright areas
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find largest bright contour
        max_contour, max_area = getAreaMaxContour(contours)
        
        if max_contour is not None and max_area >= MIN_LIGHT_AREA:
            # Get moment to find center
            M = cv2.moments(max_contour)
            if M["m00"] > 0:
                light_center_x = int(M["m10"] / M["m00"])
                light_center_y = int(M["m01"] / M["m00"])
                light_radius = int(math.sqrt(max_area / math.pi))
                
                # Draw visualization
                cv2.circle(img, (light_center_x, light_center_y), light_radius, (0, 255, 0), 2)
                cv2.circle(img, (light_center_x, light_center_y), 5, (0, 0, 255), -1)
                
                # Display info
                cv2.putText(img, f"Bright Light!", (10, 30), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(img, f"Size: {light_radius}", (10, 60), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Display "No light" message if nothing detected
    if light_center_x == -1:
        cv2.putText(img, "No bright light detected", (10, 30), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    return img

# Handle shutdown
def manual_stop(signum, frame):
    global __isRunning
    
    print('Shutting down...')
    __isRunning = False
    car_stop()
    initMove()

# Main execution
if __name__ == '__main__':
    init()
    start()
    camera = Camera.Camera()
    camera.camera_open(correction=True)  # Enable distortion correction
    signal.signal(signal.SIGINT, manual_stop)
    
    print("Light following active - point a bright light at the rover")
    print("Press Ctrl+C to exit")
    
    # Always run in headless mode since GTK backend isn't available
    headless_mode = True
    
    # Test servo movement to verify they're working
    print("Testing servo movement...")
    Board.setPWMServoPulse(1, servo1 + 200, 500)
    time.sleep(0.5)
    Board.setPWMServoPulse(1, servo1 - 200, 500)
    time.sleep(0.5)
    Board.setPWMServoPulse(1, servo1, 500)
    
    Board.setPWMServoPulse(2, servo2 + 200, 500)
    time.sleep(0.5)
    Board.setPWMServoPulse(2, servo2 - 200, 500)
    time.sleep(0.5)
    Board.setPWMServoPulse(2, servo2, 500)
    
    try:
        while __isRunning:
            img = camera.frame
            if img is not None:
                frame = img.copy()
                processed_frame = run(frame)
                
                # Only try to display if not in headless mode (which we never use now)
                if not headless_mode:
                    try:
                        frame_resize = cv2.resize(processed_frame, (320, 240))
                        cv2.imshow('Light Following', frame_resize)
                        key = cv2.waitKey(1)
                        if key == 27:  # Exit on ESC
                            break
                    except Exception as display_error:
                        print(f"Display error: {str(display_error)}")
                        headless_mode = True
                    
                # Print debug info to help troubleshoot more frequently
                if np.random.randint(0, 20) == 0:  # Print more often
                    if light_center_x != -1 and light_center_y != -1:
                        print(f"Light detected: pos=({light_center_x}, {light_center_y}), size={light_radius}")
                    else:
                        print("No light detected")
            else:
                time.sleep(0.01)
    except Exception as e:
        print(f"Error in main loop: {str(e)}")
    finally:
        # Ensure resources are properly released on exit
        print("Shutting down light following...")
        __isRunning = False
        time.sleep(0.2)  # Give threads time to exit
        car_stop()
        initMove()
        try:
            camera.camera_close()
        except:
            pass
        try:
            cv2.destroyAllWindows()
        except:
            pass
        print("Light following stopped")