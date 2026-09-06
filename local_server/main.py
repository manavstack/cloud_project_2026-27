import sys
import os
import logging
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd

# Add the root directory to path to import ml_models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.ml_models.predict import load_model, predict_next
from aws_client import AWSClient

app = FastAPI(title="Campus Edge Server")
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Global variables
model = None
feature_cols = None
aws_client = None

@app.on_event("startup")
async def startup_event():
    global model, feature_cols, aws_client
    logger.info("Starting up edge server, loading model...")
    try:
        model, feature_cols = load_model(
            model_path="../src/ml_models/model.pkl", 
            feature_cols_path="../src/ml_models/feature_columns.json"
        )
        aws_client = AWSClient()
        logger.info("Startup complete.")
    except Exception as e:
        logger.error(f"Failed to startup: {e}")

class TelemetryData(BaseModel):
    building_id: str
    timestamp: str
    power_kw: float
    occupancy: float
    temperature_c: float
    humidity_pct: float
    is_weekend: int

class PredictRequest(BaseModel):
    readings: List[TelemetryData]

@app.post("/predict")
async def predict_endpoint(request: PredictRequest):
    if not model or not feature_cols:
        raise HTTPException(status_code=500, detail="Model not loaded")
        
    if len(request.readings) < 97:
        raise HTTPException(status_code=400, detail="Need at least 97 readings to calculate lag/rolling features")

    try:
        df = pd.DataFrame([reading.dict() for reading in request.readings])
        
        forecast = predict_next(model, feature_cols, df)
        
        # Optionally send to cloud
        topic = f"campus/edge/{request.readings[-1].building_id}/forecast"
        if aws_client:
            aws_client.send_telemetry_to_cloud(topic, {
                "building_id": request.readings[-1].building_id,
                "timestamp": request.readings[-1].timestamp,
                "forecast_kw": forecast
            })
        
        return {"forecast_kw": forecast, "building_id": request.readings[-1].building_id}
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
