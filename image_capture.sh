#!/bin/bash
echo "Starting preview. Press [ENTER] to take a picture. Type 'q' to quit."

libcamera-still -t 0 --preview &  # Start preview indefinitely in the background
preview_pid=$!

count=1
while true; do
    read -p "Press [ENTER] to capture or 'q' to quit: " input
    if [ "$input" = "q" ]; then
        kill $preview_pid
        break
    fi
    libcamera-still -t 1 -n -o image_$count.jpg
    echo "Saved image_$count.jpg"
    ((count++))
done
