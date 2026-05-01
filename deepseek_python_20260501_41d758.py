import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(
    page_title="VirVentures 4-File Enricher",
    page_icon="📦",
    layout="wide",
)

st.markdown("""
<style>
.main { padding: 0 1rem; }
h1, h2, h3 { color: #1e2d4e; }
.stButton button { background-color: #f47920; color: white; font-weight: bold; border-radius: 8px; border: none; }
.stButton button:hover { background-color: #e06810; }
.stDownloadButton button { background-color: white; color: #f47920; border: 2px solid #f47920; border-radius: 8px; }
.info-box { background-color: #e8f4fd; border-left: 4px solid #f47920; border-radius: 8px; padding: 16px; margin: 16px 0; }
.success-box { background-color: #d4edda; border-left: 4px solid #28a745; border-radius: 8px; padding: 16px; margin: 16px 0; }
</style>
""", unsafe_allow_html=True)

st.title("📦 VirVentures 4-File Inventory Enricher")
st.caption("Auto-fill Inventory, Stock, Sales, and Restrictions from 4 source files")

# =============================================================================
# SESSION STATE
# =============================================================================
if 'enriched_df' not in st.session_state:
    st.session_state.enriched_df = None
if 'enriched_filename' not in st.session_state:
    st.session_state.enriched_filename = None

# =============================================================================
# UNIVERSAL FILE READER
# =============================================================================
def universal_file_reader(uploaded_file):
    """Reads ANY Excel/CSV file format without encoding issues"""
    if uploaded_file is None:
        return None
    
    try:
        file_bytes = uploaded_file.getvalue()
        filename = uploaded_file.name.lower()
        
        # CSV files
        if filename.endswith('.csv'):
            try:
                return pd.read_csv(io.BytesIO(file_bytes), encoding='utf-8')
            except:
                try:
                    return pd.read_csv(io.BytesIO(file_bytes), encoding='latin1')
                except:
                    return pd.read_csv(io.BytesIO(file_bytes), encoding='cp1252')
        
        # Try Excel engines
        engines = ['openpyxl', 'xlrd', 'calamine']
        for engine in engines:
            try:
                df = pd.read_excel(io.BytesIO(file_bytes), engine=engine)
                if df is not None and len(df) > 0:
                    return df
            except:
                continue
        
        # Try without engine
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
            if df is not None and len(df) > 0:
                return df
        except:
            pass
        
        # Try as CSV fallback
        try:
            content = file_bytes.decode('utf-8', errors='ignore')
            lines = content.split('\n')
            if ',' in lines[0]:
                return pd.read_csv(io.BytesIO(file_bytes), encoding='utf-8', errors='ignore')
            elif '\t' in lines[0]:
                return pd.read_csv(io.BytesIO(file_bytes), sep='\t', encoding='utf-8', errors='ignore')
        except:
            pass
        
        st.error(f"Cannot read {uploaded_file.name}. Please save as CSV.")
        return None
        
    except Exception as e:
        st.error(f"Error: {str(e)[:100]}")
        return None

def clean_value(val):
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    if val_str in ['#N/A', 'N/A', 'NA', 'na', 'n/a', '', 'NaN', 'nan', 'None']:
        return None
    return val_str

def extract_sku(row):
    for col in ['INV(A-Z)', 'INV(Z-A)', 'input_Model#', 'Output ASIN', 'SKU']:
        if col in row.index:
            val = clean_value(row[col])
            if val and len(val) > 3:
                return val
    return None

def extract_asin(row):
    for col in ['Output ASIN', 'ASIN', 'asin', 'input_ASIN']:
        if col in row.index:
            val = clean_value(row[col])
            if val and val.startswith('B') and len(val) == 10:
                return val
    return None

