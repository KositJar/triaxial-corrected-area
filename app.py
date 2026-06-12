# Triaxial Test — Corrected Cross-Section Area Calculator
# Copyright (c) 2026 Kosit Jariyatatsakorn. All rights reserved.
#
# Version history:
#   v1.0 (2026-06-11): Initial release — basic corrected area calculation
#   v2.0 (2026-06-12): Non-constant temperature correction, column selector,
#                      How-to section, copyright, version history
#   v3.0 (2026-06-12): Multiple LVDT support with aliases, full English UI,
#                      version number in title

import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

from calculator import (
    build_output_filename,
    dataframe_to_dat_bytes,
    process_dat_file,
    read_dat_headers,
)

APP_VERSION = "3.0"
APP_DATE = "2026-06-12"
CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "H0": 150.0,
    "Dia": 70.0,
    "sig_3": 30.0,
    "u": 0.0,
    "C": -4.42395,
    "C1": 10.00,
    "C2": -2.77,
    "smooth_window": 1,
    "temp_mode": "constant",
    "L0_app": 260.0,
    "alpha_app": 0.000017,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


# ── Page setup ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Triaxial Corrected Area",
    page_icon="🪨",
    layout="wide",
)
st.title(f"Triaxial Test — Corrected Cross-Section Area  v{APP_VERSION}")
st.caption("Developed by Kosit Jariyatatsakorn")

# ── Password gate ────────────────────────────────────────────────────────────
def _check_password() -> bool:
    """Return True if authenticated. No-op when APP_PASSWORD secret is not set."""
    if st.session_state.get("authenticated"):
        return True
    try:
        correct = st.secrets["APP_PASSWORD"]
    except (KeyError, FileNotFoundError):
        return True  # No password configured — allow access (local dev)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("### 🔒 Password Required")
        pwd = st.text_input("Enter password:", type="password", key="_pwd")
        if st.button("Login", use_container_width=True, type="primary"):
            if pwd == correct:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")
    return False

if not _check_password():
    st.stop()

# ── Sidebar: parameters ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("Parameters")
    cfg = load_config()

    H0 = st.number_input(
        "H₀ — Initial height (mm)",
        value=float(cfg.get("H0", 150.0)),
        min_value=0.1, step=1.0, format="%.2f",
    )
    Dia = st.number_input(
        "Dia — Diameter (mm)",
        value=float(cfg.get("Dia", 70.0)),
        min_value=0.1, step=1.0, format="%.2f",
    )
    sig_3 = st.number_input(
        "σ₃ — Confining pressure (kPa)",
        value=float(cfg.get("sig_3", 30.0)),
        min_value=0.0, step=1.0, format="%.3f",
    )
    u = st.number_input(
        "u — Pore pressure (kPa)",
        value=float(cfg.get("u", 0.0)),
        step=0.1, format="%.3f",
    )

    st.markdown("**Rowe's constants** — fitted from saturated specimen")
    C = st.number_input("C",  value=float(cfg.get("C",  -4.42395)), format="%.5f", step=0.001)
    C1 = st.number_input("C1", value=float(cfg.get("C1",  10.00)),  format="%.4f", step=0.01)
    C2 = st.number_input("C2", value=float(cfg.get("C2",  -2.77)),  format="%.4f", step=0.01)

    st.divider()
    st.markdown("**Displacement smoothing**")
    st.caption("window > 1 applies a rolling mean to displacement before computing eAxis")
    smooth_window = st.number_input(
        "Smoothing window (1 = no smoothing)",
        value=int(cfg.get("smooth_window", 1)),
        min_value=1, max_value=1000, step=1,
    )

    st.divider()
    st.markdown("**Temperature Correction**")
    temp_mode_label = cfg.get("temp_mode", "constant")
    temp_mode = st.radio(
        "Temperature mode",
        options=["constant", "non_constant"],
        format_func=lambda x: "☁ Constant temperature" if x == "constant"
                              else "🌡️ Non-constant temperature",
        index=0 if temp_mode_label == "constant" else 1,
        horizontal=False,
    )

    L0_app = float(cfg.get("L0_app", 260.0))
    alpha_app = float(cfg.get("alpha_app", 0.000017))

    if temp_mode == "non_constant":
        st.caption("Formula: d_sand[i+1] = d_meas[i] + α × L₀_current × ΔT[i]")
        L0_app = st.number_input(
            "L₀_app — Apparatus initial height (mm)",
            value=float(cfg.get("L0_app", 260.0)),
            min_value=0.1, step=1.0, format="%.2f",
        )
        alpha_app = st.number_input(
            "α_app — Thermal expansion coeff (/°C)",
            value=float(cfg.get("alpha_app", 0.000017)),
            format="%.8f", step=0.000001,
        )

    st.divider()
    with st.expander("📋 Version History"):
        st.markdown(
            f"**v{APP_VERSION}** ({APP_DATE}): Multiple LVDT support with aliases, full English UI  \n"
            "**v2.0** (2026-06-12): Temperature correction mode, column selector, How-to, copyright  \n"
            "**v1.0** (2026-06-11): Initial release"
        )

    if st.button("💾 Save as default config", use_container_width=True):
        save_config({
            "H0": H0, "Dia": Dia, "sig_3": sig_3, "u": u,
            "C": C, "C1": C1, "C2": C2,
            "smooth_window": smooth_window,
            "temp_mode": temp_mode,
            "L0_app": L0_app,
            "alpha_app": alpha_app,
        })
        st.success("Saved to config.json")

    st.caption(f"v{APP_VERSION} © Kosit Jariyatatsakorn")

