import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="VirVentures Data Enricher", layout="wide")

st.title("📦 VirVentures Data Enricher")
st.caption("Auto-fill empty columns from lookup files")

col1, col2 = st.columns(2)

with col1:
    main_file = st.file_uploader("Main File (vendor with empty columns)", type=["xlsx", "xls"])

with col2:
    lookup_file = st.file_uploader("Lookup File (department with actual data)", type=["xlsx", "xls"])

if main_file and lookup_file:
    main_df = pd.read_excel(main_file)
    lookup_df = pd.read_excel(lookup_file)
    
    st.write(f"Main: {len(main_df)} rows, {len(main_df.columns)} cols")
    st.write(f"Lookup: {len(lookup_df)} rows, {len(lookup_df.columns)} cols")
    
    match_col = st.selectbox("Match on column", main_df.columns.tolist())
    
    if st.button("Enrich"):
        # Simple merge
        enriched = main_df.merge(lookup_df, on=match_col, how='left', suffixes=('', '_fill'))
        
        # Fill empty columns
        for col in main_df.columns:
            if f"{col}_fill" in enriched.columns:
                enriched[col] = enriched[f"{col}_fill"].combine_first(enriched[col])
        
        # Remove helper columns
        enriched = enriched[[c for c in enriched.columns if not c.endswith('_fill')]]
        
        # Download
        output = io.BytesIO()
        enriched.to_excel(output, index=False)
        st.download_button("Download", output.getvalue(), f"Enriched_{datetime.now():%Y%m%d}.xlsx")
