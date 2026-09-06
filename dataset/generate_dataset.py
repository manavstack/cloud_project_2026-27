"""
generate_dataset.py
--------------------
Synthetic dataset generator for the Smart Campus Energy Prediction & Control
System (student3 - Dataset & ML Model owner).

Simulates 15-minute smart-meter readings for 5 campus buildings over 60 days,
including power draw, occupancy, and weather features, plus daily/seasonal
patterns and noise so the data is realistic enough to forecast on.

Output:
    dataset/raw/energy_readings_raw.csv   (untouched simulator output)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

BUILDINGS = [
    {"building_id": "B01_ACADEMIC",  "base_load_kw": 45, "occ_capacity": 800},
    {"building_id": "B02_HOSTEL",    "base_load_kw": 30, "occ_capacity": 500},
    {"building_id": "B03_LIBRARY",   "base_load_kw": 20, "occ_capacity": 300},
    {"building_id": "B04_LAB_BLOCK", "base_load_kw": 60, "occ_capacity": 250},
    {"building_id": "B05_ADMIN",     "base_load_kw": 15, "occ_capacity": 150},
]

DAYS = 60
FREQ_MINUTES = 15
START_DATE = datetime(2026, 1, 1, 0, 0, 0)


def hourly_occupancy_factor(hour, is_weekend):
    """Rough occupancy shape: low at night, peaks mid-morning/afternoon on
    weekdays, much flatter on weekends."""
    if is_weekend:
        return 0.15 + 0.10 * np.exp(-((hour - 12) ** 2) / 30)
    return 0.05 + 0.85 * np.exp(-((hour - 11) ** 2) / 18) \
              + 0.35 * np.exp(-((hour - 15) ** 2) / 18)


def simulate_weather(timestamp):
    """Simple seasonal + daily temperature cycle (deg C) with noise, plus a
    humidity figure correlated to temperature."""
    day_of_year = timestamp.timetuple().tm_yday
    seasonal = 27 + 6 * np.sin(2 * np.pi * (day_of_year - 30) / 365)
    daily = 4 * np.sin(2 * np.pi * (timestamp.hour - 9) / 24)
    temp = seasonal + daily + np.random.normal(0, 1.0)
    humidity = np.clip(75 - 0.8 * (temp - 27) + np.random.normal(0, 4), 30, 95)
    return round(temp, 2), round(humidity, 2)


def simulate_power(base_load, occ_ratio, temp, capacity, rng):
    """Power draw = base load + occupancy-driven load + HVAC load that rises
    with temperature deviation from a 24C comfort point, plus noise."""
    occ_component = base_load * 0.9 * occ_ratio
    hvac_component = base_load * 0.35 * max(0, (temp - 24) / 8) ** 1.3
    noise = rng.normal(0, base_load * 0.04)
    power = base_load * 0.25 + occ_component + hvac_component + noise
    return round(max(power, 0.5), 3)


def generate():
    rng = np.random.default_rng(RANDOM_SEED)
    n_steps = int(DAYS * 24 * 60 / FREQ_MINUTES)
    timestamps = [START_DATE + timedelta(minutes=FREQ_MINUTES * i) for i in range(n_steps)]

    rows = []
    for b in BUILDINGS:
        for ts in timestamps:
            is_weekend = ts.weekday() >= 5
            occ_ratio = hourly_occupancy_factor(ts.hour + ts.minute / 60, is_weekend)
            occ_ratio = float(np.clip(occ_ratio + rng.normal(0, 0.03), 0, 1))
            occupancy = int(occ_ratio * b["occ_capacity"])

            temp, humidity = simulate_weather(ts)
            power_kw = simulate_power(b["base_load_kw"], occ_ratio, temp, b["occ_capacity"], rng)

            rows.append({
                "building_id": b["building_id"],
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                "power_kw": power_kw,
                "occupancy": occupancy,
                "temperature_c": temp,
                "humidity_pct": humidity,
                "is_weekend": int(is_weekend),
            })

    df = pd.DataFrame(rows)
    return df


if __name__ == "__main__":
    df = generate()
    out_path = "dataset/raw/energy_readings_raw.csv"
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df):,} rows for {df['building_id'].nunique()} buildings")
    print(f"Saved raw dataset to {out_path}")
