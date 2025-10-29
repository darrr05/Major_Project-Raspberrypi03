import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from picamera2 import Picamera2
import pytesseract
import cv2
import numpy as np
import os
import time

# Output directory
output_dir = "processed_images"
os.makedirs(output_dir, exist_ok=True)

# Initialize camera with autofocus
picam2 = Picamera2()
# Check if autofocus is available
camera_config = picam2.create_preview_configuration(main={"size": (640, 480)})
# Enable continuous autofocus if supported
if "AfMode" in picam2.camera_controls:
    camera_config["controls"] = {"AfMode": 2}  # 2 = Continuous autofocus
else:
    print("Autofocus not supported by this camera module.")
picam2.configure(camera_config)
picam2.start()

# OCR function
def extract_numbers(image):
    config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(image, config=config)
    return ''.join(filter(str.isdigit, text))

# GUI class
class OCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OCR Number Detection with Autofocus")
        self.frame = ttk.Frame(self.root)
        self.frame.pack()

        self.label = ttk.Label(self.frame, text="Live Camera Feed (Autofocus Enabled)")
        self.label.pack()

        self.canvas = tk.Label(self.frame)
        self.canvas.pack()

        self.result_label = ttk.Label(self.frame, text="Detected: ", font=("Arial", 16))
        self.result_label.pack(pady=10)

        self.capture_button = ttk.Button(self.frame, text="Capture and OCR", command=self.capture_and_process)
        self.capture_button.pack()

        # ROI coordinates (adjust these)
        self.roi_x1, self.roi_y1 = 270, 190
        self.roi_x2, self.roi_y2 = 370, 290

        self.running = True
        self.update_preview()

    def update_preview(self):
        if not self.running:
            return
        frame = picam2.capture_array()

        # Draw ROI on frame
        cv2.rectangle(frame, (self.roi_x1, self.roi_y1), (self.roi_x2, self.roi_y2), (0, 255, 0), 2)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.canvas.imgtk = imgtk
        self.canvas.configure(image=imgtk)
        self.root.after(30, self.update_preview)

    def capture_and_process(self):
        frame = picam2.capture_array()

        # Crop ROI
        roi = frame[self.roi_y1:self.roi_y2, self.roi_x1:self.roi_x2]

        # Save full frame for debugging
        filename = f"processed_{int(time.time())}.png"
        output_path = os.path.join(output_dir, filename)
        cv2.imwrite(output_path, frame)
        print(f"Saved image to {output_path}")

        # OCR only on cropped ROI
        text = extract_numbers(roi)
        print("Detected:", text)
        self.result_label.configure(text=f"Detected: {text}")

    def stop(self):
        self.running = False
        picam2.stop()
        self.root.destroy()

# Start the GUI
root = tk.Tk()
app = OCRApp(root)
root.protocol("WM_DELETE_WINDOW", app.stop)
root.mainloop()