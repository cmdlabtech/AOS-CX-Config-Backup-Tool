import requests
import csv
import os
import stat
import time
from datetime import datetime
import schedule
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import json
import logging
import threading
import sys
from infi.systray import SysTrayIcon
import urllib3
from github import Github
from cryptography.fernet import Fernet
import boto3
from botocore.exceptions import ClientError

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SwitchBackup:
    VERSION = "3.3"

    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.base_dir_path = os.path.dirname(sys.executable)
        else:
            self.base_dir_path = os.path.dirname(os.path.abspath(__file__))

        if not os.path.exists(self.base_dir_path):
            os.makedirs(self.base_dir_path)

        self.config_file = os.path.join(self.base_dir_path, "backup_config.json")
        self.status_file = os.path.join(self.base_dir_path, "switch_status.json")
        self.log_file = os.path.join(self.base_dir_path, "switch_backup.log")
        self.key_file = os.path.join(self.base_dir_path, "encryption_key.key")
        self.max_backups = 5
        self.schedule_enabled = True
        self.git_repo_url = None
        self.git_token = None
        self.git_enabled = False
        self.last_git_status = "Not attempted"
        self.wasabi_access_key = None
        self.wasabi_secret_key = None
        self.wasabi_bucket = None
        self.wasabi_region = "us-east-1"
        self.wasabi_enabled = False
        self.last_wasabi_status = "Not attempted"
        self.root = None
        self.systray = None
        self.backup_lock = threading.Lock()
        self.total_switches = 0
        self.current_switch = 0
        self.fernet = None
        self.switch_status = None
        self.status_label = None
        self.progress = None

    def _initialize_encryption(self):
        if not os.path.exists(self.key_file):
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions on encryption key (Windows: read/write for owner only)
            try:
                if sys.platform == 'win32':
                    # Windows: Use os.chmod with appropriate flags
                    os.chmod(self.key_file, stat.S_IREAD | stat.S_IWRITE)
                else:
                    # Unix/Mac: 600 permissions
                    os.chmod(self.key_file, 0o600)
                logging.info(f"Set restrictive permissions on {self.key_file}")
            except Exception as e:
                logging.warning(f"Failed to set key file permissions: {str(e)}")
        else:
            with open(self.key_file, 'rb') as f:
                key = f.read()
        return Fernet(key)

    def _encrypt(self, data):
        if not data:
            return ""
        return self.fernet.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data):
        if not encrypted_data:
            return ""
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logging.error(f"Decryption failed: {str(e)}")
            return ""

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = self.base_dir_path
        return os.path.join(base_path, relative_path)

    def setup_logging(self):
        try:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                filename=self.log_file,
                filemode='a'
            )
            logging.info("Logging initialized successfully")
        except Exception as e:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler(sys.stdout)]
            )
            logging.error(f"Failed to set up file logging: {str(e)}")

    def load_config(self):
        default_config = {
            'csv_path': os.path.join(self.base_dir_path, "switches.csv"),
            'schedule_frequency': "daily",
            'schedule_times': ["02:00"],
            'schedule_day': "Monday",
            'schedule_interval': 12,
            'default_username': "",
            'default_password': "",
            'schedule_enabled': True,
            'base_dir': '',
            'timeout': 15,
            'git_repo_url': '',
            'git_token': '',
            'git_enabled': False,
            'wasabi_access_key': '',
            'wasabi_secret_key': '',
            'wasabi_bucket': '',
            'wasabi_region': 'us-east-1',
            'wasabi_enabled': False
        }
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.csv_file = config.get('csv_path', default_config['csv_path'])
                self.schedule_frequency = config.get('schedule_frequency', default_config['schedule_frequency'])
                self.schedule_times = config.get('schedule_times', default_config['schedule_times'])
                self.schedule_day = config.get('schedule_day', default_config['schedule_day'])
                self.schedule_interval = config.get('schedule_interval', default_config['schedule_interval'])
                self.default_username = self._decrypt(config.get('default_username', default_config['default_username']))
                self.default_password = self._decrypt(config.get('default_password', default_config['default_password']))
                self.schedule_enabled = config.get('schedule_enabled', default_config['schedule_enabled'])
                self.base_dir = config.get('base_dir', default_config['base_dir'])
                self.timeout = config.get('timeout', default_config['timeout'])
                self.git_repo_url = config.get('git_repo_url', default_config['git_repo_url'])
                self.git_token = self._decrypt(config.get('git_token', default_config['git_token']))
                self.git_enabled = config.get('git_enabled', default_config['git_enabled'])
                self.wasabi_access_key = self._decrypt(config.get('wasabi_access_key', default_config['wasabi_access_key']))
                self.wasabi_secret_key = self._decrypt(config.get('wasabi_secret_key', default_config['wasabi_secret_key']))
                self.wasabi_bucket = config.get('wasabi_bucket', default_config['wasabi_bucket'])
                self.wasabi_region = config.get('wasabi_region', default_config['wasabi_region'])
                self.wasabi_enabled = config.get('wasabi_enabled', default_config['wasabi_enabled'])
                logging.info(f"Loaded config: git_enabled={self.git_enabled}, wasabi_enabled={self.wasabi_enabled}")
        except FileNotFoundError:
            self.csv_file = default_config['csv_path']
            self.schedule_frequency = default_config['schedule_frequency']
            self.schedule_times = default_config['schedule_times']
            self.schedule_day = default_config['schedule_day']
            self.schedule_interval = default_config['schedule_interval']
            self.default_username = default_config['default_username']
            self.default_password = default_config['default_password']
            self.schedule_enabled = default_config['schedule_enabled']
            self.base_dir = default_config['base_dir']
            self.timeout = default_config['timeout']
            self.git_repo_url = default_config['git_repo_url']
            self.git_token = default_config['git_token']
            self.git_enabled = default_config['git_enabled']
            self.wasabi_access_key = default_config['wasabi_access_key']
            self.wasabi_secret_key = default_config['wasabi_secret_key']
            self.wasabi_bucket = default_config['wasabi_bucket']
            self.wasabi_region = default_config['wasabi_region']
            self.wasabi_enabled = default_config['wasabi_enabled']
            logging.info("Configuration file not found, using default settings")

    def load_status(self):
        try:
            with open(self.status_file, 'r') as f:
                self.switch_status = json.load(f)
        except FileNotFoundError:
            self.switch_status = {}
            logging.info("Switch status file not found, initializing empty status")

    def save_status(self):
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.switch_status, f)
            logging.info("Switch status saved successfully")
        except Exception as e:
            logging.error(f"Failed to save switch status: {str(e)}")

    def save_config(self, switch_name=None, ip=None, config=None):
        if switch_name and ip and config:
            if not self.base_dir:
                logging.error("Backup directory not set.")
                if self.status_label:
                    self.status_label.config(text="Error: Backup directory not set")
                messagebox.showerror("Error", "Backup directory not set.")
                return
            # Sanitize switch_name to prevent directory traversal
            safe_switch_name = "".join(c for c in switch_name if c.isalnum() or c in ('-', '_', '.'))
            if not safe_switch_name:
                logging.error(f"Invalid switch name: {switch_name}")
                return
            switch_dir = os.path.join(self.base_dir, safe_switch_name)
            if not os.path.exists(switch_dir):
                os.makedirs(switch_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize filename components
            safe_ip = "".join(c for c in ip if c.isalnum() or c in ('.', '-'))
            filename = f"{safe_switch_name}_{safe_ip}_{timestamp}.txt"
            filepath = os.path.join(switch_dir, filename)

            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(config)
                # Set appropriate file permissions
                try:
                    if sys.platform == 'win32':
                        os.chmod(filepath, stat.S_IREAD | stat.S_IWRITE)
                    else:
                        os.chmod(filepath, 0o600)
                except Exception as perm_error:
                    logging.warning(f"Failed to set file permissions: {str(perm_error)}")
                self.manage_retention(switch_dir)
                logging.info(f"Saved config for {switch_name} ({ip})")
            except Exception as e:
                logging.error(f"Failed to save config for {switch_name} ({ip}): {str(e)}")
        else:
            config = {
                'csv_path': self.csv_file,
                'schedule_frequency': self.schedule_frequency,
                'schedule_times': self.schedule_times,
                'schedule_day': self.schedule_day,
                'schedule_interval': self.schedule_interval,
                'default_username': self._encrypt(self.default_username),
                'default_password': self._encrypt(self.default_password),
                'schedule_enabled': self.schedule_enabled,
                'base_dir': self.base_dir,
                'timeout': self.timeout,
                'git_repo_url': self.git_repo_url,
                'git_token': self._encrypt(self.git_token),
                'git_enabled': self.git_enabled,
                'wasabi_access_key': self._encrypt(self.wasabi_access_key),
                'wasabi_secret_key': self._encrypt(self.wasabi_secret_key),
                'wasabi_bucket': self.wasabi_bucket,
                'wasabi_region': self.wasabi_region,
                'wasabi_enabled': self.wasabi_enabled
            }
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(config, f)
                logging.info("Saved application configuration")
            except Exception as e:
                logging.error(f"Failed to save application configuration: {str(e)}")

    def scale_window(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        base_width = 800
        base_height = 800
        scale_factor = min(screen_width / 1920, screen_height / 1080)
        new_width = int(base_width * scale_factor)
        new_height = int(base_height * scale_factor)
        self.root.geometry(f"{new_width}x{new_height}")

    def setup_gui(self):
        self.root = ttk.Window(themename="darkly")
        self.root.title(f"AOS-CX Config Backup Tool {self.VERSION}")
        try:
            self.root.iconbitmap(self.resource_path("icon.ico"))  # Updated to use icon.ico
        except tk.TclError:
            logging.warning("Failed to set window icon; proceeding without icon.")
        self.scale_window()
        self.root.resizable(True, True)

        notebook = ttk.Notebook(self.root, bootstyle="dark")
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="Main")

        columns_frame = ttk.Frame(main_frame)
        columns_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_column = ttk.Frame(columns_frame)
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_column = ttk.Frame(columns_frame)
        right_column.pack(side="right", fill="y", padx=(10, 0))

        version_label = ttk.Label(right_column, text=f"Version: {self.VERSION}", bootstyle="light")
        version_label.pack(side="bottom", anchor="se", pady=10)

        csv_frame = ttk.LabelFrame(left_column, text="Switch Inventory")
        csv_frame.pack(fill="x", pady=(0, 10))
        self.path_label = ttk.Label(csv_frame, text=self.csv_file, wraplength=300)
        self.path_label.pack(pady=3, padx=10)
        csv_button = ttk.Button(csv_frame, text="Select CSV", command=self.select_csv)
        csv_button.pack(pady=3, padx=10)

        ttk.Separator(left_column, orient="horizontal").pack(fill="x", pady=5)

        backup_loc_frame = ttk.LabelFrame(left_column, text="Backup Location")
        backup_loc_frame.pack(fill="x", pady=10)
        self.backup_loc_label = ttk.Label(backup_loc_frame, text=self.base_dir if self.base_dir else "Not set", wraplength=300)
        self.backup_loc_label.pack(pady=3, padx=10)
        backup_dir_button = ttk.Button(backup_loc_frame, text="Select Dir", command=self.select_backup_dir)
        backup_dir_button.pack(pady=3, padx=10)

        ttk.Separator(left_column, orient="horizontal").pack(fill="x", pady=5)

        cred_frame = ttk.LabelFrame(left_column, text="REST API Credentials")
        cred_frame.pack(fill="x", pady=10)
        cred_subframe = ttk.Frame(cred_frame)
        cred_subframe.pack(expand=True, padx=10, pady=10)
        ttk.Label(cred_subframe, text="Username:").pack(side="left", padx=3)
        self.username_entry = ttk.Entry(cred_subframe, width=15)
        self.username_entry.insert(0, self.default_username)
        self.username_entry.pack(side="left", pady=3)
        ttk.Label(cred_subframe, text="Password:").pack(side="left", padx=3)
        self.password_entry = ttk.Entry(cred_subframe, show="*", width=15)
        self.password_entry.insert(0, self.default_password)
        self.password_entry.pack(side="left", pady=3)
        cred_save_button = ttk.Button(cred_subframe, text="Save", command=self.save_credentials)
        cred_save_button.pack(pady=3)

        ttk.Separator(left_column, orient="horizontal").pack(fill="x", pady=5)

        sched_frame = ttk.LabelFrame(left_column, text="Schedule")
        sched_frame.pack(fill="x", pady=10)
        freq_frame = ttk.Frame(sched_frame)
        freq_frame.pack(fill="x", pady=3, padx=10)
        self.freq_var = tk.StringVar(value=self.schedule_frequency)
        ttk.Radiobutton(freq_frame, text="Daily", value="daily", variable=self.freq_var, command=self.update_schedule_details).pack(side="left", padx=2, expand=True)
        ttk.Radiobutton(freq_frame, text="Weekly", value="weekly", variable=self.freq_var, command=self.update_schedule_details).pack(side="left", padx=2, expand=True)
        ttk.Radiobutton(freq_frame, text="Custom", value="custom", variable=self.freq_var, command=self.update_schedule_details).pack(side="left", padx=2, expand=True)
        self.sched_details_frame = ttk.Frame(sched_frame)
        self.sched_details_frame.pack(fill="x", pady=3, padx=10)
        self.update_schedule_details()
        self.schedule_toggle_var = tk.BooleanVar(value=self.schedule_enabled)
        sched_toggle = ttk.Checkbutton(sched_frame, text="Enable", variable=self.schedule_toggle_var, command=self.toggle_schedule)
        sched_toggle.pack(pady=3, padx=10)

        ttk.Separator(left_column, orient="horizontal").pack(fill="x", pady=5)

        control_frame = ttk.LabelFrame(left_column, text="Manual Backup")
        control_frame.pack(fill="x", pady=10)
        run_backup_button = ttk.Button(control_frame, text="Run Now", command=self.manual_backup)
        run_backup_button.pack(pady=3, padx=10)
        self.status_label = ttk.Label(control_frame, text="Status: Idle")
        self.status_label.pack(pady=3, padx=10)
        self.progress = ttk.Progressbar(control_frame, length=200, mode="determinate", bootstyle="success")
        self.progress.pack(pady=3, padx=10)

        git_frame = ttk.LabelFrame(right_column, text="Git Repository")
        git_frame.pack(fill="x", pady=(0, 10))
        self.git_enabled_var = tk.BooleanVar(value=self.git_enabled)
        git_toggle = ttk.Checkbutton(git_frame, text="Enable", variable=self.git_enabled_var, command=self.toggle_git)
        git_toggle.pack(pady=3, padx=10)
        ttk.Label(git_frame, text="Repo URL:").pack(pady=1, padx=10)
        self.git_repo_entry = ttk.Entry(git_frame, width=20)
        self.git_repo_entry.insert(0, self.git_repo_url)
        self.git_repo_entry.pack(pady=1, padx=10)
        ttk.Label(git_frame, text="Token:").pack(pady=1, padx=10)
        self.git_token_entry = ttk.Entry(git_frame, show="*", width=20)
        self.git_token_entry.insert(0, self.git_token)
        self.git_token_entry.pack(pady=1, padx=10)
        git_save_button = ttk.Button(git_frame, text="Save", command=self.save_git_settings)
        git_save_button.pack(pady=3, padx=10)

        ttk.Separator(right_column, orient="horizontal").pack(fill="x", pady=5)

        wasabi_frame = ttk.LabelFrame(right_column, text="Wasabi Storage")
        wasabi_frame.pack(fill="x", pady=(0, 10))
        self.wasabi_enabled_var = tk.BooleanVar(value=self.wasabi_enabled)
        wasabi_toggle = ttk.Checkbutton(wasabi_frame, text="Enable", variable=self.wasabi_enabled_var, command=self.toggle_wasabi)
        wasabi_toggle.pack(pady=3, padx=10)
        ttk.Label(wasabi_frame, text="Access Key:").pack(pady=1, padx=10)
        self.wasabi_access_key_entry = ttk.Entry(wasabi_frame, width=20)
        self.wasabi_access_key_entry.insert(0, self.wasabi_access_key)
        self.wasabi_access_key_entry.pack(pady=1, padx=10)
        ttk.Label(wasabi_frame, text="Secret Key:").pack(pady=1, padx=10)
        self.wasabi_secret_key_entry = ttk.Entry(wasabi_frame, show="*", width=20)
        self.wasabi_secret_key_entry.insert(0, self.wasabi_secret_key)
        self.wasabi_secret_key_entry.pack(pady=1, padx=10)
        ttk.Label(wasabi_frame, text="Bucket:").pack(pady=1, padx=10)
        self.wasabi_bucket_entry = ttk.Entry(wasabi_frame, width=20)
        self.wasabi_bucket_entry.insert(0, self.wasabi_bucket)
        self.wasabi_bucket_entry.pack(pady=1, padx=10)
        ttk.Label(wasabi_frame, text="Region:").pack(pady=1, padx=10)
        self.wasabi_region_entry = ttk.Entry(wasabi_frame, width=20)
        self.wasabi_region_entry.insert(0, self.wasabi_region)
        self.wasabi_region_entry.pack(pady=1, padx=10)
        wasabi_save_button = ttk.Button(wasabi_frame, text="Save", command=self.save_wasabi_settings)
        wasabi_save_button.pack(pady=3, padx=10)

        status_frame = ttk.Frame(notebook)
        notebook.add(status_frame, text="Status")
        self.status_tree = ttk.Treeview(status_frame, columns=("Name", "IP", "Last Backup", "Status", "Git Status", "Wasabi Status"), show="headings")
        self.status_tree.heading("Name", text="Switch")
        self.status_tree.heading("IP", text="IP")
        self.status_tree.heading("Last Backup", text="Last Backup")
        self.status_tree.heading("Status", text="Status")
        self.status_tree.heading("Git Status", text="Git Status")
        self.status_tree.heading("Wasabi Status", text="Wasabi Status")
        self.status_tree.column("Name", width=80, anchor="center")
        self.status_tree.column("IP", width=80, anchor="center")
        self.status_tree.column("Last Backup", width=100, anchor="center")
        self.status_tree.column("Status", width=60, anchor="center")
        self.status_tree.column("Git Status", width=100, anchor="center")
        self.status_tree.column("Wasabi Status", width=100, anchor="center")
        self.status_tree.pack(fill="both", expand=True)
        self.status_tree.tag_configure("oddrow", background="#2a2a2a")
        self.status_tree.tag_configure("evenrow", background="#1e1e1e")
        refresh_button = ttk.Button(status_frame, text="Refresh", command=self.refresh_status)
        refresh_button.pack(pady=5)
        self.refresh_status()

    def update_schedule_details(self):
        for widget in self.sched_details_frame.winfo_children():
            widget.destroy()

        if self.freq_var.get() == "daily":
            times_frame = ttk.Frame(self.sched_details_frame)
            times_frame.pack(expand=True)
            ttk.Label(times_frame, text="Times (HH:MM):").pack(side="left", padx=2)
            self.daily_times_entry = ttk.Entry(times_frame, width=15)
            self.daily_times_entry.insert(0, ", ".join(self.schedule_times))
            self.daily_times_entry.pack(side="left", padx=2)
            ttk.Button(times_frame, text="Set", command=self.update_schedule).pack(side="left", padx=5)
        else:
            details_frame = ttk.Frame(self.sched_details_frame)
            details_frame.pack(expand=True)
            ttk.Label(details_frame, text="Day:").pack(side="left", padx=2)
            if self.freq_var.get() == "weekly":
                self.weekly_day_var = tk.StringVar(value=self.schedule_day)
                ttk.Combobox(details_frame, textvariable=self.weekly_day_var, values=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], width=10).pack(side="left", padx=2)
            else:
                self.custom_day_var = tk.StringVar(value=self.schedule_day)
                ttk.Radiobutton(details_frame, text=self.schedule_day[:3], value=self.schedule_day, variable=self.custom_day_var).pack(side="left", padx=2)
            ttk.Label(details_frame, text="Time:").pack(side="left", padx=2)
            self.hour_var = tk.StringVar(value=self.schedule_times[0].split(':')[0])
            self.minute_var = tk.StringVar(value=self.schedule_times[0].split(':')[1])
            ttk.Combobox(details_frame, textvariable=self.hour_var, values=[f"{h:02d}" for h in range(24)], width=5).pack(side="left", padx=2)
            ttk.Label(details_frame, text=":").pack(side="left")
            ttk.Combobox(details_frame, textvariable=self.minute_var, values=[f"{m:02d}" for m in range(60)], width=5).pack(side="left", padx=2)
            ttk.Button(details_frame, text="Set", command=self.update_schedule).pack(side="left", padx=5)

    def select_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")], title="Select CSV", initialdir=self.base_dir_path)
        if filepath:
            # Validate path to prevent directory traversal
            try:
                real_path = os.path.realpath(filepath)
                if not os.path.exists(real_path):
                    messagebox.showerror("Error", "Selected file does not exist")
                    return
                self.csv_file = real_path
                self.save_config()
                self.path_label.config(text=real_path)
                messagebox.showinfo("Success", "CSV updated")
                logging.info(f"Selected CSV: {real_path}")
            except Exception as e:
                logging.error(f"Error selecting CSV: {str(e)}")
                messagebox.showerror("Error", f"Invalid file path: {str(e)}")

    def select_backup_dir(self):
        directory = filedialog.askdirectory(title="Select Backup Dir", initialdir=self.base_dir_path if not self.base_dir else self.base_dir)
        if directory:
            # Validate and normalize path
            try:
                real_dir = os.path.realpath(directory)
                if not os.path.exists(real_dir):
                    os.makedirs(real_dir)
                self.base_dir = real_dir
                self.save_config()
                self.backup_loc_label.config(text=self.base_dir)
                messagebox.showinfo("Success", "Backup dir updated")
                logging.info(f"Selected backup dir: {self.base_dir}")
            except Exception as e:
                logging.error(f"Error selecting backup dir: {str(e)}")
                messagebox.showerror("Error", f"Invalid directory: {str(e)}")

    def save_credentials(self):
        self.default_username = self.username_entry.get()
        self.default_password = self.password_entry.get()
        self.save_config()
        messagebox.showinfo("Success", "Credentials updated")
        logging.info("Credentials updated")

    def toggle_git(self):
        self.git_enabled = self.git_enabled_var.get()
        self.save_config()
        logging.info(f"Git upload {'enabled' if self.git_enabled else 'disabled'}")

    def save_git_settings(self):
        self.git_repo_url = self.git_repo_entry.get()
        self.git_token = self.git_token_entry.get()
        self.git_enabled = self.git_enabled_var.get()
        self.save_config()
        messagebox.showinfo("Success", "Git settings saved")
        logging.info("Git settings updated")

    def toggle_wasabi(self):
        self.wasabi_enabled = self.wasabi_enabled_var.get()
        self.save_config()
        logging.info(f"Wasabi upload {'enabled' if self.wasabi_enabled else 'disabled'}")

    def save_wasabi_settings(self):
        self.wasabi_access_key = self.wasabi_access_key_entry.get()
        self.wasabi_secret_key = self.wasabi_secret_key_entry.get()
        self.wasabi_bucket = self.wasabi_bucket_entry.get()
        self.wasabi_region = self.wasabi_region_entry.get()
        self.wasabi_enabled = self.wasabi_enabled_var.get()
        self.save_config()
        self.load_config()
        messagebox.showinfo("Success", "Wasabi settings saved")
        logging.info("Wasabi settings updated")

    def setup_schedule(self):
        # Use wrapper function to avoid lambda closure issues
        def run_scheduled_backup():
            try:
                self.backup_switches(is_manual=False)
            except Exception as e:
                logging.error(f"Scheduled backup failed: {str(e)}")
        
        if self.schedule_frequency == "daily":
            for t in self.schedule_times:
                schedule.every().day.at(t).do(run_scheduled_backup)
        elif self.schedule_frequency == "weekly":
            getattr(schedule.every(), self.schedule_day.lower()).at(self.schedule_times[0]).do(run_scheduled_backup)
        else:
            getattr(schedule.every(), self.schedule_day.lower()).at(self.schedule_times[0]).do(run_scheduled_backup)

    def toggle_schedule(self):
        self.schedule_enabled = self.schedule_toggle_var.get()
        schedule.clear()
        if self.schedule_enabled:
            self.setup_schedule()
            logging.info("Schedule enabled")
        else:
            logging.info("Schedule disabled")
        self.save_config()

    def get_switch_config(self, ip, username, password):
        max_retries = 3
        retry_delay = 5
        session = requests.Session()
        config_text = None

        try:
            response = requests.get(f"https://{ip}", timeout=5, verify=False)
            logging.info(f"Connectivity test to {ip}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Connectivity test to {ip} failed: {str(e)}")
            return None

        for attempt in range(max_retries):
            try:
                login_url = f"https://{ip}/rest/v10.04/login"
                login_response = session.post(login_url, data={"username": username, "password": password}, verify=False, timeout=self.timeout)
                login_response.raise_for_status()
                logging.info(f"Login successful for {ip} with API v10.04")

                config_url = f"https://{ip}/rest/v10.04/configs/running-config"
                config_response = session.get(config_url, headers={"Accept": "text/plain"}, verify=False, timeout=self.timeout)
                config_response.raise_for_status()
                config_text = config_response.text
                logging.info(f"Retrieved config from {ip} with API v10.04")
                break
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed for {ip}: {str(e)}. Retrying...")
                    time.sleep(retry_delay)
                else:
                    logging.error(f"Failed to get config from {ip} after {max_retries} attempts: {str(e)}")
                    return None
            finally:
                try:
                    logout_url = f"https://{ip}/rest/v10.04/logout"
                    session.post(logout_url, verify=False, timeout=self.timeout)
                    logging.info(f"Logged out from {ip}")
                except requests.exceptions.RequestException as e:
                    logging.error(f"Failed to logout from {ip}: {str(e)}")
        return config_text

    def manage_retention(self, switch_dir):
        try:
            files = sorted([f for f in os.listdir(switch_dir) if f.endswith('.txt')], reverse=True)
            while len(files) > self.max_backups:
                os.remove(os.path.join(switch_dir, files.pop()))
                logging.info(f"Removed old backup in {switch_dir}")
        except Exception as e:
            logging.error(f"Failed to manage retention for {switch_dir}: {str(e)}")

    def refresh_status(self):
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        for idx, (switch, status) in enumerate(self.switch_status.items()):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.status_tree.insert("", "end", values=(
                status.get("name", switch),
                status.get("ip", ""),
                status.get("last_backup", "Never"),
                status.get("status", "Unknown"),
                status.get("git_status", "Not attempted"),
                status.get("wasabi_status", "Not attempted")
            ), tags=(tag,))

    def git_upload(self, is_manual=False, status_label=None, root=None):
        if not self.git_enabled or not self.git_repo_url or not self.git_token or not self.base_dir:
            self.last_git_status = "Skipped: Git settings incomplete"
            logging.info("Git upload skipped: settings incomplete")
            return
        try:
            g = Github(self.git_token)
            repo = g.get_repo(self.git_repo_url.replace('https://github.com/', '').replace('.git', ''))
            files_to_upload = []
            for switch_dir in [d for d in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, d))]:
                switch_path = os.path.join(self.base_dir, switch_dir)
                files = sorted([f for f in os.listdir(switch_path) if f.endswith('.txt')], reverse=True)
                if files:
                    file_path = os.path.join(switch_path, files[0])
                    relative_path = os.path.relpath(file_path, self.base_dir).replace(os.sep, '/')
                    files_to_upload.append((file_path, relative_path))
            for file_path, relative_path in files_to_upload:
                with open(file_path, 'r') as f:
                    content = f.read()
                try:
                    contents = repo.get_contents(relative_path)
                    repo.update_file(relative_path, f"Update {relative_path}", content, contents.sha)
                except Exception as e:
                    # File doesn't exist, create it
                    if "404" in str(e) or "Not Found" in str(e):
                        repo.create_file(relative_path, f"Add {relative_path}", content)
                    else:
                        raise
            self.last_git_status = "Success"
            logging.info("Git upload successful")
            if is_manual and status_label and root:
                status_label.config(text="Status: Git upload completed")
                root.update()
        except Exception as e:
            self.last_git_status = f"Failed: {str(e)}"
            logging.error(f"Git upload failed: {str(e)}")
            if is_manual and status_label and root:
                status_label.config(text=f"Status: Git upload failed")
                root.update()

    def wasabi_upload(self, is_manual=False, status_label=None, root=None):
        if not self.wasabi_enabled or not self.wasabi_access_key or not self.wasabi_secret_key or not self.wasabi_bucket or not self.base_dir:
            self.last_wasabi_status = "Skipped: Wasabi settings incomplete"
            logging.info("Wasabi upload skipped: settings incomplete")
            return
        try:
            s3_client = boto3.Session().client(
                's3',
                endpoint_url=f"https://s3.{self.wasabi_region}.wasabisys.com",
                aws_access_key_id=self.wasabi_access_key,
                aws_secret_access_key=self.wasabi_secret_key
            )
            files_to_upload = []
            for switch_dir in [d for d in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, d))]:
                switch_path = os.path.join(self.base_dir, switch_dir)
                files = sorted([f for f in os.listdir(switch_path) if f.endswith('.txt')], reverse=True)
                if files:
                    file_path = os.path.join(switch_path, files[0])
                    relative_path = os.path.relpath(file_path, self.base_dir).replace(os.sep, '/')
                    files_to_upload.append((file_path, relative_path))
            for file_path, relative_path in files_to_upload:
                with open(file_path, 'rb') as f:
                    s3_client.upload_fileobj(f, self.wasabi_bucket, relative_path)
            self.last_wasabi_status = "Success"
            logging.info("Wasabi upload successful")
            if is_manual and status_label and root:
                status_label.config(text="Status: Wasabi upload completed")
                root.update()
        except Exception as e:
            self.last_wasabi_status = f"Failed: {str(e)}"
            logging.error(f"Wasabi upload failed: {str(e)}")
            if is_manual and status_label and root:
                status_label.config(text=f"Status: Wasabi upload failed")
                root.update()

    def backup_switches(self, is_manual=False):
        # Try to acquire lock with timeout protection
        if not self.backup_lock.acquire(blocking=False):
            logging.warning("Backup already in progress")
            if self.status_label:
                self.status_label.config(text="Status: Backup in progress")
            if is_manual:
                messagebox.showwarning("Backup In Progress", "A backup is already running. Please wait.")
            return
        try:
            mode = "Manual" if is_manual else "Automatic"
            if self.status_label:
                self.status_label.config(text=f"Status: Running {mode.lower()} backup")
            logging.info(f"Starting {mode.lower()} backup")
            try:
                with open(self.csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    switches = list(reader)
                    self.total_switches = len(switches)
                    self.current_switch = 0
            except FileNotFoundError:
                if self.status_label:
                    self.status_label.config(text="Error: CSV not found")
                logging.error(f"CSV not found: {self.csv_file}")
                return
            self.progress["maximum"] = self.total_switches
            self.progress["value"] = 0
            has_failure = False
            with open(self.csv_file, 'r') as f:
                reader = csv.DictReader(f)
                if not all(col in reader.fieldnames for col in ['name', 'ip']):
                    if self.status_label:
                        self.status_label.config(text="Error: CSV missing columns")
                    logging.error("CSV missing 'name' or 'ip'")
                    return
                for row in reader:
                    self.current_switch += 1
                    self.progress["value"] = self.current_switch
                    if self.status_label:
                        self.status_label.config(text=f"Status: Backing up {row['name']} ({self.current_switch}/{self.total_switches})")
                        self.root.update()
                    logging.info(f"Backing up {row['name']} ({row['ip']})")
                    config = self.get_switch_config(row['ip'], row.get('username', self.default_username), row.get('password', self.default_password))
                    if config:
                        self.save_config(row['name'], row['ip'], config)
                        if not self.base_dir:
                            return
                        self.switch_status[row['name']] = {
                            "name": row['name'], "ip": row['ip'], "last_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "status": "Success", "git_status": self.last_git_status, "wasabi_status": self.last_wasabi_status
                        }
                    else:
                        has_failure = True
                        self.switch_status[row['name']] = {
                            "name": row['name'], "ip": row['ip'], "last_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "status": "Failed", "git_status": "Not attempted", "wasabi_status": "Not attempted"
                        }
                    self.save_status()
                    self.refresh_status()
            if not has_failure:
                self.git_upload(is_manual=is_manual, status_label=self.status_label, root=self.root)
                for switch in self.switch_status:
                    self.switch_status[switch]["git_status"] = self.last_git_status
                self.wasabi_upload(is_manual=is_manual, status_label=self.status_label, root=self.root)
                for switch in self.switch_status:
                    self.switch_status[switch]["wasabi_status"] = self.last_wasabi_status
                self.save_status()
                self.refresh_status()
            if self.status_label:
                self.status_label.config(text=f"Status: {mode} backup {'completed' if not has_failure else 'partially completed'}")
            logging.info(f"{mode} backup completed")
        finally:
            self.backup_lock.release()

    def manual_backup(self):
        self.backup_switches(is_manual=True)

    def update_schedule(self):
        self.schedule_frequency = self.freq_var.get()
        if self.schedule_frequency == "daily":
            times = [t.strip() for t in self.daily_times_entry.get().split(",")]
            for t in times:
                try:
                    hour, minute = map(int, t.split(":"))
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Error", "Invalid time format")
                    return
            self.schedule_times = times
        else:
            day = self.weekly_day_var.get() if self.schedule_frequency == "weekly" else self.custom_day_var.get()
            hour, minute = self.hour_var.get(), self.minute_var.get()
            try:
                if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
                    raise ValueError
                self.schedule_day, self.schedule_times = day, [f"{hour}:{minute}"]
            except ValueError:
                messagebox.showerror("Error", "Invalid time")
                return
        self.save_config()
        schedule.clear()
        if self.schedule_enabled:
            self.setup_schedule()
        messagebox.showinfo("Success", "Schedule updated")
        logging.info(f"Schedule updated: {self.schedule_frequency}")

    def run_schedule(self):
        if self.schedule_enabled:
            self.setup_schedule()
            logging.info(f"Scheduled backups set up")
        while True:
            schedule.run_pending()
            time.sleep(60)

    def initialize(self):
        if self.fernet is None:
            self.fernet = self._initialize_encryption()
        self.setup_logging()
        self.load_config()
        self.load_status()

    def open_gui(self, systray):
        if self.root is None or not tk.Tk.winfo_exists(self.root):
            self.setup_gui()
            self.root.protocol("WM_DELETE_WINDOW", self.close_gui)
            self.root.mainloop()
        else:
            self.root.deiconify()

    def close_gui(self):
        if self.root:
            self.root.withdraw()

    def quit_app(self, systray):
        if self.systray:
            self.systray.shutdown()
        if self.root:
            self.root.destroy()
        sys.exit()

    def run(self):
        self.initialize()
        menu_options = (
            ("Open GUI", None, self.open_gui),
            ("Exit", None, self.quit_app),
        )
        self.systray = SysTrayIcon(
            self.resource_path("icon.ico"),  # Updated to use icon.ico
            f"AOS-CX Config Backup Tool",
            menu_options, default_menu_index=None
        )
        self.systray.start()
        schedule_thread = threading.Thread(target=self.run_schedule, daemon=True)
        schedule_thread.start()
        self.open_gui(self.systray)

if __name__ == "__main__":
    app = SwitchBackup()
    app.run()