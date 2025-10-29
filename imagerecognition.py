import time
import libcamera
import cv2
import easyocr
import os
import re
import numpy as np
import tkinter as tk
from tkinter import Label, Button
from PIL import Image, ImageTk
from picamera2 import Picamera2

class ImageRecognitionApp:
    def __init__(self, parent=None):
        self.parent = parent
        self.output_folder = "processed_images"
        os.makedirs(self.output_folder, exist_ok=True)
        self.reader = easyocr.Reader(['en'], gpu=False)
        self.camera_width = 800
        self.camera_height = 480
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_video_configuration(main={"size": (self.camera_width, self.camera_height)}))
        self.picam2.set_controls({'AfMode': 2})
        self.picam2.set_controls({'HdrMode': libcamera.controls.HdrModeEnum.SingleExposure})
        self.picam2.start()
        time.sleep(2)
        
        # Initialize ROI and other flags
        self.roi_x1, self.roi_y1, self.roi_x2, self.roi_y2 = None, None, None, None
        self.temp_roi_x1, self.temp_roi_y1, self.temp_roi_x2, self.temp_roi_y2 = None, None, None, None
        self.dragging = False
        self.roi_set = False
        self.detection_started = False
        self.setting_roi = False

        # Setup the Tkinter window
        self.root = tk.Toplevel(parent) if parent else tk.Tk()
        self.root.title("Camera Feed with OCR Detection")
        self.root.geometry("800x600")
        self.label = Label(self.root)
        self.label.pack()

        # Setup buttons
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.set_roi_button = Button(self.button_frame, text="Set ROI", width=15, height=2, command=self.enable_set_roi)
        self.set_roi_button.pack(side=tk.LEFT, padx=5)
        self.delete_roi_button = Button(self.button_frame, text="Delete ROI", width=15, height=2, command=self.delete_roi, state=tk.DISABLED)
        self.delete_roi_button.pack(side=tk.LEFT, padx=5)
        self.start_button = Button(self.button_frame, text="Start Detection", width=15, height=2, command=self.start_detection)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.quit_button = Button(self.button_frame, text="Quit", width=15, height=2, command=self.close)
        self.quit_button.pack(side=tk.LEFT, padx=5)

        # Bind mouse events for ROI selection
        self.label.bind("<ButtonPress-1>", self.on_mouse_press)
        self.label.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.label.bind("<B1-Motion>", self.on_mouse_move)

        # Start updating the frame
        self.update_frame()

    def preprocess(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_image = clahe.apply(gray)
        adaptive_thresh = cv2.adaptiveThreshold(contrast_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                               cv2.THRESH_BINARY, 11, 2)
        denoised_image = cv2.GaussianBlur(adaptive_thresh, (5, 5), 0)
        clean_image = cv2.medianBlur(denoised_image, 3)
        return clean_image

    def process_image(self, image):
        if self.roi_x1 and self.roi_y1 and self.roi_x2 and self.roi_y2:
            cv2.rectangle(image, (self.roi_x1, self.roi_y1), (self.roi_x2, self.roi_y2), (0, 255, 0), 2)
            x1, x2 = min(self.roi_x1, self.roi_x2), max(self.roi_x1, self.roi_x2)
            y1, y2 = min(self.roi_y1, self.roi_y2), max(self.roi_y1, self.roi_y2)
            cropped_image = image[y1:y2, x1:x2]
            preprocessed_image = self.preprocess(cropped_image)
            results = self.reader.readtext(preprocessed_image)
            found_summary = False
            summary_value = None
            final_text = ""
            for bbox, text, prob in results:
                final_text += text + " "
                if "summary" in text.lower():
                    found_summary = True
            summary_match = re.search(r'(?:Summary.*?\s*(\d+)|(\d+)\s*.*?Summary)', final_text, re.IGNORECASE)
            if summary_match:
                summary_value = int(summary_match.group(1) or summary_match.group(2))
            
            # If the word "summary" is detected, disable autofocus
            if found_summary:
                self.disable_autofocus()

            return summary_value, found_summary
        return None, False

    def disable_autofocus(self):
        """
        Disable autofocus after detecting the word "summary".
        """
        self.picam2.set_controls({'AfMode': 0})  # Disable autofocus

    def scale_coordinates(self, x, y):
        label_x = self.label.winfo_width()
        label_y = self.label.winfo_height()
        scale_x = self.camera_width / label_x if label_x > 0 else 1
        scale_y = self.camera_height / label_y if label_y > 0 else 1
        return max(0, min(self.camera_width, int(x * scale_x))), max(0, min(self.camera_height, int(y * scale_y)))

    def on_mouse_press(self, event):
        if self.setting_roi and not self.detection_started:
            if 0 <= event.x <= self.label.winfo_width() and 0 <= event.y <= self.label.winfo_height():
                self.temp_roi_x1, self.temp_roi_y1 = self.scale_coordinates(event.x, event.y)
                self.dragging = True

    def on_mouse_release(self, event):
        if self.setting_roi and not self.detection_started:
            if 0 <= event.x <= self.label.winfo_width() and 0 <= event.y <= self.label.winfo_height():
                self.temp_roi_x2, self.temp_roi_y2 = self.scale_coordinates(event.x, event.y)
                self.dragging = False

    def on_mouse_move(self, event):
        if self.dragging and self.setting_roi and not self.detection_started:
            if 0 <= event.x <= self.label.winfo_width() and 0 <= event.y <= self.label.winfo_height():
                self.temp_roi_x2, self.temp_roi_y2 = self.scale_coordinates(event.x, event.y)

    def enable_set_roi(self):
        if not self.detection_started:
            self.setting_roi = True
            self.set_roi_button.config(text="Confirm ROI", command=self.confirm_set_roi)
            print("Set ROI mode enabled. Draw your ROI now.")

    def confirm_set_roi(self):
        if self.setting_roi and self.temp_roi_x1 and self.temp_roi_y1 and self.temp_roi_x2 and self.temp_roi_y2:
            self.roi_x1, self.roi_y1, self.roi_x2, self.roi_y2 = self.temp_roi_x1, self.temp_roi_y1, self.temp_roi_x2, self.temp_roi_y2
            self.roi_set = True
            self.setting_roi = False
            self.set_roi_button.config(text="Set ROI", command=self.enable_set_roi)
            self.delete_roi_button.config(state=tk.NORMAL)
            print(f"ROI set to ({self.roi_x1}, {self.roi_y1}), ({self.roi_x2}, {self.roi_y2})")

    def delete_roi(self):
        if self.roi_set:
            self.roi_x1, self.roi_y1, self.roi_x2, self.roi_y2 = None, None, None, None
            self.roi_set = False
            self.delete_roi_button.config(state=tk.DISABLED)
            print("ROI deleted.")

    def start_detection(self):
        if self.roi_set and self.roi_x1 and self.roi_y1 and self.roi_x2 and self.roi_y2:
            self.detection_started = True
            self.start_button.config(text="Stop Detection", command=self.stop_detection)
            print("Detection Started!")
        else:
            print("Please set an ROI first before starting detection.")

    def stop_detection(self):
        self.detection_started = False
        self.start_button.config(text="Start Detection", command=self.start_detection)
        print("Detection Stopped!")

    def update_frame(self):
        frame = self.picam2.capture_array()
        if self.dragging and self.temp_roi_x1 and self.temp_roi_y1 and self.temp_roi_x2 and self.temp_roi_y2:
            x1, y1 = max(0, self.temp_roi_x1), max(0, self.temp_roi_y1)
            x2, y2 = min(self.camera_width, self.temp_roi_x2), min(self.camera_height, self.temp_roi_y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
        elif self.roi_set and self.roi_x1 and self.roi_y1 and self.roi_x2 and self.roi_y2:
            x1, y1 = max(0, self.roi_x1), max(0, self.roi_y1)
            x2, y2 = min(self.camera_width, self.roi_x2), min(self.camera_height, self.roi_y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        elif not self.roi_set and self.roi_x1 and self.roi_y1 and self.roi_x2 and self.roi_y2:
            x1, y1 = max(0, self.roi_x1), max(0, self.roi_y1)
            x2, y2 = min(self.camera_width, self.roi_x2), min(self.camera_height, self.roi_y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        if self.detection_started:
            summary_value, found_summary = self.process_image(frame)
            if found_summary:
                print("'Summary' detected!")
            if summary_value is not None:
                print(f"Extracted Summary value: {summary_value}")

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        im = Image.fromarray(image)
        imgtk = ImageTk.PhotoImage(image=im)
        self.label.imgtk = imgtk
        self.label.configure(image=imgtk)
        self.label.after(20, self.update_frame)

    def close(self):
        self.picam2.stop()
        self.root.destroy()

if __name__ == "__main__":
    app = ImageRecognitionApp()
    app.root.mainloop()
