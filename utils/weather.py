"""
utils/weather.py
─────────────────────────────────────────────────────────
Fetches current weather data from Open-Meteo (free, no API key).
Used by the frontend's "Detect My Field" auto-fill flow.

GET /api/weather?lat=<lat>&lon=<lon>
"""

import urllib.request
import urllib.parse
import json

from flask import Blueprint, request, jsonify

weather_bp = Blueprint("weather", __name__, url_prefix="/api")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_weather(lat: float, lon: float) -> dict:
    """
    Call Open-Meteo and return the fields AgroSage needs:
      - temperature  (°C, current)
      - humidity     (%, current relative humidity)
      - rainfall     (mm, last 7-day total — proxy for annual trend)

    Open-Meteo docs: https://open-meteo.com/en/docs
    """
    params = {
        "latitude":        lat,
        "longitude":       lon,
        "current":         "temperature_2m,relative_humidity_2m,precipitation",
        "daily":           "precipitation_sum",
        "past_days":       7,
        "forecast_days":   1,
        "timezone":        "auto",
    }

    url = OPEN_METEO_URL + "?" + urllib.parse.urlencode(params, doseq=True)

    req      = urllib.request.Request(url, headers={"User-Agent": "AgroSage/1.0"})
    response = urllib.request.urlopen(req, timeout=8)
    data     = json.loads(response.read())

    current   = data.get("current", {})
    daily     = data.get("daily",   {})
    precip_7d = sum(daily.get("precipitation_sum", [0]) or [0])

    # Scale 7-day rainfall to rough annual estimate for the model
    # (avg mm/day × 365). This is a coarse proxy — real app should
    # use a climatological rainfall dataset (WorldClim, etc.)
    avg_daily_mm  = precip_7d / 7 if precip_7d else 0
    annual_est_mm = round(avg_daily_mm * 365, 1)

    return {
        "temperature": current.get("temperature_2m"),
        "humidity":    current.get("relative_humidity_2m"),
        "rainfall":    annual_est_mm,
        "source":      "Open-Meteo",
    }


# ────────────────────────────────────────────────────────
@weather_bp.get("/weather")
def weather():
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

    try:
        result = fetch_weather(lat, lon)
        return jsonify({"success": True, **result}), 200
    except Exception as exc:
        return jsonify({"success": False, "message": f"Weather fetch failed: {str(exc)}"}), 502
