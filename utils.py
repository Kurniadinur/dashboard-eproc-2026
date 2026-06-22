import pandas as pd
import numpy as np

def clean_currency_vectorized(series):
    if series is None or series.empty: return pd.Series(0.0)
    # 1. Hapus Rp, spasi, dan titik (ribuan)
    s = series.astype(str).str.replace('Rp','',regex=False).str.replace(' ','',regex=False).str.replace('.','',regex=False)
    # 2. Ubah koma (desimal Indo) menjadi titik (desimal Python)
    s = s.str.replace(',','.',regex=False).str.strip()
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

# Helper function to generate table data for Rekapan
def generate_rekap_table(df, group_col):
    if group_col == 'Unor':
        predefined = ['SEKJEN', 'ITJEN', 'SDA', 'BM', 'CK', 'PS', 'BK', 'PI', 'BPIW', 'BPSDM']
        all_unors = df[group_col].fillna('Belum Info').unique()
        categories = [u for u in predefined if u in all_unors] + sorted([u for u in all_unors if u not in predefined and u != 'Belum Info'])
        if 'Belum Info' in all_unors:
            categories.append('Belum Info')
    elif group_col == 'BP2JK':
        predefined = [
            'Aceh', 'Sumatera Utara', 'Sumatera Barat', 'Riau', 'Kepulauan Riau', 
            'Sumatera Selatan', 'Kepulauan Bangka Belitung', 'Jambi', 'Bengkulu', 'Lampung', 
            'DKI Jakarta', 'Jawa Barat', 'Banten', 'Jawa Tengah', 'D.I. Yogyakarta', 
            'Jawa Timur', 'Kalimantan Selatan', 'Kalimantan Barat', 'Kalimantan Tengah', 'Kalimantan Timur', 
            'Kalimantan Utara', 'Bali', 'Nusa Tenggara Barat', 'Nusa Tenggara Timur', 'Sulawesi Selatan', 
            'Sulawesi Tenggara', 'Sulawesi Tengah', 'Sulawesi Barat', 'Sulawesi Utara', 'Gorontalo', 
            'Maluku', 'Maluku Utara', 'Papua', 'Papua Barat', 'Pusat'
        ]
        all_balai = df[group_col].fillna('Belum Info').unique()
        balai_map = {b.upper().strip(): b for b in all_balai}
        categories = []
        for p in predefined:
            p_upper = p.upper().strip()
            if p_upper in balai_map:
                categories.append(balai_map[p_upper])
        predefined_upper = [p.upper().strip() for p in predefined]
        extra_categories = sorted([b for b in all_balai if b.upper().strip() not in predefined_upper and b != 'Belum Info'])
        categories.extend(extra_categories)
        if 'Belum Info' in all_balai:
            categories.append('Belum Info')
    else:
        predefined = ['BARANG', 'AU', 'PEKERJAAN KONSTRUKSI', 'JASA KONSULTASI', 'JASA LAINNYA']
        all_jenis = df[group_col].fillna('Belum Info').unique()
        categories = [j for j in predefined if j in all_jenis] + sorted([j for j in all_jenis if j not in predefined and j != 'Belum Info'])
        if 'Belum Info' in all_jenis:
            categories.append('Belum Info')
            
    progres_list = ['Belum Proses', 'Proses E-Purchasing', 'Persiapan Terkontrak', 'Terkontrak']
    
    rows = []
    for cat in categories:
        cat_df = df[df[group_col].fillna('Belum Info') == cat]
        if cat_df.empty:
            continue
        
        row = {
            'name': cat,
            'count': len(cat_df),
            'pagu_dipa': cat_df['Pagu DIPA'].sum(),
            'pagu_pengadaan': cat_df['Pagu Pengadaan'].sum(),
        }
        
        for prog in progres_list:
            prog_df = cat_df[cat_df['Progres Paket'] == prog]
            row[f'{prog}_count'] = len(prog_df)
            row[f'{prog}_pagu_dipa'] = prog_df['Pagu DIPA'].sum()
            row[f'{prog}_pagu_pengadaan'] = prog_df['Pagu Pengadaan'].sum()
            
        rows.append(row)
        
    return rows, progres_list

