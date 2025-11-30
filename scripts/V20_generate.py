import json
import math
import os
import shutil

# ==========================================
# 1. CONFIGURATION
# ==========================================
PATIENT_ID = "025" 
# CORRECT RELATIVE PATH: ../data_patient025
RAW_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", f"data_patient{PATIENT_ID}"))

OUTPUT_DIR_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
MODEL_NAME = "cow_runV20" 
FULL_OUTPUT_PATH = os.path.join(OUTPUT_DIR_BASE, MODEL_NAME)

PATH_TO_REF_HEART = "../models/Abel_ref2/heart_kim_lit.csv" 

MAT_PROPS_CEREBRAL = { "visc_fact": 2.75, "k1": 2.0e6, "k2": -2253.0, "k3": 8.65e4, "elastance": 1.5e6 }
WK_PROPS = { "R_prox": 1.45e8, "R_dist": 1.0e9, "C": 8.0e-10, "L": 5.0e4 }

INTERFACES = { "Basilar_Inlet": "n49", "R_ICA_Inlet": "n43", "L_ICA_Inlet": "n40" }

# ==========================================
# 2. STATIC BODY DATA (Vessels AND Nodes)
# ==========================================
# A. VESSELS (A1 - A59 + others)
STATIC_VESSELS = """vis_f,A1,Ascending aorta 1,H,n1,0.0294,0.0293,0.00294,0.00293,0.005,5,2.92E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A2,Aortic arch A,n2,n3,0.0251,0.024,0.00251,0.0024,0.02,5,3.19E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A3,Brachiocephalic,n2,n6,0.0202,0.018,0.00202,0.0018,0.034,6,3.62E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A4,Subclavian A,n6,n7,0.0115,0.009,0.00115,0.0009,0.034,5,5.06E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A19,Subclavian A,n4,n10,0.011,0.0085,0.0011,0.00085,0.034,8,5.20E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A5,Common carotid,n6,n32,0.0135,0.007,0.00135,0.0007,0.094,19,5.23E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A15,Common carotid,n3,n26,0.012,0.006,0.0012,0.0006,0.139,19,5.65E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A6,Vertebral,n7,n31,0.0037,0.0028,0.00037,0.00028,0.149,15,9.82E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A20,Vertebral,n10,n31,0.0037,0.0028,0.00037,0.00028,0.148,18,9.82E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A7,Subclavian B - axillary - brachial,n7,n8,0.0081,0.0047,0.00081,0.00047,0.422,53,6.73E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A21,Subclavian B - axillary - brachial,n10,n11,0.0081,0.0047,0.00081,0.00047,0.422,53,6.73E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A8,Radial,n8,p4,0.0037,0.0031,0.00037,0.00031,0.235,25,9.51E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A22,Radial,n11,p17,0.0035,0.0028,0.00035,0.00028,0.235,24,9.98E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A9,Ulnar A,n8,n9,0.0037,0.0034,0.00037,0.00034,0.067,7,9.24E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A23,Ulnar A,n11,n12,0.0043,0.0043,0.00043,0.00043,0.067,8,8.24E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A10,Interosseous,n9,p5,0.003,0.003,0.0003,0.0003,0.079,11,1.34E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A24,Interosseous,n12,p16,0.003,0.003,0.0003,0.0003,0.079,7,1.40E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A11,Ulnar B,n9,p6,0.0041,0.0037,0.00041,0.00037,0.171,17,1.02E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A25,Ulnar B,n12,p15,0.0041,0.0037,0.00041,0.00037,0.171,19,8.74E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A12,Internal carotid,n32,n46,0.0057,0.0043,0.00057,0.00043,0.178,21,7.60E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A16,Internal carotid,n26,n37,0.0053,0.0041,0.00053,0.00041,0.178,21,7.87E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A13,External carotid 1,n32,n33,0.005,0.0045,0.0005,0.00045,0.041,7,7.78E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A17,External carotid 1,n26,n27,0.0047,0.0043,0.00047,0.00043,0.041,7,8.03E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A14,Aortic arch B,n3,n4,0.0214,0.0208,0.00214,0.00208,0.039,7,3.44E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A18,Thoracic aorta A,n4,n51,0.02,0.0189,0.002,0.00189,0.052,9,3.59E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A26,Intercostals,n51,p47,0.0126,0.0095,0.00126,0.00095,0.08,12,4.86E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A27,Thoracic aorta B,n51,n52,0.0165,0.0129,0.00165,0.00129,0.104,17,4.17E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A28,Abdominal aorta A,n52,n22,0.0122,0.0122,0.00122,0.00122,0.053,8,4.58E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A29,Celiac A,n52,n20,0.0078,0.0069,0.00078,0.00069,0.02,5,6.06E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A30,Celiac B,n20,n21,0.0052,0.0049,0.00052,0.00049,0.02,5,7.50E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A31,Hepatic,n21,p18,0.0054,0.0044,0.00054,0.00044,0.066,11,7.67E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A32,Gastric,n20,p19,0.0032,0.003,0.00032,0.0003,0.071,7,1.00E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A33,Splenic,n21,p20,0.0042,0.0039,0.00042,0.00039,0.063,7,8.54E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A34,Superior mesenteric,n22,p22,0.0079,0.0071,0.00079,0.00071,0.059,8,5.99E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A35,Abdominal aorta B,n22,n23,0.0115,0.0113,0.00115,0.00113,0.02,5,4.75E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A36,Renal,n23,p21,0.0052,0.0052,0.00052,0.00052,0.032,5,7.37E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A38,Renal,n24,p23,0.0052,0.0052,0.00052,0.00052,0.032,5,7.37E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A37,Abdominal aorta C,n23,n24,0.0118,0.0118,0.00118,0.00118,0.02,5,4.66E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A39,Abdominal aorta D,n24,n25,0.0116,0.011,0.00116,0.0011,0.106,16,4.77E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A40,Inferior mesenteric,n25,p24,0.0047,0.0032,0.00047,0.00032,0.05,10,8.80E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A41,Abdominal aorta E,n25,n13,0.0108,0.0104,0.00108,0.00104,0.02,5,4.94E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A42,Common iliac,n13,n14,0.0079,0.007,0.00079,0.0007,0.059,8,6.01E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A43,Common iliac,n13,n17,0.0079,0.007,0.00079,0.0007,0.059,8,6.01E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A44,External iliac,n17,n18,0.0064,0.0061,0.00064,0.00061,0.144,18,6.63E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A50,External iliac,n14,n15,0.0064,0.0061,0.00064,0.00061,0.144,18,6.63E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A45,Inner iliac,n17,p11,0.004,0.004,0.0004,0.0004,0.05,6,8.60E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A51,Inner iliac,n14,p7,0.004,0.004,0.0004,0.0004,0.05,6,8.60E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A46,Femoral,n18,n19,0.0052,0.0038,0.00052,0.00038,0.443,51,8.10E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A52,Femoral,n15,n16,0.0052,0.0038,0.00052,0.00038,0.443,51,8.10E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A47,Deep femoral,n18,p12,0.004,0.0037,0.0004,0.00037,0.126,14,8.80E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A53,Deep femoral,n15,p8,0.004,0.0037,0.0004,0.00037,0.126,14,8.80E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A48,Posterior tibial,n19,p13,0.0031,0.0030,0.00031,0.00030,0.321,32,1.03E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A54,Posterior tibial,n16,p10,0.0031,0.0030,0.00031,0.00030,0.321,32,1.03E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A49,Anterior tibial,n19,p14,0.0030,0.0028,0.00030,0.00028,0.343,33,1.16E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A55,Anterior tibial,n16,p9,0.0030,0.0028,0.00030,0.00028,0.343,33,1.16E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A56,Basilar artery 2,n31,n50,0.004,0.0036,0.0004,0.00036,0.02,5,8.88E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A57,Superior cerebellar,n50,p35,0.0017,0.0014,0.00017,0.00014,0.01,5,1.54E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A58,Superior cerebellar,n50,p34,0.0017,0.0014,0.00017,0.00014,0.01,5,1.54E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A59,Basilar artery 1,n50,n49,0.0031,0.0027,0.00031,0.00027,0.005,5,1.05E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A79,Int. car. sinus,n46,n45,0.0043,0.0039,0.00043,0.00039,0.011,5,8.48E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A81,Int. car. sinus,n37,n38,0.0043,0.0039,0.00043,0.00039,0.011,5,8.48E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A80,Ophthalmic,n46,p37,0.001,0.0005,0.0001,0.00005,0.011,10,2.59E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A82,Ophthalmic,n37,p32,0.001,0.0005,0.0001,0.00005,0.011,10,2.59E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A83,External carotid 2,n33,n34,0.004,0.0035,0.0004,0.00035,0.061,9,8.95E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A85,External carotid 2,n27,n28,0.004,0.0035,0.0004,0.00035,0.061,9,8.95E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A84,Sup. thy. asc. ph. lyng. fac. occ.,n33,p44,0.002,0.001,0.0002,0.0001,0.101,8,1.65E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A86,Sup. thy. asc. ph. lyng. fac. occ.,n27,p25,0.002,0.001,0.0002,0.0001,0.101,8,1.65E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A87,Superficial temporal,n34,n35,0.0032,0.003,0.00032,0.0003,0.061,6,1.00E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A89,Superficial temporal,n28,n29,0.0032,0.003,0.00032,0.0003,0.061,6,1.00E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A88,Maxillary,n34,p43,0.0022,0.001,0.00022,0.0001,0.091,7,1.61E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A90,Maxillary,n28,p26,0.0022,0.001,0.00022,0.0001,0.091,9,1.61E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A91,Superficial temporal frontal br.,n35,p41,0.0022,0.0014,0.00022,0.00014,0.1,9,1.43E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A93,Superficial temporal frontal br.,n29,p28,0.0022,0.0014,0.00022,0.00014,0.1,11,1.43E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A92,Superficial temporal parietal br.,n35,p42,0.0022,0.0014,0.00022,0.00014,0.101,9,1.43E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A94,Superficial temporal parietal br.,n29,p27,0.0022,0.0014,0.00022,0.00014,0.101,11,1.43E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A95,Ascending aorta 2,n1,n2,0.0293,0.0288,0.00293,0.00288,0.035,7,2.94E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A96,RightCoronary,n1,p1,3.60E-03,2.60E-03,3.60E-04,2.60E-04,5.37E-02,7,8.60E+05,0.00E+00,0.00E+00,2.75,2.e6,-2253.,8.65e4
vis_f,A97,LeftMainCoronary,n1,n53,4.90E-03,4.70E-03,4.90E-04,4.70E-04,5.00E-03,7,7.73E+05,0.00E+00,0.00E+00,2.75,2.e6,-2253.,8.65e4
vis_f,A98,LeftAnteriorDescending,n53,p2,3.80E-03,1.50E-03,3.80E-04,1.50E-04,4.70E-02,15,8.60E+05,0.00E+00,0.00E+00,2.75,2.e6,-2253.,8.65e4
vis_f,A99,LeftCircumflex,n53,p3,3.50E-03,3.10E-03,3.50E-04,3.10E-04,2.60E-02,7,8.60E+05,0.00E+00,0.00E+00,2.75,2.e6,-2253.,8.65e4
vis_f,A100,Ant. choroidal,n44,p45,0.0015,0.0013,0.00015,0.00013,0.036,5,1.64E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A102,Ant. choroidal,n39,p46,0.0015,0.0013,0.00015,0.00013,0.036,5,1.64E+06,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A66,ICA distal PCo–ant. chor. seg.,n45,n44,0.0039,0.0038,0.00039,0.00038,0.002,5,8.80E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A67,ICA distal PCo–ant. chor. seg.,n38,n39,0.0039,0.0038,0.00039,0.00038,0.002,5,8.80E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A101,ICA distal cnt. chor.–M1 seg.,n44,n43,0.0038,0.0038,0.00038,0.00038,0.002,5,8.87E+05,0,0,2.75,2.e6,-2253.,8.65e4
vis_f,A103,ICA distal cnt. chor.–M1 seg.,n39,n40,0.0038,0.0038,0.00038,0.00038,0.002,5,8.87E+05,0,0,2.75,2.e6,-2253.,8.65e4"""

