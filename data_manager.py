import streamlit as st
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from utils import clean_currency_vectorized, normalize_status_vectorized

URL_BP2JK = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=1807383381&single=true&output=csv"
URL_IEMON = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=881219520&single=true&output=csv"
URL_INAPROC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR_NSdT2sPeoj9eIR15xqKuveTexcqiiwc0w_pO-ofCbizx5XvknIsM5bNWUDwUBNrmmMAmMIC-pcHb/pub?gid=189207385&single=true&output=csv"

import time
import os
import datetime

def read_csv_with_retry(src, max_retries=3, backoff_factor=1.5):
    def is_valid_df(df):
        if df is None or df.empty or len(df) < 5:
            return False
        cols = [str(c).strip() for c in df.columns]
        cols_upper = [c.upper() for c in cols]
        
        # Jika kolom pertama tampak seperti baris judul Google Sheets, anggap tidak valid
        first_col = cols[0]
        if first_col.upper().startswith("DAFTAR PAKET") or first_col.upper().startswith("STATUS DATA") or len(first_col) > 30:
            return False
            
        key_words = ['SIRUP', 'RUP', 'PAKET', 'PAGU', 'KONTRAK', 'BP2JK', 'SATKER', 'UNIT']
        match_count = 0
        for k in key_words:
            if any(k in c for c in cols_upper):
                match_count += 1
        return match_count >= 2

    def try_parse(source):
        # 1. Coba dengan skiprows=4 (standar sheet raw)
        try:
            df = pd.read_csv(source, skiprows=4)
            df.columns = df.columns.str.strip()
            if is_valid_df(df):
                return df
        except Exception:
            pass
        # 2. Coba dengan skiprows=None (standar backup bersih)
        try:
            df = pd.read_csv(source, skiprows=None)
            df.columns = df.columns.str.strip()
            if is_valid_df(df):
                return df
        except Exception:
            pass
        return None

    # Jika src bukan URL, langsung baca lokal
    if isinstance(src, str) and not (src.startswith("http://") or src.startswith("https://")):
        df = try_parse(src)
        if df is not None:
            return df
        raise ValueError(f"Gagal memuat berkas lokal valid dari: {src}")

    # Unduh dengan retry dan cache-busting untuk URL
    retries = 0
    delay = 1.0
    last_exception = None
    while retries < max_retries:
        try:
            sep = "&" if "?" in src else "?"
            url_to_fetch = f"{src}{sep}t={int(time.time())}"
            df = try_parse(url_to_fetch)
            if df is not None:
                return df
            raise ValueError("Data yang diunduh tidak valid (format salah atau kosong).")
        except Exception as e:
            last_exception = e
            retries += 1
            if retries >= max_retries:
                break
            time.sleep(delay)
            delay *= backoff_factor
            
    raise last_exception

