# VirVentures FBA Enrichment Engine
# Production-grade inventory enrichment tool for Amazon FBA resellers.

import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import csv
import chardet
import difflib
import re
import traceback
from datetime import datetime, date
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VirVentures · FBA Enrichment Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL STYLE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

:root {
--bg: #0a0c10;
--surface: #111318;
--border: #1e2230;
--accent: #00e5a0;
--accent2: #ff6b35;
--text: #e8ecf4;
--muted: #6b7592;
--danger: #ff4757;
--warn: #ffa502;
}

html, body, [class*="css"] {
background-color: var(--bg) !important;
color: var(--text) !important;
font-family: 'Syne', sans-serif !important;
}

/* Header */
.virv-header {
display: flex;
align-items: center;
gap: 16px;
padding: 28px 0 8px 0;
border-bottom: 1px solid var(--border);
margin-bottom: 28px;
}
.virv-logo {
font-family: 'Space Mono', monospace;
font-size: 1.05rem;
font-weight: 700;
color: var(--accent);
letter-spacing: 2px;
border: 1.5px solid var(--accent);
padding: 6px 12px;
border-radius: 4px;
}
.virv-title {
font-size: 1.55rem;
font-weight: 800;
color: var(--text);
letter-spacing: -0.5px;
}
.virv-sub {
font-size: 0.82rem;
color: var(--muted);
margin-top: 3px;
font-family: 'Space Mono', monospace;
}

/* Upload cards */
.upload-label {
font-size: 0.72rem;
font-weight: 700;
letter-spacing: 2px;
text-transform: uppercase;
color: var(--muted);
margin-bottom: 6px;
font-family: 'Space Mono', monospace;
}
.required-badge {
color: var(--accent2);
font-size: 0.65rem;
margin-left: 6px;
vertical-align: middle;
}
.optional-badge {
color: var(--muted);
font-size: 0.65rem;
margin-left: 6px;
vertical-align: middle;
}

/* Stat cards */
.stat-row {
display: grid;
grid-template-columns: repeat(4, 1fr);
gap: 14px;
margin: 20px 0;
}
.stat-card {
background: var(--surface);
border: 1px solid var(--border);
border-radius: 8px;
padding: 18px 20px;
}
.stat-card .val {
font-family: 'Space Mono', monospace;
font-size: 1.7rem;
font-weight: 700;
color: var(--accent);
line-height: 1;
}
.stat-card .lbl {
font-size: 0.72rem;
color: var(--muted);
margin-top: 6px;
letter-spacing: 1px;
text-transform: uppercase;
}

/* Enrich button */
div[data-testid="stButton"] > button {
background: var(--accent) !important;
color: #000 !important;
font-family: 'Space Mono', monospace !important;
font-weight: 700 !important;
font-size: 0.85rem !important;
letter-spacing: 2px !important;
padding: 12px 32px !important;
border: none !important;
border-radius: 4px !important;
cursor: pointer !important;
transition: all 0.15s !important;
width: 100% !important;
}
div[data-testid="stButton"] > button:hover {
background: #00ffb3 !important;
transform: translateY(-1px) !important;
}

/* Section dividers */
.section-head {
font-size: 0.7rem;
font-weight: 700;
letter-spacing: 3px;
text-transform: uppercase;
color: var(--muted);
font-family: 'Space Mono', monospace;
padding: 18px 0 10px 0;
border-top: 1px solid var(--border);
margin-top: 10px;
}

/* File badge */
.file-ok {
display: inline-block;
background: rgba(0,229,160,0.12);
color: var(--accent);
font-family: 'Space Mono', monospace;
font-size: 0.7rem;
padding: 3px 10px;
border-radius: 3px;
margin-top: 4px;
}
.file-err {
display: inline-block;
background: rgba(255,71,87,0.12);
color: var(--danger);
font-family: 'Space Mono', monospace;
font-size: 0.7rem;
padding: 3px 10px;
border-radius: 3px;
margin-top: 4px;
}

