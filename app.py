import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import io
import datetime
from utils import format_idr, generate_rekap_table, render_rekap_html
from data_manager import load_and_process_all, build_master
from styles import apply_custom_css, get_header_html

# CONFIGURATION
st.set_page_config(page_title="Dashboard Monev E-Purchasing 2026", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# APPLY STYLES
apply_custom_css()

# DATA LOADING (SHARED ACROSS PAGES)
@st.cache_data(ttl=600)
def get_data():
    raw_data, stats, dupes_data = load_and_process_all()
    master_df = build_master(raw_data)
    return raw_data, stats, dupes_data, master_df

raw_data, stats, dupes_data, master_df = get_data()

# --- PAGE FUNCTIONS ---

def dashboard_page():
    st.markdown(get_header_html(), unsafe_allow_html=True)
    
    # Check and display fallback warnings
    fallback_warnings = []
    for src in ["BP2JK", "Iemon", "Inaproc"]:
        if stats.get(f"{src}_fallback", False):
            time_str = stats.get(f"{src}_fallback_time", "Tidak diketahui")
            fallback_warnings.append(f"**{src}** (Terakhir diperbarui: {time_str})")
            
    if fallback_warnings:
        st.warning(f"⚠️ Gagal menarik data terbaru secara online dari Google Sheets. Dashboard saat ini menampilkan data cadangan lokal untuk: {', '.join(fallback_warnings)}.")
        
    if master_df.empty: 
        st.warning("⚠️ Data kosong.")
        return

    # FILTERS
    with st.expander("🔍 Filter Global", expanded=True):
        def reset_all_filters():
            for k in ['f_u', 'f_b', 'f_j', 'f_p', 'f_m', 'f_s', 'f_r']:
                st.session_state[k] = []

        f1, f2, f3, f4 = st.columns(4)
        unor_opts = sorted(master_df['Unor'].fillna('Belum Info').unique()) if 'Unor' in master_df.columns else []
        bp2jk_opts = sorted(master_df['BP2JK'].fillna('Belum Info').unique()) if 'BP2JK' in master_df.columns else []
        jenis_opts = sorted(master_df['Jenis Paket'].fillna('Belum Info').unique()) if 'Jenis Paket' in master_df.columns else []
        
        with f1: sel_u = st.multiselect("Filter Unor:", options=unor_opts, key='f_u')
        with f2: sel_b = st.multiselect("Filter BP2JK:", options=bp2jk_opts, key='f_b')
        with f3: sel_j = st.multiselect("Filter Jenis Paket:", options=jenis_opts, key='f_j')
        with f4: sel_p = st.multiselect("Filter Progres:", options=['Belum Proses', 'Proses E-Purchasing', 'Persiapan Terkontrak', 'Terkontrak', 'Batal'], key='f_p')
        
        f5, f6 = st.columns(2)
        with f5: sel_m = st.multiselect("Filter Metode:", options=['Negosiasi', 'Minikompetisi', 'Belum Info'], key='f_m')
        skala_opts = ['Pagu Kosong (Rp 0)', '< 200Jt', '200Jt - 2M', '2M - 15M', '15M - 50M', '> 50M']
        existing_skala = [opt for opt in skala_opts if opt in master_df['Range Pagu'].unique()]
        with f6: sel_s = st.multiselect("Filter Skala Paket:", options=existing_skala, key='f_s')
        
        f7, f8 = st.columns([3, 1])
        with f7: sel_r = st.multiselect("Filter Realisasi Kontrak:", options=['Ada Kontrak (> Rp 0)', 'Belum Ada Kontrak (Rp 0)', 'Nilai Kontrak > Pagu DIPA'], key='f_r')
        with f8: 
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("🔄 Reset Filter", on_click=reset_all_filters, use_container_width=True)

    # PROCESS FILTERING
    filtered = master_df.copy()
    if sel_u: filtered = filtered[filtered['Unor'].fillna('Belum Info').isin(sel_u)]
    if sel_b: filtered = filtered[filtered['BP2JK'].fillna('Belum Info').isin(sel_b)]
    if sel_j: filtered = filtered[filtered['Jenis Paket'].fillna('Belum Info').isin(sel_j)]
    if sel_p: filtered = filtered[filtered['Progres Paket'].isin(sel_p)]
    if sel_m: filtered = filtered[filtered['Metode EP'].isin(sel_m)]
    if sel_s: filtered = filtered[filtered['Range Pagu'].isin(sel_s)]
    
    if sel_r:
        mask = pd.Series(False, index=filtered.index)
        if 'Ada Kontrak (> Rp 0)' in sel_r: mask |= (filtered['Nilai Kontrak'] > 0)
        if 'Belum Ada Kontrak (Rp 0)' in sel_r: mask |= (filtered['Nilai Kontrak'] <= 0)
        if 'Nilai Kontrak > Pagu DIPA' in sel_r: mask |= (filtered['Nilai Kontrak'] - filtered['Pagu DIPA'] > 2000000)
        filtered = filtered[mask]

    # MAIN METRICS
    m1, m2, m3, m4 = st.columns(4)
    p, k = filtered['Pagu DIPA'].sum(), filtered['Nilai Kontrak'].sum()
    pct = (k / p * 100) if p > 0 else 0.0

    card_1_html = f"""<div class="metric-card card-blue">
<div class="metric-icon-container" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);">
<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2h-3"/>
<path d="M3 10h18"/>
</svg>
</div>
<div class="metric-info">
<span class="metric-label">TOTAL PAGU DIPA</span>
<div class="metric-value-wrapper">
<span class="metric-value">{format_idr(p)}</span>
</div>
</div>
</div>"""

    card_2_html = f"""<div class="metric-card card-green">
<div class="metric-icon-container" style="background: linear-gradient(135deg, #10b981 0%, #047857 100%);">
<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
<path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
</svg>
</div>
<div class="metric-info">
<span class="metric-label">REALISASI KONTRAK</span>
<div class="metric-value-wrapper">
<span class="metric-value">{format_idr(k)}</span>
<span class="metric-delta">↗ {pct:.1f}%</span>
</div>
<div class="progress-bar-container">
<div class="progress-bar-fill" style="width: {min(pct, 100.0):.1f}%;"></div>
</div>
</div>
</div>"""

    card_3_html = f"""<div class="metric-card card-purple">
<div class="metric-icon-container" style="background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);">
<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/>
<polygon points="12 22.08 12 12 3 6.92 3 17.08 12 22.08"/>
<polygon points="12 12 21 6.92 21 17.08 12 22.08"/>
<polygon points="12 2 3 6.92 12 12 21 6.92 12 2"/>
<line x1="12" y1="22.08" x2="12" y2="12"/>
</svg>
</div>
<div class="metric-info">
<span class="metric-label">TOTAL PAKET UNIK</span>
<div class="metric-value-wrapper">
<span class="metric-value">{len(filtered):,}</span>
</div>
</div>
</div>"""

    card_4_html = f"""<div class="metric-card card-amber">
<div class="metric-icon-container" style="background: linear-gradient(135deg, #f59e0b 0%, #b45309 100%);">
<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<circle cx="12" cy="8" r="7"/>
<polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>
</svg>
</div>
<div class="metric-info">
<span class="metric-label">PAKET TERKONTRAK</span>
<div class="metric-value-wrapper">
<span class="metric-value">{(filtered['Progres Paket']=='Terkontrak').sum():,}</span>
</div>
</div>
</div>"""

    with m1: st.markdown(card_1_html, unsafe_allow_html=True)
    with m2: st.markdown(card_2_html, unsafe_allow_html=True)
    with m3: st.markdown(card_3_html, unsafe_allow_html=True)
    with m4: st.markdown(card_4_html, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["📊 ANALISIS VISUAL", "📋 TABEL REKAPAN", f"📋 DAFTAR PAKET MASTER ({len(filtered):,})"])
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            if not sel_u: st.checkbox("Tampilkan Detail SIBBPI", value=False, key='s_det')
            with st.container(border=True):
                st.markdown('<p class="chart-title">Jumlah Paket per Unor</p>', unsafe_allow_html=True)
                det = True if sel_u else st.session_state.get('s_det', False)
                
                # Dinamis Height
                h_u = 700 if det else 450
                
                sib = ['SEKJEN', 'ITJEN', 'BK', 'BPIW', 'BPSDM', 'PI']
                u_vals = filtered['Unor'].fillna('Belum Info').apply(lambda x: "SIBBPI" if not det and str(x).upper() in sib else x)
                u_c = u_vals.value_counts().reset_index()
                u_c.columns = ['U', 'V']
                
                pupr_pie_colors = ['#1e3a8a', '#FFCC00', '#0f766e', '#06b6d4', '#64748b', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']
                fig_u = px.pie(u_c, values='V', names='U', height=h_u, hole=0.5, color_discrete_sequence=pupr_pie_colors)
                fig_u.update_traces(texttemplate='%{value}<br>%{percent:.1%}', textposition='auto')
                
                # Penyesuaian Layout jika Detail Aktif
                if det:
                    fig_u.update_traces(domain=dict(x=[0.2, 0.8], y=[0.2, 0.8]))
                
                fig_u.update_layout(
                    legend=dict(orientation="v", y=1, x=0), 
                    annotations=[dict(text=f"<b>{len(filtered)}</b>", x=0.5, y=0.5, showarrow=False, font_size=32)], 
                    margin=dict(t=0, b=0, l=0, r=0),
                    font_family="Inter, sans-serif"
                )
                st.plotly_chart(fig_u, use_container_width=True)
                
        with c2:
            st.checkbox("Tampilkan Detail Progres", value=False, key='p_det')
            with st.container(border=True):
                st.markdown('<p class="chart-title">Progres Tahapan</p>', unsafe_allow_html=True)

                is_detailed = st.session_state.get('p_det', False)
                
                # Dinamis Height
                h_p = 700 if is_detailed else 450
                
                p_col = 'Progres Raw' if is_detailed else 'Progres Paket'
                p_vals = filtered[p_col].copy()
                
                terkontrak_variants = ['Selesai', 'SELESAI KONTRAK', 'Selesai Kontrak', 'Terkontrak (Nasional)', 'TERKONTRAK', 'SELESAI']
                p_vals = p_vals.replace(terkontrak_variants, 'Terkontrak')
                
                p_c = p_vals.value_counts().reset_index()
                p_c.columns = ['Status', 'count']

                color_map = {
                    'Terkontrak': '#1e3a8a',
                    'Proses E-Purchasing': '#FFCC00',
                    'Persiapan Terkontrak': '#0f766e',
                    'Belum Proses': '#64748b',
                    'Batal': '#b91c1c'
                }
                
                fig_p = px.pie(p_c, values='count', names='Status', height=h_p, color='Status', 
                               color_discrete_map=color_map)
                
                fig_p.update_traces(texttemplate='%{value} (%{percent:.1%})', textposition='auto')
                
                # Penyesuaian Layout jika Detail Aktif
                if is_detailed:
                    fig_p.update_traces(domain=dict(x=[0.2, 0.8], y=[0.2, 0.8]))
                
                fig_p.update_layout(legend=dict(orientation="v", y=1, x=0), margin=dict(t=0, b=0, l=0, r=0), font_family="Inter, sans-serif")
                st.plotly_chart(fig_p, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            with st.container(border=True):
                st.markdown('<p class="chart-title">Distribusi Jenis Paket</p>', unsafe_allow_html=True)
                j_c = filtered['Jenis Paket'].value_counts().reset_index()
                jenis_color_map = {
                    'BARANG': '#1e3a8a',
                    'PEKERJAAN KONSTRUKSI': '#FFCC00',
                    'JASA KONSULTASI': '#0f766e',
                    'JASA LAINNYA': '#06b6d4',
                    'AU': '#64748b',
                    'Belum Info': '#cbd5e1'
                }
                fig_j = px.bar(j_c, x='Jenis Paket', y='count', color='Jenis Paket', text_auto=True, height=400, color_discrete_map=jenis_color_map)
                fig_j.update_layout(showlegend=False, font_family="Inter, sans-serif")
                st.plotly_chart(fig_j, use_container_width=True)
        with c4:
            with st.container(border=True):
                st.markdown('<p class="chart-title">Metode E-Purchasing</p>', unsafe_allow_html=True)
                m_c = filtered['Metode EP'].value_counts().reset_index()
                fig_m = px.treemap(m_c, path=[px.Constant("Total"), 'Metode EP'], values='count', color='Metode EP', height=400,
                                   color_discrete_sequence=['#1e3a8a', '#FFCC00', '#0f766e', '#06b6d4', '#64748b', '#3b82f6'])
                fig_m.update_layout(font_family="Inter, sans-serif")
                st.plotly_chart(fig_m, use_container_width=True)

        # --- RESTORED MISSING CHARTS ---
        with st.container(border=True):
            all_b = st.checkbox("Tampilkan Semua BP2JK", value=False)
            st.markdown('<p class="chart-title">Jumlah Paket per BP2JK</p>', unsafe_allow_html=True)
            b_c = filtered['BP2JK'].value_counts().reset_index()
            disp_b = b_c if all_b else b_c.head(10)
            fig_b = px.bar(disp_b, x='count', y='BP2JK', orientation='h', color='count', color_continuous_scale=['#cbd5e1', '#1e3a8a'], text_auto=True)
            fig_b.update_traces(textangle=0, textposition='outside')
            fig_b.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=max(400, len(disp_b)*30), margin=dict(t=10, b=10, l=10, r=10), font_family="Inter, sans-serif")
            st.plotly_chart(fig_b, use_container_width=True)

        with st.container(border=True):
            st.markdown('<p class="chart-title">Distribusi Skala Nilai Paket (Pagu DIPA)</p>', unsafe_allow_html=True)
            r_c = filtered['Range Pagu'].value_counts().reset_index()
            r_c.columns = ['Range Pagu', 'count']
            logic_order = ['Pagu Kosong (Rp 0)', '< 200Jt', '200Jt - 2M', '2M - 15M', '15M - 50M', '> 50M']
            existing_order = [o for o in logic_order if o in r_c['Range Pagu'].values]
            range_color_map = {
                'Pagu Kosong (Rp 0)': '#64748b',
                '< 200Jt': '#94a3b8',
                '200Jt - 2M': '#06b6d4',
                '2M - 15M': '#3b82f6',
                '15M - 50M': '#1e3a8a',
                '> 50M': '#FFCC00'
            }
            fig_r = px.bar(r_c, x='Range Pagu', y='count', color='Range Pagu', text_auto=True, height=400, color_discrete_map=range_color_map, category_orders={'Range Pagu': existing_order})
            fig_r.update_layout(showlegend=False, font_family="Inter, sans-serif")
            st.plotly_chart(fig_r, use_container_width=True)

    with t2:
        # Exclude Batal packages from statistics in Rekapan Tab
        df_rek = filtered[filtered['Progres Paket'] != 'Batal']
        
        rows_u, prog_u = generate_rekap_table(df_rek, 'Unor')
        if rows_u:
            st.markdown(render_rekap_html(rows_u, prog_u, "REKAP PAKET E-PURCHASING PER UNOR TA. 2026", "Unor"), unsafe_allow_html=True)
        else:
            st.info("Tidak ada data Unor yang sesuai dengan filter.")

        rows_j, prog_j = generate_rekap_table(df_rek, 'Jenis Paket')
        if rows_j:
            st.markdown(render_rekap_html(rows_j, prog_j, "REKAP PAKET E-PURCHASING PER JENIS PAKET TA. 2026", "Jenis Paket"), unsafe_allow_html=True)
        else:
            st.info("Tidak ada data Jenis Paket yang sesuai dengan filter.")

        rows_b, prog_b = generate_rekap_table(df_rek, 'BP2JK')
        if rows_b:
            st.markdown(render_rekap_html(rows_b, prog_b, "REKAP PAKET E-PURCHASING PER BALAI TA. 2026", "BP2JK Wilayah"), unsafe_allow_html=True)
        else:
            st.info("Tidak ada data BP2JK yang sesuai dengan filter.")

    with t3:
        st.markdown("### 🔍 Cari Paket")
        search_query = st.text_input("Masukkan Nama Paket atau ID SIRUP:", placeholder="Cari...", key="search_master")
        dv = filtered.copy()
        if search_query:
            dv = dv[dv['Nama Paket'].astype(str).str.contains(search_query, case=False, na=False) | dv['ID SIRUP'].astype(str).str.contains(search_query, case=False, na=False)]
        
        dv['Pagu DIPA'] = dv['Pagu DIPA'].apply(format_idr)
        dv['Nilai Kontrak'] = dv['Nilai Kontrak'].apply(format_idr)
        st.dataframe(dv[['ID SIRUP', 'Nama Paket', 'Unor', 'BP2JK', 'Progres Paket', 'Jenis Paket', 'Status Pagu', 'Pagu DIPA', 'Nilai Kontrak']], use_container_width=True, height=800, hide_index=True)

def diagnostic_page():
    st.title("🔍 Diagnostik Sinkronisasi")
    if master_df.empty:
        st.warning("⚠️ Data kosong. Tidak dapat melakukan diagnostik sinkronisasi.")
        return
        
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BP2JK", stats['BP2JK']); c2.metric("Iemon", stats['Iemon']); c3.metric("Inaproc", stats['Inaproc']); c4.metric("TOTAL MASTER", len(master_df))
    
    gs = master_df[master_df['ID SIRUP'].str.contains('missing-', case=False, na=False)].copy()
    ina_only = master_df[master_df['In Inaproc'] & ~master_df['In BP2JK'] & ~master_df['In Iemon']].copy()
    ie_only = master_df[master_df['In Iemon'] & ~master_df['In BP2JK'] & ~master_df['In Inaproc']].copy()
    bp_only = master_df[master_df['In BP2JK'] & ~master_df['In Iemon'] & ~master_df['In Inaproc']].copy()
    
    mask_internal = (master_df['In BP2JK'] | master_df['In Iemon'])
    mask_not_contracted_internal = ~master_df['Progres Paket'].isin(['Terkontrak', 'Persiapan Terkontrak'])
    gap_kontrak = master_df[mask_internal & mask_not_contracted_internal & master_df['In Inaproc']].copy()

    df_dupe_name = master_df.copy()
    df_dupe_name['name_norm'] = df_dupe_name['Nama Paket'].astype(str).str.lower().str.replace(r'[^a-z0-9]', '', regex=True).str.strip()
    
    # Vectorized check: check if a group has both at least one valid and one missing SIRUP ID
    is_missing = df_dupe_name['ID SIRUP'].str.contains('missing-|unknown-|unk-|^$', case=False, na=False)
    is_valid = ~is_missing
    
    has_valid_in_group = is_valid.groupby(df_dupe_name['name_norm']).transform('any')
    has_missing_in_group = is_missing.groupby(df_dupe_name['name_norm']).transform('any')
    
    dupe_groups = df_dupe_name[has_valid_in_group & has_missing_in_group]

    tg1, tg2, tgie, tgbp, tg3, tg4, tg5 = st.tabs([
        f"⚠️ Perlu Perbaikan SIRUP ({len(gs)})", 
        f"🌐 Inaproc Saja ({len(ina_only)})",
        f"📁 Iemon Saja ({len(ie_only)})",
        f"📁 BP2JK Saja ({len(bp_only)})",
        f"📑 Gap Status Kontrak ({len(gap_kontrak)})",
        "⚠️ Data Duplikat", 
        "🔍 Potensi Duplikat (Nama)"
    ])
    
    with tg1:
        st.warning("Paket tanpa ID SIRUP valid di internal. Tidak akan sinkron dengan Inaproc.")
        st.dataframe(gs[['ID SIRUP', 'Kode Paket', 'Nama Paket', 'Unor', 'Satker']], use_container_width=True, height=600, hide_index=True)

    with tg2:
        st.info("Hanya ada di Inaproc (Nasional), belum ada di data internal.")
        st.dataframe(ina_only[['ID SIRUP', 'Nama Paket', 'Unor', 'Satker', 'Nilai Kontrak', 'Rekanan']], use_container_width=True, height=600, hide_index=True)

    with tgie:
        st.info("Hanya ada di data Iemon.")
        st.dataframe(ie_only[['ID SIRUP', 'Kode Paket', 'Nama Paket', 'Unor', 'Satker', 'Pagu DIPA']], use_container_width=True, height=600, hide_index=True)

    with tgbp:
        st.info("Hanya ada di data BP2JK.")
        st.dataframe(bp_only[['ID SIRUP', 'Kode Paket', 'Nama Paket', 'Unor', 'Satker', 'Pagu DIPA']], use_container_width=True, height=600, hide_index=True)

    with tg3:
        st.info("Sudah berkontrak di Inaproc, tapi status internal belum 'Terkontrak'.")
        st.dataframe(gap_kontrak[['ID SIRUP', 'Nama Paket', 'Unor', 'Progres Paket', 'Nilai Kontrak']], use_container_width=True, height=600, hide_index=True)
    
    with tg4:
        for src in ["BP2JK", "Iemon", "Inaproc"]:
            d_df = dupes_data.get(src, pd.DataFrame())
            st.subheader(f"{src} ({len(d_df)} Duplikat)")
            if not d_df.empty: st.dataframe(d_df, use_container_width=True, height=400, hide_index=True)
            else: st.success(f"✅ Bersih di {src}")

    with tg5:
        st.info("Indikasi paket yang sama tapi terpisah (satu punya SIRUP, satu MISSING).")
        if not dupe_groups.empty:
            res_dupe = dupe_groups.sort_values(['name_norm', 'ID SIRUP'])
            st.dataframe(res_dupe[['Nama Paket', 'ID SIRUP', 'Kode Paket', 'Unor', 'Satker', 'Pagu DIPA']], use_container_width=True, height=600, hide_index=True)
        else:
            st.success("✅ Tidak ditemukan potensi duplikat nama.")

def detail_data_page(source_name):
    st.title(f"📄 Detail Data {source_name}")
    df_r = raw_data.get(source_name).copy()
    if not df_r.empty:
        st.dataframe(df_r, use_container_width=True, height=800, hide_index=True)
    else:
        st.warning("Data tidak tersedia.")

# --- NAMED FUNCTIONS FOR NAVIGATION (Fixes <lambda> error) ---
def bp2jk_page(): detail_data_page("BP2JK")
def iemon_page(): detail_data_page("Iemon")
def inaproc_page(): detail_data_page("Inaproc")

# --- NAVIGATION CONFIG ---
pg = st.navigation({
    "UTAMA": [
        st.Page(dashboard_page, title="Dashboard Utama", icon="🚀", default=True),
        st.Page(diagnostic_page, title="Diagnostik Data", icon="🔍"),
    ],
    "SUMBER DATA": [
        st.Page(bp2jk_page, title="Data BP2JK", icon="📁"),
        st.Page(iemon_page, title="Data Iemon", icon="📁"),
        st.Page(inaproc_page, title="Data Inaproc", icon="🌐"),
    ]
})

# --- SIDEBAR GLOBAL ELEMENTS ---
with st.sidebar:
    st.markdown('<div class="sidebar-top-container">', unsafe_allow_html=True)
    if os.path.exists("image/logo_kemenpu.png"): 
        st.image("image/logo_kemenpu.png", use_container_width=True)
    st.markdown('<div class="sidebar-header-text"><h3>SUBDIT KATALOG</h3><p>Dit. Pengadaan Jasa Konstruksi</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # "New Chat" Style Button (Update Data)
    if st.button("🔄 UPDATE DATA"):
        st.cache_data.clear()
        st.rerun()

# RUN NAVIGATION
pg.run()

st.markdown("---")
st.markdown("<center style='color: #94a3b8;'>Monitoring E-Purchasing TA.2026 | Subdit Katalog</center>", unsafe_allow_html=True)
