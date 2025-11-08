import os
import csv

# CONFIG: Set the model folder name
MODEL_NAME = "cow_runV2"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH = os.path.join(BASE_DIR, "models", MODEL_NAME)

main_path = os.path.join(MODEL_PATH, "main.csv")
arterial_path = os.path.join(MODEL_PATH, "arterial.csv")

errors = []

# --- 1. Check main.csv exists ---
if not os.path.isfile(main_path):
    errors.append(f"[ERROR] main.csv not found in: {MODEL_PATH}")
else:
    with open(main_path, newline='') as f:
        reader = list(csv.reader(f))

    declared_nodes = set()
    p_files = set()
    moc_found = False

    for row in reader:
        if not row: continue
        if row[0].startswith("node"):
            declared_nodes.add(row[1].strip())
        elif row[0].startswith("lumped"):
            if len(row) < 4:
                errors.append(f"[ERROR] Invalid lumped line: {row}")
            declared_nodes.add(row[2].strip())
            declared_nodes.add(row[3].strip())
            p_files.add(f"{row[1].strip()}.csv")
        elif row[0] == "moc":
            moc_found = True
            if len(row) % 2 != 0:
                errors.append("[ERROR] moc line has unpaired nodes/files.")
            for i in range(2, len(row), 2):
                declared_nodes.add(row[i].strip())
                p_files.add(f"{row[i+1].strip()}.csv")

    if not moc_found:
        errors.append("[ERROR] No moc line found in main.csv")

# --- 2. Check all pX.csv files exist ---
for p in sorted(p_files):
    p_path = os.path.join(MODEL_PATH, p)
    if not os.path.isfile(p_path):
        errors.append(f"[ERROR] Missing file: {p}")
    else:
        with open(p_path, newline='') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            required = ["id_start", "id_end", "length", "diameter", "wall_thickness", "E1", "E2", "eta"]
            for req in required:
                if req not in headers:
                    errors.append(f"[ERROR] {p} is missing field: {req}")
            for row in reader:
                if row['id_start'] not in declared_nodes:
                    errors.append(f"[ERROR] {p}: id_start {row['id_start']} not declared in main.csv")
                if row['id_end'] not in declared_nodes:
                    errors.append(f"[ERROR] {p}: id_end {row['id_end']} not declared in main.csv")

# --- 3. Check arterial.csv exists and is minimal format ---
if not os.path.isfile(arterial_path):
    errors.append("[ERROR] arterial.csv is missing.")
else:
    with open(arterial_path, newline='') as f:
        lines = list(csv.reader(f))
        if len(lines) < 4 or lines[0][0] != "rho":
            errors.append("[ERROR] arterial.csv does not follow minimal format (rho,nu; E1,E2,eta)")

# --- 4. Report results ---
print("\n=== MODEL INTEGRITY CHECK REPORT ===")
if not errors:
    print(f" All checks passed for model: {MODEL_NAME}")
else:
    for e in errors:
        print(e)
    print(f"\n {len(errors)} error(s) found in model: {MODEL_NAME}")
