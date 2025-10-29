import cv2
from ultralytics import YOLO

# Load a YOLOv8 model (choose 'yolov8n' for better Raspberry Pi performance)
model = YOLO('yolov8n.pt')  # You can use yolov8s.pt or a custom model too

# RTSP stream URL from dome camera
rtsp_url = 'rtsp://admin:1M_25383@192.168.1.64:554/Channels/101'

# Open RTSP stream
cap = cv2.VideoCapture(rtsp_url)

if not cap.isOpened():
    print("⚠️ Failed to open RTSP stream.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Failed to grab frame.")
        break

    # Resize for speed if needed
    # frame = cv2.resize(frame, (640, 480))

    # Run YOLOv8 inference
    results = model(frame)

    # Visualize results (draw boxes on image)
    annotated_frame = results[0].plot()

    # Show the result
    cv2.imshow("YOLOv8 + Dome Camera", annotated_frame)

    # Break on 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
