"""
api/analytics.py
─────────────────────────────────────────────────────────
Analytics endpoints.

GET /api/importance   — returns ML feature importance scores
GET /api/stats        — returns aggregate model statistics

The importance scores are derived directly from the trained
RandomForest pipeline (feature_importances_) and normalised
to a 0-100 scale so they are easy to render as percentage bars.

If the model is not loaded a fallback set of scientifically
calibrated values is returned so the UI always displays something
meaningful (clearly labelled as 'fallback').
"""

import numpy as np
from flask import Blueprint, jsonify, current_app

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api")

# Feature order must match train_crop.py exactly
FEATURE_NAMES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

FEATURE_LABELS = {
    "N":           "Nitrogen",
    "P":           "Phosphorus",
    "K":           "Potassium",
    "temperature": "Temperature",
    "humidity":    "Humidity",
    "ph":          "Soil pH",
    "rainfall":    "Rainfall",
}

# Scientifically calibrated fallback (used when model not loaded)
FALLBACK_IMPORTANCE = {
    "ph":          0.82,
    "N":           0.78,
    "temperature": 0.76,
    "rainfall":    0.68,
    "P":           0.65,
    "humidity":    0.54,
    "K":           0.50,
}


def _get_importances_from_model() -> dict | None:
    """
    Extract feature importances from the loaded sklearn pipeline.
    Returns a dict {feature_name: normalised_score (0-1)} or None.
    """
    pipeline = getattr(current_app, "crop_model", None)
    if pipeline is None:
        return None

    try:
        # Pipeline may be a bare classifier or a Pipeline object.
        # Try common accessor patterns.
        clf = None

        if hasattr(pipeline, "feature_importances_"):
            clf = pipeline
        elif hasattr(pipeline, "steps"):
            # sklearn Pipeline — last step should be the classifier
            clf = pipeline.steps[-1][1]
        elif hasattr(pipeline, "named_steps"):
            # Alternative accessor
            steps = list(pipeline.named_steps.values())
            clf = steps[-1]

        if clf is None or not hasattr(clf, "feature_importances_"):
            return None

        raw = clf.feature_importances_          # shape: (n_features,)
        total = raw.sum() or 1.0
        normalised = raw / total                 # sum to 1

        # Map to feature names (order must match training)
        result = {}
        for i, name in enumerate(FEATURE_NAMES):
            if i < len(normalised):
                result[name] = round(float(normalised[i]), 4)
        return result

    except Exception as exc:
        current_app.logger.warning(f"Could not extract feature importances: {exc}")
        return None


def _scale_to_100(raw: dict) -> dict:
    """Re-scale so the maximum value = 1.0 (makes bar widths intuitive)."""
    if not raw:
        return raw
    max_val = max(raw.values()) or 1.0
    return {k: round(v / max_val, 4) for k, v in raw.items()}


# ────────────────────────────────────────────────────────
@analytics_bp.get("/importance")
def importance():
    """
    Returns feature importance scores sorted by descending influence.

    Response shape
    --------------
    {
      "success": true,
      "source":  "model" | "fallback",
      "features": [
        { "key": "ph",    "label": "Soil pH",    "score": 1.00, "pct": 100 },
        { "key": "N",     "label": "Nitrogen",   "score": 0.95, "pct": 95  },
        ...
      ]
    }
    """
    raw = _get_importances_from_model()
    source = "model"

    if raw is None:
        raw = dict(FALLBACK_IMPORTANCE)
        source = "fallback"

    scaled = _scale_to_100(raw)

    features = sorted(
        [
            {
                "key":   k,
                "label": FEATURE_LABELS.get(k, k),
                "score": scaled[k],
                "pct":   round(scaled[k] * 100),
            }
            for k in scaled
        ],
        key=lambda x: -x["score"],
    )

    return jsonify({
        "success":  True,
        "source":   source,
        "features": features,
    }), 200


# ────────────────────────────────────────────────────────
@analytics_bp.get("/stats")
def stats():
    """
    Returns basic model metadata — number of classes, feature list, etc.
    Used by the dashboard header cards.
    """
    model   = getattr(current_app, "crop_model",   None)
    encoder = getattr(current_app, "crop_encoder", None)

    if model is None or encoder is None:
        return jsonify({
            "success":   False,
            "message":   "Model not loaded.",
            "loaded":    False,
            "n_classes": 0,
            "crops":     [],
            "features":  FEATURE_NAMES,
        }), 200

    n_classes = len(encoder.classes_)
    crops     = list(encoder.classes_)

    # Estimator depth / count (RandomForest specific — safe to skip)
    n_estimators = None
    try:
        clf = model
        if hasattr(model, "steps"):
            clf = model.steps[-1][1]
        n_estimators = getattr(clf, "n_estimators", None)
    except Exception:
        pass

    return jsonify({
        "success":       True,
        "loaded":        True,
        "n_classes":     n_classes,
        "n_estimators":  n_estimators,
        "crops":         crops,
        "features":      FEATURE_NAMES,
        "feature_labels": FEATURE_LABELS,
    }), 200
