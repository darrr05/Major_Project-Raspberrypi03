import threading
import cv2
from picamera2 import Picamera2
import pyzbar.pyzbar as pyzbar

# Function for number detection (USB camera)
def number_detection():
    # Initialize USB Camera (usually 0 for first camera)
    usb_camera = cv2.VideoCapture(0)
    
    while True:
        ret, frame = usb_camera.read()
        if not ret:
            break

        # Example of number detection (add your detection logic here)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, threshold = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        cv2.imshow("Number Detection (USB Camera)", threshold)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    usb_camera.release()
    cv2.destroyAllWindows()

# Function for barcode detection (Pi Camera)
def barcode_detection():
    # Initialize Pi Camera
    picam2 = Picamera2()
    picam2.start_preview()

    while True:
        # Capture an image from the Pi camera
        frame = picam2.capture_array()

        # Detect barcodes using pyzbar
        barcodes = pyzbar.decode(frame)
        
        for barcode in barcodes:
            # Draw a rectangle around the barcode
            rect_points = barcode.polygon
            if len(rect_points) == 4:
                pts = rect_points
            else:
                pts = cv2.convexHull(np.array([pt for pt in rect_points], dtype=np.float32))

            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, (0, 255, 0), 3)

            # Get barcode data
            barcode_data = barcode.data.decode("utf-8")
            barcode_type = barcode.type
            text = f"{barcode_data} ({barcode_type})"
            cv2.putText(frame, text, (barcode.rect[0], barcode.rect[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
        
        # Display the image with barcode detection
        cv2.imshow("Barcode Detection (Pi Camera)", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    picam2.stop_preview()
    cv2.destroyAllWindows()

# Running both functions in separate threads
def run_concurrent_detection():
    # Create threads for each detection process
    number_detection_thread = threading.Thread(target=number_detection)
    barcode_detection_thread = threading.Thread(target=barcode_detection)

    # Start both threads
    number_detection_thread.start()
    barcode_detection_thread.start()

    # Wait for both threads to complete
    number_detection_thread.join()
    barcode_detection_thread.join()

if __name__ == "__main__":
    run_concurrent_detection()
