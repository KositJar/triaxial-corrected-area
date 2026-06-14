# Changelog — Triaxial Corrected Area App

All notable changes to this project are recorded here. This file is the
canonical change log; the in-app **Version History** popover, the file header
comments, and the table in `CLAUDE.md` are kept in sync with it.

Copyright © 2026 Kosit Jariyatatsakorn. All rights reserved.

---

## v3.2 — 2026-06-14

**Scoped to consolidated drained (CD) triaxial tests on air-dried sand.**

- Documented the governing assumption in the app: CD test on an air-dried sand
  specimen, drainage valve open during shearing, so pore pressure `u = 0` and
  effective stresses equal total stresses (`σ′₁ = σ₁`, `σ′₃ = σ₃` — **not**
  `σ′₃ = σ₃ − u`).
- Removed the pore-pressure `u` input from the UI, from `config.json`, and from
  the `process_dat_file()` signature in `calculator.py`. `eff_sig_3 = sig_3` and
  `eff_sig_1 = sig_1` are now computed directly.
- The `eff_sig_1 (kPa)` output column is **kept** (now equal to `sig_1`) for
  continuity with existing result files.
- Added a top **navigation bar** of popover buttons; moved **Version History**
  out of the sidebar into it.
- Added a **"How It's Calculated"** page (top nav) that shows the full
  calculation flow as rendered LaTeX equations, covering both constant and
  non-constant temperature modes.
- Added a scope banner on the main page.
- Updated `run_tests.py` to drop the removed `u` argument (4 call sites).
- Replaced the app icon with `icon_app_v2.png` (login card, title bar, favicon).

## v3.1 — 2026-06-14

- Minimal centered login card with blue Enter button.
- Hide title on the login page; "Developed by" moved inside the card.
- Removed the icon from the sidebar.

## v3.0 — 2026-06-12

- Multiple LVDT / displacement-transducer support with optional aliases.
- Full English UI; version number shown in the title.

## v2.0 — 2026-06-12

- Non-constant temperature correction mode.
- Input column selector for the output file.
- How-to section, copyright, and in-app version history.

## v1.0 — 2026-06-11

- Initial release — basic corrected cross-section area calculation.
