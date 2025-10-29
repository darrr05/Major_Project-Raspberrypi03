import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
import os
import itertools
import datetime
import random
import subprocess
import mariadb

from tkinter import ttk


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",  # use your actual password
    "database": "Anti_Theftdb"
}


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

        self.gradient_bg = GradientFrame(self, "#007c30", "#a4d4ae")
        self.gradient_bg.pack(fill="both", expand=True)

        self.border_frame = tk.Frame(self.gradient_bg, bg="white", bd=4, relief="groove")
        self.border_frame.place(relx=0.5, rely=0.01, anchor="n", width=1500, height=940)

        self.create_widgets()
        self.bind("<Escape>", lambda e: self.destroy())

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
                # Update labels and buttons
                    if isinstance(subchild, tk.Label):
                        subchild.config(bg=self.bg_color, fg=self.text_fg)
                    elif isinstance(subchild, tk.Button):
                        subchild.config(bg=self.btn_bg, fg=self.fg_color,
                                        activebackground=self.btn_active_bg)
                    elif isinstance(subchild, tk.Frame):
                    # Recursive update for nested frames
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

        self.settings_btn = tk.Button(self.top_bar, text="⚙", font=("Times New Roman", 20), command=self.open_settings,
                                 bg="white", bd=0, activebackground="lightgray")
        self.settings_btn.pack(side=tk.LEFT, padx=20)
        #self.add_hover_effect(settings_btn, "#d6f5d6", "#007c30")

        shutdown_img = Image.open("/home/pi/hailo-rpi5-examples/images/pb.png")
        shutdown_img = shutdown_img.resize((40, 40))  # Resize as needed, you can adjust the size
        shutdown_img_tk = ImageTk.PhotoImage(shutdown_img)

# Create the button with the image
        self.shutdown_btn = tk.Button(self.top_bar, image=shutdown_img_tk, font=("Times New Roman", 20),
                               command=self.prompt_shutdown_password, fg="black", bg="white", bd=0,
                               activebackground="lightgray")

