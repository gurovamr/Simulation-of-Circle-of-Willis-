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
OUTPUT_DIR = "../models/cow_runV5"

FEATURE_FILE = os.path.join(INPUT_DIR, "feature_mr_025.json")
NODES_FILE = os.path.join(INPUT_DIR, "nodes_mr_025.json")
VARIANT_FILE = os.path.join(INPUT_DIR, "variant_mr_025.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

ARTERIAL_CSV = os.path.join(OUTPUT_DIR, "arterial.csv")
MAIN_CSV     = os.path.join(OUTPUT_DIR, "main.csv")


# -------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------
def wall_thickness(radius_m: float) -> float:
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

def si(mm: float) -> float:
    return float(mm) / 1000.0


def load_json(path: str):
    with open(path) as f:
        return json.load(f)


# -------------------------------------------------------------
# Load patient data
# -------------------------------------------------------------
feature_data = load_json(FEATURE_FILE)
nodes_data   = load_json(NODES_FILE)      # not used directly, kept for completeness
variant_data = load_json(VARIANT_FILE)   # not used directly


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
        # skip bifurcation helper elements
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

# write arterial.csv
with open(ARTERIAL_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=arterial_header)
    writer.writeheader()
    for row in arteries:
        writer.writerow(row)

    # blank line before node table
    f.write("\n")
    f.write("type,ID,name,valami,parameter,file name\n")

    unique_nodes_1d = sorted({a["start_node"] for a in arteries} |
                             {a["end_node"]   for a in arteries})

    for n in unique_nodes_1d:
        f.write(f"node,{n},0,,\n")

print(f"[OK] V5: arterial.csv written with {len(arteries)} arteries and {len(unique_nodes_1d)} 1D nodes")


# -------------------------------------------------------------
# Detect terminal 1D nodes (degree = 1) for outlets
# -------------------------------------------------------------
degree = {}
for art in arteries:
    s = art["start_node"]
    e = art["end_node"]
    degree[s] = degree.get(s, 0) + 1
    degree[e] = degree.get(e, 0) + 1

terminal_nodes = sorted([n for n, d in degree.items() if d == 1])

print(f"[INFO] V5: detected {len(terminal_nodes)} terminal nodes for p-models:")
print("      ", terminal_nodes)


# -------------------------------------------------------------
# Create main.csv (1D–0D structure)
# -------------------------------------------------------------
lines = []
lines.append(["run","forward"])
lines.append(["time","10"])
lines.append(["material","linear"])
lines.append(["solver","maccormack"])
lines.append([])

lines.append(["type","name","main node","model node"])

# MOC line: for each terminal 1D node Nterm, create a 0D interface node Ntermp
# pair (Nterm, Ntermp)
moc_row = ["moc", "arterial"]
interface_nodes = []
for n in terminal_nodes:
    n_if = f"{n}p"   # e.g. N15 -> N15p
    interface_nodes.append(n_if)
    moc_row.extend([n, n_if])
lines.append(moc_row)
lines.append([])

# Lumped models: one per terminal node
# p1 -> N15p, internal inlet node = N15 (inside p-file)
for i, n in enumerate(terminal_nodes):
    pid = f"p{i+1}"
    n_if = f"{n}p"
    # main node = interface node in the global system
    # model node = same interface node inside the p-model
    lines.append(["lumped", pid, n_if, n_if])


lines.append([])

# Node list for the global system: all 1D nodes + all 0D interface nodes
all_nodes = unique_nodes_1d + interface_nodes
for n in all_nodes:
    lines.append(["node", n])

with open(MAIN_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(lines)

print(f"[OK] V5: main.csv written with {len(terminal_nodes)} lumped models and {len(all_nodes)} total nodes")


# -------------------------------------------------------------
# Generate Windkessel pX.csv files for each terminal node
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

# Read ONLY artery rows from arterial.csv (stop before node table)
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
    L = float(row["length[SI]"])
    r = max(d * 0.5, MIN_Radius)
    Lm = max(L, MIN_Length)
    geo.setdefault(s, []).append((r, Lm))
    geo.setdefault(e, []).append((r, Lm))

def avg_geo(node: str):
    if node not in geo:
        # fallback if something weird
        return (1.0e-3, 0.02)
    r = sum(g[0] for g in geo[node]) / len(geo[node])
    Lm = sum(g[1] for g in geo[node]) / len(geo[node])
    return r, Lm

for i, n in enumerate(terminal_nodes):
    pid = f"p{i+1}"
    n_if = f"{n}p"   # global interface 0D node
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
        # interface node is n_if, internal "P1"
        w.writerow(["resistor", "R0", n_if, "P1", 0.0, f"{Rprox:.3e}"])
        w.writerow(["resistor", "R2", "P1", "g", 0.0, f"{Rdist:.3e}"])
        w.writerow(["capacitor", "C1", "P1", "g", 0.0, f"{Cval:.3e}"])
        w.writerow(["inductor", "L1", "P1", "g", 0.0, f"{Lin:.3e}"])
        w.writerow([])
        w.writerow(["data of nodes"])
        w.writerow(["type","name","initial condition [SI]"])
        w.writerow(["node", n_if, 1.000e+05])
        w.writerow(["node", "P1",  1.000e+05])
        w.writerow(["ground", "g", 1.000e+05])

print(f"[OK] V5: wrote {len(terminal_nodes)} Windkessel p-files in {OUTPUT_DIR}")
print("V5 generation complete.")
