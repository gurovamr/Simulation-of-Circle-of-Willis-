import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
# Path to the simulation output files. 
# Adjust this to where First Blood saved the .dat/.csv files for cow_runV20
# Usually: ../projects/simple_run/results/cow_runV20/arterial
RESULTS_DIR = os.path.abspath(os.path.join("..", "projects", "simple_run", "results", "cow_runV20", "arterial"))

# The specific vessels we want to analyze (IDs from arterial.csv)
# "P_BA" = Patient Basilar, "P_RMCA" = Right MCA, etc.
INTEREST_VESSELS = {
    "P_BA": "Basilar Artery",
    "P_RMCA": "Right MCA",
    "P_LMCA": "Left MCA",
    "P_RP1": "Right P1",
    "P_LP1": "Left P1"
}

# Output folder for plots
OUTPUT_PLOT_DIR = "plots"
if not os.path.exists(OUTPUT_PLOT_DIR):
    os.makedirs(OUTPUT_PLOT_DIR)

# ==========================================
# 2. DATA LOADING
# ==========================================
def load_simulation_data(vessel_id):
    """
    First Blood typically outputs files like 'P_BA.dat' or 'P_BA.csv'.
    The format is usually: Time, x_coordinate, Area, Pressure, Velocity, Flow
    We need to find the file and parse it.
    """
    # Try different extensions
    for ext in ['.dat', '.csv', '.txt']:
        path = os.path.join(RESULTS_DIR, vessel_id + ext)
        if os.path.exists(path):
            # Parsing logic depends on exact First Blood output format.
            # Assumption: Space or comma separated, usually last cycle or full time history.
            # If it's the standard 1D output, it might be a 3D matrix (Time x Space).
            # We usually want the waveform at the MIDDLE or END of the vessel.
            try:
                # Loading assuming standard tabular data with headers
                df = pd.read_csv(path, sep=r'\s+', comment='#') 
                return df
            except Exception as e:
                print(f"Error reading {path}: {e}")
                return None
    print(f"Warning: Could not find output file for {vessel_id}")
    return None

# ==========================================
# 3. ANALYSIS & PLOTTING
# ==========================================
def analyze_vessels():
    summary_data = []

    plt.figure(figsize=(15, 10))
    
    for i, (v_id, v_name) in enumerate(INTEREST_VESSELS.items()):
        df = load_simulation_data(v_id)
        
        if df is None or df.empty:
            continue

        # --- DATA EXTRACTION ---
        # We assume the file contains columns like 'time', 'pressure_in', 'pressure_out', 'flow_in', 'flow_out'
        # OR it might be just 'time', 'p', 'q' if recorded at a specific location.
        # Let's assume generic column names for now; YOU MAY NEED TO ADJUST based on actual file headers.
        
        # Heuristic to find Pressure (P) and Flow (Q) columns
        # First Blood often saves the middle node data or all nodes. 
        # Let's assume we take the last spatial point (outlet of segment) for flow/pressure.
        
        # Example adjustment: If columns are t, x, A, P, Q... 
        # We want the time series for a specific fixed x (e.g. x=Length).
        # Since parsing raw 1D solver output is complex without seeing the file, 
        # let's assume we can plot column 1 (Pressure) and column 2 (Flow) vs Time.
        
        # DUMMY LOGIC FOR DEMONSTRATION (Replace with actual column names)
        # If your .dat file is "Time, P_in, Q_in, P_out, Q_out"
        time = df.iloc[:, 0]  # First column is time
        pressure = df.iloc[:, 1] / 133.322 # Convert Pa to mmHg (usually col 1 or 3)
        flow = df.iloc[:, 2] * 1e6 # Convert m^3/s to mL/s (usually col 2 or 4)

        # --- METRICS CALCULATION ---
        # Use the last cardiac cycle (e.g., last 0.8s) if simulation is long
        last_cycle_mask = time > (time.max() - 1.0)
        p_cycle = pressure[last_cycle_mask]
        q_cycle = flow[last_cycle_mask]
        
        sys_p = p_cycle.max()
        dia_p = p_cycle.min()
        mean_q = q_cycle.mean()
        
        summary_data.append({
            "Vessel": v_name,
            "Systolic P (mmHg)": round(sys_p, 1),
            "Diastolic P (mmHg)": round(dia_p, 1),
            "Mean Flow (mL/s)": round(mean_q, 2)
        })

        # --- PLOTTING ---
        # Pressure Plot
        plt.subplot(2, 3, i+1)
        plt.plot(time[last_cycle_mask], p_cycle, label=f"{v_name} Pressure")
        plt.title(f"{v_name} Pressure")
        plt.ylabel("Pressure (mmHg)")
        plt.xlabel("Time (s)")
        plt.grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_PLOT_DIR, "pressure_waveforms.png"))
    print(f"Plots saved to {OUTPUT_PLOT_DIR}")

    # --- SAVE SUMMARY CSV ---
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv("simulation_summary.csv", index=False)
    print("\nSimulation Metrics:")
    print(summary_df)

# ==========================================
# 4. EXECUTION
# ==========================================
if __name__ == "__main__":
    print("Starting Analysis...")
    analyze_vessels()