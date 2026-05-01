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
# FILE LOADER WITH MULTIPLE ENGINES
# =============================================================================
def load_file(uploaded_file):
    """Safely load Excel or CSV file with multiple engine fallbacks"""
    if uploaded_file is None:
        return None
    
    try:
        if uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file)
        
        elif uploaded_file.name.endswith('.xls'):
            # Try xlrd for old .xls files
            try:
                return pd.read_excel(uploaded_file, engine='xlrd')
            except:
                return pd.read_excel(uploaded_file)
        
        else:  # .xlsx files
            # Try openpyxl first
            try:
                return pd.read_excel(uploaded_file, engine='openpyxl')
            except:
                # Fallback: try without specifying engine
                try:
                    return pd.read_excel(uploaded_file)
                except:
                    # Last resort: read as CSV (if it's actually CSV but named .xlsx)
                    return pd.read_csv(uploaded_file)
                    
    except Exception as e:
        st.error(f"Error loading {uploaded_file.name}: {str(e)}")
        st.info("Tip: Save your Excel file as .xls (older format) or .csv if this error persists.")
        return None

def clean_value(val):
    """Clean and return value"""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    if val_str in ['#N/A', 'N/A', 'NA', 'na', 'n/a', '', 'NaN', 'nan', 'None']:
        return None
    return val_str

def extract_sku_from_main(row):
    """Extract SKU from main file"""
    for col in ['INV(A-Z)', 'INV(Z-A)', 'input_Model#', 'Output ASIN']:
        if col in row.index:
            val = clean_value(row[col])
            if val and len(val) > 3:
                return val
    return None

def extract_asin_from_main(row):
    """Extract ASIN from main file"""
    for col in ['Output ASIN', 'ASIN', 'asin', 'input_ASIN']:
        if col in row.index:
            val = clean_value(row[col])
            if val and val.startswith('B') and len(val) == 10:
                return val
    return None

# =============================================================================
# ENRICHMENT FUNCTIONS
# =============================================================================
def enrich_from_inventory_file(main_df, inv_df):
    """Enrich from Inventory File"""
    filled_cols = []
    cells_filled = 0
    
    if inv_df is None or len(inv_df) == 0:
        return main_df, filled_cols, cells_filled
    
    inv_df.columns = [str(c).upper().strip() for c in inv_df.columns]
    
    # Build mappings
    sku_to_data = {}
    asin_to_data = {}
    
    for _, row in inv_df.iterrows():
        sku = None
        for col in ['SKU', 'SKU(A-Z)', 'SKU(Z-A)']:
            if col in inv_df.columns:
                sku = clean_value(row[col])
                if sku:
                    break
        
        asin = None
        for col in ['ASIN', 'ASIN(A-Z)', 'ASIN(Z-A)']:
            if col in inv_df.columns:
                asin = clean_value(row[col])
                if asin:
                    break
        
        data = {}
        for col in inv_df.columns:
            if col not in ['SKU', 'SKU(A-Z)', 'SKU(Z-A)', 'ASIN', 'ASIN(A-Z)', 'ASIN(Z-A)']:
                data[col] = clean_value(row[col])
        
        if sku:
            sku_to_data[sku] = data
        if asin:
            asin_to_data[asin] = data
    
    # Column mappings
    inv_mapping = {
        'Stock': ['STOCK', 'AFN-FULFILLABLE-QUANTITY'],
        'Reserve': ['RESERVE', 'AFN-RESERVED-QUANTITY'],
        'Inbound': ['INBOUND', 'AFN-INBOUND-WORKING-QUANTITY', 'AFN-INBOUND-SHIPPED-QUANTITY'],
        'Net Ordered Units': ['NET ORDERED UNITS', 'UNITS', 'UNITS SOLD'],
        'Sales 30': ['SALES 30', 'LAST 30 DAYS', '30 DAYS'],
        'Sales 3': ['SALES 3', 'LAST 3 MONTHS', '90 DAYS'],
    }
    
    for idx, row in main_df.iterrows():
        sku = extract_sku_from_main(row)
        asin = extract_asin_from_main(row)
        
        data = None
        if sku and sku in sku_to_data:
            data = sku_to_data[sku]
        elif asin and asin in asin_to_data:
            data = asin_to_data[asin]
        
        if data:
            for target_col, source_patterns in inv_mapping.items():
                if target_col in main_df.columns:
                    current_val = clean_value(row[target_col])
                    if current_val is None or current_val in ['0', '0.0', '']:
                        for source_pattern in source_patterns:
                            for inv_col in inv_df.columns:
                                if source_pattern in inv_col and inv_col in data:
                                    val = data[inv_col]
                                    if val and val not in [0, '0', '0.0', None]:
                                        try:
                                            main_df.at[idx, target_col] = val
                                            cells_filled += 1
                                            if target_col not in filled_cols:
                                                filled_cols.append(target_col)
                                        except:
                                            pass
                                        break
                            if main_df.at[idx, target_col] != row[target_col]:
                                break
    
    return main_df, filled_cols, cells_filled

