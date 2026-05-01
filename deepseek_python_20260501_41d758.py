# VirVentures FBA Enrichment Engine
# Full Production Code - Updated for Pandas 3.x Compatibility

import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import csv
import chardet
import re
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG & STYLING
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VirVentures · FBA Enrichment",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
    .reportview-container { background: #0a0c10; color: #e8ecf4; }
    .virv-header { border-bottom: 1px solid #1e2230; margin-bottom: 20px; padding-bottom: 10px; }
    .virv-logo { font-weight: bold; color: #00e5a0; border: 1px solid #00e5a0; padding: 5px 10px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
HISTORY_FILE = "history.csv"
MISSING_VALUES = {"", "0", "0.0", "na", "n/a", "none", "nan", "null"}

STANDARD_MAP = {
    "sku": ["sku", "model#", "model number", "item code", "seller sku"],
    "asin": ["asin", "amazon asin", "output asin"],
    "stock": ["stock", "afn-fulfillable-quantity", "available qty"],
    "reserve": ["reserve", "reserved", "afn-reserved-quantity"],
    "inbound": ["inbound", "inbound quantity", "afn-inbound-shipped-quantity"],
    "brand": ["brand", "brand name", "manufacturer"],
}

def clean_value(val):
    if val is None or (isinstance(val, float) and np.isnan(val)): return None
    s = str(val).strip()
    return None if s.lower() in MISSING_VALUES else s

def safe_int(val):
    try: return int(float(clean_value(val) or 0))
    except: return 0

def normalize_col(col):
    return re.sub(r"\s+", " ", str(col).strip().lower())

# ─────────────────────────────────────────────────────────────────────────────
# DATA PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def universal_file_reader(uploaded_file):
    if uploaded_file is None: return None
    try:
        raw_bytes = uploaded_file.getvalue()
        detected = chardet.detect(raw_bytes[:10000])
        enc = detected.get("encoding") or "utf-8"
        
        if uploaded_file.name.endswith(('.xlsx', '.xls')):
            return pd.read_excel(io.BytesIO(raw_bytes), dtype=str)
        else:
            return pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, dtype=str, on_bad_lines="skip")
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

def auto_map_columns(df):
    cols_norm = {normalize_col(c): c for c in df.columns}
    return {k: next((cols_norm[a] for a in aliases if a in cols_norm), None) for k, aliases in STANDARD_MAP.items()}

def build_inventory_lookup(inv_df):
    lookup = {}
    if inv_df is None: return lookup
    m = auto_map_columns(inv_df)
    for _, row in inv_df.iterrows():
        sku, asin = clean_value(row.get(m['sku'])), clean_value(row.get(m['asin']))
        data = {"stock": safe_int(row.get(m['stock'])), "reserve": safe_int(row.get(m['reserve'])), "inbound": safe_int(row.get(m['inbound']))}
        if sku: lookup[sku.lower()] = data
        if asin: lookup[asin.lower()] = data
    return lookup

def enrich_main(main_df, inv_lookup, restricted_brands):
    # CRITICAL FIX: Convert to object to avoid Arrow/String TypeError in Pandas 3.x
    df = main_df.copy().astype(object)
    m = auto_map_columns(df)
    stats = {"stock_filled": 0, "restricted_flagged": 0}
    
    for col in ["Stock", "Reserve", "Inbound", "TOTAL", "Restricted"]:
        if col not in df.columns: df[col] = None

    for i, row in df.iterrows():
        sku = (clean_value(row.get(m['sku'])) or "").lower()
        asin = (clean_value(row.get(m['asin'])) or "").lower()
        
        data = inv_lookup.get(sku) or inv_lookup.get(asin)
        if data:
            df.at[i, "Stock"] = data["stock"]
            df.at[i, "Reserve"] = data["reserve"]
            df.at[i, "Inbound"] = data["inbound"]
            df.at[i, "TOTAL"] = data["stock"] + data["reserve"] + data["inbound"]
            stats["stock_filled"] += 1
            
        brand = (clean_value(row.get(m['brand'])) or "").lower()
        df.at[i, "Restricted"] = "Yes" if brand in restricted_brands else "No"
        if brand in restricted_brands: stats["restricted_flagged"] += 1
            
    return df, stats

# ─────────────────────────────────────────────────────────────────────────────
# HISTORY LOGGING
# ─────────────────────────────────────────────────────────────────────────────

def append_history(df, stats):
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rows_processed": len(df),
        "stock_filled": stats["stock_filled"],
        "restricted_flagged": stats["restricted_flagged"]
    }
    new_df = pd.DataFrame([row])
    if os.path.exists(HISTORY_FILE):
        pd.concat([pd.read_csv(HISTORY_FILE), new_df]).to_csv(HISTORY_FILE, index=False)
    else:
        new_df.to_csv(HISTORY_FILE, index=False)

# ─────────────────────────────────────────────────────────────────────────────
# INTERFACE
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div class="virv-header"><span class="virv-logo">VV</span> <b>ENRICHMENT ENGINE</b></div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["⚡ Run", "📈 History"])

with tab1:
    col1, col2, col3 = st.columns(3)
    with col1: f_main = st.file_uploader("Main File", type=["csv", "xlsx"])
    with col2: f_inv = st.file_uploader("Inventory File", type=["csv", "xlsx"])
    with col3: f_rest = st.file_uploader("Restrictions", type=["csv", "xlsx"])

    if st.button("RUN ENRICHMENT") and f_main:
        m_df = universal_file_reader(f_main)
        i_df = universal_file_reader(f_inv)
        r_df = universal_file_reader(f_rest)
        
        if m_df is not None:
            inv_lookup = build_inventory_lookup(i_df)
            # Build restrictions set
            r_brands = set()
            if r_df is not None:
                rm = auto_map_columns(r_df)
                r_col = rm.get('brand') or r_df.columns[0]
                r_brands = {str(x).strip().lower() for x in r_df[r_col].dropna() if clean_value(x)}

            res_df, stats = enrich_main(m_df, inv_lookup, r_brands)
            append_history(res_df, stats)
            
            st.success(f"Processed {len(res_df)} rows. Found {stats['stock_filled']} matches.")
            st.dataframe(res_df.head(50))
            
            # Export
            towrite = io.BytesIO()
            res_df.to_excel(towrite, index=False, engine='xlsxwriter')
            st.download_button("Download Results", towrite.getvalue(), "enriched_data.xlsx")

with tab2:
    if os.path.exists(HISTORY_FILE):
        h_df = pd.read_csv(HISTORY_FILE)
        # Safety checks for metrics to prevent KeyError
        total_rows = h_df['rows_processed'].sum() if 'rows_processed' in h_df.columns else 0
        total_matches = h_df['stock_filled'].sum() if 'stock_filled' in h_df.columns else 0
        
        c1, c2 = st.columns(2)
        c1.metric("Total Rows Processed", f"{total_rows:,}")
        c2.metric("Total Stock Matches", f"{total_matches:,}")
        st.dataframe(h_df.sort_values("timestamp", ascending=False))
    else:
        st.info("No history found.")
