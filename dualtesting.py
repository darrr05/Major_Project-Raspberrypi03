import subprocess
import threading

def run_camera(camera_id):
    # Command to run libcamera-hello with a specific camera
    command = f"libcamera-hello -t 0 --camera {camera_id}"
    subprocess.run(command, shell=True)

def main():
    # Create threads for each camera to run in parallel
    camera1_thread = threading.Thread(target=run_camera, args=(0,))
    camera2_thread = threading.Thread(target=run_camera, args=(1,))
    
    # Start the threads
    camera1_thread.start()
    camera2_thread.start()

    # Wait for both threads to finish
    camera1_thread.join()
    camera2_thread.join()

if __name__ == "__main__":
    main()
