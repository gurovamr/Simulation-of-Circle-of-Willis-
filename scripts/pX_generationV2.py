import json
import os
import csv

# --- Paths ---
base_dir = os.path.dirname(__file__)
input_path = os.path.abspath(os.path.join(base_dir, "../data_patient025/feature_mr_025.json"))
output_dir = os.path.abspath(os.path.join(base_dir, "../outputs"))
os.makedirs(output_dir, exist_ok=True)

# --- Material properties (constants) ---
E1 = 4e6
E2 = 8e5
eta = 5e3

# --- Load data ---
with open(input_path) as f:
    features = json.load(f)

# --- Generate pX.csv files ---
p_index = 1
for section in features.values():
    for vessel_name, vessel_data in section.items():
        for entry in vessel_data:
            if 'segment' not in entry:
                continue  # skip bifurcations

            segment = entry['segment']
            radius_mm = entry['radius']['mean']
            length_mm = entry['length']

            id_start = segment['start']
            id_end = segment['end']
            length_cm = round(length_mm / 10, 3)
            diameter_cm = round(2 * radius_mm / 10, 3)
            wall_thickness = round(0.1 * diameter_cm, 3)

            filename = os.path.join(output_dir, f"p{p_index}.csv")
            with open(filename, "w", newline="") as f_csv:
                writer = csv.writer(f_csv)
                writer.writerow(["id_start", "id_end", "length", "diameter", "wall_thickness", "E1", "E2", "eta"])
                writer.writerow([f"N{id_start}", f"N{id_end}", length_cm, diameter_cm, wall_thickness, E1, E2, eta])

            p_index += 1

print(f"Generated {p_index-1} pX.csv files in: {output_dir}")
