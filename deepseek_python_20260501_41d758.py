import streamlit as st
import pandas as pd
import io
from datetime import datetime
from difflib import get_close_matches

# ================= CONFIG =================
st.set_page_config(page_title="VirVentures Enricher", layout="wide")

# ================= CSS =================
st.markdown("""
<style>
h1, h2, h3 { color: #f47920; }
.stButton>button { background-color: #f47920; color: white; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ================= SESSION =================
if "enriched_df" not in st.session_state:
    st.session_state.enriched_df = None

# ================= UNIVERSAL FILE READER =================
def universal_file_reader(uploaded_file):
    if uploaded_file is None:
        return None

    try:
        file_bytes = uploaded_file.read()
        buffer = io.BytesIO(file_bytes)

        # Excel attempts
        for engine in ["openpyxl", "xlrd"]:
            try:
                buffer.seek(0)
                return pd.read_excel(buffer, engine=engine)
            except:
                continue

        # CSV fallback
        for enc in ["utf-8", "latin1", "cp1252"]:
            try:
                buffer.seek(0)
                return pd.read_csv(buffer, encoding=enc)
            except:
                continue

        return None

    except:
        return None


# ================= CLEAN VALUE =================
def clean_value(val):
    try:
        if pd.isna(val):
            return None

        v = str(val).strip().lower()

        if v in ["", "na", "n/a", "#n/a", "none"]:
            return None
        if v in ["0", "0.0"]:
            return None

        return val
    except:
        return None


# ================= AUTO COLUMN MAPPING =================
STANDARD_MAP = {
    "sku": ["sku", "model", "item code", "inv"],
    "asin": ["asin", "output asin"],
    "stock": ["stock", "fulfillable", "available"],
    "reserve": ["reserve", "reserved"],
    "inbound": ["inbound", "incoming"],
    "brand": ["brand"],
}

def auto_map(df):
    if df is None or len(df) == 0:
        return {}

    mapped = {}
    cols = [c.lower() for c in df.columns]

    for key, variations in STANDARD_MAP.items():
        for col in cols:
            if col in variations:
                mapped[key] = col
                break

            match = get_close_matches(col, variations, n=1, cutoff=0.75)
            if match:
                mapped[key] = col
                break

    return mapped


# ================= SKU / ASIN =================
def extract_sku(row):
    for c in ['INV(A-Z)', 'INV(Z-A)', 'input_Model#', 'SKU']:
        if c in row:
            val = clean_value(row[c])
            if val:
                return str(val)
    return None

def extract_asin(row):
    for c in ['Output ASIN', 'ASIN', 'asin']:
        if c in row:
            val = clean_value(row[c])
            if val:
                return str(val)
    return None


# ================= INVENTORY ENRICH =================
def enrich_inventory(main_df, inv_df):
    if inv_df is None or len(inv_df) == 0:
        return main_df, {}

    inv_map = auto_map(inv_df)
    counts = {"Stock": 0, "Reserve": 0, "Inbound": 0}

    lookup = {}

    for _, r in inv_df.iterrows():
        sku = str(r.get(inv_map.get("sku", ""), ""))
        asin = str(r.get(inv_map.get("asin", ""), ""))

        data = {
            "Stock": r.get(inv_map.get("stock", "")),
            "Reserve": r.get(inv_map.get("reserve", "")),
            "Inbound": r.get(inv_map.get("inbound", ""))
        }

        if sku:
            lookup[("SKU", sku)] = data
        if asin:
            lookup[("ASIN", asin)] = data

    for i, r in main_df.iterrows():
        sku = extract_sku(r)
        asin = extract_asin(r)

        source = None
        if sku and ("SKU", sku) in lookup:
            source = lookup[("SKU", sku)]
        elif asin and ("ASIN", asin) in lookup:
            source = lookup[("ASIN", asin)]

        if source:
            for col in ["Stock", "Reserve", "Inbound"]:
                if col in main_df.columns:
                    if clean_value(r.get(col)) is None:
                        val = source.get(col)
                        if val is not None:
                            main_df.at[i, col] = val
                            counts[col] += 1

    return main_df, counts


# ================= RESTRICTIONS =================
def enrich_restrictions(main_df, res_df):
    if res_df is None or len(res_df) == 0:
        return main_df, 0

    blocked = set(res_df.iloc[:, 0].astype(str).str.lower())
    count = 0

    if "Brand" in main_df.columns:
        for i, r in main_df.iterrows():
            brand = str(r.get("Brand", "")).lower()
            if brand in blocked:
                main_df.at[i, "Restricted"] = "Yes"
                count += 1

    return main_df, count


# ================= DERIVED =================
def calculate(df):
    if df is None:
        return df

    def num(x):
        try: return float(x)
        except: return 0

    if "TOTAL(Stock+Reserve+inbound)" in df.columns:
        df["TOTAL(Stock+Reserve+inbound)"] = df.apply(
            lambda r: num(r.get("Stock")) + num(r.get("Reserve")) + num(r.get("Inbound")), axis=1
        )

    return df


# ================= HISTORY =================
def save_history(df):
    if df is None or len(df) == 0:
        return

    df["Processed_Date"] = datetime.now()

    try:
        old = pd.read_csv("history.csv")
        df = pd.concat([old, df])
    except:
        pass

    df.to_csv("history.csv", index=False)


# ================= UI =================
st.title("🚀 VirVentures Data Enricher")

c1, c2, c3, c4 = st.columns(4)

with c1:
    main_file = st.file_uploader("Main File")

with c2:
    inv_file = st.file_uploader("Inventory")

with c3:
    res_file = st.file_uploader("Restrictions")

with c4:
    arch_file = st.file_uploader("Archive")


# ================= PROCESS =================
if st.button("ENRICH"):

    if main_file is None:
        st.error("Upload main file")
    else:
        prog = st.progress(0)

        main_df = universal_file_reader(main_file)
        prog.progress(0.2)

        inv_df = universal_file_reader(inv_file) if inv_file else None
        prog.progress(0.4)

        res_df = universal_file_reader(res_file) if res_file else None
        prog.progress(0.6)

        if main_df is not None:

            main_df, stats = enrich_inventory(main_df, inv_df)
            main_df, res_count = enrich_restrictions(main_df, res_df)
            main_df = calculate(main_df)

            save_history(main_df)

            prog.progress(1.0)

            st.success("Done ✅")
            st.write("Filled:", stats)
            st.write("Restricted:", res_count)

            st.session_state.enriched_df = main_df

        else:
            st.error("Main file failed")


# ================= DOWNLOAD =================
if st.session_state.enriched_df is not None:
    output = io.BytesIO()

    try:
        # Try openpyxl
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            st.session_state.enriched_df.to_excel(writer, index=False)
    except:
        # Fallback to xlsxwriter
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            st.session_state.enriched_df.to_excel(writer, index=False)

    st.download_button(
        "Download Excel",
        data=output.getvalue(),
        file_name=f"enriched_{datetime.now().strftime('%H%M')}.xlsx"
    )


# ================= DASHBOARD =================
st.markdown("---")
st.header("📊 Dashboard")

try:
    hist = pd.read_csv("history.csv")

    if hist is not None and len(hist) > 0:
        hist["Processed_Date"] = pd.to_datetime(hist["Processed_Date"])

        daily = hist.groupby(hist["Processed_Date"].dt.date)["Stock"].sum()

        st.line_chart(daily)

    else:
        st.info("No data yet")

except:
    st.info("Run enrichment to build dashboard")
