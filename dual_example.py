import subprocess
import time

def capture_camera(camera_index, output_file):
    print(f"Capturing from camera {camera_index} to {output_file}...")
    cmd = [
        "libcamera-still",
        f"--camera", str(camera_index),
        "-o", output_file,
        "-n",               # no preview window
        "--timeout", "1000" # wait 1 second to capture
    ]
    subprocess.run(cmd, check=True)

def main():
    try:
        capture_camera(0, "cam0.jpg")
        time.sleep(1)  # brief pause between captures
        capture_camera(1, "cam1.jpg")
        print("✅ Images captured as cam0.jpg and cam1.jpg.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to capture image: {e}")

if __name__ == "__main__":
    main()
