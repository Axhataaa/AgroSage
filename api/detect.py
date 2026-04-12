import os, uuid, json, math
import numpy as np

from flask              import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.models          import Result

detect_bp = Blueprint("detect", __name__, url_prefix="/api")

ALLOWED_EXTENSIONS  = {"jpg", "jpeg", "png"}
LEAF_SCORE_THRESHOLD = 0.08   # fraction of plant-like pixels required

# ──────────────────────────────────────────────────────────────
#  DISEASE_INFO
#  Keys MUST exactly match the class names in disease_classes.json
#  (which is what the trained model uses).
# ──────────────────────────────────────────────────────────────
DISEASE_INFO: dict = {

    # ── APPLE ──────────────────────────────────────────────────
    "Apple___Black_Rot": {
        "plant": "Apple", "disease": "Black Rot", "severity": "high",
        "description": "Botryosphaeria obtusa causes circular brown spots with purple borders on leaves and fruit.",
        "treatment": "Prune infected limbs; apply captan or thiophanate-methyl fungicide.",
        "prevention": "Remove mummified fruits and dead wood; maintain proper tree nutrition.",
    },
    "Apple___Cedar_Rust": {
        "plant": "Apple", "disease": "Cedar Apple Rust", "severity": "medium",
        "description": "Gymnosporangium juniperi-virginianae — requires juniper as alternate host.",
        "treatment": "Apply myclobutanil during pink bud to petal-fall stage.",
        "prevention": "Remove nearby juniper or cedar trees; plant rust-resistant apple varieties.",
    },
    "Apple___Healthy": {
        "plant": "Apple", "disease": "Healthy", "severity": "none",
        "description": "No disease detected. Apple leaf appears healthy.",
        "treatment": "No treatment required.",
        "prevention": "Continue regular monitoring and preventive fungicide schedule.",
    },
    "Apple___Scab": {
        "plant": "Apple", "disease": "Apple Scab", "severity": "medium",
        "description": "Venturia inaequalis fungal infection causing olive-brown scabby lesions.",
        "treatment": "Apply myclobutanil or captan fungicide from bud break to petal fall.",
        "prevention": "Rake fallen leaves; plant resistant varieties; ensure air circulation.",
    },

    # ── BANANA ─────────────────────────────────────────────────
    "Banana___Cordana": {
        "plant": "Banana", "disease": "Cordana Leaf Spot", "severity": "medium",
        "description": "Cordana musae causes brown oval spots with yellow halos, mostly on older leaves.",
        "treatment": "Apply mancozeb or copper-based fungicide; remove severely infected leaves.",
        "prevention": "Avoid overhead irrigation; improve drainage; remove dead leaf debris.",
    },
    "Banana___Healthy": {
        "plant": "Banana", "disease": "Healthy", "severity": "none",
        "description": "No disease detected. Banana leaf appears healthy.",
        "treatment": "No treatment required.",
        "prevention": "Regular inspection; maintain field sanitation; balanced fertilisation.",
    },
    "Banana___Pestalotiopsis": {
        "plant": "Banana", "disease": "Pestalotiopsis Leaf Spot", "severity": "medium",
        "description": "Pestalotiopsis species cause grey-brown lesions with dark borders and fruiting bodies.",
        "treatment": "Remove infected leaves; apply copper oxychloride fungicide.",
        "prevention": "Avoid mechanical injury; ensure proper plant spacing for airflow.",
    },
    "Banana___Sigatoka": {
        "plant": "Banana", "disease": "Black Sigatoka (Black Leaf Streak)", "severity": "high",
        "description": "Mycosphaerella fijiensis — the most destructive banana fungal disease globally.",
        "treatment": "Systemic fungicides (propiconazole, trifloxystrobin) applied on schedule.",
        "prevention": "Use disease-resistant varieties; remove infected leaves; adequate plant spacing.",
    },

    # ── CORN / MAIZE ───────────────────────────────────────────
    "Corn___Cercospora_Leaf_Spot": {
        "plant": "Corn", "disease": "Gray Leaf Spot (Cercospora)", "severity": "high",
        "description": "Cercospora zeae-maydis causes long rectangular tan lesions bounded by leaf veins.",
        "treatment": "Apply azoxystrobin or pyraclostrobin at early tasseling.",
        "prevention": "Plant resistant hybrids; rotate crops; avoid minimum tillage in high-risk areas.",
    },
    "Corn___Common_Rust": {
        "plant": "Corn", "disease": "Common Rust", "severity": "medium",
        "description": "Puccinia sorghi causing cinnamon-brown pustules on both leaf surfaces.",
        "treatment": "Apply triazole fungicide (propiconazole) if disease appears before tasseling.",
        "prevention": "Plant resistant varieties; early planting to avoid rust-favourable conditions.",
    },
    "Corn___Healthy": {
        "plant": "Corn", "disease": "Healthy", "severity": "none",
        "description": "No disease detected. Corn leaf appears healthy.",
        "treatment": "No treatment required.",
        "prevention": "Regular scouting from V5 stage; maintain balanced nitrogen nutrition.",
    },
    "Corn___Northern_Leaf_Blight": {
        "plant": "Corn", "disease": "Northern Leaf Blight", "severity": "medium",
        "description": "Exserohilum turcicum causing cigar-shaped grey-green lesions 2.5–15 cm long.",
        "treatment": "Propiconazole or azoxystrobin fungicide at early tasseling.",
        "prevention": "Resistant hybrids most effective; crop rotation; proper field drainage.",
    },

    # ── GRAPE ──────────────────────────────────────────────────
    "Grape___Black_Rot": {
        "plant": "Grape", "disease": "Black Rot", "severity": "high",
        "description": "Guignardia bidwellii causing brown circular lesions with black pycnidia dots.",
        "treatment": "Apply myclobutanil or mancozeb every 10–14 days from bud break.",
        "prevention": "Remove mummified berries; prune for air circulation; avoid wetting leaves.",
    },
    "Grape___Esca_Black_Measles": {
        "plant": "Grape", "disease": "Esca (Black Measles)", "severity": "high",
        "description": "Wood-decaying fungi complex — chronic vascular disease causing tiger-stripe leaf patterns.",
        "treatment": "No chemical cure. Remove heavily infected vines.",
        "prevention": "Protect pruning wounds with fungicide paste; use disease-free planting material.",
    },
    "Grape___Healthy": {
        "plant": "Grape", "disease": "Healthy", "severity": "none",
        "description": "No disease detected. Grape leaf appears healthy.",
        "treatment": "No treatment required.",
        "prevention": "Preventive fungicide program from bud break; regular canopy management.",
    },
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": {
        "plant": "Grape", "disease": "Leaf Blight (Isariopsis Leaf Spot)", "severity": "medium",
        "description": "Pseudocercospora vitis causing dark brown angular leaf spots.",
        "treatment": "Apply copper-based fungicide or mancozeb at first symptom.",
        "prevention": "Improve canopy ventilation; avoid excessive vegetative growth.",
    },

    # ── MANGO ──────────────────────────────────────────────────
    "Mango___Anthracnose": {
        "plant": "Mango", "disease": "Anthracnose", "severity": "high",
        "description": "Colletotrichum gloeosporioides causes dark angular leaf spots and blossom blight.",
        "treatment": "Apply carbendazim or mancozeb at 15-day intervals during flowering.",
        "prevention": "Prune for airflow; avoid overhead irrigation; remove infected debris.",
    },
    "Mango___Bacterial_Canker": {
        "plant": "Mango", "disease": "Bacterial Canker", "severity": "high",
        "description": "Xanthomonas campestris pv. mangiferaeindicae causes water-soaked lesions that turn brown.",
        "treatment": "Copper-based bactericide sprays; prune and destroy infected material.",
        "prevention": "Use disease-free planting material; avoid mechanical injury; field sanitation.",
    },
    "Mango___Cutting_Weevil": {
        "plant": "Mango", "disease": "Cutting Weevil (Leaf Damage)", "severity": "medium",
        "description": "Deporaus marginatus weevil cuts leaves in characteristic semicircular patterns.",
        "treatment": "Apply chlorpyrifos or imidacloprid insecticide during new flush emergence.",
        "prevention": "Collect and destroy cut leaves; maintain field sanitation.",
    },
    "Mango___Die_Back": {
        "plant": "Mango", "disease": "Die Back", "severity": "high",
        "description": "Lasiodiplodia theobromae causes twig and branch dieback from tips downward.",
        "treatment": "Prune infected branches 15 cm below visible symptoms; apply copper paste on cuts.",
        "prevention": "Avoid water stress and mechanical injury; balanced fertilisation.",
    },
    "Mango___Gall_Midge": {
        "plant": "Mango", "disease": "Gall Midge", "severity": "medium",
        "description": "Procontarinia mangicola midge larvae cause spindle-shaped galls on young leaves.",
        "treatment": "Apply dimethoate or lambda-cyhalothrin at bud break.",
        "prevention": "Destroy infected leaves; synchronise pruning to break pest cycle.",
    },
    "Mango___Healthy": {
        "plant": "Mango", "disease": "Healthy", "severity": "none",
        "description": "No disease detected. Mango leaf appears healthy.",
        "treatment": "No treatment required.",
        "prevention": "Regular scouting; preventive copper sprays before flowering.",
    },
    "Mango___Powdery_Mildew": {
        "plant": "Mango", "disease": "Powdery Mildew", "severity": "medium",
        "description": "Oidium mangiferae causes white powdery coating on young leaves, flowers, and fruit.",
        "treatment": "Apply wettable sulfur or hexaconazole fungicide at first sign.",
        "prevention": "Ensure good air circulation; avoid excessive nitrogen fertilisation.",
    },
    "Mango___Sooty_Mould": {
        "plant": "Mango", "disease": "Sooty Mould", "severity": "low",
        "description": "Black fungal growth (Capnodium spp.) on honeydew secreted by sap-sucking insects.",
        "treatment": "Control the causal insect (mealybug, scale, aphid) with insecticide.",
        "prevention": "Regular monitoring for sap-sucking pests; ant control.",
    },

    # ── PEACH ──────────────────────────────────────────────────
    "Peach___Bacterial_spot": {
        "plant": "Peach", "disease": "Bacterial Spot", "severity": "medium",
        "description": "Xanthomonas arboricola pv. pruni causing water-soaked spots turning purple-brown.",
        "treatment": "Apply copper-based bactericide at shuck split; repeated applications required.",
        "prevention": "Plant resistant varieties; avoid overhead irrigation; windbreaks help.",
    },
    "Peach___Healthy": {
        "plant": "Peach", "disease": "Healthy", "severity": "none",
        "description": "No disease detected. Peach leaf appears healthy.",
        "treatment": "No treatment required.",
        "prevention": "Annual copper sprays at leaf fall and bud swell as preventive measure.",
    },

    # ── PEPPER ─────────────────────────────────────────────────
    "Pepper__bell___Bacterial_spot": {
        "plant": "Pepper (Bell)", "disease": "Bacterial Spot", "severity": "medium",
        "description": "Xanthomonas euvesicatoria causing small water-soaked leaf and fruit spots.",
        "treatment": "Copper hydroxide + mancozeb combination sprays; no curative option.",
        "prevention": "Use certified disease-free seed; avoid working in wet fields; rotate crops.",
    },
    "Pepper__bell___Healthy": {
        "plant": "Pepper (Bell)", "disease": "Healthy", "severity": "none",
        "description": "No disease detected. Pepper leaf appears healthy.",
        "treatment": "No treatment required.",
        "prevention": "Use certified transplants; stake plants for airflow; balanced fertilisation.",
    },

    # ── POTATO ─────────────────────────────────────────────────
    "Potato___Early_blight": {
        "plant": "Potato", "disease": "Early Blight", "severity": "medium",
        "description": "Alternaria solani causing target-board dark lesions on older foliage.",
        "treatment": "Apply chlorothalonil or mancozeb every 7–10 days in humid weather.",
        "prevention": "Plant certified seed; adequate nitrogen; crop rotation every 2 years.",
    },
    "Potato___Healthy": {
        "plant": "Potato", "disease": "Healthy", "severity": "none",
        "description": "No disease detected. Potato leaf appears healthy.",
        "treatment": "No treatment required.",
        "prevention": "Scout weekly during humid periods; destroy volunteer plants.",
    },
    "Potato___Late_blight": {
        "plant": "Potato", "disease": "Late Blight", "severity": "high",
        "description": "Phytophthora infestans — most devastating potato disease globally.",
        "treatment": "Apply cymoxanil+mancozeb or metalaxyl immediately; destroy infected haulm.",
        "prevention": "Resistant varieties; prophylactic sprays in blight season.",
    },

    # ── RICE ───────────────────────────────────────────────────
    "Rice___Bacterial_Leaf_Blight": {
        "plant": "Rice", "disease": "Bacterial Leaf Blight", "severity": "high",
        "description": "Xanthomonas oryzae pv. oryzae causes water-soaked leaf margins that turn yellow-white.",
        "treatment": "No effective chemical cure. Remove heavily infected plants promptly.",
        "prevention": "Use resistant varieties; balanced nitrogen; avoid excess water on leaves.",
    },
    "Rice___Brown_Spot": {
        "plant": "Rice", "disease": "Brown Spot", "severity": "medium",
        "description": "Helminthosporium oryzae causes oval brown spots with grey centres on leaves.",
        "treatment": "Apply mancozeb or iprodione fungicide at first symptom.",
        "prevention": "Balanced potassium nutrition; avoid water stress; use certified seed.",
    },
    "Rice___Healthy": {
        "plant": "Rice", "disease": "Healthy", "severity": "none",
        "description": "No disease detected. Rice leaf appears healthy.",
        "treatment": "No treatment required.",
        "prevention": "Regular field scouting; balanced NPK; proper water management.",
    },
    "Rice___Leaf_Blast": {
        "plant": "Rice", "disease": "Leaf Blast", "severity": "high",
        "description": "Magnaporthe oryzae (Pyricularia oryzae) causes diamond-shaped grey lesions on leaves.",
        "treatment": "Apply tricyclazole or isoprothiolane at first symptom and repeat in 7 days.",
        "prevention": "Resistant varieties; avoid excess nitrogen; ensure good field drainage.",
    },
    "Rice___Leaf_Scald": {
        "plant": "Rice", "disease": "Leaf Scald", "severity": "medium",
        "description": "Microdochium oryzae causes tan-coloured scalded areas along leaf edges.",
        "treatment": "Apply propiconazole fungicide; drain fields during severe outbreaks.",
        "prevention": "Balanced fertilisation; avoid dense planting; use tolerant varieties.",
    },
    "Rice___Narrow_Brown_Spot": {
        "plant": "Rice", "disease": "Narrow Brown Spot", "severity": "low",
        "description": "Cercospora janseana causes narrow brown streaks running along leaf veins.",
        "treatment": "Apply mancozeb if severe; usually manageable with good crop nutrition.",
        "prevention": "Avoid late nitrogen applications; ensure adequate potassium levels.",
    },

    # ── TOMATO ─────────────────────────────────────────────────
    "Tomato___Bacterial_spot": {
        "plant": "Tomato", "disease": "Bacterial Spot", "severity": "medium",
        "description": "Xanthomonas perforans — spreads rapidly in warm, humid conditions.",
        "treatment": "Copper hydroxide sprays. Focus on prevention; no effective chemical cure.",
        "prevention": "Certified disease-free seed; avoid working in wet fields; disinfect tools.",
    },
    "Tomato___Early_blight": {
        "plant": "Tomato", "disease": "Early Blight", "severity": "medium",
        "description": "Alternaria solani causing concentric ring lesions on lower leaves.",
        "treatment": "Copper-based fungicide or mancozeb every 7–10 days; remove infected leaves.",
        "prevention": "Rotate crops every 2 years; maintain plant spacing; avoid overhead irrigation.",
    },
    "Tomato___Healthy": {
        "plant": "Tomato", "disease": "Healthy", "severity": "none",
        "description": "No disease detected. Tomato leaf appears healthy.",
        "treatment": "No treatment required.",
        "prevention": "Regular scouting; remove lower leaves as plants grow; balanced nutrition.",
    },
    "Tomato___Late_blight": {
        "plant": "Tomato", "disease": "Late Blight", "severity": "high",
        "description": "Phytophthora infestans — same pathogen as the Irish Potato Famine.",
        "treatment": "Metalaxyl+mancozeb or chlorothalonil immediately. Destroy infected plants.",
        "prevention": "Use resistant varieties; avoid overhead irrigation; monitor cool/moist conditions.",
    },
    "Tomato___Leaf_Mold": {
        "plant": "Tomato", "disease": "Leaf Mold", "severity": "medium",
        "description": "Passalora fulva (Cladosporium fulvum) — olive-green mould on leaf undersides.",
        "treatment": "Apply chlorothalonil or copper fungicide; reduce greenhouse humidity.",
        "prevention": "Good ventilation; remove lower leaves; resistant varieties.",
    },
    "Tomato___Septoria_leaf_spot": {
        "plant": "Tomato", "disease": "Septoria Leaf Spot", "severity": "medium",
        "description": "Septoria lycopersici causing small circular spots with dark borders and grey centres.",
        "treatment": "Apply mancozeb or chlorothalonil at 7–10 day intervals; remove infected leaves.",
        "prevention": "Crop rotation; avoid overhead irrigation; remove plant debris.",
    },
    "Tomato___Spider_mites_Two_spotted_spider_mite": {
        "plant": "Tomato", "disease": "Spider Mites (Two-spotted)", "severity": "medium",
        "description": "Tetranychus urticae — a pest (not fungal) causing stippled yellowing of leaves.",
        "treatment": "Miticide (abamectin, bifenazate); increase humidity; predatory mites.",
        "prevention": "Avoid drought stress; reduce dusty conditions; introduce beneficial insects.",
    },
    "Tomato___Target_Spot": {
        "plant": "Tomato", "disease": "Target Spot", "severity": "medium",
        "description": "Corynespora cassiicola causing brown lesions with concentric rings on leaves.",
        "treatment": "Apply azoxystrobin or chlorothalonil fungicide preventively.",
        "prevention": "Crop rotation; stake plants for airflow; avoid overhead watering.",
    },
    "Tomato___Tomato_YellowLeaf__Curl_Virus": {
        "plant": "Tomato", "disease": "Yellow Leaf Curl Virus (TYLCV)", "severity": "high",
        "description": "Begomovirus transmitted by Bemisia tabaci whitefly — severe yield loss.",
        "treatment": "No chemical cure. Control whitefly with insecticide or yellow sticky traps.",
        "prevention": "Resistant varieties; reflective mulches; screen nurseries.",
    },
    "Tomato___Tomato_mosaic_virus": {
        "plant": "Tomato", "disease": "Tomato Mosaic Virus (ToMV)", "severity": "high",
        "description": "Tobamovirus spread by contact, contaminated tools, and seed.",
        "treatment": "No cure. Remove and destroy infected plants. Disinfect tools with 10% bleach.",
        "prevention": "Certified virus-free seed; wash hands before handling; resistant varieties.",
    },

    # ── FALLBACK ───────────────────────────────────────────────
    "Unknown": {
        "plant": "Unknown", "disease": "Uncertain / Invalid Image", "severity": "unknown",
        "description": "Prediction confidence too low or image does not appear to contain a plant leaf.",
        "treatment": "Please upload a clear, well-lit image of a plant leaf and try again.",
        "prevention": "Ensure the leaf fills most of the frame with good natural lighting.",
    },
}


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _softmax_entropy(probs: np.ndarray) -> float:
    probs = np.clip(probs, 1e-10, 1.0)
    raw_entropy = -np.sum(probs * np.log(probs))
    max_entropy = math.log(max(len(probs), 2))
    return float(raw_entropy / max_entropy)


