import cv2

def test_webcam(index):
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        print(f"Webcam opened successfully at index {index}")
        ret, frame = cap.read()
        if ret:
            print("Captured frame successfully")
            cv2.imshow("Test", frame)
            cv2.waitKey(1000)
        else:
            print("Failed to capture frame")
        cap.release()
    else:
        print(f"Failed to open webcam at index {index}")
    cv2.destroyAllWindows()

# Test indices from 0 to 20
for i in range(21):
    print(f"Testing index {i}")
    test_webcam(i)
