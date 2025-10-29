#!/bin/bash

# Ensure the output folder exists
mkdir -p /home/pi/Pictures

echo "📸 Camera ready!"
echo "Press ENTER to take a picture."
echo "Press CTRL+C to quit."

# Start libcamera-still in keypress mode
libcamera-still \
  --preview 0,0,640,480 \
  -t 0 \
  --keypress \
  --output '/home/pi/hailo-rpi5-examples/Number_Images/image_%04d.jpg'