# Store the reference to the image so it doesn't get garbage collected
        self.shutdown_btn.image = shutdown_img_tk

        self.shutdown_btn.pack(side=tk.RIGHT, padx=(10, 20))
        #self.add_hover_effect(self.shutdown_btn, "#f0f0f0", "black")

        self.logout_btn = tk.Button(self.top_bar, text=self.tr("logout"), font=("Times New Roman", 20),
                               command=self.logout, fg="red", bg="white", bd=0, activebackground="lightgray")
        #self.add_hover_effect(self.logout_btn, "#fddede", "red")
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
            logo_label.config(text="🛒 Giant Supermarket", font=("Times New Roman", 24, "bold"), fg="#007c30")
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
    # Update button texts
        self.about_btn.config(text=self.tr("about_system"))
        self.staff_btn.config(text=self.tr("staff_in_charge"))
        self.live_btn.config(text=self.tr("live_camera_feed"))
        self.activity_btn.config(text=self.tr("activity_log"))
        self.start_btn.config(text=self.tr("start"))

    # Update logout button if it's shown
        self.logout_btn.config(text=f"{self.tr('logout')}" if self.tr("logout") else "⏻ Logout")

    # Update status bar or any other text labels you want
        self.update_status_bar()

    #def add_hover_effect(self, widget, hover_bg, hover_fg=None):
        #original_bg = widget.cget("bg")
        #original_fg = widget.cget("fg")
        #widget.bind("<Enter>", lambda e: widget.config(bg=hover_bg, fg=hover_fg if hover_fg else original_fg))
        #widget.bind("<Leave>", lambda e: widget.config(bg=original_bg, fg=original_fg))
    
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

        prompt_win = tk.Toplevel(self.master)
        prompt_win.grab_set()
        prompt_win.resizable(False, False)
        prompt_win.overrideredirect(True)
        prompt_win.configure(bg=border_color)

    # Set size and center the window
        width, height = 420, 220
        x = (prompt_win.winfo_screenwidth() // 2) - (width // 2)
        y = (prompt_win.winfo_screenheight() // 2) - (height // 2)
        prompt_win.geometry(f"{width}x{height}+{x}+{y}")

    # Outer border frame with color
        border_frame = tk.Frame(prompt_win, bg=border_color)
        border_frame.pack(expand=True, fill="both", padx=4, pady=4)

    # Inner frame with themed background
        inner_frame = tk.Frame(border_frame, bg=self.bg_color)
        inner_frame.pack(expand=True, fill="both")

    # Title label
        title = tk.Label(inner_frame, text=self.tr("shutdown"), font=("Times New Roman", 16, "bold"),
                     bg=self.bg_color, fg=self.fg_color)
        title.pack(pady=(20, 10))

        separator = tk.Frame(inner_frame, height=2, bg=self.fg_color, bd=0, relief='flat')
        separator.pack(fill='x', padx=20, pady=(0, 10))

    # Password entry
        password_entry = tk.Entry(inner_frame, show="*", font=("Times New Roman", 14),
                              bg="white" if self.theme == "light" else "#333333",
                              fg="black" if self.theme == "light" else "#dddddd",
                              insertbackground=self.text_fg,
                              relief="solid", bd=1, width=25)
        password_entry.pack(pady=10)
        password_entry.focus()

    # Error label
        error_label = tk.Label(inner_frame, text="", font=("Times New Roman", 12),
                           fg="red", bg=self.bg_color)
        error_label.pack()

    # Buttons
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

    # Apply theme colors to settings window
        settings_win.config(bg=self.bg_color)
        border_frame = tk.Frame(settings_win, bg=border_color)
        border_frame.pack(expand=True, fill="both")

    # Inner frame with theme background
        inner_frame = tk.Frame(border_frame, bg=self.bg_color)
        inner_frame.pack(expand=True, fill="both", padx=4, pady=4)

        title = tk.Label(inner_frame, text=self.tr("settings"), font=("Times New Roman", 20, "bold"),
                     bg=self.bg_color, fg=self.fg_color)
        title.pack(pady=(20, 10))

        separator = tk.Frame(inner_frame, height=2, bg=self.fg_color, bd=0, relief='flat')
        separator.pack(fill='x', padx=20, pady=(0, 10))
    # Volume control label
        tk.Label(inner_frame, text=self.tr("volume"), font=("Times New Roman", 14),
                bg=self.bg_color, fg=self.fg_color).pack(pady=(20, 10))

        volume_scale = tk.Scale(inner_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                            length=280, font=("Times New Roman", 12),
                            bg=self.bg_color, fg=self.fg_color,
                            highlightthickness=0, troughcolor=self.btn_bg,
                            activebackground=self.btn_active_bg)
        volume_scale.set(self.volume_level)
        volume_scale.pack()

    # Theme selection label
        tk.Label(inner_frame, text=self.tr("theme"), font=("Times New Roman", 14),
                bg=self.bg_color, fg=self.fg_color).pack(pady=(30, 10))

        theme_var = tk.StringVar(value=self.theme)

    # Use frame for radio buttons with bg color
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

        # Language selection
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
        prompt_win = tk.Toplevel(self.master)
        #prompt_win.title("Login Required")
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

    # Labels and Entries
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
        if not self.current_user and not self.login_prompt():
            return
        messagebox.showinfo("Staff", f"Staff in Charge: {self.current_user}")



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

        # Title
        title = tk.Label(inner_frame, text=self.tr("activity_log"), font=("Times New Roman", 20, "bold"),
                        bg=self.bg_color, fg=self.fg_color)
        title.pack(pady=(20, 10))

        separator = tk.Frame(inner_frame, height=2, bg=self.fg_color, bd=0, relief='flat')
        separator.pack(fill='x', padx=20, pady=(0, 10))

        # Treeview styling
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

        # Cancel button
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

        header = tk.Label(inner_frame, text="🛒 About the Supermarket System",
                          font=("Times New Roman", 18, "bold"), bg="#007c30", fg="white", pady=10)
        header.pack(fill=tk.X)
        content = (
            "⌛ Platform: Raspberry Pi 5\n"
            "⌨️ Language: Python 3 (Tkinter GUI)\n"
            "[◉°] Cameras: Dome Camera + Ribbon Camera\n"
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

    def live_camera(self):
        messagebox.showinfo("Live Feed", "Camera feed placeholder.")

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
        confirm_win = tk.Toplevel(self.master)
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


    def start(self):
        live_counts_win = tk.Toplevel(self)
        live_counts_win.title("Live Counts")
        live_counts_win.attributes('-fullscreen', True)
        live_counts_win.configure(bg="#e8f5e9")

        dome_count = tk.IntVar(value=random.randint(0, 20))
        ribbon_count = tk.IntVar(value=random.randint(0, 20))

        def update_counts():
            dome_count.set(random.randint(0, 20))
            ribbon_count.set(random.randint(0, 20))
            live_counts_win.after(2000, update_counts)

        def after_count_init():
            flash_screen = tk.Toplevel(self)
            flash_screen.withdraw()
            flash_screen.attributes('-fullscreen', True)
            flash_screen.configure(bg="white")
            flash_screen.attributes("-topmost", True)

        # Image label above the text label
            flash_image_label = tk.Label(flash_screen, bg="white")
            flash_image_label.pack(pady=(100, 20))  # Add vertical padding for spacing

            flash_label = tk.Label(flash_screen, bg="white")
            flash_label.pack()

            flash_loop_id = {"id": None}

        # Load images and subsample to reduce size
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
                    return  # Stop loop if window is destroyed

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

                    if self.flash_screen and self.flash_screen.winfo_exists():
                        self.flash_screen.withdraw()
                        if self.flash_loop_id:
                            self.flash_screen.after_cancel(self.flash_loop_id)
                            self.flash_loop_id = None
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

        exit_btn = tk.Button(live_counts_win, text="Exit", font=("Times New Roman", 14, "bold"),
                     bg="#e8f5e9", activebackground="#c8e6c9", relief="raised", bd=3,
                     command=exit_fullscreen)
        exit_btn.pack(side=tk.BOTTOM, pady=40)

        live_counts_win.bind("<Escape>", lambda e: exit_fullscreen())

        update_counts()

if __name__ == "__main__":
    app = SupermarketApp()
    app.mainloop()