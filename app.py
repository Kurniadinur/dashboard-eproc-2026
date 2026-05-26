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
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Table styling */
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
    # Clean IDR format
    clean = str(val).replace('Rp', '').replace('.', '').replace(',', '').replace(' ', '').strip()
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

def normalize_status(status_str, source=None):
    if pd.isna(status_str) or status_str == "" or str(status_str).upper() == "NONE":
        return "Belum Proses"
    
    s = str(status_str).upper()
    
    # 1. Terkontrak
    if any(x in s for x in ['TERKONTRAK', 'SELESAI KONTRAK']):
        return "Terkontrak"
    
    # 2. Batal
    if 'BATAL' in s:
        return "Batal"
    
    # 3. Persiapan Terkontrak
    # Ralat User: Untuk BP2JK, 'PROSES KONTRAK' masuk sini.
    if 'PERSIAPAN TERKONTRAK' in s or (source == 'BP2JK' and 'PROSES KONTRAK' in s):
        return "Persiapan Terkontrak"
    
    # 4. Proses E-Purchasing
    # Ralat User: Untuk Iemon, 'PROSES KONTRAK' masuk sini.
    keywords_proses = ['PEMASUKAN PENAWARAN', 'PROSES EVALUASI', 'REVIEW TIMLIT', 'PROSES PENETAPAN PEMENANG']
    if any(x in s for x in keywords_proses) or (source != 'BP2JK' and 'PROSES KONTRAK' in s):
        return "Proses E-Purchasing"
    
    # 5. Belum Proses (Termasuk kata 'Persiapan' saja tanpa 'Terkontrak')
    if any(x in s for x in ['BELUM PROSES', 'PERSIAPAN']):
        return "Belum Proses"
    
    return "Belum Proses"

# Live Data Sources
URL_BP2JK = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=1807383381&single=true&output=csv"
URL_IEMON = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=881219520&single=true&output=csv"
URL_INAPROC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=189207385&single=true&output=csv"

