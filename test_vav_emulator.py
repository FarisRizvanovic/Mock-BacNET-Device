#!/usr/bin/env python3
"""
Test script for the Enhanced Virtual VAV BACnet Device Simulator
===============================================================

This script demonstrates how to use the enhanced VAV emulator and provides
a simple way to test that everything is working correctly.

Usage:
    python test_vav_emulator.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from virtual_vav_device import VAVSimulator


async def test_simulator():
    """Test the VAV simulator with basic functionality"""
    print("="*60)
    print("Enhanced Virtual VAV BACnet Device Simulator Test")
    print("="*60)
    
    # Check if required files exist
    config_file = Path("vav.ini")
    points_file = Path("points.csv")
    
    if not config_file.exists():
        print(f"❌ Configuration file not found: {config_file}")
        return False
        
    if not points_file.exists():
        print(f"❌ Points file not found: {points_file}")
        return False
    
    print(f"✓ Configuration file found: {config_file}")
    print(f"✓ Points file found: {points_file}")
    
    try:
        # Create simulator instance
        print("\n📡 Initializing VAV simulator...")
        simulator = VAVSimulator(str(config_file), str(points_file))
        
        # Start the simulator for a short test period
        print("🚀 Starting BACnet device...")
        
        # Create a task for the simulator
        sim_task = asyncio.create_task(simulator.start())
        
        # Let it run for 10 seconds to test
        print("⏱️  Running test simulation for 10 seconds...")
        try:
            await asyncio.wait_for(sim_task, timeout=10.0)
        except asyncio.TimeoutError:
            print("✓ Test completed successfully!")
            sim_task.cancel()
            
            # Give a moment for cleanup
            try:
                await sim_task
            except asyncio.CancelledError:
                pass
                
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def print_usage_instructions():
    """Print instructions for using the VAV emulator"""
    print("\n" + "="*60)
    print("HOW TO USE THE ENHANCED VAV EMULATOR")
    print("="*60)
    
    print("\n1. BASIC USAGE:")
    print("   python virtual_vav_device.py")
    print("   (Uses default vav.ini and points.csv)")
    
    print("\n2. CUSTOM FILES:")
    print("   python virtual_vav_device.py --config my_config.ini --points my_points.csv")
    
    print("\n3. CONFIGURATION:")
    print("   Edit vav.ini to customize:")
    print("   • Device IP address and port")
    print("   • Simulation parameters")
    print("   • Control algorithms")
    print("   • Environmental settings")
    
    print("\n4. POINTS DEFINITION:")
    print("   Edit points.csv to define BACnet objects:")
    print("   • Analog Input/Output/Value")
    print("   • Binary Input/Output/Value") 
    print("   • Multistate Input/Output/Value")
    
    print("\n5. FEATURES:")
    print("   ✓ Loads all points from CSV")
    print("   ✓ Adds missing object types for testing")
    print("   ✓ Realistic simulation of input values")
    print("   ✓ Output changes for priority 16 writes")
    print("   ✓ Environmental simulation (outdoor temp, humidity)")
    print("   ✓ Configurable via INI file")
    
    print("\n6. MONITORING:")
    print("   Use any BACnet client to read/write objects")
    print("   Example: VTS, YABE, or BACnet browser")
    
    print("\n" + "="*60)


async def main():
    """Main test function"""
    print("Starting Enhanced VAV Emulator Test...\n")
    
    # Run the test
    success = await test_simulator()
    
    if success:
        print("\n🎉 All tests passed!")
        print_usage_instructions()
    else:
        print("\n💥 Tests failed. Please check the error messages above.")
        print("\nCommon issues:")
        print("• Missing vav.ini or points.csv files")
        print("• BACnet port already in use")
        print("• Missing BAC0 library (pip install BAC0)")
        print("• Network interface issues")
        
    return success


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1) 