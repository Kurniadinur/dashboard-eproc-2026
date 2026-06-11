import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Import custom logic
from logic import load_and_process_all, build_master, format_idr

# --- PAGE CONFIG ---
st.set_page_config(page_title="Dashboard Monev E-Purchasing 2026", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# --- LOAD CSS ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

if os.path.exists("styles.css"):
    local_css("styles.css")

# --- SIDEBAR & DATA LOADING ---
with st.sidebar:
    if os.path.exists("image/logo_kemenpu.png"): 
        st.image("image/logo_kemenpu.png", use_container_width=True)
    st.markdown("---")
    with st.expander("🌐 Sumber Data"):
        up_bp = st.file_uploader("BP2JK", type="csv")
        up_ie = st.file_uploader("Iemon", type="csv")
        up_in = st.file_uploader("Inaproc", type="csv")
        bypass = st.checkbox("Bypass Cache (Force Refresh)", value=False)
    
    raw_data, stats, duplicates_data = load_and_process_all(
        {"BP2JK": up_bp, "Iemon": up_ie, "Inaproc": up_in}, 
        bypass_cache=bypass
    )
    master_df = build_master(raw_data)
    menu = st.radio("MENU", ["🚀 Dashboard Utama", "📁 Data BP2JK", "📁 Data Iemon", "📁 Data Inaproc", "🔍 Diagnostik Data"])

# --- RENDER LOGIC ---
if menu == "🚀 Dashboard Utama":
    st.markdown("""
        <div class="header-wrapper">
            <div class="header-text">
                <h1>Dashboard Monitoring E-Purchasing</h1>
                <p>Katalog Elektronik Sektoral Kementerian PUPR - Tahun Anggaran 2026</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if master_df.empty: 
        st.warning("⚠️ Data kosong.")
    else:
        # --- FILTERS ---
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

        # --- METRICS ---
        m1, m2, m3, m4 = st.columns(4)
        p, k = filtered['Pagu DIPA'].sum(), filtered['Nilai Kontrak'].sum()
        with m1: st.metric("TOTAL PAGU DIPA", format_idr(p))
        with m2: st.metric("REALISASI KONTRAK", format_idr(k), delta=f"{(k/p*100 if p>0 else 0):.1f}%")
        with m3: st.metric("TOTAL PAKET UNIK", f"{len(filtered):,}")
        with m4: st.metric("PAKET TERKONTRAK", f"{(filtered['Progres Paket']=='Terkontrak').sum():,}")

        # --- TABS ---
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
                fig_u.update_layout(legend=dict(orientation="v", y=1, x=0), margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_u, use_container_width=True)
                if not sel_u: st.checkbox("Tampilkan Detail SIBBPI", value=False, key='s_det')
                st.markdown('</div>', unsafe_allow_html=True)

            with c2:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown('<p class="chart-title">Progres Tahapan</p>', unsafe_allow_html=True)
                p_c = filtered['Progres Paket'].value_counts().reset_index()
                fig_p = px.pie(p_c, values='count', names='Progres Paket', height=h, 
                               color='Progres Paket', 
                               color_discrete_map={'Terkontrak':'#10b981','Batal':'#ef4444','Belum Proses':'#94a3b8','Proses E-Purchasing':'#3b82f6','Persiapan Terkontrak':'#8b5cf6'})
                fig_p.update_traces(texttemplate='%{value} (%{percent:.1%})', textposition='auto', marker=dict(line=dict(color='#FFFFFF', width=2)))
                fig_p.update_layout(legend=dict(orientation="v", y=1, x=0), margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_p, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown('<p class="chart-title">Jumlah Paket per BP2JK</p>', unsafe_allow_html=True)
            b_c = filtered['BP2JK'].value_counts().reset_index()
            fig_b = px.bar(b_c.head(15), x='count', y='BP2JK', orientation='h', color='count', color_continuous_scale='Blues', text_auto=True)
            fig_b.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
            st.plotly_chart(fig_b, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            dv = filtered.copy()
            dv['Status Display'] = dv.apply(lambda x: "🚨 " + x['Progres Paket'] if x['Alert'] else x['Progres Paket'], axis=1)
            dv['Pagu DIPA'] = dv['Pagu DIPA'].apply(format_idr)
            dv['Nilai Kontrak'] = dv['Nilai Kontrak'].apply(format_idr)
            dv.insert(0, 'No.', range(1, len(dv)+1))
            st.dataframe(dv[['No.', 'ID SIRUP', 'Nama Paket', 'Unor', 'Status Display', 'Metode EP', 'Pagu DIPA', 'Nilai Kontrak', 'Rekanan']], use_container_width=True, height=600, hide_index=True)

        with t3:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown('<p class="chart-title">Analisis Rekanan (Top 20)</p>', unsafe_allow_html=True)
            rek_df = filtered[filtered['Rekanan'] != 'None'].copy()
            if not rek_df.empty:
                rek_stats = rek_df.groupby('Rekanan').agg({'Nilai Kontrak': 'sum', 'SOURCE_KEY': 'count'}).reset_index()
                rek_stats = rek_stats.sort_values('Nilai Kontrak', ascending=False).head(20)
                fig_rek = px.bar(rek_stats, y='Rekanan', x='Nilai Kontrak', orientation='h', text_auto='.2s', color='Nilai Kontrak', color_continuous_scale='Viridis')
                fig_rek.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
                st.plotly_chart(fig_rek, use_container_width=True)
            else:
                st.info("Belum ada data rekanan.")
            st.markdown('</div>', unsafe_allow_html=True)

elif menu == "🔍 Diagnostik Data":
    st.title("🔍 Diagnostik Sinkronisasi")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BP2JK", stats['BP2JK']['total'])
    c2.metric("Iemon", stats['Iemon']['total'])
    c3.metric("Inaproc", stats['Inaproc']['total'])
    c4.metric("TOTAL MASTER", len(master_df))
    
    st.info("Gunakan tab di bawah untuk menganalisis gap data antar sumber.")
    # (Logika diagnostik lainnya bisa ditambahkan di sini agar tetap modular)

else:
    src_n = menu.split(" ")[2]
    st.title(f"📄 Detail Data {src_n}")
    df_r = raw_data.get(src_n).copy()
    if not df_r.empty:
        df_r.insert(0, 'No.', range(1, len(df_r)+1))
        st.dataframe(df_r, use_container_width=True, height=600, hide_index=True)

st.markdown("---")
st.markdown("<center style='color: #94a3b8;'>Monitoring E-Purchasing TA.2026 | Subdit Katalog</center>", unsafe_allow_html=True)
