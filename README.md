# 🌾 AgroSage — AI-Powered Crop Advisory Platform

A production-ready Flask + ML web application providing:

- **Crop Recommendation** — Random Forest model (7 soil + climate parameters)
- **Disease Detection** — CNN leaf-image analysis (stub mode if TF not installed)
- **Weather Auto-fill** — Open-Meteo API (free, no key required)
- **Soil Nutrient Auto-fill** — Region-based estimation from GPS coordinates
- **Analytics Dashboard** — Real ML feature importances from trained model
- **Authentication** — JWT tokens, bcrypt passwords, SQLite/PostgreSQL

---

## 🚀 Quick Start

```bash
# 1. Clone / unzip the project
cd agrosage_v2

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY and JWT_SECRET_KEY at minimum

# 5. Train the crop model (required before first use)
python models/train_crop.py --synthetic
# For production: download Kaggle dataset then run:
# python models/train_crop.py --data Crop_recommendation.csv

# 6. Start the server
python app.py
# Visit: http://localhost:5000
```

---

## 📡 API Reference

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/auth/signup` | POST | — | Create account, returns JWT |
| `/api/auth/login` | POST | — | Verify credentials, returns JWT |
| `/api/auth/me` | GET | JWT | Current user profile |
| `/api/recommend` | POST | JWT | Crop recommendation |
| `/api/history` | GET | JWT | Past recommendations |
| `/api/detect` | POST | JWT | Plant disease detection |
| `/api/weather` | GET | — | Weather by lat/lon |
| `/api/soil` | GET | — | Soil nutrients by lat/lon |
| `/api/importance` | GET | — | ML feature importances |
| `/api/stats` | GET | — | Model metadata |
| `/api/health` | GET | — | System health check |

### POST `/api/recommend`
```json
{
  "N": 80, "P": 40, "K": 45,
  "temperature": 25, "humidity": 70,
  "ph": 6.5, "rainfall": 180
}
```
Returns: `{ top_crop, confidence, alternatives[], field, result_id }`

### GET `/api/soil?lat=26.9&lon=75.8`
Returns: `{ N, P, K, ph, region, source }`

### GET `/api/importance`
Returns: `{ source: "model"|"fallback", features: [{key, label, score, pct}] }`

---

## 🏗 Architecture

```
agrosage_v2/
├── app.py                    # Flask factory + blueprint registration
├── config.py                 # All configuration (env-driven)
├── requirements.txt
├── .env.example
│
├── api/
│   ├── auth.py               # POST /api/auth/signup, /login, GET /me
│   ├── recommend.py          # POST /api/recommend, GET /api/history
│   ├── detect.py             # POST /api/detect
│   ├── soil.py               # GET  /api/soil       ← NEW
│   └── analytics.py          # GET  /api/importance, /api/stats  ← NEW
│
├── utils/
│   └── weather.py            # GET  /api/weather
│
├── db/
│   └── models.py             # SQLAlchemy ORM (User, Field, Result)
│
├── models/
│   ├── train_crop.py         # Training script (--synthetic or --data CSV)
│   ├── train_disease.py      # TF training script (optional)
│   └── saved/
│       ├── crop_model.pkl         # Trained after running train_crop.py
│       └── crop_label_encoder.pkl
│
├── templates/
│   ├── index.html            # Main SPA
│   ├── login.html
│   └── signup.html
│
└── static/
    ├── css/                  # Stylesheets
    └── js/
        ├── api.js            # API client (BASE_URL, token management)
        ├── geolocation.js    # Weather + Soil auto-fill ← UPDATED
        ├── charts.js         # Backend-driven importance chart ← UPDATED
        ├── recommend.js      # Backend-only predictions ← UPDATED
        ├── detect.js         # Backend-only detection ← UPDATED
        └── ...
```

---

## 🌿 Disease Detection

The disease model runs in **stub mode** by default (no TensorFlow required).
This returns a realistic demo response so the UI works during development.

To enable real inference:
1. `pip install tensorflow>=2.14.0`
2. Train or download a PlantVillage model:
   ```bash
   python models/train_disease.py
   ```
3. Place the model at `models/saved/disease_model.h5`
4. Restart the server — it auto-detects the file.

---

## 🌍 Soil Estimation

`GET /api/soil?lat=&lon=` uses a bounding-box lookup table covering 25+
agro-climatic zones worldwide (South Asia, SE Asia, Africa, Americas,
Europe, Oceania).

**To improve accuracy**, replace `api/soil.py` with a raster lookup against:
- [ISRIC SoilGrids REST API](https://www.isric.org/explore/soilgrids)
- [FAO Global Soil Database](http://www.fao.org/soils-portal/)
- Custom CSV keyed on country/admin region

The API contract (`N, P, K, ph, region, source`) stays the same.

---

## 🗃 Database

SQLite by default (`agrosage.db` in project root).
For PostgreSQL (Render, Railway, Supabase):
```dotenv
DATABASE_URL=postgresql://user:pass@host:5432/agrosage
```

---

## 🔑 Environment Variables

Copy `.env.example` → `.env` and fill in:

```dotenv
SECRET_KEY=<random 32+ char string>
JWT_SECRET_KEY=<different random string>
FLASK_ENV=development       # or production
DATABASE_URL=sqlite:///agrosage.db
ALLOWED_ORIGINS=http://localhost:5000
```
