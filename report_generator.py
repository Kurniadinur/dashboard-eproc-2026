import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils import format_idr, generate_rekap_table, render_rekap_html
import datetime

def generate_plotly_figures(filtered, det_unor=False, det_progres=False, all_bp2jk=False):
    # 1. Jumlah Paket per Unor
    sib = ['SEKJEN', 'ITJEN', 'BK', 'BPIW', 'BPSDM', 'PI']
    u_vals = filtered['Unor'].fillna('Belum Info').apply(lambda x: "SIBBPI" if not det_unor and str(x).upper() in sib else x)
    u_c = u_vals.value_counts().reset_index()
    u_c.columns = ['U', 'V']
    
    pupr_pie_colors = ['#1e3a8a', '#FFCC00', '#0f766e', '#06b6d4', '#64748b', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']
    
    h_u = 500 if det_unor else 400
    fig_u = px.pie(u_c, values='V', names='U', height=h_u, hole=0.5, color_discrete_sequence=pupr_pie_colors)
    fig_u.update_traces(texttemplate='%{value}<br>%{percent:.1%}', textposition='auto')
    
    if det_unor:
        fig_u.update_traces(domain=dict(x=[0.15, 0.85], y=[0.15, 0.85]))
        
    fig_u.update_layout(
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"), 
        annotations=[dict(text=f"<b>{len(filtered)}</b>", x=0.5, y=0.5, showarrow=False, font_size=28)], 
        margin=dict(t=10, b=40, l=10, r=10),
        font_family="Inter, sans-serif",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    # 2. Progres Tahapan
    h_p = 500 if det_progres else 400
    p_col = 'Progres Raw' if det_progres else 'Progres Paket'
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
    
    fig_p = px.pie(p_c, values='count', names='Status', height=h_p, color='Status', color_discrete_map=color_map)
    fig_p.update_traces(texttemplate='%{value} (%{percent:.1%})', textposition='auto')
    
    if det_progres:
        fig_p.update_traces(domain=dict(x=[0.15, 0.85], y=[0.15, 0.85]))
        
    fig_p.update_layout(
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"), 
        margin=dict(t=10, b=40, l=10, r=10), 
        font_family="Inter, sans-serif",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    # 3. Distribusi Jenis Paket
    j_c = filtered['Jenis Paket'].value_counts().reset_index()
    jenis_color_map = {
        'BARANG': '#1e3a8a',
        'PEKERJAAN KONSTRUKSI': '#FFCC00',
        'JASA KONSULTASI': '#0f766e',
        'JASA LAINNYA': '#06b6d4',
        'AU': '#64748b',
        'Belum Info': '#cbd5e1'
    }
    fig_j = px.bar(j_c, x='Jenis Paket', y='count', color='Jenis Paket', text_auto=True, height=350, color_discrete_map=jenis_color_map)
    fig_j.update_layout(showlegend=False, font_family="Inter, sans-serif", margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    # 4. Metode E-Purchasing
    m_c = filtered['Metode EP'].value_counts().reset_index()
    fig_m = px.treemap(m_c, path=[px.Constant("Total"), 'Metode EP'], values='count', height=350,
                       color='Metode EP', color_discrete_sequence=['#1e3a8a', '#FFCC00', '#0f766e', '#06b6d4', '#64748b', '#3b82f6'])
    fig_m.update_layout(font_family="Inter, sans-serif", margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    # 5. Jumlah Paket per BP2JK
    b_c = filtered['BP2JK'].value_counts().reset_index()
    disp_b = b_c if all_bp2jk else b_c.head(10)
    fig_b = px.bar(disp_b, x='count', y='BP2JK', orientation='h', color='count', color_continuous_scale=['#cbd5e1', '#1e3a8a'], text_auto=True)
    fig_b.update_traces(textangle=0, textposition='outside')
    fig_b.update_layout(
        yaxis={'categoryorder':'total ascending'}, 
        showlegend=False, 
        height=max(400, len(disp_b)*28), 
        margin=dict(t=10, b=10, l=10, r=20), 
        font_family="Inter, sans-serif",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    # 6. Distribusi Skala Nilai Paket
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
    fig_r = px.bar(r_c, x='Range Pagu', y='count', color='Range Pagu', text_auto=True, height=350, 
                   color_discrete_map=range_color_map, category_orders={'Range Pagu': existing_order})
    fig_r.update_layout(showlegend=False, font_family="Inter, sans-serif", margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

    return {
        'fig_u': fig_u,
        'fig_p': fig_p,
        'fig_j': fig_j,
        'fig_m': fig_m,
        'fig_b': fig_b,
        'fig_r': fig_r
    }

def generate_html_report(df, active_filters):
    # Calculate metrics
    p = df['Pagu DIPA'].sum()
    k = df['Nilai Kontrak'].sum()
    pct = (k / p * 100) if p > 0 else 0.0
    total_paket = len(df)
    terkontrak_count = (df['Progres Paket'] == 'Terkontrak').sum()

    # Generate charts
    figs = generate_plotly_figures(df, det_unor=False, det_progres=False, all_bp2jk=False)
    
    # Convert charts to HTML div chunks (WITHOUT embedding plotly.js locally)
    chart_u_div = figs['fig_u'].to_html(include_plotlyjs=False, full_html=False, config={'displayModeBar': False})
    chart_p_div = figs['fig_p'].to_html(include_plotlyjs=False, full_html=False, config={'displayModeBar': False})
    chart_j_div = figs['fig_j'].to_html(include_plotlyjs=False, full_html=False, config={'displayModeBar': False})
    chart_m_div = figs['fig_m'].to_html(include_plotlyjs=False, full_html=False, config={'displayModeBar': False})

    # Generate tables
    df_rek = df[df['Progres Paket'] != 'Batal']
    rows_u, prog_u = generate_rekap_table(df_rek, 'Unor')
    rows_j, prog_j = generate_rekap_table(df_rek, 'Jenis Paket')
    rows_b, prog_b = generate_rekap_table(df_rek, 'BP2JK')

    table_u_html = render_rekap_html(rows_u, prog_u, "REKAP PAKET E-PURCHASING PER UNOR TA. 2026", "Unor") if rows_u else "<p>Tidak ada data Unor.</p>"
    table_j_html = render_rekap_html(rows_j, prog_j, "REKAP PAKET E-PURCHASING PER JENIS PAKET TA. 2026", "Jenis Paket") if rows_j else "<p>Tidak ada data Jenis Paket.</p>"
    table_b_html = render_rekap_html(rows_b, prog_b, "REKAP PAKET E-PURCHASING PER BALAI TA. 2026", "BP2JK Wilayah") if rows_b else "<p>Tidak ada data BP2JK.</p>"

    # Generate Filter active list
    filter_items = ""
    if active_filters:
        for key, val in active_filters.items():
            filter_items += f"""
            <div class="filter-item">
                <span class="filter-key">{key}:</span>
                <span class="filter-val">{val}</span>
            </div>"""
    else:
        filter_items = "<p style='color: #64748b; margin: 0;'>Semua Data (Tidak ada filter aktif)</p>"

    current_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    # Combine into unified premium HTML template
    html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Laporan Eksekutif E-Purchasing TA. 2026</title>
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #f8fafc;
            color: #1e293b;
            margin: 0;
            padding: 2rem 1.5rem;
            line-height: 1.5;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        /* BANNER HEADER */
        .report-header {{
            background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
            padding: 2.5rem;
            border-radius: 16px;
            color: white;
            box-shadow: 0 4px 20px rgba(30, 58, 138, 0.15);
            margin-bottom: 2rem;
            position: relative;
            overflow: hidden;
        }}
        .report-header::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 6px;
            background-color: #FFCC00;
        }}
        .report-header h1 {{
            margin: 0;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.5px;
        }}
        .report-header p {{
            margin: 0.5rem 0 0 0;
            font-size: 1rem;
            opacity: 0.95;
            font-weight: 500;
        }}
        .report-metadata {{
            margin-top: 1rem;
            font-size: 0.8rem;
            opacity: 0.8;
            display: flex;
            justify-content: space-between;
        }}

        /* FILTER BADGES */
        .filter-section {{
            background-color: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        }}
        .filter-section h3 {{
            margin: 0 0 0.75rem 0;
            font-size: 0.95rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #1e3a8a;
            font-weight: 700;
        }}
        .filter-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
        }}
        .filter-item {{
            background-color: #f1f5f9;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.4rem 0.8rem;
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .filter-key {{
            font-weight: 700;
            color: #475569;
        }}
        .filter-val {{
            color: #0f172a;
            font-weight: 500;
        }}

        /* METRIC CARDS */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1.25rem;
            margin-bottom: 2.5rem;
        }}
        .metric-card {{
            background-color: white;
            padding: 1.25rem;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.03);
            display: flex;
            align-items: center;
            gap: 1rem;
            position: relative;
        }}
        .card-blue {{ border-bottom: 5px solid #3b82f6; }}
        .card-green {{ border-bottom: 5px solid #10b981; }}
        .card-purple {{ border-bottom: 5px solid #8b5cf6; }}
        .card-amber {{ border-bottom: 5px solid #f59e0b; }}
        
        .icon-container {{
            width: 44px;
            height: 44px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            flex-shrink: 0;
        }}
        
        .metric-details {{
            display: flex;
            flex-direction: column;
            width: 100%;
        }}
        .metric-label {{
            font-size: 0.72rem;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .metric-value {{
            font-size: 1.35rem;
            font-weight: 800;
            color: #1e3a8a;
            margin-top: 0.15rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
        }}
        .metric-delta {{
            font-size: 0.7rem;
            font-weight: 700;
            color: #047857;
            background-color: #ecfdf5;
            padding: 0.15rem 0.4rem;
            border-radius: 12px;
            border: 1px solid #a7f3d0;
        }}
        
        .progress-container {{
            width: 100%;
            height: 5px;
            background-color: #e2e8f0;
            border-radius: 10px;
            margin-top: 0.4rem;
            overflow: hidden;
        }}
        .progress-bar {{
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        }}

        /* SECTION TILES */
        .section-title {{
            font-size: 1.35rem;
            color: #1e3a8a;
            font-weight: 800;
            margin: 3rem 0 1.5rem 0;
            border-left: 5px solid #FFCC00;
            padding-left: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        /* CHART GRID */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .chart-box {{
            background-color: white;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.03);
            break-inside: avoid;
            page-break-inside: avoid;
        }}
        .chart-box h4 {{
            margin: 0 0 1rem 0;
            color: #1e3a8a;
            font-weight: 700;
            font-size: 1rem;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 8px;
        }}
        .full-width {{
            grid-column: span 2;
        }}

        /* TABLES SECTION */
        .tables-section {{
            margin-top: 2rem;
        }}
        
        /* FLOATING PRINT BUTTON */
        .print-btn {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background-color: #FFCC00;
            color: #1e3a8a;
            border: none;
            padding: 12px 24px;
            font-size: 0.95rem;
            font-weight: 700;
            border-radius: 30px;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(0,0,0,0.18);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
        }}
        .print-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.22);
            background-color: #ffd633;
        }}

        /* RESPONSIVE DESIGN */
        @media (max-width: 992px) {{
            .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .charts-grid {{ grid-template-columns: 1fr; }}
            .full-width {{ grid-column: span 1; }}
        }}
        @media (max-width: 576px) {{
            .metrics-grid {{ grid-template-columns: 1fr; }}
            body {{ padding: 1rem; }}
        }}

        /* PRINT STYLES */
        @media print {{
            body {{
                background-color: white;
                padding: 0;
                margin: 0;
                font-size: 11px;
            }}
            .print-btn {{
                display: none !important;
            }}
            .report-header {{
                padding: 1.5rem;
                border-radius: 0;
                box-shadow: none;
                margin-bottom: 1.5rem;
            }}
            .metric-card {{
                box-shadow: none !important;
                border: 1px solid #cbd5e1 !important;
                padding: 0.8rem;
            }}
            .chart-box {{
                box-shadow: none !important;
                border: 1px solid #cbd5e1 !important;
                padding: 1rem;
                page-break-inside: avoid;
                break-inside: avoid;
            }}
            .section-title {{
                margin-top: 2rem;
                margin-bottom: 1rem;
            }}
            .page-break {{
                page-break-before: always;
                break-before: always;
            }}
        }}
    </style>
</head>
<body>

    <button class="print-btn" onclick="window.print()">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 6 2 18 2 18 9"/>
            <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
            <rect x="6" y="14" width="12" height="8"/>
        </svg>
        Cetak ke PDF / Simpan Laporan
    </button>

    <div class="container">
        
        <!-- HEADER BANNER -->
        <div class="report-header">
            <h1>LAPORAN EKSEKUTIF MONITORING E-PURCHASING TA. 2026</h1>
            <p>Konsolidasi Data Nasional (Inaproc) & Sistem Internal Monitoring (BP2JK & Iemon)</p>
            <div class="report-metadata">
                <span>Direktorat Pengadaan Jasa Konstruksi | Subdirektorat Katalog</span>
                <span>Dibuat: {current_time} WIB</span>
            </div>
        </div>

        <!-- FILTER SUMMARY -->
        <div class="filter-section">
            <h3>🔍 Filter yang Diterapkan</h3>
            <div class="filter-grid">
                {filter_items}
            </div>
        </div>

        <!-- METRICS -->
        <div class="metrics-grid">
            
            <!-- PAGU DIPA -->
            <div class="metric-card card-blue">
                <div class="icon-container" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2h-3"/><path d="M3 10h18"/></svg>
                </div>
                <div class="metric-details">
                    <span class="metric-label">Total Pagu DIPA</span>
                    <span class="metric-value">{format_idr(p)}</span>
                </div>
            </div>

            <!-- REALISASI -->
            <div class="metric-card card-green">
                <div class="icon-container" style="background: linear-gradient(135deg, #10b981 0%, #047857 100%);">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                </div>
                <div class="metric-details">
                    <span class="metric-label">Realisasi Kontrak</span>
                    <div class="metric-value">
                        <span>{format_idr(k)}</span>
                        <span class="metric-delta">↗ {pct:.1f}%</span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: {min(pct, 100.0):.1f}%;"></div>
                    </div>
                </div>
            </div>

            <!-- TOTAL PAKET -->
            <div class="metric-card card-purple">
                <div class="icon-container" style="background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><polygon points="12 22.08 12 12 3 6.92 3 17.08 12 22.08"/><polygon points="12 12 21 6.92 21 17.08 12 22.08"/><polygon points="12 2 3 6.92 12 12 21 6.92 12 2"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
                </div>
                <div class="metric-details">
                    <span class="metric-label">Total Paket Unik</span>
                    <span class="metric-value">{total_paket:,}</span>
                </div>
            </div>

            <!-- TERKONTRAK -->
            <div class="metric-card card-amber">
                <div class="icon-container" style="background: linear-gradient(135deg, #f59e0b 0%, #b45309 100%);">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>
                </div>
                <div class="metric-details">
                    <span class="metric-label">Paket Terkontrak</span>
                    <span class="metric-value">{terkontrak_count:,}</span>
                </div>
            </div>

        </div>

        <!-- SECTION ANALISIS VISUAL -->
        <div class="section-title">
            <span>📊 Analisis Visual Grafik</span>
        </div>

        <div class="charts-grid">
            
            <div class="chart-box">
                <h4>Jumlah Paket per Unor</h4>
                {chart_u_div}
            </div>

            <div class="chart-box">
                <h4>Progres Tahapan</h4>
                {chart_p_div}
            </div>

            <div class="chart-box">
                <h4>Distribusi Jenis Paket</h4>
                {chart_j_div}
            </div>

            <div class="chart-box">
                <h4>Metode E-Purchasing</h4>
                {chart_m_div}
            </div>

        </div>

        <!-- PAGE BREAK UNTUK PRINT TABEL AGAR RAPI -->
        <div class="page-break"></div>

        <!-- SECTION TABEL REKAPAN -->
        <div class="section-title">
            <span>📋 Tabel Rekapan Data</span>
        </div>

        <div class="tables-section">
            {table_u_html}
            {table_j_html}
            {table_b_html}
        </div>

    </div>

</body>
</html>
"""
    return html_content
