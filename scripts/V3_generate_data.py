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
        if "bifurcation" in vessel_name.lower():
            continue
        for seg in vessel_list:
            start = f"N{seg['segment']['start']}"
            end = f"N{seg['segment']['end']}"
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

with open(ARTERIAL_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=arterial_header)
    writer.writeheader()

    # Write all 1D artery segments (edges)
    for row in arteries:
        writer.writerow(row)

    print("[INFO] Wrote arterial edges, now adding node definitions...")

    # --- ADD NODE SECTION (required by First Blood) ---
    # Gather all unique nodes from start/end
    unique_nodes = set()
    for art in arteries:
        unique_nodes.add(art["start_node"])
        unique_nodes.add(art["end_node"])

    # Blank line to separate sections
    f.write("\n")

    # Abel_ref2-style header for node table
    f.write("type,ID,name,valami,parameter,file name\n")

    # Write all node rows
    # You can put 0 for "valami" or a constant like 5.27E+11 — both work.
    for n in sorted(unique_nodes):
        f.write(f"node,{n},0,,\n")


print(f"[+] Generated {ARTERIAL_CSV} with {len(arteries)} arterial segments.")


# ---------------------------------------------------------------
# ---------------------- CREATE MAIN.CSV ------------------------
# ---------------------------------------------------------------

main_lines = []
main_lines.append(["run","forward"])
main_lines.append(["time","10"])
main_lines.append(["material","linear"])
main_lines.append(["solver","maccormack"])
main_lines.append([])
main_lines.append(["type","name","main node","model node"])

# 1) MOC line – ONLY 1D arterial connections
moc_line = ["moc", "arterial"]

for art in arteries:
    s = art["start_node"]
    e = art["end_node"]
    moc_line.extend([s, e])

main_lines.append(moc_line)
main_lines.append([])

# 2) Create lumped models (one pX per unique node)
unique_nodes = list(dict.fromkeys(
    [a["start_node"] for a in arteries] +
    [a["end_node"] for a in arteries]
))

node_model_pairs = [(node, f"p{i+1}") for i, node in enumerate(unique_nodes)]

for node, model in node_model_pairs:
    main_lines.append(["lumped", model, node, node])

main_lines.append([])

# 3) Node list
for node, _ in node_model_pairs:
    main_lines.append(["node", node])


# Write main.csv
with open(MAIN_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(main_lines)

print(f"[+] Generated {MAIN_CSV}.")

# Summary
print("\nGeneration complete!")
print(f"Arterial segments: {len(arteries)}")
print(f"MOC nodes:         {len(unique_nodes)}")
print(f"Output written to: {os.path.abspath(OUTPUT_DIR)}")
