# Dataset Details and Preprocessing Plan

## Selected public datasets

| Dataset | Source / URL | Size and records | Features and type | Licence | Purpose |
|---|---|---|---|---|---|
| Building Data Genome Project 2 | BUS Lab: https://github.com/buds-lab/the-building-data-genome-project | 1,570 non-residential buildings; 53.6 million hourly measurements | Building electricity time series and metadata | CC BY 4.0 | Main multi-building federated forecasting benchmark |
| Smart* Home Dataset | UMass Amherst Smart* Project | More than 6 million one-second readings from 3 real homes | Electrical power time series | Public research dataset | Edge-level sampling and preprocessing experiments |
| ASHRAE Great Energy Predictor III | Kaggle competition dataset | Multi-building, multi-year meter and weather records | Meter readings, weather and building metadata | Kaggle competition terms | Weather and cross-building variability evaluation |
| UCI Appliances Energy Prediction | UCI Machine Learning Repository | 19,735 records at 10-minute intervals | Appliance energy, temperature, humidity and weather variables | CC BY 4.0 | Prototype and feature-engineering baseline |

## Data fields used

The common model input will include timestamp, previous energy load, outside temperature, relative humidity, occupancy proxy, day type, hour, holiday flag, gross floor area and EV-charging activity where available. The forecast target is the next 15-minute or hourly electricity demand in kW/kWh.

## Preprocessing

1. Remove duplicate records and invalid negative meter values.
2. Convert timestamps to a common timezone and resample readings to 15-minute intervals.
3. Impute short gaps using forward fill or a seasonal median; flag longer gaps for exclusion.
4. Encode hour, weekday and holiday features; derive lagged load and rolling-average features.
5. Scale numerical inputs using training-partition statistics only.
6. Partition buildings into independent clients so raw records never move between clients.
7. Split each client chronologically into training, validation and test periods to prevent future-data leakage.

Raw data belongs in dataset/raw/ locally and is intentionally ignored by Git. Clean feature extracts belong in dataset/processed/ and should be stored externally if large.
