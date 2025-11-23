#!/usr/bin/env python3
import os
import json
import shutil
import math

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

INPUT_DIR = os.path.join(ROOT, "data_patient025")
FEATURE_FILE = os.path.join(INPUT_DIR, "feature_mr_025.json")
NODES_FILE   = os.path.join(INPUT_DIR, "nodes_mr_025.json")
VARIANT_FILE = os.path.join(INPUT_DIR, "variant_mr_025.json")

MODEL_SRC = os.path.join(ROOT, "models", "cow_runV8")
MODEL_DST = os.path.join(ROOT, "models", "cow_runV8_synthetic_inflow")

# synthetic waveform parameters
T_PERIOD = 1.0       # [s] duration of 1 cardiac cycle
N_CYCLES = 3         # number of cycles to generate
DT       = 1e-3      # [s] time step
Q_PEAK_BA   = 250.0  # [ml/s] peak flow at BA
Q_PEAK_ICA1 = 200.0  # [ml/s] peak flow at ICA1
Q_PEAK_ICA2 = 200.0  # [ml/s] peak flow at ICA2

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def ensure_clone(src, dst):
    if not os.path.isdir(src):
        raise RuntimeError(f"Source model folder not found: {src}")
    if os.path.isdir(dst):
        print(f"[INFO] Removing existing folder: {dst}")
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"[OK] Cloned {src} -> {dst}")

def find_inlet_nodes_from_features(feature):
    """
    Very simple logic, based on what we already observed:
      BA  segment start = 15  -> node 'N15'
      ICA1 root id        332 -> 'N332'
      ICA2 root id        493 -> 'N493'
    """
    # BA from "1" / "BA" block
    ba_start = feature["1"]["BA"][0]["segment"]["start"]   # 15
    ba_node_name = f"N{ba_start}"

    # ICA candidates: we use hard-coded IDs we know from your network
    ica1_id = 332
    ica2_id = 493
    ica1_node_name = f"N{ica1_id}"
    ica2_node_name = f"N{ica2_id}"

    print("[INFO] Detected inlet candidates from raw features:")
    print(f"       BA   inlet node: {ba_node_name} (id {ba_start})")
    print(f"       ICA1 inlet node: {ica1_node_name} (id {ica1_id})")
    print(f"       ICA2 inlet node: {ica2_node_name} (id {ica2_id})")

    return ba_node_name, ica1_node_name, ica2_node_name

def synthetic_pulse(t, q_peak):
    """
    Simple physiological-looking inflow:
    - Systolic upstroke:   0–0.15 s   (fast rise)
    - Systolic plateau:    0.15–0.35 s
    - Diastolic decay:     0.35–0.8  s
    - Rest:                0.8–1.0  s
    """
    t_in_cycle = t % T_PERIOD
    if 0.0 <= t_in_cycle < 0.15:
        # steep upstroke (half sine)
        x = t_in_cycle / 0.15
        return q_peak * math.sin(0.5 * math.pi * x)
    elif 0.15 <= t_in_cycle < 0.35:
        # plateau
        return 0.9 * q_peak
    elif 0.35 <= t_in_cycle < 0.8:
        # exponential-like diastolic decay
        x = (t_in_cycle - 0.35) / (0.8 - 0.35)
        return 0.9 * q_peak * math.exp(-3.0 * x)
    else:
        # near zero diastolic tail
        return 0.05 * q_peak

def write_inflow_file(path, q_peak):
    t_max = N_CYCLES * T_PERIOD
    n_steps = int(t_max / DT) + 1
    with open(path, "w") as f:
        for k in range(n_steps):
            t = k * DT
            q = synthetic_pulse(t, q_peak)    # [ml/s]
            # file format: time[s], Q[ml/s]
            f.write(f"{t:.7e}, {q:.7e}\n")
    print(f"[OK] Wrote synthetic inflow waveform: {path}")

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

def main():
    # 1) clone model
    ensure_clone(MODEL_SRC, MODEL_DST)

    # 2) load raw data (we only really need feature, the others are for completeness)
    feature = load_json(FEATURE_FILE)
    nodes   = load_json(NODES_FILE)
    variant = load_json(VARIANT_FILE)
    _ = nodes, variant  # not used yet, but may be useful later

    # 3) detect inlet nodes
    ba_node, ica1_node, ica2_node = find_inlet_nodes_from_features(feature)

    # 4) generate synthetic inflow waveforms
    inflow_BA   = os.path.join(MODEL_DST, "inflow_BA.txt")
    inflow_ICA1 = os.path.join(MODEL_DST, "inflow_ICA1.txt")
    inflow_ICA2 = os.path.join(MODEL_DST, "inflow_ICA2.txt")

    write_inflow_file(inflow_BA,   Q_PEAK_BA)
    write_inflow_file(inflow_ICA1, Q_PEAK_ICA1)
    write_inflow_file(inflow_ICA2, Q_PEAK_ICA2)

    # 5) summary
    print("\n[SUMMARY]")
    print(f"  Model folder   : {MODEL_DST}")
    print(f"  BA inlet node  : {ba_node},  waveform file {os.path.basename(inflow_BA)}")
    print(f"  ICA1 inlet node: {ica1_node}, waveform file {os.path.basename(inflow_ICA1)}")
    print(f"  ICA2 inlet node: {ica2_node}, waveform file {os.path.basename(inflow_ICA2)}")
    print("\nNOTE: These waveforms are NOT yet plugged into simple_run.out.")
    print("      Next step (separate): wire them as upstream BCs in the C++/CSV setup.")

if __name__ == "__main__":
    main()
