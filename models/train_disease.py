import os, json, shutil, argparse, random, math
import numpy as np

try:
    import tensorflow as tf
    from tensorflow.keras import layers, Model, callbacks as cb
    from tensorflow.keras.applications import EfficientNetB0
    from tensorflow.keras.applications.efficientnet import preprocess_input as efficientnet_preprocess
    print(f"TensorFlow {tf.__version__}  |  "
          f"GPU: {[g.name for g in tf.config.list_physical_devices('GPU')] or 'none — CPU'}")
except ImportError:
    raise SystemExit("\n  TensorFlow not found.\n  Install: pip install tensorflow\n")

try:
    from sklearn.utils.class_weight import compute_class_weight
except ImportError:
    raise SystemExit("\n  scikit-learn not found.\n  Install: pip install scikit-learn\n")

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
IMG_SIZE             = (224, 224)
BATCH_SIZE           = 32
EPOCHS_FROZEN        = 15
EPOCHS_FINETUNE      = 25
TRAIN_SPLIT          = 0.70
VAL_SPLIT            = 0.15
TEST_SPLIT           = 0.15
MIN_CLASS_IMGS       = 20
MAX_IMAGES_PER_CLASS = 1500
MAX_PLANT_RATIO      = 0.18

CONFIDENCE_THRESHOLD = 0.50
ENTROPY_THRESHOLD    = 0.70

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR     = os.path.join(BASE_DIR, "saved")
MODEL_PATH   = os.path.join(SAVE_DIR, "disease_model.keras")
MODEL_H5     = os.path.join(SAVE_DIR, "disease_model.h5")
CLASSES_PATH = os.path.join(SAVE_DIR, "disease_classes.json")
META_PATH    = os.path.join(SAVE_DIR, "disease_meta.json")
os.makedirs(SAVE_DIR, exist_ok=True)


# ═════════════════════════════════════════════════════════════
# 1.  DATASET PREPARATION
# ═════════════════════════════════════════════════════════════

def scan_dataset(data_dir: str, fast: bool = False) -> dict:
    print(f"\n  Scanning dataset at: {data_dir}")
    supported = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    class_map: dict = {}

    for cls_name in sorted(os.listdir(data_dir)):
        cls_dir = os.path.join(data_dir, cls_name)
        if not os.path.isdir(cls_dir):
            continue
        imgs = [
            os.path.join(cls_dir, f)
            for f in os.listdir(cls_dir)
            if os.path.splitext(f)[1].lower() in supported
        ]
        if len(imgs) < MIN_CLASS_IMGS:
            print(f"  Skipping '{cls_name}' — only {len(imgs)} images (min {MIN_CLASS_IMGS})")
            continue
        if len(imgs) > MAX_IMAGES_PER_CLASS:
            imgs = random.sample(imgs, MAX_IMAGES_PER_CLASS)
        if fast:
            imgs = random.sample(imgs, min(200, len(imgs)))
        class_map[cls_name] = imgs

    total = sum(len(v) for v in class_map.values())
    print(f"  Classes: {len(class_map)}  |  Total images (pre-balance): {total}")
    return class_map


def balance_by_plant(class_map: dict) -> dict:
    """Prevent any single plant family from dominating training."""
    from collections import defaultdict
    plant_classes: dict = defaultdict(list)
    for cls_name in class_map:
        if "___" in cls_name:
            plant = cls_name.split("___")[0]
        elif "__" in cls_name:
            plant = cls_name.split("__")[0]
        else:
            plant = cls_name
        plant_classes[plant].append(cls_name)

    total         = sum(len(v) for v in class_map.values())
    max_per_plant = int(total * MAX_PLANT_RATIO)

    print(f"\n  Plant-level balancing (cap: {MAX_PLANT_RATIO:.0%} = {max_per_plant} imgs per plant):")
    balanced: dict = {}
    for plant, classes in sorted(plant_classes.items()):
        plant_total = sum(len(class_map[c]) for c in classes)
        if plant_total > max_per_plant:
            scale = max_per_plant / plant_total
            for cls in classes:
                n = max(MIN_CLASS_IMGS, int(len(class_map[cls]) * scale))
                n = min(n, len(class_map[cls]))
                balanced[cls] = random.sample(class_map[cls], n)
            new_t = sum(len(balanced[c]) for c in classes)
            print(f"    {plant:<22s}: {plant_total:5d} → {new_t:5d}  (capped)")
        else:
            for cls in classes:
                balanced[cls] = class_map[cls]
            print(f"    {plant:<22s}: {plant_total:5d}  ok")

    new_total = sum(len(v) for v in balanced.values())
    print(f"\n  Total after balancing: {new_total}  (was {total})")
    return balanced


