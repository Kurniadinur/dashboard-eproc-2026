# PART 1: IMPORTS AND CSS
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import re
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Dashboard Monev EP 2026 (Cloud)", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    :root {
        --primary: #1e40af; --secondary: #3b82f6; --accent: #fbbf24;
        --bg-main: #f8fafc; --text-dark: #1e293b; --text-light: #64748b;
        --white: #ffffff; --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    .stApp { background-color: var(--bg-main); font-family: 'Plus Jakarta Sans', sans-serif; }
    .block-container { padding: 2rem 3rem !important; }
    .header-wrapper {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        padding: 2.5rem; border-radius: 20px; margin-bottom: 2.5rem; color: white;
        box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.3);
    }
    .header-text h1 { margin: 0; font-size: 2.2rem !important; font-weight: 800; }
    div[data-testid="metric-container"] {
        background-color: var(--white); padding: 1.5rem !important; border-radius: 16px !important;
        box-shadow: var(--shadow) !important; border: 1px solid #f1f5f9 !important;
    }
    .chart-card {
        background: var(--white); padding: 1.5rem; border-radius: 16px;
        box-shadow: var(--shadow); margin-bottom: 1.5rem; border: 1px solid #f1f5f9;
    }
    </style>
    """, unsafe_allow_html=True)

# PART 2: SMART HELPERS (ROBUST FOR CLOUD)
def clean_currency_vectorized(series):
    """
    Smarter currency cleaning logic to handle Linux (Cloud) environment.
    Handles Indonesian format (1.234.567,89) and handles numeric inputs.
    """
    if series is None or series.empty: return pd.Series(0.0)
    
    # 1. If already numeric, just return
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float).fillna(0.0)
    
    def smart_clean(val):
        val = str(val).lower().replace('rp', '').strip()
        if not val or val in ['-', 'nan', 'none', '']: return 0.0
        
        # Remove common hidden characters like non-breaking spaces (\xa0)
        val = val.replace('\xa0', '').replace(' ', '')
        
        # Case detection:
        # Many systems in Linux detect '15.000' as 15.0 (decimal).
        # We need to distinguish if '.' is thousands or decimal.
        # In ID finance, Pagu is usually millions/billions.
        
        # Strategy: 
        # 1. If there's a comma, it's definitely the decimal (Indonesian).
        if ',' in val:
            val = val.replace('.', '').replace(',', '.')
        else:
            # 2. If only dots exist (e.g., 15.000.000 or 15.000)
            # We treat dots as thousands UNLESS it looks like a small float.
            # But for this specific project, everything is in thousands or full IDR.
            # We assume '.' is thousands if it's not the only dot OR followed by 3 digits.
            if val.count('.') >= 1:
                # Special case: check if it's like 123.0 (from float to str conversion)
                if val.endswith('.0'):
                    val = val[:-2] # remove the .0
                
                # If there are still dots, remove them as thousands
                val = val.replace('.', '')
        
        try:
            return float(val)
        except:
            # Fallback: remove everything except digits and minus sign
            val = re.sub(r'[^-0-9]', '', val)
            try: return float(val) if val else 0.0
            except: return 0.0

    return series.apply(smart_clean)

def format_idr(val):
    if abs(val)>=1e12: return f"Rp {val/1e12:.2f} T"
    elif abs(val)>=1e9: return f"Rp {val/1e9:.2f} M"
    else: return f"Rp {val:,.0f}"

def normalize_status(s_str, source=None):
    if pd.isna(s_str) or s_str == "" or str(s_str).upper() == "NONE": return "Belum Proses"
    s = str(s_str).upper()
    if any(x in s for x in ['TERKONTRAK', 'SELESAI KONTRAK']): return "Terkontrak"
    if 'BATAL' in s: return "Batal"
    if 'PERSIAPAN TERKONTRAK' in s or (source == 'BP2JK' and 'PROSES KONTRAK' in s): return "Persiapan Terkontrak"
    if any(x in s for x in ['PEMASUKAN PENAWARAN', 'PROSES EVALUASI', 'REVIEW TIMLIT', 'PROSES PENETAPAN PEMENANG']) or (source != 'BP2JK' and 'PROSES KONTRAK' in s): return "Proses E-Purchasing"
    if any(x in s for x in ['BELUM PROSES', 'PERSIAPAN']): return "Belum Proses"
    return "Belum Proses"

def normalize_text(text):
    if pd.isna(text): return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text).lower())

# URLs and Fetch Logic
URL_BP2JK = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=1807383381&single=true&output=csv"
URL_IEMON = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=881219520&single=true&output=csv"
URL_INAPROC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=189207385&single=true&output=csv"

@st.cache_data(ttl=600)
def load_and_process_all(files=None, bypass_cache=False):
    urls = {"BP2JK": URL_BP2JK, "Iemon": URL_IEMON, "Inaproc": URL_INAPROC}
    raw, stats, duplicates = {}, {}, {}
    for n, u in urls.items():
        src = files[n] if (files and files.get(n)) else u
        try:
            df = pd.read_csv(src, skiprows=4, quotechar='"', on_bad_lines='warn', engine='python')
            df.columns = df.columns.str.strip()
            
            # Flexible Column Detection
            def find_col(keywords):
                for c in df.columns:
                    if any(k.upper() in str(c).upper() for k in keywords): return c
                return None

            sirup_col = find_col(['SIRUP', 'KODE RUP', 'KODERUP'])
            kp_col = find_col(['KODE PAKET', 'KODEPAKET'])
            
            # Extract and Clean IDs
            df['ID SIRUP'] = df[sirup_col].astype(str).str.strip().str.replace('.0','',regex=False) if sirup_col else 'MISSING'
            df['Kode Paket'] = df[kp_col].astype(str).str.strip() if kp_col else 'MISSING'
            
            invalid = ['nan', 'None', 'nan.0', '0', '-', '']
            df['ID SIRUP'] = df['ID SIRUP'].apply(lambda x: 'MISSING' if str(x).strip() in invalid else str(x).strip())
            df['Kode Paket'] = df['Kode Paket'].apply(lambda x: 'MISSING' if str(x).strip() in invalid else str(x).strip())

            if n == "Inaproc":
                df['nk_c'] = clean_currency_vectorized(df['Nilai Kontrak'])
                rek_col = find_col(['REKANAN', 'NAMA REKANAN'])
                rek_val = df[rek_col].astype(str).str.strip() if rek_col else 'None'
                df['SOURCE_KEY'] = df['ID SIRUP'] + "_" + rek_val + "_" + df['nk_c'].astype(str)
            else:
                def make_key(r):
                    if r['ID SIRUP'] != 'MISSING' and r['Kode Paket'] != 'MISSING': return f"{r['ID SIRUP']}_{r['Kode Paket']}"
                    if r['Kode Paket'] != 'MISSING': return f"KP_{r['Kode Paket']}"
                    if r['ID SIRUP'] != 'MISSING': return f"SIRUP_{r['ID SIRUP']}"
                    return f"RAND_{np.random.randint(1000000, 9999999)}"
                df['SOURCE_KEY'] = df.apply(make_key, axis=1)
            
            dup_mask = df.duplicated('SOURCE_KEY', keep=False)
            duplicates[n] = df[dup_mask].sort_values('SOURCE_KEY').copy()
            df = df.drop_duplicates('SOURCE_KEY', keep='last')
            
            if 'Nama Paket' in df.columns:
                df['norm_name'] = df['Nama Paket'].apply(normalize_text)
            
            raw[n], stats[n] = df, {"total": len(df), "before": len(df)+len(duplicates[n]), "cols": list(df.columns)}
        except Exception as e:
            raw[n], stats[n] = pd.DataFrame(), {"total": 0, "before": 0, "error": str(e)}
            duplicates[n] = pd.DataFrame()
    return raw, stats, duplicates

# PART 3: MASTER CONSTRUCTION
def build_master(raw):
    # Pre-process Finance
    for n in ["BP2JK", "Iemon", "Inaproc"]:
        df = raw[n]
        if not df.empty:
            if n == "BP2JK":
                if 'Pagu RAKL (Rp Ribu)' in df.columns:
                    df['p_c'] = clean_currency_vectorized(df['Pagu RAKL (Rp Ribu)']) * 1000
                elif 'Pagu Pengadaan (Rp Ribu)' in df.columns:
                    df['p_c'] = clean_currency_vectorized(df['Pagu Pengadaan (Rp Ribu)']) * 1000
                else:
                    df['p_c'] = 0.0

                nk_full = clean_currency_vectorized(df['Nilai Kontrak']) if 'Nilai Kontrak' in df.columns else pd.Series(0.0, index=df.index)
                nk_ribu = clean_currency_vectorized(df['Nilai Kontrak (Rp Ribu)']) * 1000 if 'Nilai Kontrak (Rp Ribu)' in df.columns else pd.Series(0.0, index=df.index)
                df['nk_c'] = nk_full.where(nk_full > 0, nk_ribu)
            elif n == "Iemon":
                df['p_c'] = clean_currency_vectorized(df['Pagu RAKL (Rp Ribu)']) * 1000 if 'Pagu RAKL (Rp Ribu)' in df.columns else 0.0
                df['nk_c'] = clean_currency_vectorized(df['Nilai Kontrak (Rp Ribu)']) * 1000 if 'Nilai Kontrak (Rp Ribu)' in df.columns else 0.0

    # Build Master
    internal_keys = []
    for n in ["BP2JK", "Iemon"]:
        if not raw[n].empty: internal_keys.append(raw[n][['SOURCE_KEY', 'ID SIRUP', 'Kode Paket']])
    
    if internal_keys:
        master_keys = pd.concat(internal_keys).drop_duplicates('SOURCE_KEY')
    else:
        master_keys = pd.DataFrame(columns=['SOURCE_KEY', 'ID SIRUP', 'Kode Paket'])
    
    master = master_keys.set_index('SOURCE_KEY')
    cols = ['Nama Paket', 'Unor', 'Satker', 'Pagu DIPA', 'Nilai Kontrak', 'Rekanan', 'Jenis Paket', 'Progres Paket', 'Metode EP', 'BP2JK', 'norm_name']
    for c in cols: master[c] = 0.0 if 'Pagu' in c or 'Nilai' in c else "None"
    
    for n in ["BP2JK", "Iemon"]:
        df = raw[n]
        if not df.empty:
            df_idx = df.set_index('SOURCE_KEY')
            for c in ['Nama Paket', 'Unor', 'Satker', 'BP2JK', 'Jenis Paket', 'norm_name']:
                if c in df_idx.columns: master[c].update(df_idx[c])
            if 'p_c' in df_idx.columns: master['Pagu DIPA'].update(df_idx['p_c'])
            if 'nk_c' in df_idx.columns: master['Nilai Kontrak'].update(df_idx['nk_c'])
            rek = 'Rekanan' if 'Rekanan' in df_idx.columns else ('Nama Rekanan' if 'Nama Rekanan' in df_idx.columns else None)
            if rek: master['Rekanan'].update(df_idx[rek])

    # Sync Inaproc
    ina = raw["Inaproc"]
    if not ina.empty:
        ina_sirup_map = ina.groupby('ID SIRUP').agg({'nk_c': 'sum', 'Nama Rekanan': lambda x: '; '.join(x.astype(str))}).to_dict('index')
        ina_name_map = ina.groupby('norm_name').agg({'nk_c': 'sum', 'Nama Rekanan': lambda x: '; '.join(x.astype(str))}).to_dict('index')
        
        def sync_row(row):
            sirup, name = str(row['ID SIRUP']), str(row['norm_name'])
            if sirup in ina_sirup_map and sirup not in ['nan', '', 'None']:
                return ina_sirup_map[sirup]['nk_c'], ina_sirup_map[sirup]['Nama Rekanan'], True, "SIRUP"
            if name in ina_name_map and name != "":
                return ina_name_map[name]['nk_c'], ina_name_map[name]['Nama Rekanan'], True, "Nama"
            return row['Nilai Kontrak'], row['Rekanan'], False, "None"

        sync_results = master.apply(sync_row, axis=1)
        master['Inaproc_NK'] = [x[0] for x in sync_results]; master['Inaproc_Rekanan'] = [x[1] for x in sync_results]
        master['Matched Inaproc'] = [x[2] for x in sync_results]; master['Match Method'] = [x[3] for x in sync_results]

    # Final Status
    bp_idx = raw["BP2JK"].set_index('SOURCE_KEY') if not raw["BP2JK"].empty else pd.DataFrame()
    ie_idx = raw["Iemon"].set_index('SOURCE_KEY') if not raw["Iemon"].empty else pd.DataFrame()

    def get_s(idx, row):
        if row.get('Matched Inaproc', False): return "Terkontrak", "Inaproc"
        if not bp_idx.empty and idx in bp_idx.index:
            v = bp_idx.loc[idx, 'Progres Paket'] if 'Progres Paket' in bp_idx.columns else None
            res = normalize_status(v, source='BP2JK')
            if res != "Belum Proses": return res, str(v)
        if not ie_idx.empty and idx in ie_idx.index:
            v = ie_idx.loc[idx, 'Status Kontrak'] if 'Status Kontrak' in ie_idx.columns else None
            res = normalize_status(v, source='Iemon')
            if res != "Belum Proses": return res, str(v)
        return "Belum Proses", "None"

    status_data = [get_s(i, r) for i, r in master.iterrows()]
    master['Progres Paket'] = [x[0] for x in status_data]; master['Raw Status'] = [x[1] for x in status_data]
    
    # Realisasi calculation
    master['Nilai Kontrak'] = master.apply(lambda x: x['Inaproc_NK'] if x.get('Matched Inaproc', False) else x['Nilai Kontrak'], axis=1)
    master['Rekanan'] = master.apply(lambda x: x['Inaproc_Rekanan'] if x.get('Matched Inaproc', False) else x['Rekanan'], axis=1)
    master['Alert'] = (master['Pagu DIPA'] >= 15e9) & (master['Progres Paket'] == 'Belum Proses')
    
    return master.reset_index()

# PART 4: UI AND SIDEBAR
with st.sidebar:
    st.title("⚙️ Cloud Setup")
    up_bp, up_ie, up_in = st.file_uploader("BP2JK", type="csv"), st.file_uploader("Iemon", type="csv"), st.file_uploader("Inaproc", type="csv")
    bypass = st.checkbox("Force Refresh Data", value=False)
    raw_data, stats, duplicates_data = load_and_process_all({"BP2JK": up_bp, "Iemon": up_ie, "Inaproc": up_in}, bypass_cache=bypass)
    master_df = build_master(raw_data)
    debug_mode = st.checkbox("🐞 Enable Finance Debug", value=True)
    menu = st.radio("MENU", ["🚀 Dashboard Utama", "🔍 Diagnostik Data"])

if debug_mode:
    st.info("🐞 **Cloud Finance Debug:** Gunakan tabel di bawah untuk melihat apakah angka terbaca benar.")
    for name, df in raw_data.items():
        if not df.empty:
            st.write(f"**Source: {name}** (Total Pagu: {format_idr(df['p_c'].sum() if 'p_c' in df.columns else 0)})")
            f_cols = [c for c in df.columns if any(k in c.upper() for k in ['PAGU', 'KONTRAK'])]
            if f_cols:
                check = df[f_cols].head(3).copy()
                for c in f_cols: check[f"CLEANED_{c}"] = clean_currency_vectorized(df[c].head(3))
                st.table(check)

if menu == "🚀 Dashboard Utama":
    st.markdown('<div class="header-wrapper"><div class="header-text"><h1>Dashboard Monitoring E-Purchasing (Cloud Optimized)</h1><p>TA. 2026 | Sektor PUPR</p></div></div>', unsafe_allow_html=True)
    if master_df.empty: st.warning("Data belum tersedia. Silakan cek koneksi Google Sheets.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        p, k = master_df['Pagu DIPA'].sum(), master_df['Nilai Kontrak'].sum()
        m1.metric("TOTAL PAGU DIPA", format_idr(p))
        m2.metric("REALISASI KONTRAK", format_idr(k), delta=f"{(k/p*100 if p>0 else 0):.1f}%")
        m3.metric("TOTAL PAKET", f"{len(master_df):,}")
        m4.metric("TERKONTRAK", f"{(master_df['Progres Paket']=='Terkontrak').sum():,}")
        
        st.markdown("---")
        st.subheader("📋 Daftar Paket Master")
        dv = master_df.copy()
        dv['Pagu DIPA'] = dv['Pagu DIPA'].apply(format_idr)
        dv['Nilai Kontrak'] = dv['Nilai Kontrak'].apply(format_idr)
        st.dataframe(dv[['ID SIRUP', 'Nama Paket', 'Unor', 'Progres Paket', 'Pagu DIPA', 'Nilai Kontrak', 'Rekanan']], use_container_width=True)

st.markdown("<center style='color: #94a3b8; padding: 2rem;'>Subdit Katalog | 2026</center>", unsafe_allow_html=True)