/* Metric accent */
.fill-stat {
font-family: 'Space Mono', monospace;
font-size: 0.78rem;
color: var(--accent);
padding: 4px 0;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
HISTORY_FILE = "history.csv"

MISSING_VALUES = {
    "", "0", "0.0", "na", "n/a", "#n/a", "none", "null",
    "nan", "#value!", "#ref!", "#name?", "n.a.", "n.a", "-",
    "unknown", "undefined",
}

STANDARD_MAP: dict[str, list[str]] = {
    "sku": ["sku", "model#", "model number", "item code", "item#", "seller sku"],
    "asin": ["asin", "amazon asin", "output asin", "parent asin"],
    "stock": ["stock", "afn-fulfillable-quantity", "available qty", "inventory"],
    "reserve": ["reserve", "reserved", "afn-reserved-quantity", "fc transfer"],
    "inbound": ["inbound", "inbound quantity", "afn-inbound-shipped-quantity"],
    "brand": ["brand", "brand name", "manufacturer"],
    "sales_30": ["sales 30", "sales30", "30 day sales"],
    "listing_status": ["listing status", "status", "item status"],
}

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def clean_value(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, float) and (np.isnan(val) or val == 0.0):
        return None
    if isinstance(val, int) and val == 0:
        return None
    s = str(val).strip()
    if s.lower() in MISSING_VALUES:
        return None
    return s

def safe_int(val, default=0) -> int:
    try:
        cv = clean_value(val)
        return int(float(cv)) if cv is not None else default
    except:
        return default

def safe_float(val, default=0.0) -> float:
    try:
        cv = clean_value(val)
        return float(cv) if cv is not None else default
    except:
        return default

def normalize_col(col: str) -> str:
    return re.sub(r"\s+", " ", str(col).strip().lower())

# ─────────────────────────────────────────────────────────────────────────────
# FILE READER
# ─────────────────────────────────────────────────────────────────────────────

def universal_file_reader(uploaded_file, label: str = "file") -> Optional[pd.DataFrame]:
    if uploaded_file is None:
        return None
    try:
        raw_bytes = uploaded_file.getvalue()
        filename = uploaded_file.name.lower()
        
        # Detect encoding
        detected = chardet.detect(raw_bytes[:4096])
        enc = detected.get("encoding") or "utf-8"
        
        if filename.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb')):
            df = pd.read_excel(io.BytesIO(raw_bytes), dtype=str)
        else:
            df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, dtype=str, on_bad_lines="skip")
        
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception as e:
        st.error(f"Error reading {label}: {e}")
    return None

def auto_map_columns(df: pd.DataFrame) -> dict:
    cols_norm = {normalize_col(c): c for c in df.columns}
    mapping = {}
    for std_key, aliases in STANDARD_MAP.items():
        found = next((cols_norm[a] for a in aliases if a in cols_norm), None)
        mapping[std_key] = found
    return mapping

# ─────────────────────────────────────────────────────────────────────────────
# LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def build_inventory_lookup(inv_df: pd.DataFrame) -> dict:
    lookup = {}
    if inv_df is None: return lookup
    m = auto_map_columns(inv_df)
    for _, row in inv_df.iterrows():
        sku = clean_value(row.get(m['sku']))
        asin = clean_value(row.get(m['asin']))
        data = {
            "stock": safe_int(row.get(m['stock'])),
            "reserve": safe_int(row.get(m['reserve'])),
            "inbound": safe_int(row.get(m['inbound']))
        }
        if sku: lookup[sku.lower()] = data
        if asin: lookup[asin.lower()] = data
    return lookup

def build_restrictions_set(rest_df: pd.DataFrame) -> set:
    brands = set()
    if rest_df is None: return brands
    m = auto_map_columns(rest_df)
    col = m.get('brand') or rest_df.columns[0]
    for val in rest_df[col].dropna():
        cv = clean_value(val)
        if cv: brands.add(cv.lower())
    return brands

