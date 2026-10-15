import numpy as np
import pandas as pd


# ============================================================
# Feature engineering
# ============================================================

def create_features(df):
    """
    Convert timestamp information into
    numerical features for ML models.
    """

    df = df.copy()

    # Make sure timestamp is datetime
    df["reading_time"] = pd.to_datetime(
        df["reading_time"]
    )

    # --------------------------------------------------------
    # Basic time features
    # --------------------------------------------------------

    df["hour"] = (
        df["reading_time"].dt.hour
    )

    df["day_of_week"] = (
        df["reading_time"].dt.dayofweek
    )

    df["day_of_month"] = (
        df["reading_time"].dt.day
    )

    df["month"] = (
        df["reading_time"].dt.month
    )

    # --------------------------------------------------------
    # Weekend
    # --------------------------------------------------------

    df["is_weekend"] = (
        df["day_of_week"] >= 5
    ).astype(int)

    # --------------------------------------------------------
    # Cyclic hour features
    # --------------------------------------------------------

    df["hour_sin"] = np.sin(
        2 * np.pi * df["hour"] / 24
    )

    df["hour_cos"] = np.cos(
        2 * np.pi * df["hour"] / 24
    )

    # --------------------------------------------------------
    # Cyclic day-of-week features
    # --------------------------------------------------------

    df["dow_sin"] = np.sin(
        2 * np.pi * df["day_of_week"] / 7
    )

    df["dow_cos"] = np.cos(
        2 * np.pi * df["day_of_week"] / 7
    )

    return df