def _compute_leaf_score(arr_01: np.ndarray) -> float:
    """
    FIX 3: Estimate whether the image contains plant-like pixels.
    Returns fraction of pixels consistent with leaves.
    """
    r, g, b = arr_01[:, :, 0], arr_01[:, :, 1], arr_01[:, :, 2]
    green_mask  = (g > r * 0.85) & (g > b * 0.85) & (g > 0.15)
    brown_mask  = (r > 0.25) & (g > 0.10) & (b < 0.55) & (r > b)
    yellow_mask = (r > 0.30) & (g > 0.25) & (b < 0.40)
    combined = green_mask | brown_mask | yellow_mask
    return float(np.mean(combined))


def _load_disease_classes() -> list:
    """Load class list from app cache, then JSON file, then DISEASE_INFO."""
    classes = getattr(current_app, "disease_classes", None)
    if classes:
        return classes
    classes_path = current_app.config.get("DISEASE_CLASSES_PATH", "")
    if os.path.exists(classes_path):
        with open(classes_path) as f:
            return json.load(f)
    return [k for k in DISEASE_INFO if k != "Unknown"]


def _parse_label(label: str) -> tuple:
    """
    FIX 4: Parse plant/disease from any label format.
    Handles: triple-underscore, double-underscore, single-underscore.
    Returns (plant, disease).
    """
    if "___" in label:
        parts = label.split("___", 1)
        plant   = parts[0].replace("__", " ").replace("_", " ").strip()
        disease = parts[1].replace("_", " ").strip()
    elif "__" in label:
        parts = label.split("__", 1)
        plant   = parts[0].replace("_", " ").strip()
        disease = parts[1].replace("_", " ").strip()
    else:
        plant   = "Unknown"
        disease = label.replace("_", " ").strip()
    return plant, disease


