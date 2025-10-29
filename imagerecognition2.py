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
    def __init__(self, parent=None, picam2=None):
        self.parent = parent
        self.output_folder = "processed_images"
        os.makedirs(self.output_folder, exist_ok=True)
        self.reader = easyocr.Reader(['en'], gpu=False)
        self.camera_width = 750
        self.camera_height = 480
        self.picam2 = picam2 if picam2 else Picamera2()
        try:
            if not picam2:
                self.picam2.configure(self.picam2.create_video_configuration(main={"size": (self.camera_width, self.camera_height)}))
                self.picam2.set_controls({'AfMode': 2})
                self.picam2.set_controls({'HdrMode': libcamera.controls.HdrModeEnum.SingleExposure})
                self.picam2.start()
                time.sleep(2)
            else:
                # Ensure the passed camera is configured for autofocus
                self.picam2.configure(self.picam2.create_video_configuration(main={"size": (self.camera_width, self.camera_height)}))
                self.picam2.set_controls({'AfMode': 2})  # Ensure continuous autofocus
                if not self.picam2.started:  # Check if camera is not already started
                    self.picam2.start()
                    time.sleep(2)
        except Exception as e:
            print(f"Error initializing camera: {e}")
            tk.messagebox.showerror("Camera Error", f"Failed to initialize camera: {e}")
            self.close()
            return
        
        # Initialize ROI and other flags
        self.roi_x1, self.roi_y1, self.roi_x2, self.roi_y2 = None, None, None, None
        self.temp_roi_x1, self.temp_roi_y1, self.temp_roi_x2, self.temp_roi_y2 = None, None, None, None
        self.dragging = False
        self.roi_set = False
        self.detection_started = False
        self.setting_roi = False
        self.non_detection_start_time = None  # Track when non-detection starts
        self.latest_summary_value = None  # Store the latest detected summary value
        self.roi_padding = 20  # Initial padding value for ROI

        # Setup the Tkinter window
        self.root = tk.Toplevel(parent) if parent else tk.Tk()
        self.root.title("Camera Feed with OCR Detection")
        width, height = 800, 600  # Match Integration.py window size
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.resizable(False, False)
        self.root.configure(bg="black")  # Border color
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.overrideredirect(True)

        # Border frame
        border_frame = tk.Frame(self.root, bg="black")
        border_frame.pack(expand=True, fill="both", padx=4, pady=4)

        # Inner frame
        inner_frame = tk.Frame(border_frame, bg="white")  # Default background color
        inner_frame.pack(expand=True, fill="both")

        # Title
        title_label = tk.Label(inner_frame, text="Camera Feed", font=("Times New Roman", 20, "bold"),
                              bg="white", fg="black")
        title_label.pack(pady=(10, 5))

        # Separator
        separator = tk.Frame(inner_frame, height=2, bg="black")
        separator.pack(fill='x', padx=20, pady=(0, 10))

        # Frame for camera feed
        camera_frame = tk.Frame(inner_frame, bg="white")
        camera_frame.pack(pady=(0, 20))

        # Camera feed label
        self.label = Label(camera_frame, bg="white")
        self.label.pack()

        # Setup alert message label
        self.alert_label = Label(
            camera_frame,
            text="No 'Summary' with number detected. Please reposition the camera.",
            font=("Arial", 12),
            fg="red",
            bg="white",
            relief="solid",
            borderwidth=1
        )
        self.alert_label.place(x=10, y=10)  # Position at top-left corner
        self.alert_label.place_forget()  # Initially hide the alert

        # Setup bottom button frame
        self.button_frame = tk.Frame(inner_frame, bg="white")
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.set_roi_button = Button(self.button_frame, text="Set ROI", width=15, height=2, command=self.enable_set_roi)
        self.set_roi_button.pack(side=tk.LEFT, padx=5)
        self.delete_roi_button = Button(self.button_frame, text="Delete ROI", width=15, height=2, command=self.delete_roi, state=tk.DISABLED)
        self.delete_roi_button.pack(side=tk.LEFT, padx=5)
        self.start_button = Button(self.button_frame, text="Start Detection", width=15, height=2, command=self.start_detection)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.quit_button = Button(self.button_frame, text="Quit", width=15, height=2, command=self.close)
        self.quit_button.pack(side=tk.LEFT, padx=5)

        # Setup padding buttons on the screen preview
        self.increase_padding_button = Button(self.label, text="+", width=3, height=2, command=self.increase_padding, state=tk.DISABLED)
        self.increase_padding_button.place(x=0, y=230)  # Top-right corner
        self.decrease_padding_button = Button(self.label, text="-", width=3, height=2, command=self.decrease_padding, state=tk.DISABLED)
        self.decrease_padding_button.place(x=0, y=280)  # Below increase button

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

    def process_image_without_roi(self, image):
        found_summary = False
        summary_value = None
        final_text = ""
        summary_bbox = None

        print("ROI not set. Using OCR to detect 'Summary' and associated number...")
        results = self.reader.readtext(image)

        for bbox, text, prob in results:
            final_text += text + " "
            if "summary" in text.lower():
                found_summary = True
                summary_bbox = bbox
                print(f"Detected 'Summary' with confidence: {prob}")

        # Look for a number in the context of "Summary:"
        summary_match = re.search(r'(?:Summary.*?\s*(\d+)|(\d+)\s*.*?Summary)', final_text, re.IGNORECASE)
        if summary_match:
            summary_value = int(summary_match.group(1) or summary_match.group(2))
            self.latest_summary_value = summary_value  # Store the latest detected value
            print(f"Detected 'Summary:' with value: {summary_value}")
            
        print(f"found_summary: {found_summary}, summary_value: {summary_value}, summary_bbox: {summary_bbox}")

        # If "Summary" and number are found, update ROI
        if found_summary and summary_value is not None and summary_bbox:
            min_x = int(summary_bbox[0][0])
            min_y = int(summary_bbox[0][1])
            max_x = int(summary_bbox[2][0])
            max_y = int(summary_bbox[2][1])
            
            # Add padding to widen the bounding box
            min_x = max(0, min_x - self.roi_padding)  # Ensure it doesn't go out of bounds
            min_y = max(0, min_y - self.roi_padding)
            max_x = min(self.camera_width, max_x + self.roi_padding)
            max_y = min(self.camera_height, max_y + self.roi_padding)

            # Update the ROI values globally
            self.roi_x1, self.roi_y1, self.roi_x2, self.roi_y2 = min_x, min_y, max_x, max_y
            if self.roi_x1 and self.roi_y1 and self.roi_x2 and self.roi_y2:
                self.delete_roi_button.config(state=tk.NORMAL)
            else:
                self.delete_roi_button.config(state=tk.DISABLED)
            self.roi_set = True  # Set the flag to true after detecting the ROI
            self.setting_roi = False
            print(f"Drawing ROI around 'Summary: {summary_value}' at ({self.roi_x1}, {self.roi_y1}), ({self.roi_x2}, {self.roi_y2}) with padding {self.roi_padding}")

            # Return the updated result
            return summary_value, found_summary

        # If no summary is detected, return the flags and None for ROI coordinates
        return summary_value, found_summary

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
                self.latest_summary_value = summary_value  # Store the latest detected value
            
            # If the word "summary" is detected, disable autofocus
            if found_summary:
                self.picam2.set_controls({'AfMode': 0})  # Disable autofocus

            return summary_value, found_summary
        return None, False

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
            self.start_button.config(state=tk.DISABLED)
            self.set_roi_button.config(text="Confirm ROI", command=self.confirm_set_roi)
            print("Set ROI mode enabled. Draw your ROI now.")

    def confirm_set_roi(self):
        if self.setting_roi and self.temp_roi_x1 and self.temp_roi_y1 and self.temp_roi_x2 and self.temp_roi_y2:
            self.roi_x1, self.roi_y1, self.roi_x2, self.roi_y2 = self.temp_roi_x1, self.temp_roi_y1, self.temp_roi_x2, self.temp_roi_y2
            self.roi_set = True
            self.setting_roi = False
            self.set_roi_button.config(text="Set ROI", command=self.enable_set_roi)
            self.delete_roi_button.config(state=tk.NORMAL)
            self.start_button.config(state=tk.NORMAL)
            print(f"ROI set to ({self.roi_x1}, {self.roi_y1}), ({self.roi_x2}, {self.roi_y2})")

    def delete_roi(self):
        if self.roi_set:
            self.roi_x1, self.roi_y1, self.roi_x2, self.roi_y2 = None, None, None, None
            self.roi_set = False
            self.delete_roi_button.config(state=tk.DISABLED)
            print("ROI deleted.")

    def increase_padding(self):
        self.roi_padding += 5  # Increase padding by 5 pixels
        print(f"ROI padding increased to {self.roi_padding} pixels")
        # Update existing ROI if set
        if self.roi_set and self.roi_x1 is not None and self.roi_y1 is not None and self.roi_x2 is not None and self.roi_y2 is not None:
            min_x = max(0, self.roi_x1 - 5)
            min_y = max(0, self.roi_y1 - 5)
            max_x = min(self.camera_width, self.roi_x2 + 5)
            max_y = min(self.camera_height, self.roi_y2 + 5)
            self.roi_x1, self.roi_y1, self.roi_x2, self.roi_y2 = min_x, min_y, max_x, max_y
            print(f"Updated ROI to ({self.roi_x1}, {self.roi_y1}), ({self.roi_x2}, {self.roi_y2})")

    def decrease_padding(self):
        self.roi_padding = max(0, self.roi_padding - 5)  # Decrease padding by 5 pixels, minimum 0
        print(f"ROI padding decreased to {self.roi_padding} pixels")
        # Update existing ROI if set
        if self.roi_set and self.roi_x1 is not None and self.roi_y1 is not None and self.roi_x2 is not None and self.roi_y2 is not None:
            min_x = min(self.camera_width, self.roi_x1 + 5)
            min_y = min(self.camera_height, self.roi_y1 + 5)
            max_x = max(0, self.roi_x2 - 5)
            max_y = max(0, self.roi_y2 - 5)
            # Ensure ROI remains valid
            if min_x < max_x and min_y < max_y:
                self.roi_x1, self.roi_y1, self.roi_x2, self.roi_y2 = min_x, min_y, max_x, max_y
                print(f"Updated ROI to ({self.roi_x1}, {self.roi_y1}), ({self.roi_x2}, {self.roi_y2})")
            else:
                print("Cannot decrease padding further; ROI would become invalid.")

    def start_detection(self):
        # Start detection even if the ROI is not set
        self.detection_started = True
        self.non_detection_start_time = None  # Reset timer
        self.start_button.config(text="Stop Detection", command=self.stop_detection)
        self.increase_padding_button.config(state=tk.NORMAL)
        self.decrease_padding_button.config(state=tk.NORMAL)
        print("Detection Started!")

    def stop_detection(self):
        self.detection_started = False
        self.non_detection_start_time = None  # Reset timer
        self.start_button.config(text="Start Detection", command=self.start_detection)
        self.increase_padding_button.config(state=tk.DISABLED)
        self.decrease_padding_button.config(state=tk.DISABLED)
        print("Detection Stopped!")

    def update_frame(self):
        frame = self.picam2.capture_array()

        # Draw temporary ROI (during dragging)
        if self.dragging and self.temp_roi_x1 and self.temp_roi_y1 and self.temp_roi_x2 and self.temp_roi_y2:
            x1, y1 = max(0, self.temp_roi_x1), max(0, self.temp_roi_y1)
            x2, y2 = min(self.camera_width, self.temp_roi_x2), min(self.camera_height, self.temp_roi_y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)  # Yellow for temp ROI

        # Draw permanent ROI (either drawn by user or detected automatically)
        elif self.roi_set and self.roi_x1 is not None and self.roi_y1 is not None and self.roi_x2 is not None and self.roi_y2 is not None:
            x1, y1 = max(0, self.roi_x1), max(0, self.roi_y1)
            x2, y2 = min(self.camera_width, self.roi_x2), min(self.camera_height, self.roi_y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Green for final ROI

        # If detection is started, process the frame for OCR
        if self.detection_started:
            if self.roi_x1 is None or self.roi_y1 is None or self.roi_x2 is None or self.roi_y2 is None:
                # If no ROI set, process the full image
                summary_value, found_summary = self.process_image_without_roi(frame)
            else:
                # If ROI is set, process only within the ROI
                summary_value, found_summary = self.process_image(frame)

            if found_summary:
                print("'Summary' detected!")
            if summary_value is not None:
                print(f"Extracted Summary value: {summary_value}")

            # Handle alert and non-detection timing
            if not found_summary or summary_value is None:
                self.alert_label.place(x=10, y=10)  # Show alert
                if self.non_detection_start_time is None:
                    self.non_detection_start_time = time.time()  # Start timer
                elif time.time() - self.non_detection_start_time >= 2:  # Check if 2 seconds have passed
                    if self.latest_summary_value is not None:
                        print(f"Latest detected Summary value: {self.latest_summary_value}")
                    else:
                        print("No Summary value has been detected yet.")
                    # Reset ROI and related states
                    self.roi_x1, self.roi_y1, self.roi_x2, self.roi_y2 = None, None, None, None
                    self.roi_set = False
                    self.delete_roi_button.config(state=tk.DISABLED)
                    self.latest_summary_value = None  # Clear last value
                    self.non_detection_start_time = None  # Reset timer to allow new detection cycle
            else:
                self.alert_label.place_forget()  # Hide alert
                self.non_detection_start_time = None  # Reset timer

        # Convert frame to RGB for displaying in Tkinter
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        im = Image.fromarray(image)
        imgtk = ImageTk.PhotoImage(image=im)
        self.label.imgtk = imgtk
        self.label.configure(image=imgtk)
        self.label.after(40, self.update_frame)  # Update the frame every 30ms

    def close(self):
        self.root.withdraw()

if __name__ == "__main__":
    app = ImageRecognitionApp()
    app.root.mainloop()