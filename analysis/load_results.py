import os
import glob
import yaml
import pandas as pd

class SimulationResults:
    def __init__(self, results_path, probe_map=None):
        self.results_path = results_path
        self.probe_map = probe_map or {}
        self.data = self._load_all()

    def _load_all(self):
        """Load each p-folder and read the .txt file inside."""
        data_dict = {}

        # Find folders starting with 'p'
        folders = sorted(
            f for f in glob.glob(os.path.join(self.results_path, "p*"))
            if os.path.isdir(f)
        )
        print("Detected probe folders:", folders)

        for folder in folders:
            probe = os.path.basename(folder)

            # Find .txt file inside the folder
            txt_files = glob.glob(os.path.join(folder, "*.txt"))
            if not txt_files:
                print(f"WARNING: no txt files inside {probe}")
                continue

            fname = txt_files[0]
            print(f"Loading file for {probe}: {fname}")

            # Skip truly empty files
            if os.path.getsize(fname) == 0:
                print(f"WARNING: Empty data file skipped: {fname}")
                continue

            # Load numeric data (comma or whitespace separated)
            try:
                df = pd.read_csv(
                    fname,
                    sep=r"[,\s]+",  # commas or whitespace
                    engine="python",
                    comment="#",
                    header=None,
                )

                # Remove empty columns (NaNs)
                df = df.dropna(axis=1, how="all")

                # Ensure minimum structure: at least time + pressure
                if df.shape[1] < 2:
                    print(f"WARNING: Not enough columns in {fname}, got {df.shape[1]}")
                    continue

                if len(df) < 2:
                    print(f"WARNING: Too few rows in {fname}")
                    continue

                data_dict[probe] = df

            except Exception as e:
                print(f"ERROR reading {fname}: {e}")
                continue

        return data_dict

    def list_probes(self):
        return list(self.data.keys())

    def get(self, probe):
        return self.data[probe]


def load_simulation(config_path="config.yaml"):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    results_path = cfg["results_dir"]
    probe_map = cfg.get("probe_map", {})

    return SimulationResults(results_path, probe_map)
