from load_results import load_simulation
from plotter import Plotter

def main():
    # Load simulation data using config.yaml
    sim = load_simulation()

    print("Loaded probes:", sim.list_probes())

    plot = Plotter(sim)

    # Example plots
    print("Plotting pressure for p1...")
    plot.plot_pressure("p1")

    print("Plotting flow for p1...")
    plot.plot_flow("p1")

    print("Plotting all pressure curves...")
    print("Loaded probes:", sim.list_probes())

    plot.plot_all() 

if __name__ == "__main__":
    main()