# B. NODES (The part you were missing!)
STATIC_NODES = """
type,ID,name,valami,parameter,file name
heart,H,0,
node,n1,0,5.27E+11,
node,n2,0,5.27E+11,
node,n3,0,5.27E+11,
node,n4,0,5.27E+11,
node,n5,0,7.27E+10,
node,n6,0,7.27E+10,
node,n7,0,7.27E+10,
node,n8,0,7.27E+10,
node,n9,0,7.27E+10,
node,n10,0,7.27E+10,
node,n11,0,7.27E+10,
node,n12,0,7.27E+10,
node,n13,0,7.27E+10,
node,n14,0,7.27E+10,
node,n15,0,7.27E+10,
node,n16,0,7.27E+10,
node,n17,0,7.27E+10,
node,n18,0,7.27E+10,
node,n19,0,7.27E+10,
node,n20,0,7.27E+10,
node,n21,0,7.27E+10,
node,n22,0,7.27E+10,
node,n23,0,7.27E+10,
node,n24,0,7.27E+10,
node,n25,0,7.27E+10,
node,n26,0,4.27E+10,
node,n27,0,4.27E+10,
node,n28,0,4.27E+10,
node,n29,0,4.27E+10,
node,n30,0,4.27E+10,
node,n31,0,4.27E+10,
node,n32,0,4.27E+10,
node,n33,0,4.27E+10,
node,n34,0,4.27E+10,
node,n35,0,4.27E+10,
node,n36,0,4.27E+10,
node,n37,0,4.27E+10,
node,n38,0,4.27E+10,
node,n39,0,4.27E+10,
node,n40,0,4.27E+10,
node,n41,0,4.27E+10,
node,n42,0,4.27E+10,
node,n43,0,4.27E+10,
node,n44,0,4.27E+10,
node,n45,0,4.27E+10,
node,n46,0,4.27E+10,
node,n47,0,4.27E+10,
node,n48,0,4.27E+10,
node,n49,0,4.27E+10,
node,n50,0,4.27E+10,
node,n51,0,4.27E+10,
node,n52,0,4.27E+10,
node,n53,0,4.27E+10,
perif,p1,0,,
perif,p2,0,,
perif,p3,0,,
perif,p4,0,,
perif,p5,0,,
perif,p6,0,,
perif,p7,0,,
perif,p8,0,,
perif,p9,0,,
perif,p10,0,,
perif,p11,0,,
perif,p12,0,,
perif,p13,0,,
perif,p14,0,,
perif,p15,0,,
perif,p16,0,,
perif,p17,0,,
perif,p18,0,,
perif,p19,0,,
perif,p20,0,,
perif,p21,0,,
perif,p22,0,,
perif,p23,0,,
perif,p24,0,,
perif,p25,0,,
perif,p26,0,,
perif,p27,0,,
perif,p28,0,,
perif,p29,0,,
perif,p30,0,,
perif,p31,0,,
perif,p32,0,,
perif,p33,0,,
perif,p34,0,,
perif,p35,0,,
perif,p36,0,,
perif,p37,0,,
perif,p38,0,,
perif,p39,0,,
perif,p40,0,,
perif,p41,0,,
perif,p42,0,,
perif,p43,0,,
perif,p44,0,,
perif,p45,0,,
perif,p46,0,,
perif,p47,0,,"""

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def load_json(filename):
    path = os.path.join(RAW_DATA_DIR, filename)
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"CRITICAL ERROR: Could not find file at: {path}")
        exit(1)

