import multiprocessing
import subprocess

def run_camera_1():
    subprocess.run(["python3", "camera1.py"])

def run_camera_2():
    subprocess.run(["python3", "camera2.py"])

if __name__ == "__main__":
    # Create two separate processes for each Python file
    process1 = multiprocessing.Process(target=run_camera_1)
    process2 = multiprocessing.Process(target=run_camera_2)

    # Start both processes
    process1.start()
    process2.start()

    # Wait for both processes to finish
    process1.join()
    process2.join()
