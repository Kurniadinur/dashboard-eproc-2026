with open("GS Monev E-Purchasing TA.2026 - Monev BP2JK.csv", "rb") as f:
    content = f.read()
    print(f"Total bytes: {len(content)}")
    # Look for \x1a (Ctrl+Z)
    idx = content.find(b'\x1a')
    if idx != -1:
        print(f"Found Ctrl+Z at index {idx}")
    else:
        print("No Ctrl+Z found.")

import pandas as pd
try:
    df = pd.read_csv("GS Monev E-Purchasing TA.2026 - Monev BP2JK.csv", skiprows=4)
    print(f"Pandas read {len(df)} rows.")
except Exception as e:
    print(f"Pandas error: {e}")
