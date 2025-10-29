import subprocess
import datetime
import os

save_folder = "/home/pi/Pictures"

os.makedirs(save_folder, exist_ok=True)

print("Live feed running in a separate window.")
print("Press Enter to capture a photo, or type 'q' then Enter to quit.")

while True:
    user_input = input("Take photo? ")
    if user_input.lower() == 'q':
        print("Exiting.")
        break

    # Timestamp-based filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"photo_{timestamp}.jpg"
    filepath = os.path.join(save_folder, filename)

    # FFmpeg command to capture one image
    command = [
        "ffmpeg",
        "-rtsp_transport", "tcp",  # stable connection
        "-i", "rtsp://admin:1M_25383@192.168.1.64:554/Streaming/Channels/101",
        "-frames:v", "1",
        "-q:v", "2",
        filepath
    ]

    print(f"Capturing photo... Saving as {filepath}")
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Photo saved.\n")
