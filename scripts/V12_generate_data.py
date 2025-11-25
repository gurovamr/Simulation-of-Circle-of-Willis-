#!/usr/bin/env python3
"""
V12_generate_data.py

Builds a 1D Circle of Willis model for a single patient using:
 - feature_mr_XXX.json : segment radii / lengths
 - nodes_mr_XXX.json   : anatomical junction nodes
 - varient_mr_XXX.json : CoW configuration (not yet used for pruning)

Compared to V11, V12 explicitly adds short "connector" segments so that
the whole CoW (BA + PCA + Pcom + ICA + MCA + ACA + Acom) is one
topologically connected arterial network.
"""

import json
import csv
import os
import math
from io import StringIO
import shutil
import pandas as pd

# -------------------------------------------------------------
# User configuration
# -------------------------------------------------------------
MODEL_NAME  = "cow_runV12"                 # folder name in ../models
INPUT_DIR   = "../data_patient025"         # raw JSON dir for this patient

PATIENT_ID  = "025"                        # only used to build file names
HEART_INLET_NODE_ID = 15                   # BA inlet node id -> "N15"

FEATURE_FILE = os.path.join(INPUT_DIR, f"feature_mr_{PATIENT_ID}.json")
NODES_FILE   = os.path.join(INPUT_DIR, f"nodes_mr_{PATIENT_ID}.json")
VARIANT_FILE = os.path.join(INPUT_DIR, f"variant_mr_{PATIENT_ID}.json")

OUTPUT_DIR   = os.path.join("../models", MODEL_NAME)
os.makedirs(OUTPUT_DIR, exist_ok=True)

ARTERIAL_CSV = os.path.join(OUTPUT_DIR, "arterial.csv")
MAIN_CSV     = os.path.join(OUTPUT_DIR, "main.csv")

# Where to copy the heart model from (already weakened by you)
ABEL_HEART = "../models/Abel_ref2/heart_kim_lit.csv"
COW_HEART  = os.path.join(OUTPUT_DIR, "heart_kim_lit.csv")

# Short technical connectors (between bifurcation and boundary nodes)
CONNECTOR_LENGTH_M = 1.0e-3  # 1 mm

# -------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------
def wall_thickness(radius_m: float) -> float:
    """Simple rule: wall thickness = 10% of radius."""
    return 0.1 * radius_m

def default_material():
    """Material/constants – same as Abel_ref2."""
    return dict(
        elastance_1 = 5.0e5,
        res_start   = 0.0,
        res_end     = 0.0,
        visc_fact   = 2.75,
        k1          = 2.0e6,
        k2          = -2253.0,
        k3          = 8.65e4,
    )

def si(mm: float) -> float:
    """Convert mm to m."""
    return float(mm) / 1000.0

def load_json(path: str):
    with open(path) as f:
        return json.load(f)

# -------------------------------------------------------------
# Load patient data
# -------------------------------------------------------------
feature_data = load_json(FEATURE_FILE)
nodes_data   = load_json(NODES_FILE)
variant_data = load_json(VARIANT_FILE)   # currently not used for pruning

# -------------------------------------------------------------
# Convenience accessors into JSON structures
# -------------------------------------------------------------
def mean_radius_from_feature(group_key: str, vessel_name: str) -> float:
    """
    Return mean radius [m] for a given anatomical segment, e.g.
    group_key = "2", vessel_name = "P1".
    """
    seg_list = feature_data[group_key][vessel_name]
    r_mm = seg_list[0]["radius"]["mean"]
    return si(r_mm)

def get_node_id(group_key: str, label: str) -> int:
    """
    Return node id for a given anatomical label in nodes_mr_XXX.json,
    e.g. group_key="4", label="ICA bifurcation".
    """
    return nodes_data[group_key][label][0]["id"]

# -------------------------------------------------------------
# Build 1D arterial network from feature_data
# (base segments only, no connectors yet)
# -------------------------------------------------------------
arterial_header = [
    "type","ID","name","start_node","end_node",
    "start_diameter[SI]","end_diameter[SI]",
    "start_thickness[SI]","end_thickness[SI]",
    "length[SI]","division_points",
    "elastance_1[SI]","res_start[SI]","res_end[SI]",
    "visc_fact[1]","k1[SI]","k2[SI]","k3[SI]"
]

arteries = []
constants = default_material()

