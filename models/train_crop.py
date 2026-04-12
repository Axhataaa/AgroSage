"""
train_crop.py
─────────────────────────────────────────────────────────
Trains a Random Forest classifier on the Crop Recommendation
dataset and saves the model + label encoder + scaler to disk.

Dataset: https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset
Expected CSV columns:
    N, P, K, temperature, humidity, ph, rainfall, label

Usage
-----
  # With the real Kaggle CSV:
  python train_crop.py --data Crop_recommendation.csv

  # Without the CSV (uses built-in synthetic data to verify pipeline):
  python train_crop.py --synthetic
"""

import argparse
import os
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble          import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing     import LabelEncoder, StandardScaler
from sklearn.model_selection   import train_test_split, cross_val_score
from sklearn.metrics           import classification_report, accuracy_score
from sklearn.pipeline          import Pipeline


# ── Output paths ──────────────────────────────────────────────
SAVE_DIR   = os.path.join(os.path.dirname(__file__), "saved")
MODEL_PATH = os.path.join(SAVE_DIR, "crop_model.pkl")
ENC_PATH   = os.path.join(SAVE_DIR, "crop_label_encoder.pkl")

os.makedirs(SAVE_DIR, exist_ok=True)


# ── Crop parameter profiles (mirrors the real Kaggle dataset) ─
# Used ONLY when --synthetic flag is passed (no real CSV available).
CROP_PROFILES = {
    "rice":       dict(N=(60,100), P=(30,50),  K=(30,60),  T=(20,35), H=(60,95), pH=(5.5,7.0), R=(150,300)),
    "wheat":      dict(N=(50,90),  P=(30,60),  K=(25,50),  T=(10,25), H=(40,70), pH=(6.0,7.5), R=(50,100)),
    "maize":      dict(N=(60,120), P=(25,50),  K=(30,70),  T=(18,35), H=(50,75), pH=(5.8,7.5), R=(80,200)),
    "chickpea":   dict(N=(15,40),  P=(30,60),  K=(20,40),  T=(15,30), H=(30,60), pH=(6.0,8.5), R=(40,80)),
    "lentil":     dict(N=(10,30),  P=(20,50),  K=(20,40),  T=(12,25), H=(30,55), pH=(6.0,7.5), R=(30,65)),
    "cotton":     dict(N=(60,120), P=(20,60),  K=(30,60),  T=(21,35), H=(50,80), pH=(5.8,8.0), R=(60,150)),
    "sugarcane":  dict(N=(80,140), P=(40,80),  K=(60,100), T=(21,38), H=(70,95), pH=(6.0,8.5), R=(100,250)),
    "mango":      dict(N=(40,80),  P=(20,40),  K=(40,80),  T=(24,38), H=(50,80), pH=(5.5,7.5), R=(75,150)),
    "banana":     dict(N=(80,140), P=(30,60),  K=(100,200),T=(20,35), H=(70,90), pH=(6.0,7.5), R=(100,200)),
    "watermelon": dict(N=(40,80),  P=(20,50),  K=(30,70),  T=(25,38), H=(50,70), pH=(6.0,7.0), R=(40,80)),
    "pigeonpea":  dict(N=(10,30),  P=(25,50),  K=(15,40),  T=(18,35), H=(40,70), pH=(5.5,7.5), R=(60,150)),
    "mustard":    dict(N=(40,80),  P=(15,40),  K=(15,40),  T=(10,25), H=(35,60), pH=(6.0,8.0), R=(25,75)),
    "coffee":     dict(N=(80,120), P=(40,80),  K=(40,80),  T=(15,28), H=(60,90), pH=(6.0,6.8), R=(100,300)),
    "coconut":    dict(N=(50,100), P=(20,60),  K=(50,100), T=(25,38), H=(70,90), pH=(5.5,7.5), R=(100,200)),
    "papaya":     dict(N=(50,90),  P=(30,60),  K=(50,100), T=(25,38), H=(60,90), pH=(6.0,7.0), R=(100,180)),
    "orange":     dict(N=(40,80),  P=(20,50),  K=(40,80),  T=(15,30), H=(50,75), pH=(5.5,7.5), R=(100,180)),
    "apple":      dict(N=(40,70),  P=(20,50),  K=(40,80),  T=(8,20),  H=(50,80), pH=(5.5,7.0), R=(100,200)),
    "grapes":     dict(N=(30,70),  P=(20,50),  K=(30,70),  T=(15,30), H=(50,80), pH=(5.5,7.5), R=(50,150)),
    "pomegranate":dict(N=(40,70),  P=(20,50),  K=(30,60),  T=(25,38), H=(40,70), pH=(5.5,7.5), R=(50,150)),
    "jute":       dict(N=(60,100), P=(30,60),  K=(30,60),  T=(24,37), H=(70,90), pH=(6.0,7.5), R=(150,250)),
    "kidneybeans":dict(N=(15,40),  P=(30,70),  K=(15,40),  T=(15,28), H=(40,70), pH=(5.5,7.5), R=(80,150)),
    "mothbeans":  dict(N=(10,30),  P=(20,50),  K=(15,35),  T=(25,38), H=(30,60), pH=(6.0,8.0), R=(30,80)),
}


