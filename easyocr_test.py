import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from picamera2 import Picamera2
import easyocr
import cv2
import numpy as np
import os

# Create output folder (optional)
os.makedirs("processed_images", exist_ok=True)

# Initialize camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
picam2.start()

# Initialize EasyOCR
reader = easyocr.Reader(['en'], gpu=False)

class LiveEasyOCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Live EasyOCR Number Detection")

        self.frame = ttk.Frame(self.root)
        self.frame.pack()

        self.canvas = tk.Label(self.frame)
        self.canvas.pack()

        self.result_label = ttk.Label(self.frame, text="Detected: ", font=("Arial", 16))
        self.result_label.pack(pady=10)

        # ROI square box
        self.roi_x1, self.roi_y1 = 270, 190
        self.roi_x2, self.roi_y2 = self.roi_x1 + 100, self.roi_y1 + 100

        self.update_feed()

    def preprocess_roi(self, roi):
        # Convert to grayscale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Adaptive thresholding to enhance contrast
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)
        return thresh

    def update_feed(self):
        frame = picam2.capture_array()

        # Draw green ROI box
        cv2.rectangle(frame, (self.roi_x1, self.roi_y1), (self.roi_x2, self.roi_y2), (0, 255, 0), 2)

        # Crop ROI
        roi = frame[self.roi_y1:self.roi_y2, self.roi_x1:self.roi_x2]
        preprocessed_roi = self.preprocess_roi(roi)

        # Run OCR on preprocessed image
        results = reader.readtext(preprocessed_roi, allowlist='0123456789')

        # Extract only digits
        #detected = "No number"
        #for _, text, conf in results:
         #   digits = ''.join(filter(str.isdigit, text))
          #  if digits:
          #      detected = digits
          #     break

        # Update GUI text
        self.result_label.config(text=f"Detected: {results}")

        # Display frame with ROI in GUI
        #rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)
        self.canvas.imgtk = imgtk
        self.canvas.configure(image=imgtk)

        # Refresh every 300 ms
        self.root.after(300, self.update_feed)

# Launch app
root = tk.Tk()
app = LiveEasyOCRApp(root)
root.mainloop()
