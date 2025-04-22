# TurboPi/FlaskFunctions/CleanupMotors.py
import RPi.GPIO as GPIO
import time

# Example motor pins — adjust as needed
motor_pins = [17, 18, 27, 22]

GPIO.setmode(GPIO.BCM)
for pin in motor_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

GPIO.cleanup()
