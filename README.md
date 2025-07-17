# Enhanced Virtual VAV BACnet Device Simulator

A sophisticated BACnet/IP device simulator that emulates a Variable Air Volume (VAV) unit with realistic behavior and comprehensive point simulation.

## Features

✅ **CSV-Based Point Loading**: Load all BACnet objects from a CSV file  
✅ **INI Configuration**: Comprehensive configuration via INI file  
✅ **Missing Object Auto-Generation**: Automatically adds missing object types for testing  
✅ **Realistic Input Simulation**: Intelligent simulation of all input objects  
✅ **Priority 16 Output Simulation**: Output objects change over time if they have write priority 16  
✅ **Environmental Modeling**: Outdoor temperature cycles, humidity variations  
✅ **Sophisticated Control**: Temperature control loops, airflow calculations  
✅ **Comprehensive Logging**: Detailed logging for monitoring and debugging

## Quick Start

1. **Install Dependencies**:

   ```bash
   pip install BAC0
   ```

2. **Run with Default Settings**:

   ```bash
   python virtual_vav_device.py
   ```

3. **Test the Emulator**:
   ```bash
   python test_vav_emulator.py
   ```

## Configuration

### Device Settings (`vav.ini` - [device] section)

- `address`: IP address in CIDR format (e.g., `192.168.1.100/24`)
- `port`: UDP port for BACnet communication (default: 47808)
- `device_id`: BACnet device instance ID (default: 3001)
- `device_name`: Device name visible to BACnet clients
- `device_description`: Device description

### Simulation Settings (`vav.ini` - [simulation] section)

- `step_interval`: Time between simulation steps (seconds)
- `ai_variation_range`: Random variation range for analog inputs
- `ao_priority16_variation`: Variation range for analog outputs with priority 16 writes
- `binary_flip_probability`: Probability of binary inputs changing state
- `multistate_change_interval`: Average time between multistate changes
- `temperature_drift_rate`: Rate of temperature drift simulation
- `flow_variation_factor`: Airflow variation factor

### Environment Settings (`vav.ini` - [environment] section)

- `outdoor_temp_cycle_minutes`: Outdoor temperature cycle period
- `outdoor_temp_base`: Base outdoor temperature
- `outdoor_temp_amplitude`: Temperature swing amplitude
- `humidity_base`: Base humidity level
- `humidity_range`: Humidity variation range

## Point Definition (CSV Format)

The `points.csv` file defines all BACnet objects with the following columns:

| Column       | Description            | Example                                              |
| ------------ | ---------------------- | ---------------------------------------------------- |
| Type         | Object type            | `Analog Input`, `Binary Output`, `Multi State Input` |
| Instance     | Object instance number | `43`, `25`, `18`                                     |
| Name         | Object name            | `Space Temperature Active`                           |
| PresentValue | Initial value          | `72.9 °F`, `[1] Cooling`, `100 %`                    |
| Override     | Override information   | `—` (not used in simulation)                         |
| Description  | Object description     | `[0]=Heating, [1]=Cooling`                           |

### Supported Object Types

- **Analog Input**: Sensor readings (temperature, flow, pressure, etc.)
- **Analog Output**: Control outputs (setpoints, valve positions, etc.)
- **Binary Input**: Status inputs (switch states, alarms, etc.)
- **Binary Output**: Control outputs (on/off commands, etc.)
- **Multi State Input**: Status with multiple states (operation modes, etc.)
- **Multi State Output**: Control with multiple states (mode commands, etc.)

## Simulation Behavior

### Input Objects (Realistic Simulation)

- **Analog Inputs**:
  - Outdoor temperature follows sine wave cycles
  - Space temperature drifts realistically
  - Flow rates vary with noise
  - Humidity random walk
  - Position feedback with small variations
- **Binary Inputs**: Occasional state changes based on probability
- **Multistate Inputs**: Periodic state transitions

### Output Objects (Priority 16 Only)

- **Analog Outputs**: Small variations around current value
- **Binary Outputs**: Occasional state flips
- **Multistate Outputs**: Periodic state changes

### Missing Object Types

If configured in the INI file, the simulator will automatically add missing object types:

- **Analog Value**: If no Analog Value objects exist in CSV
- **Binary Value**: If no Binary Value objects exist in CSV
- **Multistate Value**: If no Multistate Value objects exist in CSV

## Usage Examples

### Basic Usage

```bash
# Use default configuration and points
python virtual_vav_device.py
```

### Custom Configuration

```bash
# Use custom INI and CSV files
python virtual_vav_device.py --config my_vav.ini --points my_points.csv
```

### Testing

```bash
# Run the test script to verify everything works
python test_vav_emulator.py
```

## Monitoring and Control

Use any BACnet client to interact with the simulated device:

- **VTS (Visual Test Shell)**: Professional BACnet testing tool
- **YABE (Yet Another BACnet Explorer)**: Free BACnet browser
- **BACnet Browser**: Various commercial and open-source options

### Example BACnet Operations

- **Read Objects**: Browse and read all simulated points
- **Write Outputs**: Write to analog/binary/multistate outputs
- **Priority Arrays**: Test different priority levels (simulator responds to priority 16)
- **COV Subscriptions**: Monitor change-of-value notifications

## Logging

The simulator provides comprehensive logging:

- Object creation and configuration
- Simulation state changes
- Error conditions and warnings
- Network status

Adjust logging level by modifying the `logging.basicConfig()` call in the code.

## Troubleshooting

### Common Issues

1. **Port Already in Use**: Change port in `vav.ini` if 47808 is occupied
2. **Network Interface**: Ensure correct IP address in CIDR format
3. **Missing Dependencies**: Install BAC0 library (`pip install BAC0`)
4. **CSV Format**: Verify CSV headers match expected format
5. **INI Syntax**: Check INI file for syntax errors

### Error Messages

- Check console output for detailed error messages
- Verify file paths for `vav.ini` and `points.csv`
- Ensure BACnet device ID is unique on network

## Advanced Features

### Custom Simulation Logic

Modify the simulation methods in `VAVSimulator` class:

- `_simulate_analog_input()`: Custom analog input behavior
- `_simulate_binary_input()`: Custom binary input behavior
- `_simulate_multistate_input()`: Custom multistate input behavior

### Additional Object Types

Extend the simulator to support additional BACnet object types by:

1. Adding factory methods in `_add_*()` functions
2. Adding simulation logic in `_simulate_*()` functions
3. Updating CSV parsing for new object types

### Integration

The simulator can be integrated into larger test frameworks or automated testing systems by importing the `VAVSimulator` class and controlling it programmatically.

## Files

- `virtual_vav_device.py`: Main simulator code
- `vav.ini`: Configuration file
- `points.csv`: Point definitions
- `test_vav_emulator.py`: Test script
- `README.md`: This documentation

## License

This project is provided as-is for educational and testing purposes.
