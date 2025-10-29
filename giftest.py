import tkinter as tk
from PIL import Image, ImageSequence
from io import BytesIO
import threading

root = tk.Tk()
root.title("GIF Animation Test")
root.geometry("800x550")
root.config(background='#108cff')

gif_path = "/home/pi/hailo-rpi5-examples/images/CameraBlocked.gif"
target_width, target_height = 450, 500

frame_skip = 20  # Keep every 5th frame, starting from frame 0

gif_label = tk.Label(root, bg="#108cff")
gif_label.place(x=155, y=20, width=target_width, height=target_height)

frames = []
show_animation = None
count = 0

def display_animation():
    global show_animation, count
    if not gif_label.winfo_exists() or not frames:
        return
    try:
        gif_label.configure(image=frames[count])
        gif_label.image = frames[count]
        count = (count + 1) % len(frames)
        show_animation = root.after(50, display_animation)
    except Exception as e:
        print(f"animation error: {e}")
        gif_label.configure(text="Animation error", fg="red")

def load_frames(img, new_size):
    global frames
    try:
        for i, frame in enumerate(ImageSequence.Iterator(img)):
            if i % frame_skip != 0:
                continue  # Skip frames based on frame_skip

            frame = frame.convert("RGB").resize(new_size, Image.Resampling.LANCZOS)
            with BytesIO() as buffer:
                frame.save(buffer, format="GIF")
                buffer.seek(0)
                photo_frame = tk.PhotoImage(data=buffer.read())
                frames.append(photo_frame)

                if len(frames) == 1:
                    # Show first frame immediately
                    gif_label.configure(image=photo_frame)
                    gif_label.image = photo_frame
                    print("Displayed first frame")

        print(f"Total frames loaded after skipping: {len(frames)}")
        if len(frames) > 1:
            display_animation()
    except Exception as e:
        print(f"Error while loading frames: {e}")
        gif_label.configure(text="Failed to load animation", fg="red")

try:
    img = Image.open(gif_path)
    print(f"Loaded {gif_path}: format={img.format}, frames={getattr(img, 'n_frames', '?')}, size={img.size}")

    aspect_ratio = min(target_width / img.width, target_height / img.height)
    new_size = (int(img.width * aspect_ratio), int(img.height * aspect_ratio))
    print(f"Resizing frames to: {new_size}")

    threading.Thread(target=lambda: load_frames(img, new_size), daemon=True).start()

except Exception as e:
    print(f"Error loading GIF: {e}")
    gif_label.configure(text="Failed to load GIF", fg="red", bg="#108cff")

root.mainloop()
