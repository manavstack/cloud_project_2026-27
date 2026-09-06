| Field | Description |
|---|---|
| **Dataset Name** | Smart Campus Synthetic Energy Readings |
| **Source** | Generated in-house via `dataset/generate_dataset.py` (custom simulator, stand-in for real IoT smart meters) |
| **URL** | N/A — synthetic, generated locally / in CI |
| **Size** | ~2.8 MB (CSV) |
| **Number of Records** | 28,800 (5 buildings × 60 days × 96 readings/day at 15-min intervals) |
| **Number of Features** | 6 raw (`building_id`, `timestamp`, `power_kw`, `occupancy`, `temperature_c`, `humidity_pct`, `is_weekend`) → 14+ after feature engineering |
| **Data Type** | Time-series, tabular (CSV) |
| **License** | Synthetic data generated for this project — free to use/redistribute within the course project |
| **Purpose of Dataset** | Train and evaluate a short-term (next-15-min / next-hour) power load forecasting model per building, feeding the rule-based control Lambda described in the project proposal |
| **Preprocessing Required** | Timestamp parsing, cyclical time encoding (hour/day-of-week), lag features (t-1, t-4, t-96), rolling averages, per-building one-hot/categorical encoding, train/val/test split by time (no shuffling, to avoid leakage) |

## Why synthetic data
Per the Buildable MVP Plan (Section 1), real smart-meter hardware and months
of data collection are out of scope for a solo/team semester build. The
simulator (`dataset/generate_dataset.py`) reproduces realistic daily
occupancy curves, weekday/weekend differences, and temperature-driven HVAC
load, so the forecasting model trained on it transfers conceptually to real
meter data described in the full proposal (Section 7: swap simulator for
real IoT hardware).

