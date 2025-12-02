#!/usr/bin/env python3
"""
V22_generate.py

Patient-specific Circle of Willis for patient 025,
embedded into the Abel_ref2 full-body model.

Strategy:
  - Copy models/Abel_ref2 → models/cow_runV22
  - Load patient CoW data (feature/nodes/variant JSON)
  - Modify ONLY the Circle of Willis vessels in arterial.csv:
      A56, A59    (Basilar segments)
      A60, A61    (P1)
      A62, A63    (Pcom)
      A64, A65    (P2)
      A68, A69    (A1)
      A76, A78    (A2)
      A77         (Acom)
      A70, A73    (M1)
  - Keep main.csv and p*.csv unchanged.

This preserves:
  - connectivity
  - Windkessel assignments
  - solver expectations

and only swaps in patient-specific geometry.
"""

import os
import csv
import json
import shutil
import math

# ------------------------------------------------------------
# 1. CONFIG
# ------------------------------------------------------------
PATIENT_ID = "025"

BASE_MODEL_NAME = "Abel_ref2"
OUTPUT_MODEL_NAME = "cow_run22"

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
BASE_DIR = os.path.join(MODELS_DIR, BASE_MODEL_NAME)
OUT_DIR = os.path.join(MODELS_DIR, OUTPUT_MODEL_NAME)

RAW_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", f"data_patient{PATIENT_ID}")
)

FEATURE_FILE = os.path.join(RAW_DATA_DIR, f"feature_mr_{PATIENT_ID}.json")
VARIANT_FILE = os.path.join(RAW_DATA_DIR, f"variant_mr_{PATIENT_ID}.json")


# ------------------------------------------------------------
# 2. LOAD PATIENT DATA
# ------------------------------------------------------------
def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r") as f:
        return json.load(f)


feat_data = load_json(FEATURE_FILE)
variant_data = load_json(VARIANT_FILE)


def get_geom(label_id: int, segment_name: str):
    """
    Extract (radius [m], length [m]) from feature JSON
    for a given label index and segment name.
    Fallback to defaults if missing.
    """
    try:
        group = feat_data.get(str(label_id))
        if not group:
            return 0.0015, 0.01
        seg_data = group.get(segment_name)
        if isinstance(seg_data, list):
            data = seg_data[0]
        else:
            data = seg_data
        r_mm = data["radius"]["median"]
        l_mm = data["length"]
        return r_mm / 1000.0, l_mm / 1000.0
    except Exception:
        return 0.0015, 0.01


def num_points_from_length(l_m: float):
    """Reasonable discretization: ~1 point per 5 mm, min 5."""
    length_mm = l_m * 1000.0
    return max(5, int(length_mm / 5.0))


# ------------------------------------------------------------
# 3. COPY BASE MODEL
# ------------------------------------------------------------
def copy_base_model():
    if not os.path.isdir(BASE_DIR):
        raise RuntimeError(f"Base model directory not found: {BASE_DIR}")
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    shutil.copytree(BASE_DIR, OUT_DIR)


# ------------------------------------------------------------
# 4. MODIFY arterial.csv FOR COW VESSELS
# ------------------------------------------------------------

# Mapping: base vessel ID -> (label_id, segment_name)
# (label_id, segment_name) are as you used in your earlier V21 script.
COW_MAP = {
    # Basilar: handled specially (two segments)
    "A56": ("BA", 1, "BA"),  # Basilar 2
    "A59": ("BA", 1, "BA"),  # Basilar 1

    # P1
    "A60": ("P1_R", 2, "P1"),  # right P1
    "A61": ("P1_L", 3, "P1"),  # left  P1

    # Pcom
    "A62": ("Pcom_R", 8, "Pcom"),
    "A63": ("Pcom_L", 9, "Pcom"),

    # P2
    "A64": ("P2_R", 2, "P2"),
    "A65": ("P2_L", 3, "P2"),

    # A1
    "A68": ("A1_R", 11, "A1"),
    "A69": ("A1_L", 12, "A1"),

    # A2
    "A76": ("A2_R", 11, "A2"),
    "A78": ("A2_L", 12, "A2"),

    # Acom
    "A77": ("Acom", 10, "Acom"),

    # MCA M1
    "A70": ("MCA_R", 5, "MCA"),
    "A73": ("MCA_L", 7, "MCA"),
}


def modify_arterial():
    arterial_path = os.path.join(OUT_DIR, "arterial.csv")

    # Read all rows first
    with open(arterial_path, "r") as f:
        reader = list(csv.reader(f))

    header = reader[0]
    rows = reader[1:]

    # 1) Collect original BA lengths for A56 + A59
    L56_orig = None
    L59_orig = None
    for row in rows:
        if not row or row[0] != "vis_f":
            continue
        vid = row[1]
        if vid == "A56":
            try:
                L56_orig = float(row[9])
            except Exception:
                pass
        elif vid == "A59":
            try:
                L59_orig = float(row[9])
            except Exception:
                pass

    # Patient basilar geometry
    r_ba, L_ba = get_geom(1, "BA")
    # If we have both original BA segments, split total length
    if L56_orig is not None and L59_orig is not None and (L56_orig + L59_orig) > 0:
        Ltot = L56_orig + L59_orig
        L56_new = L_ba * (L56_orig / Ltot)
        L59_new = L_ba * (L59_orig / Ltot)
    else:
        # Fallback: half-half
        L56_new = L_ba * 0.5
        L59_new = L_ba * 0.5

    # 2) Build new rows with modified COW geometry
    new_rows = []
    for row in rows:
        if not row or row[0] != "vis_f":
            new_rows.append(row)
            continue

        vid = row[1]
        if vid not in COW_MAP:
            new_rows.append(row)
            continue

        # We will overwrite diameters, thickness, length, and division_points.
        row = row[:]  # copy

        if vid in ("A56", "A59"):
            # Basilar: use patient basilar radius, split length
            d = 2.0 * r_ba
            h = 0.1 * d
            if vid == "A56":
                L = L56_new
            else:
                L = L59_new
            N = num_points_from_length(L)
        else:
            # Other CoW segments: use mapping
            _, label_id, seg_name = COW_MAP[vid]
            r_m, L = get_geom(label_id, seg_name)
            d = 2.0 * r_m
            h = 0.1 * d
            N = num_points_from_length(L)

        # overwrite geometry columns:
        # start_diameter, end_diameter, start_thickness, end_thickness, length, division_points
        row[5] = f"{d:.6f}"
        row[6] = f"{d:.6f}"
        row[7] = f"{h:.6f}"
        row[8] = f"{h:.6f}"
        row[9] = f"{L:.6f}"
        row[10] = f"{N:d}"

        new_rows.append(row)

    # 3) Write back arterial.csv
    with open(arterial_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(new_rows)


# ------------------------------------------------------------
# 5. MAIN
# ------------------------------------------------------------
if __name__ == "__main__":
    print(f"[INFO] Base model:   {BASE_DIR}")
    print(f"[INFO] Output model: {OUT_DIR}")
    print(f"[INFO] Patient ID:   {PATIENT_ID}")

    copy_base_model()
    modify_arterial()

    print("\n[OK] V22 patient-specific CoW embedded into Abel_ref2.")
    print("Run the simulation with:")
    print("  cd ../projects/simple_run")
    print(f"  ./simple_run.out {OUTPUT_MODEL_NAME}")
