import os, json, argparse, math
import numpy as np
from PIL import Image

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL   = os.path.join(BASE_DIR, "saved", "disease_model.keras")
DEFAULT_CLASSES = os.path.join(BASE_DIR, "saved", "disease_classes.json")
DEFAULT_META    = os.path.join(BASE_DIR, "saved", "disease_meta.json")

IMG_SIZE             = (224, 224)
LEAF_SCORE_THRESHOLD = 0.08


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _softmax_entropy(probs: np.ndarray) -> float:
    probs    = np.clip(probs, 1e-10, 1.0)
    entropy  = -np.sum(probs * np.log(probs))
    max_entr = math.log(max(len(probs), 2))
    return float(entropy / max_entr)


def _compute_leaf_score(arr_01: np.ndarray) -> float:
    """Input must be in [0, 1]."""
    r, g, b     = arr_01[:, :, 0], arr_01[:, :, 1], arr_01[:, :, 2]
    green_mask  = (g > r * 0.85) & (g > b * 0.85) & (g > 0.15)
    brown_mask  = (r > 0.25) & (g > 0.10) & (b < 0.55) & (r > b)
    yellow_mask = (r > 0.30) & (g > 0.25) & (b < 0.40)
    return float(np.mean(green_mask | brown_mask | yellow_mask))


def _load_image_255(image_path: str) -> np.ndarray:
    """
    Load image and return float32 array in [0, 255].
    NO division by 255 — the model handles normalization internally.
    """
    img = Image.open(image_path).convert("RGB").resize(IMG_SIZE)
    return np.array(img, dtype=np.float32)   # [0, 255]


# ─────────────────────────────────────────────────────────────
# TTA
# ─────────────────────────────────────────────────────────────

def _build_tta_batch(arr_255: np.ndarray) -> np.ndarray:
    """7 augmented versions of image in [0, 255]."""
    return np.array([
        arr_255,
        np.fliplr(arr_255),
        np.flipud(arr_255),
        np.rot90(arr_255, k=1),
        np.rot90(arr_255, k=2),
        np.clip(arr_255 * 1.10, 0, 255),
        np.clip(arr_255 * 0.90, 0, 255),
    ], dtype=np.float32)


# ─────────────────────────────────────────────────────────────
# Predictor
# ─────────────────────────────────────────────────────────────