def split_dataset(class_map: dict) -> tuple:
    classes      = sorted(class_map.keys())
    class_to_idx = {c: i for i, c in enumerate(classes)}
    train_pairs, val_pairs, test_pairs = [], [], []
    for cls, paths in class_map.items():
        idx = class_to_idx[cls]
        random.shuffle(paths)
        n       = len(paths)
        n_train = math.ceil(n * TRAIN_SPLIT)
        n_val   = math.ceil(n * VAL_SPLIT)
        train_pairs += [(p, idx) for p in paths[:n_train]]
        val_pairs   += [(p, idx) for p in paths[n_train:n_train + n_val]]
        test_pairs  += [(p, idx) for p in paths[n_train + n_val:]]
    random.shuffle(train_pairs)
    random.shuffle(val_pairs)
    print(f"  Train: {len(train_pairs)}  Val: {len(val_pairs)}  Test: {len(test_pairs)}")
    return train_pairs, val_pairs, test_pairs, classes


def compute_weights(train_pairs: list, num_classes: int) -> dict:
    labels  = [p[1] for p in train_pairs]
    weights = compute_class_weight("balanced", classes=np.arange(num_classes), y=labels)
    return {i: float(w) for i, w in enumerate(weights)}


# ═════════════════════════════════════════════════════════════
# 2.  tf.data PIPELINE
# ═════════════════════════════════════════════════════════════
#
# Images are ALWAYS loaded as float32 in [0, 255].
# Augmentation runs at [0, 255] scale.
# Normalization to [-2.1, 2.6] happens inside the model graph
# (see build_model for how this is handled version-safely).
# ═════════════════════════════════════════════════════════════

def _load_image_255(path: tf.Tensor) -> tf.Tensor:
    """Load and resize image. Returns float32 in [0, 255]. No normalization here."""
    raw = tf.io.read_file(path)
    img = tf.image.decode_image(raw, channels=3, expand_animations=False)
    img = tf.image.resize(img, IMG_SIZE)
    img = tf.cast(img, tf.float32)   # [0, 255] — intentionally NOT divided by 255
    return img


def build_augmentation_layer() -> tf.keras.Sequential:
    """
    Augmentation for [0, 255] float32 images.
    Geometric transforms are scale-independent.
    RandomBrightness uses value_range=(0, 255) so delta is correct for this scale.
    """
    return tf.keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.10),
        layers.RandomZoom(0.15),
        layers.RandomTranslation(0.10, 0.10),
        layers.RandomBrightness(factor=0.20, value_range=(0, 255)),
        layers.RandomContrast(factor=0.20),
    ], name="augmentation")


def make_dataset(pairs: list, num_classes: int,
                 training: bool = False,
                 augment_layer=None) -> tf.data.Dataset:
    paths  = [p for p, _ in pairs]
    labels = [lb for _, lb in pairs]
    ds     = tf.data.Dataset.from_tensor_slices((paths, labels))

    def load_fn(path, label):
        img   = _load_image_255(path)
        label = tf.one_hot(label, num_classes)
        return img, label

    ds = ds.map(load_fn, num_parallel_calls=tf.data.AUTOTUNE)

    if training:
        ds = ds.shuffle(buffer_size=min(len(pairs), 5000), seed=42)

    ds = ds.batch(BATCH_SIZE)

    if training and augment_layer is not None:
        def aug_fn(imgs, lbs):
            imgs = augment_layer(imgs, training=True)
            imgs = tf.clip_by_value(imgs, 0.0, 255.0)
            return imgs, lbs
        ds = ds.map(aug_fn, num_parallel_calls=tf.data.AUTOTUNE)

    return ds.prefetch(tf.data.AUTOTUNE)


