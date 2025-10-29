#!/bin/bash

# Output folder for video recordings
mkdir -p /home/pi/Videos

echo "?? Camera ready!"
echo "Press ENTER to start/stop recording."
echo "Press CTRL+C to quit."

# Video file counter
counter=1
recording=0
pid=""

while true; do
    read -rsn1 input
    if [[ "$input" == "" ]]; then
        if [[ $recording -eq 0 ]]; then
            echo "??  Recording started..."
            libcamera-vid \
              --preview 0,0,640,480 \
              -t 0 \
              -o "/home/pi/hailo-rpi5-examples/Number_Videos/video_${counter}.h264" &
            pid=$!
            recording=1
        else
            echo "??  Stopping recording..."
            kill $pid
            wait $pid 2>/dev/null
            recording=0
            ((counter++))
        fi
    fi
done
