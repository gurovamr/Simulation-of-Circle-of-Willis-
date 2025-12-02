import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

def load_ts(path):
    """Robust loader for first_blood txt files (handles commas, etc.)."""
    with open(path, "r") as f:
        raw = f.readlines()

    data = []
    for line in raw:
        line = line.replace(",", " ").replace(";", " ").strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            t = float(parts[0])
            v = float(parts[1])
            data.append([t, v])
        except ValueError:
            continue

    if not data:
        raise ValueError(f"No numeric rows in {path}")
    arr = np.array(data)
    return arr[:, 0], arr[:, 1]


def analyze_run(
    run_name,
    p_file="aorta.txt",
    q_file="R_lv_aorta.txt",
    use_ground_baseline=True,
):
    """
    Level-1 sanity analysis for a given simulation run.
    Works for Abel_ref2, cow_runV23, etc.

    - run_name: folder name under ../projects/simple_run/results/
    - p_file:   pressure probe file inside heart_kim_lit
    - q_file:   flow probe file (e.g. resistor to aorta) inside heart_kim_lit
    - use_ground_baseline: if True, subtract g.txt as atmospheric baseline
    """

    base_dir = f"../projects/simple_run/results/{run_name}"
    heart_dir = os.path.join(base_dir, "heart_kim_lit")

    # list available signals
    print(f"=== Heart files for run: {run_name} ===")
    for fname in sorted(os.listdir(heart_dir)):
        print(" ", fname)

    P_PATH = os.path.join(heart_dir, p_file)
    Q_PATH = os.path.join(heart_dir, q_file)
    G_PATH = os.path.join(heart_dir, "g.txt")

    t_p, p_raw = load_ts(P_PATH)
    t_q, q_raw = load_ts(Q_PATH)

    # gauge pressure: subtract ground if available, otherwise 1e5 Pa
    if use_ground_baseline and os.path.exists(G_PATH):
        _, g_raw = load_ts(G_PATH)
        p_gauge = p_raw - g_raw
    else:
        p_gauge = p_raw - 1.0e5  # fallback

    # unit conversion
    p_mmHg = p_gauge / 133.322  # Pa -> mmHg
    q_Lmin = q_raw * 60.0 * 1000.0  # m^3/s -> L/min

    # metrics
    P_sys = np.max(p_mmHg)
    P_dia = np.min(p_mmHg)
    P_mean = np.mean(p_mmHg)
    PP = P_sys - P_dia

    peaks, _ = find_peaks(p_mmHg, distance=40)
    if len(peaks) > 1:
        dt = np.diff(t_p[peaks]).mean()
        HR = 60.0 / dt
    else:
        HR = np.nan

    CO = np.mean(q_Lmin)

    print("\n======= LEVEL-1 SANITY CHECK =======")
    print(f"Run: {run_name}")
    print(f"Probe P: {p_file}, Q: {q_file}\n")
    print(f"Systolic (mmHg):   {P_sys:.2f}")
    print(f"Diastolic (mmHg):  {P_dia:.2f}")
    print(f"Mean (mmHg):       {P_mean:.2f}")
    print(f"Pulse (mmHg):      {PP:.2f}")
    print(f"Heart Rate (bpm):  {HR:.2f}")
    print(f"Cardiac Output (L/min): {CO:.2f}")

    print("\n--- Physiological Ranges ---")
    print("Systolic:       110–130 mmHg")
    print("Diastolic:      70–90 mmHg")
    print("MAP:            85–100 mmHg")
    print("Pulse Pressure: 35–55 mmHg")
    print("CO:             4.5–5.5 L/min")
    print("HR:             55–90 bpm")

    # plots
    plt.figure(figsize=(12, 4))
    plt.plot(t_p, p_mmHg)
    plt.title(f"{run_name}: Aortic pressure (mmHg)")
    plt.xlabel("Time (s)")
    plt.ylabel("mmHg")
    plt.grid(True)
    plt.show()

    plt.figure(figsize=(12, 4))
    plt.plot(t_q, q_Lmin)
    plt.title(f"{run_name}: Aortic flow (L/min)")
    plt.xlabel("Time (s)")
    plt.ylabel("L/min")
    plt.grid(True)
    plt.show()


analyze_run("Abel_ref2")
#analyze_run("cow_runV23")
