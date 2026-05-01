"""
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                   ║
║                    VIRVENTURES DATAOPS PLATFORM                                   ║
║                    Enterprise Data Enrichment System                              ║
║                    Version 2.0 - Production Ready                                 ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import base64
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# =============================================================================
# PAGE CONFIG - MUST BE FIRST
# =============================================================================
st.set_page_config(
    page_title="VirVentures DataOps Platform",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# BRAND ASSETS
# =============================================================================
def get_logo_b64():
    for p in ["virventures_logo.jpg", "virventures_com_logo.jpg", "logo.png"]:
        if os.path.exists(p):
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return None

LOGO_B64 = get_logo_b64()

# =============================================================================
# PREMIUM CSS - VIRVENTURES BRANDED
# =============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

* {
    font-family: 'Inter', sans-serif !important;
}

/* Main background */
.stApp, .main, .block-container {
    background: #f5f7fb !important;
}

/* Premium Header */
.premium-header {
    background: linear-gradient(135deg, #0a1a2f 0%, #1a2a4a 100%);
    border-radius: 20px;
    padding: 24px 32px;
    margin-bottom: 24px;
    border: 1px solid rgba(244,121,32,0.2);
}

.premium-title {
    color: #ffffff !important;
    font-size: 1.5rem !important;
    font-weight: 800 !important;
    margin: 0 !important;
}

.premium-subtitle {
    color: #f47920 !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    margin: 6px 0 0 0 !important;
}

.premium-badge {
    background: rgba(244,121,32,0.15);
    border: 1px solid rgba(244,121,32,0.3);
    border-radius: 40px;
    padding: 4px 14px;
    font-size: 0.7rem;
    font-weight: 600;
    color: #f47920;
    display: inline-block;
}

/* Premium Cards */
.premium-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid #e8ecf2;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(90deg, #f47920, #ff9a45) !important;
    color: white !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 28px !important;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(244,121,32,0.3);
}

/* Download Buttons */
.stDownloadButton > button {
    background: white !important;
    color: #f47920 !important;
    border: 2px solid #f47920 !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
}

/* Metrics */
div[data-testid="metric-container"] {
    background: #ffffff !important;
    border-radius: 16px !important;
    padding: 16px !important;
    border: 1px solid #e8ecf2 !important;
}

/* Progress */
.stProgress > div > div {
    background: linear-gradient(90deg, #f47920, #ff9a45) !important;
    border-radius: 20px !important;
}

/* Section Headers */
.section-header {
    font-size: 1.2rem;
    font-weight: 800;
    color: #0a1a2f;
    margin: 24px 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 3px solid #f47920;
    display: inline-block;
}

/* Info/Warning/Success Boxes */
.info-box {
    background: #f0f4ff;
    border-left: 4px solid #3b82f6;
    border-radius: 12px;
    padding: 14px 18px;
    margin: 12px 0;
}

.success-box {
    background: #e8f5e9;
    border-left: 4px solid #22c55e;
    border-radius: 12px;
    padding: 14px 18px;
    margin: 12px 0;
}

.warning-box {
    background: #fefce8;
    border-left: 4px solid #eab308;
    border-radius: 12px;
    padding: 14px 18px;
    margin: 12px 0;
}

/* File Uploader */
[data-testid="stFileUploader"] {
    background: #fafbfc !important;
    border: 2px dashed #d1d5db !important;
    border-radius: 16px !important;
    padding: 20px !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: #f47920 !important;
    background: #fff8f3 !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a1a2f 0%, #142840 100%) !important;
}

section[data-testid="stSidebar"] * {
    color: #e5e7eb !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE
# =============================================================================
if 'enriched_df' not in st.session_state:
    st.session_state.enriched_df = None
if 'enriched_filename' not in st.session_state:
    st.session_state.enriched_filename = None
if 'processing_history' not in st.session_state:
    st.session_state.processing_history = []

# =============================================================================
# HEADER
# =============================================================================
logo_html = f'<img src="data:image/jpeg;base64,{LOGO_B64}" style="height:45px;margin-right:16px;border-radius:10px;">' if LOGO_B64 else ""

st.markdown(f"""
<div class="premium-header">
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;">
        <div style="display: flex; align-items: center;">
            {logo_html}
            <div>
                <div class="premium-title">VIRVENTURES DATAOPS PLATFORM</div>
                <div class="premium-subtitle">Enterprise Data Enrichment System</div>
            </div>
        </div>
        <div>
            <span class="premium-badge">🚀 PRODUCTION</span>
            <span class="premium-badge" style="margin-left: 8px;">⚡ REAL-TIME</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================