feat_data = load_json(f'feature_mr_{PATIENT_ID}.json')
nodes_data = load_json(f'nodes_mr_{PATIENT_ID}.json')
variant_data = load_json(f'variant_mr_{PATIENT_ID}.json')

def get_coords(node_id):
    for label_group in nodes_data.values():
        for node_list in label_group.values():
            for node in node_list:
                if node.get('id') == node_id and 'coords' in node:
                    return node['coords']
    return None

def calc_gap_meters(id1, id2):
    c1 = get_coords(id1)
    c2 = get_coords(id2)
    if c1 and c2:
        dist_mm = math.sqrt(sum((a - b)**2 for a, b in zip(c1, c2)))
        return dist_mm / 1000.0
    return 0.0

def get_geom(label_id, segment_name):
    try:
        group = feat_data.get(str(label_id))
        if not group: return 0.0015, 0.01
        seg_data = group.get(segment_name)
        if isinstance(seg_data, list): data = seg_data[0]
        else: data = seg_data
        r_mm = data['radius']['median']
        l_mm = data['length']
        return (r_mm / 1000.0), (l_mm / 1000.0)
    except Exception:
        return 0.0015, 0.01

def fmt_artery(id_str, name, start, end, r_m, l_m):
    d = r_m * 2.0
    h = d * 0.1
    N = max(3, int(l_m * 1000 / 2)) 
    return (f"vis_f,{id_str},{name},{start},{end},"
            f"{d:.6f},{d:.6f},{h:.6f},{h:.6f},{l_m:.6f},{N},"
            f"{MAT_PROPS_CEREBRAL['elastance']:.2E},0,0,"
            f"{MAT_PROPS_CEREBRAL['visc_fact']},"
            f"{MAT_PROPS_CEREBRAL['k1']:.2E},{MAT_PROPS_CEREBRAL['k2']:.2E},{MAT_PROPS_CEREBRAL['k3']:.2E}")

