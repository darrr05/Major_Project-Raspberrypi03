import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
from picamera2 import Picamera2
import os
import itertools
import datetime
import random
import subprocess
import mariadb
import cv2
import easyocr
import numpy as np
import threading
import time
from queue import Queue
from collections import deque, Counter
from tkinter import ttk

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "Anti_Theftdb"
}

reader = easyocr.Reader(['en'])

# Adjustable parameters
USE_FIXED_ROI = False  # Set to True if your camera always sees the same screen region
PADDING_X = 50
PADDING_Y = 40
ROI_Y1, ROI_Y2 = 100, 200  # Only used if USE_FIXED_ROI = True
ROI_X1, ROI_X2 = 300, 500
DEBOUNCE_COUNT = 4  # Number of consistent detections before confirming

# Store recent results for debouncing
recent_detections = deque(maxlen=DEBOUNCE_COUNT)

HARDCODED_PASSWORD = "admin123"

# Language dictionary
translations = {
    "en": {
        "settings": "Settings",
        "volume": "Speaker Volume:",
        "theme": "Display Theme:",
        "light_mode": "Light Mode",
        "dark_mode": "Dark Mode",
        "save": "Save",
        "cancel": "Cancel",
        "dome_camera": "Dome Camera Count",
        "ribbon_camera": "Ribbon Camera Count",
        "barcode_detected": "âœ… Barcode Detected",
        "barcode_blocked": "âœ– Barcode Blocked",
        "multiple_barcodes": "âœ– Multiple Barcodes Detected",
        "camera_blocked": "âœ– Camera Blocked",
        "language": "Language:",
        "english": "English",
        "chinese": "ä¸­æ–‡",
        "about_system": "â„¹ï¸ About the System",
        "staff_in_charge": "âš’ï¸ Staff in Charge",
        "live_camera_feed": "[â—‰Â°] Live Camera Feed",
        "activity_log": "âœï¸ Activity Log",
        "start": "Start",
        "submit": "Submit",
        "login": "Login",
        "username": "Username:",
        "pass": "Password:",
        "incorrect": "Incorrect password. Try again.",
        "shutdown": "âš ï¸ Shutdown Access",
        "passreq": "Password Required",
        "confirm": "Confirm Shutdown",
        "AYS": "Are you sure you want to shutdown the system?",
        "logout": "â˜¯ï¸Ž Logout",
        "staff_info": "Staff Information",
        "ok": "OK",
        "time": "Time",
        "description": "Description",
        "image": "Image",
        "exit": "Exit",
    },
    "zh": {
        "settings": "è®¾ç½®",
        "volume": "æ‰¬å£°å™¨éŸ³é‡ï¼š",
        "theme": "æ˜¾ç¤ºä¸»é¢˜ï¼š",
        "light_mode": "æµ…è‰²æ¨¡å¼",
        "dark_mode": "æ·±è‰²æ¨¡å¼",
        "save": "ä¿å­˜",
        "cancel": "å–æ¶ˆ",
        "dome_camera": "çƒå½¢æ‘„åƒå¤´è®¡æ•°",
        "ribbon_camera": "æ¡ç æ‘„åƒå¤´è®¡æ•°",
        "barcode_detected": "âœ… æ£€æµ‹åˆ°æ¡ç ",
        "barcode_blocked": "âœ– æ¡ç è¢«é®æŒ¡",
        "multiple_barcodes": "âœ– æ£€æµ‹åˆ°å¤šä¸ªæ¡ç ",
        "camera_blocked": "âœ– æ‘„åƒå¤´è¢«é®æŒ¡",
        "language": "è¯­è¨€ï¼š",
        "english": "English",
        "chinese": "ä¸­æ–‡",
        "about_system": "â„¹ï¸ å…³äºŽç³»ç»Ÿ",
        "staff_in_charge": "âš’ï¸ è´Ÿè´£äºº",
        "live_camera_feed": "[â—‰Â°] å®žæ—¶æ‘„åƒå¤´ç”»é¢",
        "activity_log": "âœï¸ æ´»åŠ¨è®°å½•",
        "start": "å¼€å§‹",
        "submit": "æäº¤",
        "login": "ç™»å½•",
        "username": "ç”¨æˆ·å:",
        "pass": "å¯†ç :",
        "incorrect": "å¯†ç ä¸æ­£ç¡®ã€‚è¯·é‡è¯•.",
        "shutdown": "âš ï¸ å…³æœºè®¿é—®",
        "passreq": "éœ€è¦å¯†ç ",
        "confirm": "ç¡®è®¤å…³æœº",
        "AYS": "æ‚¨ç¡®å®šè¦å…³é—­ç³»ç»Ÿå—?",
        "logout": "â˜¯ï¸Ž é€€å‡ºç™»å½•",
        "staff_info": "è´Ÿè´£äººä¿¡æ¯",
        "ok": "å¥½",
        "time": "æ—¶é—´",
        "description": "æè¿°",
        "image": "å›¾ç‰‡",
        "exit": "é€€å‡º",
    }
}

class GradientFrame(tk.Canvas):
    def __init__(self, parent, color1, color2, **kwargs):
        super().__init__(parent, **kwargs)
        self.color1 = color1
        self.color2 = color2
        self.bind("<Configure>", self._draw_gradient)

    def _draw_gradient(self, event=None):
        self.delete("gradient")
        width = self.winfo_width()
        height = self.winfo_height()
        limit = height
        (r1, g1, b1) = self.winfo_rgb(self.color1)
        (r2, g2, b2) = self.winfo_rgb(self.color2)
        r_ratio = float(r2 - r1) / limit
        g_ratio = float(g2 - g1) / limit
        b_ratio = float(b2 - b1) / limit
        for i in range(limit):
            nr = int(r1 + (r_ratio * i))
            ng = int(g1 + (g_ratio * i))
            nb = int(b1 + (b_ratio * i))
            color = f"#{nr//256:02x}{ng//256:02x}{nb//256:02x}"
            self.create_line(0, i, width, i, tags=("gradient",), fill=color)
        self.lower("gradient")

class LoginDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text=self.tr("username"), font=("Times New Roman", 12)).grid(row=0, column=0, sticky="e", padx=5, pady=5)
        tk.Label(master, text=self.tr("pass"), font=("Times New Roman", 12)).grid(row=1, column=0, sticky="e", padx=5, pady=5)

        self.username_entry = tk.Entry(master, font=("Times New Roman", 12))
        self.password_entry = tk.Entry(master, show="*", font=("Times New Roman", 12))

        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)

        return self.username_entry

    def apply(self):
        self.result = (self.username_entry.get(), self.password_entry.get())

class SupermarketApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.language = "en"
        self.title("Supermarket Giant System")
        self.attributes('-fullscreen', True)
        self.current_user = None

        self.volume_level = 50  # default volume level 0-100
        self.theme = "light"    # default theme
        self.set_theme_colors() # set initial colors based on theme

        # Initialize ROI coordinates
        self.roi_x1 = ROI_X1
        self.roi_y1 = ROI_Y1
        self.roi_x2 = ROI_X2
        self.roi_y2 = ROI_Y2

        self.gradient_bg = GradientFrame(self, "#007c30", "#a4d4ae")
        self.gradient_bg.pack(fill="both", expand=True)

        self.border_frame = tk.Frame(self.gradient_bg, bg="white", bd=4, relief="groove")
        self.border_frame.place(relx=0.5, rely=0.01, anchor="n", width=1500, height=940)

        self.create_widgets()
        self.bind("<Escape>", lambda e: self.destroy())
        self.picam2 = None
        self.running = False
        self.detection_thread = None
        self.detected_number = "0"
        self.recent_detections = deque(maxlen=DEBOUNCE_COUNT)
        self.reader = easyocr.Reader(['en'], gpu=False)
        self.start_detection()
        self.ocr_queue = Queue()
        self.ocr_thread = threading.Thread(target=self.ocr_loop, daemon=True)
        self.ocr_thread.start()

    def tr(self, key):
        return translations[self.language].get(key, key)

    def set_theme_colors(self):
        if self.theme == "light":
            self.bg_gradient_start = "#007c30"
            self.bg_gradient_end = "#a4d4ae"
            self.bg_color = "white"
            self.fg_color = "#007c30"
            self.btn_bg = "#e8f5e9"
            self.btn_active_bg = "#c8e6c9"
            self.text_fg = "#333333"
            self.top_bar_bg = "white"
            self.grid_frame_bg = "white"
        else:  # dark
            self.bg_gradient_start = "#004d1a"
            self.bg_gradient_end = "#2a6a3f"
            self.bg_color = "#222222"
            self.fg_color = "#a4d4ae"
            self.btn_bg = "#335533"
            self.btn_active_bg = "#4d774d"
            self.text_fg = "#dddddd"
            self.top_bar_bg = "#333333"
            self.grid_frame_bg = "#222222"

    def apply_theme(self):
        # Update gradient background colors
        self.gradient_bg.color1 = self.bg_gradient_start
        self.gradient_bg.color2 = self.bg_gradient_end
        self.gradient_bg._draw_gradient()

        # Update border frame bg
        self.border_frame.config(bg=self.bg_color)

        self.grid_frame.config(bg=self.grid_frame_bg)
        for widget in self.grid_frame.winfo_children():
            if isinstance(widget, tk.Label):
                widget.config(bg=self.grid_frame_bg, fg=self.text_fg)
            elif isinstance(widget, tk.Button):
                widget.config(bg=self.btn_bg, fg=self.fg_color,
                              activebackground=self.btn_active_bg)
        # Update top bar colors
        self.top_bar.config(bg=self.top_bar_bg)
        for widget in self.top_bar.winfo_children():
            if isinstance(widget, tk.Button):
                if widget == self.shutdown_btn:
                    widget.config(
                        bg=self.top_bar_bg,
                        fg=self.fg_color if self.theme == "dark" else "black",
                        activebackground="#444444" if self.theme == "dark" else "#f0f0f0"
                    )
                elif widget == self.settings_btn:
                    widget.config(
                        bg=self.top_bar_bg,
                        fg=self.fg_color if self.theme == "dark" else "black",
                        activebackground="#335533" if self.theme == "dark" else "#d6f5d6"
                    )
                elif widget == self.logout_btn:
                    widget.config(bg=self.top_bar_bg, fg="red", activebackground="#fddede")
                else:
                    widget.config(bg=self.top_bar_bg, fg=self.fg_color,
                                  activebackground="#d6f5d6" if self.theme == "light" else "#335533")

        # Update center frame and child widgets
        for child in self.border_frame.winfo_children():
            if isinstance(child, tk.Frame) and child != self.top_bar:
                child.config(bg=self.bg_color)
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Label):
                        subchild.config(bg=self.bg_color, fg=self.text_fg)
                    elif isinstance(subchild, tk.Button):
                        subchild.config(bg=self.btn_bg, fg=self.fg_color,
                                        activebackground=self.btn_active_bg)
                    elif isinstance(subchild, tk.Frame):
                        for nested in subchild.winfo_children():
                            if isinstance(nested, tk.Label):
                                nested.config(bg=self.bg_color, fg=self.text_fg)
                            elif isinstance(nested, tk.Button):
                                nested.config(bg=self.btn_bg, fg=self.fg_color,
                                              activebackground=self.btn_active_bg)

        # Update status bar label
        self.status_label.config(bg=self.bg_color, fg=self.fg_color)

    def create_widgets(self):
        self.top_bar = tk.Frame(self.border_frame, bg="white")
        self.top_bar.pack(side=tk.TOP, fill=tk.X, pady=10)

        self.settings_btn = tk.Button(self.top_bar, text="âš™", font=("Times New Roman", 20), command=self.open_settings,
                                      bg="white", bd=0, activebackground="lightgray")
        self.settings_btn.pack(side=tk.LEFT, padx=20)

        shutdown_path = os.path.expanduser("~/Downloads/pb.png")

        # Create shutdown button
        self.shutdown_btn = tk.Button(self.top_bar, font=("Times New Roman", 20),
                                      command=self.prompt_shutdown_password, fg="black", bg="white", bd=0,
                                      activebackground="lightgray")

        # Check if image exists and set image or fallback text
        if os.path.exists(shutdown_path):
            shutdown_img = Image.open(shutdown_path)
            shutdown_img = shutdown_img.resize((20, 25))
            shutdown_img_tk = ImageTk.PhotoImage(shutdown_img)
            self.shutdown_btn.config(image=shutdown_img_tk)
            self.shutdown_btn.image = shutdown_img_tk
        else:
            self.shutdown_btn.config(text="Shutdown", fg="red")

        self.shutdown_btn.pack(side=tk.RIGHT, padx=(10, 20))

        self.logout_btn = tk.Button(self.top_bar, text=self.tr("logout"), font=("Times New Roman", 20),
                                   command=self.logout, fg="red", bg="white", bd=0, activebackground="lightgray")
        self.logout_btn.pack_forget()

        center_frame = tk.Frame(self.border_frame, bg="white")
        center_frame.pack(fill=tk.BOTH, expand=True, pady=20)

        logo_path = os.path.expanduser("~/Downloads/Giant Logo.png")
        logo_label = tk.Label(center_frame, bg="white")
        if os.path.exists(logo_path):
            logo_img = Image.open(logo_path)
            logo_img.thumbnail((300, 300))
            self.logo = ImageTk.PhotoImage(logo_img)
            logo_label.config(image=self.logo)
        else:
            logo_label.config(text="ðŸ›’ Giant Supermarket", font=("Times New Roman", 24, "bold"), fg="#007c30")
        logo_label.pack(pady=10)

        self.grid_frame = tk.Frame(center_frame, bg="white")
        self.grid_frame.pack(pady=(60, 0))

        btn_font = ("Times New Roman", 16, "bold")
        btn_style = {"width": 22, "height": 3, "font": btn_font, "bg": "#e8f5e9",
                     "activebackground": "#c8e6c9", "bd": 2, "relief": "ridge"}

        self.about_btn = tk.Button(self.grid_frame, text=self.tr("about_system"), command=self.about_system, **btn_style)
        self.about_btn.grid(row=0, column=0, padx=20, pady=20)

        self.staff_btn = tk.Button(self.grid_frame, text=self.tr("staff_in_charge"), command=self.staff_info, **btn_style)
        self.staff_btn.grid(row=0, column=1, padx=30, pady=20)

        self.live_btn = tk.Button(self.grid_frame, text=self.tr("live_camera_feed"), command=self.live_camera, **btn_style)
        self.live_btn.grid(row=1, column=0, padx=30, pady=20)

        self.activity_btn = tk.Button(self.grid_frame, text=self.tr("activity_log"), command=self.activity_log, **btn_style)
        self.activity_btn.grid(row=1, column=1, padx=30, pady=20)

        self.start_btn = tk.Button(self.grid_frame, text=self.tr("start"), command=self.start,
                                   width=14, height=2, font=("Times New Roman", 12, "bold"),
                                   bg="#e8f5e9", activebackground="#c8e6c9", bd=2, relief="ridge")
        self.start_btn.grid(row=2, column=0, columnspan=2, pady=20)

        self.simulate_log_btn = tk.Button(
            self.grid_frame,
            text="Simulate Log",
            command=self.simulate_activity_log,
            width=14, height=2,
            font=("Times New Roman", 12, "bold"),
            bg="#e8f5e9", activebackground="#c8e6c9", bd=2, relief="ridge"
        )
        self.simulate_log_btn.grid(row=2, column=1, pady=20)

        self.create_tip_box(center_frame)

        self.status_label = tk.Label(self.border_frame, text="", bg="white", fg="#007c30",
                                     font=("Times New Roman", 12, "italic"))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        self.update_status_bar()

    def update_translations(self):
        self.about_btn.config(text=self.tr("about_system"))
        self.staff_btn.config(text=self.tr("staff_in_charge"))
        self.live_btn.config(text=self.tr("live_camera_feed"))
        self.activity_btn.config(text=self.tr("activity_log"))
        self.start_btn.config(text=self.tr("start"))
        self.logout_btn.config(text=f"{self.tr('logout')}" if self.tr("logout") else "â» Logout")
        self.update_status_bar()

    def simulate_activity_log(self):
        try:
            conn = mariadb.connect(**DB_CONFIG)
            cursor = conn.cursor()
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            description = "Simulated Theft Attempt Detected"
            image_path = ""  # Optional: Add actual image path if needed
            cursor.execute(
                "INSERT INTO activity_log (timestamp, description, image_path) VALUES (%s, %s, %s)",
                (timestamp, description, image_path)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Simulated Log", "A simulated activity log has been inserted.")
        except mariadb.Error as err:
            messagebox.showerror("Database Error", f"Failed to insert simulated log: {err}")

    def prompt_shutdown_password(self):
        def check_password():
            if password_entry.get() == HARDCODED_PASSWORD:
                prompt_win.destroy()
                self.shutdown()
            else:
                error_label.config(text=self.tr("incorrect"))
                password_entry.delete(0, tk.END)

        border_color = "white" if self.theme == "dark" else "black"
        prompt_win = tk.Toplevel(self)
        prompt_win.grab_set()
        prompt_win.resizable(False, False)
        prompt_win.overrideredirect(True)
        prompt_win.configure(bg=border_color)

        width, height = 420, 220
        x = (prompt_win.winfo_screenwidth() // 2) - (width // 2)
        y = (prompt_win.winfo_screenheight() // 2) - (height // 2)
        prompt_win.geometry(f"{width}x{height}+{x}+{y}")

        border_frame = tk.Frame(prompt_win, bg=border_color)
        border_frame.pack(expand=True, fill="both", padx=4, pady=4)

        inner_frame = tk.Frame(border_frame, bg=self.bg_color)
        inner_frame.pack(expand=True, fill="both")

        title = tk.Label(inner_frame, text=self.tr("shutdown"), font=("Times New Roman", 16, "bold"),
                         bg=self.bg_color, fg=self.fg_color)
        title.pack(pady=(20, 10))

        separator = tk.Frame(inner_frame, height=2, bg=self.fg_color, bd=0, relief='flat')
        separator.pack(fill='x', padx=20, pady=(0, 10))

        password_entry = tk.Entry(inner_frame, show="*", font=("Times New Roman", 14),
                                  bg="white" if self.theme == "light" else "#333333",
                                  fg="black" if self.theme == "light" else "#dddddd",
                                  insertbackground=self.text_fg,
                                  relief="solid", bd=1, width=25)
        password_entry.pack(pady=10)
        password_entry.focus()

        error_label = tk.Label(inner_frame, text="", font=("Times New Roman", 12),
                               fg="red", bg=self.bg_color)
        error_label.pack()

        buttons_frame = tk.Frame(inner_frame, bg=self.bg_color)
        buttons_frame.pack(pady=10)

        submit_btn = tk.Button(buttons_frame, text=self.tr("submit"), font=("Times New Roman", 12, "bold"),
                               bg=self.btn_bg, fg=self.fg_color,
                               activebackground=self.btn_active_bg,
                               relief="raised", bd=2, command=check_password)
        submit_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = tk.Button(buttons_frame, text=self.tr("cancel"), font=("Times New Roman", 12, "bold"),
                               bg=self.btn_bg, fg=self.fg_color,
                               activebackground=self.btn_active_bg,
                               relief="raised", bd=2, command=prompt_win.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=10)

        prompt_win.bind("<Return>", lambda event: check_password())

    def open_settings(self):
        border_color = "white" if self.theme == "dark" else "black"
        settings_win = tk.Toplevel(self)
        settings_win.title("Settings")
        settings_win.geometry("500x500")
        self.center_window(settings_win, 500, 500)
        settings_win.grab_set()
        settings_win.overrideredirect(True)
        settings_win.configure(bg=border_color)

        border_frame = tk.Frame(settings_win, bg=border_color)
        border_frame.pack(expand=True, fill="both")

        inner_frame = tk.Frame(border_frame, bg=self.bg_color)
        inner_frame.pack(expand=True, fill="both", padx=4, pady=4)

        title = tk.Label(inner_frame, text=self.tr("settings"), font=("Times New Roman", 20, "bold"),
                         bg=self.bg_color, fg=self.fg_color)
        title.pack(pady=(20, 10))

        separator = tk.Frame(inner_frame, height=2, bg=self.fg_color, bd=0, relief='flat')
        separator.pack(fill='x', padx=20, pady=(0, 10))

        tk.Label(inner_frame, text=self.tr("volume"), font=("Times New Roman", 14),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(20, 10))

        volume_scale = tk.Scale(inner_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                length=280, font=("Times New Roman", 12),
                                bg=self.bg_color, fg=self.fg_color,
                                highlightthickness=0, troughcolor=self.btn_bg,
                                activebackground=self.btn_active_bg)
        volume_scale.set(self.volume_level)
        volume_scale.pack()

        tk.Label(inner_frame, text=self.tr("theme"), font=("Times New Roman", 14),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(30, 10))

        theme_var = tk.StringVar(value=self.theme)

        radio_frame = tk.Frame(inner_frame, bg=self.bg_color)
        radio_frame.pack()

        light_rb = tk.Radiobutton(radio_frame, text=self.tr("light_mode"), variable=theme_var, value="light",
                                  font=("Times New Roman", 12), bg=self.bg_color, fg=self.fg_color,
                                  selectcolor=self.btn_bg, activebackground=self.bg_color)
        dark_rb = tk.Radiobutton(radio_frame, text=self.tr("dark_mode"), variable=theme_var, value="dark",
                                 font=("Times New Roman", 12), bg=self.bg_color, fg=self.fg_color,
                                 selectcolor=self.btn_bg, activebackground=self.bg_color)
        light_rb.pack(anchor="w", padx=60, pady=2)
        dark_rb.pack(anchor="w", padx=60, pady=2)

        tk.Label(inner_frame, text=self.tr("language"), font=("Times New Roman", 14),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(30, 10))

        language_var = tk.StringVar(value=self.language)

        lang_frame = tk.Frame(inner_frame, bg=self.bg_color)
        lang_frame.pack()

        tk.Radiobutton(lang_frame, text=self.tr("english"), variable=language_var, value="en",
                       font=("Times New Roman", 12), bg=self.bg_color, fg=self.fg_color,
                       selectcolor=self.btn_bg, activebackground=self.bg_color).pack(side=tk.LEFT, padx=20)

        tk.Radiobutton(lang_frame, text=self.tr("chinese"), variable=language_var, value="zh",
                       font=("Times New Roman", 12), bg=self.bg_color, fg=self.fg_color,
                       selectcolor=self.btn_bg, activebackground=self.bg_color).pack(side=tk.LEFT, padx=20)

        def save_settings():
            self.volume_level = volume_scale.get()
            self.theme = theme_var.get()
            self.language = language_var.get()
            self.update_translations()
            self.set_theme_colors()
            self.apply_theme()
            self.adjust_speaker_volume(self.volume_level)
            settings_win.destroy()

        buttons_frame = tk.Frame(inner_frame, bg=self.bg_color)
        buttons_frame.pack(pady=10)

        save_btn = tk.Button(buttons_frame, text=self.tr("save"), font=("Times New Roman", 12, "bold"),
                             bg=self.fg_color, fg=self.bg_color,
                             activebackground=self.btn_active_bg,
                             command=save_settings, relief="raised", bd=3, padx=10)
        save_btn.pack(side=tk.LEFT, padx=10)
        cancel_btn = tk.Button(buttons_frame, text=self.tr("cancel"), font=("Times New Roman", 12, "bold"),
                               bg=self.btn_bg, fg=self.fg_color,
                               activebackground=self.btn_active_bg,
                               relief="raised", bd=2, command=settings_win.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=10)

    def adjust_speaker_volume(self, volume):
        try:
            subprocess.run(["amixer", "sset", "Master", f"{volume}%"], check=True)
        except Exception as e:
            print(f"Failed to set volume: {e}")

    def logout(self):
        if self.current_user:
            self.current_user = None
            messagebox.showinfo("Logout", "You have been logged out.")
            self.update_logout_button()
        else:
            messagebox.showinfo("Logout", "No user is currently logged in.")

    def login_prompt(self):
        def check_password():
            username = username_entry.get()
            password = password_entry.get()
            if password == HARDCODED_PASSWORD:
                self.current_user = username
                self.update_logout_button()
                prompt_win.destroy()
            else:
                error_label.config(text=self.tr("incorrect"))
                password_entry.delete(0, tk.END)

        border_color = "white" if self.theme == "dark" else "black"
        prompt_win = tk.Toplevel(self)
        prompt_win.grab_set()
        prompt_win.configure(bg=border_color)
        prompt_win.resizable(False, False)
        prompt_win.overrideredirect(True)

        width, height = 400, 320
        screen_width = prompt_win.winfo_screenwidth()
        screen_height = prompt_win.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        prompt_win.geometry(f"{width}x{height}+{x}+{y}")

        border_frame = tk.Frame(prompt_win, bg=border_color)
        border_frame.pack(expand=True, fill="both", padx=4, pady=4)

        inner_frame = tk.Frame(border_frame, bg=self.bg_color)
        inner_frame.pack(expand=True, fill="both")

        title = tk.Label(inner_frame, text=self.tr("login"), font=("Times New Roman", 20, "bold"),
                         bg=self.bg_color, fg=self.fg_color)
        title.pack(pady=(20, 10))

        separator = tk.Frame(inner_frame, height=2, bg=self.fg_color, bd=0, relief='flat')
        separator.pack(fill='x', padx=20, pady=(0, 10))

        tk.Label(inner_frame, text=self.tr("username"), font=("Times New Roman", 14),
                 bg=self.bg_color, fg=self.text_fg).pack(pady=(10))

        username_entry = tk.Entry(inner_frame, font=("Times New Roman", 14),
                                  bg="white" if self.theme == "light" else "#333333",
                                  fg="black" if self.theme == "light" else "#dddddd",
                                  insertbackground=self.text_fg)
        username_entry.pack(pady=(0, 5), ipady=3, ipadx=5)
        username_entry.focus()

        tk.Label(inner_frame, text=self.tr("pass"), font=("Times New Roman", 14),
                 bg=self.bg_color, fg=self.text_fg).pack(pady=(10))

        password_entry = tk.Entry(inner_frame, show="*", font=("Times New Roman", 14),
                                  bg="white" if self.theme == "light" else "#333333",
                                  fg="black" if self.theme == "light" else "#dddddd",
                                  insertbackground=self.text_fg)
        password_entry.pack(pady=(0, 5), ipady=3, ipadx=5)

        error_label = tk.Label(inner_frame, text="", fg="red", bg=self.bg_color, font=("Times New Roman", 12))
        error_label.pack()

        buttons_frame = tk.Frame(inner_frame, bg=self.bg_color)
        buttons_frame.pack(pady=10)

        submit_btn = tk.Button(buttons_frame, text=self.tr("submit"), font=("Times New Roman", 12),
                               bg=self.btn_bg, fg=self.fg_color,
                               activebackground=self.btn_active_bg,
                               command=check_password)
        submit_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = tk.Button(buttons_frame, text=self.tr("cancel"), font=("Times New Roman", 12),
                               bg=self.btn_bg, fg=self.fg_color,
                               activebackground=self.btn_active_bg,
                               command=prompt_win.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=10)

        prompt_win.bind("<Return>", lambda e: check_password())

    def update_logout_button(self):
        if self.current_user:
            self.logout_btn.pack(side=tk.RIGHT, padx=(20, 10))
        else:
            self.logout_btn.pack_forget()

    def staff_info(self):
        if not self.current_user:
            self.login_prompt()
            if not self.current_user:
                return

        border_color = "white" if self.theme == "dark" else "black"
        prompt_win = tk.Toplevel(self)
        prompt_win.grab_set()
        prompt_win.configure(bg=border_color)
        prompt_win.resizable(False, False)
        prompt_win.overrideredirect(True)

        width, height = 400, 220
        screen_width = prompt_win.winfo_screenwidth()
        screen_height = prompt_win.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        prompt_win.geometry(f"{width}x{height}+{x}+{y}")

        border_frame = tk.Frame(prompt_win, bg=border_color)
        border_frame.pack(expand=True, fill="both", padx=4, pady=4)

        inner_frame = tk.Frame(border_frame, bg=self.bg_color)
        inner_frame.pack(expand=True, fill="both")

        title = tk.Label(inner_frame, text=self.tr("staff_info"), font=("Times New Roman", 18, "bold"),
                         bg=self.bg_color, fg=self.fg_color)
        title.pack(pady=(20, 10))

        separator = tk.Frame(inner_frame, height=2, bg=self.fg_color, bd=0, relief='flat')
        separator.pack(fill='x', padx=20, pady=(0, 10))

        info_label = tk.Label(inner_frame, text=f"{self.tr('staff_in_charge')}: {self.current_user}",
                              font=("Times New Roman", 14), bg=self.bg_color, fg=self.text_fg, wraplength=350)
        info_label.pack(pady=10)

        button_frame = tk.Frame(inner_frame, bg=self.bg_color)
        button_frame.pack(pady=(0, 20))

        ok_button = tk.Button(button_frame, text=self.tr("ok"), font=("Times New Roman", 12),
                              bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg,
                              command=prompt_win.destroy)
        ok_button.pack(pady=(10, 20))

    def activity_log(self):
        if not self.current_user:
            self.login_prompt()
            if not self.current_user:
                return
        try:
            conn = mariadb.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, description, image_path FROM activity_log ORDER BY timestamp DESC")
            records = cursor.fetchall()
            conn.close()
        except mariadb.Error as err:
            messagebox.showerror("Database Error", f"Failed to fetch logs: {err}")
            return
        border_color = "white" if self.theme == "dark" else "black"

        log_window = tk.Toplevel(self)
        log_window.title("Activity Log")
        log_window.overrideredirect(True)
        log_window.geometry("1000x600")
        log_window.configure(bg=border_color)

        width, height = 1000, 600
        screen_width = log_window.winfo_screenwidth()
        screen_height = log_window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        log_window.geometry(f"{width}x{height}+{x}+{y}")

        border_frame = tk.Frame(log_window, bg=border_color)
        border_frame.pack(expand=True, fill="both", padx=4, pady=4)

        inner_frame = tk.Frame(border_frame, bg=self.bg_color)
        inner_frame.pack(expand=True, fill="both")

        title = tk.Label(inner_frame, text=self.tr("activity_log"), font=("Times New Roman", 20, "bold"),
                         bg=self.bg_color, fg=self.fg_color)
        title.pack(pady=(20, 10))

        separator = tk.Frame(inner_frame, height=2, bg=self.fg_color, bd=0, relief='flat')
        separator.pack(fill='x', padx=20, pady=(0, 10))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=self.bg_color, fieldbackground=self.bg_color,
                        foreground=self.text_fg, rowheight=30)
        style.configure("Treeview.Heading", font=("Times New Roman", 14, "bold"),
                        background=self.btn_bg, foreground=self.fg_color)

        columns = ("Time", "Description", "Image")
        tree = ttk.Treeview(inner_frame, columns=columns, show="headings")

        tree.heading("Time", text=self.tr("time"))
        tree.heading("Description", text=self.tr("description"))
        tree.heading("Image", text=self.tr("image"))

        tree.column("Time", width=200, anchor="center")
        tree.column("Description", width=500, anchor="w")
        tree.column("Image", width=250, anchor="center")

        for timestamp, desc, image_path in records:
            img = image_path if image_path else "nil"
            tree.insert("", "end", values=(timestamp, desc, img))

        tree.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        button_frame = tk.Frame(inner_frame, bg=self.bg_color)
        button_frame.pack(pady=(0, 20))

        cancel_btn = tk.Button(button_frame, text=self.tr("cancel"), font=("Times New Roman", 12),
                              bg=self.btn_bg, fg=self.fg_color,
                              activebackground=self.btn_active_bg,
                              command=log_window.destroy)
        cancel_btn.pack()

    def about_system(self):
        border_color = "white" if self.theme == "dark" else "black"
        about_win = tk.Toplevel(self)
        about_win.title("About the System")
        about_win.configure(bg=border_color)
        about_win.resizable(False, False)
        about_win.overrideredirect(True)

        width, height = 500, 400
        self.center_window(about_win, width, height)

        border_frame = tk.Frame(about_win, bg=border_color)
        border_frame.pack(expand=True, fill="both")

        inner_frame = tk.Frame(border_frame, bg=self.bg_color)
        inner_frame.pack(expand=True, fill="both", padx=4, pady=4)

        header = tk.Label(inner_frame, text="ðŸ›’ About the Supermarket System",
                          font=("Times New Roman", 18, "bold"), bg="#007c30", fg="white", pady=10)
        header.pack(fill=tk.X)
        content = (
            "âŒ› Platform: Raspberry Pi 5\n"
            "âŒ¨ï¸ Language: Python 3 (Tkinter GUI)\n"
            "[â—‰Â°] Cameras: Dome Camera + Ribbon Camera\n"
            "âšœï¸ Features:\n"
            "  - Object & Item Count\n"
            "  - Barcode Scanner Integration\n"
            "  - Real-Time Activity Logging\n"
            "  - Staff Management Panel\n\n"
            "Designed for secure and efficient self-checkout monitoring."
        )
        label = tk.Label(inner_frame, text=content, font=("Times New Roman", 12),
                         bg="#e8f5e9", fg="#333333", justify="left", anchor="nw", padx=20, pady=20)
        label.pack(fill=tk.BOTH, expand=True)
        close_btn = tk.Button(inner_frame, text="Close", command=about_win.destroy,
                              font=("Times New Roman", 12, "bold"), bg="#007c30", fg="white", padx=10, pady=5,
                              activebackground="#005c24", relief="flat")
        close_btn.pack(pady=10)

    def create_tip_box(self, parent):
        tips = itertools.cycle([
            "Use 'Live Camera Feed' to monitor checkout areas.",
            "Remember to log out when you're done.",
            "Check Activity Log for anomalies.",
            "Use the Settings to customize system preferences."
        ])
        tip_label = tk.Label(parent, text=next(tips), bg="white", fg="#333333",
                             font=("Times New Roman", 18, "italic"), wraplength=700, justify="center")
        tip_label.pack(pady=(50, 10))
        def update_tip():
            tip_label.config(text=next(tips))
            tip_label.after(5000, update_tip)
        update_tip()

    def update_status_bar(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.status_label.config(text=f"System Status: Online | Last Sync: {now}")
        self.status_label.after(5000, self.update_status_bar)

    def center_window(self, window, width, height):
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def shutdown(self):
        def shutdown_yes():
            confirm_win.destroy()
            self.destroy()

        def shutdown_no():
            confirm_win.destroy()

        border_color = "white" if self.theme == "dark" else "black"
        confirm_win = tk.Toplevel(self)
        confirm_win.grab_set()
        confirm_win.resizable(False, False)
        confirm_win.configure(bg=border_color)
        confirm_win.overrideredirect(True)

        width, height = 420, 220
        x = (confirm_win.winfo_screenwidth() // 2) - (width // 2)
        y = (confirm_win.winfo_screenheight() // 2) - (height // 2)
        confirm_win.geometry(f"{width}x{height}+{x}+{y}")

        border_frame = tk.Frame(confirm_win, bg=border_color)
        border_frame.pack(expand=True, fill="both", padx=4, pady=4)

        inner_frame = tk.Frame(border_frame, bg=self.bg_color)
        inner_frame.pack(expand=True, fill="both")

        title = tk.Label(inner_frame, text=self.tr("confirm"), font=("Times New Roman", 20, "bold"),
                         bg=self.bg_color, fg=self.fg_color)
        title.pack(pady=(20, 10))

        separator = tk.Frame(inner_frame, height=2, bg=self.fg_color, bd=0, relief='flat')
        separator.pack(fill='x', padx=20, pady=(0, 20))

        tk.Label(inner_frame, text=self.tr("AYS"),
                 font=("Times New Roman", 14), bg=self.bg_color, fg=self.text_fg,
                 wraplength=360, justify="center").pack(pady=(0, 40))

        buttons_frame = tk.Frame(inner_frame, bg=self.bg_color)
        buttons_frame.pack()

        yes_btn = tk.Button(buttons_frame, text="Yes", font=("Times New Roman", 12, "bold"),
                            bg=self.btn_bg, fg=self.fg_color,
                            activebackground=self.btn_active_bg,
                            relief="raised", bd=2, width=10,
                            command=shutdown_yes)
        yes_btn.pack(side=tk.LEFT, padx=10)

        no_btn = tk.Button(buttons_frame, text="No", font=("Times New Roman", 12, "bold"),
                           bg=self.btn_bg, fg=self.fg_color,
                           activebackground=self.btn_active_bg,
                           relief="raised", bd=2, width=10,
                           command=shutdown_no)
        no_btn.pack(side=tk.LEFT, padx=10)
        confirm_win.bind("<Return>", lambda event: shutdown_yes())

    def start_detection(self):
        if self.running:
            return
        try:
            self.picam2 = Picamera2(1)
            self.picam2.configure(self.picam2.create_preview_configuration(main={"format": "RGB888", "size": (1280, 720)}))
            self.picam2.start()
            self.running = True
            self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
            self.detection_thread.start()
            print("Camera initialized successfully")
        except Exception as e:
            print(f"Failed to initialize camera: {e}")
            messagebox.showerror("Error", f"Cannot initialize camera: {e}")
            self.running = False

    def stop_detection(self):
        if self.running:
            self.running = False
            if self.picam2:
                self.picam2.stop()
                self.picam2 = None
            print("Camera stopped")

    def detection_loop(self):
        while self.running:
            if not self.picam2:
                break
            frame = self.picam2.capture_array()
            if frame is None:
                continue

            if USE_FIXED_ROI:
                roi = frame[self.roi_y1:self.roi_y2, self.roi_x1:self.roi_x2]
            else:
                detections = self.dummy_yolo_detector(frame)
                if not detections:
                    continue
                det = detections[0]
                if det['label'] != 'number' or det['conf'] <= 0.5:
                    continue
                x1, y1, x2, y2 = det['bbox']
                self.roi_x1 = max(0, x1 - PADDING_X)
                self.roi_y1 = max(0, y1 - PADDING_Y)
                self.roi_x2 = min(frame.shape[1], x2 + PADDING_X)
                self.roi_y2 = min(frame.shape[0], y2 + PADDING_Y)
                roi = frame[self.roi_y1:self.roi_y2, self.roi_x1:self.roi_x2]

            cv2.rectangle(frame, (self.roi_x1, self.roi_y1), (self.roi_x2, self.roi_y2), (0, 255, 0), 2)
            processed = self.preprocess_for_ocr(roi)
            self.ocr_queue.put(processed)
            time.sleep(0.1)  # Prevent overloading the queue

    def ocr_loop(self):
        while True:
            roi = self.ocr_queue.get()
            if roi is None:
                break
            results = self.reader.readtext(roi, allowlist='0123456789', min_size=3, text_threshold=0.4, adjust_contrast=0.6)
            detected_text = "".join([char for res in results for char in res[1] if char.isdigit()])
            # Apply fake ghost padding: prepend '0' to detected number
            padded_text = "0" + detected_text if detected_text else "0"
            self.detected_number = padded_text
            if detected_text:
                self.recent_detections.append(padded_text)
                debounce_threshold = 3 if len(detected_text) == 1 else DEBOUNCE_COUNT  # Lower threshold for single digits
                if len(self.recent_detections) >= debounce_threshold:
                    most_common = Counter(self.recent_detections).most_common(1)[0]
                    if most_common[1] >= debounce_threshold - 1:
                        print(f"âœ… Confirmed Number: {most_common[0]}")
            else:
                self.recent_detections.clear()

    def live_camera(self):
        if not self.running or not self.picam2:
            self.start_detection()
            if not self.running or not self.picam2:
                tk.messagebox.showerror("Error", "Cannot open camera")
                return

        border_color = "white" if self.theme == "dark" else "black"
        width, height = 700, 750
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)

        self.live_cam_win = tk.Toplevel(self)
        self.live_cam_win.grab_set()
        self.live_cam_win.resizable(False, False)
        self.live_cam_win.configure(bg=border_color)
        self.live_cam_win.overrideredirect(True)
        self.live_cam_win.geometry(f"{width}x{height}+{x}+{y}")

        border_frame = tk.Frame(self.live_cam_win, bg=border_color)
        border_frame.pack(expand=True, fill="both", padx=4, pady=4)

        inner_frame = tk.Frame(border_frame, bg=self.bg_color)
        inner_frame.pack(expand=True, fill="both")

        dome_title = tk.Label(inner_frame, text=self.tr("Dome Camera Feed"), font=("Times New Roman", 20, "bold"),
                              bg=self.bg_color, fg=self.fg_color)
        dome_title.pack(pady=(10, 5))

        dome_sep = tk.Frame(inner_frame, height=2, bg=self.fg_color)
        dome_sep.pack(fill='x', padx=20, pady=(0, 10))

        dome_frame = tk.Frame(inner_frame, bg=self.bg_color)
        dome_frame.pack(pady=(0, 20))

        self.dome_img_label = tk.Label(dome_frame, bg=self.bg_color)
        self.dome_img_label.pack()

        ribbon_title = tk.Label(inner_frame, text=self.tr("Ribbon Camera Feed"), font=("Times New Roman", 20, "bold"),
                                bg=self.bg_color, fg=self.fg_color)
        ribbon_title.pack(pady=(0, 5))

        ribbon_sep = tk.Frame(inner_frame, height=2, bg=self.fg_color)
        ribbon_sep.pack(fill='x', padx=20, pady=(0, 10))

        ribbon_frame = tk.Frame(inner_frame, bg=self.bg_color)
        ribbon_frame.pack(pady=(0, 20))

        self.raw_img_label = tk.Label(ribbon_frame, bg=self.bg_color)
        self.raw_img_label.pack(side=tk.LEFT, padx=10)

        self.proc_img_label = tk.Label(ribbon_frame, bg=self.bg_color)
        self.proc_img_label.pack(side=tk.LEFT, padx=10)

        def on_close():
            self.live_cam_running = False
            self.live_cam_win.destroy()

        cancel_btn = tk.Button(inner_frame, text=self.tr("exit"), font=("Times New Roman", 12, "bold"),
                               bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg,
                               relief="raised", bd=2, width=12, command=on_close)
        cancel_btn.pack(pady=(0, 10))

        self.live_cam_win.bind("<Escape>", lambda e: on_close())
        self.live_cam_win.protocol("WM_DELETE_WINDOW", on_close)

        self.live_cam_running = True

        def update_frame():
            if not self.live_cam_running or not self.live_cam_win.winfo_exists():
                return
            if not self.picam2:
                return

            frame = self.picam2.capture_array()
            if frame is not None:
                dome_resized = cv2.resize(frame, (640, 250))
                dome_rgb = cv2.cvtColor(dome_resized, cv2.COLOR_BGR2RGB)
                dome_img = Image.fromarray(dome_rgb)
                dome_imgtk = ImageTk.PhotoImage(image=dome_img)
                self.dome_img_label.imgtk = dome_imgtk
                self.dome_img_label.config(image=dome_imgtk)

                frame_resized = cv2.resize(frame, (300, 230))
                detections = self.dummy_yolo_detector(frame_resized)
                if detections:
                    det = detections[0]
                    x1, y1, x2, y2 = det['bbox']
                    label = det['label']
                    conf = det['conf']

                    if label == 'number' and conf > 0.5:
                        x1_exp = max(0, x1 - PADDING_X)
                        y1_exp = max(0, y1 - PADDING_Y)
                        x2_exp = min(frame_resized.shape[1], x2 + PADDING_X)
                        y2_exp = min(frame_resized.shape[0], y2 + PADDING_Y)

                        roi = frame_resized[y1_exp:y2_exp, x1_exp:x2_exp]
                        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                        thresh_resized = cv2.resize(thresh, (300, 230))

                        results = self.reader.readtext(thresh, allowlist='0123456789', min_size=3, text_threshold=0.4, adjust_contrast=0.6)
                        detected_text = "".join([c for res in results for c in res[1] if c.isdigit()])
                        # Apply fake ghost padding for display
                        padded_text = "0" + detected_text if detected_text else "0"

                        if detected_text:
                            self.recent_detections.append(padded_text)
                            if len(self.recent_detections) == DEBOUNCE_COUNT:
                                if all(text == self.recent_detections[0] for text in self.recent_detections):
                                    print(f"âœ… Confirmed Number: {self.recent_detections[0]}")
                        else:
                            self.recent_detections.clear()

                        cv2.rectangle(frame_resized, (x1_exp, y1_exp), (x2_exp, y2_exp), (0, 255, 0), 2)
                        cv2.putText(frame_resized, padded_text, (x1_exp, y1_exp - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                        img_proc = Image.fromarray(thresh_resized)
                        imgtk_proc = ImageTk.PhotoImage(image=img_proc)
                        self.proc_img_label.imgtk = imgtk_proc
                        self.proc_img_label.config(image=imgtk_proc)
                    else:
                        self.proc_img_label.config(image='')
                else:
                    self.proc_img_label.config(image='')

                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                img_raw = Image.fromarray(frame_rgb)
                imgtk_raw = ImageTk.PhotoImage(image=img_raw)
                self.raw_img_label.imgtk = imgtk_raw
                self.raw_img_label.config(image=imgtk_raw)

            self.live_cam_win.after(30, update_frame)

        update_frame()

    def dummy_yolo_detector(self, frame):
        height, width = frame.shape[:2]
        # Use a smaller bounding box for single digits
        box_w, box_h = width // 8, height // 10  # Reduced size for single digits
        x1 = width // 2 - box_w // 2
        y1 = height // 2 - box_h // 2
        x2 = x1 + box_w
        y2 = y1 + box_h
        return [{'bbox': (x1, y1, x2, y2), 'conf': 0.9, 'label': 'number'}]

    def preprocess_for_ocr(self, image):
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Apply histogram equalization to improve contrast
        gray = cv2.equalizeHist(gray)
        # Apply mild Gaussian blur to reduce noise but preserve edges
        blur = cv2.GaussianBlur(gray, (1, 1), 0)
        # Use adaptive thresholding for better handling of lighting variations
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY_INV, 11, 2)
        # Apply morphological operations to clean up small noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        return thresh

    def start(self):
        live_counts_win = tk.Toplevel(self)
        live_counts_win.title("Live Counts")
        live_counts_win.attributes('-fullscreen', True)
        live_counts_win.configure(bg="#e8f5e9")

        dome_count = tk.IntVar(value=random.randint(0, 20))
        ribbon_count = tk.IntVar(value=0)

        def update_counts():
            dome_count.set(random.randint(0, 20))
            try:
                detected_num = int(self.detected_number)
            except (AttributeError, ValueError):
                detected_num = 0
            ribbon_count.set(detected_num)
            live_counts_win.after(2000, update_counts)

        def after_count_init():
            flash_screen = tk.Toplevel(self)
            flash_screen.withdraw()
            flash_screen.attributes('-fullscreen', True)
            flash_screen.configure(bg="white")
            flash_screen.attributes("-topmost", True)

            flash_image_label = tk.Label(flash_screen, bg="white")
            flash_image_label.pack(pady=(100, 20))

            flash_label = tk.Label(flash_screen, bg="white")
            flash_label.pack()

            flash_loop_id = {"id": None}

            barcode_blocked_img = tk.PhotoImage(file="~/Downloads/barcode_blocked.png").subsample(2, 2)
            multiple_barcode_img = tk.PhotoImage(file="~/Downloads/multiple_barcode.png").subsample(2, 2)
            camera_blocked_img = tk.PhotoImage(file="~/Downloads/camera_blocked.png").subsample(2, 2)
            barcode_detected_img = tk.PhotoImage(file="~/Downloads/barcode_detected.png").subsample(2, 2)

            def flash_green_tick(text, img):
                flash_screen.configure(bg="#00ff00")
                flash_label.config(text=text,
                                   font=("Times New Roman", 48, "bold"),
                                   fg="white", bg="#00ff00")
                flash_image_label.config(image=img, bg="#00ff00")
                flash_screen.deiconify()
                flash_screen.after(1000, lambda: [
                    flash_screen.withdraw(),
                    live_counts_win.lift(),
                    live_counts_win.focus_force()
                ])

            def flash_red_screen(text, img):
                flash_screen.configure(bg="#ff0000")
                flash_label.config(text=text,
                                   font=("Times New Roman", 48, "bold"),
                                   fg="white", bg="#ff0000")
                flash_image_label.config(image=img, bg="#ff0000")
                flash_screen.deiconify()
                flash_screen.after(1500, lambda: [
                    flash_screen.withdraw(),
                    live_counts_win.lift(),
                    live_counts_win.focus_force()
                ])

            def simulate_flash_events():
                if not live_counts_win.winfo_exists():
                    return
                events = [
                    lambda: flash_green_tick(self.tr("barcode_detected"), barcode_detected_img),
                    lambda: flash_red_screen(self.tr("barcode_blocked"), barcode_blocked_img),
                    lambda: flash_red_screen(self.tr("multiple_barcodes"), multiple_barcode_img),
                    lambda: flash_red_screen(self.tr("camera_blocked"), camera_blocked_img)
                ]
                func = random.choice(events)
                func()
                flash_loop_id["id"] = self.after(5000, simulate_flash_events)

            def on_live_counts_close():
                if flash_loop_id["id"] is not None:
                    self.after_cancel(flash_loop_id["id"])
                flash_screen.destroy()
                live_counts_win.destroy()

            live_counts_win.protocol("WM_DELETE_WINDOW", on_live_counts_close)

            simulate_flash_events()

        self.after(1000, after_count_init)

        container = tk.Frame(live_counts_win, bg="#e8f5e9")
        container.pack(expand=True, fill=tk.BOTH, pady=150, padx=100)

        dome_frame = tk.Frame(container, bg="#e8f5e9")
        dome_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=50)

        tk.Label(dome_frame, text=self.tr("dome_camera"), font=("Times New Roman", 24), bg="#e8f5e9").pack(pady=(0, 10))
        tk.Label(dome_frame, textvariable=dome_count, font=("Times New Roman", 72, "bold"), fg="#007c30", bg="#e8f5e9").pack()

        ribbon_frame = tk.Frame(container, bg="#e8f5e9")
        ribbon_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=50)

        tk.Label(ribbon_frame, text=self.tr("ribbon_camera"), font=("Times New Roman", 24), bg="#e8f5e9").pack(pady=(0, 10))
        tk.Label(ribbon_frame, textvariable=ribbon_count, font=("Times New Roman", 72, "bold"), fg="#007c30", bg="#e8f5e9").pack()

        def exit_fullscreen():
            def check_password():
                if password_entry.get() == HARDCODED_PASSWORD:
                    prompt_win.destroy()
                    live_counts_win.destroy()
                    if flash_loop_id["id"] is not None:
                        self.after_cancel(flash_loop_id["id"])
                    flash_screen.destroy()
                else:
                    error_label.config(text=self.tr("incorrect"))
                    password_entry.delete(0, tk.END)

            border_color = "white" if self.theme == "dark" else "black"
            prompt_win = tk.Toplevel(live_counts_win)
            prompt_win.grab_set()
            prompt_win.resizable(False, False)
            prompt_win.configure(bg=border_color)
            prompt_win.overrideredirect(True)

            width, height = 400, 200
            screen_width = prompt_win.winfo_screenwidth()
            screen_height = prompt_win.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            prompt_win.geometry(f"{width}x{height}+{x}+{y}")

            border_frame = tk.Frame(prompt_win, bg=border_color)
            border_frame.pack(expand=True, fill="both")

            inner_frame = tk.Frame(border_frame, bg=self.bg_color)
            inner_frame.pack(expand=True, fill="both", padx=4, pady=4)

            title = tk.Label(inner_frame, text=self.tr("passreq"), font=("Times New Roman", 20, "bold"),
                             bg=self.bg_color, fg=self.fg_color)
            title.pack(pady=(20, 10))

            separator = tk.Frame(inner_frame, height=2, bg=self.fg_color, bd=0, relief='flat')
            separator.pack(fill='x', padx=20, pady=(0, 10))

            password_entry = tk.Entry(inner_frame, show="*", font=("Times New Roman", 14),
                                     bg="white" if self.theme == "light" else "#333333",
                                     fg="black" if self.theme == "light" else "#dddddd",
                                     insertbackground=self.text_fg,
                                     relief="solid", bd=1)
            password_entry.pack(pady=10)
            password_entry.focus()

            error_label = tk.Label(inner_frame, text="", fg="red", bg=self.bg_color, font=("Times New Roman", 12))
            error_label.pack()

            buttons_frame = tk.Frame(inner_frame, bg=self.bg_color)
            buttons_frame.pack(pady=10)

            tk.Button(buttons_frame, text=self.tr("submit"), font=("Times New Roman", 12, "bold"),
                      bg=self.btn_bg, fg=self.fg_color,
                      activebackground=self.btn_active_bg, bd=2,
                      command=check_password).pack(side=tk.LEFT, padx=10)

            tk.Button(buttons_frame, text=self.tr("cancel"), font=("Times New Roman", 12, "bold"),
                      bg=self.btn_bg, fg=self.fg_color,
                      activebackground=self.btn_active_bg, bd=2,
                      command=prompt_win.destroy).pack(side=tk.LEFT, padx=10)
            prompt_win.bind("<Return>", lambda e: check_password())

        exit_btn = tk.Button(live_counts_win, text=self.tr("exit"), font=("Times New Roman", 14, "bold"),
                             bg="#e8f5e9", activebackground="#c8e6c9", relief="raised", bd=3,
                             command=exit_fullscreen)
        exit_btn.pack(side=tk.BOTTOM, pady=40)
        live_counts_win.bind("<Escape>", lambda e: exit_fullscreen())

        update_counts()

if __name__ == "__main__":
    app = SupermarketApp()
    app.mainloop()