with st.sidebar:
    st.markdown("### 🏢 VirVentures")
    st.markdown("---")
    
    menu_options = ["📦 Data Enrichment", "📊 Analytics", "📋 History", "🎓 Help"]
    selected = st.radio("Navigation", menu_options, label_visibility="collapsed")
    
    st.markdown("---")
    st.caption(f"📅 {datetime.now().strftime('%B %d, %Y')}")
    st.caption("⚡ Version 2.0")
    st.caption("© 2024 VirVentures")

# =============================================================================
# DATA ENRICHMENT TAB
# =============================================================================
if selected == "📦 Data Enrichment":
    
    st.markdown("""
    <div class="info-box">
        <b>✨ Welcome to DataOps Platform</b><br>
        Upload your main file and multiple lookup files. The system will automatically match and fill all empty columns.
    </div>
    """, unsafe_allow_html=True)
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 📂 Main File")
        main_file = st.file_uploader(
            "Upload Main Excel File",
            type=["xlsx", "xls", "csv"],
            label_visibility="collapsed",
            key="main_uploader"
        )
        
        if main_file:
            if main_file.name.endswith('.csv'):
                main_df = pd.read_csv(main_file)
            else:
                main_df = pd.read_excel(main_file, dtype=str)
            main_df.columns = main_df.columns.str.strip()
            
            # Detect key column
            key_candidates = ['ASIN', 'asin', 'input_ASIN', 'UPC', 'upc', 'SKU', 'sku']
            detected_key = None
            for col in key_candidates:
                if col in main_df.columns:
                    detected_key = col
                    break
            
            if not detected_key:
                detected_key = main_df.columns[0]
            
            empty_cols = sum(1 for col in main_df.columns if main_df[col].isna().all() or (main_df[col].astype(str).str.strip() == "").all())
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("📊 Rows", len(main_df))
            col_b.metric("📝 Columns", len(main_df.columns))
            col_c.metric("⚠️ Empty Columns", empty_cols)
            
            with st.expander("Preview Main File"):
                st.dataframe(main_df.head(8), use_container_width=True)
    
    with col_right:
        st.markdown("### 📂 Lookup Files")
        st.caption("Inventory, Brand, Restrictions, etc.")
        
        num_lookups = st.number_input("Number of files", min_value=1, max_value=10, value=3)
        
        lookup_files = []
        for i in range(num_lookups):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                lf = st.file_uploader(f"File {i+1}", type=["xlsx", "xls", "csv"], label_visibility="collapsed", key=f"lookup_{i}")
            with col_b:
                label = st.text_input("Label", placeholder=f"Source {i+1}", key=f"label_{i}", label_visibility="collapsed")
            if lf:
                lookup_files.append({'file': lf, 'label': label if label else f"Source {i+1}", 'df': None})
    
    if main_file and lookup_files:
        st.markdown("---")
        st.markdown("### ⚙️ Configuration")
        
        match_col = st.selectbox("Matching Column", options=main_df.columns.tolist(), index=main_df.columns.tolist().index(detected_key) if detected_key in main_df.columns else 0)
        fill_strategy = st.selectbox("Fill Strategy", ["Only fill EMPTY cells", "Overwrite ALL cells"])
        
        if st.button("🚀 START ENRICHMENT", use_container_width=True):
            enriched_df = main_df.copy()
            processing_results = []
            all_filled_cols = []
            total_cells = 0
            
            progress_bar = st.progress(0)
            status = st.empty()
            
            for idx, lf in enumerate(lookup_files):
                status.info(f"Processing: {lf['label']}...")
                
                try:
                    if lf['file'].name.endswith('.csv'):
                        lookup_df = pd.read_csv(lf['file'])
                    else:
                        lookup_df = pd.read_excel(lf['file'], dtype=str)
                    lookup_df.columns = lookup_df.columns.str.strip()
                    
                    if match_col not in lookup_df.columns:
                        st.warning(f"⚠️ '{lf['label']}' missing '{match_col}'. Skipping...")
                        continue
                    
                    enriched_df[match_col] = enriched_df[match_col].astype(str).str.strip()
                    lookup_df[match_col] = lookup_df[match_col].astype(str).str.strip()
                    
                    filled_cols = []
                    cells_filled = 0
                    
                    for col in lookup_df.columns:
                        if col == match_col:
                            continue
                        
                        needs_fill = True if fill_strategy == "Overwrite ALL cells" else (col not in enriched_df.columns or enriched_df[col].isna().all() or (enriched_df[col].astype(str).str.strip() == "").all())
                        
                        if needs_fill:
                            lookup_dict = dict(zip(lookup_df[match_col], lookup_df[col]))
                            for row_idx, row in enriched_df.iterrows():
                                key = row[match_col]
                                if key in lookup_dict and pd.notna(lookup_dict[key]):
                                    if col not in enriched_df.columns:
                                        enriched_df[col] = None
                                    current = enriched_df.at[row_idx, col] if col in enriched_df.columns else None
                                    if fill_strategy == "Only fill EMPTY cells" and pd.notna(current) and str(current).strip() != "":
                                        continue
                                    enriched_df.at[row_idx, col] = lookup_dict[key]
                                    cells_filled += 1
                            filled_cols.append(col)
                    
                    processing_results.append({'file': lf['label'], 'cols': len(filled_cols), 'cells': cells_filled})
                    all_filled_cols.extend(filled_cols)
                    total_cells += cells_filled
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                
                progress_bar.progress((idx + 1) / len(lookup_files))
            
            progress_bar.progress(1.0)
            status.success("✅ Enrichment Complete!")
            
            st.session_state.enriched_df = enriched_df
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            original_name = main_file.name.replace('.xlsx', '').replace('.xls', '').replace('.csv', '')
            st.session_state.enriched_filename = f"{original_name}_Enriched_{timestamp}.xlsx"
            
            # Save to history
            st.session_state.processing_history.insert(0, {
                'timestamp': datetime.now().isoformat(),
                'main_file': main_file.name,
                'rows': len(enriched_df),
                'cols_filled': len(set(all_filled_cols)),
                'cells_filled': total_cells
            })
            
            # Results
            st.markdown("---")
            st.markdown("## 📊 Results")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📊 Rows", len(enriched_df))
            m2.metric("📁 Files", len(processing_results))
            m3.metric("📝 Columns Filled", len(set(all_filled_cols)))
            m4.metric("🔢 Cells Filled", f"{total_cells:,}")
            
            for pr in processing_results:
                st.markdown(f"• **{pr['file']}**: {pr['cols']} columns, {pr['cells']} cells")
            
            if all_filled_cols:
                st.markdown("**Preview of filled columns:**")
                preview_cols = [match_col] + list(set(all_filled_cols))[:5]
                preview_cols = [c for c in preview_cols if c in enriched_df.columns]
                st.dataframe(enriched_df[preview_cols].head(10), use_container_width=True)
    
    if st.session_state.enriched_df is not None:
        st.markdown("---")
        st.markdown("## ⬇️ Download")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.enriched_df.to_excel(writer, index=False, sheet_name='Enriched')
        
        st.download_button("📥 Download Excel File", data=output.getvalue(), file_name=st.session_state.enriched_filename, use_container_width=True)

