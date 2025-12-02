#!/usr/bin/env python3

"""
Diagnostic script to compare:
  - base Abel_ref2 model
  - your cow_runV22 model

It checks:
  1. nodes used in arterial.csv
  2. nodes declared in main.csv
  3. Windkessel (pX) definitions
  4. missing or extra nodes
  5. nodes added by V22
  6. mismatched vessel IDs

Run:
  python3 V22_diagnostic.py
"""

import os
import csv

BASE = "../models/Abel_ref2"
V22  = "../models/cow_runV22"


def read_arterial_nodes(path):
    used = set()
    vessels = set()
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 5:
                continue
            if row[0] == "vis_f":
                vessels.add(row[1])
                used.add(row[3])   # start node
                used.add(row[4])   # end node
    return used, vessels


def read_main_nodes_and_lumped(path):
    declared_nodes = set()
    lumped_models = {}
    with open(path, "r") as f:
        for row in csv.reader(f):
            if not row:
                continue
            if row[0] == "node":
                declared_nodes.add(row[1])
            elif row[0] == "lumped":
                # lumped,name,mainnode,modelnode
                if len(row) >= 4:
                    lumped_models[row[1]] = (row[2], row[3])
    return declared_nodes, lumped_models


def list_windkessels(folder):
    wk = set()
    for fname in os.listdir(folder):
        if fname.startswith("p") and fname.endswith(".csv"):
            wk.add(fname[:-4])  # p1.csv -> p1
    return wk


def header(title):
    print("\n" + "="*60)
    print(title)
    print("="*60)


def main():
    # -------------------------------------------------------
    # Load BASE MODEL data
    # -------------------------------------------------------
    print("[INFO] Reading Abel_ref2 model...")
    base_art_nodes, base_vessels = read_arterial_nodes(os.path.join(BASE, "arterial.csv"))
    base_nodes_main, base_lumped = read_main_nodes_and_lumped(os.path.join(BASE, "main.csv"))
    base_wk = list_windkessels(BASE)

    # -------------------------------------------------------
    # Load V22 MODEL data
    # -------------------------------------------------------
    print("[INFO] Reading cow_runV22 model...")
    v22_art_nodes, v22_vessels = read_arterial_nodes(os.path.join(V22, "arterial.csv"))
    v22_nodes_main, v22_lumped = read_main_nodes_and_lumped(os.path.join(V22, "main.csv"))
    v22_wk = list_windkessels(V22)
    # Add new out_*.csv WKs:
    for fname in os.listdir(V22):
        if fname.startswith("out_") and fname.endswith(".csv"):
            v22_wk.add(fname[:-4])

    # -------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------

    header("1. BASE MODEL: missing or inconsistent nodes")
    print("Nodes used in arterial.csv but NOT declared in main.csv:")
    missing_base = base_art_nodes - base_nodes_main
    for x in sorted(missing_base):
        print("  -", x)
    if not missing_base:
        print("  (none)")

    header("2. V22 MODEL: missing or inconsistent nodes")
    print("Nodes used in arterial.csv but NOT declared in main.csv:")
    missing_v22 = v22_art_nodes - v22_nodes_main
    for x in sorted(missing_v22):
        print("  -", x)
    if not missing_v22:
        print("  (none)")

    header("3. Nodes declared in main.csv but NOT used in arterial.csv")
    unused_v22 = v22_nodes_main - v22_art_nodes
    for x in sorted(unused_v22):
        print("  -", x)
    if not unused_v22:
        print("  (none)")

    header("4. Newly introduced nodes in V22 relative to base model")
    new_nodes = v22_nodes_main - base_nodes_main
    for x in sorted(new_nodes):
        print("  -", x)
    if not new_nodes:
        print("  (none)")

    header("5. Vessel IDs newly introduced in V22")
    new_vessels = v22_vessels - base_vessels
    for x in sorted(new_vessels):
        print("  -", x)
    if not new_vessels:
        print("  (none)")

    header("6. Windkessel models in V22")
    print("Existing WK terminals in V22:")
    for x in sorted(v22_wk):
        print("  -", x)

    missing_wk = v22_wk - v22_lumped.keys()
    print("\nWindkessel files that are NOT referenced in main.csv:")
    for x in sorted(missing_wk):
        print("  -", x)
    if not missing_wk:
        print("  (none)")

    missing_lumped = v22_lumped.keys() - v22_wk
    print("\nLumped WK entries in main.csv with NO csv file:")
    for x in sorted(missing_lumped):
        print("  -", x)
    if not missing_lumped:
        print("  (none)")


    header("7. SUMMARY FOR FIXING cow_runV22")
    print("Check sections 2 and 3 above:")
    print("  • Any missing nodes MUST be added to main.csv")
    print("  • Any node present in arterial.csv but missing in main.csv causes crash")
    print("  • All out_XXX Windkessels must appear as lumped lines in main.csv")
    print("  • All new junction nodes (cow_n1..n5) must be 'node,' lines in main.csv")
    print("  • After fixing, rerun V22_generate.py or manually repair main.csv")


if __name__ == "__main__":
    main()