# ==========================================
# 4. GENERATION
# ==========================================
def generate_arterial(output_path):
    lines = ["type,ID,name,start_node,end_node,start_diameter[SI],end_diameter[SI],start_thickness[SI],end_thickness[SI],length[SI],division_points,elastance_1[SI],res_start[SI],res_end[SI],visc_fact[1],k1[SI],k2[SI],k3[SI]"]
    
    # 1. APPEND STATIC BODY VESSELS
    lines.append(STATIC_VESSELS)

    # 2. APPEND PATIENT CoW VESSELS
    outlets = []
    junction_nodes = set(["cow_n1", "cow_n2", "cow_n3", "cow_n4", "cow_n5"])
    
    # Basilar
    r, l = get_geom(1, "BA")
    gap = calc_gap_meters(51, 59)
    lines.append(fmt_artery("P_BA", "Pat_Basilar", INTERFACES["Basilar_Inlet"], "cow_n1", r, l + gap))

    # P1
    if variant_data['posterior']['R-P1']:
        r, l = get_geom(2, "P1")
        lines.append(fmt_artery("P_RP1", "Pat_R_P1", "cow_n1", "cow_n2", r, l))
    if variant_data['posterior']['L-P1']:
        r, l = get_geom(3, "P1")
        lines.append(fmt_artery("P_LP1", "Pat_L_P1", "cow_n1", "cow_n3", r, l))

    # Pcom
    if variant_data['posterior']['R-Pcom']:
        r, l = get_geom(8, "Pcom")
        gap = calc_gap_meters(389, 619)
        lines.append(fmt_artery("P_RPcom", "Pat_R_Pcom", INTERFACES["R_ICA_Inlet"], "cow_n2", r, l + gap))
    if variant_data['posterior']['L-Pcom']:
        r, l = get_geom(9, "Pcom")
        gap = calc_gap_meters(545, 527)
        lines.append(fmt_artery("P_LPcom", "Pat_L_Pcom", INTERFACES["L_ICA_Inlet"], "cow_n3", r, l + gap))

    # A1
    if variant_data['anterior']['R-A1']:
        r, l = get_geom(11, "A1")
        gap = calc_gap_meters(389, 689)
        lines.append(fmt_artery("P_RA1", "Pat_R_A1", INTERFACES["R_ICA_Inlet"], "cow_n4", r, l + gap))
    if variant_data['anterior']['L-A1']:
        r, l = get_geom(12, "A1")
        gap = calc_gap_meters(545, 809)
        lines.append(fmt_artery("P_LA1", "Pat_L_A1", INTERFACES["L_ICA_Inlet"], "cow_n5", r, l + gap))

    # Acom
    if variant_data['anterior']['Acom']:
        r, l = get_geom(10, "Acom")
        lines.append(fmt_artery("P_Acom", "Pat_Acom", "cow_n4", "cow_n5", r, l))

    # TERMINAL OUTLETS
    r, l = get_geom(5, "MCA")
    lines.append(fmt_artery("P_RMCA", "Pat_R_MCA", INTERFACES["R_ICA_Inlet"], "out_rmca", r, l))
    outlets.append("out_rmca")
    
    r, l = get_geom(7, "MCA")
    lines.append(fmt_artery("P_LMCA", "Pat_L_MCA", INTERFACES["L_ICA_Inlet"], "out_lmca", r, l))
    outlets.append("out_lmca")

    r, l = get_geom(2, "P2")
    lines.append(fmt_artery("P_RP2", "Pat_R_P2", "cow_n2", "out_rp2", r, l))
    outlets.append("out_rp2")

    r, l = get_geom(3, "P2")
    lines.append(fmt_artery("P_LP2", "Pat_L_P2", "cow_n3", "out_lp2", r, l))
    outlets.append("out_lp2")

    r, l = get_geom(11, "A2")
    lines.append(fmt_artery("P_RA2", "Pat_R_A2", "cow_n4", "out_ra2", r, l))
    outlets.append("out_ra2")

    r, l = get_geom(12, "A2")
    lines.append(fmt_artery("P_LA2", "Pat_L_A2", "cow_n5", "out_la2", r, l))
    outlets.append("out_la2")

    # 3. APPEND STATIC NODE DATA (HEART + BODY NODES)
    lines.append(STATIC_NODES)

    # 4. APPEND NEW PATIENT NODES
    # Add new Junctions
    for node in junction_nodes:
        lines.append(f"node,{node},0,4.27E+10,") # Using stiffness ~Carotid
    
    # Add new Outlets
    for node in outlets:
        lines.append(f"perif,{node},0,,")

    with open(output_path, 'w') as f:
        f.write("\n".join(lines))
    return outlets

