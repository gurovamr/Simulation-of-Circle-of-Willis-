#!/usr/bin/env python3
"""
Diagnose ONLY the Abel_ref2 model to understand:
- which vessels belong to the Circle of Willis
- which nodes they use
- how ICA and BA connect
- which outlets use Windkessels
- how solver expects the intracranial block to look

This will let us rebuild V22 in the same structure
with patient-specific CoW geometry.
"""

import csv
import os

BASE = "../models/Abel_ref2"


def load_arteries():
    arteries = []
    with open(os.path.join(BASE, "arterial.csv")) as f:
        r = csv.reader(f)
        for row in r:
            if len(row) < 5:
                continue
            if row[0] == "vis_f":
                arteries.append({
                    "id": row[1],
                    "name": row[2],
                    "start": row[3],
                    "end": row[4]
                })
    return arteries


def load_main():
    nodes = set()
    lumped = []
    with open(os.path.join(BASE, "main.csv")) as f:
        r = csv.reader(f)
        for row in r:
            if not row:
                continue
            if row[0] == "node":
                nodes.add(row[1])
            elif row[0] == "lumped":
                lumped.append(row)
    return nodes, lumped


def is_cow_name(name):
    """
    Identify which vessels belong to CoW or brain circulation.
    """
    name = name.lower()
    keywords = [
        "basilar",
        "cerebral",     # catches "middle cerebral", "posterior cerebral"
        "communicating",
        "carotid",      # intracranial ICA segments
        "p1", "p2",     # PCA
        "a1", "a2",     # ACA
        "m1", "mca",
        "acom", "pcom"
    ]
    return any(k in name for k in keywords)


def main():
    print("\n========== ANALYZING Abel_ref2 MODEL (COW REGION) ==========\n")

    arteries = load_arteries()
    nodes_main, lumped = load_main()

    # Extract CoW arterial segments
    cow_vessels = [a for a in arteries if is_cow_name(a["name"])]

    print("### Circle of Willis Vessels (Detected by Name) ###")
    for a in cow_vessels:
        print(f"{a['id']:>8} : {a['name']:<35}  {a['start']} -> {a['end']}")
    print("Total CoW vessels:", len(cow_vessels))

    # Collect all nodes used by CoW block
    cow_nodes = set()
    for a in cow_vessels:
        cow_nodes.add(a["start"])
        cow_nodes.add(a["end"])

    print("\n### Nodes used by CoW vessels ###")
    for n in sorted(cow_nodes):
        print("  ", n)

    # ICA inlets
    ica_nodes = {a["start"] for a in cow_vessels if "carotid" in a["name"].lower()} | \
                {a["end"] for a in cow_vessels if "carotid" in a["name"].lower()}

    # Basilar inlets
    bas_nodes = {a["start"] for a in cow_vessels if "basilar" in a["name"].lower()} | \
                {a["end"] for a in cow_vessels if "basilar" in a["name"].lower()}

    print("\n### ICA-related nodes ###")
    for n in sorted(ica_nodes):
        print("  ", n)

    print("\n### Basilar-related nodes ###")
    for n in sorted(bas_nodes):
        print("  ", n)

    # Windkessel terminals attached to CoW
    wk_nodes = {r[3] for r in lumped}  # modelnode column

    cow_terminals = cow_nodes & wk_nodes
    print("\n### Brain Windkessel terminals ###")
    if cow_terminals:
        for n in sorted(cow_terminals):
            print("  ", n)
    else:
        print("  (none detected by direct WK match)")

    print("\n### Node presence in main.csv ###")
    missing = [n for n in cow_nodes if n not in nodes_main]
    if missing:
        print("Nodes used in CoW but NOT in main.csv node list:")
        for n in missing:
            print("  ", n)
    else:
        print("All CoW nodes appear in main.csv (expected).")

    print("\n============================================================")
    print("Send me this output and I will generate the correct V23 script.")
    print("============================================================\n")


if __name__ == "__main__":
    main()