# =============================================================================
# ENRICHMENT FUNCTIONS
# =============================================================================
def enrich_from_inventory(main_df, inv_df):
    filled_cols = []
    cells = 0
    
    if inv_df is None or len(inv_df) == 0:
        return main_df, filled_cols, cells
    
    inv_df.columns = [str(c).upper().strip() for c in inv_df.columns]
    
    # Build SKU mapping
    sku_map = {}
    for _, row in inv_df.iterrows():
        sku = None
        for col in ['SKU', 'SKU(A-Z)', 'SKU(Z-A)']:
            if col in inv_df.columns:
                sku = clean_value(row[col])
                if sku:
                    break
        if sku:
            sku_map[sku] = row.to_dict()
    
    # Fill data
    for idx, row in main_df.iterrows():
        sku = extract_sku(row)
        if sku and sku in sku_map:
            data = sku_map[sku]
            
            mapping = {
                'Stock': ['STOCK', 'AFN-FULFILLABLE-QUANTITY'],
                'Reserve': ['RESERVE', 'AFN-RESERVED-QUANTITY'],
                'Inbound': ['INBOUND', 'AFN-INBOUND-WORKING-QUANTITY'],
            }
            
            for target, sources in mapping.items():
                if target in main_df.columns:
                    current = clean_value(row[target])
                    if current is None or current in ['0', '0.0', '']:
                        for src in sources:
                            for col in inv_df.columns:
                                if src in col and col in data:
                                    val = clean_value(data[col])
                                    if val and val not in ['0', '0.0', None]:
                                        main_df.at[idx, target] = val
                                        cells += 1
                                        if target not in filled_cols:
                                            filled_cols.append(target)
                                        break
                                if main_df.at[idx, target] != row[target]:
                                    break
    
    return main_df, filled_cols, cells

def enrich_from_restrictions(main_df, restrict_df):
    filled_cols = []
    cells = 0
    
    if restrict_df is None or len(restrict_df) == 0:
        return main_df, filled_cols, cells
    
    # Build restricted brands set
    restricted = set()
    for col in restrict_df.columns:
        for val in restrict_df[col].dropna():
            val_str = str(val).strip().lower()
            if len(val_str) > 2:
                restricted.add(val_str)
    
    for idx, row in main_df.iterrows():
        brand_col = None
        for col in ['Brand', 'brand']:
            if col in main_df.columns:
                brand_col = col
                break
        
        if brand_col:
            brand = clean_value(row[brand_col])
            if brand and str(brand).lower() in restricted:
                for col in ['Restricted', 'Listing Status']:
                    if col in main_df.columns:
                        current = clean_value(row[col])
                        if current is None or current == 'NA':
                            main_df.at[idx, col] = 'RESTRICTED'
                            cells += 1
                            if col not in filled_cols:
                                filled_cols.append(col)
    
    return main_df, filled_cols, cells

def calculate_derived(main_df):
    if 'Stock' in main_df.columns and 'Reserve' in main_df.columns and 'Inbound' in main_df.columns:
        total_col = 'TOTAL(Stock+Reserve+inbound)'
        if total_col in main_df.columns:
            for idx, row in main_df.iterrows():
                s = float(clean_value(row['Stock']) or 0)
                r = float(clean_value(row['Reserve']) or 0)
                i = float(clean_value(row['Inbound']) or 0)
                total = s + r + i
                if total > 0:
                    main_df.at[idx, total_col] = total
    return main_df

