# CLAUDE.md — Triaxial Corrected Area App

## Project Overview

Streamlit web app replacing MATLAB for **drained triaxial test corrected cross-section area** calculation using Rowe's modified stress-dilatancy relation. Eliminates the manual Excel step — takes raw lab `.dat` files directly.

**Live URL:** https://kositjar-triaxial-corrected-area.streamlit.app  
**GitHub:** https://github.com/KositJar/triaxial-corrected-area  
**Copyright:** Kosit Jariyatatsakorn © 2026

---

## Current Version: v3.3 (2026-06-14)

> **Canonical change log:** `CHANGELOG.md`. Keep it, this table, the file header
> comments, and the in-app Version History popover in sync on every release.

### Scope (important)
This app is valid **only** for a **consolidated drained (CD)** triaxial test on
an **air-dried sand** specimen. The drainage valve is open during shearing, so
pore pressure `u = 0` and effective stresses equal total stresses
(`eff_sig_1 = sig_1`, `eff_sig_3 = sig_3` — there is no `- u` term). As of v3.2
there is no `u` parameter anywhere in the code or UI.

### Version History
| Version | Date | Changes |
|---|---|---|
| v1.0 | 2026-06-11 | Initial release — basic corrected area calculation |
| v2.0 | 2026-06-12 | Non-constant temperature correction, column selector, How-to, version history, copyright |
| v3.0 | 2026-06-12 | Multiple LVDT support with aliases, full English UI, version number in title |
| v3.1 | 2026-06-14 | Minimal centered login card, blue Enter button, hide title on login page, removed icon from sidebar |
| v3.2 | 2026-06-14 | Scoped to CD air-dried sand: removed `u` input (u=0 → eff=total stress), top nav popover bar, "How It's Calculated" LaTeX page, scope banner |
| v3.3 | 2026-06-14 | New app icon; "Other Tools" nav button (NTC Creep Simulator link); equal-height single-line nav buttons |

---

## File Structure

```
triaxial_app/
├── app.py                  # Streamlit UI — main entry point
├── calculator.py           # Core calculation engine
├── config.json             # Default parameter values (editable via UI)
├── CHANGELOG.md            # Canonical change log (source of truth)
├── requirements.txt        # streamlit>=1.35, pandas>=2.0, numpy>=1.24
├── run_app.bat             # Local launcher (tries py → python → python3)
├── setup.bat               # First-time dependency installer
├── run_tests.py            # Verification test suite (15 tests)
├── .gitignore              # Excludes .streamlit/secrets.toml, __pycache__
├── .streamlit/
│   └── secrets.toml        # LOCAL ONLY — never committed (APP_PASSWORD)
├── icon/
│   └── icon_app_v2.png     # App logo (shown in login card, title bar, browser tab)
└── Source Files/           # Original MATLAB references
    ├── Updated_R_value_v3.mlx      # v1 reference (constant temperature)
    └── Corection_TE_R_value.mlx    # v2 source (non-constant temperature)
```

---

## Key Files

### `calculator.py`
Core engine — no Streamlit dependencies, testable standalone.

**Key function:** `process_dat_file(file_obj, H0, Dia, sig_3, C, C1, C2, ...)`
(no `u` parameter — see Scope above)

Parameters:
- `disp_col_name` — explicit LVDT/displacement column (None = use col[2])
- `temp_mode` — `"constant"` (default) | `"non_constant"`
- `keep_input_cols` — list of input columns to keep in output (None = all)
- `all other params` — see docstring

**Output columns (10 always appended):**
`eAxis(%)`, `del_e_v (%/s)`, `D`, `del_e_vol (%/s)`, `e_vol (%)`, `A (mm^2)`, `q (kPa)`, `sig_1 (kPa)`, `eff_sig_1 (kPa)`, `R`

**Key formulas:**
- Constant mode: `eAxis = (Disp - Disp[0]) / H0 * 100`
- Non-constant mode (iterative): `d_sand[i+1] = d_measured[i] + alpha_app * (L0_app + d_sand[i]) * deltaT[i]`
- Corrected area: `A = A0 * (1 - e_vol/100) / (1 - eAxis/100)`
- Rowe quadratic: `C2*D² + C1*D + (C - R) = 0`, take minimum real root
- Stresses: `q = Load*1000/A`, `sig_1 = sig_3 + q`; since `u = 0`,
  `eff_sig_1 = sig_1`, `eff_sig_3 = sig_3`, `R = eff_sig_1/eff_sig_3`

