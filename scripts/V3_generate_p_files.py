#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Abel_ref2-style peripheral p-files (p1.csv ... pX.csv) from:
  models/cow_runV3/main.csv   (to discover p-models + inlet node names)
  models/cow_runV3/arterial.csv (to get geometry, so we can scale R, C, L)

Implements a 3-element Windkessel per *First Blood* (Rprox series, Rdist||C),
and adds a small inertance L for systemic branches to stabilize pulsatile flow.

Coronary branches are emitted with 'resistor_coronary' / 'capacitor_coronary'
and the simpler n1–n2 topology (matching your coronary p-file examples).

Output format exactly matches Abel_ref2 style:

data of edges
type, name, node start, node end, initial condition [SI], parameter [SI]
...
<blank line>
data of nodes
type, name, initial condition [SI]
...
"""

import os
import csv
import math
import pandas as pd

# -----------------------
# Configuration & paths
# -----------------------
MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "cow_runV3"))
ARTERIAL = os.path.join(MODEL_DIR, "arterial.csv")
MAIN = os.path.join(MODEL_DIR, "main.csv")

# Blood / wall constants (SI)
MU   = 0.0035     # viscosity [Pa·s]
RHO  = 1060.0     # density [kg/m^3]
E    = 4e6        # arterial wall modulus [Pa]
H_FRAC = 0.10     # wall thickness h = H_FRAC * r

# Windkessel split between proximal/distal resistances
RPROX_FRAC = 0.30  # 30% Rprox in series, 70% Rdist in shunt with C

# Minimums to avoid crazy numbers
MIN_R = 1e6       # [Pa·s/m^3]
MIN_C = 1e-12     # [m^3/Pa]
MIN_L = 1e5       # [Pa·s^2/m^3]
MIN_Radius = 2.5e-4  # [m] 0.25 mm
MIN_Length = 1e-3    # [m] 1 mm


def load_arterial_geometry(path: str):
    """
    Read arterial.csv and build per-node radius/length averages.
    Works with either Abel_ref2 or cow_runV3 header naming.
    """
    df = pd.read_csv(path)
    # Normalize column names to lowercase for convenience
    cols = {c.lower(): c for c in df.columns}
    # Resolve possible aliases
    start_col = cols.get("start_node") or cols.get("start") or list(df.columns)[0]
    end_col   = cols.get("end_node") or cols.get("end") or list(df.columns)[1]

    # diameter or radius columns (with or without [SI])
    def pick_col(keys):
        for k in keys:
            if k.lower() in cols:
                return cols[k.lower()]
        return None

    dstart_col = pick_col(["start_diameter[si]", "start_diameter", "d_start", "start_radius"])
    dend_col   = pick_col(["end_diameter[si]", "end_diameter", "d_end", "end_radius"])
    length_col = pick_col(["length[si]", "length", "L", "len"])

    if not (dstart_col and dend_col and length_col):
        raise ValueError(f"Could not find diameter/length columns in {path}\nColumns found: {list(df.columns)}")

    per_node = {}

    def add_node(n, d_m, L_m):
        r = max(d_m * 0.5, MIN_Radius)
        L = max(L_m, MIN_Length)
        s = per_node.setdefault(n, {"r_list": [], "L_list": []})
        s["r_list"].append(r)
        s["L_list"].append(L)

    for _, row in df.iterrows():
        start = row[start_col]
        end   = row[end_col]
        d_s   = float(row[dstart_col])
        d_e   = float(row[dend_col])
        L     = float(row[length_col])
        add_node(start, d_s, L)
        add_node(end, d_e, L)

    return per_node



def parse_lumped_from_main(path: str):
    """
    Read main.csv and collect unique p-models.
    Each lumped line:   lumped,pX,MAIN_NODE,MODEL_NODE
    We must use MODEL_NODE as the local inlet node *inside* pX.csv
    (Abel_ref2 uses 'n1' there; your model may use 'N107', etc.)
    """
    models = {}  # pid -> (main_node, model_node) (keep first occurrence)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            if line.startswith("lumped"):
                parts = [p.strip() for p in line.strip().split(",")]
                if len(parts) >= 4:
                    pid, main_node, model_node = parts[1], parts[2], parts[3]
                    if pid not in models:
                        models[pid] = (main_node, model_node)
    return models


def is_coronary(pid: str, inlet_model_node: str) -> bool:
    """
    Heuristic: treat model as coronary if id/name hints at it.
    (Your Abel_ref2 coronaries are explicitly marked as 'coronary' in file names or
     tied to heart models. For your cow_runV3, this likely remains False.
     Keeping a robust detector for future use.)
    """
    s = f"{pid}_{inlet_model_node}".lower()
    return ("cor" in s) or ("coronary" in s) or ("heart" in s)


def compute_R_total(r: float, L: float) -> float:
    # Poiseuille law
    R = (8.0 * MU * L) / (math.pi * r**4)
    return max(R, MIN_R)


def compute_C(r: float) -> float:
    # Linear elastic tube compliance approx: C ~ pi r^3 / (2 E h),  h ~ H_FRAC * r
    h = H_FRAC * r
    if h <= 0.0:
        return MIN_C
    C = (math.pi * r**3) / (2.0 * E * h)
    return max(C, MIN_C)


def compute_L_inertance(r: float, L: float) -> float:
    # Inertance: Δp = L dQ/dt  with  L = ρ L / A
    A = math.pi * r**2
    if A <= 0.0:
        return MIN_L
    Lin = (RHO * L) / A
    return max(Lin, MIN_L)


def write_systemic_p(path: str, inlet_node: str, Rprox: float, Rdist: float, C: float, Lin: float):
    """Abel_ref2-like systemic p-file with P1 node and small L to ground."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["data of edges"])
        w.writerow(["type", "name", "node start", "node end", "initial condition [SI]", "parameter [SI]"])
        w.writerow(["resistor", "R0", inlet_node, "P1", 0.0, f"{Rprox:.3e}"])
        w.writerow(["resistor", "R2", "P1", "g", 0.0, f"{Rdist:.3e}"])
        w.writerow(["capacitor", "C1", "P1", "g", 0.0, f"{C:.3e}"])
        w.writerow(["inductor", "L1", "P1", "g", 0.0, f"{Lin:.3e}"])
        w.writerow([])
        w.writerow(["data of nodes"])
        w.writerow(["type", "name", "initial condition [SI]"])
        w.writerow(["node", inlet_node, 1.000e+05])
        w.writerow(["node", "P1", 1.000e+05])
        w.writerow(["ground", "g", 1.000e+05])


