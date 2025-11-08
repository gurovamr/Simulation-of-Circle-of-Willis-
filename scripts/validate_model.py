import os
import csv
from pathlib import Path

# Set paths
base_dir = Path(__file__).resolve().parent.parent  # go up from scripts/
model_dir = base_dir / "models" / "cow_runV2"
main_csv = model_dir / "main.csv"
px_files = list(model_dir.glob("p*.csv"))

# Load declared nodes and connections from main.csv
declared_nodes = set()
lumped_nodes = []
moc_connections = []

with open(main_csv, newline='') as f:
    for line in csv.reader(f):
        if not line or line[0].startswith("#") or not line[0].strip():
            continue
        if line[0] == "node":
            declared_nodes.add(line[1])
        elif line[0] == "lumped":
            model, main_node, model_node = line[1:4]
            lumped_nodes.append((model, main_node, model_node))
        elif line[0] == "moc":
            i = 2
            while i + 1 < len(line):
                main_node = line[i]
                model_name = line[i + 1]
                moc_connections.append((main_node, model_name))
                i += 2

# Parse all pX.csv files
px_connections = set()
for f in px_files:
    with open(f, newline='') as pf:
        reader = csv.reader(pf)
        next(reader)  # skip header
        for row in reader:
            if len(row) >= 2:
                px_connections.add((row[0], f.stem))
                px_connections.add((row[1], f.stem))

# === Validation ===
errors = []

# Check lumped nodes
for model, main_node, model_node in lumped_nodes:
    if model_node != main_node:
        errors.append(f"[LUMPED] Model {model}: mismatch {main_node} ≠ {model_node}")
    if main_node not in declared_nodes:
        errors.append(f"[LUMPED] Model {model}: node {main_node} not declared")

# Check moc nodes
for main_node, model in moc_connections:
    if main_node not in declared_nodes:
        errors.append(f"[MOC] Node {main_node} used in model {model} not declared")

# Check pX.csv coverage
moc_set = set(moc_connections)
missing_in_main = px_connections - moc_set
missing_in_px = moc_set - px_connections

for node, model in missing_in_main:
    errors.append(f"[pX.csv] Node {node} in {model}.csv not declared in main.csv")

for node, model in missing_in_px:
    errors.append(f"[main.csv] Node {node} for model {model} not found in any pX.csv file")

# Output
print("=== MODEL VALIDATION REPORT ===")
if errors:
    for err in errors:
        print("❌", err)
    print(f"\nTotal issues found: {len(errors)}")
else:
    print("✅ All nodes and connections are consistent.")
