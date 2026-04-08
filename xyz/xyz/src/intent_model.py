from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Tuple

import joblib

MODEL_PATH = Path("models/intent_model.joblib")


@lru_cache(maxsize=1)
def _load_model():
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return None


def predict_intent(text: str) -> Tuple[str, float] | None:
    model = _load_model()
    if model is None:
        return None
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    if hasattr(model, "predict_proba"):
        probs = model.predict_proba([cleaned])[0]
        idx = int(probs.argmax())
        return str(model.classes_[idx]), float(probs[idx])

    if hasattr(model, "decision_function"):
        scores = model.decision_function([cleaned])
        if scores.ndim == 1:
            idx = int(scores.argmax())
            confidence = float(scores[idx])
        else:
            idx = int(scores[0].argmax())
            confidence = float(scores[0][idx])
        return str(model.classes_[idx]), confidence

    pred = model.predict([cleaned])[0]
    return str(pred), 1.0