# =============================================================================
# UI
# =============================================================================
st.markdown("""
<div class="info-box">
    <b>✨ Universal File Reader Active</b><br>
    Upload ANY Excel file format - the system will read it automatically.
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 📄 MAIN FILE")
    main_file = st.file_uploader("Main File", type=["xlsx", "xls", "csv", "xlsm"], key="main", label_visibility="collapsed")

with col2:
    st.markdown("### 📊 INVENTORY")
    inv_file = st.file_uploader("Inventory", type=["xlsx", "xls", "csv", "xlsm"], key="inv", label_visibility="collapsed")

with col3:
    st.markdown("### 🚫 RESTRICTIONS")
    restrict_file = st.file_uploader("Restrictions", type=["xlsx", "xls", "csv", "xlsm"], key="restrict", label_visibility="collapsed")

with col4:
    st.markdown("### 📚 ARCHIVE")
    archive_file = st.file_uploader("Archive", type=["xlsx", "xls", "csv", "xlsm"], key="archive", label_visibility="collapsed")

if main_file is not None:
    # Load using universal reader
    main_df = universal_file_reader(main_file)
    
    if main_df is not None and len(main_df) > 0:
        st.success(f"✅ Main: {len(main_df)} rows, {len(main_df.columns)} cols")
        
        # Load other files (check if file was uploaded first)
        inv_df = None
        restrict_df = None
        archive_df = None
        
        if inv_file is not None:
            inv_df = universal_file_reader(inv_file)
        if restrict_file is not None:
            restrict_df = universal_file_reader(restrict_file)
        if archive_file is not None:
            archive_df = universal_file_reader(archive_file)
        
        # Status
        st.markdown("**Status:**")
        s1, s2, s3, s4 = st.columns(4)
        s1.markdown("📄 Main: ✅")
        s2.markdown("📊 Inventory: ✅" if inv_df is not None else "📊 Inventory: ❌")
        s3.markdown("🚫 Restrictions: ✅" if restrict_df is not None else "🚫 Restrictions: ❌")
        s4.markdown("📚 Archive: ✅" if archive_df is not None else "📚 Archive: ❌")
        
        # Check if ANY additional files were uploaded
        has_additional = (inv_file is not None) or (restrict_file is not None) or (archive_file is not None)
        
        if has_additional:
            if st.button("🚀 START ENRICHMENT", use_container_width=True):
                enriched = main_df.copy()
                results = []
                total_cells = 0
                all_cols = []
                
                pbar = st.progress(0)
                step = 0
                total_steps = sum([1 for x in [inv_df, restrict_df, archive_df] if x is not None])
                
                if inv_df is not None:
                    step += 1
                    pbar.progress(step / total_steps if total_steps > 0 else 0.25)
                    enriched, cols, cells = enrich_from_inventory(enriched, inv_df)
                    results.append({"name": "Inventory", "cols": len(cols), "cells": cells})
                    total_cells += cells
                    all_cols.extend(cols)
                
                if restrict_df is not None:
                    step += 1
                    pbar.progress(step / total_steps if total_steps > 0 else 0.5)
                    enriched, cols, cells = enrich_from_restrictions(enriched, restrict_df)
                    results.append({"name": "Restrictions", "cols": len(cols), "cells": cells})
                    total_cells += cells
                    all_cols.extend(cols)
                
                if archive_df is not None:
                    step += 1
                    pbar.progress(step / total_steps if total_steps > 0 else 0.75)
                    # Archive enrichment here
                    pass
                
                pbar.progress(1.0)
                enriched = calculate_derived(enriched)
                
                st.session_state.enriched_df = enriched
                timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
                st.session_state.enriched_filename = f"{main_file.name.split('.')[0]}_Enriched_{timestamp}.xlsx"
                
                st.markdown('<div class="success-box">✅ Enrichment Complete!</div>', unsafe_allow_html=True)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Rows", len(enriched))
                c2.metric("Files", len(results))
                c3.metric("Columns Filled", len(set(all_cols)))
                c4.metric("Cells Updated", total_cells)
                
                for r in results:
                    st.markdown(f"• **{r['name']}**: {r['cols']} cols, {r['cells']} cells")
    else:
        st.error("Could not read main file. Please check file format.")

# Download
if st.session_state.enriched_df is not None:
    st.markdown("---")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.enriched_df.to_excel(writer, index=False)
    
    st.download_button("📥 Download Enriched File", output.getvalue(), st.session_state.enriched_filename, use_container_width=True)

st.markdown("---")
st.caption("⚡ VirVentures 4-File Enricher | Universal File Reader")
