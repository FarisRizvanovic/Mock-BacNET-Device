#!/usr/bin/env python3
"""
Virtual BACnet Device Simulator
===============================

A Python-based BACnet/IP device simulator that loads point definitions from CSV files
and creates fully functional BACnet objects with realistic simulation behavior.

Features:
• Automatic IP detection for easy network discovery
• CSV-based point loading with flexible object types
• Configurable simulation parameters via INI file
• Realistic VAV control algorithms and environmental modeling
• Compatible with YABE, VTS, and other BACnet browsers

Usage:
    python virtual_device.py [--config virtual_device.ini] [--points points.csv]
"""

import argparse
import asyncio
import configparser
import csv
import logging
import math
import random
import socket
import sys
import time
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import warnings

# Completely suppress all logging and warnings BEFORE importing BAC0
warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

# Set root logger to suppress everything
root_logger = logging.getLogger()
root_logger.disabled = True

import BAC0

# Silence BAC0 immediately after import
BAC0.log_level('silence')

# Helper function for safe emoji printing
def safe_print(message):
    """Print message with emoji fallback for encoding issues"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Remove emoji characters for ASCII-only consoles
        import re
        ascii_message = re.sub(r'[^\x00-\x7F]+', '', message)
        print(ascii_message.strip())

from BAC0.core.devices.local.factory import (
    analog_input, analog_output, analog_value,
    binary_input, binary_output, binary_value,
    multistate_input, multistate_output, multistate_value
)

# ──────────────── CLI ────────────────────────────────────────────────────────
p = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description="Virtual BACnet/IP Device - loads points from CSV with realistic simulation",
)
p.add_argument("-a", "--address", help="e.g. 192.168.88.10/24 (overrides config)")
p.add_argument("--port", type=int, help="UDP port (overrides config)")
p.add_argument("-d", "--deviceId", type=int, help="Device-instance (overrides config)")
p.add_argument("-c", "--config", default="virtual_device.ini", help="Configuration file")
p.add_argument("-p", "--points", help="Points CSV file (overrides config)")
args = p.parse_args()

# ──────────────── Point-helper functions (same as original) ──────────────────
def add_ai(app, inst, name, units, val=0, desc=""):
    analog_input(instance=inst, name=name,
                 properties={"units": units},
                 description=desc or name,
                 presentValue=val
                 ).add_objects_to_application(app)
    return app[name]

def add_ao(app, inst, name, units, val=0, desc=""):
    analog_output(instance=inst, name=name,
                  properties={"units": units},
                  description=desc or name,
                  presentValue=val,
                  relinquish_default=val            # commandable
                  ).add_objects_to_application(app)
    return app[name]

def add_av(app, inst, name, units, val=0, desc=""):
    analog_value(instance=inst, name=name,
                 properties={"units": units},
                 description=desc or name,
                 presentValue=val,
                 relinquish_default=val            # commandable
                 ).add_objects_to_application(app)
    return app[name]

def add_bi(app, inst, name, val=False, desc=""):
    binary_input(instance=inst, name=name,
                 description=desc or name,
                 presentValue=val
                 ).add_objects_to_application(app)
    return app[name]

def add_bo(app, inst, name, val=False, desc=""):
    binary_output(instance=inst, name=name,
                  description=desc or name,
                  presentValue=val,
                  relinquish_default=val            # ✨ makes BO commandable
                  ).add_objects_to_application(app)
    return app[name]

def add_bv(app, inst, name, val=False, desc=""):
    binary_value(instance=inst, name=name,
                 description=desc or name,
                 presentValue=val,
                 relinquish_default=val            # commandable
                 ).add_objects_to_application(app)
    return app[name]

def add_mi(app, inst, name, states, val=1, desc=""):
    multistate_input(instance=inst, name=name,
                     numberOfStates=len(states),
                     description=desc or name,
                     stateText=states,
                     presentValue=val
                     ).add_objects_to_application(app)
    return app[name]

def add_mo(app, inst, name, states, val=1, desc=""):
    multistate_output(instance=inst, name=name,
                      numberOfStates=len(states),
                      description=desc or name,
                      stateText=states,
                      presentValue=val,
                      relinquish_default=val         # commandable
                      ).add_objects_to_application(app)
    return app[name]

def add_mv(app, inst, name, states, val=1, desc=""):
    multistate_value(instance=inst, name=name,
                     numberOfStates=len(states),
                     description=desc or name,
                     stateText=states,
                     presentValue=val,
                     relinquish_default=val          # commandable MV
                     ).add_objects_to_application(app)
    return app[name]

# ──────────────── Auto IP Detection Function ────────────────────────────────
def get_local_ip():
    """Automatically detect the local IP address"""
    try:
        # Connect to a remote address to determine which local interface to use
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return f"{local_ip}/24"
    except Exception:
        # Fallback to localhost if auto-detection fails
        return "127.0.0.1/32"

# ──────────────── CSV Loading Function ───────────────────────────────────────
def load_points_from_csv(csv_file: str):
    """Load point definitions from CSV file"""
    points = []
    
    if not Path(csv_file).exists():
        safe_print(f"⚠ CSV file {csv_file} not found - creating minimal test device")
        return points
    
    try:
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                points.append(row)
        
        safe_print(f"✔ Loaded {len(points)} points from {csv_file}")
        return points
        
    except Exception as e:
        safe_print(f"✗ Error loading CSV: {e}")
        return points

# ──────────────── Object Creation from CSV ──────────────────────────────────
def create_objects_from_csv(app, points):
    """Create BACnet objects from CSV point definitions"""
    created_objects = {}
    total_points = len(points)
    failed_count = 0
    failed_objects = []  # Track failed objects for detailed reporting
    
    if total_points == 0:
        return created_objects
    
    safe_print(f"🔧 Creating {total_points} BACnet objects...")
    
    # Object type mapping
    object_type_map = {
        'Analog Input': 'analogInput',
        'Analog Output': 'analogOutput', 
        'Analog Value': 'analogValue',
        'Binary Input': 'binaryInput',
        'Binary Output': 'binaryOutput',
        'Binary Value': 'binaryValue',
        'Multi State Input': 'multistateInput',
        'Multi State Output': 'multistateOutput',
        'Multi State Value': 'multistateValue',
        # Handle various case versions from CSV
        'Multistate Input': 'multistateInput',
        'Multistate Output': 'multistateOutput',
        'Multistate Value': 'multistateValue',
        'multistateinput': 'multistateInput',
        'multistateoutput': 'multistateOutput',
        'multistatevalue': 'multistateValue'
    }
    
    for i, point in enumerate(points):
        try:
            # Show progress every 10 objects
            if i % 10 == 0 or i == total_points - 1:
                progress = int((i + 1) / total_points * 20)  # 20 character progress bar
                bar = "=" * progress + "-" * (20 - progress)  # Use ASCII chars for compatibility
                percent = int((i + 1) / total_points * 100)
                # For subprocess compatibility, use newlines instead of carriage returns
                if sys.stdout.isatty():
                    # Terminal output - use carriage return
                    try:
                        print(f"\r🔧 Creating objects... [{bar}] {percent}% ({i+1}/{total_points})", end="", flush=True)
                    except UnicodeEncodeError:
                        print(f"\rCreating objects... [{bar}] {percent}% ({i+1}/{total_points})", end="", flush=True)
                else:
                    # Subprocess output - use newlines for proper buffering
                    safe_print(f"Creating objects... [{bar}] {percent}% ({i+1}/{total_points})")
            
            object_type = point['Type']
            instance = int(point['Instance'])
            name = point['Name']
            units = 'noUnits'  # Not in CSV, default value
            description = point.get('Description', name)
            
            # Handle duplicate names by making them unique
            original_name = name
            counter = 1
            while name in created_objects:
                name = f"{original_name}_{counter}"
                counter += 1
            
            # Get initial value with safe conversion
            try:
                val_str = point.get('PresentValue', '0').replace(' %', '').replace(' CFM', '').replace(' F', '').replace(' GPM', '').replace(' PSI', '').split()[0]
                initial_val = float(val_str)
            except (ValueError, TypeError, IndexError):
                initial_val = 0.0
            
            bac_object_type = object_type_map.get(object_type, object_type.lower().replace(' ', ''))
            
            # Create object based on type using the same helper functions
            if bac_object_type == 'analogInput':
                obj = add_ai(app, instance, name, units, initial_val, description)
                created_objects[name] = obj
                
            elif bac_object_type == 'analogOutput':
                obj = add_ao(app, instance, name, units, initial_val, description)
                created_objects[name] = obj
                
            elif bac_object_type == 'analogValue':
                obj = add_av(app, instance, name, units, initial_val, description)
                created_objects[name] = obj
                
            elif bac_object_type == 'binaryInput':
                bool_val = bool(initial_val)
                obj = add_bi(app, instance, name, bool_val, description)
                created_objects[name] = obj
                
            elif bac_object_type == 'binaryOutput':
                bool_val = bool(initial_val)
                obj = add_bo(app, instance, name, bool_val, description)
                created_objects[name] = obj
                
            elif bac_object_type == 'binaryValue':
                bool_val = bool(initial_val)
                obj = add_bv(app, instance, name, bool_val, description)
                created_objects[name] = obj
                
            elif bac_object_type in ['multistateInput', 'multistateOutput', 'multistateValue']:
                # Default states if not specified
                states = ["State1", "State2", "State3", "State4"]
                int_val = max(1, int(initial_val))
                
                if bac_object_type == 'multistateInput':
                    obj = add_mi(app, instance, name, states, int_val, description)
                elif bac_object_type == 'multistateOutput':
                    obj = add_mo(app, instance, name, states, int_val, description)
                else:  # multistateValue
                    obj = add_mv(app, instance, name, states, int_val, description)
                    
                created_objects[name] = obj
            
            else:
                failed_count += 1
                failed_objects.append({
                    'instance': instance,
                    'name': name,
                    'type': object_type,
                    'error': f"Unsupported object type: {object_type} (mapped to: {bac_object_type})"
                })
                
        except Exception as e:
            failed_count += 1
            failed_objects.append({
                'instance': point.get('Instance', 'Unknown'),
                'name': point.get('Name', 'Unknown'),
                'type': point.get('Type', 'Unknown'),
                'error': str(e)
            })
    
    print()  # New line after progress bar
    
    if failed_count > 0:
        safe_print(f"✔ Successfully created {len(created_objects)} BACnet objects ({failed_count} failed)")
        
        # Show detailed error information for failed objects
        safe_print(f"\n❌ FAILED OBJECTS ({failed_count} total):")
        safe_print("-" * 50)
        
        # Group by error type for better readability
        error_groups = {}
        for obj in failed_objects:
            error_key = obj['error']
            if error_key not in error_groups:
                error_groups[error_key] = []
            error_groups[error_key].append(obj)
        
        for error, objects in error_groups.items():
            safe_print(f"\n🔸 Error: {error}")
            for obj in objects[:5]:  # Show first 5 of each error type
                safe_print(f"   • Instance {obj['instance']}: {obj['name']} ({obj['type']})")
            if len(objects) > 5:
                safe_print(f"   ... and {len(objects) - 5} more with this error")
    else:
        safe_print(f"✔ Successfully created {len(created_objects)} BACnet objects")
    
    return created_objects

# ──────────────── Main async task ────────────────────────────────────────────
async def main():
    # Load configuration
    config = configparser.ConfigParser()
    config.read(args.config)
    
    # Get network settings (command line overrides config file, auto-detect if not specified)
    if args.address:
        address = args.address
    elif config.has_option('device', 'address'):
        address = config.get('device', 'address')
    else:
        address = get_local_ip()
        safe_print(f"🔍 Auto-detected IP address: {address}")
    
    port = args.port or config.getint('device', 'port', fallback=47809)
    device_id = args.deviceId or config.getint('device', 'device_id', fallback=2001)
    step = config.getfloat('simulation', 'step_interval', fallback=0.5)
    
    # Get simulation behavior settings
    priority_aware = config.getboolean('simulation', 'priority_aware_simulation', fallback=True)
    
    # Get CSV filename from config or command line
    if args.points:
        points_file = args.points
    elif config.has_option('data', 'points_file'):
        points_file = config.get('data', 'points_file')
    else:
        points_file = "points.csv"
    
    # Create BACnet application (all logging already suppressed)
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        app = BAC0.lite(ip=address, port=port, deviceId=device_id)
    
    # Load and create objects from CSV
    points = load_points_from_csv(points_file)
    
    # Suppress all warnings during object creation
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with redirect_stderr(StringIO()):
            objects = create_objects_from_csv(app, points)
    
    safe_print(f"✔ Virtual BACnet device {device_id} on {address.split('/')[0]}:{port}")
    safe_print(f"✔ Running with {len(objects)} objects from {points_file}")
    safe_print(f"🚀 Device is READY and monitoring - discoverable in YABE/VTS")
    safe_print(f"📡 Broadcasting on network {address} - Port: {port} - Device ID: {device_id}")
    
    # ────────────── Simulation constants ─────────────────────────────────────
    STEP = step
    OUTDOOR_CYCLE_S = config.getint('environment', 'outdoor_temp_cycle_minutes', fallback=20) * 60
    
    # ────────────── Main simulation loop ─────────────────────────────────────
    while True:
        now = time.time()
        
        # Simulation with proper BACnet priority handling
        for name, obj in objects.items():
            try:
                if not hasattr(obj, 'presentValue'):
                    continue
                    
                # Get current value
                current_val = obj.presentValue
                
                # Determine object type from BAC0 object
                obj_type = str(type(obj).__name__).lower()
                
                # Check if this is an input object (should always update)
                is_input = ('input' in obj_type or 
                           obj_type in ['analoginput', 'binaryinput', 'multistateinput'])
                
                # Check if this is an output/value object (commandable - check priority)
                is_commandable = ('output' in obj_type or 'value' in obj_type or
                                obj_type in ['analogoutput', 'binaryoutput', 'multistateoutput',
                                           'analogvalue', 'binaryvalue', 'multistatevalue'])
                
                # For inputs, always update based on simulation
                if is_input:
                    should_update = True
                    
                # For commandable objects, behavior depends on priority_aware setting
                elif is_commandable:
                    if priority_aware:
                        # Only update if priority 16 is active (proper BACnet behavior)
                        should_update = False
                        try:
                            # Check if object has priority array and if priority 16 is active
                            if hasattr(obj, 'priorityArray'):
                                priority_array = obj.priorityArray
                                # If all higher priorities (1-15) are null, then priority 16 is active
                                higher_priorities_active = any(
                                    priority_array[i] is not None 
                                    for i in range(15)  # priorities 1-15 (0-indexed)
                                )
                                should_update = not higher_priorities_active
                            else:
                                # If no priority array, assume we can update (fallback behavior)
                                should_update = True
                        except Exception:
                            # If priority checking fails, err on the side of not updating outputs
                            should_update = False
                    else:
                        # Legacy behavior - update all commandable objects
                        should_update = True
                else:
                    # Unknown object type, skip
                    should_update = False
                
                # Apply simulation updates only if appropriate
                if should_update:
                    # Add realistic variation based on object name/type
                    if 'Temperature' in name:
                        # Temperature sine wave with small random variation
                        base_temp = 20 + 5 * math.sin(2 * math.pi * now / OUTDOOR_CYCLE_S)
                        obj.presentValue = base_temp + random.uniform(-1, 1)
                        
                    elif 'Humidity' in name:
                        # Humidity random walk
                        new_val = max(20, min(80, current_val + random.uniform(-0.5, 0.5)))
                        obj.presentValue = new_val
                        
                    elif 'Airflow' in name or 'Flow' in name:
                        # Airflow with some variation
                        base_flow = 100 + 50 * math.sin(2 * math.pi * now / (OUTDOOR_CYCLE_S * 2))
                        obj.presentValue = max(0, base_flow + random.uniform(-10, 10))
                        
                    elif 'Pressure' in name:
                        # Pressure variation
                        obj.presentValue = max(0, current_val + random.uniform(-0.1, 0.1))
                        
                    elif 'multistate' in obj_type.lower():
                        # For multistate objects, occasionally change state
                        if random.random() < 0.001:  # 0.1% chance per step
                            try:
                                num_states = obj.numberOfStates if hasattr(obj, 'numberOfStates') else 4
                                new_state = random.randint(1, num_states)
                                obj.presentValue = new_state
                            except Exception:
                                pass
                        
                    elif 'binary' in obj_type.lower():
                        # For binary objects, occasionally flip state
                        if random.random() < 0.0005:  # 0.05% chance per step
                            obj.presentValue = 'active' if obj.presentValue == 'inactive' else 'inactive'
                        
            except Exception as e:
                # Log which object failed for debugging
                if hasattr(obj, 'objectName'):
                    safe_print(f"⚠️ Simulation error for {obj.objectName}: {e}")
                pass  # Skip objects that can't be updated
        
        await asyncio.sleep(STEP)

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(main()) 