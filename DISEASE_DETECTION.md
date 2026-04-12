# 🌿 AgroSage — Plant Disease Detection System

Complete implementation guide for the AI-powered plant disease detection module.

---

## Table of Contents

1. [Overview](#overview)
2. [Folder Structure](#folder-structure)
3. [How It Works](#how-it-works)
4. [Dataset Strategy](#dataset-strategy)
5. [Step-by-Step Setup](#step-by-step-setup)
6. [Training the Model](#training-the-model)
7. [Running Locally](#running-locally)
8. [API Reference](#api-reference)
9. [Confidence & OOD Logic](#confidence--ood-logic)
10. [Deployment Options](#deployment-options)
11. [Common Errors & Fixes](#common-errors--fixes)
12. [Future Improvements](#future-improvements)

---

## Overview

| Item | Detail |
|---|---|
| **Backbone** | EfficientNetB0 (ImageNet pre-trained) |
| **Technique** | Two-phase transfer learning |
| **Classes** | 38+ plant diseases (expandable) |
| **OOD Detection** | Entropy + max-softmax threshold |
| **Imbalance handling** | Sklearn inverse-frequency class weights |
| **API endpoint** | `POST /api/detect` (JWT-protected) |
| **Frontend changes** | ❌ Zero — existing UI works as-is |

---

## Folder Structure

```
agrosage/
├── app.py                          ← Updated (loads disease_classes.json + thresholds)
├── config.py                       ← Updated (DISEASE_CLASSES_PATH, thresholds)
├── requirements.txt                ← Updated (TF uncomment instructions)
│
├── api/
│   └── detect.py                   ← Updated (OOD, full 38-class DISEASE_INFO)
│
├── models/
│   ├── train_disease.py            ← Original (MobileNetV2) — kept for reference
│   ├── train_disease_v2.py         ← NEW: EfficientNetB0 — recommended
│   ├── predict_disease.py          ← NEW: standalone CLI for testing
│   ├── dataset_setup.py            ← NEW: dataset merge + stats utility
│   └── saved/
│       ├── disease_model.keras     ← Generated after training (primary)
│       ├── disease_model.h5        ← Generated after training (compatibility)
│       ├── disease_classes.json    ← Generated after training
│       └── disease_meta.json       ← Generated after training (thresholds, stats)
│
├── dataset/                        ← NEW: your training data goes here
│   └── raw/
│       ├── Apple___Apple_scab/
│       ├── Apple___Black_rot/
│       └── ... (one folder per class)
│
└── uploads/                        ← Auto-created: user-submitted images
```

> **Nothing else changed.** All frontend files, templates, existing API routes, and the crop model are untouched.

---

## How It Works

```
User uploads image via UI
         │
         ▼
POST /api/detect  (JWT-protected)
         │
         ▼
api/detect.py
  ├── Validate file type (JPG/PNG only)
  ├── Save to uploads/
  ├── If TF model loaded:
  │     ├── Preprocess: resize 224×224, EfficientNet normalise
  │     ├── model.predict() → softmax probabilities
  │     ├── Check max confidence < threshold → "Uncertain"
  │     ├── Check entropy > threshold → "Uncertain"
  │     └── Return top-5 predictions with plant/disease/severity
  └── If no TF model (stub mode):
        └── Return fixed demo prediction (UI still works)
         │
         ▼
Persist to DB (results table)
         │
         ▼
JSON response → frontend renders result card
```

---

## Dataset Strategy

### Why These Datasets?

| Dataset | Images | Classes | Type | When to Use |
|---|---|---|---|---|
| **PlantVillage** | ~87,000 | 38 | Lab (clean) | Always — foundation |
| **PlantDoc** | ~2,500 | 27 | Field (real-world) | Add for robustness |
| **New Plant Diseases** | ~87,000 | 38 | Augmented PV | Optional extra variety |
| **Plant Pathology 2020** | ~3,600 | 4 | High-quality field | Apple-specific boost |

**Recommended combination:** PlantVillage + PlantDoc  
PlantVillage gives volume; PlantDoc gives real-world generalization.

### Class Balance Strategy

PlantVillage has near-equal class sizes (~2,000/class), but mixing datasets creates imbalance.
The training script automatically:
1. Computes inverse-frequency class weights via `sklearn.utils.class_weight.compute_class_weight`
2. Passes them to `model.fit(class_weight=…)` — no manual resampling needed
3. You can also `--cap 2000` in `dataset_setup.py` to hard-cap large classes

### Train/Val/Test Split

```
70% Training  — model learns from this
15% Validation — tunes hyperparameters, early stopping
15% Test       — final honest evaluation (never seen during training)
```
All splits are **stratified** per class — every class has the same 70/15/15 ratio.

---

## Step-by-Step Setup

### Step 1 — Install dependencies

```bash
# Core dependencies (no TF yet):
pip install -r requirements.txt

# Then add TensorFlow for your hardware:
pip install tensorflow-cpu           # CPU only (slower, always works)
# OR
pip install tensorflow               # GPU (requires CUDA 11.8 or 12.x)
# OR (Mac M1/M2/M3)
pip install tensorflow-macos tensorflow-metal
```

### Step 2 — Download a dataset

**Option A: Kaggle CLI (recommended)**
```bash
pip install kaggle
# Place your kaggle.json in ~/.kaggle/
kaggle datasets download -d abdallahalidev/plantvillage-dataset
unzip plantvillage-dataset.zip -d /tmp/plantvillage

# Optional: add PlantDoc for real-world robustness
kaggle datasets download -d nirmalsankalana/plantdoc-dataset
unzip plantdoc-dataset.zip -d /tmp/plantdoc
```

**Option B: Manual**
1. Download from https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset
2. Extract the ZIP
3. Copy the class folders to `dataset/raw/`

### Step 3 — Prepare the dataset

```bash
# View dataset statistics:
python models/dataset_setup.py --stats /tmp/plantvillage/PlantVillage

# Merge PlantVillage + PlantDoc into dataset/raw:
python models/dataset_setup.py --merge \
    --sources /tmp/plantvillage/PlantVillage /tmp/plantdoc/train \
    --output dataset/raw \
    --cap 2000

# Verify the merged result:
python models/dataset_setup.py --stats dataset/raw
```

### Step 4 — Train the model

```bash
# Quick smoke-test on CPU (10 mins, ~200 imgs/class):
python models/train_disease_v2.py --data dataset/raw --fast

# Full training (GPU recommended, 1–3 hours):
python models/train_disease_v2.py --data dataset/raw

# Custom epochs:
python models/train_disease_v2.py --data dataset/raw --epochs1 15 --epochs2 25
```

Training saves:
- `models/saved/disease_model.keras` — primary model
- `models/saved/disease_model.h5` — compatibility version
- `models/saved/disease_classes.json` — ordered class list
- `models/saved/disease_meta.json` — thresholds + accuracy stats

### Step 5 — Test the model (optional)

```bash
# Single image test:
python models/predict_disease.py --image path/to/leaf.jpg

# Batch test a folder:
python models/predict_disease.py --folder path/to/test_images/

# Show top-5:
python models/predict_disease.py --image leaf.jpg --top 5
```

### Step 6 — Run the app

```bash
python app.py
# Open: http://localhost:5000
```

You should see in the logs:
```
Disease classes loaded ✓  (38 classes)
Disease thresholds loaded from meta.json  (conf≥0.65, ent≤0.50)
Disease model loaded ✓  [disease_model.h5]  classes=38
```

---

## Training the Model

### Two-Phase Training Explained

**Phase 1 — Head-only (fast convergence)**
- EfficientNetB0 backbone is frozen (weights not updated)
- Only the custom Dense layers are trained
- High learning rate (1e-3)
- Stops early when validation accuracy plateaus (patience=4)

**Phase 2 — Fine-tuning (accuracy refinement)**
- Top 30 layers of EfficientNetB0 are unfrozen
- Very low learning rate (5e-5) to avoid catastrophic forgetting
- Stops early (patience=6)
- Best checkpoint saved automatically

### Data Augmentation Applied

```python
RandomFlip("horizontal_and_vertical")   # mirrors
RandomRotation(0.25)                     # ±45 degrees
RandomZoom(0.20)                         # ±20% zoom
RandomTranslation(0.10, 0.10)           # ±10% shift
RandomBrightness(0.25)                  # ±25% brightness
RandomContrast(0.25)                    # ±25% contrast
GaussianNoise(0.05)                     # real-world noise injection
```

This augmentation is critical for bridging the lab→field domain gap.

### Expected Performance

| Dataset | Val Accuracy | Top-5 Accuracy |
|---|---|---|
| PlantVillage only | ~95–97% | ~99% |
| PlantVillage + PlantDoc | ~88–93% | ~97% |

Real-world performance on field photos will be lower (~75–85%). This is normal and honest — PlantDoc helps significantly.

---

## API Reference

### `POST /api/detect`

**Auth:** JWT Bearer token (same as all other protected endpoints)

**Request:**
```
Content-Type: multipart/form-data
Body: image=<file.jpg or file.png>  (max 16 MB)
```

**Success Response (200):**
```json
{
  "success":    true,
  "result_id":  42,
  "label":      "Tomato___Early_blight",
  "plant":      "Tomato",
  "disease":    "Early Blight",
  "severity":   "medium",
  "confidence": 91.4,
  "top5": [
    {"label": "Tomato___Early_blight",  "confidence": 91.4},
    {"label": "Tomato___Late_blight",   "confidence":  5.2},
    {"label": "Tomato___Bacterial_spot","confidence":  2.1},
    {"label": "Potato___Early_blight",  "confidence":  0.8},
    {"label": "Tomato___healthy",       "confidence":  0.5}
  ],
  "stub_mode":  false,
  "uncertain":  false
}
```

**Uncertain / OOD Response (200):**
```json
{
  "success":    true,
  "label":      "Unknown",
  "plant":      "Unknown",
  "disease":    "Uncertain — low confidence or non-leaf image",
  "severity":   "unknown",
  "confidence": 34.2,
  "uncertain":  true,
  "stub_mode":  false
}
```

**Error Responses:**

| Code | Reason |
|---|---|
| 400 | No image / bad file type |
| 401 | Missing or expired JWT |
| 500 | Model inference error |

### Severity Levels

| Level | Meaning |
|---|---|
| `none` | Plant is healthy |
| `medium` | Disease present, manageable |
| `high` | Serious — act quickly |
| `critical` | Immediate action required |
| `unknown` | Uncertain prediction |

---

## Confidence & OOD Logic

The system uses two signals to detect "unknown / invalid" images:

### 1. Maximum Softmax Probability (MSP)
If the top predicted class has probability < `DISEASE_CONF_THRESHOLD` (default: 0.65), the image is flagged as uncertain.

### 2. Predictive Entropy
Shannon entropy of the full probability distribution, normalised to [0, 1].  
If entropy > `DISEASE_ENT_THRESHOLD` (default: 0.50), prediction is uncertain.  
High entropy means the model is equally confused across many classes — a sign of an out-of-distribution input.

### Tuning Thresholds

After training, inspect `models/saved/disease_meta.json` which contains default values.  
You can override them via environment variables:

```bash
export DISEASE_CONF_THRESHOLD=0.70   # raise for stricter filtering
export DISEASE_ENT_THRESHOLD=0.45    # lower for stricter filtering
python app.py
```

---

## Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install tensorflow-cpu    # or tensorflow for GPU

# 2. Set up .env (copy from .env.example)
cp .env.example .env

# 3. (Optional) Train the model first
python models/train_disease_v2.py --data dataset/raw --fast

# 4. Run the server
python app.py
# → http://localhost:5000

# 5. Test the API
curl -X POST http://localhost:5000/api/health
```

**Stub mode (no TF / no trained model):**  
The app works immediately without any model file — it returns a fixed demo prediction with `"stub_mode": true`. The UI shows a notice.

---

## Deployment Options

### Option A — Render.com (free tier)
```yaml
# render.yaml
services:
  - type: web
    name: agrosage
    env: python
    buildCommand: pip install -r requirements.txt && pip install tensorflow-cpu
    startCommand: gunicorn -w 2 -b 0.0.0.0:$PORT "app:create_app()"
    envVars:
      - key: FLASK_ENV
        value: production
```

**Note:** Free Render instances have 512 MB RAM. TF CPU uses ~300–400 MB at inference.  
Use `tensorflow-cpu` (not full `tensorflow`) to stay within limits.

### Option B — Railway / Fly.io
Similar to Render. Set `FLASK_ENV=production` and `PORT` as env vars.

### Option C — Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir tensorflow-cpu
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:create_app()"]
```

### Optimising Model Size

| Technique | Size | Accuracy |
|---|---|---|
| Full .h5 model | ~20 MB | Baseline |
| TF-Lite conversion | ~6 MB | -0.5% |
| TF-Lite + quantization | ~3 MB | -1–2% |

Convert to TF-Lite after training:
```python
import tensorflow as tf
converter = tf.lite.TFLiteConverter.from_keras_model(
    tf.keras.models.load_model("models/saved/disease_model.keras")
)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()
with open("models/saved/disease_model.tflite", "wb") as f:
    f.write(tflite_model)
```

---

## Common Errors & Fixes

### ❌ `No module named 'tensorflow'`
```bash
pip install tensorflow-cpu    # always works
```

### ❌ `OOM (Out Of Memory) during training`
- Reduce batch size: edit `BATCH_SIZE = 16` in `train_disease_v2.py`
- Use `--fast` mode for smoke-tests
- Switch to `tensorflow-cpu` if GPU VRAM < 4 GB

### ❌ `Model not found: models/saved/disease_model.h5`
- You need to train first: `python models/train_disease_v2.py --data dataset/raw --fast`
- The app works in stub mode without the model (for development)

### ❌ `PIL.UnidentifiedImageError`
- Corrupt image in dataset. The training script skips per-class but may fail per-image.
- Pre-screen dataset: `python models/dataset_setup.py --stats dataset/raw`

### ❌ `UserWarning: No training configuration found`
- Loading a .h5 model saved without `model.compile()`. Safe to ignore — we re-compile before training, and inference doesn't need it.

### ❌ `CUDA_ERROR_OUT_OF_MEMORY` on GPU
```python
# Add at top of train_disease_v2.py
import tensorflow as tf
gpus = tf.config.list_physical_devices("GPU")
if gpus:
    tf.config.experimental.set_memory_growth(gpus[0], True)
```

### ❌ All predictions show `stub_mode: true` even after training
1. Check `models/saved/disease_model.h5` exists
2. Check `DISEASE_MODEL_PATH` in config.py resolves correctly
3. Check Flask logs for `Disease model loaded ✓` or any load errors

### ❌ Very low confidence on real photos
- Add PlantDoc dataset: real-world field images dramatically improve field performance
- Lower `DISEASE_CONF_THRESHOLD=0.50` via env var to be less strict
- Ensure images are well-lit and the leaf fills most of the frame

---

## Future Improvements

### 🔗 1. Crop Recommendation Integration
Cross-reference detected disease with the crop recommendation model:
- If user's field soil + climate data is stored, after detecting "Tomato___Late_blight"
  suggest resistant tomato varieties that suit their specific conditions.
- API: combine `/api/detect` response with `/api/recommend` to give a combined action plan.

### 🌤️ 2. Weather-Based Insights
The weather module (`utils/weather.py`) already fetches real-time data.
- Blight spreads rapidly in cool (10–20°C) + humid (>80%) conditions
- After detection, check current weather and warn: "⚠️ Conditions favour rapid Late Blight spread"
- Add `weather_risk` field to `/api/detect` response

### 📱 3. IoT Sensor Integration
- Add MQTT / REST endpoints to accept data from field sensors
- Auto-trigger disease scan when humidity > threshold for N consecutive hours
- Store time-series data to track disease progression per field

### 🗺️ 4. Field Heatmap
- Link detected diseases to GPS coordinates (Field model already has lat/lon)
- Display disease occurrence heatmap on a map (Leaflet.js / Google Maps)
- Alert when disease clusters appear (neighbour field correlation)

### 🔄 5. Active Learning Loop
- Flag low-confidence predictions for user verification
- Store corrected labels → periodically retrain with user-validated data
- Confidence improves over time for your specific region and crop types

### 🌍 6. Multi-Language Disease Names
- Add localised disease name lookup (Hindi, regional Indian languages)
- Especially valuable for the target AgroSage farmer audience

---

*DISEASE_DETECTION.md — AgroSage v2*
