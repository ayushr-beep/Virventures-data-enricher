import streamlit as st
import pandas as pd
import io
from datetime import datetime

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="VirVentures Data Enricher",
    page_icon="📦",
    layout="wide",
)

# =============================================================================
# SIMPLE CLEAN CSS (No Conflicts)
# =============================================================================
st.markdown("""
<style>
/* Main container */
.main {
    padding: 0 1rem;
}

/* Headers */
h1, h2, h3 {
    color: #1e2d4e;
}

/* Custom buttons */
.stButton button {
    background-color: #f47920;
    color: white;
    font-weight: bold;
    border-radius: 8px;
    border: none;
}

.stButton button:hover {
    background-color: #e06810;
    color: white;
}

/* Download buttons */
.stDownloadButton button {
    background-color: white;
    color: #f47920;
    border: 2px solid #f47920;
    border-radius: 8px;
    font-weight: bold;
}

/* Metrics */
.metric-card {
    background-color: #f8f9fa;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    border: 1px solid #e9ecef;
}

/* Info box */
.info-box {
    background-color: #e8f4fd;
    border-left: 4px solid #f47920;
    border-radius: 8px;
    padding: 16px;
    margin: 16px 0;
}

.success-box {
    background-color: #d4edda;
    border-left: 4px solid #28a745;
    border-radius: 8px;
    padding: 16px;
    margin: 16px 0;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# HEADER
# =============================================================================
st.title("🏢 VirVentures DataOps Platform")
st.caption("Enterprise Data Enrichment System | From 60 minutes to 60 seconds")

st.markdown("---")

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("## 🏢 VirVentures")
    st.markdown("---")
    
    menu = st.radio("Navigation", ["📦 Data Enrichment", "📊 Analytics", "📋 History", "🎓 Help"])
    
    st.markdown("---")
    st.caption(f"📅 {datetime.now().strftime('%B %d, %Y')}")
    st.caption("⚡ Version 2.0")
    st.caption("© 2025 VirVentures")

# =============================================================================
# DATA ENRICHMENT TAB
# =============================================================================
if menu == "📦 Data Enrichment":
    
    st.markdown("""
    <div class="info-box">
        <b>✨ Welcome to DataOps Platform</b><br>
        Upload your main file and multiple lookup files. The system will automatically match and fill all empty columns.
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📂 Main File")
        st.caption("Your vendor file with empty columns")
        
        main_file = st.file_uploader(
            "Upload Main Excel File",
            type=["xlsx", "xls", "csv"],
            key="main_file"
        )
        
        if main_file:
            # Read file
            if main_file.name.endswith('.csv'):
                main_df = pd.read_csv(main_file)
            else:
                main_df = pd.read_excel(main_file, dtype=str)
            
            main_df.columns = main_df.columns.str.strip()
            
            # Detect key column
            key_options = ['ASIN', 'asin', 'input_ASIN', 'UPC', 'upc', 'SKU', 'sku']
            detected_key = None
            for col in key_options:
                if col in main_df.columns:
                    detected_key = col
                    break
            
            if not detected_key:
                detected_key = main_df.columns[0]
            
            # Show stats
            empty_cols = 0
            for col in main_df.columns:
                if main_df[col].isna().all() or (main_df[col].astype(str).str.strip() == "").all():
                    empty_cols += 1
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("📊 Rows", len(main_df))
            col_b.metric("📝 Columns", len(main_df.columns))
            col_c.metric("⚠️ Empty Columns", empty_cols)
            
            with st.expander("Preview Main File"):
                st.dataframe(main_df.head(10), use_container_width=True)
    
    with col2:
        st.subheader("📂 Lookup Files")
        st.caption("Department files (Inventory, Brand, Restrictions, etc.)")
        
        num_files = st.number_input("Number of lookup files", min_value=1, max_value=10, value=3)
        
        lookup_files = []
        for i in range(num_files):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                lf = st.file_uploader(
                    f"File {i+1}",
                    type=["xlsx", "xls", "csv"],
                    key=f"lookup_{i}",
                    label_visibility="collapsed"
                )
            with col_b:
                label = st.text_input(
                    f"Label",
                    value=f"Source {i+1}",
                    key=f"label_{i}",
                    label_visibility="collapsed"
                )
            if lf:
                lookup_files.append({
                    'file': lf,
                    'label': label if label else f"Source {i+1}"
                })
    
    # Configuration
    if main_file and lookup_files:
        st.markdown("---")
        st.subheader("⚙️ Configuration")
        
        match_col = st.selectbox(
            "🔗 Matching Column",
            options=main_df.columns.tolist(),
            index=main_df.columns.tolist().index(detected_key) if detected_key in main_df.columns else 0,
            help="This column must exist in ALL files (e.g., ASIN, UPC, SKU)"
        )
        
        fill_strategy = st.radio(
            "📌 Fill Strategy",
            ["Only fill EMPTY cells (recommended)", "Overwrite ALL cells"],
            horizontal=True
        )
        
        if st.button("🚀 START ENRICHMENT", use_container_width=True):
            # Initialize
            enriched_df = main_df.copy()
            results = []
            all_filled_cols = []
            total_cells = 0
            
            progress = st.progress(0)
            status = st.empty()
            
            for idx, lf in enumerate(lookup_files):
                status.info(f"Processing: {lf['label']}...")
                
                try:
                    # Read lookup file
                    if lf['file'].name.endswith('.csv'):
                        lookup_df = pd.read_csv(lf['file'])
                    else:
                        lookup_df = pd.read_excel(lf['file'], dtype=str)
                    
                    lookup_df.columns = lookup_df.columns.str.strip()
                    
                    # Check match column exists
                    if match_col not in lookup_df.columns:
                        st.warning(f"⚠️ '{lf['label']}' missing column '{match_col}'. Skipping...")
                        continue
                    
                    # Convert to string for matching
                    enriched_df[match_col] = enriched_df[match_col].astype(str).str.strip()
                    lookup_df[match_col] = lookup_df[match_col].astype(str).str.strip()
                    
                    filled_in_file = []
                    cells_in_file = 0
                    
                    for col in lookup_df.columns:
                        if col == match_col:
                            continue
                        
                        # Check if needs fill
                        if fill_strategy == "Only fill EMPTY cells (recommended)":
                            if col in enriched_df.columns:
                                is_empty = enriched_df[col].isna().all() or (enriched_df[col].astype(str).str.strip() == "").all()
                                if not is_empty:
                                    continue
                        
                        # Create lookup dict and fill
                        lookup_dict = dict(zip(lookup_df[match_col], lookup_df[col]))
                        
                        for row_idx, row in enriched_df.iterrows():
                            key = row[match_col]
                            if key in lookup_dict and pd.notna(lookup_dict[key]):
                                if col not in enriched_df.columns:
                                    enriched_df[col] = None
                                
                                current = enriched_df.at[row_idx, col] if col in enriched_df.columns else None
                                
                                if fill_strategy == "Only fill EMPTY cells (recommended)":
                                    if pd.notna(current) and str(current).strip() != "":
                                        continue
                                
                                enriched_df.at[row_idx, col] = lookup_dict[key]
                                cells_in_file += 1
                        
                        filled_in_file.append(col)
                    
                    results.append({
                        'name': lf['label'],
                        'cols': len(filled_in_file),
                        'cells': cells_in_file
                    })
                    
                    all_filled_cols.extend(filled_in_file)
                    total_cells += cells_in_file
                    
                except Exception as e:
                    st.error(f"Error processing {lf['label']}: {str(e)}")
                
                progress.progress((idx + 1) / len(lookup_files))
            
            progress.progress(1.0)
            status.success("✅ Enrichment Complete!")
            
            # Save to session
            st.session_state.enriched_df = enriched_df
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            original_name = main_file.name.replace('.xlsx', '').replace('.xls', '').replace('.csv', '')
            st.session_state.enriched_filename = f"{original_name}_Enriched_{timestamp}.xlsx"
            
            # Show results
            st.markdown("---")
            st.subheader("📊 Results")
            
            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            col_r1.metric("Rows Processed", len(enriched_df))
            col_r2.metric("Files Merged", len(results))
            col_r3.metric("Columns Filled", len(set(all_filled_cols)))
            col_r4.metric("Cells Filled", f"{total_cells:,}")
            
            for r in results:
                st.markdown(f"• **{r['name']}**: {r['cols']} columns, {r['cells']} cells filled")
            
            if all_filled_cols:
                st.markdown("### Preview")
                preview_cols = [match_col] + list(set(all_filled_cols))[:5]
                preview_cols = [c for c in preview_cols if c in enriched_df.columns]
                st.dataframe(enriched_df[preview_cols].head(10), use_container_width=True)
    
    # Download
    if st.session_state.get('enriched_df') is not None:
        st.markdown("---")
        st.subheader("⬇️ Download Enriched File")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.enriched_df.to_excel(writer, index=False, sheet_name='Enriched_Data')
        
        st.download_button(
            label="📥 Download Excel File",
            data=output.getvalue(),
            file_name=st.session_state.enriched_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# =============================================================================
# ANALYTICS TAB
# =============================================================================
elif menu == "📊 Analytics":
    st.subheader("📊 Analytics Dashboard")
    
    if 'processing_history' not in st.session_state:
        st.session_state.processing_history = []
    
    if st.session_state.processing_history:
        df = pd.DataFrame(st.session_state.processing_history)
        
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Total Runs", len(df))
        a2.metric("Total Rows", f"{df['rows'].sum():,}")
        a3.metric("Total Cells", f"{df['cells'].sum():,}")
        a4.metric("Time Saved", f"~{len(df) * 60} min")
        
        st.markdown("### Recent Activity")
        st.dataframe(df[['timestamp', 'file', 'rows', 'columns_filled', 'cells']].head(20), use_container_width=True)
    else:
        st.info("No analytics yet. Run some enrichments to see data.")

# =============================================================================
# HISTORY TAB
# =============================================================================
elif menu == "📋 History":
    st.subheader("📋 Processing History")
    
    if 'processing_history' not in st.session_state:
        st.session_state.processing_history = []
    
    if st.session_state.processing_history:
        for item in st.session_state.processing_history[:30]:
            st.markdown(f"""
            ### 📁 {item['file']}
            - 🕐 {item['timestamp']}
            - 📊 {item['rows']} rows processed
            - 📝 {item['columns_filled']} columns filled
            - 🔢 {item['cells']} cells updated
            """)
            st.markdown("---")
    else:
        st.info("No history yet. Run your first enrichment to see it here.")

# =============================================================================
# HELP TAB
# =============================================================================
elif menu == "🎓 Help":
    st.subheader("🎓 Help & Documentation")
    
    with st.expander("📖 How to Use", expanded=True):
        st.markdown("""
        **Step-by-Step Guide:**
        
        1. **Upload Main File** - Your vendor file with empty columns
        2. **Upload Lookup Files** - Department files (Inventory, Brand, Restrictions)
        3. **Select Matching Column** - Usually ASIN, UPC, or SKU
        4. **Choose Fill Strategy** - "Only fill EMPTY cells" is recommended
        5. **Click Start Enrichment** - Let the system work
        6. **Download** - Get your complete enriched file
        """)
    
    with st.expander("❓ FAQ"):
        st.markdown("""
        **Q: What file formats are supported?**  
        A: Excel (.xlsx, .xls) and CSV files.
        
        **Q: How many lookup files can I upload?**  
        A: Up to 10 files per session.
        
        **Q: Does it handle large files?**  
        A: Yes, optimized for files up to 100MB.
        """)
    
    with st.expander("⚡ Productivity Gains"):
        st.markdown("""
        | Metric | Before | After |
        |--------|--------|-------|
        | Time per enrichment | 60 min | 1 min |
        | Error rate | 5-10% | <0.1% |
        | Daily output | 1 file | 10+ files |
        """)

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.caption("⚡ VirVentures DataOps Platform | From 60 minutes to 60 seconds")
