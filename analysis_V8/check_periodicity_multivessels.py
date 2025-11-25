#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt

# ================================
# USER SETTINGS
# ================================

FILES = {
    "ICA_4": "../projects/simple_run/results/cow_runV10/arterial/ICA_4.txt",
    "MCA_5": "../projects/simple_run/results/cow_runV10/arterial/MCA_5.txt",
    "PCA_2": "../projects/simple_run/results/cow_runV10/arterial/PCA_2.txt",
}

HAS_HEADER = False
TIME_COL = 0
PRESSURE_COL = 1     # All your arterial files use column 1 as pressure

N_CYCLES_TO_COMPARE = 3



# ================================
# FUNCTIONS
# ================================

def load_time_pressure(filename, has_header, t_col, p_col):
    data = np.loadtxt(filename, delimiter=",")
    t = data[:, t_col]
    p = data[:, p_col]
    return t, p

def find_peaks(t, p):
    peaks = []
    for i in range(1, len(p)-1):
        if p[i] > p[i-1] and p[i] > p[i+1]:
            peaks.append(i)
    return np.array(peaks)

def extract_cycles(t, p, peaks, n):
    if len(peaks) < n+1:
        raise RuntimeError("Not enough peaks to extract cycles.")

    peaks = peaks[-(n+1):]  # last cycles

    cycles = []
    for i in range(n):
        start = peaks[i]
        end = peaks[i+1]
        ts = t[start:end+1] - t[start]
        ps = p[start:end+1]
        cycles.append((ts, ps))
    return cycles

def resample_to_phase(tseg, pseg, npoints=200):
    T = tseg[-1]
    phase_old = tseg / T
    phase = np.linspace(0, 1, npoints)
    pnew = np.interp(phase, phase_old, pseg)
    return phase, pnew




# ================================
# MAIN SCRIPT
# ================================

def process_vessel(name, filepath):
    print(f"\n=== Processing {name} ===")

    t, p = load_time_pressure(filepath, HAS_HEADER, TIME_COL, PRESSURE_COL)
    print(f"Loaded {len(t)} samples from {filepath}")

    peaks = find_peaks(t, p)
    print(f"Found {len(peaks)} peaks")

    cycles = extract_cycles(t, p, peaks, N_CYCLES_TO_COMPARE)

    phase_grid = None
    resampled = []

    for ts, ps in cycles:
        ph, p_interp = resample_to_phase(ts, ps)
        phase_grid = ph
        resampled.append(p_interp)

    resampled = np.array(resampled)
    mean_wave = np.mean(resampled, axis=0)

    diffs = resampled - mean_wave
    rms_global = np.sqrt(np.mean(diffs**2))

    print(f"Global RMS difference = {rms_global:.3f} Pa")

    # plot
    plt.figure()
    for i, cyc in enumerate(resampled, 1):
        plt.plot(phase_grid, cyc, label=f"Cycle {i}")
    plt.plot(phase_grid, mean_wave, "--k", lw=2, label="Mean")

    plt.title(f"{name} – Phase-normalized last {N_CYCLES_TO_COMPARE} cycles")
    plt.xlabel("Cardiac Phase")
    plt.ylabel("Pressure (Pa)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    for name, path in FILES.items():
        process_vessel(name, path)