# =============================================================================
# ANALYTICS TAB
# =============================================================================
elif selected == "📊 Analytics":
    st.markdown("## 📊 Analytics Dashboard")
    
    if st.session_state.processing_history:
        df = pd.DataFrame(st.session_state.processing_history)
        
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Total Runs", len(df))
        a2.metric("Total Rows", f"{df['rows'].sum():,}")
        a3.metric("Total Cells", f"{df['cells_filled'].sum():,}")
        a4.metric("Time Saved", f"~{len(df) * 60} min")
        
        st.markdown("### Recent Activity")
        st.dataframe(df[['timestamp', 'main_file', 'rows', 'cols_filled', 'cells_filled']].head(20), use_container_width=True)
    else:
        st.info("No analytics yet. Run some enrichments to see data.")

# =============================================================================
# HISTORY TAB
# =============================================================================
elif selected == "📋 History":
    st.markdown("## 📋 Processing History")
    
    if st.session_state.processing_history:
        for item in st.session_state.processing_history[:30]:
            st.markdown(f"""
            <div class="premium-card" style="margin-bottom: 12px;">
                <b>📁 {item['main_file']}</b><br>
                🕐 {datetime.fromisoformat(item['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}<br>
                📊 {item['rows']} rows · 📝 {item['cols_filled']} columns filled · 🔢 {item['cells_filled']} cells
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No history yet.")

# =============================================================================
# HELP TAB
# =============================================================================
elif selected == "🎓 Help":
    st.markdown("## 🎓 Help & Documentation")
    
    with st.expander("How to Use", expanded=True):
        st.markdown("""
        1. **Upload Main File** - Your vendor file with empty columns
        2. **Upload Lookup Files** - Department files (Inventory, Brand, Restrictions)
        3. **Select Matching Column** - Usually ASIN, UPC, or SKU
        4. **Choose Fill Strategy** - "Only fill EMPTY cells" is recommended
        5. **Click Start** - Let the system work
        6. **Download** - Get your complete enriched file
        """)
    
    with st.expander("Best Practices"):
        st.markdown("""
        - Use ASIN as the matching key whenever possible
        - Keep column names consistent across files
        - Review the analytics dashboard to track savings
        - Download enriched files before closing the session
        """)

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.caption("⚡ VirVentures DataOps Platform v2.0 | From 60 minutes to 60 seconds")
