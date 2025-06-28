import argparse, asyncio, math, random, time
import BAC0
from BAC0.core.devices.local.factory import (
    analog_input, analog_output, binary_output, multistate_input
)

# ------------------------ CLI --------------------------------------------
p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
p.add_argument("-a", "--address", required=True, help="e.g. 192.168.68.107/24")
p.add_argument("-p", "--port", type=int, default=47809, help="UDP port")
p.add_argument("-d", "--deviceId", type=int, default=2001, help="Device-ID")
p.add_argument("-s", "--step", type=float, default=0.5, help="Sim step (s)")
args = p.parse_args()

# -------------------- point helpers --------------------------------------
def add_ai(app, inst, name, units, val=0, desc=""):
    analog_input(instance=inst, name=name,
                 properties={"units": units},
                 description=desc or name, presentValue=val
                 ).add_objects_to_application(app)
    return app[name]

def add_ao(app, inst, name, units, val=0, desc=""):
    analog_output(instance=inst, name=name,
                  properties={"units": units},
                  description=desc or name, presentValue=val,
                  relinquish_default=val
                  ).add_objects_to_application(app)
    return app[name]

def add_bo(app, inst, name, val=False):
    binary_output(instance=inst, name=name, presentValue=val
                  ).add_objects_to_application(app)
    return app[name]

def add_mi(app, inst, name, states, val=1):
    multistate_input(instance=inst, name=name,
                     numberOfStates=len(states), stateText=states,
                     presentValue=val
                     ).add_objects_to_application(app)
    return app[name]

# ---------------------- async main ---------------------------------------
async def main():
    app = BAC0.lite(ip=args.address, port=args.port, deviceId=args.deviceId)

    # writable
    damper        = add_ao(app, 1, "Damper",         "percent", 0)
    damper_hot    = add_ao(app, 2, "DamperHotDeck",  "percent", 0)
    damper_cold   = add_ao(app, 3, "DamperColdDeck", "percent", 0)
    reheat        = add_ao(app, 4, "Reheat",         "percent", 0)
    heat_sp       = add_ao(app, 5, "HeatSetpoint",   "degreesCelsius", 21)
    cool_sp       = add_ao(app, 6, "CoolSetpoint",   "degreesCelsius", 24)
    occupied_cmd  = add_bo(app, 1, "OccupiedCommand", True)

    # sensors
    inlet_temp         = add_ai(app,  1, "InletTemperature",         "degreesCelsius", 12)
    inlet_temp_hot     = add_ai(app,  2, "InletTemperatureHotDeck",  "degreesCelsius", 30)
    inlet_temp_cold    = add_ai(app,  3, "InletTemperatureColdDeck", "degreesCelsius", 12)
    discharge_temp     = add_ai(app,  4, "DischargeTemperature",     "degreesCelsius", 12)
    space_temp         = add_ai(app,  5, "SpaceTemperature",         "degreesCelsius", 22)
    space_setpoint     = add_ai(app,  6, "SpaceSetpoint",            "degreesCelsius", 22)
    airflow            = add_ai(app,  7, "Airflow",                  "litersPerSecond", 0)
    airflow_hot        = add_ai(app,  8, "AirflowHotDeck",           "litersPerSecond", 0)
    airflow_cold       = add_ai(app,  9, "AirflowColdDeck",          "litersPerSecond", 0)
    humidity           = add_ai(app, 10, "Humidity",                 "percentRelativeHumidity", 40)
    max_airflow        = add_ai(app, 11, "MaximumAirflow",           "litersPerSecond", 400)
    outdoor_temp       = add_ai(app, 12, "OutdoorTemperature",       "degreesCelsius", 15)

    op_status          = add_mi(app, 1, "OperationStatus",
                                ["OK", "Fault", "Off"], 1)

    print(f"✔ VAV {args.deviceId} running on {args.address.split('/')[0]}:{args.port}")

    # --- dynamic behaviour parameters -----------------------------------
    STEP = args.step
    BAND, GAIN, ROOM_G = 0.5, 4.0, 0.04
    COOL, HEAT = 12.0, 30.0

    OUTDOOR_CYCLE_S = 20*60           # one “day” every 20 min
    FAULT_MEAN_S   = 120             # mean time between brief “faults”
    MAX_FLOW_REFRESH_S = 3600        # hourly
    next_fault = time.time() + random.expovariate(1/FAULT_MEAN_S)
    next_max  = time.time() + MAX_FLOW_REFRESH_S

    tick = 0
    last_occ = occupied_cmd.presentValue

    while True:
        # --- control loop for primary dampers ---------------------------
        sp, t = space_setpoint.presentValue, space_temp.presentValue
        err   = sp - t
        if err < -BAND:
            damper.presentValue   = min(100, damper.presentValue + (-err)*GAIN)
            reheat.presentValue   = 0
        elif err > BAND:
            damper.presentValue   = max(0, damper.presentValue - err*GAIN)
            reheat.presentValue   = min(100, err*GAIN*2)
        else:
            reheat.presentValue   = 0
            damper.presentValue  += (30 - damper.presentValue)*0.1
        damper.presentValue = max(0, min(100, damper.presentValue))

        # derive deck‐specific points
        damper_hot.presentValue  = reheat.presentValue
        damper_cold.presentValue = damper.presentValue
        airflow.presentValue     = damper.presentValue * 1.2
        airflow_hot.presentValue = damper_hot.presentValue * 1.0
        airflow_cold.presentValue= damper_cold.presentValue * 1.0

        discharge_temp.presentValue = (
            COOL*(1 - reheat.presentValue/100) +
            HEAT*(reheat.presentValue/100)
        )
        inlet_temp.presentValue += (discharge_temp.presentValue -
                                    inlet_temp.presentValue)*0.05

        # room thermal response
        t += ((discharge_temp.presentValue - t) *
              (airflow.presentValue/120) * ROOM_G)
        space_temp.presentValue = t

        # --- environment / random variation -----------------------------
        now = time.time()

        # outdoor temperature sine wave
        outdoor_temp.presentValue = (
            21 + 6*math.sin(2*math.pi * now / OUTDOOR_CYCLE_S)
        )

        # humidity random walk
        humidity.presentValue = max(25, min(75,
            humidity.presentValue + random.uniform(-0.2, 0.2)))

        # occasional operation fault blip
        if now >= next_fault:
            op_status.presentValue = 2  # Fault
            await asyncio.sleep(5)
            op_status.presentValue = 1  # OK
            next_fault = now + random.expovariate(1/FAULT_MEAN_S)

        # refresh max airflow hourly
        if now >= next_max:
            max_airflow.presentValue = random.uniform(350, 450)
            next_max = now + MAX_FLOW_REFRESH_S

        # shift setpoint on occupancy toggle
        if occupied_cmd.presentValue != last_occ:
            space_setpoint.presentValue += 0.1 if occupied_cmd.presentValue else -0.1
            last_occ = occupied_cmd.presentValue

        await asyncio.sleep(STEP)
        tick += 1

# -------------------- run -------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
