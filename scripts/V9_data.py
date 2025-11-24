#!/usr/bin/env python3
import json, csv, os, math
import pandas as pd
from io import StringIO
from shutil import copyfile, rmtree

# ============================================================
# CONFIG
# ============================================================
INPUT_DIR  = "../data_patient025"
OUTPUT_DIR = "../models/cow_runV9"

FEATURE = os.path.join(INPUT_DIR, "feature_mr_025.json")
NODES   = os.path.join(INPUT_DIR, "nodes_mr_025.json")
VARIANT = os.path.join(INPUT_DIR, "variant_mr_025.json")

HEART_SRC = "../models/Abel_ref2/heart_kim_lit.csv"

os.makedirs(OUTPUT_DIR, exist_ok=True)
ARTERIAL_CSV = os.path.join(OUTPUT_DIR, "arterial.csv")
MAIN_CSV     = os.path.join(OUTPUT_DIR, "main.csv")


# ============================================================
# Helpers
# ============================================================
def si(mm):
    return float(mm)/1000.0

def wall_thickness(radius):
    return 0.1*radius

def load_json(path):
    with open(path) as f:
        return json.load(f)


# ============================================================
# Load raw data
# ============================================================
feat = load_json(FEATURE)
nodes_raw = load_json(NODES)

# ============================================================
# Build arterial rows
# ============================================================
mater = dict(
    elastance_1 = 5e5,
    res_start   = 0.0,
    res_end     = 0.0,
    visc_fact   = 2.75,
    k1          = 2e6,
    k2          = -2253.0,
    k3          = 8.65e4
)

arteries = []

for group_id, vessels in feat.items():
    for vessel_name, seglist in vessels.items():

        if "bifurcation" in vessel_name.lower():
            continue

        for seg in seglist:
            s = f"N{seg['segment']['start']}"
            e = f"N{seg['segment']['end']}"

            r = si(seg["radius"]["mean"])
            d = 2*r
            t = wall_thickness(r)
            L = si(seg["length"])

            arteries.append([
                "vis_f",
                f"{vessel_name}_{group_id}",
                vessel_name,
                s,e,
                d,d, t,t, L,
                5,
                mater["elastance_1"],mater["res_start"],mater["res_end"],
                mater["visc_fact"], mater["k1"],mater["k2"],mater["k3"]
            ])

# Write arterial.csv
with open(ARTERIAL_CSV,"w",newline="") as f:
    w = csv.writer(f)
    w.writerow([
        "type","ID","name","start_node","end_node",
        "start_diameter[SI]","end_diameter[SI]",
        "start_thickness[SI]","end_thickness[SI]",
        "length[SI]","division_points",
        "elastance_1[SI]","res_start[SI]","res_end[SI]",
        "visc_fact[1]","k1[SI]","k2[SI]","k3[SI]"
    ])
    for a in arteries:
        w.writerow(a)

    f.write("\n")
    f.write("type,ID,name,valami,parameter,file name\n")

# Collect 1D nodes
all_nodes_1d = sorted(set([a[3] for a in arteries] + [a[4] for a in arteries]))

# Write nodes table
with open(ARTERIAL_CSV,"a") as f:
    for n in all_nodes_1d:
        f.write(f"node,{n},0,,\n")


print(f"[OK] V9: arterial.csv written ({len(arteries)} arteries, {len(all_nodes_1d)} nodes)")


# ============================================================
# Detect inlets (ICA detection)
# ============================================================
# Rule:
# - choose top 2 largest arteries whose name contains "ICA"
# - if none exist, choose 2 largest radii overall

diameters = {}
for row in arteries:
    name = row[2].lower()
    d = float(row[5]) # diameter
    s = row[3]
    e = row[4]

    if "ica" in name:
        diameters[(name,s,e)] = d

if len(diameters) < 2:
    # fallback: largest two arteries
    diameters = { (row[2].lower(), row[3],row[4]): float(row[5]) for row in arteries }

# sort by diameter
sorted_icas = sorted(diameters.items(), key=lambda x: -x[1])
ICA1 = sorted_icas[0][0]
ICA2 = sorted_icas[1][0]

