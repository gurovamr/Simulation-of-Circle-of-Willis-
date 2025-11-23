#!/usr/bin/env python3
"""
Quick analysis and plotting script for cow_runV8 results.

- Automatically finds Circle-of-Willis arteries in:
    ../projects/simple_run/results/cow_runV8/arterial/*.txt

- For each selected artery, it:
    * loads time series
    * computes pressure in mmHg
    * computes flow (uses solver units)
    * computes cross-sectional area and diameter from area
    * plots p(t), q(t), d(t)

- Also (if present) plots aortic pressure from the heart model:
    ../projects/simple_run/results/cow_runV8/heart_kim_lit/aorta.txt
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------
MMHG_TO_PA = 133.3616
BASELINE_P = 1.0e5  # reference pressure used in the solver [Pa]

# Relative to this script's folder
HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(HERE, "..", "projects", "simple_run", "results", "cow_runV8")
ARTERIAL_DIR = os.path.join(BASE_DIR, "arterial")
HEART_DIR = os.path.join(BASE_DIR, "heart_kim_lit")


# --------------------------------------------------------------------
# Loading helpers
# --------------------------------------------------------------------
def load_artery(file_path):
    """
    Load an arterial result file (BA_1.txt, ICA_4.txt, ...) and extract
    time, pressure, flow, area, diameter.

    Column layout (from your BA_1.txt sample):
        0: time [s]
        1: proximal pressure [Pa]
        2: distal pressure [Pa]
        3: proximal flow
        4: distal flow
        ...
        9: proximal area [m^2]
        10: distal area [m^2]
        11: something like c or characteristic variable
        12: same at distal end
    """
    df = pd.read_csv(file_path, header=None)

    t = df[0].to_numpy()

    p_prox = df[1].to_numpy()
    p_dist = df[2].to_numpy()
    q_prox = df[3].to_numpy()
    q_dist = df[4].to_numpy()

    # These indices were identified from BA_1.txt
    A_prox = df[9].to_numpy()
    A_dist = df[10].to_numpy()

    # Average proximal + distal values to get a single representative signal
    p = 0.5 * (p_prox + p_dist)      # [Pa]
    q = 0.5 * (q_prox + q_dist)      # solver units (likely m^3/s)
    A = 0.5 * (A_prox + A_dist)      # [m^2]

    # Compute diameter from area: A = pi * (d/2)^2  => d = 2 * sqrt(A/pi)
    # Guard against tiny negative rounding errors
    A_clipped = np.clip(A, 0.0, None)
    d = 2.0 * np.sqrt(A_clipped / np.pi)  # [m]

    # Pressure in mmHg (subtract baseline)
    p_mmHg = (p - BASELINE_P) / MMHG_TO_PA

    return t, p_mmHg, q, A, d


def load_heart_aorta(heart_dir=HEART_DIR):
    """
    Load aortic pressure from the heart model, if present.
    Expects: heart_dir/aorta.txt with columns: t, p.
    """
    path = os.path.join(heart_dir, "aorta.txt")
    if not os.path.exists(path):
        return None, None

    df = pd.read_csv(path, header=None)
    t = df[0].to_numpy()
    p = df[1].to_numpy()
    p_mmHg = (p - BASELINE_P) / MMHG_TO_PA

    return t, p_mmHg


# --------------------------------------------------------------------
# Vessel selection
# --------------------------------------------------------------------
def find_cow_vessels(arterial_dir=ARTERIAL_DIR, max_vessels=8):
    """
    Scan all arterial/*.txt and select those that look like CoW vessels
    based on their names (BA, ICA, MCA, ACA, PCA, Pcom, Acom, A1, A2, P1, P2).

    Returns a list of base names WITHOUT extension, e.g. ['BA_1', 'ICA_4', ...]
    """
    # patterns that typically appear in CoW vessel names
    SUBSTRINGS = [
        "BA",      # basilar artery
        "ICA",     # internal carotid
        "MCA",     # middle cerebral
        "ACA",     # anterior cerebral
        "PCA",     # posterior cerebral
        "Pcom",    # posterior communicating
        "Acom",    # anterior communicating
        "A1_", "A2_", "P1_", "P2_"  # segment labels
    ]

    pattern = os.path.join(arterial_dir, "*.txt")
    all_files = sorted(glob.glob(pattern))

    selected = []
    for f in all_files:
        name = os.path.splitext(os.path.basename(f))[0]  # e.g. 'BA_1'
        if any(sub in name for sub in SUBSTRINGS):
            selected.append(name)

    # Remove duplicates, sort, and limit the number
    vessels = sorted(set(selected))
    if len(vessels) > max_vessels:
        vessels = vessels[:max_vessels]

    return vessels


# --------------------------------------------------------------------
# Plotting
# --------------------------------------------------------------------
def plot_arteries(vessels):
    """
    For each vessel name in 'vessels', load its data and create a figure:

    For each vessel (row):
        left:  pressure [mmHg]
        middle: flow [solver units]
        right: diameter [mm]
    """
    if not vessels:
        print("No vessels selected to plot.")
        return

    n = len(vessels)
    fig, axes = plt.subplots(
        nrows=n, ncols=3, sharex=True, figsize=(12, 2.5 * n), constrained_layout=True
    )

    # If only one vessel, axes is 1D
    if n == 1:
        axes = np.array([axes])

    for i, v in enumerate(vessels):
        file_path = os.path.join(ARTERIAL_DIR, f"{v}.txt")
        if not os.path.exists(file_path):
            print(f"[WARN] File not found for vessel {v}: {file_path}")
            continue

        t, p_mmHg, q, A, d = load_artery(file_path)

        ax_p, ax_q, ax_d = axes[i]

        ax_p.plot(t, p_mmHg)
        ax_p.set_ylabel(f"{v}\nP [mmHg]")
        ax_p.grid(True, alpha=0.3)

        ax_q.plot(t, q)
        ax_q.set_ylabel("q [solver units]")
        ax_q.grid(True, alpha=0.3)

        ax_d.plot(t, d * 1e3)  # convert m -> mm
        ax_d.set_ylabel("D [mm]")
        ax_d.grid(True, alpha=0.3)

    axes[-1, 0].set_xlabel("t [s]")
    axes[-1, 1].set_xlabel("t [s]")
    axes[-1, 2].set_xlabel("t [s]")

    fig.suptitle("Circle of Willis – arterial signals (cow_runV8)", fontsize=14)
    plt.show()


def plot_heart():
    """
    Plot aortic pressure from the heart model, if available.
    """
    t, p_mmHg = load_heart_aorta()
    if t is None:
        print("No heart aorta.txt found – skipping heart plot.")
        return

    plt.figure(figsize=(8, 4))
    plt.plot(t, p_mmHg)
    plt.xlabel("t [s]")
    plt.ylabel("Aortic pressure [mmHg]")
    plt.title("Heart model – aortic pressure (cow_runV8)")
    plt.grid(True, alpha=0.3)
    plt.show()


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------
def main():
    print("Base results dir:", BASE_DIR)
    if not os.path.isdir(ARTERIAL_DIR):
        print(f"[ERROR] Arterial results dir not found: {ARTERIAL_DIR}")
        return

    vessels = find_cow_vessels()
    print("Selected CoW vessels to plot:", vessels)

    plot_arteries(vessels)
    plot_heart()


if __name__ == "__main__":
    main()
