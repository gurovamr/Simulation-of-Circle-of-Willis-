#!/bin/bash

# Directory where the main files are stored
DIR="$HOME/Simulation-of-Circle-of-Willis/models/cow_runV2"

cd "$DIR" || { echo "Directory not found"; exit 1; }

echo "Comparing main.csv files in: $DIR"
echo

# Check files exist
for f in main.csv main_clean.csv main_fixed.csv; do
    if [ ! -f "$f" ]; then
        echo " Missing file: $f"
        echo "Make sure file names are exactly: main.csv, main_clean.csv, main_fixed.csv"
        exit 1
    fi
done

echo "=== Diff: main.csv vs main_clean.csv ==="
diff -y --suppress-common-lines main.csv main_clean.csv || echo "(No differences)"
echo

echo "=== Diff: main.csv vs main_fixed.csv ==="
diff -y --suppress-common-lines main.csv main_fixed.csv || echo "(No differences)"
echo

echo "=== Diff: main_clean.csv vs main_fixed.csv ==="
diff -y --suppress-common-lines main_clean.csv main_fixed.csv || echo "(No differences)"
echo

echo " Comparison finished."