for group_id, segments in feature_data.items():
    for vessel_name, vessel_list in segments.items():
        # Skip bifurcation meta-entries
        if "bifurcation" in vessel_name.lower():
            continue

        for seg in vessel_list:
            start = f"N{seg['segment']['start']}"
            end   = f"N{seg['segment']['end']}"

            radius_m   = si(seg['radius']['mean'])
            diameter_m = 2.0 * radius_m
            thick      = wall_thickness(radius_m)
            length     = si(seg['length'])

            arteries.append({
                "type": "vis_f",
                "ID": f"{vessel_name}_{group_id}",
                "name": vessel_name,
                "start_node": start,
                "end_node": end,
                "start_diameter[SI]": diameter_m,
                "end_diameter[SI]": diameter_m,
                "start_thickness[SI]": thick,
                "end_thickness[SI]": thick,
                "length[SI]": length,
                "division_points": 5,
                "elastance_1[SI]": constants["elastance_1"],
                "res_start[SI]": constants["res_start"],
                "res_end[SI]": constants["res_end"],
                "visc_fact[1]": constants["visc_fact"],
                "k1[SI]": constants["k1"],
                "k2[SI]": constants["k2"],
                "k3[SI]": constants["k3"],
            })

# -------------------------------------------------------------
# Add short connector segments so that CoW is topologically connected
# -------------------------------------------------------------
def add_connector_segment(ID: str,
                          name: str,
                          start_node_id: int,
                          end_node_id: int,
                          base_group: str,
                          base_vessel: str):
    """
    Add a very short (1 mm) segment between two anatomical nodes, using
    the radius of `base_vessel` in `base_group` for its diameter.
    """
    radius_m   = mean_radius_from_feature(base_group, base_vessel)
    diameter_m = 2.0 * radius_m
    thick      = wall_thickness(radius_m)

    arteries.append({
        "type": "vis_f",
        "ID": ID,
        "name": name,
        "start_node": f"N{start_node_id}",
        "end_node":   f"N{end_node_id}",
        "start_diameter[SI]": diameter_m,
        "end_diameter[SI]": diameter_m,
        "start_thickness[SI]": thick,
        "end_thickness[SI]": thick,
        "length[SI]": CONNECTOR_LENGTH_M,
        "division_points": 1,
        "elastance_1[SI]": constants["elastance_1"],
        "res_start[SI]": constants["res_start"],
        "res_end[SI]": constants["res_end"],
        "visc_fact[1]": constants["visc_fact"],
        "k1[SI]": constants["k1"],
        "k2[SI]": constants["k2"],
        "k3[SI]": constants["k3"],
    })

# --- Posterior: BA bifurcation to PCA boundaries (right & left) ---
BA_BIF     = get_node_id("1", "BA bifurcation")
R_PCA_BND  = get_node_id("1", "R-PCA boundary")
L_PCA_BND  = get_node_id("1", "L-PCA boundary")

add_connector_segment("BA_to_RPCA", "BA_conn", BA_BIF, R_PCA_BND, "1", "BA")
add_connector_segment("BA_to_LPCA", "BA_conn", BA_BIF, L_PCA_BND, "1", "BA")

# --- Posterior communicating arteries (right & left) ---
P1R_PCOM_BIF   = get_node_id("2", "Pcom bifurcation")
P1L_PCOM_BIF   = get_node_id("3", "Pcom bifurcation")
PCOMR_PCA_BND  = get_node_id("8", "PCA boundary")
PCOML_PCA_BND  = get_node_id("9", "PCA boundary")
PCOMR_ICA_BIF  = get_node_id("4", "Pcom bifurcation")
PCOML_ICA_BIF  = get_node_id("6", "Pcom bifurcation")
PCOMR_ICA_BND  = get_node_id("8", "ICA boundary")
PCOML_ICA_BND  = get_node_id("9", "ICA boundary")

# P1 side -> PCA-side Pcom boundary
add_connector_segment("P1R_to_Pcom", "Pcom_conn", P1R_PCOM_BIF, PCOMR_PCA_BND, "2", "P1")
add_connector_segment("P1L_to_Pcom", "Pcom_conn", P1L_PCOM_BIF, PCOML_PCA_BND, "3", "P1")

# ICA-side Pcom boundary -> ICA trunk Pcom bifurcation
add_connector_segment("PcomR_to_ICA", "Pcom_conn", PCOMR_PCA_BND, PCOMR_ICA_BIF, "8", "Pcom")
add_connector_segment("PcomL_to_ICA", "Pcom_conn", PCOML_PCA_BND, PCOML_ICA_BIF, "9", "Pcom")