def render_rekap_html(rows, progres_list, title, type_label):
    html = f"""<div style="overflow-x: auto; margin-bottom: 2.5rem;">
<div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #FFCC00; padding-bottom: 10px; margin-bottom: 15px;">
<h3 style="color: #1e3a8a; margin: 0; font-family: 'Inter', sans-serif; font-weight: 800; font-size: 1.25rem;">{title}</h3>
<span style="color: #64748b; font-size: 0.85rem; font-weight: 600;">Subdit Katalog | E-Purchasing TA. 2026</span>
</div>
<table style="width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; font-size: 0.82rem; text-align: center; color: #1e293b;">
<thead>
<tr style="background-color: #1e3a8a; color: white;">
<th rowspan="3" style="border: 1px solid #cbd5e1; padding: 10px 5px; font-weight: 700; width: 40px;">No</th>
<th rowspan="3" style="border: 1px solid #cbd5e1; padding: 10px 10px; font-weight: 700; text-align: left; min-width: 150px;">{type_label}</th>
<th rowspan="3" style="border: 1px solid #cbd5e1; padding: 10px 5px; font-weight: 700;">Jumlah Paket</th>
<th rowspan="3" style="border: 1px solid #cbd5e1; padding: 10px 5px; font-weight: 700;">Total Pagu DIPA<br>(Rp Ribu)</th>
<th rowspan="3" style="border: 1px solid #cbd5e1; padding: 10px 5px; font-weight: 700;">Total Pagu Pengadaan<br>(Rp Ribu)</th>
<th colspan="12" style="border: 1px solid #cbd5e1; padding: 5px; font-weight: 700; background-color: #1a365d;">Progres Paket</th>
</tr>
<tr style="background-color: #1e3a8a; color: white;">"""
    for prog in progres_list:
        html += f"""<th colspan="3" style="border: 1px solid #cbd5e1; padding: 5px; font-weight: 700; background-color: #1a365d;">{prog}</th>"""
        
    html += """</tr>
<tr style="background-color: #2563eb; color: white; font-size: 0.75rem;">"""
    for prog in progres_list:
        html += """<th style="border: 1px solid #cbd5e1; padding: 3px; font-weight: 600;">Jml Pkt</th>
<th style="border: 1px solid #cbd5e1; padding: 3px; font-weight: 600;">Pagu DIPA<br>(Rp Ribu)</th>
<th style="border: 1px solid #cbd5e1; padding: 3px; font-weight: 600;">Pagu Pengd<br>(Rp Ribu)</th>"""
        
    html += """</tr>
</thead>
<tbody>"""
    
    def fmt_val(val, is_count=False):
        if val == 0:
            return "-"
        if is_count:
            return f"{val:,}"
        ribu_val = val / 1000
        return f"{ribu_val:,.0f}".replace(",", ".")

    for idx, r in enumerate(rows):
        bg_color = "#ffffff" if idx % 2 == 0 else "#f8fafc"
        html += f"""<tr style="background-color: {bg_color}; border-bottom: 1px solid #e2e8f0; font-weight: 500;">
<td style="border: 1px solid #cbd5e1; padding: 8px 5px;">{idx + 1}</td>
<td style="border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; font-weight: 600;">{r['name'].upper()}</td>
<td style="border: 1px solid #cbd5e1; padding: 8px 5px;">{fmt_val(r['count'], is_count=True)}</td>
<td style="border: 1px solid #cbd5e1; padding: 8px 5px; text-align: right; font-weight: 600; color: #1e3a8a;">{fmt_val(r['pagu_dipa'])}</td>
<td style="border: 1px solid #cbd5e1; padding: 8px 5px; text-align: right; font-weight: 600; color: #0f766e;">{fmt_val(r['pagu_pengadaan'])}</td>"""
        for prog in progres_list:
            c = r[f'{prog}_count']
            pdipa = r[f'{prog}_pagu_dipa']
            ppeng = r[f'{prog}_pagu_pengadaan']
            
            html += f"""<td style="border: 1px solid #cbd5e1; padding: 8px 5px;">{fmt_val(c, is_count=True)}</td>
<td style="border: 1px solid #cbd5e1; padding: 8px 5px; text-align: right; color: #475569;">{fmt_val(pdipa)}</td>
<td style="border: 1px solid #cbd5e1; padding: 8px 5px; text-align: right; color: #475569;">{fmt_val(ppeng)}</td>"""
            
        html += "</tr>"
        
    total_count = sum(r['count'] for r in rows)
    total_pagu_dipa = sum(r['pagu_dipa'] for r in rows)
    total_pagu_peng = sum(r['pagu_pengadaan'] for r in rows)
    
    html += f"""<tr style="background-color: #fef08a; font-weight: 800; border-top: 2px solid #eab308; border-bottom: 2px solid #eab308; color: #854d0e;">
<td colspan="2" style="border: 1px solid #cbd5e1; padding: 10px; text-align: center;">TOTAL</td>
<td style="border: 1px solid #cbd5e1; padding: 10px;">{total_count:,}</td>
<td style="border: 1px solid #cbd5e1; padding: 10px; text-align: right;">{fmt_val(total_pagu_dipa)}</td>
<td style="border: 1px solid #cbd5e1; padding: 10px; text-align: right;">{fmt_val(total_pagu_peng)}</td>"""
    
    for prog in progres_list:
        c_tot = sum(r[f'{prog}_count'] for r in rows)
        pdipa_tot = sum(r[f'{prog}_pagu_dipa'] for r in rows)
        ppeng_tot = sum(r[f'{prog}_pagu_pengadaan'] for r in rows)
        
        html += f"""<td style="border: 1px solid #cbd5e1; padding: 10px;">{fmt_val(c_tot, is_count=True)}</td>
<td style="border: 1px solid #cbd5e1; padding: 10px; text-align: right;">{fmt_val(pdipa_tot)}</td>
<td style="border: 1px solid #cbd5e1; padding: 10px; text-align: right;">{fmt_val(ppeng_tot)}</td>"""
        
    html += """</tr>
</tbody>
</table>
</div>
</div>"""
    return html