@st.cache_data(ttl=600)
def load_and_process_all(files=None):
    urls = {"BP2JK": URL_BP2JK, "Iemon": URL_IEMON, "Inaproc": URL_INAPROC}
    
    def process_source(name, url):
        src = files[name] if (files and files.get(name)) else url
        is_fallback = False
        fallback_time = ""
        backup_dir = "backup_data"
        backup_path = os.path.join(backup_dir, f"{name}_fallback.csv")
        baseline_path = f"GS Monev E-Purchasing TA.2026 - Monev {name}.csv"
        
        df = pd.DataFrame()
        try:
            # 1. Coba download dari internet dengan retry
            df = read_csv_with_retry(src)
            # Jika sukses memuat, simpan ke backup lokal (Penyimpanan Sementara)
            if not df.empty:
                os.makedirs(backup_dir, exist_ok=True)
                df.to_csv(backup_path, index=False)
        except Exception as e:
            # 2. Jika gagal download, coba load dari cadangan lokal (fallback)
            if os.path.exists(backup_path):
                try:
                    df = read_csv_with_retry(backup_path)
                    is_fallback = True
                    mtime = os.path.getmtime(backup_path)
                    dt = datetime.datetime.fromtimestamp(mtime)
                    fallback_time = dt.strftime("%d-%m-%Y %H:%M")
                except Exception as backup_err:
                    df = pd.DataFrame()
            
            # 3. Jika cadangan lokal gagal, coba load dari baseline Git di root
            if df.empty and os.path.exists(baseline_path):
                try:
                    df = read_csv_with_retry(baseline_path)
                    is_fallback = True
                    mtime = os.path.getmtime(baseline_path)
                    dt = datetime.datetime.fromtimestamp(mtime)
                    fallback_time = dt.strftime("%d-%m-%Y %H:%M") + " (Baseline Git)"
                except Exception as baseline_err:
                    df = pd.DataFrame()
                    
        dupes = pd.DataFrame()
        if not df.empty:
            df.columns = df.columns.str.strip()
            sirup_keywords = ['SIRUP', 'KODE RUP', 'ID RUP', 'ID_RUP', 'KODE_RUP']
            sirup_col = next((c for c in df.columns if any(k in c.upper() for k in sirup_keywords)), None)
            
            if sirup_col:
                # Normalisasi ID SIRUP
                df['ID SIRUP'] = df[sirup_col].astype(str).str.strip().str.lower().str.replace(r'\.0+$', '', regex=True)
                invalid_ids = ['', 'nan', 'none', '0', '-', 'nan.0', 'null']
                mask_valid_sirup = ~df['ID SIRUP'].isin(invalid_ids)
                
                if name == "Inaproc":
                    # Inaproc: Simpan semua transaksi (nanti diagregasi di build_master)
                    dupes = pd.DataFrame()
                elif 'Kode Paket' in df.columns:
                    df['Kode Paket'] = df['Kode Paket'].astype(str).str.strip().replace(['nan', 'None', 'null', '0', '-'], '')
                    mask_invalid = df['ID SIRUP'].isin(invalid_ids)
                    
                    # Pastikan ID SIRUP 'missing' juga unik dengan menambahkan index jika Kode Paket kosong
                    missing_ids = "missing-" + df['Kode Paket'].str.lower()
                    mask_empty_kode = (df['Kode Paket'] == "") | (df['Kode Paket'].isna())
                    missing_ids = np.where(mask_empty_kode, "missing-unk-" + df.index.astype(str), missing_ids)
                    
                    df['ID SIRUP'] = np.where(mask_invalid, missing_ids, df['ID SIRUP'])
                    
                    # Cek duplikat hanya untuk Kode Paket yang TIDAK KOSONG
                    mask_has_kode = (df['Kode Paket'] != "") & (df['Kode Paket'].notna())
                    dupes = df[mask_has_kode & df.duplicated('Kode Paket', keep=False)].copy()
                    
                    # Drop duplicates hanya pada baris yang punya Kode Paket
                    df_with_kode = df[mask_has_kode].drop_duplicates('Kode Paket', keep='last')
                    df_no_kode = df[~mask_has_kode]
                    df = pd.concat([df_with_kode, df_no_kode], ignore_index=True)
                else:
                    dupes = df[mask_valid_sirup & df.duplicated('ID SIRUP', keep=False)].copy()
                    df = df[~df['ID SIRUP'].isin(invalid_ids)]
                    df = df.drop_duplicates('ID SIRUP', keep='last')
            else:
                # Fallback jika tidak ketemu kolom SIRUP tapi ada Kode Paket
                if 'Kode Paket' in df.columns:
                    df['Kode Paket'] = df['Kode Paket'].astype(str).str.strip()
                    df['ID SIRUP'] = "missing-" + df['Kode Paket'].str.lower()
                else:
                    df['ID SIRUP'] = "unknown-" + pd.Series(range(len(df))).astype(str)
            
        return name, df, dupes, is_fallback, fallback_time
 
    raw, stats, all_dupes = {}, {}, {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(lambda x: process_source(*x), urls.items()))
    
    for name, df, dupes, is_fallback, fallback_time in results:
        raw[name] = df
        stats[name] = len(df)
        all_dupes[name] = dupes
        stats[f"{name}_fallback"] = is_fallback
        stats[f"{name}_fallback_time"] = fallback_time
        
    return raw, stats, all_dupes

