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
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings (optional - not recommended for production)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SwitchBackup:
    def __init__(self):
        self.config_file = "backup_config.json"
        self.max_backups = 5
        self.schedule_enabled = True  # Track whether automatic scheduling is enabled
        self.load_config()
        self.root = tk.Tk()
        self.root.title("AOS-CX Switch Backup")
        self.root.geometry("740x835")  # Default size as requested
        self.root.configure(bg="#f0f0f0")
        self.setup_gui()
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def load_config(self):
        """Load saved configuration from file. CSV file can be named anything."""
        default_config = {
            'csv_path': "switches.csv",
            'schedule_time': "02:00",
            'default_username': "admin",
            'default_password': "",
            'schedule_enabled': True,
            'base_dir': "switch_configs"
        }
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.csv_file = config.get('csv_path', default_config['csv_path'])
                self.schedule_time = config.get('schedule_time', default_config['schedule_time'])
                self.default_username = config.get('default_username', default_config['default_username'])
                self.default_password = config.get('default_password', default_config['default_password'])
                self.schedule_enabled = config.get('schedule_enabled', default_config['schedule_enabled'])
                self.base_dir = config.get('base_dir', default_config['base_dir'])
        except FileNotFoundError:
            self.csv_file = default_config['csv_path']
            self.schedule_time = default_config['schedule_time']
            self.default_username = default_config['default_username']
            self.default_password = default_config['default_password']
            self.schedule_enabled = default_config['schedule_enabled']
            self.base_dir = default_config['base_dir']

    def save_config(self, switch_name=None, ip=None, config=None):
        """Save configuration to file and manage retention"""
        if switch_name and ip and config:  # If called to save a switch config
            switch_dir = os.path.join(self.base_dir, switch_name)
            if not os.path.exists(switch_dir):
                os.makedirs(switch_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{switch_name}_{ip}_{timestamp}.txt"
            filepath = os.path.join(switch_dir, filename)

            with open(filepath, 'w') as f:
                f.write(config)

            self.manage_retention(switch_dir)
            logging.info(f"Saved config for {switch_name} ({ip}) to {filepath}")
        else:  # If called to save the app config (CSV path, schedule, etc.)
            config = {
                'csv_path': self.csv_file,
                'schedule_time': self.schedule_time,
                'default_username': self.default_username,
                'default_password': self.default_password,
                'schedule_enabled': self.schedule_enabled,
                'base_dir': self.base_dir
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            logging.info("Saved application configuration")

    def setup_gui(self):
        """Set up the GUI elements with modern styling"""
        style = ttk.Style()
        style.configure("TButton", padding=6, font=('Helvetica', 10))
        style.configure("TLabel", background="#f0f0f0", font=('Helvetica', 10))
        
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill="both", expand=True)

        # CSV File Section
        csv_frame = ttk.LabelFrame(main_frame, text="Switch Inventory", padding="10")
        csv_frame.pack(fill="x", pady=(0, 15))
        
        self.path_label = ttk.Label(csv_frame, text=self.csv_file, wraplength=700)
        self.path_label.pack(pady=5)
        
        ttk.Button(csv_frame, text="Select CSV File", command=self.select_csv).pack()

        # Backup Location Section
        backup_loc_frame = ttk.LabelFrame(main_frame, text="Backup Location", padding="10")
        backup_loc_frame.pack(fill="x", pady=15)
        
        self.backup_loc_label = ttk.Label(backup_loc_frame, text=self.base_dir, wraplength=700)
        self.backup_loc_label.pack(pady=5)
        
        ttk.Button(backup_loc_frame, text="Select Backup Directory", command=self.select_backup_dir).pack()

        # Credentials Section (Centered)
        cred_frame = ttk.LabelFrame(main_frame, text="REST API Credentials", padding="10")
        cred_frame.pack(fill="x", pady=15)
        
        # Create a subframe to center the credentials fields
        cred_subframe = ttk.Frame(cred_frame)
        cred_subframe.pack(expand=True)

        username_frame = ttk.Frame(cred_subframe)
        username_frame.pack(pady=5)
        ttk.Label(username_frame, text="Username:").pack(side="left", padx=5)
        self.username_entry = ttk.Entry(username_frame, width=30)
        self.username_entry.insert(0, self.default_username)
        self.username_entry.pack(side="left", padx=5)

        password_frame = ttk.Frame(cred_subframe)
        password_frame.pack(pady=5)
        ttk.Label(password_frame, text="Password:").pack(side="left", padx=5)
        self.password_entry = ttk.Entry(password_frame, show="*", width=30)
        self.password_entry.insert(0, self.default_password)
        self.password_entry.pack(side="left", padx=5)

        ttk.Button(cred_subframe, text="Save Credentials", command=self.save_credentials).pack(pady=5)

        # Schedule Section
        sched_frame = ttk.LabelFrame(main_frame, text="Automatic Backup Schedule", padding="10")
        sched_frame.pack(fill="x", pady=15)
        
        time_frame = ttk.Frame(sched_frame)
        time_frame.pack(pady=5)
        
        self.hour_var = tk.StringVar(value=self.schedule_time.split(':')[0])
        self.minute_var = tk.StringVar(value=self.schedule_time.split(':')[1])
        
        ttk.Combobox(time_frame, textvariable=self.hour_var, 
                    values=[f"{h:02d}" for h in range(24)], 
                    width=5).pack(side="left", padx=5)
        ttk.Label(time_frame, text=":").pack(side="left")
        ttk.Combobox(time_frame, textvariable=self.minute_var, 
                    values=[f"{m:02d}" for m in range(60)], 
                    width=5).pack(side="left", padx=5)
        ttk.Button(time_frame, text="Set", command=self.update_schedule).pack(side="left", padx=5)

        self.schedule_label = ttk.Label(sched_frame, text=f"Daily Backup: {self.schedule_time}")
        self.schedule_label.pack(pady=5)

        self.schedule_toggle_var = tk.BooleanVar(value=self.schedule_enabled)
        ttk.Checkbutton(sched_frame, text="Automatic Schedule", 
                       variable=self.schedule_toggle_var, 
                       command=self.toggle_schedule).pack(pady=5)

        # Manual Backup Section
        control_frame = ttk.LabelFrame(main_frame, text="Manual Backup", padding="10")
        control_frame.pack(fill="x", pady=15)
        
        ttk.Button(control_frame, text="Run Backup Now", command=self.manual_backup).pack(pady=5)
        
        self.status_label = ttk.Label(control_frame, text="Status: Idle")
        self.status_label.pack(pady=5)

    def select_csv(self):
        """Handle CSV file selection - file can be named anything with .csv extension"""
        filepath = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv")],
            title="Select Switch Inventory CSV"
        )
        if filepath:
            self.csv_file = filepath
            self.save_config()  # Save the app config
            self.path_label.config(text=filepath)
            messagebox.showinfo("Success", "CSV file path updated")
            logging.info(f"Selected CSV file: {filepath}")

    def select_backup_dir(self):
        """Select directory for storing backup configuration files"""
        directory = filedialog.askdirectory(
            title="Select Backup Directory"
        )
        if directory:
            self.base_dir = directory
            self.save_config()  # Save the app config
            self.backup_loc_label.config(text=self.base_dir)
            messagebox.showinfo("Success", "Backup directory updated")
            logging.info(f"Selected backup directory: {self.base_dir}")

    def save_credentials(self):
        """Save the updated credentials"""
        self.default_username = self.username_entry.get()
        self.default_password = self.password_entry.get()
        self.save_config()  # Save the app config
        messagebox.showinfo("Success", "Credentials updated")
        logging.info("Credentials updated")

    def update_schedule(self):
        """Update the backup schedule"""
        hour = self.hour_var.get()
        minute = self.minute_var.get()
        try:
            if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
                raise ValueError
            self.schedule_time = f"{hour}:{minute}"
            self.save_config()  # Save the app config
            self.schedule_label.config(text=f"Daily Backup: {self.schedule_time}")
            schedule.clear()
            if self.schedule_enabled:
                schedule.every().day.at(self.schedule_time).do(self.backup_switches)
            messagebox.showinfo("Success", f"Schedule updated to {self.schedule_time}")
            logging.info(f"Schedule updated to {self.schedule_time}")
        except ValueError:
            messagebox.showerror("Error", "Invalid time format. Use HH:MM (24-hour)")
            logging.error("Invalid time format entered for schedule")

    def toggle_schedule(self):
        """Enable or disable the automatic schedule"""
        self.schedule_enabled = self.schedule_toggle_var.get()
        schedule.clear()
        if self.schedule_enabled:
            schedule.every().day.at(self.schedule_time).do(self.backup_switches)
            logging.info("Automatic schedule enabled")
        else:
            logging.info("Automatic schedule disabled")
        self.save_config()  # Save the app config

    def get_switch_config(self, ip, username, password):
        """Get switch configuration via REST API (AOS-CX 10.13)"""
        session = requests.Session()
        config_text = None
        try:
            # Login URL for REST API v10.13
            login_url = f"https://{ip}/rest/v10.13/login"
            login_response = session.post(
                login_url,
                data={"username": username, "password": password},
                verify=False,
                timeout=10
            )
            login_response.raise_for_status()

            # Retrieve running config using REST API v10.13 endpoint
            config_url = f"https://{ip}/rest/v10.13/configs/running-config"
            headers = {"Accept": "text/plain"}
            config_response = session.get(
                config_url,
                headers=headers,
                verify=False,
                timeout=10
            )
            config_response.raise_for_status()
            config_text = config_response.text

        except requests.exceptions.RequestException as e:
            self.status_label.config(text=f"Error: {str(e)}")
            logging.error(f"Failed to get config from {ip}: {str(e)}")
            return None

        finally:
            # Ensure logout is always performed at the very end, even if an error occurs
            try:
                logout_url = f"https://{ip}/rest/v10.13/logout"
                session.post(logout_url, verify=False, timeout=10)
                logging.info(f"Successfully logged out from {ip}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to logout from {ip}: {str(e)}")

        return config_text

    def manage_retention(self, switch_dir):
        """Keep only the latest 5 configuration files"""
        files = sorted(
            [f for f in os.listdir(switch_dir) if f.endswith('.txt')],
            reverse=True
        )
        while len(files) > self.max_backups:
            oldest_file = os.path.join(switch_dir, files.pop())
            os.remove(oldest_file)
            logging.info(f"Removed old backup: {oldest_file}")

    def backup_switches(self, is_manual=False):
        """Read CSV and backup all switches - CSV file can be any name"""
        mode = "Manual" if is_manual else "Automatic"
        self.status_label.config(text=f"Status: Running {mode.lower()} backup...")
        logging.info(f"Starting {mode.lower()} backup process")
        try:
            with open(self.csv_file, 'r') as f:
                reader = csv.DictReader(f)
                required_cols = ['name', 'ip']
                if not all(col in reader.fieldnames for col in required_cols):
                    self.status_label.config(text="Error: CSV missing required columns")
                    messagebox.showerror("Error", "CSV must contain 'name' and 'ip' columns")
                    logging.error("CSV missing required columns: 'name' and 'ip'")
                    return

                for row in reader:
                    self.status_label.config(text=f"Status: Backing up {row['name']}")
                    self.root.update()
                    username = row.get('username', self.default_username)
                    password = row.get('password', self.default_password)
                    config = self.get_switch_config(
                        row['ip'],
                        username,
                        password
                    )
                    if config:
                        self.save_config(row['name'], row['ip'], config)
                    else:
                        logging.warning(f"No config retrieved for {row['name']} ({row['ip']})")

            self.status_label.config(text=f"Status: {mode} backup completed")
            logging.info(f"{mode} backup process completed")

        except FileNotFoundError:
            self.status_label.config(text="Error: CSV file not found")
            messagebox.showerror("Error", f"CSV file not found: {self.csv_file}")
            logging.error(f"CSV file not found: {self.csv_file}")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            messagebox.showerror("Error", f"Backup failed: {str(e)}")
            logging.error(f"Backup failed: {str(e)}")

    def manual_backup(self):
        """Run a manual backup immediately"""
        self.backup_switches(is_manual=True)

    def run_schedule(self):
        """Run scheduled backups if enabled"""
        if self.schedule_enabled:
            schedule.every().day.at(self.schedule_time).do(lambda: self.backup_switches(is_manual=False))
            logging.info(f"Scheduled backups to run daily at {self.schedule_time}")
        while True:
            schedule.run_pending()
            time.sleep(60)

    def run(self):
        """Start the application"""
        import threading
        schedule_thread = threading.Thread(target=self.run_schedule, daemon=True)
        schedule_thread.start()
        
        self.root.mainloop()

def main():
    backup = SwitchBackup()
    backup.run()

if __name__ == "__main__":
    main()