# ═════════════════════════════════════════════════════════════
# 3.  MODEL ARCHITECTURE  —  version-safe preprocessing
# ═════════════════════════════════════════════════════════════

def _backbone_has_internal_preprocessing(backbone) -> bool:
    """
    Detect at runtime whether the backbone already contains a
    Rescaling (÷255) layer as its first processing layer.

    Returns True  → backbone preprocesses internally; feed [0,255] directly.
    Returns False → backbone does NOT preprocess; we must apply it manually.
    """
    rescaling_types = []
    try:
        rescaling_types.append(tf.keras.layers.Rescaling)
    except AttributeError:
        pass

    # Check first 3 layers (Input + first 1-2 processing layers)
    for layer in backbone.layers[:4]:
        class_name = type(layer).__name__.lower()
        if "rescaling" in class_name or "rescale" in class_name:
            return True
        for rtype in rescaling_types:
            if isinstance(layer, rtype):
                return True
    return False


def build_model(num_classes: int) -> tuple:
    """
    Build EfficientNetB0 transfer-learning model.

    The model always receives float32 [0, 255] inputs.
    Normalization to [-2.1, 2.6] is handled either:
      (a) by the backbone's internal Rescaling layer, or
      (b) by an explicit Lambda(preprocess_input) layer inserted before the backbone

    Which path is taken is detected automatically at build time.
    """
    # Build backbone — no version-specific arguments
    backbone = EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=(*IMG_SIZE, 3),
        pooling=None,
    )
    backbone.trainable = False

    # ── Self-detect preprocessing ──────────────────────────────────
    has_internal_prep = _backbone_has_internal_preprocessing(backbone)
    if has_internal_prep:
        print("  Backbone preprocessing: INTERNAL (Rescaling layer detected)")
        print("  Strategy: feed [0,255] directly — backbone handles normalization")
    else:
        print("  Backbone preprocessing: NONE detected")
        print("  Strategy: inserting explicit preprocess_input Lambda layer")

    # ── Build model graph ──────────────────────────────────────────
    inputs = tf.keras.Input(shape=(*IMG_SIZE, 3), name="image_input")
    x = inputs

    if not has_internal_prep:
        # Insert official preprocess_input: [0,255] → [-2.1, 2.6]
        x = layers.Lambda(
            efficientnet_preprocess,
            name="efficientnet_preprocess"
        )(x)

    x = backbone(x, training=False)
    x = layers.GlobalAveragePooling2D(name="gap")(x)
    x = layers.Dense(512, name="fc1")(x)
    x = layers.BatchNormalization(name="bn1")(x)
    x = layers.Activation("relu")(x)
    x = layers.Dropout(0.30, name="drop1")(x)
    x = layers.Dense(256, name="fc2")(x)
    x = layers.BatchNormalization(name="bn2")(x)
    x = layers.Activation("relu")(x)
    x = layers.Dropout(0.20, name="drop2")(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="predictions")(x)

    model = Model(inputs, outputs, name="agrosage_disease_detector")

    # ── Sanity check: verify output is not already uniform ─────────
    # Create a synthetic green-leaf-like image and check top prob > 1/N
    dummy   = np.random.uniform(60, 180, (1, *IMG_SIZE, 3)).astype(np.float32)
    out     = model(dummy, training=False).numpy()[0]
    top_p   = float(out.max())
    uniform = 1.0 / num_classes
    print(f"  Sanity check: top softmax prob on random input = {top_p:.4f}  "
          f"(uniform would be {uniform:.4f})")
    if top_p < uniform * 1.5:
        print("  *** WARNING: output is near-uniform before training starts.")
        print("  *** This is unusual — model may have a preprocessing issue.")
        print("  *** Check that your TF/Keras installation is not corrupted.")
    else:
        print("  Sanity check PASSED — model output is non-uniform before training.")

    return model, backbone, has_internal_prep


