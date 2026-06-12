# PART 1: IMPORTS AND CSS
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import re
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Dashboard Monev E-Purchasing 2026", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    :root {
        --primary: #1e40af;
        --secondary: #3b82f6;
        --accent: #fbbf24;
        --bg-main: #f8fafc;
        --text-dark: #1e293b;
        --text-light: #64748b;
        --white: #ffffff;
        --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    }

    .stApp { background-color: var(--bg-main); font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* Main Container Padding */
    .block-container { padding: 2rem 3rem !important; }

    /* Professional Header */
    .header-wrapper {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        padding: 2.5rem; border-radius: 20px; margin-bottom: 2.5rem; color: white;
        box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.3);
        position: relative; overflow: hidden;
    }
    .header-wrapper::after {
        content: ""; position: absolute; top: -50%; right: -10%; width: 300px; height: 300px;
        background: rgba(255,255,255,0.05); border-radius: 50%;
    }
    .header-text h1 { margin: 0; font-size: 2.2rem !important; font-weight: 800; letter-spacing: -1px; }
    .header-text p { margin: 0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.8; font-weight: 400; }

    /* Metric Cards Styling */
    div[data-testid="metric-container"] {
        background-color: var(--white); padding: 1.5rem !important; border-radius: 16px !important;
        box-shadow: var(--shadow) !important; border: 1px solid #f1f5f9 !important;
        transition: transform 0.2s ease;
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-5px); }
    div[data-testid="stMetricValue"] { color: var(--primary) !important; font-size: 1.8rem !important; font-weight: 700 !important; }
    div[data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: var(--text-light) !important; letter-spacing: 0.5px; font-weight: 600; }

    /* Custom Chart Card */
    .chart-card {
        background: var(--white); padding: 1.5rem; border-radius: 16px;
        box-shadow: var(--shadow); margin-bottom: 1.5rem; border: 1px solid #f1f5f9;
    }
    .chart-title { 
        color: var(--text-dark); font-weight: 700; margin-bottom: 1.2rem; 
        font-size: 1.1rem; display: flex; align-items: center; gap: 10px;
    }
    .chart-title::before {
        content: ""; display: inline-block; width: 4px; height: 18px; 
        background-color: var(--accent); border-radius: 2px;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        background-color: #e2e8f0; border-radius: 8px 8px 0 0; padding: 10px 20px;
        color: var(--text-light); font-weight: 600; transition: all 0.3s;
    }
    .stTabs [aria-selected="true"] { background-color: var(--primary) !important; color: white !important; }

    /* Dataframe Polish */
    .stDataFrame { border-radius: 12px; overflow: hidden; box-shadow: var(--shadow); }

    /* Sidebar Polish */
    section[data-testid="stSidebar"] { background-color: var(--white); border-right: 1px solid #e2e8f0; }
    .stSidebar [data-testid="stMarkdownContainer"] p { font-size: 0.95rem; }
    
    /* Footer */
    .footer { text-align: center; padding: 2rem; color: var(--text-light); font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

# PART 2: HELPERS AND FETCH LOGIC
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
    if any(x in s for x in ['BELUM PROSES', 'PERSIAPAN']): return "Belum Proses"
    return "Belum Proses"

def normalize_text(text):
    if pd.isna(text): return ""
    # Lowercase and remove all non-alphanumeric characters for fuzzy-ish matching
    return re.sub(r'[^a-zA-Z0-9]', '', str(text).lower())

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
            # More robust CSV reading
            df = pd.read_csv(src, skiprows=4, quotechar='"', on_bad_lines='warn', engine='python')
            df.columns = df.columns.str.strip()
            
            # 1. Flexible Column Detection
            def find_col(keywords):
                for c in df.columns:
                    if any(k.upper() in str(c).upper() for k in keywords): return c
                return None

            sirup_col = find_col(['SIRUP', 'KODE RUP', 'KODERUP'])
            kp_col = find_col(['KODE PAKET', 'KODEPAKET'])
            
            # 2. Extract and Clean IDs
            df['ID SIRUP'] = df[sirup_col].astype(str).str.strip().str.replace('.0','',regex=False) if sirup_col else 'MISSING'
            df['Kode Paket'] = df[kp_col].astype(str).str.strip() if kp_col else 'MISSING'
            
            # Standardize missing values
            invalid = ['nan', 'None', 'nan.0', '0', '-', '']
            df['ID SIRUP'] = df['ID SIRUP'].apply(lambda x: 'MISSING' if str(x).strip() in invalid else str(x).strip())
            df['Kode Paket'] = df['Kode Paket'].apply(lambda x: 'MISSING' if str(x).strip() in invalid else str(x).strip())

            # 3. Create SOURCE_KEY
            if n == "Inaproc":
                df['nk_c'] = clean_currency_vectorized(df['Nilai Kontrak'])
                rek_col = find_col(['REKANAN', 'NAMA REKANAN'])
                rek_val = df[rek_col].astype(str).str.strip() if rek_col else 'None'
                df['SOURCE_KEY'] = df['ID SIRUP'] + "_" + rek_val + "_" + df['nk_c'].astype(str)
            else:
                # Internal: Priority SIRUP + KP
                def make_key(r):
                    if r['ID SIRUP'] != 'MISSING' and r['Kode Paket'] != 'MISSING': return f"{r['ID SIRUP']}_{r['Kode Paket']}"
                    if r['Kode Paket'] != 'MISSING': return f"KP_{r['Kode Paket']}"
                    if r['ID SIRUP'] != 'MISSING': return f"SIRUP_{r['ID SIRUP']}"
                    return f"RAND_{np.random.randint(1000000, 9999999)}"
                df['SOURCE_KEY'] = df.apply(make_key, axis=1)
            
            # 4. Diagnostics: Capture Duplicates
            dup_mask = df.duplicated('SOURCE_KEY', keep=False)
            duplicates[n] = df[dup_mask].sort_values('SOURCE_KEY').copy()
            
            # 5. Deduplicate
            count_before = len(df)
            df = df.drop_duplicates('SOURCE_KEY', keep='last')
            
            if 'Nama Paket' in df.columns:
                df['norm_name'] = df['Nama Paket'].apply(normalize_text)
            
            raw[n], stats[n] = df, {"total": len(df), "before": count_before, "cols": list(df.columns)}
        except Exception as e:
            raw[n], stats[n] = pd.DataFrame(), {"total": 0, "before": 0, "error": str(e)}
            duplicates[n] = pd.DataFrame()
    return raw, stats, duplicates

# PART 3: MASTER CONSTRUCTION AND SIDEBAR
def build_master(raw):
    # 1. Pre-process Finance
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

    # 2. Build Master based on Union of Internal Data (BP2JK & Iemon)
    # We prioritize Internal Data as the foundation (The actual list of packages to be monitored)
    internal_keys = []
    for n in ["BP2JK", "Iemon"]:
        if not raw[n].empty: internal_keys.append(raw[n][['SOURCE_KEY', 'ID SIRUP', 'Kode Paket']])
    
    if internal_keys:
        master_keys = pd.concat(internal_keys).drop_duplicates('SOURCE_KEY')
    else:
        master_keys = pd.DataFrame(columns=['SOURCE_KEY', 'ID SIRUP', 'Kode Paket'])
    
    master = master_keys.set_index('SOURCE_KEY')
    
    # Initialize Columns
    cols = ['Nama Paket', 'Unor', 'Satker', 'Pagu DIPA', 'Nilai Kontrak', 'Rekanan', 'Jenis Paket', 'Progres Paket', 'Metode EP', 'BP2JK', 'norm_name']
    for c in cols: master[c] = 0.0 if 'Pagu' in c or 'Nilai' in c else "None"
    
    # 3. Fill Internal Data (Priority: BP2JK -> Iemon)
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

    # 4. Sinkronisasi dengan Inaproc
    ina = raw["Inaproc"]
    if not ina.empty:
        # Create a lookup for Inaproc by SIRUP
        ina_sirup_map = ina.groupby('ID SIRUP').agg({'nk_c': 'sum', 'Nama Rekanan': lambda x: '; '.join(x.astype(str))}).to_dict('index')
        # Create a lookup for Inaproc by Normalized Name
        ina_name_map = ina.groupby('norm_name').agg({'nk_c': 'sum', 'Nama Rekanan': lambda x: '; '.join(x.astype(str))}).to_dict('index')
        
        # Track matches
        master['Matched Inaproc'] = False
        master['Match Method'] = "None"

        def sync_row(row):
            sirup, name = str(row['ID SIRUP']), str(row['norm_name'])
            # Priority 1: SIRUP Match
            if sirup in ina_sirup_map and sirup not in ['nan', '', 'None']:
                return ina_sirup_map[sirup]['nk_c'], ina_sirup_map[sirup]['Nama Rekanan'], True, "SIRUP"
            # Priority 2: Name Match (Fallback)
            if name in ina_name_map and name != "":
                return ina_name_map[name]['nk_c'], ina_name_map[name]['Nama Rekanan'], True, "Nama"
            return row['Nilai Kontrak'], row['Rekanan'], False, "None"

        # Apply Sync
        sync_results = master.apply(sync_row, axis=1)
        master['Inaproc_NK'] = [x[0] for x in sync_results]
        master['Inaproc_Rekanan'] = [x[1] for x in sync_results]
        master['Matched Inaproc'] = [x[2] for x in sync_results]
        master['Match Method'] = [x[3] for x in sync_results]

    # 5. Final Status Logic
    bp_idx = raw["BP2JK"].set_index('SOURCE_KEY') if not raw["BP2JK"].empty else pd.DataFrame()
    ie_idx = raw["Iemon"].set_index('SOURCE_KEY') if not raw["Iemon"].empty else pd.DataFrame()

    def get_s(idx, row):
        if row.get('Matched Inaproc', False): return "Terkontrak", "Data Nasional (Inaproc)"
        # Check BP2JK
        if not bp_idx.empty and idx in bp_idx.index:
            v = bp_idx.loc[idx, 'Progres Paket'] if 'Progres Paket' in bp_idx.columns else (bp_idx.loc[idx, 'Status Kontrak'] if 'Status Kontrak' in bp_idx.columns else None)
            res = normalize_status(v, source='BP2JK')
            if res != "Belum Proses": return res, str(v)
        # Check Iemon
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
    
    # Realisasi calculation: use Inaproc value if matched, else use Internal value
    master['Nilai Kontrak'] = master.apply(lambda x: x['Inaproc_NK'] if x.get('Matched Inaproc', False) else x['Nilai Kontrak'], axis=1)
    master['Rekanan'] = master.apply(lambda x: x['Inaproc_Rekanan'] if x.get('Matched Inaproc', False) else x['Rekanan'], axis=1)
    
    # Flags for Diagnostics
    master['In BP2JK'] = master.index.isin(raw['BP2JK']['SOURCE_KEY']) if not raw['BP2JK'].empty else False
    master['In Iemon'] = master.index.isin(raw['Iemon']['SOURCE_KEY']) if not raw['Iemon'].empty else False
    master['In Inaproc'] = master.get('Matched Inaproc', False)
    
    # Alerting Logic: High Value (> 15M) and still "Belum Proses"
    master['Alert'] = (master['Pagu DIPA'] >= 15e9) & (master['Progres Paket'] == 'Belum Proses')
    
    return master.reset_index()

with st.sidebar:
    if os.path.exists("image/logo_kemenpu.png"): st.image("image/logo_kemenpu.png", use_container_width=True)
    st.markdown("---")
    with st.expander("🌐 Sumber Data"):
        up_bp, up_ie, up_in = st.file_uploader("BP2JK", type="csv"), st.file_uploader("Iemon", type="csv"), st.file_uploader("Inaproc", type="csv")
        bypass = st.checkbox("Bypass Cache (Force Refresh)", value=False)
    raw_data, stats, duplicates_data = load_and_process_all({"BP2JK": up_bp, "Iemon": up_ie, "Inaproc": up_in}, bypass_cache=bypass)
    master_df = build_master(raw_data)
    
    st.markdown("---")
    debug_mode = st.checkbox("🐞 Debug Mode (Lihat Raw Data)", value=False)
    
    menu = st.radio("MENU", ["🚀 Dashboard Utama", "📁 Data BP2JK", "📁 Data Iemon", "📁 Data Inaproc", "🔍 Diagnostik Data"])

if debug_mode:
    st.title("🐞 Debug: Raw Data Inspection")
    for name, df in raw_data.items():
        st.subheader(f"Raw Data: {name}")
        if not df.empty:
            st.write(f"Columns: {list(df.columns)}")
            st.dataframe(df.head(10))
        else:
            st.error(f"Data {name} Kosong!")
    st.markdown("---")

# PART 4: DASHBOARD UTAMA
if menu == "🚀 Dashboard Utama":
    st.markdown("""
        <div class="header-wrapper">
            <div class="header-text">
                <h1>Dashboard Monitoring E-Purchasing</h1>
                <p>Katalog Elektronik Sektoral Kementerian PUPR - Tahun Anggaran 2026</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if master_df.empty: st.warning("⚠️ Data kosong.")
    else:
        # Check if there are duplicates in any source
        has_duplicates = any(not df.empty for df in duplicates_data.values())
        if has_duplicates:
            st.warning("⚠️ **Peringatan:** Terdeteksi data duplikat pada sumber Google Sheet. Silakan cek menu **🔍 Diagnostik Data** untuk detailnya.")
        
        with st.expander("🔍 Filter Global", expanded=True):
            f1, f2, f3, f4 = st.columns(4)
            with f1: sel_u = st.multiselect("Filter Unor:", options=sorted(master_df['Unor'].unique()))
            with f2: sel_b = st.multiselect("Filter BP2JK:", options=sorted(master_df['BP2JK'].unique()))
            with f3: sel_j = st.multiselect("Filter Jenis Paket:", options=sorted(master_df['Jenis Paket'].unique()))
            with f4: sel_p = st.multiselect("Filter Progres:", options=['Belum Proses', 'Proses E-Purchasing', 'Persiapan Terkontrak', 'Terkontrak', 'Batal'])
            f5, f6 = st.columns(2)
            with f5: sel_m = st.multiselect("Filter Metode:", options=['Negosiasi', 'Minikompetisi', 'Belum Info'])
            with f6: sel_s = st.multiselect("Filter Skala Paket:", options=['>= 15M', '< 15M', 'Pagu Kosong (Rp 0)'])

        filtered = master_df.copy()
        def cls_sk(x):
            if x <= 0: return 'Pagu Kosong (Rp 0)'
            elif x >= 15e9: return '>= 15M'
            else: return '< 15M'
        filtered['tmp_skala'] = filtered['Pagu DIPA'].apply(cls_sk)
        if sel_u: filtered = filtered[filtered['Unor'].isin(sel_u)]
        if sel_b: filtered = filtered[filtered['BP2JK'].isin(sel_b)]
        if sel_j: filtered = filtered[filtered['Jenis Paket'].isin(sel_j)]
        if sel_p: filtered = filtered[filtered['Progres Paket'].isin(sel_p)]
        if sel_m: filtered = filtered[filtered['Metode EP'].isin(sel_m)]
        if sel_s: filtered = filtered[filtered['tmp_skala'].isin(sel_s)]

        m1, m2, m3, m4 = st.columns(4)
        p, k = filtered['Pagu DIPA'].sum(), filtered['Nilai Kontrak'].sum()
        with m1: st.metric("TOTAL PAGU DIPA", format_idr(p))
        with m2: st.metric("REALISASI KONTRAK", format_idr(k), delta=f"{(k/p*100 if p>0 else 0):.1f}%")
        with m3: st.metric("TOTAL PAKET UNIK", f"{len(filtered):,}")
        with m4: st.metric("PAKET TERKONTRAK", f"{(filtered['Progres Paket']=='Terkontrak').sum():,}")

# PART 5: CHARTS AND LIST VIEW
        t1, t2, t3 = st.tabs(["📊 ANALISIS VISUAL", "📋 DAFTAR PAKET MASTER", "🏢 ANALISIS REKANAN"])
        with t1:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown('<p class="chart-title">Jumlah Paket per Unor</p>', unsafe_allow_html=True)
                det = True if sel_u else st.session_state.get('s_det', False)
                sib = ['SEKJEN', 'ITJEN', 'BK', 'BPIW', 'BPSDM', 'PI']
                u_c = filtered['Unor'].apply(lambda x: "SIBBPI" if not det and str(x).upper() in sib else x).value_counts().reset_index()
                u_c.columns = ['U', 'V']
                h = 700 if det else 450
                fig_u = px.pie(u_c, values='V', names='U', height=h, hole=0.5, color_discrete_sequence=px.colors.qualitative.Prism)
                fig_u.update_traces(texttemplate='%{value}<br>%{percent:.1%}', textposition='auto', marker=dict(line=dict(color='#FFFFFF', width=2)))
                if det: fig_u.update_traces(domain=dict(x=[0.3, 0.9], y=[0.2, 0.8]))
                fig_u.update_layout(
                    legend=dict(orientation="v", y=1, x=0), 
                    annotations=[dict(text=f"<b>{len(filtered)}</b>", x=0.6 if det else 0.5, y=0.5, showarrow=False, font_size=24, font_family="Plus Jakarta Sans")],
                    margin=dict(t=0, b=0, l=0, r=0)
                )
                st.plotly_chart(fig_u, use_container_width=True)
                if not sel_u: st.checkbox("Tampilkan Detail SIBBPI", value=False, key='s_det')
                st.markdown('</div>', unsafe_allow_html=True)

            with c2:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown('<p class="chart-title">Progres Tahapan</p>', unsafe_allow_html=True)
                
                det_prog = st.session_state.get('s_det_prog', False)
                if det_prog:
                    display_filtered = filtered.copy()
                    display_filtered['Progres View'] = display_filtered.apply(
                        lambda x: x['Raw Status'] if x['Progres Paket'] in ['Persiapan Terkontrak', 'Proses E-Purchasing'] else x['Progres Paket'], 
                        axis=1
                    )
                    p_c = display_filtered['Progres View'].value_counts().reset_index()
                    names_col = 'Progres View'
                else:
                    p_c = filtered['Progres Paket'].value_counts().reset_index()
                    names_col = 'Progres Paket'
                
                fig_p = px.pie(
                    p_c, values='count', names=names_col, height=h, 
                    color=names_col, 
                    color_discrete_map={'Terkontrak':'#10b981','Batal':'#ef4444','Belum Proses':'#94a3b8','Proses E-Purchasing':'#3b82f6','Persiapan Terkontrak':'#8b5cf6'}
                )
                fig_p.update_traces(texttemplate='%{value} (%{percent:.1%})', textposition='auto', marker=dict(line=dict(color='#FFFFFF', width=2)))
                if det: fig_p.update_traces(domain=dict(x=[0.3, 0.9], y=[0.2, 0.8]))
                fig_p.update_layout(legend=dict(orientation="v", y=1, x=0), margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_p, use_container_width=True)
                st.checkbox("Tampilkan Detail Progres", value=False, key='s_det_prog')
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div style="height: 1.5rem;"></div>', unsafe_allow_html=True)
            c3, c4 = st.columns(2)
            with c3:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown('<p class="chart-title">Distribusi Jenis Paket</p>', unsafe_allow_html=True)
                j_c = filtered['Jenis Paket'].value_counts().reset_index()
                st.plotly_chart(px.bar(j_c, x='Jenis Paket', y='count', color='Jenis Paket', text_auto=True, height=400, color_discrete_sequence=px.colors.qualitative.Safe), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with c4:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown('<p class="chart-title">Metode E-Purchasing</p>', unsafe_allow_html=True)
                m_c = filtered['Metode EP'].value_counts().reset_index()
                st.plotly_chart(px.treemap(m_c, path=[px.Constant("Total"), 'Metode EP'], values='count', color='Metode EP', color_discrete_map={'Negosiasi':'#6366f1','Minikompetisi':'#ec4899','Belum Info':'#94a3b8'}, height=400), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            all_b = st.checkbox("Tampilkan Semua BP2JK", value=False)
            st.markdown('<p class="chart-title">Jumlah Paket per BP2JK</p>', unsafe_allow_html=True)
            b_c = filtered['BP2JK'].value_counts().reset_index()
            disp_b = b_c if all_b else b_c.head(10)
            fig_b = px.bar(disp_b, x='count', y='BP2JK', orientation='h', color='count', color_continuous_scale='Blues', text_auto=True)
            fig_b.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=max(400, len(disp_b)*30), margin=dict(t=20, b=20))
            st.plotly_chart(fig_b, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            dv = filtered.copy()
            # Add Alert Emoji for visual emphasis
            dv['Status Display'] = dv.apply(lambda x: "🚨 " + x['Progres Paket'] if x['Alert'] else x['Progres Paket'], axis=1)
            dv['Pagu DIPA'] = dv['Pagu DIPA'].apply(format_idr)
            dv['Nilai Kontrak'] = dv['Nilai Kontrak'].apply(format_idr)
            dv.insert(0, 'No.', range(1, len(dv)+1))
            st.dataframe(
                dv[['No.', 'ID SIRUP', 'Nama Paket', 'Unor', 'Status Display', 'Metode EP', 'Pagu DIPA', 'Nilai Kontrak', 'Rekanan']], 
                use_container_width=True, 
                height=600, 
                hide_index=True
            )
            if any(dv['Alert']):
                st.info("💡 **Catatan:** Paket dengan simbol 🚨 adalah paket dengan Pagu >= 15M namun masih berstatus 'Belum Proses'.")

        with t3:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown('<p class="chart-title">Analisis Konsentrasi Rekanan (Top 20)</p>', unsafe_allow_html=True)
            
            rek_df = filtered[filtered['Rekanan'] != 'None'].copy()
            if not rek_df.empty:
                rek_stats = rek_df.groupby('Rekanan').agg({
                    'SOURCE_KEY': 'count',
                    'Nilai Kontrak': 'sum'
                }).reset_index().rename(columns={'SOURCE_KEY': 'Jumlah Paket', 'Nilai Kontrak': 'Total Kontrak'})
                
                rek_stats = rek_stats.sort_values('Total Kontrak', ascending=False).head(20)
                rek_stats['Label'] = rek_stats['Total Kontrak'].apply(lambda x: f"{x/1e12:.2f} T" if x >= 1e12 else (f"{x/1e9:.2f} M" if x >= 1e9 else f"{x/1e6:.2f} J"))
                
                c_rek1, c_rek2 = st.columns([1, 1])
                with c_rek1:
                    fig_rek_val = px.bar(
                        rek_stats, y='Rekanan', x='Total Kontrak', 
                        orientation='h', title='Top 20 Rekanan Berdasarkan Nilai Kontrak',
                        color='Total Kontrak', color_continuous_scale='Viridis',
                        text='Label'
                    )
                    fig_rek_val.update_traces(textposition='outside')
                    fig_rek_val.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=600)
                    st.plotly_chart(fig_rek_val, use_container_width=True)
                
                with c_rek2:
                    fig_rek_count = px.treemap(
                        rek_stats, path=[px.Constant("Semua Rekanan"), 'Rekanan'], 
                        values='Jumlah Paket', color='Jumlah Paket',
                        color_continuous_scale='Blues',
                        title='Distribusi Volume Paket per Rekanan'
                    )
                    fig_rek_count.update_layout(height=600)
                    st.plotly_chart(fig_rek_count, use_container_width=True)
                
                st.markdown("---")
                st.subheader("Tabel Detail Rekanan")
                disp_rek = rek_stats.copy()
                disp_rek['Total Kontrak'] = disp_rek['Total Kontrak'].apply(format_idr)
                st.dataframe(disp_rek, use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada data rekanan/kontrak yang tersedia untuk difilter.")
            st.markdown('</div>', unsafe_allow_html=True)

# PART 6: EXTRA MENUS AND FOOTER
elif menu == "🔍 Diagnostik Data":
    st.title("🔍 Diagnostik Sinkronisasi")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("BP2JK", stats['BP2JK']['total'])
        st.caption(f"Raw Rows: {stats['BP2JK']['before']}")
    with c2:
        st.metric("Iemon", stats['Iemon']['total'])
        st.caption(f"Raw Rows: {stats['Iemon']['before']}")
    with c3:
        st.metric("Inaproc", stats['Inaproc']['total'])
        st.caption(f"Raw Rows: {stats['Inaproc']['before']}")
    c4.metric("TOTAL MASTER", len(master_df))
    gb, gi = master_df[~master_df['In BP2JK']].copy(), master_df[~master_df['In Iemon']].copy()
    gn = master_df[master_df['In Inaproc'] & (~master_df['In BP2JK'] | ~master_df['In Iemon'])].copy()
    gs = master_df[master_df['ID SIRUP'].str.contains('MISSING-', na=False)].copy()
    
    # Fix column name for name matching diagnostic
    gm = master_df[master_df['Match Method'] == "Nama"].copy()
    
    tg1, tg2, tg3, tg4, tg5, tg6, tg7 = st.tabs([
        f"❌ Belum Masuk BP2JK ({len(gb)})", 
        f"❌ Belum Masuk Iemon ({len(gi)})", 
        f"🌐 Gap Inaproc ({len(gn)})",
        f"⚠️ Perlu Perbaikan SIRUP ({len(gs)})",
        f"🔗 Cocok Nama ({len(gm)})",
        "👯 Duplikat ID",
        "📊 Skor Integritas"
    ])
    
    with tg1: gb.insert(0,'No.',range(1,len(gb)+1)); st.dataframe(gb[['No.','ID SIRUP','Nama Paket','Unor','Satker']], use_container_width=True, hide_index=True)
    with tg2: gi.insert(0,'No.',range(1,len(gi)+1)); st.dataframe(gi[['No.','ID SIRUP','Nama Paket','Unor','Satker']], use_container_width=True, hide_index=True)
    with tg3: gn.insert(0,'No.',range(1,len(gn)+1)); st.dataframe(gn[['No.','ID SIRUP','Nama Paket','Unor','In Inaproc','In BP2JK','In Iemon']], use_container_width=True, hide_index=True)
    with tg4: 
        st.warning("Daftar paket di bawah ini tidak memiliki ID SIRUP yang valid di data internal (BP2JK/Iemon).")
        gs.insert(0,'No.',range(1,len(gs)+1)); st.dataframe(gs[['No.','ID SIRUP','Kode Paket','Nama Paket','Unor','Satker']], use_container_width=True, hide_index=True)
    with tg5:
        st.info("Daftar paket yang berhasil disinkronkan dengan Inaproc menggunakan kesamaan NAMA PAKET (karena ID SIRUP kosong).")
        if not gm.empty:
            gm.insert(0,'No.',range(1,len(gm)+1))
            st.dataframe(gm[['No.','ID SIRUP','Nama Paket','Unor','Match Method']], use_container_width=True, hide_index=True)
        else:
            st.write("Tidak ada paket yang cocok melalui nama.")
    with tg6:
        st.info("Menampilkan baris data yang memiliki ID SIRUP ganda di sumber data Google Sheet. Baris ini menyebabkan perbedaan jumlah total antara Google Sheet dan Dashboard (karena dashboard hanya mengambil satu baris unik).")
        for src, df_dup in duplicates_data.items():
            if not df_dup.empty:
                st.subheader(f"Data Duplikat di {src} ({len(df_dup)} baris)")
                st.dataframe(df_dup, use_container_width=True, hide_index=True)
            else:
                st.success(f"✅ Tidak ada duplikat ID di {src}")
    
    with tg7:
        st.subheader("Data Integrity Scorecard")
        st.markdown("Analisis kualitas dan konsistensi data antar sumber (Internal vs Nasional).")
        
        # 1. Sync Rate Analysis
        total_terkontrak = (master_df['Progres Paket'] == 'Terkontrak').sum()
        sync_terkontrak = ((master_df['Progres Paket'] == 'Terkontrak') & (master_df['In Inaproc'])).sum()
        sync_rate = (sync_terkontrak / total_terkontrak * 100) if total_terkontrak > 0 else 0
        
        # 2. SIRUP Validity
        total_paket = len(master_df)
        valid_sirup = total_paket - len(gs)
        sirup_rate = (valid_sirup / total_paket * 100) if total_paket > 0 else 0
        
        # 3. Value Consistency (Internal vs Inaproc)
        matched = master_df[master_df['In Inaproc']].copy()
        # In build_master, Nilai Kontrak is already updated to Inaproc value if matched.
        # We need to look at raw data to compare. 
        # For simplicity in this display, let's use the 'Match Method' as a proxy for quality.
        nama_match_rate = (len(gm) / len(matched) * 100) if len(matched) > 0 else 0

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("Sync Rate (Inaproc)", f"{sync_rate:.1f}%")
            st.progress(sync_rate/100)
            st.caption("Persentase paket 'Terkontrak' yang terdata di Inaproc.")
        
        with sc2:
            st.metric("SIRUP Validity", f"{sirup_rate:.1f}%")
            st.progress(sirup_rate/100)
            st.caption("Persentase paket dengan ID SIRUP valid (bukan MISSING).")
            
        with sc3:
            st.metric("Match Quality", f"{100-nama_match_rate:.1f}%")
            st.progress((100-nama_match_rate)/100)
            st.caption("Persentase sinkronisasi menggunakan SIRUP (bukan Nama).")

        st.markdown("---")
        st.subheader("💡 Rekomendasi Perbaikan Data")
        if sync_rate < 80: st.warning("🔴 **Sync Rate Rendah**: Banyak paket sudah kontrak di internal tapi belum tayang/tercatat di Inaproc. Segera update data di aplikasi Katalog.")
        if sirup_rate < 95: st.error("🔴 **SIRUP Missing**: Terdapat paket tanpa ID SIRUP. Hal ini akan menghambat sinkronisasi otomatis.")
        if nama_match_rate > 10: st.info("🟡 **Match by Name**: Cukup banyak paket sinkron via Nama. Pastikan ID SIRUP diinput dengan benar untuk akurasi 100%.")
        if sync_rate >= 80 and sirup_rate >= 95: st.success("🟢 **Kualitas Data Baik**: Data secara umum sudah konsisten dan sinkron.")

else:
    src_n = menu.split(" ")[2]
    st.title(f"📄 Detail Data {src_n}")
    df_r = raw_data.get(src_n).copy()
    if not df_r.empty:
        df_r.insert(0, 'No.', range(1, len(df_r)+1))
        st.dataframe(df_r, use_container_width=True, height=600, hide_index=True)

st.markdown("---")
st.markdown("<center style='color: #94a3b8;'>Monitoring E-Purchasing TA.2026 | Subdit Katalog</center>", unsafe_allow_html=True)