# ── How to Use ───────────────────────────────────────────────────────────────
with st.expander("❓ How to Use", expanded=False):
    st.markdown("""
**Steps:**

1. **Enter Parameters** in the left sidebar
   - H₀: Initial specimen height (mm)
   - Dia: Diameter (mm)
   - σ₃: Confining pressure (kPa)
   - u: Pore pressure (kPa — use 0 for air-dried)
   - C, C1, C2: Rowe's constants fitted from saturated specimen

2. **Select Temperature mode**
   - **Constant**: temperature is stable throughout the test (default)
   - **Non-constant**: temperature varies — enter L₀_app and α_app;
     input file must contain a Temperature column

3. **Upload** `.dat` file(s) from the lab (multiple files: hold Ctrl while selecting)

4. **Select displacement transducer(s)**
   - **Single**: choose which column contains the displacement reading
   - **Multiple**: choose all LVDT columns; optionally rename each one
     (alias is used in the output filename and column header)

5. **Configure output columns** — choose which input columns to keep in the output
   (the 10 calculated columns are always appended; other LVDT columns are
   automatically excluded from each output file)

6. **Select Temperature column** (Non-constant mode only)

7. **Click "▶ Process All Files"**
   - 1 input file × 1 LVDT → 1 output file
   - 1 input file × N LVDTs → N output files

8. **Download** results individually or as a ZIP

---
**Calculated output columns:**
`eAxis(%)` · `del_e_v (%/s)` · `D` · `del_e_vol (%/s)` · `e_vol (%)` · `A (mm²)` · `q (kPa)` · `sig_1 (kPa)` · `eff_sig_1 (kPa)` · `R`

**Output filename (single LVDT):** `Result_{name}_{YYMMDD}.dat`
**Output filename (multiple LVDTs):** `Result_{name}_{LVDT alias}_{YYMMDD}.dat`
    """)

