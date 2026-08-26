import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))
from core.storage import get_all_readings  # noqa: E402

st.set_page_config(page_title="Smart Campus Energy Dashboard", layout="wide")
st.title("Smart Campus Energy Dashboard")
st.caption("Cloud Energy Consumption Prediction Framework — local MVP view")

readings = get_all_readings()
if not readings:
    st.warning(
        "No data yet. In a separate terminal run:\n\n"
        "1) python local_server/app.py\n"
        "2) python simulator/simulate_readings.py"
    )
    st.stop()

df = pd.DataFrame(readings)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Live Power Draw by Building (kW)")
    pivot = df.pivot_table(index="timestamp", columns="building_id", values="power_kw")
    st.line_chart(pivot)

with col2:
    st.subheader("Latest Readings")
    latest = df.groupby("building_id").tail(1).sort_values("building_id")
    st.dataframe(
        latest[["building_id", "timestamp", "power_kw", "temperature", "occupancy"]],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Forecast Model")
model_path = Path(__file__).resolve().parent.parent / "models" / "forecast_model.pkl"
if model_path.exists():
    st.success("Forecast model is trained and available at models/forecast_model.pkl")
else:
    st.info("Not trained yet. Run: python sagemaker/train_forecast_model.py")

st.subheader("Alerts")
alerts_path = Path(__file__).resolve().parent.parent / "data" / "alerts.log"
if alerts_path.exists() and alerts_path.stat().st_size > 0:
    st.text(alerts_path.read_text()[-3000:])
else:
    st.info("No alerts triggered yet. Run: python lambda/control_policy/handler.py")

