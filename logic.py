import pandas as pd
import numpy as np
import streamlit as st
import re
from concurrent.futures import ThreadPoolExecutor

# --- CONSTANTS ---
URL_BP2JK = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=1807383381&single=true&output=csv"
URL_IEMON = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=881219520&single=true&output=csv"
URL_INAPROC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=189207385&single=true&output=csv"

# --- HELPER FUNCTIONS ---
def clean_currency_vectorized(series):
    if series is None or series.empty: return pd.Series(0.0)
    s = series.astype(str).str.replace('Rp','',regex=False).str.replace('.','',regex=False).str.replace(',','',regex=False).str.replace(' ','',regex=False).str.strip()
    return pd.to_numeric(s, errors='coerce').fillna(0.0)

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
    return "Belum Proses"

def normalize_text(text):
    if pd.isna(text): return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text).lower())

# --- DATA FETCHING & PROCESSING ---
@st.cache_data(ttl=600)
def load_and_process_all(files=None, bypass_cache=False):
    urls = {"BP2JK": URL_BP2JK, "Iemon": URL_IEMON, "Inaproc": URL_INAPROC}
    raw, stats, duplicates = {}, {}, {}
    
    def fetch_single(n, u):
        try:
            src = files[n] if (files and files.get(n)) else u
            df = pd.read_csv(src, skiprows=4, quotechar='"', on_bad_lines='warn', engine='python')
            df.columns = df.columns.str.strip()
            
            def find_col(keywords):
                for c in df.columns:
                    if any(k.upper() in str(c).upper() for k in keywords): return c
                return None

            sirup_col = find_col(['SIRUP', 'KODE RUP', 'KODERUP'])
            kp_col = find_col(['KODE PAKET', 'KODEPAKET'])
            
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
            df_dups = df[dup_mask].sort_values('SOURCE_KEY').copy()
            
            count_before = len(df)
            df = df.drop_duplicates('SOURCE_KEY', keep='last')
            
            if 'Nama Paket' in df.columns:
                df['norm_name'] = df['Nama Paket'].apply(normalize_text)
            
            return n, df, {"total": len(df), "before": count_before, "cols": list(df.columns)}, df_dups
        except Exception as e:
            return n, pd.DataFrame(), {"total": 0, "before": 0, "error": str(e)}, pd.DataFrame()

    with ThreadPoolExecutor() as executor:
        results = executor.map(lambda x: fetch_single(*x), urls.items())
    
    for n, df, s, d in results:
        raw[n], stats[n], duplicates[n] = df, s, d
        
    return raw, stats, duplicates

