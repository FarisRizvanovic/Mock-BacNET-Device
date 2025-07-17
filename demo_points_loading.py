#!/usr/bin/env python3
"""
Demo script to show CSV point loading functionality
==================================================

This script demonstrates how the enhanced VAV emulator loads and processes
points from the CSV file without starting the actual BACnet service.
"""

import csv
import re
from pathlib import Path


def parse_present_value(value: str) -> float:
    """Extract numeric value from CSV present value strings"""
    if not value or value == '—':
        return 0.0
    
    value = str(value).strip()
    
    # Handle multistate values like "[1] Cooling"
    match = re.search(r'\[(\d+)\]', value)
    if match:
        return float(match.group(1))
    
    # Handle numeric values with units like "72.9 °F" or "100 %"
    match = re.search(r'(-?\d+(?:\.\d+)?)', value)
    if match:
        return float(match.group(1))
    
    return 0.0


def parse_multistate_states(description: str) -> list:
    """Parse multistate description to extract state text list"""
    if not description:
        return ["State1", "State2"]
    
    # Look for patterns like "[1]=State1, [2]=State2, ..."
    states = []
    matches = re.findall(r'\[(\d+)\]=([^,\]]+)', description)
    if matches:
        # Sort by state number and extract state text
        sorted_matches = sorted(matches, key=lambda x: int(x[0]))
        states = [match[1].strip() for match in sorted_matches]
    
    return states if states else ["State1", "State2"]


def determine_units(name: str, present_value_str: str) -> str:
    """Determine appropriate units based on point name and value"""
    name_lower = name.lower()
    pv_lower = str(present_value_str).lower()
    
    if 'temperature' in name_lower or 'temp' in name_lower:
        if '°f' in pv_lower or 'fahrenheit' in pv_lower:
            return 'degreesFahrenheit'
        return 'degreesCelsius'
    elif 'flow' in name_lower or 'cfm' in pv_lower:
        return 'cubicFeetPerMinute'
    elif 'percent' in name_lower or '%' in pv_lower:
        return 'percent'
    elif 'humidity' in name_lower:
        return 'percentRelativeHumidity'
    elif 'pressure' in name_lower:
        return 'pascals'
    elif 'speed' in name_lower:
        return 'percent'
    else:
        return 'noUnits'


def demo_csv_loading(csv_file: str = "points.csv"):
    """Demonstrate loading and parsing the CSV file"""
    print("="*70)
    print("ENHANCED VAV EMULATOR - CSV POINT LOADING DEMO")
    print("="*70)
    
    # Check if file exists
    points_path = Path(csv_file)
    if not points_path.exists():
        print(f"❌ Points file not found: {csv_file}")
        return
    
    print(f"✓ Loading points from: {csv_file}")
    print()
    
    # Load and process points
    points_by_type = {}
    total_points = 0
    
    with open(points_path, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            obj_type = row['Type'].strip()
            instance = int(row['Instance'])
            name = row['Name'].strip()
            present_value_str = row['PresentValue']
            description = row.get('Description', '').strip()
            
            present_value = parse_present_value(present_value_str)
            units = determine_units(name, present_value_str)
            
            # Group by object type
            if obj_type not in points_by_type:
                points_by_type[obj_type] = []
            
            point_info = {
                'instance': instance,
                'name': name,
                'present_value': present_value,
                'present_value_str': present_value_str,
                'units': units,
                'description': description
            }
            
            # Add multistate info if applicable
            if 'Multi State' in obj_type:
                point_info['states'] = parse_multistate_states(description)
            
            points_by_type[obj_type].append(point_info)
            total_points += 1
    
    # Display results
    print(f"📊 LOADED {total_points} TOTAL POINTS")
    print("="*70)
    
    for obj_type, points in points_by_type.items():
        print(f"\n🔹 {obj_type.upper()} ({len(points)} objects)")
        print("-" * (len(obj_type) + 15))
        
        for point in points[:3]:  # Show first 3 of each type
            print(f"   Instance {point['instance']:3d}: {point['name']}")
            print(f"                    Value: {point['present_value_str']}")
            print(f"                    Units: {point['units']}")
            if 'states' in point and point['states']:
                print(f"                    States: {', '.join(point['states'][:3])}...")
            print()
        
        if len(points) > 3:
            print(f"   ... and {len(points) - 3} more {obj_type.lower()} objects")
            print()
    
    # Check for missing object types
    print("\n📋 MISSING OBJECT TYPE ANALYSIS")
    print("-" * 35)
    
    all_types = {'Analog Input', 'Analog Output', 'Analog Value',
                 'Binary Input', 'Binary Output', 'Binary Value',
                 'Multi State Input', 'Multi State Output', 'Multi State Value'}
    
    existing_types = set(points_by_type.keys())
    missing_types = all_types - existing_types
    
    if missing_types:
        print("Missing object types (will be auto-generated if enabled in INI):")
        for missing_type in sorted(missing_types):
            print(f"   • {missing_type}")
    else:
        print("✓ All standard object types are present in CSV")
    
    print("\n🔧 SIMULATION FEATURES")
    print("-" * 25)
    print("The enhanced emulator will provide:")
    print("• Realistic temperature cycles for outdoor sensors")
    print("• Space temperature drift simulation")
    print("• Airflow variations with noise")
    print("• Humidity random walk")
    print("• Binary input state changes")
    print("• Multistate transitions")
    print("• Output changes for priority 16 writes")
    print("• Environmental modeling")
    
    print("\n🚀 NEXT STEPS")
    print("-" * 15)
    print("1. Configure vav.ini for your network settings")
    print("2. Run: python virtual_vav_device.py")
    print("3. Connect with a BACnet client (VTS, YABE, etc.)")
    print("4. Monitor realistic point behavior")
    print("5. Test priority array writes")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    demo_csv_loading() 