def generate_synthetic_data(samples_per_crop: int = 200) -> pd.DataFrame:
    """
    Generate realistic synthetic training data based on known agronomic ranges.
    This mirrors the structure of the real Kaggle dataset so the pipeline is
    identical — swap in the real CSV for production.
    """
    rng    = np.random.default_rng(42)
    rows   = []

    for crop, p in CROP_PROFILES.items():
        for _ in range(samples_per_crop):
            # Sample from uniform range then add Gaussian noise
            def s(lo, hi, noise=0.06):
                base  = rng.uniform(lo, hi)
                jitter= rng.normal(0, (hi - lo) * noise)
                return float(np.clip(base + jitter, lo * 0.85, hi * 1.15))

            rows.append({
                "N":           s(*p["N"]),
                "P":           s(*p["P"]),
                "K":           s(*p["K"]),
                "temperature": s(*p["T"]),
                "humidity":    s(*p["H"]),
                "ph":          s(*p["pH"]),
                "rainfall":    s(*p["R"]),
                "label":       crop,
            })

    df = pd.DataFrame(rows)
    print(f"  Synthetic dataset: {len(df):,} rows | {df['label'].nunique()} crops")
    return df


def load_real_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    required = {"N", "P", "K", "temperature", "humidity", "ph", "rainfall", "label"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}")
    print(f"  Real dataset loaded: {len(df):,} rows | {df['label'].nunique()} crops")
    return df


def train(df: pd.DataFrame):
    # ── Features & target ──
    FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
    X = df[FEATURES].values
    y = df["label"].values

    # ── Encode labels ──
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    print(f"  Classes ({len(le.classes_)}): {', '.join(sorted(le.classes_))}")

    # ── Train / test split ──
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    # ── Model: Random Forest inside a pipeline with scaler ──
    # (RF is invariant to feature scale, but scaler helps if you swap to SVM later)
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    RandomForestClassifier(
            n_estimators     = 200,
            max_depth        = None,
            min_samples_leaf = 1,
            n_jobs           = -1,
            random_state     = 42,
        )),
    ])

    print("\n  Training Random Forest …")
    pipeline.fit(X_train, y_train)

    # ── Evaluate ──
    y_pred   = pipeline.predict(X_test)
    acc      = accuracy_score(y_test, y_pred)
    cv_scores= cross_val_score(pipeline, X, y_enc, cv=5, scoring="accuracy", n_jobs=-1)

    print(f"\n  Test accuracy  : {acc * 100:.2f}%")
    print(f"  CV accuracy    : {cv_scores.mean() * 100:.2f}% ± {cv_scores.std() * 100:.2f}%")
    print("\n  Per-class report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # ── Save ──
    joblib.dump(pipeline, MODEL_PATH)
    joblib.dump(le,       ENC_PATH)
    print(f"\n  ✅  Model saved  → {MODEL_PATH}")
    print(f"  ✅  Encoder saved → {ENC_PATH}")

    return pipeline, le


def predict_sample(pipeline, le):
    """Quick smoke-test with a known rice profile."""
    sample = np.array([[80, 40, 40, 25, 80, 6.5, 200]])  # → rice expected
    pred_idx  = pipeline.predict(sample)[0]
    pred_crop = le.inverse_transform([pred_idx])[0]
    proba     = pipeline.predict_proba(sample)[0]
    top3_idx  = np.argsort(proba)[::-1][:3]
    print("\n  Smoke-test (rice profile):")
    for i in top3_idx:
        print(f"    {le.classes_[i]:<15} {proba[i]*100:.1f}%")
    print(f"  → Prediction: {pred_crop}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",      help="Path to Crop_recommendation.csv")
    parser.add_argument("--synthetic", action="store_true",
                        help="Use built-in synthetic data (no CSV needed)")
    args = parser.parse_args()

    print("═" * 52)
    print("  AgroSage — Crop Recommendation Model Training")
    print("═" * 52)

    if args.data:
        print(f"\n  Loading real data from: {args.data}")
        df = load_real_data(args.data)
    else:
        print("\n  No CSV provided — generating synthetic data …")
        print("  (Download real data from Kaggle for production use)")
        df = generate_synthetic_data(samples_per_crop=220)

    pipeline, le = train(df)
    predict_sample(pipeline, le)
    print("\n  Done. ✓")
