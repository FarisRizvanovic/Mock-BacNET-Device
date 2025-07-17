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
from pathlib import Path

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
        ttk.Label(device_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.port_var = tk.StringVar(value="47809")
        ttk.Entry(device_frame, textvariable=self.port_var, width=10).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Device ID
        ttk.Label(device_frame, text="Device ID:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.device_id_var = tk.StringVar(value="3001")
        ttk.Entry(device_frame, textvariable=self.device_id_var, width=10).grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        # Device Name
        ttk.Label(device_frame, text="Device Name:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.device_name_var = tk.StringVar(value="Virtual VAV Unit")
        ttk.Entry(device_frame, textvariable=self.device_name_var).grid(row=2, column=1, sticky=(tk.W, tk.E))
        
        # Device Description
        ttk.Label(device_frame, text="Description:").grid(row=3, column=0, sticky=tk.W, padx=(0, 5))
        self.device_desc_var = tk.StringVar(value="Enhanced Virtual BACnet Device with CSV Point Loading")
        ttk.Entry(device_frame, textvariable=self.device_desc_var).grid(row=3, column=1, sticky=(tk.W, tk.E))
        
        row += 1
        
        # Data Settings
        data_frame = ttk.LabelFrame(parent, text="Data Source", padding="5")
        data_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        data_frame.columnconfigure(1, weight=1)
        
        # Points File
        ttk.Label(data_frame, text="Points CSV File:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        points_frame = ttk.Frame(data_frame)
        points_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        points_frame.columnconfigure(0, weight=1)
        
        self.points_file_var = tk.StringVar(value="points.csv")
        ttk.Entry(points_frame, textvariable=self.points_file_var).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(points_frame, text="Browse", command=self.browse_points_file, width=8).grid(row=0, column=1, padx=(5, 0))
        
        row += 1
        
        # Simulation Settings
        sim_frame = ttk.LabelFrame(parent, text="Simulation Settings", padding="5")
        sim_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        sim_frame.columnconfigure(1, weight=1)
        
        # Step Interval
        ttk.Label(sim_frame, text="Step Interval (s):").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.step_interval_var = tk.StringVar(value="0.5")
        ttk.Entry(sim_frame, textvariable=self.step_interval_var, width=10).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # AI Variation Range
        ttk.Label(sim_frame, text="AI Variation Range:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.ai_variation_var = tk.StringVar(value="0.15")
        ttk.Entry(sim_frame, textvariable=self.ai_variation_var, width=10).grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        # AO Priority 16 Variation
        ttk.Label(sim_frame, text="AO Priority 16 Variation:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.ao_variation_var = tk.StringVar(value="0.25")
        ttk.Entry(sim_frame, textvariable=self.ao_variation_var, width=10).grid(row=2, column=1, sticky=(tk.W, tk.E))
        
        # Binary Flip Probability
        ttk.Label(sim_frame, text="Binary Flip Probability:").grid(row=3, column=0, sticky=tk.W, padx=(0, 5))
        self.binary_flip_var = tk.StringVar(value="0.01")
        ttk.Entry(sim_frame, textvariable=self.binary_flip_var, width=10).grid(row=3, column=1, sticky=(tk.W, tk.E))
        
        row += 1
        
        # Environment Settings
        env_frame = ttk.LabelFrame(parent, text="Environment Settings", padding="5")
        env_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        env_frame.columnconfigure(1, weight=1)
        
        # Outdoor Temp Cycle
        ttk.Label(env_frame, text="Outdoor Temp Cycle (min):").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.temp_cycle_var = tk.StringVar(value="20")
        ttk.Entry(env_frame, textvariable=self.temp_cycle_var, width=10).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Base Temperature
        ttk.Label(env_frame, text="Base Temperature (°C):").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.base_temp_var = tk.StringVar(value="21.0")
        ttk.Entry(env_frame, textvariable=self.base_temp_var, width=10).grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        # Temperature Amplitude
        ttk.Label(env_frame, text="Temperature Amplitude (°C):").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.temp_amplitude_var = tk.StringVar(value="6.0")
        ttk.Entry(env_frame, textvariable=self.temp_amplitude_var, width=10).grid(row=2, column=1, sticky=(tk.W, tk.E))
        
        row += 1
        
        # Config file controls
        config_controls = ttk.Frame(parent)
        config_controls.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(config_controls, text="Load Config", command=self.load_config_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(config_controls, text="Save Config", command=self.save_config_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(config_controls, text="Reset Defaults", command=self.reset_defaults).pack(side=tk.LEFT)
        
    def create_control_panel(self, parent):
        """Create control panel with start/stop and output"""
        # Control buttons
        button_frame = ttk.LabelFrame(parent, text="Device Control", padding="10")
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.start_button = ttk.Button(button_frame, text="🚀 Start Device", 
                                      command=self.start_device, style="Green.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="⏹ Stop Device", 
                                     command=self.stop_device, state=tk.DISABLED, style="Red.TButton")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
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
        
        self.console_text = scrolledtext.ScrolledText(console_frame, height=20, width=60)
        self.console_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear console button
        ttk.Button(console_frame, text="Clear Console", 
                  command=lambda: self.console_text.delete(1.0, tk.END)).grid(row=1, column=0, pady=(5, 0))
        
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
                "--config", config_file
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
        self.console_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.console_text.see(tk.END)
    
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