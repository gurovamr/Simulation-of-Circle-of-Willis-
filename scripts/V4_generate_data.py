#!/usr/bin/env python3
import json
import csv
import os
import math
from io import StringIO
import pandas as pd

# -------------------------------------------------------------
# Configuration
# -------------------------------------------------------------
INPUT_DIR = "../data_patient025"
OUTPUT_DIR = "../models/cow_runV4"

FEATURE_FILE = os.path.join(INPUT_DIR, "feature_mr_025.json")
NODES_FILE = os.path.join(INPUT_DIR, "nodes_mr_025.json")
VARIANT_FILE = os.path.join(INPUT_DIR, "variant_mr_025.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

ARTERIAL_CSV = os.path.join(OUTPUT_DIR, "arterial.csv")
MAIN_CSV     = os.path.join(OUTPUT_DIR, "main.csv")


# -------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------
def wall_thickness(radius_m):
    return 0.1 * radius_m

def default_material():
    return dict(
        elastance_1=5.0e5,
        res_start=0.0,
        res_end=0.0,
        visc_fact=2.75,
        k1=2.0e6,
        k2=-2253.0,
        k3=8.65e4
    )

def si(mm):
    return float(mm) / 1000.0


# -------------------------------------------------------------
# Load patient data
# -------------------------------------------------------------
def load_json(path):
    with open(path) as f:
        return json.load(f)

feature_data = load_json(FEATURE_FILE)
nodes_data = load_json(NODES_FILE)      # not used directly but kept
variant_data = load_json(VARIANT_FILE)  # for completeness


# -------------------------------------------------------------
# Create arterial.csv
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
        # skip bifurcation helper objects
        if "bifurcation" in vessel_name.lower():
            continue
        for seg in vessel_list:
            start = f"N{seg['segment']['start']}"
            end   = f"N{seg['segment']['end']}"
            radius_m = si(seg['radius']['mean'])
            diameter_m = 2 * radius_m
            thick = wall_thickness(radius_m)
            length = si(seg['length'])

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

# Write arterial.csv (arteries + node table)
with open(ARTERIAL_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=arterial_header)
    writer.writeheader()
    for row in arteries:
        writer.writerow(row)

    # blank line before node table
    f.write("\n")
    f.write("type,ID,name,valami,parameter,file name\n")

    unique_nodes = sorted({a["start_node"] for a in arteries} |
                          {a["end_node"]   for a in arteries})

    for n in unique_nodes:
        f.write(f"node,{n},0,,\n")

print(f"[OK] arterial.csv written ({len(arteries)} arteries)")


# -------------------------------------------------------------
# Graph degrees → terminal nodes
# -------------------------------------------------------------
node_degree = {}
for art in arteries:
    s = art["start_node"]
    e = art["end_node"]
    node_degree[s] = node_degree.get(s, 0) + 1
    node_degree[e] = node_degree.get(e, 0) + 1

terminal_nodes = sorted([n for n, deg in node_degree.items() if deg == 1])

if not terminal_nodes:
    print("[WARN] No terminal nodes detected – check your geometry.")

print(f"[INFO] Detected {len(terminal_nodes)} terminal nodes for p-files.")


# -------------------------------------------------------------
# Create main.csv with Abel_ref2-style single MOC line
# -------------------------------------------------------------
lines = []
lines.append(["run","forward"])
lines.append(["time","10"])
lines.append(["material","linear"])
lines.append(["solver","maccormack"])
lines.append([])

# header (Abel_ref2 style; extra pairs allowed after col 4)
lines.append(["type","name","main node","model node"])

# Single MOC row: moc,arterial, N1,p1, N2,p2, ...
moc_row = ["moc", "arterial"]
for i, node in enumerate(terminal_nodes):
    pid = f"p{i+1}"
    moc_row.extend([node, pid])
lines.append(moc_row)
lines.append([])

# Lumped models: one per terminal node
for i, node in enumerate(terminal_nodes):
    pid = f"p{i+1}"
    # main node in network = node, model node (inside p-file) = same name
    lines.append(["lumped", pid, node, node])

lines.append([])

# Node list: all 1D-network nodes
for n in unique_nodes:
    lines.append(["node", n])

with open(MAIN_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(lines)

print(f"[OK] main.csv written with {len(terminal_nodes)} lumped models.")


# -------------------------------------------------------------
# Generate Windkessel pX.csv files (one per terminal node)
# -------------------------------------------------------------
MU   = 0.0035
RHO  = 1060.0
E    = 4e6
H_FRAC = 0.10
RPROX_FRAC = 0.30
MIN_R = 1e6
MIN_C = 1e-12
MIN_L = 1e5
MIN_Radius = 2.5e-4
MIN_Length = 1e-3

def compute_R_total(r, L):
    return max((8*MU*L) / (math.pi*r**4), MIN_R)

def compute_C(r):
    h = H_FRAC * r
    if h <= 0:
        return MIN_C
    return max((math.pi*r**3) / (2*E*h), MIN_C)

def compute_L(r, L):
    A = math.pi*r**2
    if A <= 0:
        return MIN_L
    return max((RHO*L) / A, MIN_L)

# Read ONLY artery rows from arterial.csv
artery_rows = []
with open(ARTERIAL_CSV) as f:
    for line in f:
        if not line.strip():
            break  # stop at blank line before node table
        artery_rows.append(line)

df_geo = pd.read_csv(StringIO("".join(artery_rows)))

geo = {}
for _, row in df_geo.iterrows():
    s = row["start_node"]
    e = row["end_node"]
    d = float(row["start_diameter[SI]"])
    L = float(row["length[SI]"])
    r = max(d * 0.5, MIN_Radius)
    Lm = max(L, MIN_Length)
    geo.setdefault(s, []).append((r, Lm))
    geo.setdefault(e, []).append((r, Lm))

def avg_geo(node):
    if node not in geo:
        # fallback if node not found in artery table
        return (1e-3, 0.02)
    r = sum(g[0] for g in geo[node]) / len(geo[node])
    Lm = sum(g[1] for g in geo[node]) / len(geo[node])
    return r, Lm

for i, node in enumerate(terminal_nodes):
    pid = f"p{i+1}"
    r, Lm = avg_geo(node)

    Rtot  = compute_R_total(r, Lm)
    Rprox = max(RPROX_FRAC * Rtot, MIN_R)
    Rdist = max((1 - RPROX_FRAC) * Rtot, MIN_R)
    Cval  = compute_C(r)
    Lin   = compute_L(r, Lm) * 0.25

    pfile = os.path.join(OUTPUT_DIR, f"{pid}.csv")
    with open(pfile, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["data of edges"])
        w.writerow(["type","name","node start","node end","initial condition [SI]","parameter [SI]"])
        w.writerow(["resistor", "R0", node, "P1", 0.0, f"{Rprox:.3e}"])
        w.writerow(["resistor", "R2", "P1", "g", 0.0, f"{Rdist:.3e}"])
        w.writerow(["capacitor", "C1", "P1", "g", 0.0, f"{Cval:.3e}"])
        w.writerow(["inductor", "L1", "P1", "g", 0.0, f"{Lin:.3e}"])
        w.writerow([])
        w.writerow(["data of nodes"])
        w.writerow(["type","name","initial condition [SI]"])
        w.writerow(["node", node, 1.000e+05])
        w.writerow(["node", "P1", 1.000e+05])
        w.writerow(["ground", "g", 1.000e+05])

print(f"[OK] Wrote {len(terminal_nodes)} Windkessel p-files in {OUTPUT_DIR}")
print("Generation complete.")
