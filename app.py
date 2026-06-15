# PART 1: IMPORTS AND CSS
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Dashboard Monev E-Purchasing 2026", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
    .block-container { max-width: 98% !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    .header-container {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 2rem; border-radius: 15px; margin-bottom: 2rem; color: white;
        box-shadow: 0 4px 15px rgba(30, 58, 138, 0.2); display: flex; flex-direction: column; gap: 0.5rem;
    }
    .header-text h1 { margin: 0; font-size: clamp(1.2rem, 4vw, 2rem) !important; font-weight: 800; letter-spacing: -0.5px; }
    .header-text p { margin: 0; font-size: clamp(0.8rem, 2vw, 1rem); opacity: 0.9; }
    div[data-testid="metric-container"] {
        background-color: white; padding: 1.2rem !important; border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important; border-bottom: 5px solid #FFCC00 !important;
    }
    div[data-testid="stMetricValue"] { color: #1e3a8a !important; font-size: clamp(1.8rem, 5vw, 2.8rem) !important; font-weight: 800 !important; line-height: 1.1; }
    div[data-testid="stMetricLabel"] { font-size: 0.9rem !important; text-transform: uppercase; font-weight: 700; color: #64748b !important; letter-spacing: 0.5px; }
    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    .chart-title { color: #1e3a8a; font-weight: 700; margin-bottom: 1.5rem; border-left: 5px solid #FFCC00; padding-left: 15px; font-size: clamp(1rem, 2vw, 1.2rem); }
    .stDataFrame { border: 1px solid #e2e8f0; border-radius: 12px; }
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

def normalize_status_vectorized(series, source=None):
    s = series.astype(str).str.upper()
    res = pd.Series("Belum Proses", index=series.index)
    
    cond_terkontrak = s.str.contains('TERKONTRAK|SELESAI KONTRAK', na=False)
    cond_batal = s.str.contains('BATAL', na=False)
    
    if source == 'BP2JK':
        cond_persiapan = s.str.contains('PERSIAPAN TERKONTRAK|PROSES KONTRAK', na=False)
        cond_proses = s.str.contains('PEMASUKAN PENAWARAN|PROSES EVALUASI|REVIEW TIMLIT|PROSES PENETAPAN PEMENANG', na=False)
    else:
        cond_persiapan = s.str.contains('PERSIAPAN TERKONTRAK', na=False)
        cond_proses = s.str.contains('PEMASUKAN PENAWARAN|PROSES EVALUASI|REVIEW TIMLIT|PROSES PENETAPAN PEMENANG|PROSES KONTRAK', na=False)

    res = np.where(cond_terkontrak, "Terkontrak",
          np.where(cond_batal, "Batal",
          np.where(cond_persiapan, "Persiapan Terkontrak",
          np.where(cond_proses, "Proses E-Purchasing", "Belum Proses"))))
    
    res[series.isna() | (s == "") | (s == "NONE") | (s == "NAN")] = "Belum Proses"
    return res

URL_BP2JK = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=1807383381&single=true&output=csv"
URL_IEMON = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=881219520&single=true&output=csv"
URL_INAPROC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=189207385&single=true&output=csv"

@st.cache_data(ttl=600)
def load_and_process_all(files=None):
    urls = {"BP2JK": URL_BP2JK, "Iemon": URL_IEMON, "Inaproc": URL_INAPROC}
    
    def process_source(name, url):
        src = files[name] if (files and files.get(name)) else url
        try:
            df = pd.read_csv(src, skiprows=4)
            df.columns = df.columns.str.strip()
            sirup_col = next((c for c in df.columns if 'SIRUP' in c.upper() or 'KODE RUP' in c.upper()), None)
            
            dupes = pd.DataFrame()
            if sirup_col:
                df['ID SIRUP'] = df[sirup_col].astype(str).str.strip().str.replace('.0','',regex=False)
                invalid_ids = ['', 'nan', 'None', '0', '-', 'nan.0']
                
                # Identifikasi Duplikat SEBELUM di-drop
                mask_valid_sirup = ~df['ID SIRUP'].isin(invalid_ids)
                dupes = df[mask_valid_sirup & df.duplicated('ID SIRUP', keep=False)].copy()
                
                if 'Kode Paket' in df.columns:
                    df['Kode Paket'] = df['Kode Paket'].astype(str).str.strip()
                    mask_invalid = df['ID SIRUP'].isin(invalid_ids)
                    df['ID SIRUP'] = np.where(mask_invalid, "MISSING-" + df['Kode Paket'], df['ID SIRUP'])
                else:
                    df = df[~df['ID SIRUP'].isin(invalid_ids)]
                
                df = df.drop_duplicates('ID SIRUP', keep='last')
            
            if 'Kode Paket' in df.columns and 'ID SIRUP' not in df.columns:
                df['Kode Paket'] = df['Kode Paket'].astype(str).str.strip()
                
            return name, df, dupes
        except:
            return name, pd.DataFrame(), pd.DataFrame()

    raw, stats, all_dupes = {}, {}, {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(lambda x: process_source(*x), urls.items()))
    
    for name, df, dupes in results:
        raw[name], stats[name], all_dupes[name] = df, len(df), dupes
        
    return raw, stats, all_dupes

# PART 3: MASTER CONSTRUCTION AND SIDEBAR
def build_master(raw):
    d_proc = {}
    for n in ["Inaproc", "BP2JK", "Iemon"]:
        df = raw[n].copy()
        if df.empty or 'ID SIRUP' not in df.columns:
            d_proc[n] = pd.DataFrame(columns=['ID SIRUP'])
            continue
        if n == "BP2JK":
            p_ribuan = clean_currency_vectorized(df['Pagu RAKL (Rp Ribu)']) * 1000 if 'Pagu RAKL (Rp Ribu)' in df.columns else 0.0
            df['p_c'] = p_ribuan
            nk_aw = clean_currency_vectorized(df['Nilai Kontrak']) if 'Nilai Kontrak' in df.columns else 0.0
            nk_v = clean_currency_vectorized(df['Nilai Kontrak (Rp Ribu)']) * 1000 if 'Nilai Kontrak (Rp Ribu)' in df.columns else 0.0
            df['nk_c'] = nk_aw.where(nk_aw > 0, nk_v)
            df['status_norm'] = normalize_status_vectorized(df['Progres Paket'] if 'Progres Paket' in df.columns else (df['Status Kontrak'] if 'Status Kontrak' in df.columns else pd.Series(index=df.index)), source='BP2JK')
        elif n == "Iemon":
            df['p_c'] = clean_currency_vectorized(df['Pagu RAKL (Rp Ribu)']) * 1000 if 'Pagu RAKL (Rp Ribu)' in df.columns else 0.0
            df['nk_c'] = clean_currency_vectorized(df['Nilai Kontrak (Rp Ribu)']) * 1000 if 'Nilai Kontrak (Rp Ribu)' in df.columns else 0.0
            df['status_norm'] = normalize_status_vectorized(df['Status Kontrak'] if 'Status Kontrak' in df.columns else pd.Series(index=df.index), source='Iemon')
        elif n == "Inaproc":
            df['nk_c'] = clean_currency_vectorized(df['Nilai Kontrak'])
            df['status_norm'] = "Terkontrak"
        m_ep = df['Metode E-Purchasing'].astype(str).str.upper() if 'Metode E-Purchasing' in df.columns else pd.Series("", index=df.index)
        m_p = df['Metode Pemilihan'].astype(str).str.upper() if 'Metode Pemilihan' in df.columns else pd.Series("", index=df.index)
        df['metode_norm'] = np.where(m_ep.str.contains('MINI') | m_p.str.contains('MINI'), "Minikompetisi",
                            np.where(m_ep.str.contains('NEGOSIASI|SURAT PESANAN|PURCHASING') | m_p.str.contains('NEGOSIASI|SURAT PESANAN|PURCHASING'), "Negosiasi", "Belum Info"))
        d_proc[n] = df

    all_ids = pd.unique(pd.concat([d_proc[n]['ID SIRUP'] for n in d_proc]))
    master = pd.DataFrame({'ID SIRUP': all_ids}).set_index('ID SIRUP')
    map_cols = {'Nama Paket': 'Nama Paket', 'Kode Paket': 'Kode Paket', 'Unor': 'Unor', 'Satker': 'Satker', 'BP2JK': 'BP2JK', 'Jenis Paket': 'Jenis Paket', 'p_c': 'Pagu DIPA', 'nk_c': 'Nilai Kontrak'}
    
    for n in ["Iemon", "BP2JK", "Inaproc"]:
        df = d_proc[n]
        if df.empty: continue
        df_to_merge = df.set_index('ID SIRUP')
        rek_col = next((c for c in ['Rekanan', 'Nama Rekanan'] if c in df_to_merge.columns), None)
        update_dict = {map_cols[c]: df_to_merge[c] for c in map_cols if c in df_to_merge.columns}
        if rek_col: update_dict['Rekanan'] = df_to_merge[rek_col]
        valid_status = df_to_merge['status_norm'] != "Belum Proses"
        valid_method = df_to_merge['metode_norm'] != "Belum Info"
        for col, data in update_dict.items():
            if col not in master.columns: 
                # Inisialisasi kolom baru dengan dtype yang sesuai dari data sumber
                master[col] = pd.Series(index=master.index, dtype=data.dtype)
            master[col].update(data)
        
        # Penanganan Progres dan Metode secara khusus
        if n == "Inaproc":
            if 'Progres Paket' not in master.columns: master['Progres Paket'] = pd.Series(index=master.index, dtype=object)
            if 'Metode EP' not in master.columns: master['Metode EP'] = pd.Series(index=master.index, dtype=object)
            master['Progres Paket'].update(df_to_merge['status_norm'])
            master['Metode EP'].update(df_to_merge['metode_norm'].where(valid_method))
        else:
            if 'Progres Paket' not in master.columns: master['Progres Paket'] = pd.Series(index=master.index, dtype=object)
            if 'Metode EP' not in master.columns: master['Metode EP'] = pd.Series(index=master.index, dtype=object)
            master['Progres Paket'].update(df_to_merge['status_norm'].where(valid_status))
            master['Metode EP'].update(df_to_merge['metode_norm'].where(valid_method))

    master = master.fillna({'Pagu DIPA': 0.0, 'Nilai Kontrak': 0.0, 'Progres Paket': 'Belum Proses', 'Metode EP': 'Belum Info'}).reset_index()
    master['In BP2JK'] = master['ID SIRUP'].isin(d_proc['BP2JK']['ID SIRUP'])
    master['In Iemon'] = master['ID SIRUP'].isin(d_proc['Iemon']['ID SIRUP'])
    master['In Inaproc'] = master['ID SIRUP'].isin(d_proc['Inaproc']['ID SIRUP'])
    return master

with st.sidebar:
    if os.path.exists("image/logo_kemenpu.png"): st.image("image/logo_kemenpu.png", use_container_width=True)
    st.markdown("---")
    with st.expander("🌐 Sumber Data"):
        up_bp, up_ie, up_in = st.file_uploader("BP2JK", type="csv"), st.file_uploader("Iemon", type="csv"), st.file_uploader("Inaproc", type="csv")
    raw_data, stats, dupes_data = load_and_process_all({"BP2JK": up_bp, "Iemon": up_ie, "Inaproc": up_in})
    master_df = build_master(raw_data)
    menu = st.radio("MENU", ["🚀 Dashboard Utama", "📁 Data BP2JK", "📁 Data Iemon", "📁 Data Inaproc", "🔍 Diagnostik Data"])

if menu == "🚀 Dashboard Utama":
    st.markdown('<div class="header-container"><div class="header-text"><h1>MONITORING E-PURCHASING TA.2026</h1><p>Konsolidasi Data Nasional (Inaproc) & Sistem Internal Monitoring (BP2JK / Iemon)</p></div></div>', unsafe_allow_html=True)
    if master_df.empty: st.warning("⚠️ Data kosong.")
    else:
        with st.expander("🔍 Filter Global", expanded=True):
            f1, f2, f3, f4 = st.columns(4)
            with f1: sel_u = st.multiselect("Filter Unor:", options=sorted(master_df['Unor'].astype(str).unique()))
            with f2: sel_b = st.multiselect("Filter BP2JK:", options=sorted(master_df['BP2JK'].astype(str).unique()))
            with f3: sel_j = st.multiselect("Filter Jenis Paket:", options=sorted(master_df['Jenis Paket'].astype(str).unique()))
            with f4: sel_p = st.multiselect("Filter Progres:", options=['Belum Proses', 'Proses E-Purchasing', 'Persiapan Terkontrak', 'Terkontrak', 'Batal'])
            f5, f6 = st.columns(2)
            with f5: sel_m = st.multiselect("Filter Metode:", options=['Negosiasi', 'Minikompetisi', 'Belum Info'])
            with f6: sel_s = st.multiselect("Filter Skala Paket:", options=['>= 15M', '< 15M', 'Pagu Kosong (Rp 0)'])

        filtered = master_df.copy()
        filtered['tmp_skala'] = np.where(filtered['Pagu DIPA'] <= 0, 'Pagu Kosong (Rp 0)', np.where(filtered['Pagu DIPA'] >= 15e9, '>= 15M', '< 15M'))
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

        t1, t2 = st.tabs(["📊 ANALISIS VISUAL", "📋 DAFTAR PAKET MASTER"])
        with t1:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<p class="chart-title">Jumlah Paket per Unor</p>', unsafe_allow_html=True)
                det = True if sel_u else st.session_state.get('s_det', False)
                sib = ['SEKJEN', 'ITJEN', 'BK', 'BPIW', 'BPSDM', 'PI']
                u_c = filtered['Unor'].apply(lambda x: "SIBBPI" if not det and str(x).upper() in sib else x).value_counts().reset_index()
                u_c.columns = ['U', 'V']
                h = 700 if det else 450
                fig_u = px.pie(u_c, values='V', names='U', height=h, hole=0.5, color_discrete_sequence=px.colors.qualitative.Bold)
                fig_u.update_traces(texttemplate='%{value}<br>%{percent:.1%}', textposition='auto')
                if det: fig_u.update_traces(domain=dict(x=[0.3, 0.9], y=[0.2, 0.8]))
                fig_u.update_layout(legend=dict(orientation="v", y=1, x=0), annotations=[dict(text=f"<b>{len(filtered)}</b>", x=0.6 if det else 0.5, y=0.5, showarrow=False, font_size=32)])
                st.plotly_chart(fig_u, use_container_width=True)
                if not sel_u: st.checkbox("Tampilkan Detail SIBBPI", value=False, key='s_det')
            with c2:
                st.markdown('<p class="chart-title">Progres Tahapan</p>', unsafe_allow_html=True)
                p_c = filtered['Progres Paket'].value_counts().reset_index()
                fig_p = px.pie(p_c, values='count', names='Progres Paket', height=h, color='Progres Paket', color_discrete_map={'Terkontrak':'#22c55e','Batal':'#ef4444','Belum Proses':'#94a3b8'})
                fig_p.update_traces(texttemplate='%{value} (%{percent:.1%})', textposition='auto')
                if det: fig_p.update_traces(domain=dict(x=[0.3, 0.9], y=[0.2, 0.8]))
                fig_p.update_layout(legend=dict(orientation="v", y=1, x=0))
                st.plotly_chart(fig_p, use_container_width=True)
            st.markdown("---")
            c3, c4 = st.columns(2)
            with c3:
                st.markdown('<p class="chart-title">Distribusi Jenis Paket</p>', unsafe_allow_html=True)
                j_c = filtered['Jenis Paket'].value_counts().reset_index()
                st.plotly_chart(px.bar(j_c, x='Jenis Paket', y='count', color='Jenis Paket', text_auto=True, height=400), use_container_width=True)
            with c4:
                st.markdown('<p class="chart-title">Metode E-Purchasing</p>', unsafe_allow_html=True)
                m_c = filtered['Metode EP'].value_counts().reset_index()
                st.plotly_chart(px.treemap(m_c, path=[px.Constant("Total"), 'Metode EP'], values='count', color='Metode EP', color_discrete_map={'Negosiasi':'#6366f1','Minikompetisi':'#ec4899','Belum Info':'#94a3b8'}, height=400), use_container_width=True)
            st.markdown("---")
            all_b = st.checkbox("Tampilkan Semua BP2JK", value=False)
            st.markdown('<p class="chart-title">Jumlah Paket per BP2JK</p>', unsafe_allow_html=True)
            b_c = filtered['BP2JK'].value_counts().reset_index()
            disp_b = b_c if all_b else b_c.head(10)
            fig_b = px.bar(disp_b, x='count', y='BP2JK', orientation='h', color='count', color_continuous_scale='Blues', text_auto=True)
            fig_b.update_traces(textangle=0, textposition='outside')
            fig_b.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=max(400, len(disp_b)*30))
            st.plotly_chart(fig_b, use_container_width=True)

        with t2:
            dv = filtered.copy()
            # Bersihkan ID SIRUP internal untuk tampilan (tampilkan kosong jika MISSING-)
            mask_missing = dv['ID SIRUP'].str.contains('MISSING-', na=False)
            dv.loc[mask_missing, 'ID SIRUP'] = "" 
            
            dv['Pagu DIPA'] = dv['Pagu DIPA'].apply(format_idr)
            dv['Nilai Kontrak'] = dv['Nilai Kontrak'].apply(format_idr)
            dv.insert(0, 'No.', range(1, len(dv)+1))
            st.dataframe(dv[['No.', 'ID SIRUP', 'Nama Paket', 'Unor', 'Progres Paket', 'Metode EP', 'Pagu DIPA', 'Nilai Kontrak', 'Rekanan']], use_container_width=True, height=600, hide_index=True)

elif menu == "🔍 Diagnostik Data":
    st.title("🔍 Diagnostik Sinkronisasi")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BP2JK", stats['BP2JK']); c2.metric("Iemon", stats['Iemon']); c3.metric("Inaproc", stats['Inaproc']); c4.metric("TOTAL MASTER", len(master_df))
    gb, gi = master_df[~master_df['In BP2JK']].copy(), master_df[~master_df['In Iemon']].copy()
    gn = master_df[master_df['In Inaproc'] & (~master_df['In BP2JK'] | ~master_df['In Iemon'])].copy()
    gs = master_df[master_df['ID SIRUP'].str.contains('MISSING-', na=False)].copy()
    tg1, tg2, tg3, tg4, tg5 = st.tabs([f"❌ Belum Masuk BP2JK ({len(gb)})", f"❌ Belum Masuk Iemon ({len(gi)})", f"🌐 Gap Inaproc ({len(gn)})", f"⚠️ Perlu Perbaikan SIRUP ({len(gs)})", "⚠️ Data Duplikat"])
    with tg1: gb.insert(0,'No.',range(1,len(gb)+1)); st.dataframe(gb[['No.','ID SIRUP','Nama Paket','Unor','Satker']], use_container_width=True, hide_index=True)
    with tg2: gi.insert(0,'No.',range(1,len(gi)+1)); st.dataframe(gi[['No.','ID SIRUP','Nama Paket','Unor','Satker']], use_container_width=True, hide_index=True)
    with tg3: gn.insert(0,'No.',range(1,len(gn)+1)); st.dataframe(gn[['No.','ID SIRUP','Nama Paket','Unor','In Inaproc','In BP2JK','In Iemon']], use_container_width=True, hide_index=True)
    with tg4: 
        st.warning("Daftar paket di bawah ini tidak memiliki ID SIRUP yang valid di data internal (BP2JK/Iemon). Paket ini TIDAK AKAN bisa sinkron dengan data Inaproc sampai ID SIRUP diperbaiki.")
        gs_display = gs.copy()
        gs_display.loc[gs_display['ID SIRUP'].str.contains('MISSING-', na=False), 'ID SIRUP'] = "MISSING"
        gs_display.insert(0,'No.',range(1,len(gs_display)+1))
        st.dataframe(gs_display[['No.','ID SIRUP','Kode Paket','Nama Paket','Unor','Satker']], use_container_width=True, hide_index=True)
    with tg5:
        st.info("Data duplikat terdeteksi jika satu ID SIRUP digunakan oleh lebih dari satu paket dalam satu sumber data yang sama.")
        for src in ["BP2JK", "Iemon", "Inaproc"]:
            d_df = dupes_data.get(src, pd.DataFrame())
            if not d_df.empty:
                st.subheader(f"Duplikat di {src} ({len(d_df)} baris)")
                d_df.insert(0, 'No.', range(1, len(d_df)+1))
                st.dataframe(d_df, use_container_width=True, hide_index=True)
            else:
                st.success(f"✅ Tidak ada duplikat di {src}")

else:
    src_n = menu.split(" ")[2]
    st.title(f"📄 Detail Data {src_n}")
    df_r = raw_data.get(src_n).copy()
    if not df_r.empty:
        df_r.insert(0, 'No.', range(1, len(df_r)+1))
        st.dataframe(df_r, use_container_width=True, height=600, hide_index=True)

st.markdown("---")
st.markdown("<center style='color: #94a3b8;'>Monitoring E-Purchasing TA.2026 | Subdit Katalog</center>", unsafe_allow_html=True)
