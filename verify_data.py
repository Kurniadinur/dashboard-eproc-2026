import pandas as pd
import sys

files = [
    "GS Monev E-Purchasing TA.2026 - Monev BP2JK.csv",
    "GS Monev E-Purchasing TA.2026 - Monev Iemon.csv",
    "GS Monev E-Purchasing TA.2026 - Monev Inaproc.csv"
]

for f in files:
    print(f"--- Testing {f} ---")
    try:
        df = pd.read_csv(f, skiprows=4, on_bad_lines='warn')
        print(f"Successfully read {len(df)} rows.")
        print(f"Columns: {df.columns.tolist()[:5]}...")
    except Exception as e:
        print(f"Error reading {f}: {e}")
