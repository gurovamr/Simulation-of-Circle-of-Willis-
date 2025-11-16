import os
import csv

INPUT_FOLDER = "../models/cow_runV3"
MAIN_FILE = os.path.join(INPUT_FOLDER, "main.csv")

# create p-files directory (optional)
os.makedirs(INPUT_FOLDER, exist_ok=True)

# read main.csv to get lumped model mapping
pairs = []  # list of (model, node)
with open(MAIN_FILE) as f:
    for line in f:
        if line.startswith("lumped"):
            parts = line.strip().split(",")
            model = parts[1]
            node  = parts[2]
            pairs.append((model, node))

print(f"Found {len(pairs)} lumped models.")

# generate minimal p-files
for model, node in pairs:
    filename = os.path.join(INPUT_FOLDER, f"{model}.csv")
    with open(filename, "w") as f:
        f.write("data of edges\n")
        f.write("type, name, node start, node end, initial condition [SI], parameter [SI]\n\n")

        f.write("data of nodes\n")
        f.write("type, name, initial condition [SI]\n")
        f.write(f"node, {node}, 100000\n")

    print(f"Wrote {filename}")

print("\nAll p-files generated successfully.")