def clean_and_prep_internal(df, source_name):
    # Selalu pastikan Kode Paket ada, meskipun data kosong
    if df is None or df.empty: 
        return pd.DataFrame(columns=['Kode Paket', 'ID SIRUP', 'Nama Paket', 'Unor', 'Satker', 'BP2JK', 'Jenis Paket', 'p_c', 'pp_c', 'nk_c', 'status_norm', 'status_raw', 'metode_norm', 'nama_clean'])
    
    d = df.copy()
    
    # 1. Normalize Kode Paket (Kunci Utama)
    if 'Kode Paket' in d.columns:
        # Bersihkan string dan ubah nilai-nilai 'kosong' menjadi NaN agar mudah diproses
        d['Kode Paket'] = d['Kode Paket'].astype(str).str.strip().replace(['nan', 'None', 'null', '0', '-', ''], np.nan)
        
        # Jika ada yang kosong, beri ID Unik berbasis Index dan Nama Source agar tidak bentrok antar file
        mask_missing = d['Kode Paket'].isna()
        if mask_missing.any():
            d.loc[mask_missing, 'Kode Paket'] = f"TEMP-{source_name}-" + d.index[mask_missing].astype(str)
    else:
        # Jika kolom Kode Paket memang tidak ada sama sekali
        d['Kode Paket'] = f"TEMP-{source_name}-" + d.index.astype(str)
        
    # 2. Currency
    p_col = 'Pagu RAKL (Rp Ribu)'
    pp_col = 'Pagu Pengadaan (Rp Ribu)'
    nk_col = 'Nilai Kontrak'
    nk_v_col = 'Nilai Kontrak (Rp Ribu)'
    
    d['p_c'] = clean_currency_vectorized(d[p_col]) * 1000 if p_col in d.columns else 0.0
    d['pp_c'] = clean_currency_vectorized(d[pp_col]) * 1000 if pp_col in d.columns else 0.0
    
    nk_aw = clean_currency_vectorized(d[nk_col]) if nk_col in d.columns else pd.Series(0.0, index=d.index)
    nk_v = clean_currency_vectorized(d[nk_v_col]) * 1000 if nk_v_col in d.columns else pd.Series(0.0, index=d.index)
    
    d['nk_c'] = np.where(nk_aw > 0, nk_aw, nk_v)
    
    # 3. Status
    status_col = 'Progres Paket' if 'Progres Paket' in d.columns else ('Status Kontrak' if 'Status Kontrak' in d.columns else None)
    raw_status_vals = d[status_col].fillna("Belum Proses") if status_col else pd.Series("Belum Proses", index=d.index)
    d['status_raw'] = raw_status_vals.astype(str).str.strip()
    d['status_norm'] = normalize_status_vectorized(raw_status_vals, source=source_name)
    
    # 4. Metode
    m_ep = d['Metode E-Purchasing'].astype(str).str.upper() if 'Metode E-Purchasing' in d.columns else pd.Series("", index=d.index)
    m_p = d['Metode Pemilihan'].astype(str).str.upper() if 'Metode Pemilihan' in d.columns else pd.Series("", index=d.index)
    d['metode_norm'] = np.where(m_ep.str.contains('MINI') | m_p.str.contains('MINI'), "Minikompetisi",
                        np.where(m_ep.str.contains('NEGOSIASI|SURAT PESANAN|PURCHASING') | m_p.str.contains('NEGOSIASI|SURAT PESANAN|PURCHASING'), "Negosiasi", "Belum Info"))
    
    # 5. Clean Nama Paket (untuk matching fallback)
    if 'Nama Paket' in d.columns:
        d['nama_clean'] = d['Nama Paket'].astype(str).str.lower().str.replace(r'[^a-z0-9]', '', regex=True).str.strip()
    else:
        d['nama_clean'] = ""
    
    return d