# ── File upload ───────────────────────────────────────────────────────────────
uploaded_files = st.file_uploader(
    "Select `.dat` file(s) from the lab (multiple files supported)",
    type=["dat"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Upload a file to begin.")
    st.stop()

# ── Read headers from first file ─────────────────────────────────────────────
headers = read_dat_headers(uploaded_files[0].getvalue())

if not headers:
    st.error("Could not read headers from file. Please check the file format.")
    st.stop()

default_disp_idx = min(2, len(headers) - 1)

# ── LVDT / Displacement column selector ──────────────────────────────────────
st.markdown("**📏 Displacement Transducer(s)**")

transducer_mode = st.radio(
    "Number of displacement transducers",
    options=["single", "multiple"],
    format_func=lambda x: "Single transducer" if x == "single" else "Multiple transducers",
    horizontal=True,
)

if transducer_mode == "single":
    disp_col_single = st.selectbox(
        "Displacement column",
        options=headers,
        index=default_disp_idx,
    )
    lvdt_cols = [disp_col_single]
    lvdt_aliases = {disp_col_single: ""}
else:
    default_lvdt = [headers[default_disp_idx]]
    lvdt_cols = st.multiselect(
        "Displacement columns (select all LVDT columns)",
        options=headers,
        default=default_lvdt,
    )
    if not lvdt_cols:
        st.warning("Please select at least one displacement column.")
        st.stop()

    st.caption("Optionally rename each LVDT — used in the output filename and column header.")
    lvdt_aliases = {}
    alias_cols = st.columns(min(len(lvdt_cols), 4))
    for i, col in enumerate(lvdt_cols):
        with alias_cols[i % len(alias_cols)]:
            alias = st.text_input(
                f"`{col}`",
                key=f"alias_{col}",
                placeholder="alias (optional)",
            )
            lvdt_aliases[col] = alias.strip()

# ── Output column configuration ───────────────────────────────────────────────
st.markdown("**⚙️ Output Settings**")

col_sel, col_temp = st.columns([3, 2])

with col_sel:
    keep_input_cols = st.multiselect(
        "Input columns to include in output",
        options=headers,
        default=headers,
    )

with col_temp:
    if temp_mode == "non_constant":
        default_temp_idx = 3 if len(headers) > 3 else 0
        temp_col_name = st.selectbox(
            "🌡️ Temperature column in input file",
            options=headers,
            index=default_temp_idx,
        )
    else:
        temp_col_name = None
        st.caption("Temperature correction: disabled (Constant mode)")

if not keep_input_cols:
    st.warning("Please select at least one column.")
    st.stop()

# ── Process button ────────────────────────────────────────────────────────────
run = st.button("▶ Process All Files", type="primary", use_container_width=True)

if not run:
    st.stop()

results = []
errors = []
total = len(uploaded_files) * len(lvdt_cols)
done = 0
progress = st.progress(0.0, text="Processing…")

for upload in uploaded_files:
    content = upload.getvalue().decode("utf-8", errors="replace")

    for lvdt_col in lvdt_cols:
        alias = lvdt_aliases.get(lvdt_col, "").strip()
        effective_name = alias if alias else lvdt_col

        progress.progress(
            done / total,
            text=f"Processing {upload.name} — {effective_name}…",
        )

        # Exclude other LVDT columns from this output file
        other_lvdts = [c for c in lvdt_cols if c != lvdt_col]
        effective_keep = [c for c in keep_input_cols if c not in other_lvdts]

        # Pass None (keep all) only for single LVDT with all headers selected
        if not other_lvdts and effective_keep == headers:
            keep_arg = None
        else:
            keep_arg = effective_keep

        try:
            df_result = process_dat_file(
                io.StringIO(content),
                H0=H0, Dia=Dia, sig_3=sig_3, u=u,
                C=C, C1=C1, C2=C2,
                smooth_window=int(smooth_window),
                temp_mode=temp_mode,
                L0_app=L0_app,
                alpha_app=alpha_app,
                temp_col_name=temp_col_name,
                disp_col_name=lvdt_col,
                keep_input_cols=keep_arg,
            )

            # Rename LVDT column in output if alias provided
            if alias and alias != lvdt_col:
                df_result = df_result.rename(columns={lvdt_col: alias})

            # Build filename — include LVDT label for multiple mode, or if alias given
            if transducer_mode == "multiple":
                lvdt_label = effective_name
            else:
                lvdt_label = alias  # empty string → no label in filename

            out_name = build_output_filename(upload.name, lvdt_label)
            out_bytes = dataframe_to_dat_bytes(df_result)
            results.append((out_name, out_bytes, df_result))
        except Exception as exc:
            errors.append(f"**{upload.name}** ({effective_name}): {exc}")

        done += 1

progress.progress(1.0, text="Done")

if errors:
    st.error("Errors occurred in some files:")
    for e in errors:
        st.markdown(f"- {e}")

if not results:
    st.stop()

# ── Show results ──────────────────────────────────────────────────────────────
st.success(f"Processed {len(results)} file(s) successfully")

for out_name, out_bytes, df_result in results:
    with st.expander(f"📄 {out_name}", expanded=len(results) == 1):
        st.dataframe(df_result.head(10), use_container_width=True)
        col_l, col_r = st.columns([1, 3])
        with col_l:
            st.download_button(
                label="⬇ Download",
                data=out_bytes,
                file_name=out_name,
                mime="text/plain",
                use_container_width=True,
                key=f"dl_{out_name}",
            )
        with col_r:
            temp_label = f"  |  Temp mode: {temp_mode}" if temp_mode == "non_constant" else ""
            st.caption(
                f"Rows: {len(df_result):,}  |  "
                f"A₀ = {df_result['A (mm^2)'].iloc[0]:.3f} mm²  |  "
                f"R₀ = {df_result['R'].iloc[0]:.7f}"
                f"{temp_label}"
            )

# ── Batch ZIP ─────────────────────────────────────────────────────────────────
if len(results) > 1:
    st.divider()
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for out_name, out_bytes, _ in results:
            zf.writestr(out_name, out_bytes)
    st.download_button(
        label=f"⬇ Download All as ZIP ({len(results)} files)",
        data=zip_buf.getvalue(),
        file_name="triaxial_results.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True,
    )