def enrich_from_restrictions_file(main_df, restrict_df):
    """Enrich from Restrictions File"""
    filled_cols = []
    cells_filled = 0
    
    if restrict_df is None or len(restrict_df) == 0:
        return main_df, filled_cols, cells_filled
    
    # Build restricted brands list
    restricted_brands = set()
    for col in restrict_df.columns:
        for val in restrict_df[col].dropna():
            val_str = str(val).strip().lower()
            if len(val_str) > 2:
                restricted_brands.add(val_str)
    
    restriction_columns = ['Restricted', 'Listing Status', 'SKU Status(A-Z)', 'SKU Status(Z-A)']
    
    for idx, row in main_df.iterrows():
        brand_col = None
        for col in ['Brand', 'brand']:
            if col in main_df.columns:
                brand_col = col
                break
        
        if brand_col:
            brand_val = clean_value(row[brand_col])
            if brand_val and str(brand_val).lower() in restricted_brands:
                for col in restriction_columns:
                    if col in main_df.columns:
                        current_val = clean_value(row[col])
                        if current_val is None or current_val == 'NA':
                            try:
                                main_df.at[idx, col] = 'RESTRICTED - REVIEW'
                                cells_filled += 1
                                if col not in filled_cols:
                                    filled_cols.append(col)
                            except:
                                pass
    
    return main_df, filled_cols, cells_filled

def enrich_from_archive_file(main_df, archive_df):
    """Enrich from Archive File"""
    filled_cols = []
    cells_filled = 0
    
    if archive_df is None or len(archive_df) == 0:
        return main_df, filled_cols, cells_filled
    
    archive_df.columns = [str(c).upper().strip() for c in archive_df.columns]
    
    asin_to_data = {}
    for _, row in archive_df.iterrows():
        asin = None
        for col in ['ASIN', 'ASIN(A-Z)', 'ASIN(Z-A)']:
            if col in archive_df.columns:
                asin = clean_value(row[col])
                if asin:
                    break
        
        if asin:
            data = {}
            for col in archive_df.columns:
                if col not in ['ASIN', 'ASIN(A-Z)', 'ASIN(Z-A)', 'SKU', 'SKU(A-Z)', 'SKU(Z-A)']:
                    data[col] = clean_value(row[col])
            asin_to_data[asin] = data
    
    archive_mapping = {
        'TOTAL(Stock+Reserve+inbound)': ['TOTAL', 'TOTAL QUANTITY'],
        'Ageing': ['AGEING', 'AGE'],
        'Return': ['RETURN', 'RETURN RATE'],
    }
    
    for idx, row in main_df.iterrows():
        asin = extract_asin_from_main(row)
        
        if asin and asin in asin_to_data:
            data = asin_to_data[asin]
            for target_col, source_patterns in archive_mapping.items():
                if target_col in main_df.columns:
                    current_val = clean_value(row[target_col])
                    if current_val is None or current_val in ['0', '0.0', 'NA']:
                        for source_pattern in source_patterns:
                            for arch_col in archive_df.columns:
                                if source_pattern in arch_col and arch_col in data:
                                    val = data[arch_col]
                                    if val and val not in [0, '0', '0.0', None, 'NA']:
                                        try:
                                            main_df.at[idx, target_col] = val
                                            cells_filled += 1
                                            if target_col not in filled_cols:
                                                filled_cols.append(target_col)
                                        except:
                                            pass
                                        break
                            if main_df.at[idx, target_col] != row[target_col]:
                                break
    
    return main_df, filled_cols, cells_filled

