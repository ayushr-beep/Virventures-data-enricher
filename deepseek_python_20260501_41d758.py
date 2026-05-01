import streamlit as st
import pandas as pd
import io
import base64
import os
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="VirVentures Data Enricher",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# LOGO & CSS
# =============================================================================
def get_logo_b64():
    for p in ["virventures_logo.jpg", "virventures_com_logo.jpg"]:
        if os.path.exists(p):
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return None

LOGO_B64 = get_logo_b64()
LOGO_HTML = (
    f'<img src="data:image/jpeg;base64,{LOGO_B64}" '
    f'style="height:55px;width:auto;border-radius:10px;">'
    if LOGO_B64 else ""
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*, html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp, .main, .block-container { background: #f8f9fb !important; }
.vv-header {
    background: linear-gradient(135deg, #1e2d4e 0%, #2a3f6e 100%);
    border-radius: 16px; padding: 20px 30px; margin-bottom: 24px;
    display: flex; align-items: center; gap: 18px;
    border-left: 6px solid #f47920;
}
.vv-title { color: #ffffff !important; font-size: 1.1rem !important; font-weight: 800 !important; margin: 0; }
.vv-sub { color: #f47920 !important; font-size: 0.7rem !important; font-weight: 700 !important; text-transform: uppercase; margin: 0; }
.stButton > button { background: linear-gradient(90deg, #f47920, #ff9a45) !important; color: #fff !important; font-weight: 700 !important; border: none !important; border-radius: 10px !important; padding: 12px 28px !important; }
.stDownloadButton > button { background: #fff !important; color: #f47920 !important; border: 2px solid #f47920 !important; font-weight: 600 !important; }
div[data-testid="metric-container"] { background: #fff !important; border: 1.5px solid #e0e0e0 !important; border-radius: 12px !important; padding: 15px !important; }
.sec { color: #1e2d4e; font-size: 0.9rem; font-weight: 800; padding-bottom: 5px; border-bottom: 3px solid #f47920; display: inline-block; margin: 15px 0 12px 0; }
.info-box { background: #fff8f3; border-left: 4px solid #f47920; border-radius: 0 10px 10px 0; padding: 12px 16px; margin: 10px 0; }
.success-box { background: #e8f5e9; border-left: 4px solid #2e7d32; border-radius: 0 10px 10px 0; padding: 12px 16px; margin: 10px 0; }
.match-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 12px; margin: 5px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="vv-header">
    {LOGO_HTML}
    <div>
        <p class="vv-title">VirVentures Data Enricher</p>
        <p class="vv-sub">Auto-fill empty columns from lookup files · 60 min/day saved → 2 min</p>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE INIT
# =============================================================================
if 'enriched_df' not in st.session_state:
    st.session_state.enriched_df = None
if 'enriched_filename' not in st.session_state:
    st.session_state.enriched_filename = None

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def enrich_data(main_df, lookup_df, match_col, fill_strategy="empty_only"):
    """
    Enrich main_df with data from lookup_df based on match_col
    fill_strategy: "empty_only" or "overwrite_all" or "keep_main"
    """
    # Convert key column to string for both dataframes
    main_df[match_col] = main_df[match_col].astype(str)
    lookup_df[match_col] = lookup_df[match_col].astype(str)
    
    # Create a lookup dictionary
    lookup_dict = {}
    for _, row in lookup_df.iterrows():
        key = row[match_col]
        if key not in lookup_dict:
            lookup_dict[key] = row.to_dict()
    
    # Track what was filled
    filled_columns = []
    filled_count = 0
    rows_affected = 0
    
    # For each column in main_df, if it's empty or we want to fill it
    for col in main_df.columns:
        if col == match_col:
            continue
        
        # Find matching column in lookup_df (same name or similar)
        lookup_col = None
        if col in lookup_df.columns:
            lookup_col = col
        else:
            # Try case-insensitive match
            for lcol in lookup_df.columns:
                if lcol.lower() == col.lower():
                    lookup_col = lcol
                    break
        
        if lookup_col is None:
            continue
        
        # Check if this column needs filling
        if fill_strategy == "overwrite_all":
            needs_fill = True
        else:
            # Check if column has any empty/null values
            needs_fill = main_df[col].isna().any() or (main_df[col].astype(str).str.strip() == "").any()
        
        if needs_fill:
            filled_columns.append(col)
            # Fill values
            for idx, row in main_df.iterrows():
                key = row[match_col]
                if key in lookup_dict and lookup_dict[key].get(lookup_col):
                    current_val = main_df.at[idx, col]
                    if fill_strategy == "empty_only" and pd.notna(current_val) and str(current_val).strip() != "":
                        continue
                    main_df.at[idx, col] = lookup_dict[key][lookup_col]
                    filled_count += 1
            rows_affected += len(main_df)
    
    return main_df, filled_columns, filled_count, rows_affected

# =============================================================================
# AUTO-DETECT KEY COLUMN
# =============================================================================
def detect_key_column(df):
    """Auto-detect best column to use as matching key"""
    candidates = ['ASIN', 'asin', 'input_ASIN', 'UPC', 'upc', 'SKU', 'sku', 'Product ID']
    for col in candidates:
        if col in df.columns:
            return col
    # If no standard column, return first column
    return df.columns[0]

# =============================================================================
# UI
# =============================================================================
st.markdown("""
<div class="info-box">
    <b>📋 How it works:</b><br>
    1. Upload your MAIN file (has empty columns that need filling)<br>
    2. Upload LOOKUP file (has the actual data)<br>
    3. Select which column to match on (ASIN/UPC/SKU)<br>
    4. Click ENRICH - all empty columns will be filled automatically!<br>
    5. Download the complete file
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📂 MAIN FILE")
    st.caption("Vendor file with empty columns")
    main_file = st.file_uploader(
        "Upload Main Excel File",
        type=["xlsx", "xls"],
        label_visibility="collapsed",
        key="main_uploader"
    )

with col2:
    st.markdown("### 📂 LOOKUP FILE")
    st.caption("Department file with actual data")
    lookup_file = st.file_uploader(
        "Upload Lookup Excel File",
        type=["xlsx", "xls"],
        label_visibility="collapsed",
        key="lookup_uploader"
    )

if main_file and lookup_file:
    # Read files
    main_df = pd.read_excel(main_file, dtype=str)
    lookup_df = pd.read_excel(lookup_file, dtype=str)
    
    # Clean column names
    main_df.columns = main_df.columns.str.strip()
    lookup_df.columns = lookup_df.columns.str.strip()
    
    st.markdown('<p class="sec">📊 File Preview</p>', unsafe_allow_html=True)
    
    preview_col1, preview_col2 = st.columns(2)
    with preview_col1:
        st.caption(f"Main File: {len(main_df)} rows, {len(main_df.columns)} columns")
        st.dataframe(main_df.head(5), use_container_width=True)
    with preview_col2:
        st.caption(f"Lookup File: {len(lookup_df)} rows, {len(lookup_df.columns)} columns")
        st.dataframe(lookup_df.head(5), use_container_width=True)
    
    # Detect empty columns in main file
    empty_cols = []
    for col in main_df.columns:
        if col in main_df.columns:
            is_empty = main_df[col].isna().all() or (main_df[col].astype(str).str.strip() == "").all()
            if is_empty and col not in ['SKU', 'ASIN', 'asin', 'UPC', 'upc']:
                empty_cols.append(col)
    
    st.markdown('<p class="sec">⚙️ Configuration</p>', unsafe_allow_html=True)
    
    # Match column selection
    all_cols_main = list(main_df.columns)
    default_match = detect_key_column(main_df)
    
    match_col = st.selectbox(
        "🔗 Match files using this column (must exist in BOTH files)",
        options=all_cols_main,
        index=all_cols_main.index(default_match) if default_match in all_cols_main else 0,
        help="Values in this column will be used to match rows between files"
    )
    
    # Check if match column exists in lookup file
    if match_col not in lookup_df.columns:
        st.error(f"⚠️ Column '{match_col}' not found in LOOKUP file. Please check.")
        st.stop()
    
    # Show columns that will be filled
    st.markdown("### 📝 Columns to be filled")
    
    if empty_cols:
        st.info(f"🔍 Found **{len(empty_cols)} empty columns** that can be filled:")
        
        # Try to find matching columns in lookup file
        fillable_cols = []
        for col in empty_cols:
            if col in lookup_df.columns:
                fillable_cols.append((col, "✅ Will be filled", lookup_df[col].iloc[0] if len(lookup_df) > 0 else "N/A"))
            else:
                # Try case-insensitive match
                matched = False
                for lcol in lookup_df.columns:
                    if lcol.lower() == col.lower():
                        fillable_cols.append((col, "✅ Will be filled (case match)", lookup_df[lcol].iloc[0] if len(lookup_df) > 0 else "N/A"))
                        matched = True
                        break
                if not matched:
                    fillable_cols.append((col, "❌ No matching column in lookup file", "—"))
        
        for col, status, sample in fillable_cols[:20]:
            if "✅" in status:
                st.markdown(f"• **{col}** — {status}")
            else:
                st.markdown(f"• ~~{col}~~ — {status}")
        
        if len(empty_cols) > 20:
            st.caption(f"... and {len(empty_cols) - 20} more columns")
    else:
        st.success("✅ No completely empty columns found! File may already be enriched.")
    
    # Fill strategy
    fill_strategy = st.radio(
        "📌 Fill Strategy",
        options=["empty_only", "overwrite_all"],
        format_func=lambda x: "Only fill EMPTY cells (keep existing data)" if x == "empty_only" else "Overwrite ALL cells (replace existing data)",
        horizontal=True
    )
    
    # Enrich button
    if st.button("🚀 ENRICH DATA", use_container_width=True):
        with st.spinner("Processing..."):
            enriched_df, filled_cols, filled_count, rows_affected = enrich_data(
                main_df.copy(), lookup_df.copy(), match_col, fill_strategy
            )
            
            st.session_state.enriched_df = enriched_df
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            original_name = main_file.name.replace('.xlsx', '').replace('.xls', '')
            st.session_state.enriched_filename = f"{original_name}_Enriched_{timestamp}.xlsx"
            
            st.markdown('<div class="success-box">✅ <b>Enrichment Complete!</b></div>', unsafe_allow_html=True)
            
            col_metrics1, col_metrics2, col_metrics3, col_metrics4 = st.columns(4)
            col_metrics1.metric("📊 Rows Processed", rows_affected)
            col_metrics2.metric("📝 Columns Filled", len(filled_cols))
            col_metrics3.metric("🔢 Cells Filled", filled_count)
            col_metrics4.metric("⏱️ Time Saved Today", "~60 min", delta="-60 min")
            
            # Preview enriched data
            st.markdown('<p class="sec">👁️ Preview (Enriched)</p>', unsafe_allow_html=True)
            
            # Show sample of filled columns
            if filled_cols:
                preview_cols = [match_col] + filled_cols[:5]
                preview_df = enriched_df[preview_cols].head(10)
                st.dataframe(preview_df, use_container_width=True)
    
    # Download button
    if st.session_state.enriched_df is not None:
        st.markdown('<p class="sec">⬇️ Download</p>', unsafe_allow_html=True)
        
        # Convert to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.enriched_df.to_excel(writer, index=False, sheet_name='Enriched_Data')
        
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 DOWNLOAD ENRICHED FILE",
            data=excel_data,
            file_name=st.session_state.enriched_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        
        st.caption("💾 File is ready to use in ASIN Verifier or share with team")

else:
    st.info("📂 Please upload BOTH files to begin")

st.markdown("---")
st.caption("⚡ VirVentures Data Enricher v1.0 | Zero cost · Saves 60 minutes daily | Deployed on Streamlit Cloud")