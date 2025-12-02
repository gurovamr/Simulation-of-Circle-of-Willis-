import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from io import StringIO

# ==========================================
# CONFIGURATION
# ==========================================
RESULTS_DIR = os.path.abspath(os.path.join("..", "projects", "simple_run", "results", "cow_runV21", "arterial"))
OUTPUT_PLOT_DIR = "plots_debug"
if not os.path.exists(OUTPUT_PLOT_DIR): os.makedirs(OUTPUT_PLOT_DIR)

# DIAGNOSTIC NODES/VESSELS
# We want to check the "Static Body" vessels that feed the brain
DIAGNOSTICS = {
    "A59": "Body_Basilar_Inlet",  # Feeds P_BA
    "A101": "Body_R_ICA_Inlet",   # Feeds P_RMCA/P_RA1
    "A103": "Body_L_ICA_Inlet",   # Feeds P_LMCA/P_LA1
    "P_BA": "Patient_Basilar",
    "P_RMCA": "Patient_R_MCA"
}

def load_data(v_id):
    path = os.path.join(RESULTS_DIR, f"{v_id}.txt") # Assuming .txt based on previous ls
    if not os.path.exists(path): return None
    try:
        with open(path, 'r') as f: content = f.read().replace(',', ' ')
        df = pd.read_csv(StringIO(content), sep=r'\s+', header=None, engine='python')
        return df.apply(pd.to_numeric, errors='coerce').dropna()
    except: return None

def run_diagnostics():
    plt.figure(figsize=(15, 10))
    
    for i, (vid, name) in enumerate(DIAGNOSTICS.items()):
        df = load_data(vid)
        if df is None:
            print(f"MISSING: {vid} ({name})")
            continue
            
        # Heuristic Column Mapping
        means = df.abs().mean()
        p_idx, q_idx = -1, -1
        for c in range(1, len(df.columns)):
            if means[c] > 50000 and p_idx == -1: p_idx = c
            elif 0 < means[c] < 0.001 and q_idx == -1: q_idx = c
            
        if p_idx == -1: p_idx = 1
        if q_idx == -1: q_idx = df.shape[1]-2

        # Convert
        time = df.iloc[:, 0]
        # Gauge Pressure (mmHg)
        press = (df.iloc[:, p_idx] - 1.0e5) / 133.32 
        
        # Plotting Last Cycle
        t_max = time.max()
        mask = time > (t_max - 1.0)
        
        plt.subplot(2, 3, i+1)
        plt.plot(time[mask], press[mask], label=name)
        plt.title(f"{name}\nMean P: {press[mask].mean():.1f} mmHg")
        plt.grid(True)
        plt.ylabel("Gauge P (mmHg)")

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_PLOT_DIR, "diagnostic_pressure.png"))
    print(f"Diagnostic plots saved to {OUTPUT_PLOT_DIR}")

if __name__ == "__main__":
    run_diagnostics()