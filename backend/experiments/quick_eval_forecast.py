from __future__ import annotations

"""
Evaluate forecasting RMSE/MAPE and produce an overlay plot for recent days.

Usage (from backend/):
  python -m experiments.quick_eval_forecast --region guangdong --test_days 30 --outdir experiments/results
Outputs:
  - fig4_forecast_overlay.png
  - forecast_metrics.json
"""

import os
import json
import argparse
from typing import Tuple
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from services.load_prediction import LoadPrediction, load_prediction


def split_train_test(df: pd.DataFrame, test_days: int = 30) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values('timestamp')
    cutoff = df['timestamp'].max() - pd.Timedelta(days=test_days)
    train = df[df['timestamp'] <= cutoff].copy()
    test = df[df['timestamp'] > cutoff].copy()
    return train, test


def predict_from_df(df_train: pd.DataFrame, horizon_hours: int) -> pd.DataFrame:
    # Reuse the same logic as in LoadPrediction but on a given df subset
    # Simple trend + seasonal + daily + weekly based on last 30 days mean
    last_date = df_train['timestamp'].max()
    future_dates = pd.date_range(start=last_date + pd.Timedelta(hours=1), periods=horizon_hours, freq='H')
    base_load = df_train.tail(30 * 24)['load_mw'].mean()
    # Estimate growth from year-over-year if possible
    if len(df_train) > 365 * 24 + 30 * 24:
        recent = df_train.tail(30 * 24)['load_mw'].mean()
        year_ago = df_train.iloc[-(365 + 30) * 24:-(365) * 24]['load_mw'].mean()
        growth_rate = (recent - year_ago) / max(1e-6, year_ago)
    else:
        growth_rate = 0.05
    hours = np.arange(len(future_dates))
    trend = base_load * growth_rate * hours / (365 * 24)
    seasonal = base_load * 0.08 * np.sin(2 * np.pi * hours / (365 * 24))
    daily = base_load * 0.15 * np.sin(2 * np.pi * (hours % 24) / 24 - np.pi / 2)
    weekly = base_load * 0.05 * (np.array([d.weekday() < 5 for d in future_dates]).astype(float) - 0.5)
    predicted = base_load + trend + seasonal + daily + weekly
    return pd.DataFrame({'timestamp': future_dates, 'predicted_load_mw': predicted})


def rmse_mape(y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[float, float]:
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mape = float(np.mean(np.abs((y_true - y_pred) / np.maximum(1e-6, y_true)))) * 100.0
    return rmse, mape


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--region', default='guangdong')
    ap.add_argument('--test_days', type=int, default=30)
    ap.add_argument('--outdir', default='experiments/results')
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # Load full historical df
    df = load_prediction.load_historical_data()
    train, test = split_train_test(df, test_days=args.test_days)
    pred = predict_from_df(train, horizon_hours=len(test))

    # Align arrays
    merged = pd.merge(test[['timestamp', 'load_mw']], pred, on='timestamp', how='inner')
    y_true = merged['load_mw'].to_numpy()
    y_pred = merged['predicted_load_mw'].to_numpy()
    rmse, mape = rmse_mape(y_true, y_pred)

    # FIG overlay (last 7 days)
    last_days = min(7, args.test_days)
    tail = merged.tail(last_days * 24)
    plt.figure(figsize=(7,4))
    plt.plot(tail['timestamp'], tail['load_mw'], label='Actual', color='#111827')
    plt.plot(tail['timestamp'], tail['predicted_load_mw'], label='Predicted', color='#2563eb')
    plt.xticks(rotation=30)
    plt.xlabel('Time')
    plt.ylabel('Load (MW)')
    plt.title(f'Forecast Overlay (Last {last_days} days)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    fig = os.path.join(args.outdir, 'fig4_forecast_overlay.png')
    plt.tight_layout(); plt.savefig(fig, dpi=150)
    print('Saved', fig)

    with open(os.path.join(args.outdir, 'forecast_metrics.json'), 'w') as f:
        json.dump({'rmse': rmse, 'mape': mape, 'points': int(len(merged))}, f, indent=2)
    print(f'RMSE={rmse:.2f}, MAPE={mape:.2f}% over {len(merged)} points')


if __name__ == '__main__':
    main()

