# Virtual VAV BACnet Device Simulator

A Python-based BACnet/IP device simulator that emulates a Variable Air Volume (VAV) unit with realistic control behavior. This simulator loads point definitions from CSV files and creates fully functional BACnet objects that can be discovered and controlled by any BACnet client software.

## Features

- 🔧 **CSV Point Loading**: Automatically loads BACnet objects from CSV files
- 🌐 **Auto IP Detection**: Automatically detects your network interface
- 📊 **Multiple Object Types**: Supports Analog, Binary, and Multistate objects (Input, Output, Value)
- 🎛️ **Realistic Simulation**: Implements VAV control algorithms with temperature, airflow, and humidity simulation
- ⚙️ **Configurable**: Extensive configuration options via INI file
- 🔍 **BACnet Discovery**: Compatible with YABE, VTS, and other BACnet browsers

## Quick Start

### Prerequisites

```bash
pip install BAC0
```

### Basic Usage

```bash
# Run with default settings (auto-detects IP, uses port 47809)
python virtual_vav_device.py

# Run with custom CSV file
python virtual_vav_device.py --points my_points.csv

# Run with specific network settings
python virtual_vav_device.py -a 192.168.1.100/24 --port 47808 -d 2001
```

### Expected Output

```
🔍 Auto-detected IP address: 192.168.0.206/24
✔ Loaded 42 points from points.csv
Creating analogInput 43: Air Valve Position Command
Creating analogOutput 25: Minimum Flow Setpoint Multiplier BAS
...
✔ Successfully created 1139 BACnet objects
✔ Virtual VAV device 3001 on 192.168.0.206:47809
✔ Running with 1139 objects from CSV
```

## Command Line Options

| Option           | Description                 | Example               |
| ---------------- | --------------------------- | --------------------- |
| `-a, --address`  | IP address with subnet mask | `-a 192.168.1.100/24` |
| `--port`         | UDP port number             | `--port 47808`        |
| `-d, --deviceId` | BACnet device instance ID   | `-d 2001`             |
| `-c, --config`   | Configuration file path     | `-c my_config.ini`    |
| `-p, --points`   | Points CSV file path        | `-p my_points.csv`    |

## Configuration File (vav.ini)

### [device] Section

Controls basic device settings:

```ini
[device]
port = 47809                    # UDP port for BACnet communication
device_id = 3001               # BACnet device instance ID (must be unique on network)
device_name = Virtual VAV Unit  # Device name visible in BACnet browsers
device_description = Enhanced Virtual VAV BACnet Device with CSV Point Loading
```

**Notes:**

- `port`: Standard BACnet port is 47808, but use different ports to avoid conflicts
- `device_id`: Must be unique on your BACnet network (1-4194303)
- IP address is auto-detected but can be overridden with command line `-a` option

### [simulation] Section

Controls simulation behavior:

```ini
[simulation]
step_interval = 0.5              # Simulation update interval in seconds
ai_variation_range = 0.15        # Random variation for analog inputs (±15%)
ao_priority16_variation = 0.25   # Variation for analog outputs with priority 16
binary_flip_probability = 0.01  # Probability of binary inputs changing state per step
multistate_change_interval = 20 # Seconds between multistate input changes
temperature_drift_rate = 0.05   # Rate of temperature changes
flow_variation_factor = 0.1     # Airflow variation factor
```

**Parameter Details:**

- `step_interval`: Lower values = more responsive simulation, higher CPU usage
- `ai_variation_range`: Simulates sensor noise and real-world fluctuations
- `ao_priority16_variation`: Simulates automatic control adjustments
- `binary_flip_probability`: Simulates alarm conditions and status changes
- `multistate_change_interval`: How often operation modes change
- `temperature_drift_rate`: How quickly temperatures respond to control changes
- `flow_variation_factor`: Natural airflow fluctuations

### [environment] Section

Controls environmental simulation:

```ini
[environment]
outdoor_temp_cycle_minutes = 20    # Duration of outdoor temperature cycle
outdoor_temp_base = 21.0          # Base outdoor temperature (°C)
outdoor_temp_amplitude = 6.0      # Temperature swing (±6°C from base)
```

**Environmental Simulation:**

- Creates realistic daily temperature cycles
- Affects indoor temperature simulation
- Base temperature represents average daily temperature
- Amplitude creates morning/evening temperature swings

## CSV Point Format

