import requests
import csv
import os
import time
from datetime import datetime
import schedule
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import logging
import threading
import sys
from infi.systray import SysTrayIcon
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from github import Github
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Suppress SSL warnings (optional - not recommended for production)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class SwitchBackup:
    VERSION = "3.0"  # Updated to V3

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

        # Initialize encryption
        self.fernet = self._initialize_encryption()

        self.setup_logging()
        self.load_config()
        self.load_status()
        self.root = None
        self.systray = None
        self.backup_lock = threading.Lock()
        self.total_switches = 0
        self.current_switch = 0

    def _initialize_encryption(self):
        """Initialize Fernet encryption with a key derived from a password."""
        if not os.path.exists(self.key_file):
            # Generate a new key
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
        else:
            # Load existing key
            with open(self.key_file, 'rb') as f:
                key = f.read()
        return Fernet(key)

    def _encrypt(self, data):
        """Encrypt data using Fernet."""
        if not data:
            return ""
        return self.fernet.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data):
        """Decrypt data using Fernet."""
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
                filemode='a'  # Append mode to preserve logs
            )
            logging.info("Logging initialized successfully")
        except Exception as e:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler(sys.stdout)]
            )
            logging.error(f"Failed to set up file logging to {self.log_file}: {str(e)}")

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
            'git_enabled': False
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
                logging.info(f"Loaded config: git_enabled={self.git_enabled}, git_repo_url={self.git_repo_url}, base_dir={self.base_dir}")
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
                logging.error("Backup directory not set. Please set a backup directory first.")
                if self.status_label:
                    self.status_label.config(text="Error: Backup directory not set")
                messagebox.showerror("Error", "Backup directory not set. Please select a backup directory.")
                return
            switch_dir = os.path.join(self.base_dir, switch_name)
            if not os.path.exists(switch_dir):
                os.makedirs(switch_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{switch_name}_{ip}_{timestamp}.txt"
            filepath = os.path.join(switch_dir, filename)

            try:
                with open(filepath, 'w') as f:
                    f.write(config)
                self.manage_retention(switch_dir)
                logging.info(f"Saved config for {switch_name} ({ip}) to {filepath}")
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
                'git_enabled': self.git_enabled
            }
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(config, f)
                logging.info("Saved application configuration")
            except Exception as e:
                logging.error(f"Failed to save application configuration: {str(e)}")

    def setup_gui(self):
        style = ttk.Style()
        style.configure("TButton", padding=6, font=('Helvetica', 10))
        style.configure("TLabel", background="#f0f0f0", font=('Helvetica', 10))

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=20, pady=20)

        main_frame = ttk.Frame(notebook, padding="20")
        notebook.add(main_frame, text="Main")

        # Create a two-column layout
        columns_frame = ttk.Frame(main_frame)
        columns_frame.pack(fill="both", expand=True)

        # Left column for existing sections
        left_column = ttk.Frame(columns_frame)
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Right column for Git section
        right_column = ttk.Frame(columns_frame)
        right_column.pack(side="right", fill="y", padx=(10, 0))

        # Version Label (bottom-right of left column)
        version_label = ttk.Label(right_column, text=f"Version: {self.VERSION}", font=('Helvetica', 10, 'italic'))
        version_label.pack(side="bottom", anchor="se", pady=5)

        # CSV File Section (Left Column)
        csv_frame = ttk.LabelFrame(left_column, text="Switch Inventory", padding="10")
        csv_frame.pack(fill="x", pady=(0, 15))
        
        self.path_label = ttk.Label(csv_frame, text=self.csv_file, wraplength=400)
        self.path_label.pack(pady=5)
        
        ttk.Button(csv_frame, text="Select CSV File", command=self.select_csv).pack()

        # Backup Location Section (Left Column)
        backup_loc_frame = ttk.LabelFrame(left_column, text="Backup Location", padding="10")
        backup_loc_frame.pack(fill="x", pady=15)
        
        self.backup_loc_label = ttk.Label(backup_loc_frame, text=self.base_dir if self.base_dir else "Not set", wraplength=400)
        self.backup_loc_label.pack(pady=5)
        
        ttk.Button(backup_loc_frame, text="Select Backup Directory", command=self.select_backup_dir).pack()

        # Credentials Section (Left Column)
        cred_frame = ttk.LabelFrame(left_column, text="REST API Credentials", padding="10")
        cred_frame.pack(fill="x", pady=15)
        
        cred_subframe = ttk.Frame(cred_frame)
        cred_subframe.pack(expand=True)

        username_frame = ttk.Frame(cred_subframe)
        username_frame.pack(pady=5)
        ttk.Label(username_frame, text="Username:").pack(side="left", padx=5)
        self.username_entry = ttk.Entry(username_frame, width=20)
        self.username_entry.insert(0, self.default_username)
        self.username_entry.pack(side="left", padx=5)

        password_frame = ttk.Frame(cred_subframe)
        password_frame.pack(pady=5)
        ttk.Label(password_frame, text="Password:").pack(side="left", padx=5)
        self.password_entry = ttk.Entry(password_frame, show="*", width=20)
        self.password_entry.insert(0, self.default_password)
        self.password_entry.pack(side="left", padx=5)

        ttk.Button(cred_subframe, text="Save Credentials", command=self.save_credentials).pack(pady=5)

        # Schedule Section (Left Column)
        sched_frame = ttk.LabelFrame(left_column, text="Automatic Backup Schedule", padding="10")
        sched_frame.pack(fill="x", pady=15)
        
        freq_frame = ttk.Frame(sched_frame)
        freq_frame.pack(pady=5)
        freq_inner_frame = ttk.Frame(freq_frame)
        freq_inner_frame.pack(expand=True)
        ttk.Label(freq_inner_frame, text="Frequency:").pack(side="left", padx=5)
        self.freq_var = tk.StringVar(value=self.schedule_frequency)
        ttk.Radiobutton(freq_inner_frame, text="Daily", value="daily", variable=self.freq_var, command=self.update_schedule_details).pack(side="left", padx=5)
        ttk.Radiobutton(freq_inner_frame, text="Weekly", value="weekly", variable=self.freq_var, command=self.update_schedule_details).pack(side="left", padx=5)
        ttk.Radiobutton(freq_inner_frame, text="Custom", value="custom", variable=self.freq_var, command=self.update_schedule_details).pack(side="left", padx=5)

        self.sched_details_frame = ttk.Frame(sched_frame)
        self.sched_details_frame.pack(pady=5)
        self.update_schedule_details()

        sched_toggle_frame = ttk.Frame(sched_frame)
        sched_toggle_frame.pack(pady=5)
        self.schedule_toggle_var = tk.BooleanVar(value=self.schedule_enabled)
        ttk.Checkbutton(sched_toggle_frame, text="Automatic Schedule", 
                       variable=self.schedule_toggle_var, 
                       command=self.toggle_schedule).pack()

        # Manual Backup Section (Left Column)
        control_frame = ttk.LabelFrame(left_column, text="Manual Backup", padding="10")
        control_frame.pack(fill="x", pady=15)
        
        ttk.Button(control_frame, text="Run Backup Now", command=self.manual_backup).pack(pady=5)
        
        self.status_label = ttk.Label(control_frame, text="Status: Idle")
        self.status_label.pack(pady=5)

        self.progress = ttk.Progressbar(control_frame, orient="horizontal", length=200, mode="determinate")
        self.progress.pack(pady=5)

        # Git Repository Section (Right Column)
        git_frame = ttk.LabelFrame(right_column, text="Git Repository", padding="10")
        git_frame.pack(fill="x", pady=(0, 15))

        self.git_enabled_var = tk.BooleanVar(value=self.git_enabled)
        ttk.Checkbutton(git_frame, text="Enable Git Upload", variable=self.git_enabled_var, 
                       command=self.toggle_git).pack(pady=5)

        ttk.Label(git_frame, text="Repo URL:").pack(pady=2)
        self.git_repo_entry = ttk.Entry(git_frame, width=30)
        self.git_repo_entry.insert(0, self.git_repo_url)
        self.git_repo_entry.pack(pady=2)

        ttk.Label(git_frame, text="Token:").pack(pady=2)
        self.git_token_entry = ttk.Entry(git_frame, show="*", width=30)
        self.git_token_entry.insert(0, self.git_token)
        self.git_token_entry.pack(pady=2)

        ttk.Button(git_frame, text="Save Git Settings", command=self.save_git_settings).pack(pady=5)

        # Switch Status Tab
        status_frame = ttk.Frame(notebook, padding="20")
        notebook.add(status_frame, text="Switch Status")

        self.status_tree = ttk.Treeview(status_frame, columns=("Name", "IP", "Last Backup", "Status", "Git Status"), show="headings")
        self.status_tree.heading("Name", text="Switch Name")
        self.status_tree.heading("IP", text="IP Address")
        self.status_tree.heading("Last Backup", text="Last Backup")
        self.status_tree.heading("Status", text="Status")
        self.status_tree.heading("Git Status", text="Git Upload Status")
        # Set column widths to fit content in narrower window
        self.status_tree.column("Name", width=100, anchor="center")
        self.status_tree.column("IP", width=100, anchor="center")
        self.status_tree.column("Last Backup", width=120, anchor="center")
        self.status_tree.column("Status", width=80, anchor="center")
        self.status_tree.column("Git Status", width=120, anchor="center")
        self.status_tree.pack(fill="both", expand=True)

        ttk.Button(status_frame, text="Refresh Status", command=self.refresh_status).pack(pady=5)

        self.refresh_status()

    def update_schedule_details(self):
        for widget in self.sched_details_frame.winfo_children():
            widget.destroy()

        details_row1 = ttk.Frame(self.sched_details_frame)
        details_row1.pack(fill="x", pady=2)
        details_row2 = ttk.Frame(self.sched_details_frame)
        details_row2.pack(fill="x", pady=2)
        set_button_frame = ttk.Frame(self.sched_details_frame)
        set_button_frame.pack(pady=5)

        if self.freq_var.get() == "daily":
            details_inner_row1 = ttk.Frame(details_row1)
            details_inner_row1.pack(expand=True)
            ttk.Label(details_inner_row1, text="Times (HH:MM, comma-separated):").pack(side="left", padx=5)
            self.daily_times_entry = ttk.Entry(details_inner_row1, width=30)
            self.daily_times_entry.insert(0, ", ".join(self.schedule_times))
            self.daily_times_entry.pack(side="left", padx=5)
        else:
            details_inner_row1 = ttk.Frame(details_row1)
            details_inner_row1.pack(expand=True)
            ttk.Label(details_inner_row1, text="Day:").pack(side="left", padx=5)
            if self.freq_var.get() == "weekly":
                self.weekly_day_var = tk.StringVar(value=self.schedule_day)
                ttk.Combobox(details_inner_row1, textvariable=self.weekly_day_var, 
                            values=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], 
                            width=10).pack(side="left", padx=5)
            else:
                self.custom_day_var = tk.StringVar(value=self.schedule_day)
                days_frame = ttk.Frame(details_inner_row1)
                days_frame.pack(side="left", padx=5)
                for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
                    ttk.Radiobutton(days_frame, text=day, value=day, variable=self.custom_day_var).pack(side="left", padx=2)

            details_inner_row2 = ttk.Frame(details_row2)
            details_inner_row2.pack(expand=True)
            ttk.Label(details_inner_row2, text="Time:").pack(side="left", padx=5)
            time_frame = ttk.Frame(details_inner_row2)
            time_frame.pack(side="left", padx=5)
            self.hour_var = tk.StringVar(value=self.schedule_times[0].split(':')[0])
            self.minute_var = tk.StringVar(value=self.schedule_times[0].split(':')[1])
            ttk.Combobox(time_frame, textvariable=self.hour_var, 
                        values=[f"{h:02d}" for h in range(24)], 
                        width=5).pack(side="left", padx=2)
            ttk.Label(time_frame, text=":").pack(side="left")
            ttk.Combobox(time_frame, textvariable=self.minute_var, 
                        values=[f"{m:02d}" for m in range(60)], 
                        width=5).pack(side="left", padx=2)

        ttk.Button(set_button_frame, text="Set", command=self.update_schedule).pack()

    def select_csv(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv")],
            title="Select Switch Inventory CSV",
            initialdir=self.base_dir_path
        )
        if filepath:
            self.csv_file = filepath
            self.save_config()
            self.path_label.config(text=filepath)
            messagebox.showinfo("Success", "CSV file path updated")
            logging.info(f"Selected CSV file: {filepath}")

    def select_backup_dir(self):
        directory = filedialog.askdirectory(
            title="Select Backup Directory",
            initialdir=self.base_dir_path if not self.base_dir else self.base_dir
        )
        if directory:
            self.base_dir = directory
            self.save_config()
            self.backup_loc_label.config(text=self.base_dir)
            messagebox.showinfo("Success", "Backup directory updated")
            logging.info(f"Selected backup directory: {self.base_dir}")

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

    def setup_schedule(self):
        if self.schedule_frequency == "daily":
            for t in self.schedule_times:
                schedule.every().day.at(t).do(lambda: self.backup_switches(is_manual=False))
        elif self.schedule_frequency == "weekly":
            getattr(schedule.every(), self.schedule_day.lower()).at(self.schedule_times[0]).do(lambda: self.backup_switches(is_manual=False))
        else:
            getattr(schedule.every(), self.schedule_day.lower()).at(self.schedule_times[0]).do(lambda: self.backup_switches(is_manual=False))

    def toggle_schedule(self):
        self.schedule_enabled = self.schedule_toggle_var.get()
        schedule.clear()
        if self.schedule_enabled:
            self.setup_schedule()
            logging.info("Automatic schedule enabled")
        else:
            logging.info("Automatic schedule disabled")
        self.save_config()

    def get_switch_config(self, ip, username, password):
        max_retries = 3
        retry_delay = 5
        session = requests.Session()
        config_text = None

        try:
            response = requests.get(f"https://{ip}", timeout=5, verify=False)
            logging.info(f"Connectivity test to {ip}: HTTP status {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Connectivity test to {ip} failed: {str(e)}")
            return None

        for attempt in range(max_retries):
            try:
                login_url = f"https://{ip}/rest/v10.13/login"
                logging.info(f"Attempting login to {ip} (attempt {attempt + 1}/{max_retries})")
                login_response = session.post(
                    login_url,
                    data={"username": username, "password": password},
                    verify=False,
                    timeout=self.timeout
                )
                login_response.raise_for_status()
                logging.info(f"Login successful for {ip}")

                config_url = f"https://{ip}/rest/v10.13/configs/running-config"
                headers = {"Accept": "text/plain"}
                logging.info(f"Fetching running-config from {ip}")
                config_response = session.get(
                    config_url,
                    headers=headers,
                    verify=False,
                    timeout=self.timeout
                )
                config_response.raise_for_status()
                config_text = config_response.text
                logging.info(f"Successfully retrieved config from {ip}")
                break

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed for {ip}: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    if self.status_label:
                        self.status_label.config(text=f"Error: Failed to connect to {ip}: {str(e)}")
                    logging.error(f"Failed to get config from {ip} after {max_retries} attempts: {str(e)}")
                    return None

            finally:
                try:
                    logout_url = f"https://{ip}/rest/v10.13/logout"
                    session.post(logout_url, verify=False, timeout=self.timeout)
                    logging.info(f"Successfully logged out from {ip}")
                except requests.exceptions.RequestException as e:
                    logging.error(f"Failed to logout from {ip}: {str(e)}")

        return config_text

    def manage_retention(self, switch_dir):
        try:
            files = sorted(
                [f for f in os.listdir(switch_dir) if f.endswith('.txt')],
                reverse=True
            )
            while len(files) > self.max_backups:
                oldest_file = os.path.join(switch_dir, files.pop())
                os.remove(oldest_file)
                logging.info(f"Removed old backup: {oldest_file}")
        except Exception as e:
            logging.error(f"Failed to manage retention for {switch_dir}: {str(e)}")

    def refresh_status(self):
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        for switch, status in self.switch_status.items():
            self.status_tree.insert("", "end", values=(
                status.get("name", switch),
                status.get("ip", ""),
                status.get("last_backup", "Never"),
                status.get("status", "Unknown"),
                status.get("git_status", "Not attempted")
            ))

    def git_upload(self, is_manual=False, status_label=None, root=None):
        logging.info("Starting Git upload process")
        logging.info(f"Git settings: enabled={self.git_enabled}, repo_url={self.git_repo_url}, token={'set' if self.git_token else 'not set'}, base_dir={self.base_dir}")

        if not self.git_enabled:
            self.last_git_status = "Skipped: Git upload not enabled"
            logging.info("Git upload skipped: not enabled")
            return
        if not self.git_repo_url:
            self.last_git_status = "Skipped: Git repository URL not set"
            logging.info("Git upload skipped: repository URL not set")
            return
        if not self.git_token:
            self.last_git_status = "Skipped: Git token not set"
            logging.info("Git upload skipped: token not set")
            return
        if not self.base_dir:
            self.last_git_status = "Failed: Backup directory not set"
            logging.error("Backup directory not set. Cannot perform Git upload.")
            return

        try:
            logging.info("Initializing GitHub client")
            g = Github(self.git_token)
            repo_name = self.git_repo_url.replace('https://github.com/', '').replace('.git', '')
            logging.info(f"Accessing repository: {repo_name}")
            repo = g.get_repo(repo_name)

            # Collect the most recent file for each switch
            files_to_upload = []
            switch_dirs = [d for d in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, d))]
            
            for switch_dir in switch_dirs:
                switch_path = os.path.join(self.base_dir, switch_dir)
                # Get all .txt files in the switch directory
                files = [f for f in os.listdir(switch_path) if f.endswith('.txt')]
                if not files:
                    continue
                # Sort files by timestamp (newest first)
                files.sort(key=lambda x: x.split('_')[-1].replace('.txt', ''), reverse=True)
                # Take the most recent file
                most_recent_file = files[0]
                file_path = os.path.join(switch_path, most_recent_file)
                relative_path = os.path.relpath(file_path, self.base_dir).replace(os.sep, '/')
                files_to_upload.append((file_path, relative_path))
            logging.info(f"Found {len(files_to_upload)} most recent files to upload")

            # Update status label with total files to upload
            if is_manual and status_label and root:
                status_label.config(text=f"Status: Uploading {len(files_to_upload)} files to GitHub...")
                root.update()

            for idx, (file_path, relative_path) in enumerate(files_to_upload, 1):
                # Update status label for each file
                if is_manual and status_label and root:
                    status_label.config(text=f"Status: Uploading file {idx}/{len(files_to_upload)} to GitHub: {relative_path}")
                    root.update()
                logging.info(f"Uploading file to GitHub path: {relative_path}")
                with open(file_path, 'r') as f:
                    content = f.read()
                # Check if file exists in repo
                try:
                    contents = repo.get_contents(relative_path)
                    # Update file
                    repo.update_file(
                        relative_path,
                        f"Update {relative_path} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        content,
                        contents.sha
                    )
                    logging.info(f"Updated file in repo: {relative_path}")
                except Exception as e:
                    if "404" in str(e):
                        # Create file
                        repo.create_file(
                            relative_path,
                            f"Add {relative_path} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            content
                        )
                        logging.info(f"Created file in repo: {relative_path}")
                    else:
                        raise e
            self.last_git_status = "Success"
            logging.info("Successfully uploaded configs to GitHub repo")
            if is_manual and status_label and root:
                status_label.config(text="Status: Git upload completed")
                root.update()
        except Exception as e:
            self.last_git_status = f"Failed: {str(e)}"
            logging.error(f"Git upload failed: {str(e)}")
            if is_manual and status_label and root:
                status_label.config(text=f"Status: Git upload failed: {str(e)}")
                root.update()

    def backup_switches(self, is_manual=False):
        if not self.backup_lock.acquire(blocking=False):
            logging.warning("Backup already in progress, skipping this run")
            if self.status_label:
                self.status_label.config(text="Status: Backup already in progress")
            return

        try:
            mode = "Manual" if is_manual else "Automatic"
            if self.status_label:
                self.status_label.config(text=f"Status: Running {mode.lower()} backup...")
            logging.info(f"Starting {mode.lower()} backup process")

            try:
                with open(self.csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    switches = list(reader)
                    self.total_switches = len(switches)
                    self.current_switch = 0
            except FileNotFoundError:
                if self.status_label:
                    self.status_label.config(text="Error: CSV file not found")
                messagebox.showerror("Error", f"CSV file not found: {self.csv_file}")
                logging.error(f"CSV file not found: {self.csv_file}")
                return

            self.progress["maximum"] = self.total_switches
            self.progress["value"] = 0

            has_failure = False

            try:
                with open(self.csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    required_cols = ['name', 'ip']
                    if not all(col in reader.fieldnames for col in required_cols):
                        if self.status_label:
                            self.status_label.config(text="Error: CSV missing required columns")
                        messagebox.showerror("Error", "CSV must contain 'name' and 'ip' columns")
                        logging.error("CSV missing required columns: 'name' and 'ip'")
                        return

                    for row in reader:
                        self.current_switch += 1
                        self.progress["value"] = self.current_switch
                        if self.status_label:
                            self.status_label.config(text=f"Status: Backing up {row['name']} ({self.current_switch}/{self.total_switches})")
                            self.root.update()
                        logging.info(f"Starting backup for {row['name']} ({row['ip']})")
                        username = row.get('username', self.default_username)
                        password = row.get('password', self.default_password)
                        config = self.get_switch_config(
                            row['ip'],
                            username,
                            password
                        )
                        if config:
                            self.save_config(row['name'], row['ip'], config)
                            if not self.base_dir:
                                return
                            self.switch_status[row['name']] = {
                                "name": row['name'],
                                "ip": row['ip'],
                                "last_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "status": "Success",
                                "git_status": self.last_git_status
                            }
                        else:
                            has_failure = True
                            self.switch_status[row['name']] = {
                                "name": row['name'],
                                "ip": row['ip'],
                                "last_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "status": "Failed",
                                "git_status": "Not attempted"
                            }
                        self.save_status()
                        self.refresh_status()
                        logging.info(f"Completed backup for {row['name']} ({row['ip']})")

                if not has_failure:
                    logging.info("No failures detected, proceeding with Git upload")
                    # Pass status_label and root for manual backups
                    self.git_upload(is_manual=is_manual, status_label=self.status_label, root=self.root)
                    # Update git_status for all switches after upload
                    for switch in self.switch_status:
                        self.switch_status[switch]["git_status"] = self.last_git_status
                    self.save_status()
                    self.refresh_status()
                else:
                    logging.info("Backup had failures, skipping Git upload")

                if self.status_label:
                    if has_failure:
                        self.status_label.config(text=f"Status: {mode} backup partially completed. See 'Switch Status' tab.")
                    else:
                        self.status_label.config(text=f"Status: {mode} backup completed.")
                logging.info(f"{mode} backup process completed")

            except FileNotFoundError:
                if self.status_label:
                    self.status_label.config(text="Error: CSV file not found")
                messagebox.showerror("Error", f"CSV file not found: {self.csv_file}")
                logging.error(f"CSV file not found: {self.csv_file}")
            except Exception as e:
                if self.status_label:
                    self.status_label.config(text=f"Error: {str(e)}")
                messagebox.showerror("Error", f"Backup failed: {str(e)}")
                logging.error(f"Backup failed: {str(e)}")

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
                    messagebox.showerror("Error", "Invalid time format. Use HH:MM, comma-separated")
                    return
            self.schedule_times = times
        elif self.schedule_frequency == "weekly":
            self.schedule_day = self.weekly_day_var.get()
            hour = self.hour_var.get()
            minute = self.minute_var.get()
            try:
                if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
                    raise ValueError
                self.schedule_times = [f"{hour}:{minute}"]
            except ValueError:
                messagebox.showerror("Error", "Invalid time format. Use HH:MM (24-hour)")
                return
        else:
            self.schedule_day = self.custom_day_var.get()
            hour = self.hour_var.get()
            minute = self.minute_var.get()
            try:
                if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
                    raise ValueError
                self.schedule_times = [f"{hour}:{minute}"]
            except ValueError:
                messagebox.showerror("Error", "Invalid time format. Use HH:MM (24-hour)")
                return

        self.save_config()
        schedule.clear()
        if self.schedule_enabled:
            self.setup_schedule()
        messagebox.showinfo("Success", "Schedule updated")
        logging.info(f"Schedule updated: {self.schedule_frequency}")

    def run_schedule(self):
        if self.schedule_enabled:
            try:
                self.setup_schedule()
                logging.info(f"Scheduled backups set up: {self.schedule_frequency}")
            except AttributeError as e:
                logging.error(f"Failed to set up schedule: {str(e)}")
        while True:
            schedule.run_pending()
            time.sleep(60)

    def open_gui(self, systray):
        if self.root is None or not tk.Tk.winfo_exists(self.root):
            self.root = tk.Tk()  # Fixed syntax
            self.root.title(f"AOS-CX Config Backup Tool {self.VERSION}")
            self.root.geometry("810x990")
            self.root.resizable(False, False)
            self.root.configure(bg="#f0f0f0")
            try:
                icon_path = self.resource_path("icon-ico.ico")
                self.root.iconbitmap(icon_path)
                logging.info(f"Successfully set window icon to {icon_path}")
            except tk.TclError as e:
                logging.error(f"Failed to set window icon: {str(e)}")
            self.setup_gui()
            self.root.protocol("WM_DELETE_WINDOW", self.close_gui)
            self.root.mainloop()
        else:
            self.root.deiconify()

    def close_gui(self):
        if self.root:
            self.root.withdraw()

    def run(self):
        menu_options = (
            ("Open GUI", None, self.open_gui),
        )
        self.systray = SysTrayIcon("icon-ico.ico", f"AOS-CX Config Backup Tool {self.VERSION}", menu_options)
        self.systray.start()

        schedule_thread = threading.Thread(target=self.run_schedule, daemon=True)
        schedule_thread.start()

        self.open_gui(self.systray)

if __name__ == "__main__":
    app = SwitchBackup()
    app.run()