class DiseasePredictor:
    def __init__(
        self,
        model_path:   str,
        classes_path: str,
        meta_path:    "str | None" = None,
        conf_thresh:  "float | None" = None,
        ent_thresh:   "float | None" = None,
        use_tta:      bool = False,
    ):
        try:
            import tensorflow as tf
            self._tf = tf
        except ImportError:
            raise SystemExit("TensorFlow not found.  pip install tensorflow")

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found: {model_path}\n"
                "Train first: python models/train_disease.py --data dataset/raw"
            )
        if not os.path.exists(classes_path):
            raise FileNotFoundError(f"Classes file not found: {classes_path}")

        print(f"  Loading model  : {model_path}")
        self.model   = tf.keras.models.load_model(model_path)
        self.use_tta = use_tta

        with open(classes_path) as f:
            self.classes = json.load(f)
        print(f"  Classes loaded : {len(self.classes)}")

        self.conf_thresh = 0.50
        self.ent_thresh  = 0.70

        if meta_path and os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            self.conf_thresh = meta.get("confidence_threshold", self.conf_thresh)
            self.ent_thresh  = meta.get("entropy_threshold",    self.ent_thresh)

            test_acc = meta.get("test_accuracy", 100.0)
            ver      = meta.get("model_version", "?")
            if test_acc < 5.0:
                print(f"\n  WARNING: Loaded model ({ver}) has test_accuracy={test_acc}%")
                print("  This model was trained with a broken pipeline.")
                print("  Please retrain using the latest training pipeline.\n")

        if conf_thresh is not None: self.conf_thresh = conf_thresh
        if ent_thresh  is not None: self.ent_thresh  = ent_thresh

        print(f"  Thresholds : conf>={self.conf_thresh:.2f}  ent<={self.ent_thresh:.2f}  "
              f"leaf>={LEAF_SCORE_THRESHOLD:.2f}  TTA={'on' if use_tta else 'off'}")

    def _run_inference(self, arr_255: np.ndarray, debug: bool = False) -> tuple:
        if self.use_tta:
            batch     = _build_tta_batch(arr_255)
            all_probs = self.model.predict(batch, verbose=0)
            avg_probs = np.mean(all_probs, axis=0)
            tta_std   = float(np.max(np.std(all_probs, axis=0)))
            if debug:
                print(f"  [TTA] std across 7 runs (max class): {tta_std:.4f}")
        else:
            inp       = np.expand_dims(arr_255, axis=0)
            avg_probs = self.model.predict(inp, verbose=0)[0]
            tta_std   = 0.0
        return avg_probs, tta_std

    def predict(self, image_path: str, top_k: int = 5, debug: bool = False) -> dict:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        arr_255    = _load_image_255(image_path)
        arr_01     = arr_255 / 255.0
        leaf_score = _compute_leaf_score(arr_01)

        if debug:
            print(f"\n  [DEBUG] {os.path.basename(image_path)}")
            print(f"  [DEBUG] Leaf score: {leaf_score:.4f}  (min: {LEAF_SCORE_THRESHOLD})")

        if leaf_score < LEAF_SCORE_THRESHOLD:
            if debug:
                print("  [DEBUG] Rejected by leaf validator")
            return {
                "label":      "Unknown",
                "plant":      "Unknown",
                "disease":    "Image rejected — does not appear to contain a plant leaf",
                "confidence": 0.0,
                "top_k":      [],
                "uncertain":  True,
                "entropy":    1.0,
                "leaf_score": round(leaf_score, 4),
            }

        probs, tta_std = self._run_inference(arr_255, debug=debug)

        if debug:
            print("\n  [DEBUG] Top-10 probabilities:")
            for i in np.argsort(probs)[::-1][:10]:
                bar = "#" * max(1, int(probs[i] * 40))
                print(f"    {self.classes[i]:<55s}  {probs[i]*100:6.2f}%  {bar}")
            print(f"  [DEBUG] max_conf={float(np.max(probs))*100:.2f}%  "
                  f"entropy={_softmax_entropy(probs):.4f}  tta_std={tta_std:.4f}\n")

        top_indices = np.argsort(probs)[::-1][:top_k]
        top_results = [
            {"label": self.classes[i],
             "confidence": round(float(probs[i]) * 100, 2)}
            for i in top_indices
        ]
        top_label = self.classes[top_indices[0]]
        top_conf  = round(float(probs[top_indices[0]]) * 100, 2)
        entropy   = round(_softmax_entropy(probs), 4)

        uncertain = (
            top_conf / 100 < self.conf_thresh
            or entropy     > self.ent_thresh
            or leaf_score  < LEAF_SCORE_THRESHOLD
        )

        if "___" in top_label:
            parts = top_label.split("___", 1)
        elif "__" in top_label:
            parts = top_label.split("__", 1)
        else:
            parts = [top_label, top_label]

        plant   = parts[0].replace("_", " ").strip()
        disease = parts[1].replace("_", " ").strip() if len(parts) > 1 else parts[0].replace("_", " ").strip()

        if uncertain:
            return {
                "label":      "Unknown",
                "plant":      "Unknown",
                "disease":    "Uncertain — low confidence or non-leaf image",
                "confidence": top_conf,
                "top_k":      top_results,
                "uncertain":  True,
                "entropy":    entropy,
                "leaf_score": round(leaf_score, 4),
            }

        return {
            "label":      top_label,
            "plant":      plant,
            "disease":    disease,
            "confidence": top_conf,
            "top_k":      top_results,
            "uncertain":  False,
            "entropy":    entropy,
            "leaf_score": round(leaf_score, 4),
        }

    def predict_batch(self, folder: str, top_k: int = 3, debug: bool = False) -> list:
        supported = (".jpg", ".jpeg", ".png", ".bmp")
        files = [
            os.path.join(folder, f)
            for f in sorted(os.listdir(folder))
            if os.path.splitext(f)[1].lower() in supported
        ]
        print(f"\n  Found {len(files)} images in {folder}")
        results = []
        for i, path in enumerate(files, 1):
            try:
                pred         = self.predict(path, top_k=top_k, debug=debug)
                pred["file"] = os.path.basename(path)
                results.append(pred)
                tag = "UNCERTAIN" if pred["uncertain"] else "OK      "
                print(f"  [{i:3d}/{len(files)}] {tag}  "
                      f"{pred['disease']:<35s}  conf={pred['confidence']:5.1f}%  "
                      f"ent={pred['entropy']:.3f}  "
                      f"leaf={pred.get('leaf_score',0):.2f}  "
                      f"({os.path.basename(path)})")
            except Exception as exc:
                print(f"  [{i:3d}] ERROR  {os.path.basename(path)}: {exc}")
        return results


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AgroSage Disease Predictor")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image",   type=str)
    group.add_argument("--folder",  type=str)
    parser.add_argument("--model",   default=DEFAULT_MODEL)
    parser.add_argument("--classes", default=DEFAULT_CLASSES)
    parser.add_argument("--meta",    default=DEFAULT_META)
    parser.add_argument("--top",     type=int,   default=5)
    parser.add_argument("--conf",    type=float, default=None)
    parser.add_argument("--ent",     type=float, default=None)
    parser.add_argument("--tta",     action="store_true")
    parser.add_argument("--debug",   action="store_true")
    args = parser.parse_args()

    print("=" * 58)
    print("  AgroSage — Disease Prediction Utility")
    print("=" * 58)

    predictor = DiseasePredictor(
        args.model, args.classes, args.meta,
        conf_thresh=args.conf, ent_thresh=args.ent,
        use_tta=args.tta,
    )

    if args.image:
        print(f"\n  Predicting: {args.image}")
        result = predictor.predict(args.image, top_k=args.top, debug=args.debug)

        print("\n" + "-" * 58)
        if result["uncertain"]:
            print(f"  Result    : UNCERTAIN")
            print(f"  Reason    : {result['disease']}")
            print(f"  Tip       : --debug shows raw probabilities")
            print(f"              --conf 0.35 uses a more lenient threshold")
        else:
            print(f"  Plant     : {result['plant']}")
            print(f"  Disease   : {result['disease']}")
        print(f"  Confidence: {result['confidence']:.1f}%")
        print(f"  Entropy   : {result['entropy']}  (0=certain, 1=uniform)")
        print(f"  Leaf score: {result.get('leaf_score', 'n/a')}")
        print(f"\n  Top-{args.top}:")
        for i, r in enumerate(result["top_k"], 1):
            bar = "#" * max(1, int(r["confidence"] / 4))
            print(f"    {i}. {r['label']:<52s}  {r['confidence']:5.1f}%  {bar}")
        print("-" * 58)

    elif args.folder:
        results    = predictor.predict_batch(args.folder, top_k=args.top, debug=args.debug)
        n_unc      = sum(1 for r in results if r["uncertain"])
        print(f"\n  Summary: {len(results)} images — {n_unc} uncertain")
        out = "batch_results.json"
        with open(out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  Full results → {out}")


if __name__ == "__main__":
    main()