def _get_disease_info(label: str) -> dict:
    """
    FIX 1 + FIX 4: Look up disease info.
    If exact match not found, build a sensible fallback from the label itself
    instead of returning 'Unknown / Unknown'.
    """
    if label in DISEASE_INFO:
        return DISEASE_INFO[label]
    if label == "Unknown":
        return DISEASE_INFO["Unknown"]

    # Dynamic fallback for any class not hardcoded above
    plant, disease = _parse_label(label)
    severity = "none" if "Healthy" in label or "healthy" in label else "unknown"
    return {
        "plant":       plant,
        "disease":     disease,
        "severity":    severity,
        "description": f"Disease information for '{disease}' is not yet in the database.",
        "treatment":   "Consult an agricultural expert for treatment advice.",
        "prevention":  "Maintain field sanitation and regular monitoring.",
    }


def _run_model(image_path: str) -> dict:
    predictor = getattr(current_app, "disease_predictor", None)

    if predictor is not None:
        return predictor.predict(image_path, debug=False)

    # fallback (if model not loaded)
    return {
        "label": "Unknown",
        "confidence": 0.0,
        "top5": [],
        "uncertain": True,
        "entropy": 1.0,
        "leaf_score": 0.0,
    }


# ──────────────────────────────────────────────────────────────
# Endpoint
# ──────────────────────────────────────────────────────────────

