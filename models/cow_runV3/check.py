import pandas as pd
a = pd.read_csv("arterial.csv")
arterial_nodes = set(a["start_node"]).union(a["end_node"])
main_nodes = {line.split(",")[2] for line in open("main.csv") if line.startswith("lumped")}
print("Missing:", main_nodes - arterial_nodes)