@st.cache_data(ttl=600)
def load_and_process_all(uploaded_files=None):
    urls = {"BP2JK": URL_BP2JK, "Iemon": URL_IEMON, "Inaproc": URL_INAPROC}
    raw_data = {}
    stats = {}
    
    for name, url in urls.items():
        source = uploaded_files[name] if (uploaded_files and uploaded_files.get(name)) else url
        try:
            df = pd.read_csv(source, skiprows=4)
            df.columns = df.columns.str.strip()
            
            # MANDATORY: Clean IDs and Deduplicate
            if 'Kode Paket' in df.columns:
                df['Kode Paket'] = df['Kode Paket'].astype(str).str.strip()
                df = df[df['Kode Paket'] != 'nan']
                df = df.drop_duplicates('Kode Paket', keep='last')
            
            raw_data[name] = df
            stats[name] = len(df)
        except Exception:
            raw_data[name] = pd.DataFrame()
            stats[name] = 0

    # --- Pre-processing Finance ---
    if not raw_data["BP2JK"].empty:
        df = raw_data["BP2JK"]
        df['Nilai Kontrak AW'] = df['Nilai Kontrak'].apply(clean_currency) if 'Nilai Kontrak' in df.columns else 0.0
        df['Nilai Kontrak V'] = df['Nilai Kontrak (Rp Ribu)'].apply(clean_currency) * 1000 if 'Nilai Kontrak (Rp Ribu)' in df.columns else 0.0
        df['Nilai Kontrak Clean'] = df['Nilai Kontrak AW'].where(df['Nilai Kontrak AW'] > 0, df['Nilai Kontrak V'])
        df['Pagu Clean'] = df['Pagu RAKL (Rp Ribu)'].apply(clean_currency) * 1000 if 'Pagu RAKL (Rp Ribu)' in df.columns else 0.0
        df['Pagu Pengadaan Clean'] = df['Pagu Pengadaan (Rp Ribu)'].apply(clean_currency) * 1000 if 'Pagu Pengadaan (Rp Ribu)' in df.columns else 0.0

    if not raw_data["Iemon"].empty:
        df = raw_data["Iemon"]
        df['Nilai Kontrak Clean'] = df['Nilai Kontrak (Rp Ribu)'].apply(clean_currency) * 1000 if 'Nilai Kontrak (Rp Ribu)' in df.columns else 0.0
        df['Pagu Clean'] = df['Pagu RAKL (Rp Ribu)'].apply(clean_currency) * 1000 if 'Pagu RAKL (Rp Ribu)' in df.columns else 0.0
        df['Pagu Pengadaan Clean'] = df['Pagu Pengadaan (Rp Ribu)'].apply(clean_currency) * 1000 if 'Pagu Pengadaan (Rp Ribu)' in df.columns else 0.0

    if not raw_data["Inaproc"].empty:
        df = raw_data["Inaproc"]
        df['Nilai Kontrak Clean'] = df['Nilai Kontrak'].apply(clean_currency) if 'Nilai Kontrak' in df.columns else 0.0

    # --- Build Master (Union of all Kode Paket) ---
    all_codes = pd.concat([raw_data[n]['Kode Paket'] for n in raw_data if not raw_data[n].empty]).dropna().unique()
    
    final_columns = ['Kode Paket', 'Nama Paket', 'Unor', 'Satker', 'Pagu DIPA', 'Nilai Kontrak', 
                     'Pagu Pengadaan', 'Rekanan', 'Jenis Paket', 'Progres Paket', 'BP2JK', 
                     'In BP2JK', 'In Iemon', 'In Inaproc']
    
    if len(all_codes) == 0:
        return raw_data, pd.DataFrame(columns=final_columns), stats

    master = pd.DataFrame({'Kode Paket': all_codes})
    for col in final_columns:
        if col not in master.columns:
            master[col] = 0.0 if col in ['Pagu DIPA', 'Nilai Kontrak', 'Pagu Pengadaan'] else (False if 'In ' in col else "None")

    master.set_index('Kode Paket', inplace=True)
    
    # Fill Data (Priority: Iemon -> BP2JK -> Inaproc)
    for name in ["Inaproc", "BP2JK", "Iemon"]:
        df = raw_data[name]
        if not df.empty:
            df_src = df.set_index('Kode Paket')
            # Basic Info
            for c in ['Nama Paket', 'Unor', 'Satker', 'BP2JK', 'Jenis Paket']:
                if c in df_src.columns: master.update(df_src[[c]])
            # Finance
            if 'Pagu Clean' in df_src.columns: master.update(df_src[['Pagu Clean']].rename(columns={'Pagu Clean':'Pagu DIPA'}))
            if 'Pagu Pengadaan Clean' in df_src.columns: master.update(df_src[['Pagu Pengadaan Clean']].rename(columns={'Pagu Pengadaan Clean':'Pagu Pengadaan'}))
            if 'Nilai Kontrak Clean' in df_src.columns: master.update(df_src[['Nilai Kontrak Clean']].rename(columns={'Nilai Kontrak Clean':'Nilai Kontrak'}))
            # Rekanan
            rek_col = 'Rekanan' if 'Rekanan' in df_src.columns else ('Nama Rekanan' if 'Nama Rekanan' in df_src.columns else None)
            if rek_col: master.update(df_src[[rek_col]].rename(columns={rek_col:'Rekanan'}))

    # --- Status Logic (Inaproc > BP2JK > Iemon) ---
    in_inaproc = set(raw_data["Inaproc"]['Kode Paket']) if not raw_data["Inaproc"].empty else set()

    def calc_status(kp):
        # 1. Inaproc (Data Transaksi Riil)
        if kp in in_inaproc: return "Terkontrak"
        
        # 2. BP2JK (Prioritas: Progres Paket)
        if kp in raw_data["BP2JK"].set_index('Kode Paket').index:
            df_bp = raw_data["BP2JK"].set_index('Kode Paket')
            v_progres = df_bp.loc[kp, 'Progres Paket'] if 'Progres Paket' in df_bp.columns else None
            v_status = df_bp.loc[kp, 'Status Kontrak'] if 'Status Kontrak' in df_bp.columns else None
            
            if not pd.isna(v_progres) and str(v_progres).strip() != "":
                st_norm = normalize_status(v_progres, source='BP2JK')
                if st_norm != "Belum Proses": return st_norm
            
            if not pd.isna(v_status) and str(v_status).strip() != "":
                st_norm = normalize_status(v_status, source='BP2JK')
                if st_norm != "Belum Proses": return st_norm
        
        # 3. Iemon (Prioritas: Status Kontrak)
        if kp in raw_data["Iemon"].set_index('Kode Paket').index:
            df_ie = raw_data["Iemon"].set_index('Kode Paket')
            v_status = df_ie.loc[kp, 'Status Kontrak'] if 'Status Kontrak' in df_ie.columns else None
            
            if not pd.isna(v_status) and str(v_status).strip() != "":
                st_norm = normalize_status(v_status, source='Iemon')
                if st_norm != "Belum Proses": return st_norm

        return "Belum Proses"

    master['Progres Paket'] = [calc_status(i) for i in master.index]
    master['In BP2JK'] = master.index.isin(raw_data['BP2JK']['Kode Paket']) if not raw_data['BP2JK'].empty else False
    master['In Iemon'] = master.index.isin(raw_data['Iemon']['Kode Paket']) if not raw_data['Iemon'].empty else False
    master['In Inaproc'] = master.index.isin(in_inaproc)
    
    master.reset_index(inplace=True)
    return raw_data, master[final_columns], stats

