import matplotlib.pyplot as plt

class Plotter:
    def __init__(self, sim):
        self.sim = sim

    def plot_pressure(self, probe):
        df = self.sim.get(probe)

        if df.shape[1] < 2:
            print(f"Probe {probe}: not enough columns ({df.shape[1]})")
            return

        t = df.iloc[:, 0]
        p = df.iloc[:, 1]

        plt.figure(figsize=(10,5))
        plt.plot(t, p)
        plt.title(f"Pressure - {probe}")
        plt.xlabel("Time [s]")
        plt.ylabel("Pressure [Pa]")
        plt.grid(True)
        plt.show()

    def plot_flow(self, probe):
        df = self.sim.get(probe)

        # You do NOT have flow in solver output → warn
        if df.shape[1] < 3:
            print(f"Probe {probe}: flow column not available")
            return

        t = df.iloc[:, 0]
        q = df.iloc[:, 2]

        plt.figure(figsize=(10,5))
        plt.plot(t, q)
        plt.title(f"Flow - {probe}")
        plt.xlabel("Time [s]")
        plt.ylabel("Flow")
        plt.grid(True)
        plt.show()

    def plot_all(self):
        plt.figure(figsize=(12,6))

        for probe in self.sim.list_probes():
            df = self.sim.get(probe)

            if df.shape[1] < 2:
                print(f"Skipping {probe}, not enough columns")
                continue

            plt.plot(df.iloc[:, 0], df.iloc[:, 1], label=probe)

        plt.title("All Probe Pressures")
        plt.xlabel("Time [s]")
        plt.ylabel("Pressure [Pa]")
        plt.legend()
        plt.grid(True)
        plt.show()
