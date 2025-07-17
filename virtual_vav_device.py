# ─────────── virtual_vav_device.py ─────────────────────────────────────────
"""
Virtual BACnet/IP VAV device built from a CSV definition.

Usage example
-------------
python virtual_vav_device.py -f vav-4_20250716.csv \
                             -a 192.168.88.10/24 -p 47808 -d 2001 \
                             -c vav.ini
"""
import argparse
import asyncio
import configparser
import itertools
import math
import random
import re
import time
from pathlib import Path
from typing import Dict, List

import pandas as pd
import BAC0
from BAC0.core.devices.local.factory import (
    analog_input, analog_output, analog_value,
    binary_input, binary_output, binary_value,
    multistate_input, multistate_output, multistate_value
)

# ────────────── internal helpers & constants ──────────────────────────────
_OBJ_MAP = {
    'analog input':  analog_input,
    'analog output': analog_output,
    'analog value':  analog_value,
    'binary input':  binary_input,
    'binary output': binary_output,
    'binary value':  binary_value,
    'multi state input':  multistate_input,
    'multi state output': multistate_output,
    'multi state value':  multistate_value,
}

_CORE_TYPES = list(_OBJ_MAP.keys())
_NUMERIC     = re.compile(r'^\s*([-+]?\d*\.?\d+)', re.I)
_PRIORITY_16 = re.compile(r'level\s*16', re.I)

def _parse_val(text: str) -> float | int:
    """Extract numeric or state index from the PresentValue column."""
    if pd.isna(text):
        return 0
    m = _NUMERIC.match(str(text))
    if m:
        return float(m.group(1))
    m = re.match(r'\[\s*(\d+)\s*\]', str(text))
    return int(m.group(1)) if m else 0

def _add_placeholder(app, obj_type: str, inst: int):
    """Guarantee every core object type is represented."""
    fn  = _OBJ_MAP[obj_type]
    fn(instance=inst, name=f'Placeholder {obj_type}',
       description='Does not exist on physical VAV – added for testing.',
       presentValue=0,
       relinquish_default=0 if 'output' in obj_type or 'value' in obj_type else None
    ).add_objects_to_application(app)

# ────────────── CSV → BACnet objects ──────────────────────────────────────
def build_objects(app, df: pd.DataFrame):
    """Create objects; return buckets grouped by behaviour."""
    buckets: Dict[str, List] = {k: [] for k in (
        'ai','ao','av','bi','bo','bv','msi','mso','msv')}
    highest_inst = max(df['Instance'].astype(int).tolist() + [0])

    for _, row in df.iterrows():
        t_raw = str(row['Type']).strip().lower()
        if t_raw not in _OBJ_MAP:
            print(f'⚠ Unknown type: {row["Type"]} – skipped')
            continue
        fn   = _OBJ_MAP[t_raw]
        inst = int(row['Instance'])
        name = str(row['Name']).strip()
        desc = str(row.get('Description', '') or name)
        val  = _parse_val(row.get('PresentValue', 0))

        kwargs = dict(instance=inst, name=name,
                      description=desc, presentValue=val)
        if 'output' in t_raw or 'value' in t_raw:
            kwargs['relinquish_default'] = val  # make commandable

        obj = fn(**kwargs)
        obj.add_objects_to_application(app)

        key = (t_raw
               .replace(' ', '')   # e.g. "multi state input"
               .replace('analog', 'a')
               .replace('binary', 'b')
               .replace('input', 'i')
               .replace('output', 'o')
               .replace('value', 'v'))
        buckets[key].append((obj, row.get('Override', '')))

    # inject placeholders
    for kind in _CORE_TYPES:
        if kind not in df['Type'].str.lower().unique():
            highest_inst += 1
            _add_placeholder(app, kind, highest_inst)

    return buckets

# ────────────── simulation loop ───────────────────────────────────────────
async def simulate(b, step: float, cfg: Dict[str, float]):
    ai_var, ao_var = cfg['ai_var'], cfg['ao_var']
    flip_p, msi_per = cfg['flip_p'], cfg['msi_per']
    msi_clock = 0.0

    while True:
        # Analog & binary inputs
        for (obj, _) in b['ai']:
            obj.presentValue += random.uniform(-ai_var, ai_var)
        for (obj, _) in b['bi']:
            if random.random() < flip_p:
                obj.presentValue = int(not obj.presentValue)

        # Multistate inputs (periodic cycle)
        msi_clock += step
        if msi_clock >= msi_per:
            for (obj, _) in b['msi']:
                obj.presentValue = (int(obj.presentValue or 1) % 5) + 1
            msi_clock = 0.0

        # Drift *outputs* only when Level‑16 is the active writer
        def drift_ok(override: str) -> bool:
            return bool(_PRIORITY_16.search(str(override)))

        for (obj, ov) in b['ao'] + b['av']:
            if drift_ok(ov):
                obj.presentValue += random.uniform(-ao_var, ao_var)
        for (obj, ov) in b['bo'] + b['bv']:
            if drift_ok(ov) and random.random() < flip_p:
                obj.presentValue = int(not obj.presentValue)
        for (obj, ov) in b['mso'] + b['msv']:
            if drift_ok(ov):
                obj.presentValue = (int(obj.presentValue or 1) % 5) + 1

        await asyncio.sleep(step)

# ────────────── configuration helpers ─────────────────────────────────────
def load_ini(path: Path):
    c = configparser.ConfigParser()
    c.read_dict({
        'device': {'step':'0.5'},
        'simulation': {
            'ai_var':'0.2', 'ao_var':'0.3',
            'flip_p':'0.005', 'msi_per':'30'
        }
    })
    if path and path.exists():
        c.read(path)
    return c

# ────────────── main entry point ──────────────────────────────────────────
async def main():
    p = argparse.ArgumentParser(description='Virtual VAV from CSV')
    p.add_argument('-f', '--file',  type=Path, required=True, help='CSV file')
    p.add_argument('-c', '--config',type=Path, help='INI with overrides')
    p.add_argument('-a', '--address',help='192.168.88.10/24')
    p.add_argument('-p', '--port',   type=int, help='UDP port')
    p.add_argument('-d', '--deviceId',type=int, help='Device instance')
    p.add_argument('-s', '--step',   type=float, help='Simulation step (s)')
    args = p.parse_args()

    ini = load_ini(args.config or Path())
    addr = args.address  or ini['device'].get('address', '192.168.88.10/24')
    port = args.port     or ini.getint('device','port', 47808)
    devid= args.deviceId or ini.getint('device','device_id', 2001)
    step = args.step     or ini.getfloat('device','step', 0.5)

    sim_cfg = {
        'ai_var' : ini.getfloat('simulation', 'ai_variation', 0.2),
        'ao_var' : ini.getfloat('simulation', 'ao_variation', 0.3),
        'flip_p' : ini.getfloat('simulation', 'binary_flip_p', 0.005),
        'msi_per': ini.getfloat('simulation', 'msi_period', 30)
    }

    app = BAC0.lite(ip=addr, port=port, deviceId=devid)
    buckets = build_objects(app, pd.read_csv(args.file, encoding='utf-8'))

    print(f'✓ Device {devid} online @ {addr.split("/")[0]}:{port} — '
          f'{sum(len(v) for v in buckets.values())} objects')
    await simulate(buckets, step, sim_cfg)

if __name__ == '__main__':
    asyncio.run(main())