# --- Anterior: ICA bifurcations to MCA / A1 (right & left) ---
ICA_R_BIF      = get_node_id("4", "ICA bifurcation")
ICA_L_BIF      = get_node_id("6", "ICA bifurcation")
MCA_R_BOUNDARY = get_node_id("4", "MCA boundary")
MCA_L_BOUNDARY = get_node_id("6", "MCA boundary")
ACA_R_BOUNDARY = get_node_id("4", "ACA boundary")
ACA_L_BOUNDARY = get_node_id("6", "ACA boundary")

# To MCA trunks
add_connector_segment("ICA_R_to_MCA", "ICA_MCA_conn", ICA_R_BIF, MCA_R_BOUNDARY, "5", "MCA")
add_connector_segment("ICA_L_to_MCA", "ICA_MCA_conn", ICA_L_BIF, MCA_L_BOUNDARY, "7", "MCA")

# To A1 segments
add_connector_segment("ICA_R_to_A1", "ICA_A1_conn", ICA_R_BIF, ACA_R_BOUNDARY, "11", "A1")
add_connector_segment("ICA_L_to_A1", "ICA_A1_conn", ICA_L_BIF, ACA_L_BOUNDARY, "12", "A1")

# -------------------------------------------------------------
# Collect unique 1D nodes *after* adding connectors
# -------------------------------------------------------------
unique_nodes_1d = sorted({a["start_node"] for a in arteries} |
                         {a["end_node"]   for a in arteries})

print(f"[OK] V12: 1D network has {len(arteries)} arteries and {len(unique_nodes_1d)} nodes.")

# -------------------------------------------------------------
# Choose heart inlet and detect outlet (terminal) nodes
# -------------------------------------------------------------
HEART_INLET = f"N{HEART_INLET_NODE_ID}"

if HEART_INLET not in unique_nodes_1d:
    raise RuntimeError(f"Chosen heart inlet {HEART_INLET} is not a 1D node in this network.")

# Degree count to find terminals
degree = {}
for art in arteries:
    s = art["start_node"]
    e = art["end_node"]
    degree[s] = degree.get(s, 0) + 1
    degree[e] = degree.get(e, 0) + 1

terminal_nodes = sorted([n for n, d in degree.items() if d == 1])
print(f"[INFO] V12: raw terminal nodes = {terminal_nodes}")

if HEART_INLET not in terminal_nodes:
    print(f"[WARN] V12: {HEART_INLET} is not degree-1, but will still be used as heart inlet.")

outlet_nodes = [n for n in terminal_nodes if n != HEART_INLET]
print(f"[INFO] V12: using {HEART_INLET} as heart inlet.")
print(f"[INFO] V12: using {len(outlet_nodes)} outlet nodes for Windkessels:")
print("       ", outlet_nodes)

# -------------------------------------------------------------
# Write arterial.csv
# -------------------------------------------------------------
with open(ARTERIAL_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=arterial_header)
    writer.writeheader()
    for row in arteries:
        writer.writerow(row)

    # Blank line before node/perif meta-table (this matches Abel_ref2 style)
    f.write("\n")
    f.write("type,ID,name,valami,parameter,file name\n")

    # Register heart model
    f.write("heart,heart_kim_lit,0,,\n")

    # All 1D nodes
    for n in unique_nodes_1d:
        f.write(f"node,{n},0,,\n")

    # perif rows: one ID per outlet p1..pK
    for i, n in enumerate(outlet_nodes):
        pid = f"p{i+1}"
        f.write(f"perif,{pid},0,,\n")

print(f"[OK] V12: arterial.csv written -> {ARTERIAL_CSV}")

# -------------------------------------------------------------
# Write main.csv  (heart + CoW + Windkessels)
# -------------------------------------------------------------
lines = []
lines.append(["run","forward"])
lines.append(["time","10"])
lines.append(["material","linear"])
lines.append(["solver","maccormack"])
lines.append([])

lines.append(["type","name","main node","model node"])

# MOC line:
#  - Pair (node, node) for every 1D node so that solver can map
moc_row = ["moc", "arterial"]
for n in unique_nodes_1d:
    moc_row.extend([n, n])
lines.append(moc_row)
lines.append([])

# Lumped models:
# Heart model connected at HEART_INLET, internal heart node "aorta"
lines.append(["lumped", "heart_kim_lit", HEART_INLET, "aorta"])

