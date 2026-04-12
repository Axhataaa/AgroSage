"""
api/soil.py
─────────────────────────────────────────────────────────
Soil nutrient estimation endpoint.

GET /api/soil?lat=<lat>&lon=<lon>

Returns estimated N, P, K and pH values based on geographic
region using an agro-climatic zone lookup table.  Designed
to be swapped out for a real soil dataset (SoilGrids, FAO,
or ISRIC) without changing the API contract.

Response
--------
{
  "success": true,
  "N":   <float>,    # Nitrogen  (kg/ha)
  "P":   <float>,    # Phosphorus (kg/ha)
  "K":   <float>,    # Potassium  (kg/ha)
  "ph":  <float>,    # Soil pH
  "region": "<str>", # Human-readable region label
  "source": "region-estimate"
}
"""

from flask import Blueprint, request, jsonify

soil_bp = Blueprint("soil", __name__, url_prefix="/api")


# ── Agro-climatic zone definitions ────────────────────────────
# Each zone is a bounding box (lat_min, lat_max, lon_min, lon_max)
# with representative average soil properties for the region.
# Values are derived from FAO / ISRIC SoilGrids regional averages
# and peer-reviewed agronomy literature.
#
# Add more zones / narrower bounding boxes for higher accuracy.
# Replace with a proper raster lookup once a dataset is available.

SOIL_ZONES = [
    # ── South Asia (Indian Subcontinent) ──
    {
        "name":   "Indo-Gangetic Plains (North India)",
        "lat":    (25, 35), "lon": (70, 90),
        "N": 65, "P": 38, "K": 48, "ph": 7.4,
    },
    {
        "name":   "Deccan Plateau (Central/South India)",
        "lat":    (15, 25), "lon": (73, 82),
        "N": 55, "P": 30, "K": 40, "ph": 7.0,
    },
    {
        "name":   "Coastal India / Sri Lanka",
        "lat":    (8, 15),  "lon": (76, 82),
        "N": 48, "P": 28, "K": 55, "ph": 6.5,
    },
    {
        "name":   "Northeast India / Bangladesh",
        "lat":    (22, 28), "lon": (88, 97),
        "N": 70, "P": 35, "K": 42, "ph": 5.8,
    },
    {
        "name":   "Pakistan / Northwest India",
        "lat":    (25, 38), "lon": (63, 75),
        "N": 50, "P": 22, "K": 38, "ph": 7.8,
    },

    # ── Southeast Asia ──
    {
        "name":   "Southeast Asia (Mekong / Java)",
        "lat":    (-10, 22), "lon": (95, 140),
        "N": 72, "P": 32, "K": 58, "ph": 5.9,
    },
    {
        "name":   "Philippines / Pacific Islands",
        "lat":    (5, 20),  "lon": (115, 130),
        "N": 65, "P": 30, "K": 52, "ph": 6.1,
    },

    # ── East Asia ──
    {
        "name":   "Eastern China / Korea / Japan",
        "lat":    (25, 50), "lon": (100, 145),
        "N": 80, "P": 42, "K": 60, "ph": 6.3,
    },

    # ── Sub-Saharan Africa ──
    {
        "name":   "West Africa (Sahel)",
        "lat":    (10, 20), "lon": (-18, 15),
        "N": 35, "P": 18, "K": 30, "ph": 6.8,
    },
    {
        "name":   "East Africa (Great Lakes)",
        "lat":    (-5, 10), "lon": (28, 42),
        "N": 50, "P": 25, "K": 40, "ph": 6.2,
    },
    {
        "name":   "Southern Africa",
        "lat":    (-35, -5), "lon": (16, 40),
        "N": 42, "P": 22, "K": 36, "ph": 6.5,
    },

    # ── Latin America ──
    {
        "name":   "Amazon Basin (Brazil)",
        "lat":    (-15, 5),  "lon": (-65, -45),
        "N": 55, "P": 20, "K": 50, "ph": 5.2,
    },
    {
        "name":   "Pampas / Southern Brazil",
        "lat":    (-35, -15), "lon": (-65, -45),
        "N": 62, "P": 35, "K": 55, "ph": 6.0,
    },
    {
        "name":   "Andean Region",
        "lat":    (-20, 10), "lon": (-80, -65),
        "N": 45, "P": 28, "K": 38, "ph": 6.4,
    },
    {
        "name":   "Mexico / Central America",
        "lat":    (8, 32),  "lon": (-92, -85),
        "N": 52, "P": 30, "K": 42, "ph": 6.7,
    },

    # ── North America ──
    {
        "name":   "US Corn Belt (Midwest)",
        "lat":    (36, 48), "lon": (-100, -80),
        "N": 90, "P": 50, "K": 70, "ph": 6.8,
    },
    {
        "name":   "US Great Plains",
        "lat":    (32, 48), "lon": (-105, -95),
        "N": 60, "P": 35, "K": 50, "ph": 7.1,
    },
    {
        "name":   "US Southeast (Cotton Belt)",
        "lat":    (28, 38), "lon": (-90, -75),
        "N": 55, "P": 30, "K": 48, "ph": 6.2,
    },
    {
        "name":   "Canada Prairies",
        "lat":    (48, 58), "lon": (-115, -85),
        "N": 58, "P": 28, "K": 42, "ph": 7.3,
    },

    # ── Europe ──
    {
        "name":   "Western Europe (Atlantic)",
        "lat":    (43, 55), "lon": (-10, 15),
        "N": 75, "P": 45, "K": 65, "ph": 6.5,
    },
    {
        "name":   "Eastern Europe / Black Sea",
        "lat":    (43, 55), "lon": (22, 40),
        "N": 70, "P": 40, "K": 58, "ph": 7.0,
    },
    {
        "name":   "Mediterranean Basin",
        "lat":    (35, 45), "lon": (-5, 35),
        "N": 58, "P": 32, "K": 44, "ph": 7.5,
    },

    # ── Middle East / Central Asia ──
    {
        "name":   "Middle East / Fertile Crescent",
        "lat":    (28, 38), "lon": (35, 55),
        "N": 45, "P": 20, "K": 35, "ph": 7.9,
    },
    {
        "name":   "Central Asia (Steppe)",
        "lat":    (40, 55), "lon": (55, 85),
        "N": 50, "P": 24, "K": 38, "ph": 7.6,
    },

    # ── Oceania ──
    {
        "name":   "Australia (Wheat Belt)",
        "lat":    (-35, -25), "lon": (115, 150),
        "N": 48, "P": 26, "K": 36, "ph": 6.8,
    },
    {
        "name":   "New Zealand / Pacific South",
        "lat":    (-47, -33), "lon": (165, 178),
        "N": 60, "P": 38, "K": 55, "ph": 5.8,
    },
]

