import os
import csv

# --- Paths ---
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
model_name = "cow_runV2"
model_dir = os.path.join(base_dir, "models", model_name)

input_main = os.path.join(model_dir, "main.csv")
output_main = os.path.join(model_dir, "main_fixed.csv")

if not os.path.isfile(input_main):
    print(f"[ERROR] Could not find main.csv in {model_dir}")
    exit(1)

with open(input_main, newline='') as f:
    lines = list(csv.reader(f))

fixed_lines = []
for row in lines:
    if row and row[0] == "lumped":
        # Replace 'n1' with the same node name from column 2 (model node = global node)
        fixed_row = [row[0], row[1], row[2], row[2]]  # make column 4 = column 2
        fixed_lines.append(fixed_row)
    else:
        fixed_lines.append(row)

# Write new file
with open(output_main, "w", newline='') as f_out:
    writer = csv.writer(f_out)
    writer.writerows(fixed_lines)

print(f"Fixed main.csv saved as: {output_main}")
print("   - All 'n1' replaced with proper node names.")
