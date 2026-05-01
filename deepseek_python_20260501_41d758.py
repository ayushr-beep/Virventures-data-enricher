import streamlit as st
import pandas as pd
import io
import re
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
.warning-box { background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 8px; padding: 16px; margin: 16px 0; }
.file-card { border: 1px solid #e0e0e0; border-radius: 10px; padding: 12px; margin: 8px 0; background-color: #fafafa; }
.fill-column { background-color: #d4edda; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
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
# HELPER FUNCTIONS
# =============================================================================
def clean_value(val):
    """Clean and return value, handle NaN/None/#N/A/NA"""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    if val_str in ['#N/A', 'N/A', 'NA', 'na', 'n/a', '', 'NaN', 'nan', 'None']:
        return None
    return val_str

def extract_sku_from_main(row):
    """Extract SKU from main file - looks for first non-empty column that looks like SKU"""
    # Your main file has SKUs in INV(A-Z) column and also in first column
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
# ENRICHMENT FUNCTIONS FOR EACH SOURCE FILE
# =============================================================================

def enrich_from_inventory_file(main_df, inv_df):
    """
    Enrich from Inventory File (File 2)
    Maps: SKU/ASIN → Stock, Reserve, Inbound, Sales data
    """
    filled_cols = []
    cells_filled = 0
    
    # Clean inventory file - standardize columns
    inv_df.columns = inv_df.columns.str.upper().str.strip()
    
    # Create mapping dictionaries for different key types
    sku_to_data = {}
    asin_to_data = {}
    
    for _, row in inv_df.iterrows():
        # Get SKU
        sku = None
        for col in ['SKU', 'SKU(A-Z)', 'SKU(Z-A)']:
            if col in inv_df.columns:
                sku = clean_value(row[col])
                if sku:
                    break
        
        # Get ASIN
        asin = None
        for col in ['ASIN', 'ASIN(A-Z)', 'ASIN(Z-A)']:
            if col in inv_df.columns:
                asin = clean_value(row[col])
                if asin:
                    break
        
        # Map data
        data = {}
        for col in inv_df.columns:
            if col not in ['SKU', 'SKU(A-Z)', 'SKU(Z-A)', 'ASIN', 'ASIN(A-Z)', 'ASIN(Z-A)']:
                data[col] = clean_value(row[col])
        
        if sku:
            sku_to_data[sku] = data
        if asin:
            asin_to_data[asin] = data
    
    # Columns to fill from inventory file
    inv_mapping = {
        'STOCK': ['Stock', 'AFN-FULFILLABLE-QUANTITY', 'STOCK'],
        'RESERVE': ['Reserve', 'AFN-RESERVED-QUANTITY', 'RESERVE'],
        'INBOUND': ['Inbound', 'AFN-INBOUND-WORKING-QUANTITY', 'AFN-INBOUND-SHIPPED-QUANTITY', 'INBOUND'],
        'Net Ordered GMS($)': ['NET ORDERED GMS($)', 'GMS', 'SALES'],
        'Net Ordered Units': ['NET ORDERED UNITS', 'UNITS', 'UNITS SOLD'],
        'Lifetime': ['LIFETIME', 'LIFETIME SALES'],
        'Sales 2023': ['SALES 2023', '2023 SALES', 'YTD'],
        'Current year': ['CURRENT YEAR', 'CURRENT YEAR SALES'],
        'Sales 30': ['SALES 30', 'LAST 30 DAYS', '30 DAYS'],
        'Sales 3': ['SALES 3', 'LAST 3 MONTHS', '90 DAYS'],
        'Sales 1': ['SALES 1', 'LAST 1 MONTH'],
        'FBM-LIFETIME': ['FBM-LIFETIME', 'FBM LIFETIME'],
        'FBM-LAST YEAR': ['FBM-LAST YEAR', 'FBM LAST YEAR'],
        'FBM-CURRENT YEAR': ['FBM-CURRENT YEAR', 'FBM CURRENT YEAR'],
    }
    
    # Fill each row
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
                    if current_val is None or current_val == '0' or current_val == '0.0':
                        for source_pattern in source_patterns:
                            for inv_col in inv_df.columns:
                                if source_pattern in inv_col and inv_col in data:
                                    val = data[inv_col]
                                    if val and val not in [0, '0', '0.0', None]:
                                        main_df.at[idx, target_col] = val
                                        cells_filled += 1
                                        if target_col not in filled_cols:
                                            filled_cols.append(target_col)
                                        break
                            if main_df.at[idx, target_col] != row[target_col]:
                                break
    
    return main_df, filled_cols, cells_filled

def enrich_from_restrictions_file(main_df, restrictions_df):
    """
    Enrich from Restrictions File (File 3)
    Checks if brand is restricted
    """
    filled_cols = []
    cells_filled = 0
    
    # Build restricted brands list
    restricted_brands = set()
    brand_restriction_details = {}
    
    for col in restrictions_df.columns:
        for val in restrictions_df[col].dropna():
            val_str = str(val).strip().lower()
            if len(val_str) > 2:
                restricted_brands.add(val_str)
                brand_restriction_details[val_str] = val_str
    
    # Columns to update
    restriction_columns = ['Restricted', 'Listing Status', 'SKU Status(A-Z)', 'SKU Status(Z-A)']
    
    for idx, row in main_df.iterrows():
        # Get brand name
        brand_col = None
        for col in ['Brand', 'brand']:
            if col in main_df.columns:
                brand_col = col
                break
        
        if brand_col:
            brand_val = clean_value(row[brand_col])
            if brand_val:
                brand_lower = str(brand_val).lower()
                
                if brand_lower in restricted_brands:
                    for col in restriction_columns:
                        if col in main_df.columns:
                            if clean_value(row[col]) is None or clean_value(row[col]) == 'NA':
                                main_df.at[idx, col] = 'RESTRICTED - MANUAL REVIEW'
                                cells_filled += 1
                                if col not in filled_cols:
                                    filled_cols.append(col)
    
    return main_df, filled_cols, cells_filled

def enrich_from_archive_file(main_df, archive_df):
    """
    Enrich from Archive Inventory File (File 4)
    Gets historical ASIN data, Total, Fulfillable quantities
    """
    filled_cols = []
    cells_filled = 0
    
    archive_df.columns = archive_df.columns.str.upper().str.strip()
    
    # Create ASIN to data mapping
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
    
    # Column mappings from archive to main
    archive_mapping = {
        'TOTAL(Stock+Reserve+inbound)': ['TOTAL', 'TOTAL QUANTITY'],
        'INV(A-Z)': ['INV(A-Z)', 'SKU'],
        'INV(Z-A)': ['INV(Z-A)', 'SKU'],
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
                    if current_val is None or current_val == '0' or current_val == '0.0' or current_val == 'NA':
                        for source_pattern in source_patterns:
                            for arch_col in archive_df.columns:
                                if source_pattern in arch_col and arch_col in data:
                                    val = data[arch_col]
                                    if val and val not in [0, '0', '0.0', None, 'NA', '#N/A']:
                                        main_df.at[idx, target_col] = val
                                        cells_filled += 1
                                        if target_col not in filled_cols:
                                            filled_cols.append(target_col)
                                        break
                            if main_df.at[idx, target_col] != row[target_col]:
                                break
    
    return main_df, filled_cols, cells_filled

def calculate_derived_columns(main_df):
    """Calculate derived columns like TOTAL and Days of stock"""
    
    # Calculate TOTAL(Stock+Reserve+inbound)
    if 'Stock' in main_df.columns and 'Reserve' in main_df.columns and 'Inbound' in main_df.columns:
        total_col = 'TOTAL(Stock+Reserve+inbound)'
        if total_col in main_df.columns:
            for idx, row in main_df.iterrows():
                stock = clean_value(row['Stock'])
                reserve = clean_value(row['Reserve'])
                inbound = clean_value(row['Inbound'])
                
                stock_val = float(stock) if stock and stock != '0' else 0
                reserve_val = float(reserve) if reserve and reserve != '0' else 0
                inbound_val = float(inbound) if inbound and inbound != '0' else 0
                
                total = stock_val + reserve_val + inbound_val
                if total > 0:
                    main_df.at[idx, total_col] = total
    
    # Calculate Days of stock(30) based on Sales 30
    if 'Days of stock(30)' in main_df.columns and 'Stock' in main_df.columns and 'Sales 30' in main_df.columns:
        for idx, row in main_df.iterrows():
            stock = clean_value(row['Stock'])
            sales_30 = clean_value(row['Sales 30'])
            
            stock_val = float(stock) if stock and stock != '0' else 0
            sales_val = float(sales_30) if sales_30 and sales_30 != '0' else 0
            
            if sales_val > 0:
                days = round((stock_val / sales_val) * 30, 1)
                main_df.at[idx, 'Days of stock(30)'] = days
    
    # Calculate Days of stock(3) based on Sales 3
    if 'Days of stock(3)' in main_df.columns and 'Stock' in main_df.columns and 'Sales 3' in main_df.columns:
        for idx, row in main_df.iterrows():
            stock = clean_value(row['Stock'])
            sales_3 = clean_value(row['Sales 3'])
            
            stock_val = float(stock) if stock and stock != '0' else 0
            sales_val = float(sales_3) if sales_3 and sales_3 != '0' else 0
            
            if sales_val > 0:
                days = round((stock_val / sales_val) * 90, 1)
                main_df.at[idx, 'Days of stock(3)'] = days
    
    return main_df

# =============================================================================
# UI - FILE UPLOADS
# =============================================================================

# File 1: Main File
st.markdown("---")
st.subheader("📁 STEP 1: Upload Your Main File")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 📄 FILE 1")
    st.caption("Your Vendor File")
    main_file = st.file_uploader("Main Excel File", type=["xlsx", "xls", "csv"], key="main")

with col2:
    st.markdown("### 📊 FILE 2")
    st.caption("Inventory File (Stock, Sales)")
    inv_file = st.file_uploader("Inventory Excel File", type=["xlsx", "xls", "csv"], key="inv")

with col3:
    st.markdown("### 🚫 FILE 3")
    st.caption("Restrictions File (Brand Blocklist)")
    restrict_file = st.file_uploader("Restrictions Excel File", type=["xlsx", "xls", "csv"], key="restrict")

with col4:
    st.markdown("### 📚 FILE 4")
    st.caption("Archive Inventory File")
    archive_file = st.file_uploader("Archive Excel File", type=["xlsx", "xls", "csv"], key="archive")

if main_file:
    # Load main file
    if main_file.name.endswith('.csv'):
        main_df = pd.read_csv(main_file)
    else:
        main_df = pd.read_excel(main_file, dtype=str)
    main_df.columns = main_df.columns.str.strip()
    
    st.success(f"✅ Main file loaded: {len(main_df)} rows, {len(main_df.columns)} columns")
    
    # Show empty columns preview
    empty_cols = []
    for col in main_df.columns:
        na_count = main_df[col].isna().sum()
        zero_count = (main_df[col].astype(str).str.strip() == '0').sum()
        na_count += (main_df[col].astype(str).str.strip() == '#N/A').sum()
        na_count += (main_df[col].astype(str).str.strip() == 'NA').sum()
        
        if na_count > len(main_df) * 0.5 or zero_count > len(main_df) * 0.5:
            empty_cols.append(col)
    
    if empty_cols:
        st.info(f"📝 Found {len(empty_cols)} columns that need filling")
        with st.expander("View columns to be filled"):
            st.write(empty_cols[:30])
    
    # ENRICH BUTTON
    if inv_file or restrict_file or archive_file:
        st.markdown("---")
        if st.button("🚀 START ENRICHMENT", use_container_width=True):
            enriched_df = main_df.copy()
            all_results = []
            total_cells = 0
            all_filled_cols = []
            
            progress = st.progress(0)
            status = st.empty()
            step = 0
            total_steps = sum([1 for f in [inv_file, restrict_file, archive_file] if f])
            
            # Step 1: Inventory File
            if inv_file:
                status.info("📊 Processing Inventory File (Stock, Sales, Reserve, Inbound)...")
                if inv_file.name.endswith('.csv'):
                    inv_df = pd.read_csv(inv_file)
                else:
                    inv_df = pd.read_excel(inv_file, dtype=str)
                
                enriched_df, filled_cols, cells = enrich_from_inventory_file(enriched_df, inv_df)
                all_results.append({"file": "Inventory File", "cols": len(filled_cols), "cells": cells})
                total_cells += cells
                all_filled_cols.extend(filled_cols)
                step += 1
                progress.progress(step / total_steps)
            
            # Step 2: Restrictions File
            if restrict_file:
                status.info("🚫 Processing Restrictions File (Brand Blocklist)...")
                if restrict_file.name.endswith('.csv'):
                    restrict_df = pd.read_csv(restrict_file)
                else:
                    restrict_df = pd.read_excel(restrict_file, dtype=str)
                
                enriched_df, filled_cols, cells = enrich_from_restrictions_file(enriched_df, restrict_df)
                all_results.append({"file": "Restrictions File", "cols": len(filled_cols), "cells": cells})
                total_cells += cells
                all_filled_cols.extend(filled_cols)
                step += 1
                progress.progress(step / total_steps)
            
            # Step 3: Archive File
            if archive_file:
                status.info("📚 Processing Archive File (Historical Data)...")
                if archive_file.name.endswith('.csv'):
                    archive_df = pd.read_csv(archive_file)
                else:
                    archive_df = pd.read_excel(archive_file, dtype=str)
                
                enriched_df, filled_cols, cells = enrich_from_archive_file(enriched_df, archive_df)
                all_results.append({"file": "Archive File", "cols": len(filled_cols), "cells": cells})
                total_cells += cells
                all_filled_cols.extend(filled_cols)
                step += 1
                progress.progress(step / total_steps)
            
            # Step 4: Calculate derived columns
            status.info("🧮 Calculating derived columns (TOTAL, Days of stock)...")
            enriched_df = calculate_derived_columns(enriched_df)
            
            progress.progress(1.0)
            status.success("✅ Enrichment Complete!")
            
            # Store results
            st.session_state.enriched_df = enriched_df
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            original_name = main_file.name.replace('.xlsx', '').replace('.xls', '').replace('.csv', '')
            st.session_state.enriched_filename = f"{original_name}_Enriched_{timestamp}.xlsx"
            
            # Show results
            st.markdown('<div class="success-box">✅ <b>Enrichment Complete!</b></div>', unsafe_allow_html=True)
            
            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            col_r1.metric("Rows Processed", len(enriched_df))
            col_r2.metric("Files Processed", len(all_results))
            col_r3.metric("Columns Filled", len(set(all_filled_cols)))
            col_r4.metric("Cells Updated", f"{total_cells:,}")
            
            for res in all_results:
                st.markdown(f"• **{res['file']}**: {res['cols']} columns, {res['cells']} cells filled")
            
            # Preview showing before/after
            st.markdown("### Preview (First 10 rows of filled columns)")
            preview_cols = [c for c in ['Output ASIN', 'INV(A-Z)', 'Stock', 'Reserve', 'Inbound', 'TOTAL(Stock+Reserve+inbound)', 'Restricted', 'Sales 30', 'Days of stock(30)'] if c in enriched_df.columns]
            if preview_cols:
                st.dataframe(enriched_df[preview_cols].head(10), use_container_width=True)

# Download section
if st.session_state.enriched_df is not None:
    st.markdown("---")
    st.subheader("⬇️ Download Enriched File")
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.enriched_df.to_excel(writer, index=False, sheet_name='Enriched_Data')
    
    st.download_button(
        label="📥 Download Complete Excel File",
        data=output.getvalue(),
        file_name=st.session_state.enriched_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# Footer
st.markdown("---")
st.caption("⚡ VirVentures 4-File Enricher | Auto-fills Inventory, Stock, Sales, and Restrictions from 4 source files")
