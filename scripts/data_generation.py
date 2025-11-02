import json
import csv
from pathlib import Path

# === CONFIGURATION ===
FEATURES_JSON = Path("../CoW_Centerline_Data/cow_features/topcow_mr_025.json")
OUTPUT_CSV = Path("../outputs/arterial_cow_full.csv")

# === PHYSIOLOGICAL CONSTANTS (Alastruey et al., 2007) ===
WALL_THICKNESS_FRAC = 0.25  # wall thickness = 25% of radius
YOUNG_MODULUS = 1.6e6        # Pa (for cerebral arteries)
DEFAULT_CAPACITANCE = "7.27E+10"
DIVISION_POINTS = 5
RES_START = 0.0
RES_END = 0.0
VISC_FACT = 2.75
K1, K2, K3 = 2.0e6, -2253.0, 8.65e4

# === LABEL MAPPING (TopCoW anatomical segments) ===
LABEL_MAP = {
    "1": ("",   "BA"),
    "2": ("R",  "PCA"),
    "3": ("L",  "PCA"),
    "4": ("R",  "ICA"),
    "5": ("R",  "MCA"),
    "6": ("L",  "ICA"),
    "7": ("L",  "MCA"),
    "8": ("R",  "Pcom"),
    "9": ("L",  "Pcom"),
    "10": ("",  "Acom"),
    "11": ("R", "ACA"),
    "12": ("L", "ACA"),
    "15": ("",  "3rd-A2")
}

SUBSEG_KEYS = {"P1", "P2", "A1", "A2", "C6", "C7"}

def make_name(side, vessel, sub=None):
    return f"{side}-{sub}" if sub else f"{side}-{vessel}" if side else vessel

# === Read CoW features JSON ===
with open(FEATURES_JSON, "r") as f:
    data = json.load(f)

vessels = []
node_ids = set()

for label_id, blocks in data.items():
    if label_id not in LABEL_MAP:
        continue
    side, vessel = LABEL_MAP[label_id]
    for key, entries in blocks.items():
        if not isinstance(entries, list) or not entries:
            continue
        seg = entries[0]
        if not all(k in seg for k in ["segment", "radius", "length"]):
            continue

        start = seg["segment"]["start"]
        end = seg["segment"]["end"]
        r_mm = float(seg["radius"]["mean"])
        L_mm = float(seg["length"])

        node_ids.update([f"n{start}", f"n{end}"])

        name = make_name(side, vessel, key if key in SUBSEG_KEYS else None)
        ID = name.replace("-", "_")
        D = 2 * r_mm / 1000           # diameter in meters
        T = D * WALL_THICKNESS_FRAC   # thickness in meters
        L = L_mm / 1000               # length in meters
        A0 = 3.1416 * (D / 2) ** 2
        elastance_1 = (YOUNG_MODULUS * T) / A0

        vessels.append([
            "vis_f", ID, name, f"n{start}", f"n{end}",
            f"{D:.6g}", f"{D:.6g}", f"{T:.6g}", f"{T:.6g}", f"{L:.6g}",
            DIVISION_POINTS, f"{elastance_1:.6g}", RES_START, RES_END,
            VISC_FACT, K1, K2, K3
        ])

# === Write complete arterial.csv ===
with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)

    # Header for vessel rows
    writer.writerow([
        "type", "ID", "name", "start_node", "end_node",
        "start_diameter[SI]", "end_diameter[SI]",
        "start_thickness[SI]", "end_thickness[SI]",
        "length[SI]", "division_points", "elastance_1[SI]",
        "res_start[SI]", "res_end[SI]", "visc_fact[1]",
        "k1[SI]", "k2[SI]", "k3[SI]"
    ])
    writer.writerows(vessels)

    # Node section
    writer.writerow(["type", "ID", "name", "valami", "parameter", "file name"])
    writer.writerow(["heart", "H", "0", "", ""])
    for node in sorted(node_ids):
        writer.writerow(["node", node, "0", DEFAULT_CAPACITANCE, ""])

print(f" arterial.csv generated with {len(vessels)} vessels and {len(node_ids)} nodes → {OUTPUT_CSV}")
