import os
import cv2
import time
from picamera2 import Picamera2

# ==== CONFIGURATION ====
SAVE_DIR = "new_digit_dataset"
CAPTURE_INTERVAL = 0.1  # seconds between frames
RECORD_DURATION = 10    # seconds per digit
AFTER_RECORD_PREVIEW = 3  # seconds to preview after recording

# ==== Ensure save directory exists ====
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# ==== Start camera and preview immediately ====
picam2 = Picamera2(0)
picam2.preview_configuration.main.size = (640, 480)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")

# Enable continuous autofocus
picam2.set_controls({"AfMode": 2})

picam2.start()
print("Camera started. Showing live preview...")

# ==== Prompt for digit before entering preview loop ====
while True:
    digit = input("Enter the digit you are recording (0-9): ").strip()
    if digit.isdigit() and 0 <= int(digit) <= 9:
        break
    print("Invalid digit. Try again.")

# ==== Wait for Enter key to start recording (show live preview before that) ====
print("Press ENTER to start recording, or 'q' in the preview window to quit.")
while True:
    frame = picam2.capture_array()
    cv2.imshow("Live Preview", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        print("Quit before recording.")
        picam2.close()
        cv2.destroyAllWindows()
        exit(0)

    if cv2.getWindowProperty("Live Preview", cv2.WND_PROP_VISIBLE) < 1:
        print("Preview window closed.")
        picam2.close()
        exit(0)

    if key == 13:  # ENTER key
        break

# ==== Recording ====
print(f"Recording digit '{digit}' for {RECORD_DURATION} seconds...")
start_time = time.time()
frame_count = 0

try:
    while time.time() - start_time < RECORD_DURATION:
        frame = picam2.capture_array()

        # Show preview window
        cv2.imshow("Live Preview", frame)

        # Save frame
        frame_name = f"{digit}_{frame_count:03d}.jpg"
        save_path = os.path.join(SAVE_DIR, frame_name)
        cv2.imwrite(save_path, frame)

        frame_count += 1
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Recording stopped by user.")
            break

        time.sleep(CAPTURE_INTERVAL)

    print(f"Saved {frame_count} images for digit '{digit}' in '{SAVE_DIR}'")

    # === Preview AFTER recording ===
    print(f"Previewing for {AFTER_RECORD_PREVIEW} seconds...")
    end_time = time.time() + AFTER_RECORD_PREVIEW
    while time.time() < end_time:
        frame = picam2.capture_array()
        cv2.imshow("Live Preview", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("Recording interrupted.")

finally:
    picam2.close()
    cv2.destroyAllWindows()
