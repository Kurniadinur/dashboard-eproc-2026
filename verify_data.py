import pandas as pd

def clean_currency(val):
    if pd.isna(val) or val == "" or val == "-":
        return 0.0
    clean = str(val).replace('Rp', '').replace('.', '').replace(',', '').replace(' ', '').strip()
    try:
        return float(clean)
    except:
        return 0.0

# Load data
files = {
    "BP2JK": "GS Monev E-Purchasing TA.2026 - Monev BP2JK.csv",
    "Iemon": "GS Monev E-Purchasing TA.2026 - Monev Iemon.csv",
    "Inaproc": "GS Monev E-Purchasing TA.2026 - Monev Inaproc.csv"
}

data = {}
for name, path in files.items():
    df = pd.read_csv(path, skiprows=4)
    df.columns = df.columns.str.strip()
    if 'Kode Paket' in df.columns:
        df['Kode Paket'] = df['Kode Paket'].astype(str).str.strip()
        df = df[df['Kode Paket'] != 'nan']
        df = df.drop_duplicates('Kode Paket', keep='last')
    data[name] = df

# Filter Terkontrak
# 1. Inaproc (Semua paket dianggap terkontrak)
inaproc_codes = set(data['Inaproc']['Kode Paket'])

# 2. BP2JK & Iemon (Hanya yang kolom 'Status Kontrak' == 'Terkontrak')
bp2jk_cont = set(data['BP2JK'][data['BP2JK']['Status Kontrak'].str.contains('Terkontrak', na=False, case=False)]['Kode Paket'])
iemon_cont = set(data['Iemon'][data['Iemon']['Status Kontrak'].str.contains('Terkontrak', na=False, case=False)]['Kode Paket'])

# Master Unik
all_codes = pd.concat([data[n]['Kode Paket'] for n in data]).unique()
total_master = len(all_codes)

# Gabungan Terkontrak (Union)
terkontrak_gabungan = inaproc_codes.union(bp2jk_cont).union(iemon_cont)
total_terkontrak = len(terkontrak_gabungan)

print(f"--- HASIL PERHITUNGAN ULANG ---")
print(f"Total Paket Unik di Master: {total_master}")
print(f"Paket Terkontrak (Inaproc): {len(inaproc_codes)}")
print(f"Paket Terkontrak (BP2JK): {len(bp2jk_cont)}")
print(f"Paket Terkontrak (Iemon): {len(iemon_cont)}")
print(f"-------------------------------")
print(f"TOTAL PAKET TERKONTRAK (KONSOLIDASI): {total_terkontrak}")
print(f"Persentase Terkontrak: {(total_terkontrak/total_master*100):.2f}%")
