from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("SKLEARN_NUM_THREADS", "1")

from threadpoolctl import threadpool_limits

from src.data import load_or_generate_dataset
from src.modeling import save_model, train_aqi_model, train_model

DATA_PATH = Path("data/historical_weather.csv")
MODEL_PATH = Path("models/temperature_model.pkl")
METRICS_PATH = Path("models/metrics.json")
AQI_MODEL_PATH = Path("models/aqi_model.pkl")
AQI_METRICS_PATH = Path("models/aqi_metrics.json")


def main() -> None:
    df, source = load_or_generate_dataset(DATA_PATH)

    with threadpool_limits(limits=1):
        model, metrics = train_model(df)
        save_model(model, MODEL_PATH)
        METRICS_PATH.write_text(json.dumps({"source": source, **metrics}, indent=2))

        print("Temperature model trained.")
        print(f"Data source: {source}")
        print(f"MAE: {metrics['mae']:.3f}")

        if "aqi" in df.columns:
            aqi_model, aqi_metrics = train_aqi_model(df)
            save_model(aqi_model, AQI_MODEL_PATH)
            AQI_METRICS_PATH.write_text(json.dumps({"source": source, **aqi_metrics}, indent=2))
            print("AQI model trained.")
            print(f"AQI MAE: {aqi_metrics['mae']:.3f}")
        else:
            print("AQI column not found. Skipping AQI model training.")


if __name__ == "__main__":
    main()
