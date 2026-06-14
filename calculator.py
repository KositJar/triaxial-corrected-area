# Triaxial Test — Corrected Cross-Section Area Calculator
# Copyright (c) 2026 Kosit Jariyatatsakorn. All rights reserved.
#
# Version history:
#   v1.0 (2026-06-11): Initial release — basic corrected area calculation
#   v2.0 (2026-06-12): Non-constant temperature correction, column selector
#   v3.0 (2026-06-12): Explicit LVDT column selection (disp_col_name parameter),
#                      LVDT alias support in output filename, English error messages
#   v3.2 (2026-06-14): Scoped to consolidated drained (CD) tests on air-dried sand.
#                      Drainage valve open during shearing => u = 0, so effective
#                      stresses equal total stresses. Removed the `u` parameter:
#                      eff_sig_3 = sig_3 and eff_sig_1 = sig_1 directly.

import re

import numpy as np
import pandas as pd
from datetime import date


def read_dat_headers(file_bytes: bytes) -> list:
    """Return column names that have actual data from a tab-delimited .dat file."""
    import io
    content = file_bytes.decode("utf-8", errors="replace")
    df_sample = pd.read_csv(
        io.StringIO(content),
        sep="\t",
        header=0,
        nrows=5,
        engine="python",
        skip_blank_lines=True,
        on_bad_lines="skip",
    )
    df_sample = df_sample.dropna(axis=1, how="all")
    return list(df_sample.columns)


