import os
import pandas as pd
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import numpy as np
from io import StringIO

# ==========================================
# 1. CONFIGURATION
# ==========================================
RESULTS_DIR = os.path.abspath(os.path.join("..", "projects", "simple_run", "results", "cow_runV21", "arterial"))

# Standard Atmospheric Pressure in Pa (used by First Blood)
P_ATM = 1.0e5 

INTEREST_VESSELS = {
    "P_BA": "Basilar Artery",
    "P_RMCA": "Right MCA",
    "P_LMCA": "Left MCA",
    "P_RP1": "Right P1",
    "P_LP1": "Left P1"
}

OUTPUT_PLOT_DIR = "plots21"
if not os.path.exists(OUTPUT_PLOT_DIR):
    os.makedirs(OUTPUT_PLOT_DIR)

# ==========================================
# 2. DATA LOADING
# ==========================================
def load_simulation_data(vessel_id):
    for ext in ['.dat', '.csv', '.txt']:
        path = os.path.join(RESULTS_DIR, vessel_id + ext)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    content = f.read()
                clean_content = content.replace(',', ' ')
                df = pd.read_csv(StringIO(clean_content), sep=r'\s+', header=None, engine='python')
                return df
            except Exception as e:
                print(f"Error reading {path}: {e}")
                return None
    return None

# ==========================================
# 3. ANALYSIS & PLOTTING
# ==========================================
def analyze_vessels():
    summary_data = []
    plt.figure(figsize=(15, 10))
    
    for i, (v_id, v_name) in enumerate(INTEREST_VESSELS.items()):
        df = load_simulation_data(v_id)
        if df is None or df.empty: continue

        try:
            df = df.apply(pd.to_numeric, errors='coerce').dropna()
            time = df.iloc[:, 0]
            
            # Column Mapping (Heuristic)
            means = df.abs().mean()
            p_idx, q_idx = -1, -1
            
            for c in range(1, len(df.columns)):
                val = means.iloc[c]
                # Look for Absolute Pressure (~100,000 Pa)
                if val > 80000 and p_idx == -1: p_idx = c
                # Look for Flow (< 0.001 m3/s)
                elif 0 < val < 0.001 and q_idx == -1: q_idx = c
            
            if p_idx == -1: p_idx = 1
            if q_idx == -1: q_idx = df.shape[1]-2 if df.shape[1] > 2 else 2

            # --- CONVERSION & GAUGE CORRECTION ---
            # 1. Convert Raw Pa to Gauge Pa (Subtract Atmosphere)
            p_absolute_pa = df.iloc[:, p_idx]
            p_gauge_pa = p_absolute_pa - P_ATM
            
            # 2. Convert Gauge Pa to mmHg
            pressure = p_gauge_pa / 133.322 
            
            # 3. Flow m3/s to mL/s
            flow = df.iloc[:, q_idx] * 1e6 

        except Exception as e:
             print(f"Error processing {v_name}: {e}")
             continue

        # Use last cycle
        t_max = time.max()
        last_cycle_mask = time > (t_max - 1.0) if t_max > 1.0 else [True] * len(time)

        p_cycle = pressure[last_cycle_mask]
        t_cycle = time[last_cycle_mask]
        
        if p_cycle.empty: continue

        summary_data.append({
            "Vessel": v_name,
            "Systolic P (mmHg)": round(p_cycle.max(), 2),
            "Diastolic P (mmHg)": round(p_cycle.min(), 2),
            "Mean Flow (mL/s)": round(flow[last_cycle_mask].mean(), 2)
        })

        plt.subplot(2, 3, i+1)
        plt.plot(t_cycle, p_cycle, label=f"{v_name}")
        plt.title(f"{v_name}")
        plt.ylabel("Gauge Pressure (mmHg)")
        plt.xlabel("Time (s)")
        plt.grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_PLOT_DIR, "pressure_waveforms_gauge.png"))
    print(f"Plots saved to {OUTPUT_PLOT_DIR}")

    if summary_data:
        print("\nSimulation Metrics (Gauge Pressure):")
        print(pd.DataFrame(summary_data))

if __name__ == "__main__":
    analyze_vessels()