#!/usr/bin/env python3
import json
import csv
import os

# --- Configuration ---
INPUT_DIR = "../data_patient025"
OUTPUT_DIR = "../models/cow_runV3"

FEATURE_FILE = os.path.join(INPUT_DIR, "feature_mr_025.json")
NODES_FILE = os.path.join(INPUT_DIR, "nodes_mr_025.json")
VARIANT_FILE = os.path.join(INPUT_DIR, "variant_mr_025.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

ARTERIAL_CSV = os.path.join(OUTPUT_DIR, "arterial.csv")
MAIN_CSV = os.path.join(OUTPUT_DIR, "main.csv")

# --- Helper functions ---
def wall_thickness(radius_m):
    """Approximate wall thickness as 10% of vessel radius."""
    return 0.1 * radius_m

def default_material():
    """Default mechanical constants based on Aber_ref2 typical values."""
    return dict(
        elastance_1=5.0e5,
        res_start=0.0,
        res_end=0.0,
        visc_fact=2.75,
        k1=2.0e6,
        k2=-2253.0,
        k3=8.65e4
    )

def si(mm_value):
    """Convert mm to meters."""
    return float(mm_value) / 1000.0


# --- Load patient data ---
with open(FEATURE_FILE) as f:
    feature_data = json.load(f)

with open(NODES_FILE) as f:
    nodes_data = json.load(f)

with open(VARIANT_FILE) as f:
    variant_data = json.load(f)

# --- Create arterial.csv ---
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
        # skip bifurcations, only process true segments
        if "bifurcation" in vessel_name.lower():
            continue
        for seg in vessel_list:
            start = f"N{seg['segment']['start']}"
            end = f"N{seg['segment']['end']}"
            radius_m = si(seg['radius']['mean'])
            diameter_m = 2 * radius_m
            thickness_m = wall_thickness(radius_m)
            length_m = si(seg['length'])
            #entry = {
                #"type": "vis_f",
                #"ID": f"{vessel_name}_{group_id}",
                #"name": vessel_name,
                #"start_node": start,
                #"end_node": end,
                #"start_diameter[SI]": diameter_m,
                #"end_diameter[SI]": diameter_m,
                #"start_thickness[SI]": thickness_m,
                #"end_thickness[SI]": thickness_m,
                #"length[SI]": length_m,
                #"division_points": 5,
                #**constants
            #}
            entry = {
                "type": "vis_f",
                "ID": f"{vessel_name}_{group_id}",
                "name": vessel_name,
                "start_node": start,
                "end_node": end,
                "start_diameter[SI]": diameter_m,
                "end_diameter[SI]": diameter_m,
                "start_thickness[SI]": thickness_m,
                "end_thickness[SI]": thickness_m,
                "length[SI]": length_m,
                "division_points": 5,
                "elastance_1[SI]": constants["elastance_1"],
                "res_start[SI]": constants["res_start"],
                "res_end[SI]": constants["res_end"],
                "visc_fact[1]": constants["visc_fact"],
                "k1[SI]": constants["k1"],
                "k2[SI]": constants["k2"],
                "k3[SI]": constants["k3"],
            }

            arteries.append(entry)

with open(ARTERIAL_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=arterial_header)
    writer.writeheader()
    for row in arteries:
        writer.writerow(row)

print(f"[+] Generated {ARTERIAL_CSV} with {len(arteries)} arterial segments.")


# --- Create main.csv ---
main_lines = []
main_lines.append(["run","forward"])
main_lines.append(["time","10"])
main_lines.append(["material","linear"])
main_lines.append(["solver","maccormack"])
main_lines.append([])
main_lines.append([
    "type","name","main node","model node",
    "main node","model node","main node","model node"
])

# 1. MOC (arterial connections)
arterial_nodes = []
for art in arteries:
    arterial_nodes.append(art["start_node"])
    arterial_nodes.append(art["end_node"])

# keep unique nodes, preserve order
arterial_nodes = list(dict.fromkeys(arterial_nodes))

# assign unique model names
node_model_pairs = []
for i, node in enumerate(arterial_nodes, start=1):
    model_name = f"p{i}"
    node_model_pairs.append((node, model_name))

# build MOC line
moc_line = ["moc", "arterial"]
for node, model in node_model_pairs:
    moc_line.extend([node, model])
main_lines.append(moc_line)
main_lines.append([])

# 2. Lumped connections
for node, model in node_model_pairs:
    main_lines.append(["lumped", model, node, node])

# 3. Node list
main_lines.append([])
for node, _ in node_model_pairs:
    main_lines.append(["node", node])


# --- Write main.csv ---
with open(MAIN_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    for row in main_lines:
        writer.writerow(row)

print(f"[+] Generated {MAIN_CSV}.")


# --- Summary ---
print("\n Generation complete!")
print(f"Arterial segments: {len(arteries)}")
print(f"Main connections:  {len(arterial_nodes)}")
print(f"Output written to: {os.path.abspath(OUTPUT_DIR)}")
