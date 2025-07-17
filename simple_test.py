#!/usr/bin/env python3
"""
Simple test script to isolate BAC0 factory function issues
"""

import BAC0
from BAC0.core.devices.local.factory import analog_input

def test_simple_analog_input():
    """Test creating a simple analog input without our complex setup"""
    try:
        print("Testing BAC0 and factory imports...")
        print(f"BAC0 version: {BAC0.__version__ if hasattr(BAC0, '__version__') else 'Unknown'}")
        
        print("Creating BAC0 lite application...")
        app = BAC0.lite(ip='192.168.68.105/24', port=47810)
        
        print("Testing simple analog input creation...")
        obj = analog_input(
            instance=1,
            name="TestAnalogInput",
            presentValue=25.0,
            description="Simple test object"
        )
        
        print("Adding object to application...")
        obj.add_objects_to_application(app)
        
        print("SUCCESS: Simple analog input created successfully!")
        
        # Clean up
        app.disconnect()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        if 'app' in locals():
            app.disconnect()
        return False

if __name__ == "__main__":
    test_simple_analog_input() 