def enrich_main(main_df, inv_lookup, restricted_brands, progress_cb=None):
    df = main_df.copy()
    m = auto_map_columns(df)
    stats = {"stock_filled": 0, "restricted_flagged": 0}
    
    for col in ["Stock", "Reserve", "Inbound", "TOTAL", "Restricted"]:
        if col not in df.columns: df[col] = None

    for i, row in df.iterrows():
        sku = clean_value(row.get(m['sku']))
        asin = clean_value(row.get(m['asin']))
        
        key = (sku or "").lower()
        data = inv_lookup.get(key) or inv_lookup.get((asin or "").lower())
        
        if data:
            df.at[i, "Stock"] = data["stock"]
            df.at[i, "Reserve"] = data["reserve"]
            df.at[i, "Inbound"] = data["inbound"]
            df.at[i, "TOTAL"] = data["stock"] + data["reserve"] + data["inbound"]
            stats["stock_filled"] += 1
            
        brand_val = clean_value(row.get(m['brand']))
        if brand_val and brand_val.lower() in restricted_brands:
            df.at[i, "Restricted"] = "Yes"
            stats["restricted_flagged"] += 1
        else:
            df.at[i, "Restricted"] = "No"
            
    return df, stats

# ─────────────────────────────────────────────────────────────────────────────
# HISTORY WITH SAFETY
# ─────────────────────────────────────────────────────────────────────────────

def append_history(df, stats):
    try:
        row = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "rows_processed": len(df),
            "stock_filled": stats.get("stock_filled", 0),
            "restricted_flagged": stats.get("restricted_flagged", 0),
            "total_stock_units": sum(safe_int(v) for v in df["Stock"]) if "Stock" in df.columns else 0
        }
        new_df = pd.DataFrame([row])
        if os.path.exists(HISTORY_FILE):
            pd.concat([pd.read_csv(HISTORY_FILE), new_df]).to_csv(HISTORY_FILE, index=False)
        else:
            new_df.to_csv(HISTORY_FILE, index=False)
    except: pass

def load_history():
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    return None

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div class="virv-header"><div class="virv-logo">VV</div><div class="virv-title">FBA Enrichment Engine</div></div>', unsafe_allow_html=True)

tab_enrich, tab_history = st.tabs(["⚡ ENRICH", "📈 HISTORY"])

with tab_enrich:
    c1, c2, c3 = st.columns(3)
    with c1: main_file = st.file_uploader("Main File", type=["csv", "xlsx"])
    with c2: inv_file = st.file_uploader("Inventory File", type=["csv", "xlsx"])
    with c3: rest_file = st.file_uploader("Restrictions", type=["csv", "xlsx"])

    if st.button("⚡ RUN ENRICHMENT") and main_file:
        m_df = universal_file_reader(main_file, "MAIN")
        i_df = universal_file_reader(inv_file, "INV")
        r_df = universal_file_reader(rest_file, "REST")
        
        if m_df is not None:
            inv_lookup = build_inventory_lookup(i_df)
            rest_set = build_restrictions_set(r_df)
            
            res_df, stats = enrich_main(m_df, inv_lookup, rest_set)
            st.session_state["res"] = res_df
            st.session_state["stats"] = stats
            append_history(res_df, stats)
            st.success("Enrichment Complete!")
            st.dataframe(res_df.head(100))
            
            # Download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res_df.to_excel(writer, index=False)
            st.download_button("⬇ Download Result", output.getvalue(), "enriched.xlsx")

with tab_history:
    h_df = load_history()
    if h_df is not None:
        hc1, hc2 = st.columns(2)
        # Safe sum checks to prevent KeyError
        rp = h_df['rows_processed'].sum() if 'rows_processed' in h_df.columns else 0
        sf = h_df['stock_filled'].sum() if 'stock_filled' in h_df.columns else 0
        
        hc1.metric("Total Rows", f"{rp:,}")
        hc2.metric("Stock Matches", f"{sf:,}")
        st.dataframe(h_df)
    else:
        st.info("No history yet.")
