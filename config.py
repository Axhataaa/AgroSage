"""
config.py
─────────────────────────────────────────────────────────
Central app configuration. All values come from environment
variables (loaded from .env in development).
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Flask core ──────────────────────────────────────────────
    SECRET_KEY  = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    FLASK_ENV   = os.getenv("FLASK_ENV", "production")
    DEBUG       = FLASK_ENV == "development"

    # ── JWT ─────────────────────────────────────────────────────
    JWT_SECRET_KEY           = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24 * 7   # 7 days (in seconds)

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///agrosage.db")
    # SQLAlchemy needs 'postgresql://' not 'postgres://' (Render uses the old form)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI        = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── CORS ─────────────────────────────────────────────────────
    ALLOWED_ORIGINS = [
        o.strip()
        for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5500").split(",")
        if o.strip()
    ]

    # ── Base directory ───────────────────────────────────────────
    BASE_DIR = os.path.dirname(__file__)

    # ── Crop model paths (existing — unchanged) ──────────────────
    CROP_MODEL_PATH = os.path.join(BASE_DIR, "models", "saved", "crop_model.pkl")
    CROP_ENC_PATH   = os.path.join(BASE_DIR, "models", "saved", "crop_label_encoder.pkl")

    # ── Disease model paths ──────────────────────────────────────
    # Primary: .keras format (TF 2.12+)  |  Fallback: .h5 (legacy)
    _keras_path = os.path.join(BASE_DIR, "models", "saved", "disease_model.keras")
    _h5_path    = os.path.join(BASE_DIR, "models", "saved", "disease_model.h5")

    # Prefer .keras if it exists, otherwise use .h5
    DISEASE_MODEL_PATH = _keras_path if os.path.exists(_keras_path) else _h5_path

    # Class list (JSON array of class name strings)
    DISEASE_CLASSES_PATH = os.path.join(BASE_DIR, "models", "saved", "disease_classes.json")

    # Model metadata (thresholds, accuracy stats)
    DISEASE_META_PATH = os.path.join(BASE_DIR, "models", "saved", "disease_meta.json")

    # ── OOD / Confidence thresholds ──────────────────────────────
    # Predictions below conf_threshold are flagged as "uncertain".
    # Predictions above ent_threshold are flagged as "uncertain".
    # Start permissive (0.55 / 0.65) and raise after validating your model.
    # Override via env vars without restarting:
    #   set DISEASE_CONF_THRESHOLD=0.70 && python app.py
    DISEASE_CONF_THRESHOLD = float(os.getenv("DISEASE_CONF_THRESHOLD", "0.55"))
    DISEASE_ENT_THRESHOLD  = float(os.getenv("DISEASE_ENT_THRESHOLD",  "0.65"))

    # ── Upload folder ─────────────────────────────────────────────
    UPLOAD_FOLDER      = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024      # 16 MB
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
