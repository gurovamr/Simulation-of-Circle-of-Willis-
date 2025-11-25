#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
import csv
import os

# ============================================================
# Paths (adapt if needed)
# ============================================================
MODEL_NAME = "cow_runV11"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT, "models", MODEL_NAME)
RESULT_DIR = os.path.join(ROOT, "projects", "simple_run", "results", MODEL_NAME, "arterial")

MAIN_CSV = os.path.join(MODEL_DIR, "main.csv")

# Key vessel files we want to inspect (if they exist)
KEY_VESSELS = [
    "ICA_4.txt",
    "MCA_5.txt",
    "PCA_2.txt",
    "BA_1.txt",
]

N_CYCLES_TO_COMPARE = 3


# ============================================================
# Helpers
# ============================================================
def find_heart_inlet_from_main(main_csv_path):
    """
    Parse main.csv, find the lumped heart line:
      lumped,heart_kim_lit,<main node>,aorta
    Return that <main node> (e.g. 'N332').
    """
    with open(main_csv_path) as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4 and row[0] == "lumped" and row[1] == "heart_kim_lit":
                return row[2]  # main node
    raise RuntimeError("Could not find 'lumped,heart_kim_lit' line in main.csv")


def load_time_pressure(filename, t_col=0, p_col=1):
    data = np.loadtxt(filename, delimiter=",")
    t = data[:, t_col]
    p = data[:, p_col]
    return t, p


def find_peaks(t, p):
    peaks = []
    for i in range(1, len(p) - 1):
        if p[i] > p[i-1] and p[i] > p[i+1]:
            peaks.append(i)
    return np.array(peaks, dtype=int)


def extract_cycles(t, p, peaks, n_cycles):
    if len(peaks) < n_cycles + 1:
        raise RuntimeError(f"Not enough peaks ({len(peaks)}) to extract {n_cycles} cycles.")
    peaks_used = peaks[-(n_cycles + 1):]
    cycles = []
    for i in range(n_cycles):
        i_start = peaks_used[i]
        i_end   = peaks_used[i+1]
        t_seg = t[i_start:i_end+1] - t[i_start]
        p_seg = p[i_start:i_end+1]
        cycles.append((t_seg, p_seg))
    return cycles


def resample_to_phase(t_seg, p_seg, n_points=200):
    T = t_seg[-1]
    phase_old = t_seg / T
    phase = np.linspace(0.0, 1.0, n_points)
    p_interp = np.interp(phase, phase_old, p_seg)
    return phase, p_interp


def analyse_one_signal(name, filepath):
    print(f"\n=== {name} ===")
    if not os.path.exists(filepath):
        print(f"  [WARN] File not found: {filepath}")
        return

    t, p = load_time_pressure(filepath, 0, 1)
    print(f"  Loaded {len(t)} samples from {filepath}")
    print(f"  Pressure range: {p.min():.1f} .. {p.max():.1f} Pa")

    peaks = find_peaks(t, p)
    print(f"  Found {len(peaks)} peaks")

    if len(peaks) < N_CYCLES_TO_COMPARE + 1:
        print("  [WARN] Not enough peaks for periodicity analysis.")
        return

    cycles = extract_cycles(t, p, peaks, N_CYCLES_TO_COMPARE)

    phase_grid = None
    resampled = []
    for (ts, ps) in cycles:
        phase, p_interp = resample_to_phase(ts, ps)
        phase_grid = phase
        resampled.append(p_interp)
    resampled = np.array(resampled)
    mean_wave = np.mean(resampled, axis=0)

    diffs = resampled - mean_wave
    rms_global = np.sqrt(np.mean(diffs**2))
    print(f"  Global RMS difference (Pa) = {rms_global:.3f}")

    # relative RMS wrt pulse pressure
    psys = mean_wave.max()
    pdia = mean_wave.min()
    pulse = psys - pdia
    if pulse > 0:
        rel_rms = rms_global / pulse * 100.0
        print(f"  Pulse pressure (Pa)       = {pulse:.1f}")
        print(f"  relRMS vs pulse pressure = {rel_rms:.3f} %")
    else:
        print("  [WARN] Pulse pressure <= 0, cannot compute relative RMS.")

    # plot
    plt.figure()
    for i, cyc in enumerate(resampled, start=1):
        plt.plot(phase_grid, cyc, label=f"Cycle {i}")
    plt.plot(phase_grid, mean_wave, "--k", lw=2, label="Mean")

    plt.title(f"{name} – Phase-normalized last {N_CYCLES_TO_COMPARE} cycles")
    plt.xlabel("Cardiac phase [-]")
    plt.ylabel("Pressure [Pa]")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()


def main():
    # 1) find heart inlet node from main.csv
    heart_inlet_node = find_heart_inlet_from_main(MAIN_CSV)
    print(f"[INFO] Heart inlet node from main.csv = {heart_inlet_node}")

    inlet_file = os.path.join(RESULT_DIR, f"{heart_inlet_node}.txt")
    analyse_one_signal(f"Inlet ({heart_inlet_node})", inlet_file)

    # 2) analyse key CoW arteries if present
    for fname in KEY_VESSELS:
        path = os.path.join(RESULT_DIR, fname)
        analyse_one_signal(fname.replace(".txt", ""), path)

    plt.show()


if __name__ == "__main__":
    main()
