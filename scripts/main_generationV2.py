import json
import csv
import os

# --- Paths ---
base_dir = os.path.dirname(__file__)  # /scripts/
input_dir = os.path.abspath(os.path.join(base_dir, "../data_patient025"))
output_dir = os.path.abspath(os.path.join(base_dir, "../outputs"))
os.makedirs(output_dir, exist_ok=True)

# --- Load JSON files ---
with open(os.path.join(input_dir, 'feature_mr_025.json')) as f:
    features = json.load(f)
with open(os.path.join(input_dir, 'nodes_mr_025.json')) as f:
    nodes = json.load(f)

# --- Output setup ---
moc_line = ["moc", "arterial"]
lumped_lines = []
node_ids = set()
p_index = 1

# --- Process each segment ---
for section in features.values():
    for vessel_name, vessel_data in section.items():
        for item in vessel_data:
            if 'segment' not in item:
                continue  # Skip bifurcations
            segment = item['segment']
            start_id = segment['start']
            end_id = segment['end']

            # Format node and file names
            N_start = f"N{start_id}"
            N_end = f"N{end_id}"
            p_file = f"p{p_index}"

            # Add to MoC connection line
            moc_line += [N_start, p_file, N_end, p_file]

            # Add to lumped lines
            lumped_lines.append(["lumped", p_file, N_start, "n1"])
            lumped_lines.append(["lumped", p_file, N_end, "n1"])

            # Track nodes
            node_ids.update([N_start, N_end])
            p_index += 1

# --- Write main.csv ---
main_path = os.path.join(output_dir, "main.csv")
with open(main_path, "w", newline="") as f:
    writer = csv.writer(f)
    # Header
    writer.writerow(["run", "forward"])
    writer.writerow(["time", "10"])
    writer.writerow(["material", "linear"])
    writer.writerow(["solver", "maccormack"])
    # MoC line
    writer.writerow(["type", "name", "main node", "model node"] + moc_line[2:])
    writer.writerow(moc_line)
    # Lumped elements
    writer.writerows(lumped_lines)
    # Node list
    for node in sorted(node_ids):
        writer.writerow(["node", node])

print(f" main.csv generated at: {main_path}")
