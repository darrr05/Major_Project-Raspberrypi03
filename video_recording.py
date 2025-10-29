from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder
import time

picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": (1920, 1080)})
picam2.configure(video_config)
encoder = H264Encoder(bitrate=10000000)  # 10 Mbps

picam2.start_preview(Preview.QT)
picam2.start()
picam2.start_recording(encoder, "Number_Videos/test_video1.h264")
print("Recording started... Press Ctrl+C to stop.")

try:
    while True:
        time.sleep(1)  # Keep the script alive
except KeyboardInterrupt:
    print("\nCtrl+C detected. Stopping recording...")

picam2.stop_recording()
picam2.stop_preview()
print("Recording complete.")