def generate_main(outlets, output_path):
    content = """run,forward
time,10.0
material,linear
solver,maccormack

type,name,main node,model node
moc,arterial,Heart,H

lumped,heart_kim_lit,Heart,aorta
"""
    # 1. Standard Body Outlets (p1-p47)
    for i in range(1, 48):
        content += f"lumped,p{i},p{i},n1\n"

    # 2. Patient CoW Outlets
    for out in outlets:
        content += f"lumped,{out},{out},n1\n"

    content += "\nnode,Heart\n"
    with open(output_path, 'w') as f:
        f.write(content)

def generate_windkessel_files(outlets, output_dir):
    def wk_content(name, proximal_node):
        return f"""data of edges
type, name, node start, node end, initial condition [SI], parameter [SI]
resistor, R_prox, {proximal_node}, p_mid, 0.0, {WK_PROPS['R_prox']:.2E}
resistor, R_dist, p_mid, g, 0.0, {WK_PROPS['R_dist']:.2E}
capacitor, C_wk, p_mid, g, 0.0, {WK_PROPS['C']:.2E}

data of nodes
type, name, initial condition [SI]
node, {proximal_node}, 1.00e+05
node, p_mid, 1.00e+05
ground, g, 1.00e+05
"""
    # Generate files for new brain outlets
    for out_node in outlets:
        with open(os.path.join(output_dir, f"{out_node}.csv"), 'w') as f:
            f.write(wk_content(out_node, "n1"))
            
    # Generate dummy files for body outlets p1..p47
    for i in range(1, 48):
        name = f"p{i}"
        with open(os.path.join(output_dir, f"{name}.csv"), 'w') as f:
            f.write(wk_content(name, "n1"))

