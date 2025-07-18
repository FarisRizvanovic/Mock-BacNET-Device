# Virtual BACnet Device Simulator - Company Guide

## Quick Start

```bash
# Run the GUI interface
python virtual_device_gui.py

# Or run the command-line version directly
python virtual_device.py --config virtual_device.ini
```

## File Purposes

| File                        | Purpose                                                                                                                                                           |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`virtual_device_gui.py`** | **Main GUI application** - Provides graphical interface for configuring and controlling the virtual BACnet device. All settings can be adjusted through the UI.   |
| **`virtual_device.py`**     | **Core device engine** - The actual BACnet device simulator that creates objects from CSV and handles network communication. Can run standalone via command line. |
| **`virtual_device.ini`**    | **Configuration file** - Contains all device settings (IP, port, device ID, simulation parameters). The GUI reads/writes this file to persist settings.           |

## Configuration Flow

```
virtual_device.ini ←→ virtual_device_gui.py → virtual_device.py
     (settings)         (user interface)      (BACnet device)
```

## Requirements

- Python 3.7+
- BAC0 library: `pip install BAC0`
- CSV file with BACnet object definitions (e.g., `points.csv`)

## Usage Notes

- **GUI Mode**: Use `virtual_device_gui.py` for easy configuration and monitoring
- **Headless Mode**: Use `virtual_device.py` directly for server deployments
- **Network**: Device becomes discoverable in YABE, VTS, and other BACnet tools
- **CSV Format**: Must contain columns: `Type,Instance,Name,PresentValue,Override,Description`

## Common Commands

```bash
# Install dependencies
pip install BAC0

# Run with custom config
python virtual_device.py --config my_config.ini

# Run with custom CSV
python virtual_device.py --points my_points.csv

# Run with specific IP/port
python virtual_device.py -a 192.168.1.100 --port 47809
```
