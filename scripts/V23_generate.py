#!/usr/bin/env python3
"""
V23_generate.py

Safe, solver-compatible patient-specific Circle of Willis generator.
This script modifies ONLY the CoW vessels inside Abel_ref2/arterial.csv.

Guaranteed properties:
  - preserves FULL SYSTEMIC TREE from Abel_ref2
  - preserves all node names (nXX, pXX)
  - preserves main.csv EXACTLY
  - preserves every Windkessel (p1..p47)
  - preserves heart_kim_lit.csv
  - only replaces diameters + thickness + lengths + discretization points
    for Circle of Willis vessels using MR-derived geometry.
"""

import os
import csv
import shutil
import json

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
PATIENT_ID = "025"

BASE_NAME = "Abel_ref2"
OUT_NAME  = "cow_runV23"

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", BASE_NAME)
)
OUT_DIR  = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", OUT_NAME)
)

RAW_DIR  = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", f"data_patient{PATIENT_ID}")
)

FEATURE_FILE = os.path.join(RAW_DIR, f"feature_mr_{PATIENT_ID}.json")
VARIANT_FILE = os.path.join(RAW_DIR, f"variant_mr_{PATIENT_ID}.json")


# ----------------------------------------------------------------------
# LOAD PATIENT GEOMETRY
# ----------------------------------------------------------------------
def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r") as f:
        return json.load(f)

feat = load_json(FEATURE_FILE)
var  = load_json(VARIANT_FILE)


def get_geom(label, segname):
    """
    Returns: (radius_m, length_m)
    Provides robust fallback if MR data unavailable.
    """
    try:
        block = feat.get(str(label))
        if not block:
            return 0.0015, 0.01
        seg = block.get(segname)
        if isinstance(seg, list):
            seg = seg[0]
        r_mm = seg["radius"]["median"]
        L_mm = seg["length"]
        return r_mm / 1000.0, L_mm / 1000.0
    except Exception:
        return 0.0015, 0.01


def discretize(L_m):
    """Good CoW discretization: >5 points, roughly 1 point per 5 mm."""
    return max(5, int((L_m * 1000.0) / 5.0))


# ----------------------------------------------------------------------
# CoW vessel mapping (ID → (labelId, segmentName))
# ----------------------------------------------------------------------
COW_VESSELS = {
    "A56": (1, "BA"),     # Basilar artery 2
    "A59": (1, "BA"),     # Basilar artery 1

    "A60": (2, "P1"),     # Right P1
    "A61": (3, "P1"),     # Left P1

    "A62": (8, "Pcom"),   # Right Pcom
    "A63": (9, "Pcom"),   # Left Pcom

    "A64": (2, "P2"),     # Right P2
    "A65": (3, "P2"),     # Left P2

    "A68": (11, "A1"),    # Right A1
    "A69": (12, "A1"),    # Left A1

    "A76": (11, "A2"),    # Right A2
    "A78": (12, "A2"),    # Left A2

    "A77": (10, "Acom"),  # Acom

    "A70": (5, "MCA"),    # Right MCA M1
    "A73": (7, "MCA"),    # Left MCA M1
}


# ----------------------------------------------------------------------
# COPY ABEL_REF2 → OUTPUT
# ----------------------------------------------------------------------
def clone_model():
    if not os.path.exists(BASE_DIR):
        raise RuntimeError(f"Base model directory not found: {BASE_DIR}")
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    shutil.copytree(BASE_DIR, OUT_DIR)


# ----------------------------------------------------------------------
# MODIFY ARTERIAL.CSV BY OVERWRITING ONLY CoW GEOMETRY
# ----------------------------------------------------------------------
def modify_arterial():
    path = os.path.join(OUT_DIR, "arterial.csv")

    # load file
    with open(path, "r") as f:
        rows = list(csv.reader(f))

    if not rows:
        raise RuntimeError("arterial.csv is empty")

    header = rows[0]
    body = rows[1:]

    # --- 1) Collect original BA lengths for A56 + A59 (skip empty lines) ---
    L56_orig = None
    L59_orig = None
    for r in body:
        if not r or len(r) == 0:
            continue
        if r[0] != "vis_f":
            continue
        if r[1] == "A56":
            try:
                L56_orig = float(r[9])
            except Exception:
                pass
        elif r[1] == "A59":
            try:
                L59_orig = float(r[9])
            except Exception:
                pass

    # patient basilar geometry
    r_ba, L_ba = get_geom(1, "BA")
    if L56_orig is not None and L59_orig is not None and (L56_orig + L59_orig) > 0:
        Ltot = L56_orig + L59_orig
        L56_new = L_ba * (L56_orig / Ltot)
        L59_new = L_ba * (L59_orig / Ltot)
    else:
        # fallback: equal split
        L56_new = L_ba * 0.5
        L59_new = L_ba * 0.5

    # --- 2) Build new body, modifying only CoW lines and skipping empties ---
    new_body = []
    for r in body:
        # preserve completely empty lines
        if not r or len(r) == 0:
            new_body.append(r)
            continue

        if r[0] != "vis_f":
            new_body.append(r)
            continue

        vid = r[1]

        if vid not in COW_VESSELS:
            # non-CoW vessel: copy as is
            new_body.append(r)
            continue

        # copy row before modification
        r2 = r[:]

        # --- CoW geometry overwrite ---
        if vid in ("A56", "A59"):
            d = 2.0 * r_ba
            h = 0.1 * d
            L = L56_new if vid == "A56" else L59_new
            N = discretize(L)
        else:
            label, segname = COW_VESSELS[vid]
            radius, L = get_geom(label, segname)
            d = 2.0 * radius
            h = 0.1 * d
            N = discretize(L)

        # overwrite geometry columns:
        # [5]=start_d, [6]=end_d, [7]=start_h, [8]=end_h, [9]=length, [10]=N
        if len(r2) < 11:
            # arterial.csv should have >= 11 columns for vis_f lines;
            # if not, we bail out with a clear error:
            raise RuntimeError(f"Unexpected vis_f row format for {vid}: {r2}")

        r2[5]  = f"{d:.6f}"
        r2[6]  = f"{d:.6f}"
        r2[7]  = f"{h:.6f}"
        r2[8]  = f"{h:.6f}"
        r2[9]  = f"{L:.6f}"
        r2[10] = f"{N:d}"

        new_body.append(r2)

    # --- 3) Write back ---
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(new_body)


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("[INFO] Cloning Abel_ref2 → cow_runV23 ...")
    clone_model()

    print("[INFO] Injecting patient-specific CoW geometry ...")
    modify_arterial()

    print("\n[OK] cow_runV23 ready.")
    print("Run with:")
    print("   cd ../projects/simple_run")
    print("   ./simple_run.out cow_runV23")