# --- UI Setup ---
with st.sidebar:
    st.markdown("<h1 style='color: #1e3a8a; font-size: 24px;'>🛡️ EP-Monev 2026</h1>", unsafe_allow_html=True)
    with st.expander("🌐 Opsi Sumber Data", expanded=False):
        st.write("Upload CSV jika online gagal:")
        up_bp = st.file_uploader("CSV BP2JK", type="csv")
        up_ie = st.file_uploader("CSV Iemon", type="csv")
        up_in = st.file_uploader("CSV Inaproc", type="csv")
    uploaded_dict = {"BP2JK": up_bp, "Iemon": up_ie, "Inaproc": up_in}
    st.markdown("---")
    menu = st.radio("MAIN MENU", ["🚀 Dashboard Utama", "📁 Data BP2JK", "📁 Data Iemon", "📁 Data Inaproc", "🔍 Diagnostik Data"])
    st.markdown("---")

data_raw, master_df, data_stats = load_and_process_all(uploaded_dict)

if menu == "🚀 Dashboard Utama":
    st.markdown('<p class="main-header">Master Monitoring E-Purchasing TA.2026</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Konsolidasi Data Nasional & Internal Subdit Katalog</p>', unsafe_allow_html=True)
    
    if master_df.empty:
        st.warning("⚠️ Data kosong. Harap periksa koneksi atau upload CSV.")
    else:
        with st.expander("🔍 Filter Global", expanded=True):
            f1, f2, f3, f4 = st.columns(4)
            with f1: sel_unor = st.multiselect("Filter Unor:", options=sorted(master_df['Unor'].unique()))
            with f2: sel_bp2jk = st.multiselect("Filter BP2JK:", options=sorted(master_df['BP2JK'].unique()))
            with f3: sel_jenis = st.multiselect("Filter Jenis Paket:", options=sorted(master_df['Jenis Paket'].unique()))
            with f4: sel_progres = st.multiselect("Filter Progres:", options=['Belum Proses', 'Proses E-Purchasing', 'Persiapan Terkontrak', 'Terkontrak', 'Batal'])
            
            # Checkbox Dinamis: Sembunyikan jika filter Unor digunakan
            if not sel_unor:
                show_detail_sib = st.checkbox("Tampilkan Detail SIBBPI (Sekjen, Itjen, BK, BPIW, BPSDM, PI)", value=False)
            else:
                show_detail_sib = True # Selalu tampilkan detail jika user memfilter manual

        filtered = master_df.copy()
        
        # Logika Pengelompokan Unor untuk Grafik
        sib_list = ['SEKJEN', 'ITJEN', 'BK', 'BPIW', 'BPSDM', 'PI']
        def group_unor(u):
            if not show_detail_sib and str(u).upper() in sib_list:
                return "SIBBPI"
            return u
        
        filtered['Unor Visual'] = filtered['Unor'].apply(group_unor)

        if sel_unor: filtered = filtered[filtered['Unor'].isin(sel_unor)]
        if sel_bp2jk: filtered = filtered[filtered['BP2JK'].isin(sel_bp2jk)]
        if sel_jenis: filtered = filtered[filtered['Jenis Paket'].isin(sel_jenis)]
        if sel_progres: filtered = filtered[filtered['Progres Paket'].isin(sel_progres)]

        m1, m2, m3, m4 = st.columns(4)
        pagu, kontrak = filtered['Pagu DIPA'].sum(), filtered['Nilai Kontrak'].sum()
        with m1: st.metric("Pagu DIPA", format_idr(pagu))
        with m2: st.metric("Realisasi Kontrak", format_idr(kontrak), delta=f"{(kontrak/pagu*100 if pagu>0 else 0):.1f}%")
        with m3: st.metric("Total Paket Unik", f"{len(filtered):,}")
        with m4: st.metric("Terkontrak", f"{(filtered['Progres Paket']=='Terkontrak').sum():,}")

        tab1, tab2 = st.tabs(["📊 Analisis Grafik", "📋 Tabel Master"])
        with tab1:
            # Row 1: Pie Charts
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### Jumlah Paket per Unor")
                unor_counts = filtered['Unor Visual'].value_counts().reset_index()
                unor_counts.columns = ['Unor Visual', 'Jumlah Paket']
                fig_unor = px.pie(unor_counts, values='Jumlah Paket', names='Unor Visual', height=350, hole=0.5)
                # Jumlah di atas, Persentase di bawah
                fig_unor.update_traces(
                    texttemplate='%{value}<br>%{percent:.2%}', 
                    textposition='auto',
                    insidetextorientation='horizontal'
                )
                fig_unor.update_layout(
                    uniformtext_minsize=9, 
                    uniformtext_mode='hide',
                    margin=dict(t=30, b=30, l=0, r=0),
                    legend=dict(font=dict(size=10)),
                    annotations=[dict(text=f"<b>{len(filtered):,}</b>", x=0.5, y=0.5, font_size=24, showarrow=False, font_color="#1e3a8a")]
                )
                st.plotly_chart(fig_unor, use_container_width=True)
            with c2:
                st.markdown("#### Progres Tahapan")
                order = ['Belum Proses', 'Proses E-Purchasing', 'Persiapan Terkontrak', 'Terkontrak', 'Batal']
                # Hitung jumlah paket per kategori
                counts = filtered['Progres Paket'].value_counts().reset_index()
                counts.columns = ['Progres Paket', 'count']
                
                # Filter hanya kategori yang ada datanya (> 0)
                counts = counts[counts['count'] > 0]
                
                # Urutkan berdasarkan urutan logis yang diinginkan (hanya yang tersedia)
                counts['sort_order'] = counts['Progres Paket'].apply(lambda x: order.index(x) if x in order else 99)
                counts = counts.sort_values('sort_order').drop('sort_order', axis=1)

                fig_prog = px.pie(counts, values='count', names='Progres Paket', color='Progres Paket', height=350,
                                       color_discrete_map={
                                           'Belum Proses':'#94a3b8',
                                           'Proses E-Purchasing':'#fbbf24',
                                           'Persiapan Terkontrak':'#38bdf8',
                                           'Terkontrak':'#22c55e',
                                           'Batal':'#ef4444'
                                       })
                # Jumlah + Persentase 2 desimal
                fig_prog.update_traces(
                    texttemplate='%{value} (%{percent:.2%})', 
                    textposition='auto',
                    insidetextorientation='horizontal'
                )
                fig_prog.update_layout(
                    uniformtext_minsize=9, 
                    uniformtext_mode='hide',
                    margin=dict(t=30, b=30, l=0, r=0),
                    legend=dict(font=dict(size=10))
                )
                st.plotly_chart(fig_prog, use_container_width=True)
            
            # Row 2: Bar Charts
            st.markdown("---")
            c3, c4 = st.columns(2)
            with c3:
                st.markdown("#### Top 10 BP2JK (Jumlah Paket)")
                top_bp = filtered['BP2JK'].value_counts().head(10).reset_index()
                top_bp.columns = ['BP2JK', 'Jumlah Paket']
                fig_bp = px.bar(top_bp, x='Jumlah Paket', y='BP2JK', orientation='h', 
                                color='Jumlah Paket', color_continuous_scale='Blues',
                                text='Jumlah Paket')
                fig_bp.update_traces(textposition='outside')
                fig_bp.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                st.plotly_chart(fig_bp, use_container_width=True)
                
            with c4:
                st.markdown("#### Distribusi Jenis Paket")
                jenis_counts = filtered['Jenis Paket'].value_counts().reset_index()
                jenis_counts.columns = ['Jenis Paket', 'Jumlah Paket']
                fig_jenis = px.bar(jenis_counts, x='Jenis Paket', y='Jumlah Paket', 
                                   color='Jenis Paket', color_discrete_sequence=px.colors.qualitative.Safe,
                                   text='Jumlah Paket')
                fig_jenis.update_traces(textposition='outside')
                st.plotly_chart(fig_jenis, use_container_width=True)

        with tab2:
            search = st.text_input("Cari Paket...")
            disp = filtered.copy()
            if search: disp = disp[disp['Nama Paket'].str.contains(search, case=False, na=False) | disp['Kode Paket'].str.contains(search, case=False, na=False)]
            disp_view = disp.copy()
            disp_view['Pagu DIPA'] = disp_view['Pagu DIPA'].apply(format_idr)
            disp_view['Nilai Kontrak'] = disp_view['Nilai Kontrak'].apply(format_idr)
            for c in ['In BP2JK', 'In Iemon', 'In Inaproc']: disp_view[c] = disp_view[c].apply(lambda x: "✅" if x else "❌")
            st.dataframe(disp_view[['Kode Paket', 'Nama Paket', 'Unor', 'Progres Paket', 'Pagu DIPA', 'Nilai Kontrak', 'Rekanan', 'In BP2JK', 'In Iemon', 'In Inaproc']], use_container_width=True, height=600)

