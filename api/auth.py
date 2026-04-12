"""
api/auth.py
─────────────────────────────────────────────────────────
Authentication endpoints.

POST /api/auth/signup   — create account, return JWT
POST /api/auth/login    — verify credentials, return JWT
GET  /api/auth/me       — return current user (JWT required)
"""

import bcrypt
from flask              import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy         import select
from sqlalchemy.orm     import Session

from db.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _get_db() -> Session:
    """Pull the SQLAlchemy session from the app context."""
    return current_app.db_session()


# ────────────────────────────────────────────────────────
@auth_bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}

    name     = (data.get("name")     or "").strip()
    email    = (data.get("email")    or "").strip().lower()
    password =  data.get("password") or ""

    # ── Validation ──
    errors = {}
    if not name:                        errors["name"]     = "Name is required."
    if not email or "@" not in email:   errors["email"]    = "Valid email is required."
    if len(password) < 6:              errors["password"] = "Password must be at least 6 characters."
    if errors:
        return jsonify({"success": False, "errors": errors}), 422

    with _get_db() as db:
        # Check duplicate email
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            return jsonify({"success": False, "errors": {"email": "Email already registered."}}), 409

        # Hash password
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        user = User(name=name, email=email, password=pw_hash)
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(identity=str(user.id))
        return jsonify({
            "success": True,
            "token":   token,
            "user":    user.to_dict(),
        }), 201


# ────────────────────────────────────────────────────────
@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email    = (data.get("email")    or "").strip().lower()
    password =  data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    with _get_db() as db:
        user = db.scalar(select(User).where(User.email == email))

        if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
            return jsonify({"success": False, "message": "Invalid email or password."}), 401

        if not user.is_active:
            return jsonify({"success": False, "message": "Account is deactivated."}), 403

        token = create_access_token(identity=str(user.id))
        return jsonify({
            "success": True,
            "token":   token,
            "user":    user.to_dict(),
        }), 200


# ────────────────────────────────────────────────────────
@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    with _get_db() as db:
        user = db.get(User, user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found."}), 404
        return jsonify({"success": True, "user": user.to_dict()}), 200