def copy_heart(output_dir):
    try:
        if os.path.exists(PATH_TO_REF_HEART):
            shutil.copy(PATH_TO_REF_HEART, os.path.join(output_dir, "heart_kim_lit.csv"))
        else:
            # Fallback: Write a default heart file
            content = """type, name, node start, node end, initial condition [SI], parameter [SI], parameter [SI]
Right Atrium
voltage, V_ra, g, p_RA1, 0.000e+00, 8.0e+02
inductor, L_ra, p_RA1, p_RA2, 0.000e+00, 5.000e+4
diode, R_ra, p_RA2, p_RA3, 0.000e+00, 1.000e+06
Right Ventrice
elastance, E_rv, g2, p_RA3, 0.000e+00, 6.67e+07, 8.0e+06
inductor, L_rv, p_RA3, p_RV1, 0.000e+00, 2.50e+04
diode, R_rv, p_RV1, p_RV2, 0.000e+00, 2.000e+06
P
resistor, R_pa, p_RV2, p_LA1, 0.000e+00, 1.2e+07
capacitor, C_pa, g, p_RV2, 0.000e+00, 3.0e-08
Left Atrium
capacitor, E_la, g3, p_LA1, 0.000e+00, 3.60e-08
inductor, L_la, p_LA1, p_LA2, 0.000e+00, 1.00e+04
diode, R_la, p_LA2, p_LA3, 0.000e+00, 5.000e+05
Left Ventrice
elastance, E_lv, g1, p_LA3, 0.000e+00, 2.67e+08, 8.0e+06
inductor, L_lv_aorta, p_LA3, p_LV1, 0.000e+00, 6.50e+04
diode, R_lv_aorta, p_LV1, aorta, 0.000e+00, 1.00e+06

data of nodes
type, name, initial condition [SI]
node, aorta, 1.13e+05
ground, g, 1.00e+05
ground, g1, 1.00e+05
ground, g2, 1.00e+05
ground, g3, 1.00e+05
node, p_RA1, 1.010e+05
node, p_RA2, 1.010e+05
node, p_RA3, 1.010e+05
node, p_RV1, 1.010e+05
node, p_RV2, 1.010e+05
node, p_LA1, 1.0110e+05
node, p_LA2, 1.0110e+05
node, p_LA3, 1.0110e+05
node, p_LV1, 1.0110e+05
"""
            with open(os.path.join(output_dir, "heart_kim_lit.csv"), 'w') as f:
                f.write(content)
    except Exception as e:
        print(f"Error copying heart: {e}")

# ==========================================
# 5. EXECUTION
# ==========================================
if __name__ == "__main__":
    if not os.path.exists(FULL_OUTPUT_PATH):
        os.makedirs(FULL_OUTPUT_PATH)
        print(f"Created output directory: {FULL_OUTPUT_PATH}")
    
    outlets = generate_arterial(os.path.join(FULL_OUTPUT_PATH, 'arterial.csv'))
    print(f"Generated arterial.csv")
    
    generate_main(outlets, os.path.join(FULL_OUTPUT_PATH, 'main.csv'))
    print("Generated main.csv")
    
    copy_heart(FULL_OUTPUT_PATH)
    print("Generated heart model")
    
    generate_windkessel_files(outlets, FULL_OUTPUT_PATH)
    print(f"Generated Windkessel files for body (p1-p47) and brain outlets.")
    
    print("\nDONE. You can now run:")
    print(f"cd ../projects/simple_run")
    print(f"./simple_run.out {MODEL_NAME}")