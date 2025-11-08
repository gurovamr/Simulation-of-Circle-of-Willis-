import csv
import os

model_name = "cow_runV2"
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
main_path = os.path.join(base_dir, "models", model_name, "main.csv")

if not os.path.exists(main_path):
    print(f"[ERROR] main.csv not found at: {main_path}")
    exit(1)

declared_nodes = set()
used_nodes = set()

with open(main_path, newline='') as f:
    for row in csv.reader(f):
        if not row:
            continue
        if row[0] == "node":
            declared_nodes.add(row[1].strip())
        elif row[0] == "lumped":
            used_nodes.add(row[2].strip())  # main node
            used_nodes.add(row[3].strip())  # model node
        elif row[0] == "moc":
            for i in range(2, len(row), 2):
                used_nodes.add(row[i].strip())  # node
                # model node is a pX, not added here

undefined = sorted(used_nodes - declared_nodes)

print("\n=== UNDECLARED NODES USED IN main.csv ===")
if undefined:
    for node in undefined:
        print(f" {node} is used but NOT declared as 'node,{node}'")
    print(f"\n Total missing: {len(undefined)}")
else:
    print("All used nodes are properly declared.")
