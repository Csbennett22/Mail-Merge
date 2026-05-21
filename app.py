import sys
import os

# When run directly with `python app.py`, re-launch via streamlit.
# The env var prevents re-entry when Streamlit itself re-executes this file.
if __name__ == "__main__" and not os.environ.get("_STREAMLIT_RUNNING"):
    import subprocess
    env = {**os.environ, "_STREAMLIT_RUNNING": "1"}
    sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", __file__] + sys.argv[1:], env=env))

import io
import re
import pandas as pd
import streamlit as st
from produce_envelopes import register_fonts, create_envelope_pdf

# ---------------------------------------------------------------------------
# Column auto-detection
# ---------------------------------------------------------------------------

_FIELD_SYNONYMS = {
    "Name": [
        "name", "full name", "fullname", "recipient", "addressee",
        "guest", "person", "contact", "display name",
    ],
    "Address": [
        "address", "addr", "street", "street address", "address1",
        "address 1", "address line", "line 1", "line1",
    ],
    "CityStateZip": [
        "citystatezip", "city state zip", "city,state,zip", "city state",
        "citystate", "city/state/zip", "csz", "city, state zip",
        "city state and zip", "city-state-zip",
    ],
}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def guess_column(headers: list[str], field: str) -> str | None:
    synonyms = [_normalize(s) for s in _FIELD_SYNONYMS[field]]
    for header in headers:
        norm = _normalize(header)
        if any(syn in norm or norm in syn for syn in synonyms):
            return header
    return None


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Envelope Generator", page_icon="✉️", layout="centered")
st.title("Envelope PDF Generator")
st.caption("Upload a CSV or Excel file with address data, map your columns, and download a print-ready PDF.")

# --- Step 1: File upload ---
uploaded = st.file_uploader(
    "Upload address file",
    type=["csv", "xlsx", "xls"],
    help="Supported formats: .csv, .xlsx, .xls",
)

if uploaded is None:
    st.info("Upload a file above to get started.")
    st.stop()

# --- Read the file ---
df_raw = None
try:
    name_lower = uploaded.name.lower()
    if name_lower.endswith(".csv"):
        df_raw = pd.read_csv(uploaded)
    else:
        df_raw = pd.read_excel(uploaded)
except Exception as e:
    st.error(f"Could not read file: {e}")
    st.stop()

if df_raw is None or df_raw.empty:
    st.error("The uploaded file contains no data.")
    st.stop()

headers = list(df_raw.columns)
st.success(f"Loaded **{len(df_raw):,}** rows with columns: {', '.join(f'`{h}`' for h in headers)}")

# --- Step 2: Column mapping ---
st.subheader("Map your columns")
st.caption("We've made our best guess — correct any that are wrong.")

col_a, col_b, col_c = st.columns(3)

with col_a:
    default_name = guess_column(headers, "Name")
    name_col = st.selectbox(
        "Name / Recipient",
        options=headers,
        index=headers.index(default_name) if default_name else 0,
        help="Full name to appear on the envelope",
    )

with col_b:
    default_addr = guess_column(headers, "Address")
    addr_col = st.selectbox(
        "Street Address",
        options=headers,
        index=headers.index(default_addr) if default_addr else 0,
        help="Street address line (e.g. 123 Main St)",
    )

with col_c:
    default_csz = guess_column(headers, "CityStateZip")
    csz_col = st.selectbox(
        "City, State, ZIP",
        options=headers,
        index=headers.index(default_csz) if default_csz else 0,
        help="Combined city/state/ZIP line (e.g. Salt Lake City, UT 84101)",
    )

# --- Preview ---
preview_df = df_raw[[name_col, addr_col, csz_col]].rename(
    columns={name_col: "Name", addr_col: "Address", csz_col: "City / State / ZIP"}
)
with st.expander("Preview first 5 rows", expanded=True):
    st.dataframe(preview_df.head(5), use_container_width=True)

# --- Step 3: Options ---
with st.expander("Options", expanded=False):
    env_w = st.number_input("Envelope width (inches)", value=7.25, step=0.25, min_value=3.0, max_value=14.0)
    env_h = st.number_input("Envelope height (inches)", value=5.25, step=0.25, min_value=2.0, max_value=10.0)
    name_size = st.slider("Name font size (pt)", min_value=10, max_value=36, value=21)
    addr_size = st.slider("Address font size (pt)", min_value=8, max_value=28, value=15)

# --- Step 4: Generate ---
st.divider()
if st.button("Generate PDF", type="primary", use_container_width=True):
    mapped = df_raw[[name_col, addr_col, csz_col]].rename(
        columns={name_col: "Name", addr_col: "Address", csz_col: "Zip"}
    )

    register_fonts()

    buf = io.BytesIO()
    try:
        create_envelope_pdf(
            mapped,
            buf,
            envelope_size_inches=(env_w, env_h),
            name_size=name_size,
            address_size=addr_size,
        )
    except Exception as e:
        st.error(f"PDF generation failed: {e}")
        st.stop()

    buf.seek(0)
    st.success(f"Generated {len(mapped):,} envelopes.")
    st.download_button(
        label="Download envelopes.pdf",
        data=buf,
        file_name="envelopes.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
