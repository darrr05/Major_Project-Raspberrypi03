import tkinter as tk
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
import queue
import paho.mqtt.client as mqtt
import re

from io import BytesIO
from picamera2 import Picamera2
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk, ImageSequence
from collections import deque, Counter
from tkinter import ttk

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "Anti_Theftdb"
}

# Adjustable parameters
USE_FIXED_ROI = False
PADDING_X = 50
PADDING_Y = 30
ROI_Y1, ROI_Y2 = 100, 200  # Only used if USE_FIXED_ROI = True
ROI_X1, ROI_X2 = 300, 500
DEBOUNCE_COUNT = 2  # Kept at 2 for faster response
HARDCODED_PASSWORD = "admin123"

MQTT_BROKER = "10.238.131.60"
MQTT_PORT = 1883
MQTT_TOPIC_BARCODE = "barcode/data"
MQTT_TOPIC_COUNTER = "counter/data"
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
        "barcode_detected": "✅ Barcode Detected",
        "barcode_blocked": "✖ Barcode Blocked",
        "multiple_barcodes": "✖ Multiple Barcodes Detected",
        "camera_blocked": "✖ Camera Blocked",
        "language": "Language:",
        "english": "English",
        "chinese": "中文",
        "about_system": "ℹ️ About the System",
        "staff_in_charge": "⚒️ Staff in Charge",
        "live_camera_feed": "[◉°] Live Camera Feed",
        "activity_log": "✍️ Activity Log",
        "start": "Start",
        "submit": "Submit",
        "login": "Login",
        "username": "Username:",
        "pass": "Password:",
        "incorrect": "Incorrect password. Try again.",
        "shutdown": "⚠️ Shutdown Access",
        "passreq": "Password Required",
        "confirm": "Confirm Shutdown",
        "AYS": "Are you sure you want to shutdown the system?",
        "logout": "☯︎ Logout",
        "staff_info": "Staff Information",
        "ok": "OK",
        "time": "Time",
        "description": "Description",
        "image": "Image",
        "exit": "Exit",
        "delete": "Delete",
        "mqtt_broker": "MQTT Broker IP:",
        "invalid_ip": "Invalid IP address format",
        "object_count": "Object Count",
        "number_count": "Summary Count",
    },
    "zh": {
        "settings": "设置",
        "volume": "扬声器音量：",
        "theme": "显示主题：",
        "light_mode": "浅色模式",
        "dark_mode": "深色模式",
        "save": "保存",
        "cancel": "取消",
        "dome_camera": "球形摄像头计数",
        "ribbon_camera": "条码摄像头计数",
        "barcode_detected": "✅ 检测到条码",
        "barcode_blocked": "✖ 条码被遮挡",
        "multiple_barcodes": "✖ 检测到多个条码",
        "camera_blocked": "✖ 摄像头被遮挡",
        "language": "语言：",
        "english": "English",
        "chinese": "中文",
        "about_system": "ℹ️ 关于系统",
        "staff_in_charge": "⚒️ 负责人",
        "live_camera_feed": "[◉°] 实时摄像头画面",
        "activity_log": "✍️ 活动记录",
        "start": "开始",
        "submit": "提交",
        "login": "登录",
        "username": "用户名:",
        "pass": "密码:",
        "incorrect": "密码不正确。请重试.",
        "shutdown": "⚠️ 关机访问",
        "passreq": "需要密码",
        "confirm": "确认关机",
        "AYS": "您确定要关闭系统吗?",
        "logout": "☯︎ 退出登录",
        "staff_info": "负责人信息",
        "ok": "好",
        "time": "时间",
        "description": "描述",
        "image": "图片",
        "exit": "退出",
        "delete": "删除",
        "mqtt_broker": "MQTT经纪人IP：",
        "invalid_ip": "无效的IP地址格式",
        "object_count": "物件数目",
        "number_count": "数目统计",
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
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        
        self.mqtt_client = None
        self.mqtt_thread = None
        self.current_user = None
        self.mqtt_broker = MQTT_BROKER

        self.volume_level = 50
        self.theme = "light"
        self.set_theme_colors()

        self.gradient_bg = GradientFrame(self, "#007c30", "#a4d4ae")
        self.gradient_bg.pack(fill="both", expand=True)

        self.border_frame = tk.Frame(self.gradient_bg, bg="white", bd=4, relief="groove")
        self.border_frame.place(relx=0.5, rely=0.01, anchor="n", width=1250, height=720)

        self.create_widgets()
        self.bind("<Escape>", lambda e: self.destroy())
        self.picam2 = None
        self.running = False
        self.detection_thread = None
        self.detected_number = "0"
        self.confirmed_number = "0"
        self.dome_count = tk.IntVar(value=0)
        self.number_lock = threading.Lock()
        self.recent_detections = deque(maxlen=DEBOUNCE_COUNT)
        self.reader = easyocr.Reader(['en'], recog_network='best_accuracy', gpu=False)
        self.ocr_queue = queue.Queue(maxsize=10)
        self.ocr_thread = threading.Thread(target=self.ocr_loop, daemon=True)
        self.ocr_thread.start()
        self.start_detection()
        self.flash_screen = None
        self.flash_loop_id = None
        self.roi_save_counter = 0
        self.flash_lock = threading.Lock()  # Lock for flash operations
        self.last_flash_time = 0  # Timestamp of last flash
        self.flash_cooldown = 3.5  # Cooldown period (seconds)
        self.current_flash_key = None
        self.current_animation = None

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
        else:
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
        self.gradient_bg.color1 = self.bg_gradient_start
        self.gradient_bg.color2 = self.bg_gradient_end
        self.gradient_bg._draw_gradient()
        self.border_frame.config(bg=self.bg_color)
        self.grid_frame.config(bg=self.grid_frame_bg)
        for widget in self.grid_frame.winfo_children():
            if isinstance(widget, tk.Label):
                widget.config(bg=self.grid_frame_bg, fg=self.text_fg)
            elif isinstance(widget, tk.Button):
                widget.config(bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg)
        self.top_bar.config(bg=self.top_bar_bg)
        for widget in self.top_bar.winfo_children():
            if isinstance(widget, tk.Button):
                if widget in (self.settings_btn, self.shutdown_btn):
                    widget.config(bg=self.top_bar_bg, fg=self.fg_color if self.theme == "dark" else "black", activebackground="#335533" if self.theme == "dark" else "#d6f5d6")
                elif widget == self.logout_btn:
                    widget.config(bg=self.top_bar_bg, fg="red", activebackground="#fddede")
                else:
                    widget.config(bg=self.top_bar_bg, fg=self.fg_color, activebackground="#d6f5d6" if self.theme == "light" else "#335533")
        for child in self.border_frame.winfo_children():
            if isinstance(child, tk.Frame) and child != self.top_bar:
                child.config(bg=self.bg_color)
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Label):
                        subchild.config(bg=self.bg_color, fg=self.text_fg)
                    elif isinstance(subchild, tk.Button):
                        subchild.config(bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg)
                    elif isinstance(subchild, tk.Frame):
                        for nested in subchild.winfo_children():
                            if isinstance(nested, tk.Label):
                                nested.config(bg=self.bg_color, fg=self.text_fg)
                            elif isinstance(nested, tk.Button):
                                nested.config(bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg)
        self.status_label.config(bg=self.bg_color, fg=self.fg_color)

    def create_widgets(self):
        self.top_bar = tk.Frame(self.border_frame, bg="white")
        self.top_bar.pack(side=tk.TOP, fill=tk.X, pady=10)
        self.settings_btn = tk.Button(self.top_bar, text="⚙", font=("Times New Roman", 20), command=self.open_settings,
                                     bg="white", bd=0, activebackground="lightgray")
        self.settings_btn.pack(side=tk.LEFT, padx=20)
        shutdown_path = os.path.expanduser("/home/pi/hailo-rpi5-examples/images/pb2.png")
        self.shutdown_btn = tk.Button(self.top_bar, font=("Times New Roman", 20),
                                     command=self.prompt_shutdown_password, bg="white", fg="black", bd=0,
                                     activebackground="lightgray")
        if os.path.exists(shutdown_path):
            shutdown_img = Image.open(shutdown_path)
            shutdown_img = shutdown_img.resize((40, 40))
            shutdown_img_tk = ImageTk.PhotoImage(shutdown_img)
            self.shutdown_btn.config(image=shutdown_img_tk)
            self.shutdown_btn.image = shutdown_img_tk
        else:
            self.shutdown_btn.config(text="Shutdown")
        self.shutdown_btn.pack(side=tk.RIGHT, padx=(10, 20))
        self.logout_btn = tk.Button(self.top_bar, text=self.tr("logout"), font=("Times New Roman", 20),
                                   command=self.logout, fg="red", bg="white", bd=0, activebackground="lightgray")
        self.logout_btn.pack_forget()
        center_frame = tk.Frame(self.border_frame, bg="white")
        center_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        logo_path = os.path.expanduser("/home/pi/hailo-rpi5-examples/images/Giant Logo.png")
        logo_label = tk.Label(center_frame, bg="white")
        if os.path.exists(logo_path):
            logo_img = Image.open(logo_path)
            logo_img.thumbnail((200, 200))
            self.logo = ImageTk.PhotoImage(logo_img)
            logo_label.config(image=self.logo)
        else:
            logo_label.config(text="🛒 Giant Supermarket", font=("Times New Roman", 24, "bold"), fg="#007c30")
        logo_label.pack(pady=10)
        self.grid_frame = tk.Frame(center_frame, bg="white")
        self.grid_frame.pack(pady=(10, 0))
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
        self.simulate_log_btn = tk.Button(self.grid_frame, text="Simulate Log", command=self.simulate_activity_log,
                                         width=14, height=2, font=("Times New Roman", 12, "bold"),
                                         bg="#e8f5e9", activebackground="#c8e6c9", bd=2, relief="ridge")
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
        self.logout_btn.config(text=f"{self.tr('logout')}" if self.tr("logout") else "⏻ Logout")
        self.update_status_bar()

    def simulate_activity_log(self):
        try:
            conn = mariadb.connect(**DB_CONFIG)
            cursor = conn.cursor()
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            description = "Simulated Theft Attempt Detected"
            image_path = ""
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
                                 insertbackground=self.text_fg, relief="solid", bd=1, width=25)
        password_entry.pack(pady=10)
        password_entry.focus()
        error_label = tk.Label(inner_frame, text="", font=("Times New Roman", 12),
                              fg="red", bg=self.bg_color)
        error_label.pack()
        buttons_frame = tk.Frame(inner_frame, bg=self.bg_color)
        buttons_frame.pack(pady=10)
        submit_btn = tk.Button(buttons_frame, text=self.tr("submit"), font=("Times New Roman", 12, "bold"),
                              bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg,
                              relief="raised", bd=2, command=check_password)
        submit_btn.pack(side=tk.LEFT, padx=10)
        cancel_btn = tk.Button(buttons_frame, text=self.tr("cancel"), font=("Times New Roman", 12, "bold"),
                              bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg,
                              relief="raised", bd=2, command=prompt_win.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=10)
        prompt_win.bind("<Return>", lambda event: check_password())

    def validate_ip(self, ip):
        ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        return re.match(ip_pattern, ip) is not None
        
    def open_settings(self):
        border_color = "white" if self.theme == "dark" else "black"
        settings_win = tk.Toplevel(self)
        settings_win.title("Settings")
        settings_win.geometry("500x500")
        self.center_window(settings_win, 500, 600)
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
                      
        tk.Label(inner_frame, text=self.tr("mqtt_broker"), font=("Times New Roman", 14),
                bg=self.bg_color, fg=self.fg_color).pack(pady=(30, 10))
                      
        mqtt_entry = tk.Entry(inner_frame, font=("Times New Roman", 12),
                             bg="white" if self.theme == "light" else "#333333",
                             fg="black" if self.theme == "light" else "#dddddd",
                             insertbackground=self.text_fg)
        mqtt_entry.insert(0, self.mqtt_broker)
        mqtt_entry.pack()
        
        error_label = tk.Label(inner_frame, text="", font=("Times New Roman", 12),
                              fg="red", bg=self.bg_color)
        error_label.pack()
        
        def save_settings():
            new_ip = mqtt_entry.get()
            if not self.validate_ip(new_ip):
                error_label.config(text=self.tr("invalid_ip"))
                return
            self.volume_level = volume_scale.get()
            self.theme = theme_var.get()
            self.language = language_var.get()
            self.update_translations()
            self.set_theme_colors()
            self.apply_theme()
            self.adjust_speaker_volume(self.volume_level)
            settings_win.destroy()
            self.mqtt_broker = new_ip
            
        buttons_frame = tk.Frame(inner_frame, bg=self.bg_color)
        buttons_frame.pack(pady=10)
        save_btn = tk.Button(buttons_frame, text=self.tr("save"), font=("Times New Roman", 12, "bold"),
                            bg=self.fg_color, fg=self.bg_color, activebackground=self.btn_active_bg,
                            relief="raised", bd=3, padx=10, command=save_settings)
        save_btn.pack(side=tk.LEFT, padx=10)
        cancel_btn = tk.Button(buttons_frame, text=self.tr("cancel"), font=("Times New Roman", 12, "bold"),
                              bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg,
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
        def delete_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning(self.tr("warning"), self.tr("select_log_first"))
                return
            try:
                conn = mariadb.connect(**DB_CONFIG)
                cursor = conn.cursor()

                for item in selected:
                    log_id = tree.item(item)['values'][0]
                    cursor.execute("DELETE FROM activity_log WHERE id = ?", (log_id,))
                    tree.delete(item)

                conn.commit()
                conn.close()
            except mariadb.Error as err:
                messagebox.showerror("Database Error", f"Failed to delete log: {err}")

        button_frame = tk.Frame(inner_frame, bg=self.bg_color)
        button_frame.pack(pady=(0, 20))

        cancel_btn = tk.Button(button_frame, text=self.tr("cancel"), font=("Times New Roman", 12),
                            bg=self.btn_bg, fg=self.fg_color,
                            activebackground=self.btn_active_bg,
                            command=log_window.destroy)
        cancel_btn.pack(side="left", padx=10)

        delete_btn = tk.Button(button_frame, text=self.tr("delete"), font=("Times New Roman", 12),
                            bg=self.btn_bg, fg=self.fg_color,
                            activebackground=self.btn_active_bg,
                            command=delete_selected)
        delete_btn.pack(side="left", padx=10)

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
        header = tk.Label(inner_frame, text="🛒 About the Supermarket System",
                         font=("Times New Roman", 18, "bold"), bg="#007c30", fg="white", pady=10)
        header.pack(fill=tk.X)
        content = (
            "⌛ Platform: Raspberry Pi 5\n"
            "⌨️ Language: Python 3 (Tkinter GUI)\n"
            "[◉°] Cameras: Raspberry Pi Camera Module\n"
            "⚜️ Features:\n"
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
        tip_label.pack(pady=(20, 10))
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
                           bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg,
                           relief="raised", bd=2, width=10, command=shutdown_yes)
        yes_btn.pack(side=tk.LEFT, padx=10)
        no_btn = tk.Button(buttons_frame, text="No", font=("Times New Roman", 12, "bold"),
                          bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg,
                          relief="raised", bd=2, width=10, command=shutdown_no)
        no_btn.pack(side=tk.LEFT, padx=10)
        confirm_win.bind("<Return>", lambda event: shutdown_yes())

    def start_detection(self):
        if self.running:
            return
        try:
            self.picam2 = Picamera2(0)
            self.picam2.configure(self.picam2.create_preview_configuration(main={"format": "RGB888"}))
            self.picam2.start()
            self.running = True
            self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
            self.detection_thread.start()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot initialize PiCamera2: {e}")
            self.picam2 = None

    def stop_detection(self):
        self.running = False
        if self.detection_thread is not None:
            self.detection_thread.join(timeout=2)
        if self.picam2 is not None:
            self.picam2.stop()
            self.picam2.close()
            self.picam2 = None
        #self.ocr_queue.put(None)

    def detection_loop(self):
        while self.running:
            if not self.picam2:
                print("No camera available in detection loop")
                break
            frame = self.picam2.capture_array()
            if frame is None:
                print("Failed to capture frame")
                time.sleep(0.1)
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convert to BGR for OpenCV
            if USE_FIXED_ROI:
                roi = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]
            else:
                detections = self.dummy_yolo_detector(frame)
                if not detections:
                    time.sleep(0.1)
                    continue
                det = detections[0]
                if det['label'] != 'number' or det['conf'] <= 0.5:
                    time.sleep(0.1)
                    continue
                x1, y1, x2, y2 = det['bbox']
                x1_exp = max(0, x1 - PADDING_X)
                y1_exp = max(0, y1 - PADDING_Y)
                x2_exp = min(frame.shape[1], x2 + PADDING_X)
                y2_exp = min(frame.shape[0], y2 + PADDING_Y)
                roi = frame[y1_exp:y2_exp, x1_exp:x2_exp]
            try:
                self.ocr_queue.put_nowait(self.preprocess_for_ocr(roi))
            except queue.Full:
                print("OCR queue full, clearing old frames")
                while not self.ocr_queue.empty():
                    try:
                        self.ocr_queue.get_nowait()
                    except queue.Empty:
                        break
                self.ocr_queue.put(self.preprocess_for_ocr(roi))
            time.sleep(0.3)  # Increased to reduce frame rate

    def ocr_loop(self):
        while True:
            try:
                roi = self.ocr_queue.get(timeout=1.0)
                if roi is None:
                    print("OCR Loop: Received None, exiting")
                    break
                print(f"OCR Loop: Processing ROI of shape {roi.shape}")
                # Save ROI for debugging (every 100th frame)
                if self.roi_save_counter % 100 == 0:
                    cv2.imwrite(f"roi_{self.roi_save_counter}.png", roi)
                    print(f"Saved ROI as roi_{self.roi_save_counter}.png")
                self.roi_save_counter += 1
                results = self.reader.readtext(roi, allowlist='0123456789')
                detected_text = "".join([char for res in results for char in res[1] if char.isdigit()])
                print(f"OCR Loop: Detected text = {detected_text}")
                self.detected_number = detected_text if detected_text else "0"
                if detected_text:
                    self.recent_detections.append(detected_text)
                    print(f"OCR Loop: Recent detections = {list(self.recent_detections)}")
                    if len(self.recent_detections) >= DEBOUNCE_COUNT:
                        most_common = Counter(self.recent_detections).most_common(1)[0]
                        if most_common[1] >= DEBOUNCE_COUNT:
                            with self.number_lock:
                                self.confirmed_number = most_common[0]
                            print(f"✅ Confirmed Number: {self.confirmed_number}")
                else:
                    self.recent_detections.clear()
                    with self.number_lock:
                        self.confirmed_number = "0"
                    # Clear queue to prioritize new frames
                    while not self.ocr_queue.empty():
                        try:
                            self.ocr_queue.get_nowait()
                            print("OCR Loop: Cleared queue to prioritize new frames")
                        except queue.Empty:
                            break
                    print("OCR Loop: Cleared recent detections, confirmed_number = 0")
                print(f"OCR Loop: Queue size = {self.ocr_queue.qsize()}")
            except queue.Empty:
                print("OCR Loop: Queue empty, waiting...")
                continue
            except Exception as e:
                print(f"OCR Loop: Error processing ROI: {e}")
                continue

    def dummy_yolo_detector(self, frame):
        height, width = frame.shape[:2]
        box_w, box_h = width // 3, height // 3
        x1 = width // 2 - box_w // 2
        y1 = height // 2 - box_h // 2
        x2 = x1 + box_w
        y2 = y1 + box_h
        return [{'bbox': (x1, y1, x2, y2), 'conf': 0.9, 'label': 'number'}]

    def preprocess_for_ocr(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blur)
        _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def live_camera(self):
        if not self.picam2 or not self.running:
            self.start_detection()
            if not self.picam2 or not self.running:
                tk.messagebox.showerror("Error", "Cannot initialize PiCamera2")
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
            dome_frame = self.picam2.capture_array()
            if dome_frame is not None:
                dome_frame = cv2.cvtColor(dome_frame, cv2.COLOR_RGB2BGR)
                dome_resized = cv2.resize(dome_frame, (640, 250))
                dome_rgb = cv2.cvtColor(dome_resized, cv2.COLOR_BGR2RGB)
                dome_img = Image.fromarray(dome_rgb)
                dome_imgtk = ImageTk.PhotoImage(image=dome_img)
                self.dome_img_label.imgtk = dome_imgtk
                self.dome_img_label.config(image=dome_imgtk)
            frame = self.picam2.capture_array()
            if frame is not None:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
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
                        results = self.reader.readtext(thresh, allowlist='0123456789')
                        detected_text = "".join([c for res in results for c in res[1] if c.isdigit()])
                        if detected_text:
                            self.recent_detections.append(detected_text)
                            if len(self.recent_detections) == DEBOUNCE_COUNT:
                                if all(text == self.recent_detections[0] for text in self.recent_detections):
                                    with self.number_lock:
                                        self.confirmed_number = detected_text
                                    print(f"✅ Confirmed Number: {self.confirmed_number}")
                        else:
                            self.recent_detections.clear()
                        cv2.rectangle(frame_resized, (x1_exp, y1_exp), (x2_exp, y2_exp), (0, 255, 0), 2)
                        cv2.putText(frame_resized, detected_text, (x1_exp, y1_exp - 10),
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

    def start_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("Connected to MQTT broker")
                client.subscribe(MQTT_TOPIC_COUNTER)
                client.subscribe(MQTT_TOPIC_BARCODE)
            else:
                print(f"MQTT connection failed with code {rc}")

        def on_message(client, userdata, msg):
            try:
                message = msg.payload.decode()
                print(f"Received MQTT message on topic {msg.topic}: {message}")
                if msg.topic == MQTT_TOPIC_COUNTER:
                    if message.startswith("Object Count:"):
                        count = int(message.split(":")[1].strip())
                        self.dome_count.set(count)
                    else:
                        print(f"Unknown MQTT message format: {message}")
                elif msg.topic == MQTT_TOPIC_BARCODE:
                    message_map = {
                        "Barcode Detected": "barcode_detected",
                        "Blocked Barcode Detected": "barcode_blocked",
                        "Multiple Barcodes Detected": "multiple_barcodes",
                        "Camera Blocked": "camera_blocked"
                    }
                    text_key = message_map.get(message)
                    if not text_key:
                        print(f"Invalid barcode message: {message}")
                        return
                    if not (hasattr(self, 'flash_event') and self.flash_screen and self.flash_screen.winfo_exists()):
                        print(f"Skipping flash_event for '{message}': flash_screen not available or does not exist")
                        return
                    current_time = time.time()
                    with self.flash_lock:
                        # Check if a flash is in progress
                        if current_time - self.last_flash_time < self.flash_cooldown:
                            if self.current_flash_key == "multiple_barcodes" and text_key != "multiple_barcodes":
                                print(f"Ignoring {text_key} due to active multiple_barcodes flash")
                                return
                            elif text_key == "multiple_barcodes" and self.current_flash_key:
                                print(f"Prioritizing multiple_barcodes, canceling {self.current_flash_key}")
                                if self.current_animation:
                                    self.flash_screen.after_cancel(self.current_animation)
                                    self.current_animation = None
                                    self.flash_screen.withdraw()
                            elif text_key == "barcode_blocked" and self.current_flash_key:
                                print(f"Prioritizing barcode_blocked, canceling {self.current_flash_key}")
                                if self.current_animation:
                                    self.flash_screen.after_cancel(self.current_animation)
                                    self.current_animation = None
                                    self.flash_screen.withdraw()
                            else:
                                print(f"Ignoring {text_key} due to active flash: {self.current_flash_key}")
                                return
                        self.current_flash_key = text_key
                        self.last_flash_time = current_time
                    print(f"Triggering flash_event for {text_key}")
                    self.flash_event(text_key)
            except ValueError as e:
                print(f"Invalid MQTT message received: {message}, error: {e}")
            except Exception as e:
                print(f"Error processing MQTT message: {e}")

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message

        try:
            self.mqtt_client.connect(self.mqtt_broker, MQTT_PORT)
            self.mqtt_thread = threading.Thread(target=self.mqtt_client.loop_forever)
            self.mqtt_thread.daemon = True
            self.mqtt_thread.start()
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            messagebox.showerror("MQTT Error", f"Failed to connect to MQTT broker: {e}")

    def stop_mqtt(self):
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_client = None
            self.mqtt_thread = None
            print("MQTT client stopped")

    def start(self):
        self.start_mqtt()
        live_counts_win = tk.Toplevel(self)
        live_counts_win.title("Live Counts")
        live_counts_win.geometry(f"{live_counts_win.winfo_screenwidth()}x{live_counts_win.winfo_screenheight()}")
        live_counts_win.configure(bg="#e8f5e9")
        dome_count = tk.IntVar(value=random.randint(0, 20))
        ribbon_count = tk.IntVar(value=0)
        def update_counts():
            if not live_counts_win.winfo_exists():
                return
            dome_count.set(random.randint(0, 20))
            with self.number_lock:
                confirmed_number = self.confirmed_number
            print(f"Update Counts: Attempting to set ribbon_count to {confirmed_number}")
            try:
                ribbon_count.set(int(confirmed_number))
                print(f"Update Counts: Successfully set ribbon_count to {confirmed_number}")
            except ValueError as e:
                print(f"Progress: Update Counts: ValueError setting ribbon_count, confirmed_number={confirmed_number}, error={e}")
                ribbon_count.set(0)
            live_counts_win.after(500, update_counts)

        def after_count_init():
            if not live_counts_win.winfo_exists():
                print("after_count_init: live_counts_win does not exist, aborting")
                return
            self.flash_screen = tk.Toplevel(self)
            self.flash_screen.withdraw()
            self.flash_screen.configure(bg="white")
            self.flash_screen.attributes("-topmost", True)
            self.flash_screen.geometry(f"{self.flash_screen.winfo_screenwidth()}x{self.flash_screen.winfo_screenheight()}")
            self.flash_screen.overrideredirect(True)

            flash_image_label = tk.Label(self.flash_screen, bg="white")
            flash_image_label.pack(pady=(100, 20))

            flash_label = tk.Label(self.flash_screen, bg="white")
            flash_label.pack()

            gif_paths = {
                "barcode_detected": "/home/pi/hailo-rpi5-examples/images/BarcodeDetected.gif",
                "barcode_blocked": "/home/pi/hailo-rpi5-examples/images/BarcodeBlocked.gif",
                "multiple_barcodes": "/home/pi/hailo-rpi5-examples/images/MultipleBarcode.gif",
                "camera_blocked": "/home/pi/hailo-rpi5-examples/images/CameraBlocked.gif"
            }
            target_width, target_height = 450, 500
            frame_skip = 8
            gif_frames = {key: [] for key in gif_paths}

            def load_frames(img, new_size, key):
                try:
                    frames = []
                    for i, frame in enumerate(ImageSequence.Iterator(img)):
                        if i % frame_skip != 0:
                            continue
                        frame = frame.convert("RGB").resize(new_size, Image.Resampling.LANCZOS)
                        with BytesIO() as buffer:
                            frame.save(buffer, format="GIF")
                            buffer.seek(0)
                            photo_frame = tk.PhotoImage(data=buffer.read())
                            frames.append(photo_frame)
                    gif_frames[key] = frames
                    print(f"Loaded {key}: {len(gif_frames[key])} frames")
                    if not gif_frames[key]:
                        print(f"Error: No frames loaded for {key}")
                        flash_image_label.config(text=f"No frames in {key}", fg="red")
                except Exception as e:
                    print(f"Error loading frames for {key}: {e}")
                    flash_image_label.config(text=f"Failed to load {key}", fg="red")

            def load_all_gifs():
                for key, path in gif_paths.items():
                    try:
                        img = Image.open(path)
                        print(f"Loaded {path}: format={img.format}, frames={getattr(img, 'n_frames', '?')}, size={img.size}")
                        aspect_ratio = min(target_width / img.width, target_height / img.height)
                        new_size = (int(img.width * aspect_ratio), int(img.height * aspect_ratio))
                        print(f"Resizing {key} frames to: {new_size}")
                        load_frames(img, new_size, key)
                    except Exception as e:
                        print(f"Error loading GIF {key}: {e}")
                        flash_image_label.config(text=f"Failed to load {key}", fg="red")

            threading.Thread(target=load_all_gifs, daemon=True).start()

            test_btn = tk.Button(live_counts_win, text="Test Flash", font=("Times New Roman", 14),
                                 command=lambda: self.flash_event("barcode_blocked"),  # Changed to test barcode_blocked
                                 bg="#e8f5e9", activebackground="#c8e6c9")
            test_btn.pack(side=tk.BOTTOM, pady=10)

            def animate_gif(label, frames):
                count = [0]
                def update_frame():
                    if not label.winfo_exists() or not frames:
                        return
                    try:
                        label.config(image=frames[count[0]])
                        label.image = frames[count[0]]
                        count[0] = (count[0] + 1) % len(frames)
                        self.current_animation = label.after(50, update_frame)
                    except Exception as e:
                        print(f"Animation error: {e}")
                        label.config(text="Animation error", fg="red")
                update_frame()

            def flash_green_tick(text_key, frames):
                if not frames:
                    print(f"No frames available for {text_key}")
                    return
                with self.flash_lock:
                    print(f"Starting flash_green_tick for {text_key}")
                    self.flash_screen.configure(bg="#00ff00")
                    # Update text to include checkmark and "Barcode Detected" for barcode_detected
                    display_text = "✓ Barcode Detected" if text_key == "barcode_detected" else self.tr(text_key)
                    flash_label.config(text=display_text,
                                       font=("Times New Roman", 48, "bold"),
                                       fg="white", bg="#00ff00")
                    flash_image_label.config(bg="#00ff00")
                    self.current_animation = None  # Reset animation
                    animate_gif(flash_image_label, frames)
                    self.flash_screen.deiconify()
                    self.flash_screen.after(3000, lambda: [
                        self.flash_screen.withdraw(),
                        live_counts_win.lift(),
                        live_counts_win.focus_force(),
                        flash_image_label.after_cancel(self.current_animation) if self.current_animation else None,
                        setattr(self, 'current_animation', None),
                        setattr(self, 'current_flash_key', None)
                    ])

            def flash_red_screen(text_key, frames):
                if not frames:
                    print(f"No frames available for {text_key}")
                    return
                with self.flash_lock:
                    print(f"Starting flash_red_screen for {text_key}")
                    self.flash_screen.configure(bg="#ff0000")
                    if text_key == "barcode_blocked":
                        display_text = "✗ Barcode Blocked"
                        log_description = "Suspicious Activity: Barcode Blocked"
                    elif text_key == "multiple_barcodes":
                        display_text = "✗ Multiple Barcodes"
                        log_description = "Suspicious Activity: Multiple Barcodes"
                    elif text_key == "camera_blocked":
                        display_text = "✗ Camera Blocked"
                        log_description = "Suspicious Activity: Camera Blocked"
                    else:
                        display_text = self.tr(text_key)
                        log_description = self.tr(text_key)
                    flash_label.config(text=display_text,
                                       font=("Times New Roman", 48, "bold"),
                                       fg="white", bg="#ff0000")
                    flash_image_label.config(bg="#ff0000")
                    self.current_animation = None
                    animate_gif(flash_image_label, frames)
                    self.flash_screen.deiconify()
                    # Log the suspicious activity to the database
                    try:
                        conn = mariadb.connect(**DB_CONFIG)
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO activity_log (timestamp, description, image_path) VALUES (NOW(), ?, NULL)",
                            (log_description,)
                        )
                        conn.commit()
                        conn.close()
                        print(f"Logged to activity_log: {log_description}")
                    except mariadb.Error as err:
                        print(f"Error logging to activity_log: {err}")
                    self.flash_screen.after(3000, lambda: [
                        self.flash_screen.withdraw(),
                        live_counts_win.lift(),
                        live_counts_win.focus_force(),
                        flash_image_label.after_cancel(self.current_animation) if self.current_animation else None,
                        setattr(self, 'current_animation', None),
                        setattr(self, 'current_flash_key', None)
                    ])

            def flash_event(text_key):
                if not live_counts_win.winfo_exists() or not self.flash_screen.winfo_exists():
                    print("flash_event: Window does not exist, aborting")
                    return
                print(f"flash_event: Triggering {text_key}")
                frames = gif_frames.get(text_key, [])
                if text_key == "barcode_detected":
                    flash_green_tick(text_key, frames)
                elif text_key in ["barcode_blocked", "multiple_barcodes", "camera_blocked"]:
                    flash_red_screen(text_key, frames)
                else:
                    print(f"Unknown text_key: {text_key}")

            self.flash_event = flash_event
            self.tr = lambda x: x  # Mock translation function

            def on_live_counts_close():
                if self.flash_screen and self.flash_screen.winfo_exists():
                    self.flash_screen.destroy()
                live_counts_win.destroy()
                self.stop_mqtt()

            live_counts_win.protocol("WM_DELETE_WINDOW", on_live_counts_close)

        self.after(1000, after_count_init)

        container = tk.Frame(live_counts_win, bg="#e8f5e9")
        container.pack(expand=True, fill=tk.BOTH, pady=150, padx=100)

        dome_frame = tk.Frame(container, bg="#e8f5e9")
        dome_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=50)

        tk.Label(dome_frame, text=self.tr("object_count"), font=("Times New Roman", 24), bg="#e8f5e9").pack(pady=(0, 10))
        tk.Label(dome_frame, textvariable=self.dome_count, font=("Times New Roman", 72, "bold"), fg="#007c30", bg="#e8f5e9").pack()

        ribbon_frame = tk.Frame(container, bg="#e8f5e9")
        ribbon_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=50)

        tk.Label(ribbon_frame, text=self.tr("number_count"), font=("Times New Roman", 24), bg="#e8f5e9").pack(pady=(0, 10))
        tk.Label(ribbon_frame, textvariable=ribbon_count, font=("Times New Roman", 72, "bold"), fg="#007c30", bg="#e8f5e9").pack()

        def exit_fullscreen():
            def check_password():
                if password_entry.get() == HARDCODED_PASSWORD:
                    prompt_win.destroy()
                    live_counts_win.destroy()
                    if self.flash_screen and self.flash_screen.winfo_exists():
                        self.flash_screen.withdraw()
                        if self.flash_loop_id and self.flash_loop_id["id"]:
                            self.after_cancel(self.flash_loop_id["id"])
                            self.flash_loop_id["id"] = None
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
            title = tk.Label(inner_frame, text=self.tr("Password Required"), font=("Times New Roman", 20, "bold"),
                            bg=self.bg_color, fg=self.fg_color)
            title.pack(pady=(20, 10))
            separator = tk.Frame(inner_frame, height=2, bg=self.fg_color, bd=0, relief='flat')
            separator.pack(fill='x', padx=20, pady=(0, 10))
            password_entry = tk.Entry(inner_frame, show="*", font=("Times New Roman", 14),
                                    bg="white" if self.theme == "light" else "#333333",
                                    fg="black" if self.theme == "light" else "#dddddd",
                                    insertbackground=self.text_fg, relief="solid", bd=1)
            password_entry.pack(pady=10)
            password_entry.focus()
            error_label = tk.Label(inner_frame, text="", fg="red", bg=self.bg_color, font=("Times New Roman", 12))
            error_label.pack()
            buttons_frame = tk.Frame(inner_frame, bg=self.bg_color)
            buttons_frame.pack(pady=10)
            tk.Button(buttons_frame, text=self.tr("submit"), font=("Times New Roman", 12, "bold"),
                     bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg, bd=2,
                     command=check_password).pack(side=tk.LEFT, padx=10)
            tk.Button(buttons_frame, text=self.tr("cancel"), font=("Times New Roman", 12, "bold"),
                     bg=self.btn_bg, fg=self.fg_color, activebackground=self.btn_active_bg, bd=2,
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