def write_coronary_p(path: str, inlet_node: str, Rprox: float, Rdist: float, C: float):
    """Abel_ref2-like coronary p-file with n2 node (matches your coronary examples)."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["data of edges"])
        w.writerow(["type", "name", "node start", "node end", "initial condition [SI]", "parameter [SI]"])
        w.writerow(["resistor_coronary", "R1", inlet_node, "n2", 0.0, f"{Rprox:.3e}"])
        w.writerow(["resistor_coronary", "R2", "n2", "g", 0.0, f"{Rdist:.3e}"])
        w.writerow(["capacitor_coronary", "C", "n2", "g", 0.0, f"{C:.3e}"])
        # Note: most Abel coronary examples omit the inductor; keep that style.
        w.writerow([])
        w.writerow(["data of nodes"])
        w.writerow(["type", "name", "initial condition [SI]"])
        w.writerow(["node", inlet_node, 1.000e+05])
        w.writerow(["node", "n2", 1.000e+05])
        w.writerow(["ground", "g", 1.000e+05])


def main():
    print("[*] Generating Abel_ref2-style p-files from cow_runV3/main.csv + arterial.csv")
    if not os.path.isfile(ARTERIAL):
        raise FileNotFoundError(f"Missing arterial.csv at {ARTERIAL}")
    if not os.path.isfile(MAIN):
        raise FileNotFoundError(f"Missing main.csv at {MAIN}")

    per_node = load_arterial_geometry(ARTERIAL)
    models = parse_lumped_from_main(MAIN)
    print(f"[INFO] Discovered {len(models)} unique p-models in main.csv")

    made = 0
    for pid, (main_node, model_node) in models.items():
        # inlet node inside p-file MUST be the model_node from main.csv
        inlet = model_node

        # choose geometry near MAIN node to scale parameters
        if main_node in per_node and per_node[main_node]["r_list"]:
            r = max(sum(per_node[main_node]["r_list"]) / len(per_node[main_node]["r_list"]), MIN_Radius)
            L = max(sum(per_node[main_node]["L_list"]) / len(per_node[main_node]["L_list"]), MIN_Length)
        else:
            # conservative defaults
            r, L = 1.0e-3, 0.02

        Rtot = compute_R_total(r, L)
        Rprox = max(RPROX_FRAC * Rtot, MIN_R)
        Rdist = max((1.0 - RPROX_FRAC) * Rtot, MIN_R)
        C = compute_C(r)
        Lin = compute_L_inertance(r, L) * 0.25  # keep small for stability

        out_path = os.path.join(MODEL_DIR, f"{pid}.csv")
        if is_coronary(pid, inlet):
            write_coronary_p(out_path, inlet, Rprox, Rdist, C)
        else:
            write_systemic_p(out_path, inlet, Rprox, Rdist, C, Lin)

        made += 1
        print(f"  → wrote {os.path.basename(out_path)}  (inlet={inlet}, r={r:.3e} m, L={L:.3e} m)")

    print(f"[OK] Wrote {made} p-files to {MODEL_DIR}")
    print("Tip: grep -c '^lumped' main.csv should equal the number of unique p-files here.")


if __name__ == "__main__":
    main()