elif menu == "🔍 Diagnostik Data":
    st.title("🔍 Diagnostik Konsolidasi Data")
    st.write("Gunakan halaman ini untuk memverifikasi apakah jumlah paket unik sudah benar.")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Paket BP2JK", f"{data_stats['BP2JK']:,}")
    col2.metric("Paket Iemon", f"{data_stats['Iemon']:,}")
    col3.metric("Paket Inaproc", f"{data_stats['Inaproc']:,}")
    col4.metric("TOTAL MASTER (UNIK)", f"{len(master_df):,}")
    
    st.info("""
    **Catatan Perhitungan:**
    - **Total Master (Unik)** adalah gabungan (*union*) dari semua Kode Paket yang ada di ketiga sistem.
    - Jika paket yang sama ada di BP2JK dan Iemon, maka hanya dihitung **1 kali**.
    - Jika ada perbedaan penulisan Kode Paket (misal beda spasi), sistem akan mendeteksinya sebagai paket yang berbeda.
    """)
    
    if not master_df.empty:
        st.subheader("Sampel Data Master")
        st.dataframe(master_df.head(20))

else:
    source_name = menu.split(" ")[2]
    st.title(f"📄 Detail {source_name}")
    df = data_raw.get(source_name)
    if df is not None and not df.empty:
        st.write(f"Total: {len(df):,} baris.")
        st.dataframe(df, use_container_width=True, height=600)
    else:
        st.warning("Data tidak tersedia.")

st.markdown("---")
st.markdown("<center style='color: #94a3b8;'>Monitoring E-Purchasing TA.2026 | Subdit Katalog</center>", unsafe_allow_html=True)