def build_master(raw):
    for n in ["BP2JK", "Iemon", "Inaproc"]:
        df = raw[n]
        if not df.empty:
            if n == "BP2JK":
                p_ribuan = clean_currency_vectorized(df['Pagu RAKL (Rp Ribu)']) * 1000 if 'Pagu RAKL (Rp Ribu)' in df.columns else 0.0
                df['p_c'] = p_ribuan
                nk_aw = clean_currency_vectorized(df['Nilai Kontrak']) if 'Nilai Kontrak' in df.columns else 0.0
                nk_v = clean_currency_vectorized(df['Nilai Kontrak (Rp Ribu)']) * 1000 if 'Nilai Kontrak (Rp Ribu)' in df.columns else 0.0
                df['nk_c'] = nk_aw.where(nk_aw > 0, nk_v)
            elif n == "Iemon":
                df['p_c'] = clean_currency_vectorized(df['Pagu RAKL (Rp Ribu)']) * 1000 if 'Pagu RAKL (Rp Ribu)' in df.columns else 0.0
                df['nk_c'] = clean_currency_vectorized(df['Nilai Kontrak (Rp Ribu)']) * 1000 if 'Nilai Kontrak (Rp Ribu)' in df.columns else 0.0

    internal_keys = []
    for n in ["BP2JK", "Iemon"]:
        if not raw[n].empty: internal_keys.append(raw[n][['SOURCE_KEY', 'ID SIRUP', 'Kode Paket']])
    
    master_keys = pd.concat(internal_keys).drop_duplicates('SOURCE_KEY') if internal_keys else pd.DataFrame(columns=['SOURCE_KEY', 'ID SIRUP', 'Kode Paket'])
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

    ina = raw["Inaproc"]
    if not ina.empty:
        ina_sirup_map = ina.groupby('ID SIRUP').agg({'nk_c': 'sum', 'Nama Rekanan': lambda x: '; '.join(x.astype(str))}).to_dict('index')
        ina_name_map = ina.groupby('norm_name').agg({'nk_c': 'sum', 'Nama Rekanan': lambda x: '; '.join(x.astype(str))}).to_dict('index')
        
        def sync_row(row):
            sirup, name = str(row['ID SIRUP']), str(row['norm_name'])
            if sirup in ina_sirup_map and sirup not in ['nan', '', 'None', 'MISSING']:
                return ina_sirup_map[sirup]['nk_c'], ina_sirup_map[sirup]['Nama Rekanan'], True, "SIRUP"
            if name in ina_name_map and name != "":
                return ina_name_map[name]['nk_c'], ina_name_map[name]['Nama Rekanan'], True, "Nama"
            return row['Nilai Kontrak'], row['Rekanan'], False, "None"

        sync_results = master.apply(sync_row, axis=1)
        master['Inaproc_NK'] = [x[0] for x in sync_results]
        master['Inaproc_Rekanan'] = [x[1] for x in sync_results]
        master['Matched Inaproc'] = [x[2] for x in sync_results]
        master['Match Method'] = [x[3] for x in sync_results]

    bp_idx = raw["BP2JK"].set_index('SOURCE_KEY') if not raw["BP2JK"].empty else pd.DataFrame()
    ie_idx = raw["Iemon"].set_index('SOURCE_KEY') if not raw["Iemon"].empty else pd.DataFrame()

    def get_s(idx, row):
        if row.get('Matched Inaproc', False): return "Terkontrak", "Data Nasional (Inaproc)"
        if not bp_idx.empty and idx in bp_idx.index:
            v = bp_idx.loc[idx, 'Progres Paket'] if 'Progres Paket' in bp_idx.columns else (bp_idx.loc[idx, 'Status Kontrak'] if 'Status Kontrak' in bp_idx.columns else None)
            res = normalize_status(v, source='BP2JK')
            if res != "Belum Proses": return res, str(v)
        if not ie_idx.empty and idx in ie_idx.index:
            v = ie_idx.loc[idx, 'Status Kontrak'] if 'Status Kontrak' in ie_idx.columns else None
            res = normalize_status(v, source='Iemon')
            if res != "Belum Proses": return res, str(v)
        return "Belum Proses", "Belum Ada Info Detail"

    def get_m(idx):
        for df in [bp_idx, ie_idx]:
            if not df.empty and idx in df.index:
                m_ep = str(df.loc[idx, 'Metode E-Purchasing']).upper() if 'Metode E-Purchasing' in df.columns else ""
                m_p = str(df.loc[idx, 'Metode Pemilihan']).upper() if 'Metode Pemilihan' in df.columns else ""
                if 'MINI' in m_ep or 'MINI' in m_p: return "Minikompetisi"
                if any(x in m_ep or x in m_p for x in ['NEGOSIASI', 'SURAT PESANAN', 'PURCHASING']): return "Negosiasi"
        return "Belum Info"

    status_data = [get_s(i, r) for i, r in master.iterrows()]
    master['Progres Paket'] = [x[0] for x in status_data]
    master['Raw Status'] = [x[1] for x in status_data]
    master['Metode EP'] = [get_m(i) for i in master.index]
    
    master['Nilai Kontrak'] = master.apply(lambda x: x['Inaproc_NK'] if x.get('Matched Inaproc', False) else x['Nilai Kontrak'], axis=1)
    master['Rekanan'] = master.apply(lambda x: x['Inaproc_Rekanan'] if x.get('Matched Inaproc', False) else x['Rekanan'], axis=1)
    
    master['In BP2JK'] = master.index.isin(raw['BP2JK']['SOURCE_KEY']) if not raw['BP2JK'].empty else False
    master['In Iemon'] = master.index.isin(raw['Iemon']['SOURCE_KEY']) if not raw['Iemon'].empty else False
    master['In Inaproc'] = master.get('Matched Inaproc', False)
    master['Alert'] = (master['Pagu DIPA'] >= 15e9) & (master['Progres Paket'] == 'Belum Proses')
    
    return master.reset_index()
