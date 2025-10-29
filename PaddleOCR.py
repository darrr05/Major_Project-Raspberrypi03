import cv2
from paddleocr import PaddleOCR
from picamera2 import Picamera2
import numpy as np
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize PaddleOCR
try:
    ocr = PaddleOCR(use_textline_orientation=True, lang='en')
    logging.info("PaddleOCR initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize PaddleOCR: {e}")
    exit(1)

# Initialize Pi Camera
picam2 = Picamera2()
try:
    picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"}))  # Explicit RGB format
    picam2.start()
    time.sleep(2)  # Allow camera to warm up
    logging.info("Camera initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize camera: {e}")
    exit(1)

try:
    # Capture image
    logging.info("Capturing image...")
    image = picam2.capture_array()
    logging.info(f"Image captured, shape: {image.shape}, dtype: {image.dtype}")

    # Convert image to BGR
    logging.info("Converting image to BGR...")
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    logging.info(f"Image converted, shape: {image.shape}, dtype: {image.dtype}")

    # Save raw image for debugging
    cv2.imwrite("raw_image.jpg", image)
    logging.info("Raw image saved as 'raw_image.jpg'")

    # Perform OCR
    logging.info("Performing OCR...")
    result = ocr.predict(image)
    logging.info("OCR completed")

    # Extract and print detected numbers
    detected_numbers = []
    for line in result[0]:  # result[0] contains detection results
        text = line[1][0]  # Extracted text
        confidence = line[1][1]  # Confidence score
        if any(char.isdigit() for char in text):
            detected_numbers.append((text, confidence))
    
    # Print results
    if detected_numbers:
        logging.info("Detected numbers:")
        for text, conf in detected_numbers:
            logging.info(f"Text: {text}, Confidence: {conf:.2f}")
    else:
        logging.info("No numbers detected.")
    
    # Save processed image
    cv2.imwrite("processed_image.jpg", image)
    logging.info("Processed image saved as 'processed_image.jpg'")

except Exception as e:
    logging.error(f"Error during processing: {e}")
finally:
    # Clean up
    picam2.stop()
    logging.info("Camera stopped.")