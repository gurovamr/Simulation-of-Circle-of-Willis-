import csv
import os

model_name = "cow_runV2"
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
model_dir = os.path.join(base_dir, "models", model_name)

main_path = os.path.join(model_dir, "main_fixed.csv")
clean_path = os.path.join(model_dir, "main_clean.csv")

if not os.path.exists(main_path):
    print(f"[ERROR] main.csv not found at {main_path}")
    exit(1)

with open(main_path, newline='') as f_in, open(clean_path, "w", newline='') as f_out:
    reader = csv.reader(f_in)
    writer = csv.writer(f_out)
    
    for row in reader:
        clean_row = [cell.strip() for cell in row]
        writer.writerow(clean_row)

print(f"Cleaned main.csv written to: {clean_path}")