def calculate_derived_columns(main_df):
    """Calculate derived columns"""
    
    if 'Stock' in main_df.columns and 'Reserve' in main_df.columns and 'Inbound' in main_df.columns:
        total_col = 'TOTAL(Stock+Reserve+inbound)'
        if total_col in main_df.columns:
            for idx, row in main_df.iterrows():
                stock = clean_value(row['Stock'])
                reserve = clean_value(row['Reserve'])
                inbound = clean_value(row['Inbound'])
                
                s = float(stock) if stock and stock != '0' else 0
                r = float(reserve) if reserve and reserve != '0' else 0
                i = float(inbound) if inbound and inbound != '0' else 0
                
                total = s + r + i
                if total > 0:
                    try:
                        main_df.at[idx, total_col] = total
                    except:
                        pass
    
    if 'Days of stock(30)' in main_df.columns and 'Stock' in main_df.columns and 'Sales 30' in main_df.columns:
        for idx, row in main_df.iterrows():
            stock = clean_value(row['Stock'])
            sales = clean_value(row['Sales 30'])
            
            s = float(stock) if stock and stock != '0' else 0
            sl = float(sales) if sales and sales != '0' else 0
            
            if sl > 0:
                try:
                    main_df.at[idx, 'Days of stock(30)'] = round((s / sl) * 30, 1)
                except:
                    pass
    
    return main_df