@detect_bp.post("/detect")
@jwt_required()
def detect():
    user_id = int(get_jwt_identity())

    if "image" not in request.files:
        return jsonify({"success": False,
                        "message": "No image provided. Send a file with key 'image'."}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"success": False, "message": "No file selected."}), 400

    if not _allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "unknown"
        return jsonify({"success": False,
                        "message": f"Unsupported file type '.{ext}'. Upload a JPG or PNG."}), 400

    upload_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    ext       = file.filename.rsplit(".", 1)[1].lower()
    filename  = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(upload_dir, filename)
    file.save(save_path)

    try:
        prediction = _run_model(save_path)
    except Exception as exc:
        current_app.logger.exception("Disease model inference error")
        return jsonify({"success": False, "message": f"Model error: {str(exc)}"}), 500

    label      = prediction["label"]
    confidence = prediction["confidence"]
    uncertain  = prediction.get("uncertain", False)

    # FIX 1 + FIX 4: correct lookup for all 47 classes
    info = _get_disease_info(label)

    with current_app.db_session() as db:
        result = Result(
            user_id      = user_id,
            top_crop     = "N/A",
            confidence   = 0,
            disease_name = info["disease"],
            disease_conf = confidence,
            image_path   = filename,
        )
        db.add(result)
        db.commit()
        db.refresh(result)

    return jsonify({
        "success":    True,
        "result_id":  result.id,
        "label":      label,
        "plant":      info["plant"],
        "disease":    info["disease"],
        "severity":   info["severity"],
        "confidence": confidence,
        "top5": prediction.get("top_k", []),
        "stub_mode":  not hasattr(current_app, "disease_predictor"),
        "uncertain":  uncertain,
    }), 200
