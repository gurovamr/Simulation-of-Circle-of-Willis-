import csv
from pathlib import Path
from collections import defaultdict

# === CONFIG ===
ARTERIAL_CSV = Path("../outputs/arterial.csv")
MAIN_CSV = Path("../outputs/main.csv")
SIMULATION_TIME = 10.0  # seconds
SOLVER = "maccormack"

# === Read arterial.csv to extract vessel and node structure ===
with open(ARTERIAL_CSV, newline="") as f:
    reader = csv.DictReader(f)
    vessels = [row for row in reader if row['type'] == 'vis_f']

# Track node connections
connections = defaultdict(list)

for row in vessels:
    start = row['start_node']
    end = row['end_node']
    connections[start].append(end)

# Find terminal nodes (nodes not used as start_node)
all_start_nodes = set(row['start_node'] for row in vessels)
all_end_nodes = set(row['end_node'] for row in vessels)
terminal_nodes = sorted(all_end_nodes - all_start_nodes)

# Assume Heart is the first start node
inlet_node = sorted(all_start_nodes)[0]

# === Write main.csv ===
with open(MAIN_CSV, "w", newline="") as f:
    writer = csv.writer(f)

    # Global simulation parameters
    writer.writerow(["run", "forward"])
    writer.writerow(["time", f"{SIMULATION_TIME:.3f}"])
    writer.writerow(["material", "linear"])
    writer.writerow(["solver", SOLVER])
    writer.writerow([])

    # MOC type connections
    writer.writerow(["type", "name", "main node", "model node"] +
                    [f"N{i+1}p" for i in range(len(terminal_nodes))] + ["Heart"])
    writer.writerow(["moc", "arterial"] + [f"p{i+1}" for i in range(len(terminal_nodes))] + ["H"])
    writer.writerow([])

    # Lumped peripheral connections
    for i, node in enumerate(terminal_nodes):
        writer.writerow(["lumped", f"p{i+1}", f"N{i+1}p", node])
    writer.writerow(["lumped", "heart_cow", "Heart", inlet_node])
    writer.writerow([])

    # Output nodes
    for i in range(len(terminal_nodes)):
        writer.writerow(["node", f"N{i+1}p"])
    writer.writerow(["node", "Heart"])

print(f"main.csv written with {len(terminal_nodes)} periphery connections → {MAIN_CSV}")