# ═════════════════════════════════════════════════════════════
# 4.  TRAINING
# ═════════════════════════════════════════════════════════════

def train(data_dir: str, fast: bool, epochs1: int, epochs2: int):
    class_map = scan_dataset(data_dir, fast=fast)
    class_map = balance_by_plant(class_map)

    print("\n  Class distribution after balancing:")
    for cls, imgs in class_map.items():
        print(f"    {cls:<50s}  {len(imgs)}")

    if len(class_map) < 2:
        raise ValueError(f"Need at least 2 classes — found {len(class_map)}")

    train_pairs, val_pairs, test_pairs, classes = split_dataset(class_map)
    num_classes   = len(classes)
    class_weights = compute_weights(train_pairs, num_classes)

    aug_layer = build_augmentation_layer()
    train_ds  = make_dataset(train_pairs, num_classes, training=True,  augment_layer=aug_layer)
    val_ds    = make_dataset(val_pairs,   num_classes, training=False)
    test_ds   = make_dataset(test_pairs,  num_classes, training=False)

    print("\n  Building model ...")
    model, backbone, has_internal_prep = build_model(num_classes)
    model.summary(line_length=90, expand_nested=False)

    # ── Phase 1: head only ────────────────────────────────────
    print(f"\n  -- Phase 1: Head-only ({epochs1} epochs max) --")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.05),
        metrics=["accuracy",
                 tf.keras.metrics.TopKCategoricalAccuracy(k=5, name="top5_acc")],
    )

    ckpt1 = os.path.join(SAVE_DIR, "ckpt_phase1.keras")
    hist1 = model.fit(
        train_ds, validation_data=val_ds, epochs=epochs1,
        class_weight=class_weights,
        callbacks=[
            cb.EarlyStopping("val_accuracy", patience=5,
                             restore_best_weights=True, verbose=1),
            cb.ReduceLROnPlateau("val_loss", factor=0.5, patience=3,
                                 min_lr=1e-7, verbose=1),
            cb.ModelCheckpoint(ckpt1, "val_accuracy",
                               save_best_only=True, verbose=0),
        ],
        verbose=1,
    )

    # Check Phase 1 progress — catch stuck training early
    best_val_acc = max(hist1.history.get("val_accuracy", [0]))
    print(f"\n  Phase 1 best val_accuracy: {best_val_acc*100:.2f}%")
    if best_val_acc < 0.05:
        print("  *** ALERT: Phase 1 val_accuracy < 5% — model is NOT learning.")
        print("  *** Possible causes:")
        print("  ***   1. Dataset path is wrong (check --data argument)")
        print("  ***   2. Images are corrupted or all the same")
        print("  ***   3. TF/Keras installation issue")
        print("  *** Training will continue but results will be poor.")

    # ── Phase 2: fine-tune top-30 backbone layers ─────────────
    print(f"\n  -- Phase 2: Fine-tune top-30 layers ({epochs2} epochs max) --")
    backbone.trainable = True
    for layer in backbone.layers[:-30]:
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(5e-5),
        loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.05),
        metrics=["accuracy",
                 tf.keras.metrics.TopKCategoricalAccuracy(k=5, name="top5_acc")],
    )

    ckpt2 = os.path.join(SAVE_DIR, "ckpt_phase2.keras")
    model.fit(
        train_ds, validation_data=val_ds, epochs=epochs2,
        class_weight=class_weights,
        callbacks=[
            cb.EarlyStopping("val_accuracy", patience=7,
                             restore_best_weights=True, verbose=1),
            cb.ReduceLROnPlateau("val_loss", factor=0.4, patience=3,
                                 min_lr=1e-8, verbose=1),
            cb.ModelCheckpoint(ckpt2, "val_accuracy",
                               save_best_only=True, verbose=1),
        ],
        verbose=1,
    )

    # ── Evaluate ──────────────────────────────────────────────
    print("\n  Evaluating on test set ...")
    test_loss, test_acc, test_top5 = model.evaluate(test_ds, verbose=1)
    print(f"  Test accuracy  : {test_acc  * 100:.2f}%")
    print(f"  Test top-5 acc : {test_top5 * 100:.2f}%")
    print(f"  Test loss      : {test_loss:.4f}")

    # ── Save ──────────────────────────────────────────────────
    model.save(MODEL_PATH)
    model.save(MODEL_H5)
    with open(CLASSES_PATH, "w") as f:
        json.dump(classes, f, indent=2)

    meta = {
        "num_classes":            num_classes,
        "classes":                classes,
        "confidence_threshold":   CONFIDENCE_THRESHOLD,
        "entropy_threshold":      ENTROPY_THRESHOLD,
        "img_size":               list(IMG_SIZE),
        "backbone":               "EfficientNetB0",
        "input_range":            "0-255",
        "backbone_internal_preprocessing": has_internal_prep,
        "label_smoothing":        0.05,
        "plant_balance_ratio":    MAX_PLANT_RATIO,
        "test_accuracy":          round(test_acc  * 100, 2),
        "test_top5_accuracy":     round(test_top5 * 100, 2),
        "test_loss":              round(test_loss, 4),
        "dataset_dir":            os.path.abspath(data_dir),
        "train_samples":          len(train_pairs),
        "val_samples":            len(val_pairs),
        "test_samples":           len(test_pairs),
        "class_counts":           {c: len(v) for c, v in class_map.items()},
        "model_version":          "AgroSage v1.0",
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n  Model   -> {MODEL_PATH}")
    print(f"  Classes -> {CLASSES_PATH}")
    print(f"  Meta    -> {META_PATH}")

    for ck in [ckpt1, ckpt2]:
        if os.path.exists(ck):
            shutil.rmtree(ck) if os.path.isdir(ck) else os.remove(ck)

    return model, classes, meta


# ═════════════════════════════════════════════════════════════
# 5.  CLI
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgroSage Disease Training")
    parser.add_argument("--data",    required=True,
                        help="Path to dataset root (one subfolder per class)")
    parser.add_argument("--fast",    action="store_true",
                        help="Quick smoke-test: 200 images/class, fewer epochs")
    parser.add_argument("--epochs1", type=int, default=EPOCHS_FROZEN,
                        help=f"Head-only epochs (default {EPOCHS_FROZEN})")
    parser.add_argument("--epochs2", type=int, default=EPOCHS_FINETUNE,
                        help=f"Fine-tune epochs (default {EPOCHS_FINETUNE})")
    args = parser.parse_args()

    if not os.path.isdir(args.data):
        raise SystemExit(f"\n  Dataset directory not found: {args.data}\n")

    random.seed(42)
    np.random.seed(42)
    tf.random.set_seed(42)

    print("=" * 65)
    print(" AgroSage Disease Training ")
    print("-" * 65)
    print("  Input:        float32 [0, 255]")
    print("  Preprocessing: auto-detected at build time (no guessing)")
    print("  Augmentation: horizontal flip, ±36 deg rotation, zoom, brightness")
    print("  Dropout:      0.30 / 0.20  |  Label smooth: 0.05")
    print("  Plant balance: no single plant > 18%")
    print("=" * 65)

    model, classes, meta = train(args.data, args.fast, args.epochs1, args.epochs2)

    print("\n" + "=" * 65)
    print(f"  Done.  Classes: {meta['num_classes']}  |  Test acc: {meta['test_accuracy']}%")
    print("=" * 65)
