import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Set page config for a professional look
st.set_page_config(
    page_title="Dashboard Monev E-Purchasing 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Executive Look ---
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Executive Card Style for Metrics */
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 20px 25px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 5px solid #0046ad;
        transition: transform 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
    }
    
    /* Header styling */
    .main-header {
        font-size: 32px;
        font-weight: 800;
        color: #1e3a8a;
        margin-bottom: 0px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .sub-header {
        font-size: 18px;
        color: #64748b;
        margin-bottom: 30px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 10px 10px 0px 0px;
        gap: 1px;
        padding: 10px 20px;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stTabs [aria-selected="true"] {
        background-color: #0046ad !important;
        color: white !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Table hover effect */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# Helper functions
def clean_currency(val):
    if pd.isna(val) or val == "" or val == "-":
        return 0.0
    # Remove Rp, dots, and spaces
    clean = str(val).replace('Rp', '').replace('.', '').replace(',', '').strip()
    try:
        return float(clean)
    except:
        return 0.0

def format_idr(val):
    if val >= 1e12:
        return f"Rp {val/1e12:.2f} T"
    elif val >= 1e9:
        return f"Rp {val/1e9:.2f} M"
    else:
        return f"Rp {val:,.0f}"

# Live Data Sources from Google Sheets
URL_BP2JK = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=1807383381&single=true&output=csv"
URL_IEMON = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=881219520&single=true&output=csv"
URL_INAPROC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=189207385&single=true&output=csv"

@st.cache_data(ttl=600) # Cache for 10 minutes
def load_data():
    urls = {"BP2JK": URL_BP2JK, "Iemon": URL_IEMON, "Inaproc": URL_INAPROC}
    data = {}
    for name, url in urls.items():
        try:
            df = pd.read_csv(url, skiprows=4)
            df.columns = df.columns.str.strip()
            cols_to_drop = [c for c in df.columns if c.upper() == 'NO']
            if cols_to_drop:
                df = df.drop(columns=cols_to_drop)
            data[name] = df
        except Exception as e:
            st.error(f"Gagal memuat data {name}: {e}")
    return data

def process_master(data):
    if not data: return pd.DataFrame()
    
    # Financial Standardization
    if "Inaproc" in data:
        data["Inaproc"]['Nilai Kontrak Clean'] = data["Inaproc"]['Nilai Kontrak'].apply(clean_currency)
    if "Iemon" in data:
        data["Iemon"]['Nilai Kontrak Clean'] = data["Iemon"]['Nilai Kontrak (Rp Ribu)'].apply(clean_currency) * 1000
        data["Iemon"]['Pagu Clean'] = data["Iemon"]['Pagu RAKL (Rp Ribu)'].apply(clean_currency) * 1000
    if "BP2JK" in data:
        data["BP2JK"]['Nilai Kontrak AW'] = data["BP2JK"]['Nilai Kontrak'].apply(clean_currency)
        data["BP2JK"]['Nilai Kontrak V'] = data["BP2JK"]['Nilai Kontrak (Rp Ribu)'].apply(clean_currency) * 1000
        data["BP2JK"]['Nilai Kontrak Clean'] = data["BP2JK"]['Nilai Kontrak AW'].where(data["BP2JK"]['Nilai Kontrak AW'] > 0, data["BP2JK"]['Nilai Kontrak V'])
        data["BP2JK"]['Pagu Clean'] = data["BP2JK"]['Pagu RAKL (Rp Ribu)'].apply(clean_currency) * 1000

    all_codes = pd.concat([
        data['BP2JK']['Kode Paket'] if 'BP2JK' in data else pd.Series(),
        data['Iemon']['Kode Paket'] if 'Iemon' in data else pd.Series(),
        data['Inaproc']['Kode Paket'] if 'Inaproc' in data else pd.Series()
    ]).dropna().unique()
    
    master = pd.DataFrame({'Kode Paket': all_codes})
    lookup_bp2jk = data['BP2JK'].set_index('Kode Paket') if 'BP2JK' in data else pd.DataFrame()
    lookup_iemon = data['Iemon'].set_index('Kode Paket') if 'Iemon' in data else pd.DataFrame()
    lookup_inaproc = data['Inaproc'].set_index('Kode Paket') if 'Inaproc' in data else pd.DataFrame()

    def get_master_row(row):
        code = row['Kode Paket']
        pagu = kontrak = 0
        if code in lookup_iemon.index:
            p = lookup_iemon.loc[code, 'Pagu Clean']
            pagu = p.iloc[0] if isinstance(p, pd.Series) else p
        elif code in lookup_bp2jk.index:
            p = lookup_bp2jk.loc[code, 'Pagu Clean']
            pagu = p.iloc[0] if isinstance(p, pd.Series) else p

        if code in lookup_bp2jk.index:
            v = lookup_bp2jk.loc[code, 'Nilai Kontrak Clean']
            kontrak = v.iloc[0] if isinstance(v, pd.Series) else v
        if kontrak == 0 and code in lookup_iemon.index:
            v = lookup_iemon.loc[code, 'Nilai Kontrak Clean']
            kontrak = v.iloc[0] if isinstance(v, pd.Series) else v
        if kontrak == 0 and code in lookup_inaproc.index:
            v = lookup_inaproc.loc[code, 'Nilai Kontrak Clean']
            kontrak = v.iloc[0] if isinstance(v, pd.Series) else v
        return pd.Series([pagu, kontrak])

    master[['Pagu DIPA', 'Nilai Kontrak']] = master.apply(get_master_row, axis=1)
    info_source = pd.concat([
        data['Iemon'][['Kode Paket', 'Nama Paket', 'Unor', 'Satker']].drop_duplicates('Kode Paket') if 'Iemon' in data else pd.DataFrame(),
        data['BP2JK'][['Kode Paket', 'Nama Paket', 'Unor', 'Satker']].drop_duplicates('Kode Paket') if 'BP2JK' in data else pd.DataFrame(),
        data['Inaproc'][['Kode Paket', 'Nama Paket', 'Unor', 'Satker']].drop_duplicates('Kode Paket') if 'Inaproc' in data else pd.DataFrame()
    ]).drop_duplicates('Kode Paket').set_index('Kode Paket')
    
    master = master.join(info_source, on='Kode Paket')
    master['In BP2JK'] = master['Kode Paket'].isin(data['BP2JK']['Kode Paket']) if 'BP2JK' in data else False
    master['In Iemon'] = master['Kode Paket'].isin(data['Iemon']['Kode Paket']) if 'Iemon' in data else False
    master['In Inaproc'] = master['Kode Paket'].isin(data['Inaproc']['Kode Paket']) if 'Inaproc' in data else False
    return master

# --- UI Setup ---
data_raw = load_data()
master_df = process_master(data_raw)

with st.sidebar:
    st.markdown("<h1 style='color: #1e3a8a; font-size: 24px;'>🛡️ EP-Monev 2026</h1>", unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("MAIN MENU", ["🚀 Dashboard Utama", "📁 Data BP2JK", "📁 Data Iemon", "📁 Data Inaproc"])
    st.markdown("---")
    st.info(f"💡 Terakhir diperbarui: {pd.Timestamp.now().strftime('%H:%M:%S')}")

if menu == "🚀 Dashboard Utama":
    st.markdown('<p class="main-header">Master Monitoring E-Purchasing TA.2026</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Konsolidasi Data Nasional & Internal Subdit Katalog</p>', unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    total_pagu, total_kontrak = master_df['Pagu DIPA'].sum(), master_df['Nilai Kontrak'].sum()
    total_unique, sudah_kontrak = len(master_df), master_df['In Inaproc'].sum()

    with m1: st.metric("Anggaran Pagu DIPA", format_idr(total_pagu))
    with m2: st.metric("Realisasi Kontrak", format_idr(total_kontrak), delta=f"{(total_kontrak/total_pagu*100):.1f}% dari Pagu")
    with m3: st.metric("Total Paket Unik", f"{total_unique:,}")
    with m4: st.metric("Status Berkontrak", f"{sudah_kontrak:,}", delta=f"{total_unique - sudah_kontrak} Belum")

    tab1, tab2 = st.tabs(["📊 Analisis Grafik", "🔍 Eksplorasi Data Master"])
    
    with tab1:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("#### 🍰 Distribusi Pagu per Unor")
            unor_fin = master_df.groupby('Unor')['Pagu DIPA'].sum().reset_index()
            fig_unor = px.pie(unor_fin, values='Pagu DIPA', names='Unor', hole=0.5, color_discrete_sequence=px.colors.qualitative.Prism)
            st.plotly_chart(fig_unor, use_container_width=True)
        with col_c2:
            st.markdown("#### 📈 Paket per Sistem")
            sync_data = {'Sistem': ['BP2JK', 'Iemon', 'Inaproc'], 'Jumlah': [master_df['In BP2JK'].sum(), master_df['In Iemon'].sum(), master_df['In Inaproc'].sum()]}
            fig_sync = px.bar(sync_data, x='Sistem', y='Jumlah', color='Sistem', text_auto=True, color_discrete_sequence=['#0046ad', '#0095ff', '#ff9900'])
            st.plotly_chart(fig_sync, use_container_width=True)

    with tab2:
        st.markdown("#### 📋 Daftar Master Paket Terkonsolidasi")
        search = st.text_input("Cari Nama atau Kode Paket...", placeholder="Contoh: Jambo Aye")
        disp = master_df.copy()
        if search:
            disp = disp[disp['Nama Paket'].str.contains(search, case=False, na=False) | disp['Kode Paket'].str.contains(search, case=False, na=False)]
        
        disp = disp.reset_index(drop=True)
        disp.index = disp.index + 1
        disp['Pagu DIPA'] = disp['Pagu DIPA'].apply(format_idr)
        disp['Nilai Kontrak'] = disp['Nilai Kontrak'].apply(format_idr)
        disp = disp.rename(columns={'In BP2JK': '📁 BP2JK', 'In Iemon': '📁 Iemon', 'In Inaproc': '📑 Kontrak'})
        for col in ['📁 BP2JK', '📁 Iemon', '📑 Kontrak']:
            disp[col] = disp[col].apply(lambda x: "✅" if x else "❌")
        st.dataframe(disp, use_container_width=True, height=500)

else:
    source = menu.split(" ")[2]
    st.title(f"📄 Detail Transaksi {source}")
    df = data_raw.get(source).copy() if data_raw.get(source) is not None else None
    if df is not None:
        df = df.reset_index(drop=True)
        df.index = df.index + 1
        with st.expander("🛠️ Opsi Filter"):
            if 'Unor' in df.columns:
                sel_unor = st.multiselect("Filter Unor:", options=sorted(df['Unor'].unique().astype(str)))
                if sel_unor: df = df[df['Unor'].isin(sel_unor)]
        st.write(f"Total: **{len(df):,}** baris.")
        st.dataframe(df, use_container_width=True)

st.markdown("---")
st.markdown("<center style='color: #94a3b8;'>Monitoring E-Purchasing TA.2026 | Subdit Katalog</center>", unsafe_allow_html=True)