def process_dat_file(
    file_obj,
    H0: float,
    Dia: float,
    sig_3: float,
    C: float,
    C1: float,
    C2: float,
    smooth_window: int = 1,
    temp_mode: str = "constant",
    L0_app: float = 260.0,
    alpha_app: float = 0.000017,
    temp_col_name: str = None,
    keep_input_cols: list = None,
    disp_col_name: str = None,
) -> pd.DataFrame:
    """
    Read a raw tab-delimited .dat file and return a DataFrame with input columns
    (filtered by keep_input_cols) plus 10 calculated columns appended.

    Assumption: consolidated drained (CD) triaxial test on an air-dried sand
    specimen. The drainage valve is open throughout shearing, so pore pressure
    u = 0 and effective stresses equal total stresses (eff_sig_1 = sig_1,
    eff_sig_3 = sig_3). There is therefore no `u` parameter.

    Parameters
    ----------
    file_obj        : file-like object or path
    H0              : initial specimen height (mm)
    Dia             : specimen diameter (mm)
    sig_3           : confining pressure (kPa)
    C, C1, C2       : Rowe's parabola coefficients  C2*D^2 + C1*D + (C - R) = 0
    smooth_window   : rolling-mean window for displacement (1 = no smoothing)
    temp_mode       : "constant" (default) or "non_constant"
    L0_app          : initial apparatus height in mm (non-constant mode only)
    alpha_app       : linear thermal expansion coeff /degC (non-constant mode only)
    temp_col_name   : name of temperature column in input file (non-constant mode only)
    keep_input_cols : list of input column names to include in output (None = all)
    disp_col_name   : explicit displacement/LVDT column name (None = use col[2])
    """
    # ── Read all columns; drop empty ones ────────────────────────────────────
    df_raw = pd.read_csv(
        file_obj,
        sep="\t",
        header=0,
        engine="python",
        skip_blank_lines=True,
        on_bad_lines="skip",
    )
    df_raw = df_raw.dropna(axis=1, how="all")

    if df_raw.shape[1] < 3:
        raise ValueError("File must have at least 3 columns (Time, Load, Displacement)")

    # ── Time and Load are always positional (col[0], col[1]) ─────────────────
    time_col = df_raw.columns[0]
    load_col = df_raw.columns[1]

    # ── Displacement: explicit column name or fall back to col[2] ─────────────
    if disp_col_name is not None:
        if disp_col_name not in df_raw.columns:
            raise ValueError(
                f"Displacement column '{disp_col_name}' not found in file. "
                f"Available columns: {list(df_raw.columns)}"
            )
        disp_col = disp_col_name
    else:
        disp_col = df_raw.columns[2]

    df_raw = df_raw.dropna(subset=[time_col, load_col, disp_col]).reset_index(drop=True)

    time = df_raw[time_col].to_numpy(dtype=float)
    load = df_raw[load_col].to_numpy(dtype=float)
    disp_raw = df_raw[disp_col].to_numpy(dtype=float)

    n = len(time)
    if n < 2:
        raise ValueError("File has too few data rows (minimum 2 required)")

    # ── Optional rolling-mean smoothing on displacement ───────────────────────
    if smooth_window > 1:
        s = pd.Series(disp_raw)
        disp = s.rolling(window=smooth_window, min_periods=1, center=True).mean().to_numpy()
    else:
        disp = disp_raw

    # ── Axial strain ─────────────────────────────────────────────────────────
    if temp_mode == "non_constant":
        # Iterative thermal expansion correction (from MATLAB Corection_TE_R_value.mlx)
        #   L0_current = L0_app + d_sand[i]
        #   d_sand[i+1] = d_measured[i] + alpha_app * L0_current * deltaT[i]
        #   corrected_e_v[i] = d_sand[i+1] / H0 * 100
        if temp_col_name is None or temp_col_name not in df_raw.columns:
            raise ValueError(
                f"Temperature column '{temp_col_name}' not found in file — "
                "please select the correct Temperature column"
            )
        temp = df_raw[temp_col_name].to_numpy(dtype=float)
        T0 = temp[0]
        deltaT = temp - T0

        d_sand = np.zeros(n + 1)
        corrected_e_v = np.zeros(n)
        for i in range(n):
            L0_current = L0_app + d_sand[i]
            d_sand[i + 1] = disp[i] + alpha_app * L0_current * deltaT[i]
            corrected_e_v[i] = d_sand[i + 1] / H0 * 100.0
        e_v = corrected_e_v
    else:
        e_v = (disp - disp[0]) / H0 * 100.0

    # ── Initial cross-sectional area ─────────────────────────────────────────
    A0 = 0.25 * np.pi * Dia ** 2

    # ── Finite-difference derivative of axial strain ─────────────────────────
    del_e_v = np.zeros(n)
    dt = np.diff(time)
    de = np.diff(e_v)
    fwd = de / dt

    del_e_v[0] = fwd[0]
    del_e_v[-1] = fwd[-1]
    for i in range(1, n - 1):
        del_e_v[i] = 0.5 * (fwd[i] + fwd[i - 1])

    # ── Sequential stress-dilatancy + area correction loop ───────────────────
    A = np.empty(n)
    A[0] = A0
    e_vol = np.zeros(n)
    del_e_vol = np.zeros(n)
    D = np.zeros(n)
    q = np.zeros(n)
    sig_1 = np.zeros(n)
    eff_sig_1 = np.zeros(n)
    R = np.zeros(n)

    # Air-dried sand, drained shearing (valve open) => u = 0, so effective
    # stresses equal total stresses.
    eff_sig_3 = sig_3

    for i in range(n):
        q[i] = load[i] * 1000.0 / A[i]
        sig_1[i] = sig_3 + q[i]
        eff_sig_1[i] = sig_1[i]
        R[i] = eff_sig_1[i] / eff_sig_3

        # Solve C2*D^2 + C1*D + (C - R) = 0 — take minimum real root
        C0_coeff = C - R[i]
        discriminant = C1 ** 2 - 4 * C2 * C0_coeff
        if discriminant >= 0:
            sqrt_disc = np.sqrt(discriminant)
            D[i] = min((-C1 + sqrt_disc) / (2 * C2),
                       (-C1 - sqrt_disc) / (2 * C2))
        else:
            D[i] = -C1 / (2 * C2)

        del_e_vol[i] = (1.0 - D[i]) * del_e_v[i]
        e_vol[i] = (0.0 if i == 0 else e_vol[i - 1] + del_e_vol[i])

        if i < n - 1:
            denom = 1.0 - e_v[i] / 100.0
            if abs(denom) < 1e-10:
                denom = 1e-10
            A[i + 1] = A0 * (1.0 - e_vol[i] / 100.0) / denom

    # ── Build output: selected input columns + 10 calculated columns ─────────
    if keep_input_cols is not None:
        cols_to_keep = [c for c in keep_input_cols if c in df_raw.columns]
        df_out = df_raw[cols_to_keep].copy()
    else:
        df_out = df_raw.copy()

    df_out["eAxis(%)"] = e_v
    df_out["del_e_v (%/s)"] = del_e_v
    df_out["D"] = D
    df_out["del_e_vol (%/s)"] = del_e_vol
    df_out["e_vol (%)"] = e_vol
    df_out["A (mm^2)"] = A
    df_out["q (kPa)"] = q
    df_out["sig_1 (kPa)"] = sig_1
    df_out["eff_sig_1 (kPa)"] = eff_sig_1
    df_out["R"] = R

    return df_out


def build_output_filename(original_name: str, lvdt_label: str = "") -> str:
    """Build output filename, optionally embedding a sanitized LVDT label.

    Examples:
        build_output_filename("SL_1T60.dat")               -> "Result_SL_1T60_260612.dat"
        build_output_filename("SL_1T60.dat", "LVDT-50mm")  -> "Result_SL_1T60_LVDT-50mm_260612.dat"
        build_output_filename("SL_1T60.dat", "LVDT_2(mm)") -> "Result_SL_1T60_LVDT_2_mm_260612.dat"
    """
    stem = original_name.rsplit(".", 1)[0]
    today = date.today().strftime("%y%m%d")
    if lvdt_label:
        safe = re.sub(r'[^\w\-]', '_', lvdt_label)
        safe = re.sub(r'_+', '_', safe).strip('_')
        return f"Result_{stem}_{safe}_{today}.dat"
    return f"Result_{stem}_{today}.dat"


def dataframe_to_dat_bytes(df: pd.DataFrame) -> bytes:
    """Serialise DataFrame as comma-separated .dat bytes."""
    return df.to_csv(index=False).encode("utf-8")