**Regression values** (SL_1T60.dat, H0=150, Dia=70):
- `A[0] = 3848.451 mm²`
- `R[0] = 1.0045373`

### `app.py`
UI flow (in order):
1. `st.set_page_config` — uses icon_app_v2.png as favicon
2. `_check_password()` — login card (shown when not authenticated, then `st.stop()`)
3. Title header with icon (shown only after login)
4. Title header → top nav bar (📋 Version History, 🔍 How It's Calculated, 🔗 Other Tools link) → scope banner
5. Sidebar: H0, Dia, σ3, C/C1/C2, smoothing, temperature mode (no `u`)
6. Main area: How-to expander → file upload → LVDT selector → output settings → Process button → results

**Password gate:** reads `st.secrets["APP_PASSWORD"]`; if key missing → open access (local dev mode)

**Login card design:**
- `st.container(border=True)` centered in `st.columns([1, 2, 1])`
- Custom CSS: blue button `#4A90D9`, hover `#357abd`
- Content: icon → app name + `v3.1` (color `#7EC8E3`) → "Developed by Kosit Jariyatatsakorn" → subtitle → password field → Enter button

---

## Input / Output Format

**Input:** Tab-delimited `.dat` from lab equipment
- Column layout: `Time(s)` [0] · `Load_(N)` [1] · `Disp.(mm)` [2 default] · ... (up to 9 data columns)
- Files may have 17 header columns but only 9 contain data — `read_dat_headers()` auto-detects via `dropna(axis=1, how='all')`

**Output:** Comma-separated `.dat`
- Filename (single LVDT): `Result_{stem}_{YYMMDD}.dat`
- Filename (multiple LVDTs): `Result_{stem}_{alias}_{YYMMDD}.dat`
- Content: selected input columns + 10 calculated columns

---

## LVDT / Multiple Transducer Logic

- User selects **Single** or **Multiple** transducer mode
- Single: selectbox defaults to col[2], optional alias
- Multiple: multiselect + optional alias text field per LVDT
- Each LVDT → **separate output file**
- Other LVDT columns automatically excluded from each output file
- Alias used in: output filename (sanitized) + column header inside file
- Temperature column shared across all LVDTs

---

## Deployment

**Platform:** Streamlit Community Cloud (free tier)  
**GitHub repo:** KositJar/triaxial-corrected-area (branch: `main`)  
**Deploy trigger:** Auto-deploys on every `git push` to `main`

**To deploy changes:**
```powershell
cd "C:\Users\kosit\Desktop\Sandbox\Correction Area\triaxial_app"
git add <files>
git commit -m "vX.Y: description"
git push
```

**Password setup (Streamlit Cloud):**  
Dashboard → App → ⋮ → Settings → Secrets → paste:
```toml
APP_PASSWORD = "your_password"
```

**Local secrets:** `.streamlit/secrets.toml` (gitignored):
```toml
APP_PASSWORD = geotech13
```

---

## Default Parameters (config.json)

| Parameter | Value | Description |
|---|---|---|
| H0 | 150.0 mm | Initial specimen height |
| Dia | 70.0 mm | Diameter |
| sig_3 | 30.0 kPa | Confining pressure |
| C | -4.42395 | Rowe's constant |
| C1 | 10.0 | Rowe's constant |
| C2 | -2.77 | Rowe's constant |
| smooth_window | 1 | Rolling-mean window (1 = off) |
| temp_mode | "constant" | Temperature correction mode |
| L0_app | 260.0 mm | Apparatus initial height (non-constant mode) |
| alpha_app | 0.000017 /°C | Thermal expansion coefficient |

---

## Running Tests

```powershell
cd "C:\Users\kosit\Desktop\Sandbox\Correction Area\triaxial_app"
py run_tests.py
```

All 15 tests should PASS. Tests cover:
1. Constant mode regression (A[0], R[0] values)
2. Column selector (keep 3 input cols → 13 total)
3. Non-constant temperature correction
4. `read_dat_headers` detects 9 of 17 header columns
5. ValueError on missing temperature column

---

## Known Constraints

- Input files must have Time as col[0] and Load as col[1] (positional, not configurable)
- Streamlit Community Cloud free tier: may sleep after inactivity (cold start ~30s)
- `run_tests.py` requires test data at `../SL_1T60.dat` or `../Source Files/SL_1T60.dat`
- `.streamlit/secrets.toml` is gitignored — never commit it
