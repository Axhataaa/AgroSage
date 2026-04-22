import os
import json
import joblib
from contextlib import contextmanager

from flask              import Flask, render_template, jsonify, request
from flask_jwt_extended import JWTManager
from sqlalchemy         import create_engine
from sqlalchemy.orm     import sessionmaker
from models.predict_disease import DiseasePredictor

from config    import Config
from db.models import Base


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── CORS ──────────────────────────────────────────────────────
    @app.after_request
    def add_cors(response):
        origin  = request.headers.get("Origin", "")
        allowed = app.config.get("ALLOWED_ORIGINS", [])
        # Also allow any localhost / 127.0.0.1 origin in dev
        # (covers VS Code Live Server, file://, etc.)
        is_local = (
            origin.startswith("http://localhost") or
            origin.startswith("http://127.0.0.1") or
            origin.startswith("file://")
        )
        if origin in allowed or is_local:
            response.headers["Access-Control-Allow-Origin"]      = origin or "*"
        else:
            response.headers["Access-Control-Allow-Origin"]      = "*"
        response.headers["Access-Control-Allow-Headers"]     = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"]     = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            return jsonify({}), 200

    # ── JWT ───────────────────────────────────────────────────────
    jwt = JWTManager(app)

    @jwt.expired_token_loader
    def expired_token(_jwt_header, _jwt_payload):
        return jsonify({"success": False, "message": "Token has expired. Please log in again."}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"success": False, "message": f"Invalid token: {reason}"}), 401

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return jsonify({"success": False, "message": "Authentication required."}), 401

    # ── Database ──────────────────────────────────────────────────
    db_uri         = app.config["SQLALCHEMY_DATABASE_URI"]
    connect_kwargs = {"check_same_thread": False} if "sqlite" in db_uri else {}
    engine         = create_engine(db_uri, connect_args=connect_kwargs)
    SessionLocal   = sessionmaker(bind=engine, expire_on_commit=False)

    Base.metadata.create_all(engine)
    app.logger.info("Database tables verified / created ✓")

    @contextmanager
    def get_db():
        session = SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.db_session = get_db

    # ── Crop ML model (existing — unchanged) ──────────────────────
    crop_model_path = app.config["CROP_MODEL_PATH"]
    crop_enc_path   = app.config["CROP_ENC_PATH"]

    if os.path.exists(crop_model_path) and os.path.exists(crop_enc_path):
        app.crop_model   = joblib.load(crop_model_path)
        app.crop_encoder = joblib.load(crop_enc_path)
        app.logger.info(f"Crop model loaded ✓  ({len(app.crop_encoder.classes_)} classes)")
    else:
        app.crop_model   = None
        app.crop_encoder = None
        app.logger.warning("⚠️  Crop model not found — run: python models/train_crop.py --synthetic")

    # ── Disease Detection Model ───────────────────────────────────
    disease_model_path   = app.config.get("DISEASE_MODEL_PATH",   "")
    disease_classes_path = app.config.get("DISEASE_CLASSES_PATH", "")
    disease_meta_path    = app.config.get("DISEASE_META_PATH",    "")

    app.disease_classes = []

    # Load class list (needed even in stub mode for health check)
    if os.path.exists(disease_classes_path):
        try:
            with open(disease_classes_path) as f:
                app.disease_classes = json.load(f)
            app.logger.info(f"Disease classes loaded ✓  ({len(app.disease_classes)} classes)")
        except Exception as exc:
            app.logger.warning(f"⚠️  Could not load disease_classes.json: {exc}")

    # Load confidence thresholds from metadata if available
    # (overrides config defaults — allows per-model tuning without env vars)
    if os.path.exists(disease_meta_path):
        try:
            with open(disease_meta_path) as f:
                meta = json.load(f)
            app.config["DISEASE_CONF_THRESHOLD"] = meta.get(
                "confidence_threshold", app.config["DISEASE_CONF_THRESHOLD"]
            )
            app.config["DISEASE_ENT_THRESHOLD"] = meta.get(
                "entropy_threshold", app.config["DISEASE_ENT_THRESHOLD"]
            )
            app.logger.info(
                f"Disease thresholds loaded from meta.json  "
                f"(conf≥{app.config['DISEASE_CONF_THRESHOLD']}, "
                f"ent≤{app.config['DISEASE_ENT_THRESHOLD']})"
            )
        except Exception as exc:
            app.logger.warning(f"⚠️  Could not load disease_meta.json: {exc}")

    # Load TF model
    if os.path.exists(disease_model_path):
        try:
            import tensorflow as tf
            app.disease_predictor = DiseasePredictor(
                model_path=disease_model_path,
                classes_path=disease_classes_path,
                meta_path=disease_meta_path,
                use_tta=False
            )
            app.logger.info(
                f"Disease model loaded ✓  "
                f"[{os.path.basename(disease_model_path)}]  "
                f"classes={len(app.disease_classes)}"
            )
        except ImportError:
            app.logger.warning(
                "TensorFlow not installed — disease detection runs in stub mode.\n"
                "  Install: pip install tensorflow  (GPU) or pip install tensorflow-cpu"
            )
        except Exception as exc:
            app.logger.warning(f"⚠️  Disease model load failed: {exc}")
    else:
        app.logger.warning(
            "⚠️  Disease model not found — stub mode active.\n"
            f"   Expected at: {disease_model_path}\n"
            "   Train with: python models/train_disease.py --data dataset/raw"
        )

    # ── API Blueprints ────────────────────────────────────────────
    from api.auth      import auth_bp
    from api.recommend import recommend_bp
    from api.detect    import detect_bp
    from api.soil      import soil_bp
    from api.analytics import analytics_bp
    from utils.weather import weather_bp

    app.register_blueprint(auth_bp)       # /api/auth/*
    app.register_blueprint(recommend_bp)  # /api/recommend, /api/history
    app.register_blueprint(detect_bp)     # /api/detect
    app.register_blueprint(weather_bp)    # /api/weather
    app.register_blueprint(soil_bp)       # /api/soil
    app.register_blueprint(analytics_bp)  # /api/importance, /api/stats

    # ── Page routes ───────────────────────────────────────────────
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/login")
    def login_page():
        return render_template("login.html")

    @app.get("/signup")
    def signup_page():
        return render_template("signup.html")

    # ── Health check ──────────────────────────────────────────────
    @app.get("/api/health")
    def health():
        disease_status = "not loaded (stub mode active)"
        if hasattr(app, "disease_predictor"):
            disease_status = f"ready ({len(app.disease_classes)} classes)"

        return jsonify({
            "status":        "ok",
            "crop_model":    "ready" if app.crop_model else "not loaded — run train_crop.py --synthetic",
            "disease_model": disease_status,
            "endpoints": {
                "recommend":  "/api/recommend  [POST, JWT]",
                "detect":     "/api/detect     [POST, JWT]",
                "weather":    "/api/weather    [GET]",
                "soil":       "/api/soil       [GET]",
                "importance": "/api/importance [GET]",
                "stats":      "/api/stats      [GET]",
                "history":    "/api/history    [GET, JWT]",
            },
        }), 200

    # ── Error handlers ────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": f"API route not found: {request.path}"}), 404
        return render_template("index.html")  # SPA fallback

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({
            "success": False,
            "message": f"Method '{request.method}' not allowed on {request.path}."
        }), 405

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception(e)
        return jsonify({"success": False, "message": "Internal server error."}), 500

    return app


# ── Dev entry point ───────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