ICA1_node = ICA1[1]
ICA2_node = ICA2[1]

print(f"[INFO] Inlets detected: ICA1={ICA1_node}, ICA2={ICA2_node}")


# ============================================================
# Detect terminal nodes for outlets
# ============================================================
deg = {}
for row in arteries:
    s,e = row[3],row[4]
    deg[s] = deg.get(s,0)+1
    deg[e] = deg.get(e,0)+1

terminal = [n for n,d in deg.items() if d==1]

# remove ICA nodes (they are inlets, not outlets)
terminal = [n for n in terminal if n not in (ICA1_node,ICA2_node)]

print(f"[INFO] Terminal outlets (Windkessel): {terminal}")


# ============================================================
# Build main.csv (heart at ICA1 & ICA2)
# ============================================================
lines=[]
lines.append(["run","forward"])
lines.append(["time","10"])
lines.append(["material","linear"])
lines.append(["solver","maccormack"])
lines.append([])
lines.append(["type","name","main node","model node"])

# MOC block
moc = ["moc","arterial"]

# add ICA inlets -> heart input node is "Heart"
moc.extend([ICA1_node,"Heart"])
moc.extend([ICA2_node,"Heart"])

# add all other terminal nodes as pX
for n in terminal:
    moc.extend([n,f"{n}_wk"])

lines.append(moc)
lines.append([])

# Heart model
lines.append(["lumped","heart_kim_lit","Heart","aorta"])

# Windkessel models
for n in terminal:
    pid = f"{n}_WK"
    lines.append(["lumped",pid,f"{n}_wk","n1"])

lines.append([])

# Node list
for n in all_nodes_1d:
    lines.append(["node",n])
lines.append(["node","Heart"])


with open(MAIN_CSV,"w",newline="") as f:
    csv.writer(f).writerows(lines)

print("[OK] V9 main.csv written.")


# ============================================================
# Generate Windkessel p-files
# ============================================================
# Geometry lookup
geo = {}
for row in arteries:
    s,e = row[3],row[4]
    d = float(row[5])
    L = float(row[9])
    r = d/2
    geo.setdefault(s,[]).append((r,L))
    geo.setdefault(e,[]).append((r,L))

def avg_geo(node):
    vals = geo.get(node)
    if not vals:
        return (1e-3,0.02)
    r = sum(v[0] for v in vals)/len(vals)
    L = sum(v[1] for v in vals)/len(vals)
    return r,L

MU  = 0.0035
RHO = 1060.0
E   = 4e6

def R_total(r,L):
    return (8*MU*L)/(math.pi*r**4)

def C_total(r):
    h=0.1*r
    return (math.pi*r**3)/(2*E*h)

def L_total(r,L):
    A=math.pi*r**2
    return (RHO*L)/A

for n in terminal:
    pid = f"{n}_WK"
    r,L = avg_geo(n)
    R = R_total(r,L); C = C_total(r); Lin = 0.25*L_total(r,L)

    fname = os.path.join(OUTPUT_DIR,f"{pid}.csv")
    with open(fname,"w") as f:
        f.write("data of edges\n")
        f.write("type,name,node start,node end,initial condition [SI],parameter [SI]\n")
        f.write(f"resistor,R0,n1,P1,0,{0.3*R}\n")
        f.write(f"resistor,R2,P1,g,0,{0.7*R}\n")
        f.write(f"capacitor,C1,P1,g,0,{C}\n")
        f.write(f"inductor,L1,P1,g,0,{Lin}\n")
        f.write("\n")
        f.write("data of nodes\n")
        f.write("type,name,initial condition [SI]\n")
        f.write("node,n1,100000\n")
        f.write("node,P1,100000\n")
        f.write("ground,g,100000\n")

print("[OK] V9 Windkessels written.")


# ============================================================
# Copy heart
# ============================================================
copyfile(HEART_SRC, os.path.join(OUTPUT_DIR,"heart_kim_lit.csv"))
print("[OK] Heart model copied.")

print("\nV9 generation complete.")