# =============================================================================
# UI
# =============================================================================
st.markdown("""
<div class="info-box">
    <b>✨ How it works:</b><br>
    1. Upload your MAIN file (has empty columns like Stock, Sales, Restrictions)<br>
    2. Upload INVENTORY file (has Stock, Reserve, Sales data)<br>
    3. Upload RESTRICTIONS file (has Brand blocklist)<br>
    4. Upload ARCHIVE file (has historical ASIN data)<br>
    5. Click ENRICH - all columns will be filled automatically!
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 📄 FILE 1")
    st.caption("Your Vendor File")
    main_file = st.file_uploader("Main Excel", type=["xlsx", "xls", "xlsm", "csv"], key="main", label_visibility="collapsed")

with col2:
    st.markdown("### 📊 FILE 2")
    st.caption("Inventory File")
    inv_file = st.file_uploader("Inventory Excel", type=["xlsx", "xls", "xlsm", "csv"], key="inv", label_visibility="collapsed")

with col3:
    st.markdown("### 🚫 FILE 3")
    st.caption("Restrictions File")
    restrict_file = st.file_uploader("Restrictions Excel", type=["xlsx", "xls", "xlsm", "csv"], key="restrict", label_visibility="collapsed")

with col4:
    st.markdown("### 📚 FILE 4")
    st.caption("Archive File")
    archive_file = st.file_uploader("Archive Excel", type=["xlsx", "xls", "xlsm", "csv"], key="archive", label_visibility="collapsed")

if main_file:
    # Load main file
    main_df = load_file(main_file)
    
    if main_df is not None:
        st.success(f"✅ Main file loaded: {len(main_df)} rows, {len(main_df.columns)} columns")
        
        # Load other files
        inv_df = load_file(inv_file) if inv_file else None
        restrict_df = load_file(restrict_file) if restrict_file else None
        archive_df = load_file(archive_file) if archive_file else None
        
        # Show which files are loaded
        st.markdown("**Files loaded:**")
        col_status1, col_status2, col_status3, col_status4 = st.columns(4)
        col_status1.markdown("📄 Main: ✅" if main_df is not None else "📄 Main: ❌")
        col_status2.markdown("📊 Inventory: ✅" if inv_df is not None else "📊 Inventory: ❌")
        col_status3.markdown("🚫 Restrictions: ✅" if restrict_df is not None else "🚫 Restrictions: ❌")
        col_status4.markdown("📚 Archive: ✅" if archive_df is not None else "📚 Archive: ❌")
        
        if inv_file or restrict_file or archive_file:
            if st.button("🚀 START ENRICHMENT", use_container_width=True):
                enriched_df = main_df.copy()
                results = []
                total_cells = 0
                all_filled_cols = []
                
                progress = st.progress(0)
                status = st.empty()
                steps = []
                if inv_df is not None: steps.append("inventory")
                if restrict_df is not None: steps.append("restrictions")
                if archive_df is not None: steps.append("archive")
                
                current_step = 0
                
                if inv_df is not None:
                    status.info("📊 Processing Inventory File...")
                    enriched_df, cols, cells = enrich_from_inventory_file(enriched_df, inv_df)
                    results.append({"name": "Inventory", "cols": len(cols), "cells": cells})
                    total_cells += cells
                    all_filled_cols.extend(cols)
                    current_step += 1
                    if steps:
                        progress.progress(current_step / len(steps))
                
                if restrict_df is not None:
                    status.info("🚫 Processing Restrictions File...")
                    enriched_df, cols, cells = enrich_from_restrictions_file(enriched_df, restrict_df)
                    results.append({"name": "Restrictions", "cols": len(cols), "cells": cells})
                    total_cells += cells
                    all_filled_cols.extend(cols)
                    current_step += 1
                    if steps:
                        progress.progress(current_step / len(steps))
                
                if archive_df is not None:
                    status.info("📚 Processing Archive File...")
                    enriched_df, cols, cells = enrich_from_archive_file(enriched_df, archive_df)
                    results.append({"name": "Archive", "cols": len(cols), "cells": cells})
                    total_cells += cells
                    all_filled_cols.extend(cols)
                    current_step += 1
                    if steps:
                        progress.progress(current_step / len(steps))
                
                status.info("🧮 Calculating derived columns...")
                enriched_df = calculate_derived_columns(enriched_df)
                
                progress.progress(1.0)
                status.success("✅ Enrichment Complete!")
                
                st.session_state.enriched_df = enriched_df
                timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
                original_name = main_file.name.replace('.xlsx', '').replace('.xls', '').replace('.csv', '')
                st.session_state.enriched_filename = f"{original_name}_Enriched_{timestamp}.xlsx"
                
                st.markdown('<div class="success-box">✅ <b>Enrichment Complete!</b></div>', unsafe_allow_html=True)
                
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                col_r1.metric("Rows", len(enriched_df))
                col_r2.metric("Files Processed", len(results))
                col_r3.metric("Columns Filled", len(set(all_filled_cols)))
                col_r4.metric("Cells Updated", f"{total_cells:,}")
                
                for r in results:
                    st.markdown(f"• **{r['name']}**: {r['cols']} columns, {r['cells']} cells")
                
                preview_cols = ['Output ASIN', 'Stock', 'Reserve', 'Inbound', 'Sales 30', 'Restricted']
                preview_cols = [c for c in preview_cols if c in enriched_df.columns]
                if preview_cols:
                    st.dataframe(enriched_df[preview_cols].head(10), use_container_width=True)

# Download
if st.session_state.enriched_df is not None:
    st.markdown("---")
    st.subheader("⬇️ Download")
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.enriched_df.to_excel(writer, index=False, sheet_name='Enriched')
    
    st.download_button(
        label="📥 Download Excel File",
        data=output.getvalue(),
        file_name=st.session_state.enriched_filename,
        use_container_width=True
    )

st.markdown("---")
st.caption("⚡ VirVentures 4-File Enricher")
