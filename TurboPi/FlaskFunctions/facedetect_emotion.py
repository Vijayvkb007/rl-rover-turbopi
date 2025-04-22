import cv2
from deepface import DeepFace
import sys
import time

# Load haar cascade classifier for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Initialize video capture
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open camera")
    sys.stdout.flush()
    sys.exit(1)

# Set camera properties for better performance
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Performance settings
frame_rate = 5  # Reduced for better DeepFace performance
skip_frames = 2  # Process every Nth frame
frame_count = 0
prev_frame_time = 0
last_valid_emotion = "no face detected"

try:
    while True:
        # Control the frame rate
        current_time = time.time()
        delta_time = current_time - prev_frame_time
        if delta_time < 1.0/frame_rate:
            time.sleep(1.0/frame_rate - delta_time)  # Sleep properly
            continue
        
        prev_frame_time = time.time()
        
        # Capture frame
        ret, frame = cap.read()
        if not ret:
            print("no face detected")
            sys.stdout.flush()
            time.sleep(0.1)  # Short pause before retrying
            continue
        
        # Skip frames for performance
        frame_count += 1
        if frame_count % skip_frames != 0:
            # Still output the last valid emotion to keep communication flowing
            if last_valid_emotion != "no face detected":
                print(last_valid_emotion)
                sys.stdout.flush()
            continue
        
        # Convert to grayscale for face detection
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces with optimized parameters
        faces = face_cascade.detectMultiScale(
            gray_frame, 
            scaleFactor=1.2,  # Faster detection with slight accuracy tradeoff
            minNeighbors=5, 
            minSize=(50, 50)  # Increased minimum face size
        )
        
        if len(faces) > 0:
            # Find the largest face (usually the closest person)
            largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
            (x, y, w, h) = largest_face
            
            # Add margin around face for better emotion detection
            margin = int(0.2 * w)  # 20% margin
            x_with_margin = max(0, x - margin)
            y_with_margin = max(0, y - margin)
            w_with_margin = min(frame.shape[1] - x_with_margin, w + 2*margin)
            h_with_margin = min(frame.shape[0] - y_with_margin, h + 2*margin)
            
            face_roi = frame[y_with_margin:y_with_margin+h_with_margin, 
                             x_with_margin:x_with_margin+w_with_margin]
            
            # Skip very small faces which might give unreliable results
            if w*h < 2500:  # Increased threshold
                print("face too small")
                sys.stdout.flush()
                continue
            
            try:
                # Analyze the face - convert to RGB first
                rgb_face_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB)
                result = DeepFace.analyze(
                    rgb_face_roi, 
                    actions=['emotion'], 
                    enforce_detection=False,
                    silent=True  # Suppress DeepFace warnings
                )
                
                if result and len(result) > 0:
                    output_emotion = result[0]['dominant_emotion']
                    last_valid_emotion = output_emotion
                    
                    # Draw rectangle and emotion on frame
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, output_emotion, (x, y-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    
                    # Output emotion
                    print(output_emotion)
                    sys.stdout.flush()
                
            except Exception as e:
                print(f"no face detected")  # Simplified error output
                sys.stdout.flush()
        else:
            print("no face detected")
            sys.stdout.flush()
        
        # # Display the output frame
        # cv2.imshow('Emotion Detection', frame)
        
        # # Break loop on 'q' press
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break
        
except KeyboardInterrupt:
    print("Exiting emotion detection")
    sys.stdout.flush()
except Exception as e:
    print(f"Fatal error: {str(e)}")
    sys.stdout.flush()
finally:
    # Clean up
    cap.release()
    # cv2.destroyAllWindows()
