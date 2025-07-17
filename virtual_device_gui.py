#!/usr/bin/env python3
"""
Virtual BACnet Device Simulator - GUI Version
=============================================

A graphical interface for the Virtual BACnet Device Simulator with:
• Configuration panel for all INI settings
• Start/Stop device controls
• Real-time console output
• Progress bar for object creation
• Save/Load configuration
• Helpful tooltips for all settings

Usage:
    python virtual_device_gui.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import configparser
import sys
import io
import time
import queue
import subprocess
import os
import socket
from pathlib import Path

class ToolTip:
    """Simple tooltip implementation for widgets"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.tooltip = None

    def enter(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, background="lightyellow",
                        relief="solid", borderwidth=1, font=("Arial", 9), wraplength=300)
        label.pack()

    def leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class VirtualDeviceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Virtual BACnet Device Simulator")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Initialize variables
        self.device_process = None
        self.is_running = False
        self.config_file = "virtual_device.ini"
        self.output_queue = queue.Queue()
        
        # Create the GUI
        self.create_widgets()
        self.load_config()
        
        # Start output monitoring
        self.monitor_output()
        
    def get_local_ip(self):
        """Get the local IP address"""
        try:
            # Connect to a remote address to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "192.168.1.100"
    
    def generate_device_ip(self, base_ip=None):
        """Generate a unique IP address for this device"""
        if base_ip is None:
            # Use the actual local IP address of this machine
            local_ip = self.get_local_ip()
            return local_ip
        return base_ip
    
    def auto_generate_ip(self):
        """Auto-detect the local IP address"""
        new_ip = self.generate_device_ip()
        self.ip_var.set(new_ip)
        self.log_message(f"✔ Auto-detected local IP: {new_ip}")
        
    def create_widgets(self):
        # Create main frame with notebook for tabs
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Virtual BACnet Device Simulator", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Left panel - Configuration
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        config_frame.columnconfigure(1, weight=1)
        
        # Right panel - Control and Output
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        control_frame.columnconfigure(0, weight=1)
        control_frame.rowconfigure(2, weight=1)
        
        self.create_config_panel(config_frame)
        self.create_control_panel(control_frame)
        
    def create_config_panel(self, parent):
        """Create configuration input panel"""
        row = 0
        
        # Device Settings
        device_frame = ttk.LabelFrame(parent, text="Device Settings", padding="5")
        device_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        device_frame.columnconfigure(1, weight=1)
        
        # Port
        port_label = ttk.Label(device_frame, text="Port:")
        port_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.port_var = tk.StringVar(value="47809")
        port_entry = ttk.Entry(device_frame, textvariable=self.port_var, width=10)
        port_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        ToolTip(port_label, "UDP port for BACnet communication\n• Standard BACnet port is 47808\n• Use different ports to avoid conflicts\n• Range: 1024-65535")
        
        # IP Address
        ip_label = ttk.Label(device_frame, text="IP Address:")
        ip_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        ip_frame = ttk.Frame(device_frame)
        ip_frame.grid(row=1, column=1, sticky=(tk.W, tk.E))
        ip_frame.columnconfigure(0, weight=1)
        
        self.ip_var = tk.StringVar(value=self.generate_device_ip())
        ip_entry = ttk.Entry(ip_frame, textvariable=self.ip_var)
        ip_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        auto_ip_btn = ttk.Button(ip_frame, text="Auto", command=self.auto_generate_ip, width=6)
        auto_ip_btn.grid(row=0, column=1, padx=(5, 0))
        ToolTip(ip_label, "IP address for BACnet communication\n• Must be unique on your network\n• Auto-detects your local network\n• Click 'Auto' to regenerate automatically")
        ToolTip(auto_ip_btn, "Automatically generate a unique IP address\n• Uses your current network settings\n• Assigns next available address in range")
        
        # Device ID
        id_label = ttk.Label(device_frame, text="Device ID:")
        id_label.grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.device_id_var = tk.StringVar(value="3001")
        id_entry = ttk.Entry(device_frame, textvariable=self.device_id_var, width=10)
        id_entry.grid(row=2, column=1, sticky=(tk.W, tk.E))
        ToolTip(id_label, "BACnet device instance ID\n• Must be unique on your BACnet network\n• This is how the device appears in BACnet browsers\n• Range: 1-4194303")
        
        # Device Name
        name_label = ttk.Label(device_frame, text="Device Name:")
        name_label.grid(row=3, column=0, sticky=tk.W, padx=(0, 5))
        self.device_name_var = tk.StringVar(value="Virtual VAV Unit")
        name_entry = ttk.Entry(device_frame, textvariable=self.device_name_var)
        name_entry.grid(row=3, column=1, sticky=(tk.W, tk.E))
        ToolTip(name_label, "Device name visible in BACnet browsers\n• Keep it descriptive but concise\n• Shows up in YABE, VTS, and other BACnet tools")
        
        # Device Description
        desc_label = ttk.Label(device_frame, text="Description:")
        desc_label.grid(row=4, column=0, sticky=tk.W, padx=(0, 5))
        self.device_desc_var = tk.StringVar(value="Enhanced Virtual BACnet Device with CSV Point Loading")
        desc_entry = ttk.Entry(device_frame, textvariable=self.device_desc_var)
        desc_entry.grid(row=4, column=1, sticky=(tk.W, tk.E))
        ToolTip(desc_label, "Device description shown in BACnet browsers\n• Provide detailed information about the device's purpose\n• Helps identify the device in network discovery")
        
        row += 1
        
        # Data Settings
        data_frame = ttk.LabelFrame(parent, text="Data Source", padding="5")
        data_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        data_frame.columnconfigure(1, weight=1)
        
        # Points File
        points_label = ttk.Label(data_frame, text="Points CSV File:")
        points_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        points_frame = ttk.Frame(data_frame)
        points_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        points_frame.columnconfigure(0, weight=1)
        
        self.points_file_var = tk.StringVar(value="points.csv")
        points_entry = ttk.Entry(points_frame, textvariable=self.points_file_var)
        points_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(points_frame, text="Browse", command=self.browse_points_file, width=8).grid(row=0, column=1, padx=(5, 0))
        ToolTip(points_label, "CSV file containing BACnet object definitions\n• Should have columns: Type, Instance, Name, PresentValue, Override, Description\n• If file doesn't exist, simulator will create a minimal test device\n• Supports Analog, Binary, and Multistate objects")
        
        row += 1
        
        # Simulation Settings
        sim_frame = ttk.LabelFrame(parent, text="Simulation Settings", padding="5")
        sim_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        sim_frame.columnconfigure(1, weight=1)
        
        # Step Interval
        step_label = ttk.Label(sim_frame, text="Step Interval (s):")
        step_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.step_interval_var = tk.StringVar(value="0.5")
        step_entry = ttk.Entry(sim_frame, textvariable=self.step_interval_var, width=10)
        step_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        ToolTip(step_label, "Simulation update interval in seconds\n• Lower values = more responsive simulation, higher CPU usage\n• Range: 0.1-10.0\n• Recommended: 0.5-2.0 seconds")
        
        # AI Variation Range
        ai_label = ttk.Label(sim_frame, text="AI Variation Range:")
        ai_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.ai_variation_var = tk.StringVar(value="0.15")
        ai_entry = ttk.Entry(sim_frame, textvariable=self.ai_variation_var, width=10)
        ai_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
        ToolTip(ai_label, "Random variation for analog inputs (percentage)\n• Simulates sensor noise and real-world fluctuations\n• 0.15 = ±15% variation from base value\n• Range: 0.0-1.0")
        
        # AO Priority 16 Variation
        ao_label = ttk.Label(sim_frame, text="AO Priority 16 Variation:")
        ao_label.grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.ao_variation_var = tk.StringVar(value="0.25")
        ao_entry = ttk.Entry(sim_frame, textvariable=self.ao_variation_var, width=10)
        ao_entry.grid(row=2, column=1, sticky=(tk.W, tk.E))
        ToolTip(ao_label, "Variation for analog outputs with priority 16 (percentage)\n• Simulates automatic control system adjustments\n• Only affects outputs that have been written to with priority 16\n• Range: 0.0-1.0")
        
        # Binary Flip Probability
        binary_label = ttk.Label(sim_frame, text="Binary Flip Probability:")
        binary_label.grid(row=3, column=0, sticky=tk.W, padx=(0, 5))
        self.binary_flip_var = tk.StringVar(value="0.01")
        binary_entry = ttk.Entry(sim_frame, textvariable=self.binary_flip_var, width=10)
        binary_entry.grid(row=3, column=1, sticky=(tk.W, tk.E))
        ToolTip(binary_label, "Probability of binary inputs changing state per simulation step\n• Simulates alarm conditions, status changes, and sensor triggers\n• 0.01 = 1% chance per step (with 0.5s steps = ~1 change per 50 seconds)\n• Range: 0.0-1.0")
        
        row += 1
        
        # Environment Settings
        env_frame = ttk.LabelFrame(parent, text="Environment Settings", padding="5")
        env_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        env_frame.columnconfigure(1, weight=1)
        
        # Outdoor Temp Cycle
        cycle_label = ttk.Label(env_frame, text="Outdoor Temp Cycle (min):")
        cycle_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.temp_cycle_var = tk.StringVar(value="20")
        cycle_entry = ttk.Entry(env_frame, textvariable=self.temp_cycle_var, width=10)
        cycle_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        ToolTip(cycle_label, "Duration of outdoor temperature cycle in minutes\n• Creates realistic daily temperature patterns\n• 20 minutes = accelerated daily cycle for testing\n• 1440 minutes = real 24-hour cycle\n• Currently used for temperature sensors with 'Temperature' in their name")
        
        # Base Temperature
        base_label = ttk.Label(env_frame, text="Base Temperature (°C):")
        base_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.base_temp_var = tk.StringVar(value="21.0")
        base_entry = ttk.Entry(env_frame, textvariable=self.base_temp_var, width=10)
        base_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
        ToolTip(base_label, "Base outdoor temperature in degrees Celsius\n• Average temperature around which variations occur\n• Typical values: 15-25°C depending on season/location\n• Note: Currently hard-coded to 20°C in simulation")
        
        # Temperature Amplitude
        amp_label = ttk.Label(env_frame, text="Temperature Amplitude (°C):")
        amp_label.grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.temp_amplitude_var = tk.StringVar(value="6.0")
        amp_entry = ttk.Entry(env_frame, textvariable=self.temp_amplitude_var, width=10)
        amp_entry.grid(row=2, column=1, sticky=(tk.W, tk.E))
        ToolTip(amp_label, "Temperature swing amplitude in degrees Celsius\n• How much temperature varies above/below base temperature\n• Creates morning cool / afternoon warm cycles\n• Typical values: 3-10°C\n• Note: Currently hard-coded to 5°C in simulation")
        
        # Info label about environmental settings
        info_label = ttk.Label(env_frame, text="ℹ️ Environmental settings create realistic temperature cycles for sensors", 
                              font=("Arial", 8), foreground="blue")
        info_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        ToolTip(info_label, "Environmental simulation creates:\n• Sine wave temperature cycles for outdoor sensors\n• Random walk for humidity sensors\n• Realistic variations for airflow sensors\n• Only affects objects with specific keywords in their names")
        
        row += 1
        
        # Config file controls
        config_controls = ttk.Frame(parent)
        config_controls.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        load_btn = ttk.Button(config_controls, text="Load Config", command=self.load_config_file)
        load_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(load_btn, "Load configuration from an INI file\n• Restores all device and simulation settings\n• Useful for switching between different device configurations")
        
        save_btn = ttk.Button(config_controls, text="Save Config", command=self.save_config_file)
        save_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(save_btn, "Save current configuration to an INI file\n• Preserves all settings for future use\n• Creates a reusable device configuration")
        
        reset_btn = ttk.Button(config_controls, text="Reset Defaults", command=self.reset_defaults)
        reset_btn.pack(side=tk.LEFT)
        ToolTip(reset_btn, "Reset all settings to default values\n• Restores factory default configuration\n• Useful for starting over with clean settings")
        
    def create_control_panel(self, parent):
        """Create control panel with start/stop and output"""
        # Control buttons
        button_frame = ttk.LabelFrame(parent, text="Device Control", padding="10")
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.start_button = ttk.Button(button_frame, text="🚀 Start Device", 
                                      command=self.start_device, style="Green.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        ToolTip(self.start_button, "Start the virtual BACnet device\n• Creates BACnet objects from CSV file\n• Begins simulation with current settings\n• Device becomes discoverable on network")
        
        self.stop_button = ttk.Button(button_frame, text="⏹ Stop Device", 
                                     command=self.stop_device, state=tk.DISABLED, style="Red.TButton")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        ToolTip(self.stop_button, "Stop the virtual BACnet device\n• Terminates simulation\n• Releases network port\n• Device no longer discoverable")
        
        # Status indicator
        self.status_label = ttk.Label(button_frame, text="● Stopped", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Progress bar
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding="5")
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, length=300)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="Ready to start")
        self.progress_label.pack()
        
        # Console output
        console_frame = ttk.LabelFrame(parent, text="Console Output", padding="5")
        console_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        
        # Make console read-only
        self.console_text = scrolledtext.ScrolledText(console_frame, height=20, width=60, state=tk.DISABLED)
        self.console_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear console button
        clear_btn = ttk.Button(console_frame, text="Clear Console", command=self.clear_console)
        clear_btn.grid(row=1, column=0, pady=(5, 0))
        ToolTip(clear_btn, "Clear all console output\n• Removes all logged messages\n• Useful for focusing on current session")
        
    def clear_console(self):
        """Clear console output"""
        self.console_text.config(state=tk.NORMAL)
        self.console_text.delete(1.0, tk.END)
        self.console_text.config(state=tk.DISABLED)
        
    def browse_points_file(self):
        """Browse for points CSV file"""
        filename = filedialog.askopenfilename(
            title="Select Points CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.points_file_var.set(filename)
    
    def load_config_file(self):
        """Load configuration from file"""
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")]
        )
        if filename:
            self.config_file = filename
            self.load_config()
    
    def save_config_file(self):
        """Save configuration to file"""
        filename = filedialog.asksaveasfilename(
            title="Save Configuration",
            defaultextension=".ini",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")]
        )
        if filename:
            self.config_file = filename
            self.save_config()
    
    def load_config(self):
        """Load configuration from INI file"""
        if not os.path.exists(self.config_file):
            return
            
        config = configparser.ConfigParser()
        config.read(self.config_file)
        
        try:
            # Device settings
            if config.has_section('device'):
                self.port_var.set(config.get('device', 'port', fallback='47809'))
                self.ip_var.set(config.get('device', 'ip', fallback=self.generate_device_ip()))
                self.device_id_var.set(config.get('device', 'device_id', fallback='3001'))
                self.device_name_var.set(config.get('device', 'device_name', fallback='Virtual VAV Unit'))
                self.device_desc_var.set(config.get('device', 'device_description', 
                                                   fallback='Enhanced Virtual BACnet Device with CSV Point Loading'))
            
            # Data settings
            if config.has_section('data'):
                self.points_file_var.set(config.get('data', 'points_file', fallback='points.csv'))
            
            # Simulation settings
            if config.has_section('simulation'):
                self.step_interval_var.set(config.get('simulation', 'step_interval', fallback='0.5'))
                self.ai_variation_var.set(config.get('simulation', 'ai_variation_range', fallback='0.15'))
                self.ao_variation_var.set(config.get('simulation', 'ao_priority16_variation', fallback='0.25'))
                self.binary_flip_var.set(config.get('simulation', 'binary_flip_probability', fallback='0.01'))
            
            # Environment settings
            if config.has_section('environment'):
                self.temp_cycle_var.set(config.get('environment', 'outdoor_temp_cycle_minutes', fallback='20'))
                self.base_temp_var.set(config.get('environment', 'outdoor_temp_base', fallback='21.0'))
                self.temp_amplitude_var.set(config.get('environment', 'outdoor_temp_amplitude', fallback='6.0'))
                
            self.log_message("✔ Configuration loaded successfully")
        except Exception as e:
            self.log_message(f"✗ Error loading configuration: {e}")
    
    def save_config(self):
        """Save current configuration to INI file"""
        config = configparser.ConfigParser()
        
        # Device section
        config.add_section('device')
        config.set('device', 'port', self.port_var.get())
        config.set('device', 'ip', self.ip_var.get())
        config.set('device', 'device_id', self.device_id_var.get())
        config.set('device', 'device_name', self.device_name_var.get())
        config.set('device', 'device_description', self.device_desc_var.get())
        
        # Data section
        config.add_section('data')
        config.set('data', 'points_file', self.points_file_var.get())
        
        # Simulation section
        config.add_section('simulation')
        config.set('simulation', 'step_interval', self.step_interval_var.get())
        config.set('simulation', 'ai_variation_range', self.ai_variation_var.get())
        config.set('simulation', 'ao_priority16_variation', self.ao_variation_var.get())
        config.set('simulation', 'binary_flip_probability', self.binary_flip_var.get())
        
        # Environment section
        config.add_section('environment')
        config.set('environment', 'outdoor_temp_cycle_minutes', self.temp_cycle_var.get())
        config.set('environment', 'outdoor_temp_base', self.base_temp_var.get())
        config.set('environment', 'outdoor_temp_amplitude', self.temp_amplitude_var.get())
        
        try:
            with open(self.config_file, 'w') as f:
                config.write(f)
            self.log_message(f"✔ Configuration saved to {self.config_file}")
        except Exception as e:
            self.log_message(f"✗ Error saving configuration: {e}")
    
    def reset_defaults(self):
        """Reset all settings to defaults"""
        self.port_var.set("47809")
        self.ip_var.set(self.generate_device_ip())
        self.device_id_var.set("3001")
        self.device_name_var.set("Virtual VAV Unit")
        self.device_desc_var.set("Enhanced Virtual BACnet Device with CSV Point Loading")
        self.points_file_var.set("points.csv")
        self.step_interval_var.set("0.5")
        self.ai_variation_var.set("0.15")
        self.ao_variation_var.set("0.25")
        self.binary_flip_var.set("0.01")
        self.temp_cycle_var.set("20")
        self.base_temp_var.set("21.0")
        self.temp_amplitude_var.set("6.0")
        self.log_message("✔ Settings reset to defaults")
    
    def start_device(self):
        """Start the virtual device"""
        if self.is_running:
            return
        
        # Save current config before starting
        temp_config = "temp_gui_config.ini"
        old_config_file = self.config_file
        self.config_file = temp_config
        self.save_config()
        self.config_file = old_config_file
        
        # Start device in separate thread
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="● Starting...", foreground="orange")
        self.progress_var.set(0)
        self.progress_label.config(text="Initializing...")
        
        # Start device process
        threading.Thread(target=self.run_device, args=(temp_config,), daemon=True).start()
        
        self.log_message("🚀 Starting Virtual BACnet Device...")
    
    def stop_device(self):
        """Stop the virtual device"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.device_process:
            self.device_process.terminate()
            self.device_process = None
        
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="● Stopped", foreground="red")
        self.progress_var.set(0)
        self.progress_label.config(text="Device stopped")
        
        self.log_message("⏹ Virtual BACnet Device stopped")
        
        # Clean up temp config
        try:
            os.remove("temp_gui_config.ini")
        except:
            pass
    
    def run_device(self, config_file):
        """Run the virtual device process"""
        try:
            # Build command
            cmd = [
                sys.executable, "virtual_device.py",
                "--config", config_file,
                "-a", self.ip_var.get(),
                "--port", self.port_var.get()
            ]
            
            # Start process with unbuffered output
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'  # Force unbuffered output
            
            self.device_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # Update status
            self.root.after(0, lambda: self.status_label.config(text="● Running", foreground="green"))
            
            # Read output
            for line in iter(self.device_process.stdout.readline, ''):
                if not self.is_running:
                    break
                
                line = line.strip()
                if line:
                    # Update progress bar based on output
                    if "Creating objects..." in line and "%" in line:
                        try:
                            percent = int(line.split('%')[0].split()[-1])
                            self.root.after(0, lambda p=percent: self.progress_var.set(p))
                            self.root.after(0, lambda: self.progress_label.config(text="Creating BACnet objects..."))
                        except:
                            pass
                    elif "Successfully created" in line:
                        self.root.after(0, lambda: self.progress_var.set(100))
                        self.root.after(0, lambda: self.progress_label.config(text="Objects created successfully"))
                    elif "Device is READY" in line:
                        self.root.after(0, lambda: self.progress_label.config(text="Device ready and monitoring"))
                    
                    # Add to console
                    self.root.after(0, lambda msg=line: self.log_message(msg))
            
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"✗ Error running device: {e}"))
            self.root.after(0, self.stop_device)
    
    def log_message(self, message):
        """Add message to console output"""
        self.console_text.config(state=tk.NORMAL)
        self.console_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.console_text.see(tk.END)
        self.console_text.config(state=tk.DISABLED)
    
    def monitor_output(self):
        """Monitor output queue for messages"""
        try:
            while not self.output_queue.empty():
                message = self.output_queue.get_nowait()
                self.log_message(message)
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.monitor_output)
    
    def on_closing(self):
        """Handle window closing"""
        if self.is_running:
            if messagebox.askokcancel("Quit", "Device is running. Stop and quit?"):
                self.stop_device()
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    
    # Configure styles
    style = ttk.Style()
    style.configure("Green.TButton", foreground="green")
    style.configure("Red.TButton", foreground="red")
    
    app = VirtualDeviceGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main() 