The CSV file should contain BACnet object definitions with these columns:

| Column       | Description             | Example                                             |
| ------------ | ----------------------- | --------------------------------------------------- |
| Type         | BACnet object type      | `Analog Input`, `Binary Output`, `Multistate Value` |
| Instance     | Object instance number  | `43`, `25`, `101`                                   |
| Name         | Object name             | `Air Valve Position Command`                        |
| PresentValue | Initial value           | `100 %`, `635.8 CFM`, `True`                        |
| Override     | Priority array override | (optional)                                          |
| Description  | Object description      | (optional)                                          |

### Supported Object Types

- **Analog Input** - Read-only sensor values
- **Analog Output** - Controllable analog setpoints
- **Analog Value** - General analog values
- **Binary Input** - Read-only digital status
- **Binary Output** - Controllable digital commands
- **Binary Value** - General binary values
- **Multistate Input** - Read-only multi-position status
- **Multistate Output** - Controllable multi-position commands
- **Multistate Value** - General multi-position values

### CSV Example

```csv
Type,Instance,Name,PresentValue,Override,Description
Analog Input,43,Air Valve Position Command,100 %,,
Analog Output,25,Minimum Flow Setpoint Multiplier BAS,1.0,,
Binary Input,27,Air Valve Control Action Active,False,,
Multistate Value,18,Communication Status,1,,
```

## Connecting with BACnet Browsers

### YABE (Yet Another BACnet Explorer)

1. **Auto Discovery:**

   - Open YABE
   - Press F5 or File → Rescan Network
   - Look for device ID 3001

2. **Manual Add:**
   - File → Add Device
   - IP: `192.168.0.206` (or your detected IP)
   - Port: `47809`
   - Device Instance: `3001`

### VTS (Visual Test Shell)

1. Configure network interface to match your subnet
2. Scan for devices or add manually
3. Browse object hierarchy

### Other BACnet Clients

- Use detected IP address and port 47809
- Device instance ID is configurable in vav.ini
- Supports all standard BACnet services (Read/Write Property, Subscribe COV, etc.)

## Simulation Features

### Temperature Control

- PI controller simulation for space temperature
- Reheat valve control based on temperature error
- Damper position adjustments
- Realistic thermal response

### Airflow Management

- Variable airflow based on damper positions
- Hot and cold deck airflow calculations
- Maximum airflow limitations
- Flow measurement simulation

### Environmental Modeling

- Outdoor temperature cycles
- Humidity random walk simulation
- Seasonal variations
- Indoor/outdoor temperature relationships

### Control Logic

- Occupancy-based setpoint adjustments
- Heat/cool mode switching
- Override and priority handling
- Fault condition simulation

## Troubleshooting

### Device Not Visible in YABE

1. **Check IP Address**: Ensure auto-detected IP is on same subnet as YABE
2. **Firewall**: Windows firewall may block UDP traffic on port 47809
3. **Network Interface**: Try specifying IP manually: `-a YOUR_IP/24`
4. **Port Conflicts**: Change port if 47809 is in use: `--port 47810`

### Object Creation Errors

1. **CSV Format**: Verify CSV headers match exactly: `Type,Instance,Name,PresentValue,Override,Description`
2. **Instance Numbers**: Ensure instance numbers are unique and within BACnet limits (1-4194303)
3. **Object Types**: Check spelling of object types (case-sensitive)

### Performance Issues

1. **Step Interval**: Increase `step_interval` in vav.ini for less CPU usage
2. **Object Count**: Large CSV files (1000+ objects) may cause slower startup
3. **Simulation**: Reduce variation ranges to minimize calculation overhead

### Network Issues

1. **Multiple Interfaces**: Specify exact IP if auto-detection picks wrong interface
2. **VPN**: Disable VPN if causing network detection issues
3. **Subnet**: Ensure BACnet browser is on same subnet as device

## Development

### Adding New Object Types

Extend the `object_type_map` in `create_objects_from_csv()` function.

### Custom Simulation

Modify the simulation loop in `main()` function to add custom control logic.

### Configuration Options

Add new settings to vav.ini and update the configuration parsing section.

## License

This project is provided as-is for educational and testing purposes.

## Support

For issues or questions:

1. Check this README for troubleshooting steps
2. Verify CSV format and configuration settings
3. Test with minimal CSV file to isolate issues
4. Check Windows firewall and network settings
