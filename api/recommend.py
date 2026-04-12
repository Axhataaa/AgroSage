"""
api/recommend.py
─────────────────────────────────────────────────────────
Crop recommendation endpoints.

POST /api/recommend   — run prediction (JWT required)
GET  /api/history     — list user's past recommendations (JWT required)

FIXES APPLIED:
  • predict() return-type safety: handles both numeric index and
    string label returns from the sklearn pipeline.
  • Robust confidence extraction regardless of pipeline internals.
  • Cleaner error message if model is not loaded.
"""

import json
import numpy as np
from flask              import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy         import select

from db.models import Field, Result, User

recommend_bp = Blueprint("recommend", __name__, url_prefix="/api")


def _get_db():
    return current_app.db_session()


def _load_model():
    return current_app.crop_model, current_app.crop_encoder


# ── Input schema & validation ranges ─────────────────────────
FIELD_RULES = {
    "N":           (0,   150,  "Nitrogen (kg/ha)"),
    "P":           (0,   80,   "Phosphorus (kg/ha)"),
    "K":           (0,   120,  "Potassium (kg/ha)"),
    "temperature": (0,   50,   "Temperature (°C)"),
    "humidity":    (0,   100,  "Humidity (%)"),
    "ph":          (0,   14,   "Soil pH"),
    "rainfall":    (0,   300,  "Rainfall (mm)"),
}


def _validate_inputs(data: dict):
    errors = {}
    values = {}
    for key, (lo, hi, label) in FIELD_RULES.items():
        raw = data.get(key)
        if raw is None:
            errors[key] = f"{label} is required."
            continue
        try:
            val = float(raw)
        except (TypeError, ValueError):
            errors[key] = f"{label} must be a number."
            continue
        if not (lo <= val <= hi):
            errors[key] = f"{label} must be between {lo} and {hi}."
            continue
        values[key] = val
    return values, errors


# ─────────────────────────────────────────────────────────────
@recommend_bp.post("/recommend")
@jwt_required()
def recommend():
    user_id = int(get_jwt_identity())
    data    = request.get_json(silent=True) or {}

    # ── Validate inputs ──
    values, errors = _validate_inputs(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 422

    # ── Check model is loaded ──
    pipeline, le = _load_model()
    if pipeline is None or le is None:
        return jsonify({
            "success": False,
            "message": "Crop model not loaded. Run: python models/train_crop.py --synthetic"
        }), 503

    # ── Build feature vector (must match training column order) ──
    X = np.array([[
        values["N"],
        values["P"],
        values["K"],
        values["temperature"],
        values["humidity"],
        values["ph"],
        values["rainfall"],
    ]])

    # ── Predict ──
    # FIX: pipeline.predict() may return a class label (string) OR a
    # numeric index depending on whether the pipeline contains the encoder.
    # We normalise to a class label string here safely.
    raw_pred = pipeline.predict(X)[0]
    proba    = pipeline.predict_proba(X)[0]   # shape: (n_classes,)

    # Convert prediction to class label regardless of type
    if isinstance(raw_pred, (int, np.integer)):
        top_crop = le.inverse_transform([raw_pred])[0]
        top_idx  = int(raw_pred)
    else:
        # Already a string label
        top_crop = str(raw_pred)
        # Find its numeric index in the encoder classes
        classes_list = list(le.classes_)
        top_idx = classes_list.index(top_crop) if top_crop in classes_list else int(np.argmax(proba))

    confidence = round(float(proba[top_idx]) * 100, 1)

    # ── Top-5 alternatives (excluding the winner) ──
    top5_idx = np.argsort(proba)[::-1][:6]
    alternatives = [
        {"crop": le.classes_[i], "confidence": round(float(proba[i]) * 100, 1)}
        for i in top5_idx
        if i != top_idx
    ][:4]

    # ── Persist to DB ──
    field_name = (data.get("field_name") or "My Field").strip()
    lat        = data.get("latitude")
    lng        = data.get("longitude")

    with _get_db() as db:
        field = Field(
            user_id     = user_id,
            name        = field_name,
            latitude    = float(lat) if lat is not None else None,
            longitude   = float(lng) if lng is not None else None,
            nitrogen    = values["N"],
            phosphorus  = values["P"],
            potassium   = values["K"],
            ph          = values["ph"],
            temperature = values["temperature"],
            humidity    = values["humidity"],
            rainfall    = values["rainfall"],
        )
        db.add(field)
        db.flush()   # get field.id before commit

        result = Result(
            user_id      = user_id,
            field_id     = field.id,
            top_crop     = top_crop,
            confidence   = confidence,
            alternatives = json.dumps(alternatives),
        )
        db.add(result)
        db.commit()
        db.refresh(result)

    return jsonify({
        "success":      True,
        "result_id":    result.id,
        "top_crop":     top_crop,
        "confidence":   confidence,
        "alternatives": alternatives,
        "field":        field.to_dict(),
    }), 200


# ─────────────────────────────────────────────────────────────
@recommend_bp.get("/history")
@jwt_required()
def history():
    user_id  = int(get_jwt_identity())
    page     = max(1, int(request.args.get("page",     1)))
    per_page = min(50, int(request.args.get("per_page", 10)))
    offset   = (page - 1) * per_page

    with _get_db() as db:
        stmt = (
            select(Result)
            .where(Result.user_id == user_id)
            .order_by(Result.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        results = db.scalars(stmt).all()
        return jsonify({
            "success": True,
            "page":    page,
            "results": [r.to_dict() for r in results],
        }), 200