# One Windkessel model pX at each outlet, internal interface node "n1"
for i, n in enumerate(outlet_nodes):
    pid = f"p{i+1}"
    lines.append(["lumped", pid, n, "n1"])

lines.append([])

# Node list: all 1D nodes (no extra interface nodes)
for n in unique_nodes_1d:
    lines.append(["node", n])

with open(MAIN_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(lines)

print(f"[OK] V12: main.csv written -> {MAIN_CSV}")

# -------------------------------------------------------------
# Generate Windkessel pX.csv files
# -------------------------------------------------------------
MU   = 0.0035
RHO  = 1060.0
E    = 4e6
H_FRAC     = 0.10
RPROX_FRAC = 0.30
MIN_R      = 1e6
MIN_C      = 1e-12
MIN_L      = 1e5
MIN_Radius = 2.5e-4
MIN_Length = 1e-3

def compute_R_total(r, L):
    return max((8.0 * MU * L) / (math.pi * r**4), MIN_R)

def compute_C(r):
    h = H_FRAC * r
    if h <= 0.0:
        return MIN_C
    return max((math.pi * r**3) / (2.0 * E * h), MIN_C)

def compute_L(r, L):
    A = math.pi * r**2
    if A <= 0.0:
        return MIN_L
    return max((RHO * L) / A, MIN_L)

# Read ONLY artery rows from arterial.csv (until blank line)
artery_rows = []
with open(ARTERIAL_CSV) as f:
    for line in f:
        if not line.strip():
            break
        artery_rows.append(line)

df_geo = pd.read_csv(StringIO("".join(artery_rows)))

geo = {}
for _, row in df_geo.iterrows():
    s = row["start_node"]
    e = row["end_node"]
    d = float(row["start_diameter[SI]"])
    Lm = float(row["length[SI]"])
    r  = max(d * 0.5, MIN_Radius)
    Lm = max(Lm, MIN_Length)
    geo.setdefault(s, []).append((r, Lm))
    geo.setdefault(e, []).append((r, Lm))

def avg_geo(node: str):
    """Average radius/length of arteries touching this node."""
    if node not in geo:
        return (1.0e-3, 0.02)
    r = sum(g[0] for g in geo[node]) / len(geo[node])
    Lm = sum(g[1] for g in geo[node]) / len(geo[node])
    return r, Lm

for i, n in enumerate(outlet_nodes):
    pid = f"p{i+1}"
    r, Lm = avg_geo(n)

    Rtot  = compute_R_total(r, Lm)
    Rprox = max(RPROX_FRAC * Rtot, MIN_R)
    Rdist = max((1.0 - RPROX_FRAC) * Rtot, MIN_R)
    Cval  = compute_C(r)
    Lin   = compute_L(r, Lm) * 0.25

    pfile = os.path.join(OUTPUT_DIR, f"{pid}.csv")
    with open(pfile, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["data of edges"])
        w.writerow(["type","name","node start","node end","initial condition [SI]","parameter [SI]"])
        # Interface node is "n1" (matches 'model node' in main.csv)
        w.writerow(["resistor", "R0", "n1", "P1", 0.0, f"{Rprox:.3e}"])
        w.writerow(["resistor", "R2", "P1", "g",  0.0, f"{Rdist:.3e}"])
        w.writerow(["capacitor", "C1", "P1", "g", 0.0, f"{Cval:.3e}"])
        w.writerow(["inductor", "L1", "P1", "g", 0.0, f"{Lin:.3e}"])
        w.writerow([])
        w.writerow(["data of nodes"])
        w.writerow(["type","name","initial condition [SI]"])
        w.writerow(["node","n1", 1.000e+05])
        w.writerow(["node","P1", 1.000e+05])
        w.writerow(["ground","g",1.000e+05])

print(f"[OK] V12: wrote {len(outlet_nodes)} Windkessel p-files in {OUTPUT_DIR}")

# -------------------------------------------------------------
# Copy heart model (you already weakened it manually once)
# -------------------------------------------------------------
if os.path.exists(ABEL_HEART):
    shutil.copy2(ABEL_HEART, COW_HEART)
    print(f"[OK] V12: copied heart model from {ABEL_HEART} to {COW_HEART}")
else:
    print(f"[WARN] V12: could not find {ABEL_HEART}, heart file not copied.")

print("V12 generation complete.")
