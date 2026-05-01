import streamlit as st
import pandas as pd
import io
from datetime import datetime

# ================= PAGE CONFIG =================
st.set_page_config(page_title="VirVentures 4-File Enricher", layout="wide")

# ================= CSS =================
st.markdown("""
<style>
body { background-color: #f7f7f7; }
h1, h2, h3 { color: #f47920; }
.stButton>button {
    background-color: #f47920;
    color: white;
    border-radius: 8px;
}
.stProgress > div > div > div > div {
    background-color: #f47920;
}
</style>
""", unsafe_allow_html=True)

# ================= SESSION STATE =================
if "enriched_df" not in st.session_state:
    st.session_state.enriched_df = None

# ================= UNIVERSAL FILE READER =================
def universal_file_reader(uploaded_file):
    if uploaded_file is None:
        return None

    try:
        file_bytes = uploaded_file.read()
        file_buffer = io.BytesIO(file_bytes)

        # Try Excel engines
        for engine in ["openpyxl", "xlrd"]:
            try:
                df = pd.read_excel(file_buffer, engine=engine)
                return df
            except:
                file_buffer.seek(0)

        # Try CSV encodings
        for enc in ["utf-8", "latin1", "cp1252"]:
            try:
                file_buffer.seek(0)
                df = pd.read_csv(file_buffer, encoding=enc)
                return df
            except:
                continue

        # Final fallback: generic read
        try:
            file_buffer.seek(0)
            df = pd.read_csv(file_buffer)
            return df
        except:
            st.error(f"⚠️ Could not read file: {uploaded_file.name}")
            return None

    except Exception:
        st.error(f"⚠️ Error loading file: {uploaded_file.name}")
        return None


# ================= CLEAN VALUE =================
def clean_value(val):
    try:
        if pd.isna(val):
            return None

        val_str = str(val).strip().lower()

        if val_str in ["", "na", "n/a", "#n/a", "none"]:
            return None

        if val_str in ["0", "0.0"]:
            return None

        return val
    except:
        return None


# ================= EXTRACT SKU =================
def extract_sku(row):
    cols = ['INV(A-Z)', 'INV(Z-A)', 'input_Model#', 'Output ASIN', 'SKU']
    for col in cols:
        if col in row:
            val = clean_value(row[col])
            if val is not None:
                return str(val)
    return None


# ================= EXTRACT ASIN =================
def extract_asin(row):
    cols = ['Output ASIN', 'ASIN', 'asin', 'input_ASIN']
    for col in cols:
        if col in row:
            val = clean_value(row[col])
            if val is not None:
                return str(val)
    return None


# ================= INVENTORY ENRICH =================
def enrich_from_inventory(main_df, inv_df):
    if inv_df is None or len(inv_df) == 0:
        return main_df, {}

    filled_counts = {}

    # Normalize columns
    inv_df.columns = [c.upper() for c in inv_df.columns]

    # Build lookup
    lookup = {}
    for _, row in inv_df.iterrows():
        sku = str(row.get("SKU") or row.get("SKU(A-Z)") or row.get("SKU(Z-A)") or "")
        asin = str(row.get("ASIN") or "")

        data = {
            "Stock": row.get("STOCK") or row.get("AFN-FULFILLABLE-QUANTITY"),
            "Reserve": row.get("RESERVE") or row.get("AFN-RESERVED-QUANTITY"),
            "Inbound": row.get("INBOUND") or row.get("AFN-INBOUND-WORKING-QUANTITY")
        }

        if sku:
            lookup[("SKU", sku)] = data
        if asin:
            lookup[("ASIN", asin)] = data

    # Fill main file
    for col in ["Stock", "Reserve", "Inbound"]:
        filled_counts[col] = 0

    for i, row in main_df.iterrows():
        sku = extract_sku(row)
        asin = extract_asin(row)

        source = None
        if sku and ("SKU", sku) in lookup:
            source = lookup[("SKU", sku)]
        elif asin and ("ASIN", asin) in lookup:
            source = lookup[("ASIN", asin)]

        if source:
            for col in ["Stock", "Reserve", "Inbound"]:
                if col in main_df.columns:
                    current_val = clean_value(row.get(col))
                    if current_val is None:
                        new_val = source.get(col)
                        if new_val is not None:
                            main_df.at[i, col] = new_val
                            filled_counts[col] += 1

    return main_df, filled_counts