@st.cache_data
def build_master(raw):
    # --- PHASE 1: PREP INTERNAL ---
    df_bp = clean_and_prep_internal(raw.get("BP2JK"), "BP2JK")
    df_ie = clean_and_prep_internal(raw.get("Iemon"), "Iemon")
    
    # --- PHASE 2: CONSOLIDATE INTERNAL ---
    if df_bp.empty and df_ie.empty:
        return pd.DataFrame()
    
    # Merge HANYA jika keduanya punya data, jika salah satu kosong ambil yang ada
    if not df_bp.empty and not df_ie.empty:
        internal = pd.merge(df_bp, df_ie, on='Kode Paket', how='outer', suffixes=('_bp', '_ie'))
    elif not df_bp.empty:
        internal = df_bp.rename(columns={c: f"{c}_bp" for c in df_bp.columns if c != 'Kode Paket'})
        internal['Kode Paket'] = df_bp['Kode Paket']
    else:
        internal = df_ie.rename(columns={c: f"{c}_ie" for c in df_ie.columns if c != 'Kode Paket'})
        internal['Kode Paket'] = df_ie['Kode Paket']
    
    # Resolve conflicting columns (Prefer BP2JK)
    master = pd.DataFrame(index=internal.index)
    cols_to_resolve = ['ID SIRUP', 'Nama Paket', 'Unor', 'Satker', 'BP2JK', 'Jenis Paket', 'status_norm', 'status_raw', 'metode_norm', 'p_c', 'pp_c', 'nk_c', 'nama_clean', 'Rekanan']
    
    for c in cols_to_resolve:
        c_bp, c_ie = f"{c}_bp", f"{c}_ie"
        if c_bp in internal.columns and c_ie in internal.columns:
            if c in ['p_c', 'pp_c', 'nk_c']:
                master[c] = np.maximum(internal[c_bp].fillna(0), internal[c_ie].fillna(0))
            else:
                master[c] = internal[c_bp].fillna(internal[c_ie])
        elif c_bp in internal.columns:
            master[c] = internal[c_bp]
        elif c_ie in internal.columns:
            master[c] = internal[c_ie]
        else:
            master[c] = ""
    
    master['Kode Paket'] = internal['Kode Paket']
    master['In BP2JK'] = internal['ID SIRUP_bp'].notna() if 'ID SIRUP_bp' in internal.columns else (~df_bp.empty if not df_bp.empty else False)
    master['In Iemon'] = internal['ID SIRUP_ie'].notna() if 'ID SIRUP_ie' in internal.columns else (~df_ie.empty if not df_ie.empty else False)
    
    # --- PHASE 3: PREP INAPROC (NO AGGREGATION) ---
    df_ina = raw.get("Inaproc", pd.DataFrame()).copy()
    if not df_ina.empty:
        df_ina['nk_c'] = clean_currency_vectorized(df_ina['Nilai Kontrak'])
        
        # Dinamis deteksi kolom
        ina_nama_col = next((c for c in ['Nama Paket', 'Paket', 'Nama_Paket', 'Uraian Pekerjaan'] if c in df_ina.columns), None)
        ina_unor_col = next((c for c in ['Unor', 'Instansi', 'Kementerian', 'Lembaga', 'Unit Kerja', 'Unit Organisasi'] if c in df_ina.columns), None)
        ina_satker_col = next((c for c in ['Satuan Kerja', 'Satker', 'Nama Satker'] if c in df_ina.columns), None)
        rek_col_ina = next((c for c in ['Rekanan', 'Nama Rekanan', 'Rekanan '] if c in df_ina.columns), None)
        ina_jenis_col = next((c for c in ['Jenis Paket', 'Jenis Pengadaan', 'Jenis'] if c in df_ina.columns), None)
        
        # Rename untuk standardisasi (Langsung di raw agar detail data juga terbaca)
        rename_map = {}
        if ina_nama_col: rename_map[ina_nama_col] = 'Nama Paket'
        if ina_unor_col: rename_map[ina_unor_col] = 'Instansi'
        if ina_satker_col: rename_map[ina_satker_col] = 'Satuan Kerja'
        if rek_col_ina: rename_map[rek_col_ina] = 'Rekanan'
        if ina_jenis_col: rename_map[ina_jenis_col] = 'Jenis Paket_ina'
        
        if rename_map: df_ina = df_ina.rename(columns=rename_map)
        
        # Pastikan kolom Nama Paket ada
        if 'Nama Paket' not in df_ina.columns: 
            ina_nama_col = next((c for c in ['Nama Paket', 'Paket', 'Nama_Paket', 'Uraian Pekerjaan'] if c in df_ina.columns), None)
            if ina_nama_col: df_ina = df_ina.rename(columns={ina_nama_col: 'Nama Paket'})
            else: df_ina['Nama Paket'] = "Tanpa Nama"

        # Pastikan kolom mandatory ada di df_ina agar tidak error saat merge
        for c in ['Instansi', 'Satuan Kerja', 'Rekanan', 'Jenis Paket_ina']:
            if c not in df_ina.columns: df_ina[c] = ""
    
    # --- PHASE 4: CONSOLIDATE (INAPROC-CENTRIC) ---
    # 1. Start with Inaproc as base (Every Inaproc row is a unique package)
    if not df_ina.empty:
        # Buat mapping dari internal (Ambil info internal berdasarkan ID SIRUP)
        # Jika satu ID SIRUP punya beberapa Kode Paket di internal, kita ambil yang pertama
        internal_valid = master[~master['ID SIRUP'].str.contains('missing-|unknown-|unk-|^$', case=False, na=False)]
        internal_lookup = internal_valid.drop_duplicates('ID SIRUP').set_index('ID SIRUP')
        
        # Match Inaproc rows to Internal info
        master_ina = df_ina.copy()
        cols_to_map = ['Kode Paket', 'Unor', 'Satker', 'BP2JK', 'Jenis Paket', 'status_norm', 'status_raw', 'metode_norm', 'p_c', 'pp_c', 'In BP2JK', 'In Iemon']
        for col in cols_to_map:
            if col in internal_lookup.columns:
                mapped = master_ina['ID SIRUP'].map(internal_lookup[col])
                if col in master_ina.columns:
                    master_ina[col] = mapped.fillna(master_ina[col])
                else:
                    master_ina[col] = mapped
        
        # Fallback values for Inaproc matching results
        master_ina['In BP2JK'] = master_ina['In BP2JK'].fillna(False)
        master_ina['In Iemon'] = master_ina['In Iemon'].fillna(False)
        master_ina['Kode Paket'] = master_ina['Kode Paket'].fillna("INAPROC-ONLY")
        
        # UTAMA: Pastikan Unor, Satker, dan Jenis Paket terisi dari Inaproc jika matching internal gagal
        master_ina['Unor'] = master_ina['Unor'].fillna(master_ina['Instansi'])
        master_ina['Satker'] = master_ina['Satker'].fillna(master_ina['Satuan Kerja'])
        master_ina['Jenis Paket'] = master_ina['Jenis Paket'].fillna(master_ina['Jenis Paket_ina'])
        
        master_ina['status_norm'] = "Terkontrak" # Inaproc default status
        master_ina['status_raw'] = master_ina['status_raw'].fillna("Terkontrak (Nasional)")
        master_ina['nk_c_final'] = master_ina['nk_c']
        master_ina['In Inaproc'] = True
        
        # Cek mana saja paket internal yang TIDAK masuk di Inaproc
        # Gunakan Kode Paket yang terpetakan untuk menyaring agar record duplikat ID SIRUP tidak hilang
        matched_kodes = master_ina['Kode Paket'].dropna().unique()
        matched_kodes = [k for k in matched_kodes if k != "INAPROC-ONLY"]
        internal_only = master[~master['Kode Paket'].isin(matched_kodes)].copy()
        internal_only['nk_c_final'] = internal_only['nk_c']
        internal_only['In Inaproc'] = False
        
        # Gabungkan keduanya
        master_final = pd.concat([master_ina, internal_only], ignore_index=True)
    else:
        # Jika Inaproc kosong, Master adalah semua data internal
        master_final = master.copy()
        master_final['nk_c_final'] = master_final['nk_c']
        master_final['In Inaproc'] = False
    
    # Track source availability for all records
    master_final['In BP2JK'] = master_final['In BP2JK'].fillna(False)
    master_final['In Iemon'] = master_final['In Iemon'].fillna(False)
    master_final['In Inaproc'] = master_final['In Inaproc'].fillna(False)

    # --- PHASE 5: FINAL CLEANUP ---
    res = pd.DataFrame()
    res['ID SIRUP'] = master_final['ID SIRUP'].fillna("")
    res['Kode Paket'] = master_final['Kode Paket'].fillna("")
    res['Nama Paket'] = master_final['Nama Paket'].fillna("")
    
    # Pengisian Unor yang lebih robust
    if 'Unor' in master_final.columns:
        res['Unor'] = master_final['Unor'].fillna(master_final.get('Instansi', "Belum Info"))
    else:
        res['Unor'] = master_final.get('Instansi', "Belum Info")
        
    res['Satker'] = master_final['Satker'].fillna(master_final.get('Satuan Kerja', ""))
    res['BP2JK'] = master_final['BP2JK'].fillna("Belum Info").replace(['', 'nan', 'None'], 'Belum Info')
    res['Jenis Paket'] = master_final['Jenis Paket'].fillna("Belum Info").replace(['', 'nan', 'None'], 'Belum Info')
    res['Progres Paket'] = master_final['status_norm'].fillna("Belum Proses")
    res['Progres Raw'] = master_final['status_raw'].fillna("Belum Proses")
    res['Metode EP'] = master_final['metode_norm'].fillna("Belum Info")
    res['Pagu DIPA'] = master_final['p_c'].fillna(0.0)
    res['Pagu Pengadaan'] = master_final['pp_c'].fillna(0.0)
    res['Nilai Kontrak'] = master_final['nk_c_final'].fillna(0.0)
    res['Rekanan'] = master_final['Rekanan'].fillna("") if 'Rekanan' in master_final.columns else ""
    
    # In-source flags
    for n in ["BP2JK", "Iemon", "In Inaproc"]:
        col_src = n if n == "In Inaproc" else f"In {n}"
        res[col_src] = master_final[col_src].fillna(False)
    
    # Status Pagu
    res['Status Pagu'] = "✅ AMAN"
    res.loc[(res['Pagu DIPA'] <= 0) & (res['Nilai Kontrak'] > 2), 'Status Pagu'] = "⚠️ PAGU KOSONG (INAPROC ONLY)"
    res.loc[(res['Nilai Kontrak'] - res['Pagu DIPA'] > 2000000) & (res['Pagu DIPA'] > 0), 'Status Pagu'] = "❗ MELEBIHI PAGU"
    
    # Range Pagu
    res['Range Pagu'] = "Pagu Kosong (Rp 0)"
    mask_has_pagu = res['Pagu DIPA'] > 0
    bins = [0, 200e6, 2e9, 15e9, 50e9, float('inf')]
    labels = ['< 200Jt', '200Jt - 2M', '2M - 15M', '15M - 50M', '> 50M']
    res.loc[mask_has_pagu, 'Range Pagu'] = pd.cut(res.loc[mask_has_pagu, 'Pagu DIPA'], bins=bins, labels=labels, include_lowest=False).astype(str)
    res['Range Pagu'] = res['Range Pagu'].fillna("Pagu Kosong (Rp 0)")

    return res
