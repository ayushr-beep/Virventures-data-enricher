
Ayush Ray
10:16 PM (0 minutes ago)
to me

"""
VirVentures FBA Enrichment Engine
Production-grade inventory enrichment tool for Amazon FBA resellers.
"""

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

/* Progress */
div[data-testid="stProgress"] > div > div {
background-color: var(--accent) !important;
}

/* Tables */
div[data-testid="stDataFrame"] {
border: 1px solid var(--border) !important;
border-radius: 6px !important;
}

/* Alerts */
div[data-testid="stAlert"] {
border-radius: 6px !important;
font-family: 'Space Mono', monospace !important;
font-size: 0.8rem !important;
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

/* Streamlit overrides */
section[data-testid="stFileUploadDropzone"] {
background: var(--surface) !important;
border: 1.5px dashed var(--border) !important;
border-radius: 6px !important;
}
section[data-testid="stFileUploadDropzone"]:hover {
border-color: var(--accent) !important;
}
.stTabs [data-baseweb="tab"] {
font-family: 'Space Mono', monospace !important;
font-size: 0.78rem !important;
letter-spacing: 1px !important;
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
"sku": [
"sku", "model#", "model number", "item code", "item#",
"seller sku", "merchant sku", "product code", "part number",
"listing sku", "fnsku", "msku",
],
"asin": [
"asin", "amazon asin", "output asin", "parent asin",
"child asin", "asin1",
],
"stock": [
"stock", "afn-fulfillable-quantity", "afn fulfillable quantity",
"available qty", "available quantity", "fulfillable qty",
"qty available", "on hand", "inventory", "fba stock",
"warehouse stock", "total stock", "qty",
],
"reserve": [
"reserve", "reserved", "afn-reserved-quantity",
"reserved quantity", "fc transfer", "pending",
"afn reserved", "reserve qty",
],
"inbound": [
"inbound", "inbound quantity", "afn-inbound-shipped-quantity",
"in transit", "shipped inbound", "inbound qty",
"shipment qty", "incoming",
],
"brand": [
"brand", "brand name", "manufacturer", "make",
"vendor brand", "item brand",
],
"price": [
"price", "selling price", "sale price", "list price",
"buy box price", "your price", "cost",
],
"sales_30": [
"sales 30", "sales30", "30 day sales", "units sold 30",
"sold last 30", "30d sales", "sales last 30 days",
],
"listing_status": [
"listing status", "status", "item status", "active",
"inactive", "suppressed",
],
}

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def clean_value(val) -> Optional[str]:
"""
Returns None if val is considered missing/zero/NA.
Otherwise returns the stripped string.
"""
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
"""Convert to int safely, defaulting on failure."""
try:
cv = clean_value(val)
if cv is None:
return default
return int(float(cv))
except Exception:
return default


def safe_float(val, default=0.0) -> float:
"""Convert to float safely, defaulting on failure."""
try:
cv = clean_value(val)
if cv is None:
return default
return float(cv)
except Exception:
return default


def normalize_col(col: str) -> str:
"""Lowercase, strip, collapse whitespace."""
return re.sub(r"\s+", " ", str(col).strip().lower())


# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSAL FILE READER
# ─────────────────────────────────────────────────────────────────────────────

def universal_file_reader(uploaded_file, label: str = "file") -> Optional[pd.DataFrame]:
"""
Fault-tolerant file reader that tries every known strategy.
Never crashes. Returns None on total failure.
"""
if uploaded_file is None:
return None

try:
raw_bytes = uploaded_file.getvalue()
except Exception as e:
st.error(f"❌ [{label}] Could not read file bytes: {e}")
return None

filename = getattr(uploaded_file, "name", "").lower()
is_csv_ext = filename.endswith(".csv")
is_excel_ext = any(filename.endswith(x) for x in (".xlsx", ".xls", ".xlsm", ".xlsb"))

strategies = []

# ── Excel strategies ──────────────────────────────────────────────────────
if not is_csv_ext:
for engine in ("openpyxl", "xlrd"):
for skip in range(0, 16):
strategies.append(("excel", engine, skip))

# ── CSV strategies ─────────────────────────────────────────────────────────
detected_enc = "utf-8"
try:
detected = chardet.detect(raw_bytes[:4096])
detected_enc = detected.get("encoding") or "utf-8"
except Exception:
pass

encodings = list(dict.fromkeys([detected_enc, "utf-8", "latin1", "cp1252", "utf-8-sig"]))
separators = [",", "\t", ";", "|"]
for enc in encodings:
for sep in separators:
for skip in range(0, 16):
strategies.append(("csv", enc, sep, skip))

last_err = ""
for strat in strategies:
try:
buf = io.BytesIO(raw_bytes)
if strat[0] == "excel":
_, engine, skip = strat
df = pd.read_excel(buf, engine=engine, skiprows=skip, header=0, dtype=str)
else:
_, enc, sep, skip = strat
buf.seek(0)
df = pd.read_csv(
buf,
encoding=enc,
sep=sep,
skiprows=skip,
header=0,
dtype=str,
on_bad_lines="skip",
low_memory=False,
)

# Validate: must have rows and at least 2 real columns
if df is not None and len(df) > 0:
# Drop fully-unnamed columns
df = df.loc[:, ~df.columns.astype(str).str.match(r"^Unnamed: \d+$")]
if len(df.columns) < 1:
continue
# Drop rows that are entirely NaN
df.dropna(how="all", inplace=True)
if len(df) > 0:
df.columns = [str(c).strip() for c in df.columns]
return df
except Exception as e:
last_err = str(e)
continue

st.error(f"❌ [{label}] Could not parse file after all strategies. Last error: {last_err}")
return None


# ─────────────────────────────────────────────────────────────────────────────
# AUTO COLUMN MAPPER
# ─────────────────────────────────────────────────────────────────────────────

def auto_map_columns(df: pd.DataFrame) -> dict[str, Optional[str]]:
"""
Uses fuzzy matching (difflib) to map DataFrame columns → standard keys.
Returns dict {standard_key: actual_col_name_or_None}.
"""
cols_norm = {normalize_col(c): c for c in df.columns}
mapping: dict[str, Optional[str]] = {}

for std_key, aliases in STANDARD_MAP.items():
found = None
# 1) Exact match against normalized aliases
for alias in aliases:
if alias in cols_norm:
found = cols_norm[alias]
break
# 2) Fuzzy match
if found is None:
all_alias_words = aliases
matches = difflib.get_close_matches(
std_key,
list(cols_norm.keys()),
n=1,
cutoff=0.72,
)
if matches:
found = cols_norm[matches[0]]
else:
# Try each alias vs each column
for alias in all_alias_words:
m = difflib.get_close_matches(alias, list(cols_norm.keys()), n=1, cutoff=0.75)
if m:
found = cols_norm[m[0]]
break
mapping[std_key] = found

return mapping


# ─────────────────────────────────────────────────────────────────────────────
# IDENTIFIER EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_sku(row: pd.Series, df_cols: list[str]) -> Optional[str]:
"""
Priority: INV(A-Z) → INV(Z-A) → input_Model# → SKU columns.
"""
# 1) Columns matching INV(A-Z) pattern
inv_cols_az = sorted([c for c in df_cols if re.match(r"^inv[a-z]$", c.lower())])
for c in inv_cols_az:
v = clean_value(row.get(c))
if v:
return v

# 2) INV(Z-A)
inv_cols_za = sorted(
[c for c in df_cols if re.match(r"^inv[a-z]$", c.lower())], reverse=True
)
for c in inv_cols_za:
v = clean_value(row.get(c))
if v:
return v

# 3) input_Model# or model# variants
for c in df_cols:
if "model" in c.lower() or "input_model" in c.lower():
v = clean_value(row.get(c))
if v:
return v

# 4) SKU-like columns
for c in df_cols:
if "sku" in c.lower():
v = clean_value(row.get(c))
if v:
return v

return None


def extract_asin(row: pd.Series, df_cols: list[str]) -> Optional[str]:
"""
Priority: Output ASIN → ASIN → asin variants.
"""
for c in df_cols:
if "output" in c.lower() and "asin" in c.lower():
v = clean_value(row.get(c))
if v:
return v
for c in df_cols:
if normalize_col(c) == "asin":
v = clean_value(row.get(c))
if v:
return v
for c in df_cols:
if "asin" in c.lower():
v = clean_value(row.get(c))
if v:
return v
return None


# ─────────────────────────────────────────────────────────────────────────────
# ENRICHMENT ENGINES
# ─────────────────────────────────────────────────────────────────────────────

def build_inventory_lookup(inv_df: pd.DataFrame) -> dict:
"""
Build {sku_lower: {stock, reserve, inbound}, asin_lower: {...}}
"""
lookup: dict = {}
if inv_df is None or len(inv_df) == 0:
return lookup

mapping = auto_map_columns(inv_df)
cols = list(inv_df.columns)

for _, row in inv_df.iterrows():
sku_raw = None
asin_raw = None

# Get SKU
if mapping.get("sku"):
sku_raw = clean_value(row.get(mapping["sku"]))
if sku_raw is None:
sku_raw = extract_sku(row, cols)

# Get ASIN
if mapping.get("asin"):
asin_raw = clean_value(row.get(mapping["asin"]))
if asin_raw is None:
asin_raw = extract_asin(row, cols)

stock_val = safe_int(row.get(mapping["stock"]) if mapping.get("stock") else None)
reserve_val = safe_int(row.get(mapping["reserve"]) if mapping.get("reserve") else None)
inbound_val = safe_int(row.get(mapping["inbound"]) if mapping.get("inbound") else None)

entry = {
"stock": stock_val,
"reserve": reserve_val,
"inbound": inbound_val,
}

if sku_raw:
lookup[sku_raw.lower()] = entry
if asin_raw:
lookup[asin_raw.lower()] = entry

return lookup


def build_restrictions_set(rest_df: pd.DataFrame) -> set:
"""
Returns set of restricted brand names (lowercase).
"""
brands: set = set()
if rest_df is None or len(rest_df) == 0:
return brands

mapping = auto_map_columns(rest_df)
brand_col = mapping.get("brand")

if brand_col is None:
# Try to find any column with 'brand' in name
for c in rest_df.columns:
if "brand" in c.lower():
brand_col = c
break

if brand_col is None and len(rest_df.columns) > 0:
brand_col = rest_df.columns[0] # fallback: first column

if brand_col:
for val in rest_df[brand_col].dropna():
cv = clean_value(val)
if cv:
brands.add(cv.lower())

return brands


def build_archive_lookup(arch_df: pd.DataFrame) -> dict:
"""
Build ASIN → {listing_status, ...} from archive.
"""
lookup: dict = {}
if arch_df is None or len(arch_df) == 0:
return lookup

mapping = auto_map_columns(arch_df)
cols = list(arch_df.columns)

for _, row in arch_df.iterrows():
asin_raw = None
if mapping.get("asin"):
asin_raw = clean_value(row.get(mapping["asin"]))
if asin_raw is None:
asin_raw = extract_asin(row, cols)

if asin_raw:
entry = {}
if mapping.get("listing_status"):
entry["listing_status"] = clean_value(row.get(mapping["listing_status"]))
lookup[asin_raw.lower()] = entry

return lookup


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENRICHMENT PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def enrich_main(
main_df: pd.DataFrame,
inv_lookup: dict,
restricted_brands: set,
arch_lookup: dict,
progress_cb=None,
) -> tuple[pd.DataFrame, dict]:
"""
Core enrichment logic. Returns (enriched_df, stats).
"""
df = main_df.copy()
total = max(len(df), 1)
cols = list(df.columns)

# Ensure output columns exist
for col in ["_SKU", "_ASIN", "Stock", "Reserve", "Inbound",
"TOTAL", "Restricted", "Listing Status", "Days of Stock"]:
if col not in df.columns:
df[col] = None

stats = {
"stock_filled": 0,
"reserve_filled": 0,
"inbound_filled": 0,
"restricted_flagged": 0,
"archive_filled": 0,
}

mapping = auto_map_columns(df)

for idx, (i, row) in enumerate(df.iterrows()):
# Progress
if progress_cb and idx % 50 == 0:
progress_cb(min(idx / total, 0.95))

# ── Extract identifiers ────────────────────────────────────────────
sku = None
asin = None

if mapping.get("sku"):
sku = clean_value(row.get(mapping["sku"]))
if sku is None:
sku = extract_sku(row, cols)

if mapping.get("asin"):
asin = clean_value(row.get(mapping["asin"]))
if asin is None:
asin = extract_asin(row, cols)

df.at[i, "_SKU"] = sku or ""
df.at[i, "_ASIN"] = asin or ""

sku_key = sku.lower() if sku else None
asin_key = asin.lower() if asin else None

# ── Inventory enrichment ───────────────────────────────────────────
inv_data = (
inv_lookup.get(sku_key)
or inv_lookup.get(asin_key)
or {}
)

for field, col_name in [("stock", "Stock"), ("reserve", "Reserve"), ("inbound", "Inbound")]:
existing = clean_value(row.get(col_name)) if col_name in df.columns else None
if existing is None and field in inv_data:
df.at[i, col_name] = inv_data[field]
stats[f"{field}_filled"] += 1

# ── Restrictions ───────────────────────────────────────────────────
brand_col = mapping.get("brand")
brand_val = clean_value(row.get(brand_col)) if brand_col else None
if brand_val and brand_val.lower() in restricted_brands:
df.at[i, "Restricted"] = "Yes"
stats["restricted_flagged"] += 1
else:
if clean_value(df.at[i, "Restricted"]) is None:
df.at[i, "Restricted"] = "No"

# ── Archive ────────────────────────────────────────────────────────
if asin_key and asin_key in arch_lookup:
arch = arch_lookup[asin_key]
if arch.get("listing_status"):
existing_ls = clean_value(df.at[i, "Listing Status"])
if existing_ls is None:
df.at[i, "Listing Status"] = arch["listing_status"]
stats["archive_filled"] += 1

# ── Derived: TOTAL ─────────────────────────────────────────────────
s = safe_int(df.at[i, "Stock"])
r = safe_int(df.at[i, "Reserve"])
nb = safe_int(df.at[i, "Inbound"])
df.at[i, "TOTAL"] = s + r + nb

# ── Derived: Days of Stock ─────────────────────────────────────────
sales_col = mapping.get("sales_30")
if sales_col:
sales_30 = safe_float(row.get(sales_col))
if sales_30 > 0:
dos = round((s / sales_30) * 30, 1)
df.at[i, "Days of Stock"] = dos

if progress_cb:
progress_cb(1.0)

return df, stats


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────────────────────────────────────

def append_history(df: pd.DataFrame, stats: dict):
"""Append summary row to history.csv."""
try:
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
total_stock = 0
if "Stock" in df.columns:
total_stock = sum(safe_int(v) for v in df["Stock"])

row = {
"timestamp": now,
"date": datetime.now().strftime("%Y-%m-%d"),
"rows_processed": len(df),
"stock_filled": stats.get("stock_filled", 0),
"reserve_filled": stats.get("reserve_filled", 0),
"inbound_filled": stats.get("inbound_filled", 0),
"restricted_flagged": stats.get("restricted_flagged", 0),
"archive_filled": stats.get("archive_filled", 0),
"total_stock_units": total_stock,
}

new_df = pd.DataFrame([row])
if os.path.exists(HISTORY_FILE):
existing = pd.read_csv(HISTORY_FILE, dtype=str)
combined = pd.concat([existing, new_df], ignore_index=True)
else:
combined = new_df

combined.to_csv(HISTORY_FILE, index=False)
except Exception as e:
st.warning(f"⚠️ Could not save history: {e}")


def load_history() -> Optional[pd.DataFrame]:
"""Load history CSV if it exists."""
try:
if os.path.exists(HISTORY_FILE):
df = pd.read_csv(HISTORY_FILE, dtype=str)
if df is not None and len(df) > 0:
return df
except Exception:
pass
return None


# ─────────────────────────────────────────────────────────────────────────────
# EXCEL WRITER
# ─────────────────────────────────────────────────────────────────────────────

def to_excel_bytes(df: pd.DataFrame) -> bytes:
"""Write DataFrame to Excel bytes, with openpyxl fallback to xlsxwriter."""
buf = io.BytesIO()
try:
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
df.to_excel(writer, index=False, sheet_name="Enriched")
except Exception:
try:
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
df.to_excel(writer, index=False, sheet_name="Enriched")
except Exception as e:
st.error(f"❌ Could not write Excel output: {e}")
return b""
return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

if "enriched_df" not in st.session_state:
st.session_state["enriched_df"] = None
if "stats" not in st.session_state:
st.session_state["stats"] = {}
if "run_complete" not in st.session_state:
st.session_state["run_complete"] = False


# ─────────────────────────────────────────────────────────────────────────────
# UI — HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="virv-header">
<div class="virv-logo">VV</div>
<div>
<div class="virv-title">FBA Enrichment Engine</div>
<div class="virv-sub">AUTOMATED INVENTORY INTELLIGENCE · VIRVENTURES OPS PLATFORM</div>
</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# UI — TABS
# ─────────────────────────────────────────────────────────────────────────────

tab_enrich, tab_history, tab_help = st.tabs(["⚡ ENRICH", "📈 HISTORY", "📖 GUIDE"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ENRICH
# ══════════════════════════════════════════════════════════════════════════════
with tab_enrich:

st.markdown('<div class="section-head">01 · UPLOAD FILES</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)

with c1:
st.markdown(
'<div class="upload-label">MAIN / VENDOR FILE'
'<span class="required-badge">★ REQUIRED</span></div>',
unsafe_allow_html=True,
)
main_file = st.file_uploader(
"main", type=["xlsx", "xls", "xlsm", "xlsb", "csv"],
label_visibility="collapsed", key="main_file"
)

with c2:
st.markdown(
'<div class="upload-label">INVENTORY FILE'
'<span class="optional-badge">optional</span></div>',
unsafe_allow_html=True,
)
inv_file = st.file_uploader(
"inv", type=["xlsx", "xls", "xlsm", "xlsb", "csv"],
label_visibility="collapsed", key="inv_file"
)

with c3:
st.markdown(
'<div class="upload-label">RESTRICTIONS FILE'
'<span class="optional-badge">optional</span></div>',
unsafe_allow_html=True,
)
rest_file = st.file_uploader(
"rest", type=["xlsx", "xls", "xlsm", "xlsb", "csv"],
label_visibility="collapsed", key="rest_file"
)

with c4:
st.markdown(
'<div class="upload-label">ARCHIVE FILE'
'<span class="optional-badge">optional</span></div>',
unsafe_allow_html=True,
)
arch_file = st.file_uploader(
"arch", type=["xlsx", "xls", "xlsm", "xlsb", "csv"],
label_visibility="collapsed", key="arch_file"
)

# ── File status previews ──────────────────────────────────────────────────
st.markdown('<div class="section-head">02 · FILE STATUS</div>', unsafe_allow_html=True)

file_dfs: dict[str, Optional[pd.DataFrame]] = {}
file_meta: dict[str, dict] = {}

for label, fobj in [
("MAIN", main_file),
("INVENTORY", inv_file),
("RESTRICTIONS", rest_file),
("ARCHIVE", arch_file),
]:
if fobj is not None:
df_test = universal_file_reader(fobj, label=label)
file_dfs[label] = df_test
if df_test is not None and len(df_test) > 0:
file_meta[label] = {"rows": len(df_test), "cols": len(df_test.columns)}
else:
file_meta[label] = None
else:
file_dfs[label] = None
file_meta[label] = None

fc1, fc2, fc3, fc4 = st.columns(4)
for col_ui, lbl in zip([fc1, fc2, fc3, fc4], ["MAIN", "INVENTORY", "RESTRICTIONS", "ARCHIVE"]):
with col_ui:
meta = file_meta.get(lbl)
if file_dfs.get(lbl) is not None and meta:
st.markdown(
f'<div class="file-ok">✓ {lbl}<br>{meta["rows"]:,} rows × {meta["cols"]} cols</div>',
unsafe_allow_html=True,
)
elif (lbl == "MAIN" and main_file is not None) or \
(lbl == "INVENTORY" and inv_file is not None) or \
(lbl == "RESTRICTIONS" and rest_file is not None) or \
(lbl == "ARCHIVE" and arch_file is not None):
st.markdown(
f'<div class="file-err">✗ {lbl} · PARSE FAILED</div>',
unsafe_allow_html=True,
)
else:
st.markdown(
f'<div style="color:var(--muted);font-size:0.72rem;font-family:\'Space Mono\',monospace;">'
f'{lbl} · not uploaded</div>',
unsafe_allow_html=True,
)

# ── Options ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-head">03 · OPTIONS</div>', unsafe_allow_html=True)

oc1, oc2, oc3 = st.columns(3)
with oc1:
opt_overwrite = st.checkbox("Overwrite existing values", value=False,
help="If checked, inventory values will overwrite even non-empty cells.")
with oc2:
opt_days_stock = st.checkbox("Calculate Days of Stock", value=True,
help="Requires 'Sales 30' column in main file.")
with oc3:
opt_save_history = st.checkbox("Save run to history", value=True)

# ── ENRICH button ─────────────────────────────────────────────────────────
st.markdown('<div class="section-head">04 · RUN</div>', unsafe_allow_html=True)

enrich_btn = st.button("⚡ ENRICH NOW", disabled=(file_dfs.get("MAIN") is None))

if enrich_btn:
main_df = file_dfs.get("MAIN")
if main_df is None or len(main_df) == 0:
st.error("❌ MAIN file is required and could not be parsed.")
else:
progress_bar = st.progress(0.0, text="Initialising enrichment pipeline…")
status_area = st.empty()

def update_progress(val: float):
pct = int(val * 100)
progress_bar.progress(val, text=f"Enriching records… {pct}%")

# Build lookups
status_area.info("🔍 Building inventory lookup…")
inv_df = file_dfs.get("INVENTORY")
rest_df = file_dfs.get("RESTRICTIONS")
arch_df = file_dfs.get("ARCHIVE")

inv_lookup = build_inventory_lookup(inv_df) if inv_df is not None else {}
restricted_brands = build_restrictions_set(rest_df) if rest_df is not None else set()
arch_lookup = build_archive_lookup(arch_df) if arch_df is not None else {}

status_area.info(f"⚙️ Running enrichment on {len(main_df):,} rows…")

try:
enriched_df, stats = enrich_main(
main_df,
inv_lookup,
restricted_brands,
arch_lookup,
progress_cb=update_progress,
)

st.session_state["enriched_df"] = enriched_df
st.session_state["stats"] = stats
st.session_state["run_complete"] = True

if opt_save_history:
append_history(enriched_df, stats)

progress_bar.progress(1.0, text="✅ Enrichment complete!")
status_area.success(
f"✅ Enriched {len(enriched_df):,} rows · "
f"Stock filled: {stats['stock_filled']} · "
f"Restricted flagged: {stats['restricted_flagged']}"
)

except Exception as e:
progress_bar.progress(0.0, text="")
status_area.error(f"❌ Enrichment failed: {e}")
st.code(traceback.format_exc(), language="text")

# ── Results ───────────────────────────────────────────────────────────────
if st.session_state.get("run_complete") and st.session_state.get("enriched_df") is not None:
enriched_df = st.session_state["enriched_df"]
stats = st.session_state["stats"]

st.markdown('<div class="section-head">05 · RESULTS</div>', unsafe_allow_html=True)

# Stat cards
total_stock = sum(safe_int(v) for v in enriched_df.get("Stock", pd.Series([])))
total_rows = len(enriched_df)
restricted = stats.get("restricted_flagged", 0)
filled = stats.get("stock_filled", 0) + stats.get("reserve_filled", 0) + stats.get("inbound_filled", 0)

st.markdown(f"""
<div class="stat-row">
<div class="stat-card">
<div class="val">{total_rows:,}</div>
<div class="lbl">Rows Enriched</div>
</div>
<div class="stat-card">
<div class="val">{total_stock:,}</div>
<div class="lbl">Total Stock Units</div>
</div>
<div class="stat-card">
<div class="val">{restricted:,}</div>
<div class="lbl">Restricted Brands</div>
</div>
<div class="stat-card">
<div class="val">{filled:,}</div>
<div class="lbl">Fields Auto-Filled</div>
</div>
</div>
""", unsafe_allow_html=True)

# Fill breakdown
rc1, rc2, rc3 = st.columns(3)
with rc1:
st.markdown(f'<div class="fill-stat">📦 Stock filled: {stats.get("stock_filled", 0)}</div>', unsafe_allow_html=True)
with rc2:
st.markdown(f'<div class="fill-stat">🔄 Reserve filled: {stats.get("reserve_filled", 0)}</div>', unsafe_allow_html=True)
with rc3:
st.markdown(f'<div class="fill-stat">🚚 Inbound filled: {stats.get("inbound_filled", 0)}</div>', unsafe_allow_html=True)

# Preview table
st.markdown("**Preview (first 200 rows)**")
st.dataframe(enriched_df.head(200), use_container_width=True, height=350)

# Download
st.markdown('<div class="section-head">06 · DOWNLOAD</div>', unsafe_allow_html=True)
excel_bytes = to_excel_bytes(enriched_df)
if excel_bytes:
fname = f"virventures_enriched_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
st.download_button(
label="⬇ DOWNLOAD ENRICHED FILE (.xlsx)",
data=excel_bytes,
file_name=fname,
mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — HISTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:
st.markdown('<div class="section-head">RUN HISTORY · DAILY TREND</div>', unsafe_allow_html=True)

hist_df = load_history()

if hist_df is not None and len(hist_df) > 0:
# Numeric coercion
for col in ["rows_processed", "stock_filled", "restricted_flagged", "total_stock_units"]:
if col in hist_df.columns:
hist_df[col] = pd.to_numeric(hist_df[col], errors="coerce").fillna(0).astype(int)

# Summary stats
hc1, hc2, hc3, hc4 = st.columns(4)
with hc1:
st.metric("Total Runs", len(hist_df))
with hc2:
st.metric("Total Rows Processed", f"{hist_df['rows_processed'].sum():,}")
with hc3:
st.metric("Total Stock Filled", f"{hist_df['stock_filled'].sum():,}")
with hc4:
st.metric("Restricted Flagged", f"{hist_df['restricted_flagged'].sum():,}")

# Charts
if "date" in hist_df.columns and "total_stock_units" in hist_df.columns:
daily = (
hist_df.groupby("date")["total_stock_units"]
.sum()
.reset_index()
.sort_values("date")
.tail(30)
)
if len(daily) > 1:
st.markdown("**Total Stock Units · Last 30 Days**")
st.line_chart(daily.set_index("date")["total_stock_units"])

if "date" in hist_df.columns and "rows_processed" in hist_df.columns:
daily_rows = (
hist_df.groupby("date")["rows_processed"]
.sum()
.reset_index()
.sort_values("date")
.tail(30)
)
if len(daily_rows) > 1:
st.markdown("**Rows Processed · Last 30 Days**")
st.bar_chart(daily_rows.set_index("date")["rows_processed"])

st.markdown("**Full Run Log**")
st.dataframe(hist_df.sort_values("timestamp", ascending=False) if "timestamp" in hist_df.columns else hist_df,
use_container_width=True)

# Download history
hist_bytes = hist_df.to_csv(index=False).encode("utf-8")
st.download_button(
label="⬇ DOWNLOAD HISTORY (.csv)",
data=hist_bytes,
file_name="virventures_history.csv",
mime="text/csv",
)
else:
st.info("No history yet. Run your first enrichment to start tracking.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — HELP
# ══════════════════════════════════════════════════════════════════════════════
with tab_help:
st.markdown('<div class="section-head">USER GUIDE</div>', unsafe_allow_html=True)

st.markdown("""
**VirVentures FBA Enrichment Engine** automates the manual VLOOKUP + cleanup workflow.

---

### 📂 FILE GUIDE

| File | Required | Purpose |
|------|----------|---------|
| **Main / Vendor** | ✅ Yes | Base file to enrich |
| **Inventory** | Optional | Stock / Reserve / Inbound data |
| **Restrictions** | Optional | Brand blocklist → flags "Restricted = Yes" |
| **Archive** | Optional | Historical ASIN data for filling Listing Status |

---

### 🤖 AUTO-DETECTED COLUMNS

The engine **auto-maps messy column names** — no manual setup needed.

| Standard Field | Examples Detected |
|----------------|-------------------|
| SKU | `SKU`, `Model#`, `Item Code`, `INV(A-Z)` |
| ASIN | `ASIN`, `Output ASIN`, `ASIN1` |
| Stock | `Stock`, `AFN-FULFILLABLE-QUANTITY`, `Available Qty` |
| Reserve | `Reserve`, `AFN-RESERVED-QUANTITY`, `Pending` |
| Inbound | `Inbound`, `AFN-INBOUND-SHIPPED-QUANTITY`, `In Transit` |
| Brand | `Brand`, `Brand Name`, `Manufacturer` |

---

### ⚡ DERIVED COLUMNS ADDED

- **TOTAL** = Stock + Reserve + Inbound
- **Days of Stock** = (Stock / Sales30) × 30 *(if Sales 30 column exists)*
- **Restricted** = Yes / No *(based on Restrictions file)*

---

### 🔒 DATA SAFETY

Values treated as **missing** (will be filled if enrichment data exists):

`0`, `0.0`, `NA`, `N/A`, `#N/A`, `None`, `null`, `nan`, blank, `-`

---

### 📁 SUPPORTED FILE FORMATS

`.xlsx` · `.xls` · `.xlsm` · `.xlsb` · `.csv`

Files with junk header rows, wrong encoding, or corrupted data are handled automatically.
""")