# ================= RESTRICTIONS ENRICH =================
def enrich_from_restrictions(main_df, restrict_df):
    if restrict_df is None or len(restrict_df) == 0:
        return main_df, 0

    restricted_brands = set(restrict_df.iloc[:, 0].astype(str).str.lower())

    count = 0
    if "Brand" in main_df.columns:
        for i, row in main_df.iterrows():
            brand = str(row.get("Brand", "")).lower()
            if brand in restricted_brands:
                main_df.at[i, "Restricted"] = "Yes"
                count += 1

    return main_df, count


# ================= ARCHIVE ENRICH =================
def enrich_from_archive(main_df, archive_df):
    if archive_df is None or len(archive_df) == 0:
        return main_df

    archive_lookup = {}
    for _, row in archive_df.iterrows():
        asin = str(row.get("ASIN") or "")
        archive_lookup[asin] = row.to_dict()

    for i, row in main_df.iterrows():
        asin = extract_asin(row)
        if asin in archive_lookup:
            # Example: fill listing status
            if "Listing Status" in main_df.columns:
                if clean_value(row.get("Listing Status")) is None:
                    main_df.at[i, "Listing Status"] = archive_lookup[asin].get("Listing Status")

    return main_df


# ================= DERIVED CALCULATIONS =================
def calculate_derived(df):
    if df is None or len(df) == 0:
        return df

    def safe_num(x):
        try:
            return float(x)
        except:
            return 0

    if "TOTAL(Stock+Reserve+inbound)" in df.columns:
        df["TOTAL(Stock+Reserve+inbound)"] = df.apply(
            lambda r: safe_num(r.get("Stock")) +
                      safe_num(r.get("Reserve")) +
                      safe_num(r.get("Inbound")), axis=1
        )

    if "Days of stock(30)" in df.columns:
        def calc_days(r):
            stock = safe_num(r.get("Stock"))
            sales = safe_num(r.get("Sales 30"))
            if sales > 0:
                return (stock / sales) * 30
            return None

        df["Days of stock(30)"] = df.apply(calc_days, axis=1)

    return df


# ================= UI =================
st.title("🚀 VirVentures 4-File Data Enricher")

col1, col2, col3, col4 = st.columns(4)

with col1:
    main_file = st.file_uploader("📂 Main File", type=["xlsx", "xls", "xlsm", "csv"])

with col2:
    inv_file = st.file_uploader("📦 Inventory File", type=["xlsx", "xls", "xlsm", "csv"])

with col3:
    restrict_file = st.file_uploader("🚫 Restrictions File", type=["xlsx", "xls", "csv"])

with col4:
    archive_file = st.file_uploader("🗂 Archive File", type=["xlsx", "xls", "csv"])


# ================= PROCESSING =================
if st.button("⚡ ENRICH DATA"):

    if main_file is None:
        st.error("❌ Please upload Main File")
    else:
        progress = st.progress(0)

        steps = 5
        step = 0

        # Load files
        main_df = universal_file_reader(main_file)
        step += 1
        progress.progress(step / steps)

        inv_df = universal_file_reader(inv_file) if inv_file is not None else None
        step += 1
        progress.progress(step / steps)

        restrict_df = universal_file_reader(restrict_file) if restrict_file is not None else None
        step += 1
        progress.progress(step / steps)

        archive_df = universal_file_reader(archive_file) if archive_file is not None else None
        step += 1
        progress.progress(step / steps)

        if main_df is not None and len(main_df) > 0:

            # Enrichment
            main_df, inv_stats = enrich_from_inventory(main_df, inv_df)
            main_df, restrict_count = enrich_from_restrictions(main_df, restrict_df)
            main_df = enrich_from_archive(main_df, archive_df)
            main_df = calculate_derived(main_df)

            step += 1
            progress.progress(step / steps)

            st.success("✅ Enrichment Complete!")

            # Stats
            st.subheader("📊 Fill Summary")
            st.write(inv_stats)
            st.write(f"Restricted flagged: {restrict_count}")

            st.session_state.enriched_df = main_df

        else:
            st.error("❌ Main file could not be processed")


# ================= DOWNLOAD =================
if st.session_state.enriched_df is not None:

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        st.session_state.enriched_df.to_excel(writer, index=False)

    st.download_button(
        label="⬇️ Download Enriched File",
        data=output.getvalue(),
        file_name=f"VirVentures_Enriched_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