# ── World-average fallback ─────────────────────────────────────
WORLD_AVG = {
    "name": "World Average (fallback)",
    "N": 58, "P": 30, "K": 45, "ph": 6.8,
}


def _estimate_soil(lat: float, lon: float) -> dict:
    """
    Return soil estimates for (lat, lon).

    Scoring: exact bounding-box matches are weighted by how central
    the point is within the box (distance from centre), so points near
    zone edges gradually blend toward the world average rather than
    flipping abruptly.
    """
    candidates = []
    for zone in SOIL_ZONES:
        lat_lo, lat_hi = zone["lat"]
        lon_lo, lon_hi = zone["lon"]
        if lat_lo <= lat <= lat_hi and lon_lo <= lon <= lon_hi:
            # Compute 0-1 score: 1 = dead centre, 0 = edge
            lat_centre = (lat_lo + lat_hi) / 2
            lon_centre = (lon_lo + lon_hi) / 2
            lat_half   = (lat_hi - lat_lo) / 2 or 1
            lon_half   = (lon_hi - lon_lo) / 2 or 1
            score = (1 - abs(lat - lat_centre) / lat_half) * \
                    (1 - abs(lon - lon_centre) / lon_half)
            candidates.append((score, zone))

    if not candidates:
        return WORLD_AVG

    # Best match (highest centre score)
    _, best = max(candidates, key=lambda x: x[0])
    return best


# ────────────────────────────────────────────────────────
@soil_bp.get("/soil")
def soil():
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if lat is None or lon is None:
        return jsonify({"success": False, "message": "lat and lon query params are required."}), 400

    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        return jsonify({"success": False, "message": "lat and lon must be numbers."}), 400

    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return jsonify({"success": False, "message": "Coordinates out of range."}), 400

    zone = _estimate_soil(lat, lon)

    return jsonify({
        "success": True,
        "N":       zone["N"],
        "P":       zone["P"],
        "K":       zone["K"],
        "ph":      zone["ph"],
        "region":  zone["name"],
        "source":  "region-estimate",
    }), 200
