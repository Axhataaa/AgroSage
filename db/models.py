"""
db/models.py
─────────────────────────────────────────────────────────
SQLAlchemy ORM definitions.
Tables: users, fields, results
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    ForeignKey, Text, Boolean
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True)
    name       = Column(String(120), nullable=False)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    password   = Column(String(255), nullable=False)   # bcrypt hash
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active  = Column(Boolean, default=True)

    # Relationships
    fields  = relationship("Field",  back_populates="user", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "created_at": self.created_at.isoformat(),
        }


# ────────────────────────────────────────────────────────
class Field(Base):
    """Stores one soil/climate parameter snapshot for a user's field."""
    __tablename__ = "fields"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    name        = Column(String(120), default="My Field")      # optional label
    latitude    = Column(Float, nullable=True)
    longitude   = Column(Float, nullable=True)

    # Soil nutrients
    nitrogen    = Column(Float, nullable=False)
    phosphorus  = Column(Float, nullable=False)
    potassium   = Column(Float, nullable=False)
    ph          = Column(Float, nullable=False)

    # Climate
    temperature = Column(Float, nullable=False)
    humidity    = Column(Float, nullable=False)
    rainfall    = Column(Float, nullable=False)

    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user    = relationship("User",   back_populates="fields")
    results = relationship("Result", back_populates="field", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "latitude":    self.latitude,
            "longitude":   self.longitude,
            "nitrogen":    self.nitrogen,
            "phosphorus":  self.phosphorus,
            "potassium":   self.potassium,
            "ph":          self.ph,
            "temperature": self.temperature,
            "humidity":    self.humidity,
            "rainfall":    self.rainfall,
            "created_at":  self.created_at.isoformat(),
        }


# ────────────────────────────────────────────────────────
class Result(Base):
    """Stores a crop recommendation result tied to a field snapshot."""
    __tablename__ = "results"

    id             = Column(Integer, primary_key=True)
    user_id        = Column(Integer, ForeignKey("users.id"),  nullable=False)
    field_id       = Column(Integer, ForeignKey("fields.id"), nullable=True)

    # Crop recommendation
    top_crop       = Column(String(80),  nullable=False)
    confidence     = Column(Float,       nullable=False)   # 0–100
    alternatives   = Column(Text,        nullable=True)    # JSON string

    # Disease detection (optional — only set when /detect is called)
    disease_name   = Column(String(120), nullable=True)
    disease_conf   = Column(Float,       nullable=True)
    image_path     = Column(String(255), nullable=True)

    created_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user  = relationship("User",  back_populates="results")
    field = relationship("Field", back_populates="results")

    def to_dict(self):
        import json
        return {
            "id":           self.id,
            "top_crop":     self.top_crop,
            "confidence":   self.confidence,
            "alternatives": json.loads(self.alternatives) if self.alternatives else [],
            "disease_name": self.disease_name,
            "disease_conf": self.disease_conf,
            "created_at":   self.created_at.isoformat(),
        }
