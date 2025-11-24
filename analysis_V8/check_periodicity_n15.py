#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt

# === SETTINGS =====================================================
FILENAME = "../projects/simple_run/results/cow_runV10/arterial/N15.txt"
HAS_HEADER = False
TIME_COL = 0
PRESSURE_COL = 1
N_CYCLES_TO_COMPARE = 3
# ==================================================================

def load_time_pressure(fname, has_header, tcol, pcol):
    data = np.loadtxt(fname, delimiter=",")
    t = data[:, tcol]
    p = data[:, pcol]
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

def main():
    t, p = load_time_pressure(FILENAME, HAS_HEADER, TIME_COL, PRESSURE_COL)
    print(f"Loaded {len(t)} samples")

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

    # RMS difference
    diffs = resampled - mean_wave
    rms_global = np.sqrt(np.mean(diffs**2))

    print(f"Global RMS difference = {rms_global:.3f} Pa")

    # Plot
    plt.figure()
    for i, cyc in enumerate(resampled, 1):
        plt.plot(phase_grid, cyc, label=f"Cycle {i}")
    plt.plot(phase_grid, mean_wave, "--k", lw=2, label="Mean")
    plt.xlabel("Phase")
    plt.ylabel("Pressure (Pa)")
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()
