"""Quick verification tests for v2.0."""
import sys, io
sys.path.insert(0, ".")
from calculator import process_dat_file, read_dat_headers
import pandas as pd
import numpy as np

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

def check(label, cond):
    print(f"  [{PASS if cond else FAIL}] {label}")
    return cond

# ── Test 1: Constant mode (regression) ──────────────────────────────────────
DAT = next(p for p in [
    "../SL_1T60.dat",
    "../Source Files/SL_1T60.dat",
] if __import__("os").path.exists(p))
with open(DAT, encoding="utf-8", errors="replace") as f:
    content = f.read()

df = process_dat_file(
    io.StringIO(content), H0=150.0, Dia=70.0, sig_3=30.0,
    C=-4.42395, C1=10.0, C2=-2.77, temp_mode="constant",
)
print("Test 1: Constant mode (regression)")
check(f"Rows={len(df)}", len(df) == 142240)
check(f"Cols={len(df.columns)} (9 input + 10 calc)", len(df.columns) == 19)
check(f"A[0]={df['A (mm^2)'].iloc[0]:.3f} ~= 3848.451", abs(df["A (mm^2)"].iloc[0] - 3848.451) < 0.01)
check(f"R[0]={df['R'].iloc[0]:.7f} ~= 1.0045373", abs(df["R"].iloc[0] - 1.0045373) < 0.0001)

# ── Test 2: Column selector ──────────────────────────────────────────────────
df2 = process_dat_file(
    io.StringIO(content), H0=150.0, Dia=70.0, sig_3=30.0,
    C=-4.42395, C1=10.0, C2=-2.77,
    keep_input_cols=["Time(s)", "Load_(N)", "Disp.(mm)"],
)
print("\nTest 2: Column selector (keep 3 input cols)")
check(f"Cols={len(df2.columns)} (3 input + 10 calc = 13)", len(df2.columns) == 13)
check("Has eAxis(%)", "eAxis(%)" in df2.columns)
check("Has R", "R" in df2.columns)
check("No Cell_P.(kPa)", "Cell_P.(kPa)" not in df2.columns)

# ── Test 3: Non-constant temperature mode ───────────────────────────────────
n = 200
buf = io.StringIO()
pd.DataFrame({
    "Time(s)": np.arange(n) * 0.5,
    "Load_(N)": np.full(n, 0.5),
    "Disp.(mm)": np.linspace(0, 2.0, n),
    "Temp(C)": 20.0 + np.linspace(0, 5.0, n),
}).to_csv(buf, sep="\t", index=False)
buf.seek(0)

df3 = process_dat_file(
    buf, H0=150.0, Dia=70.0, sig_3=30.0,
    C=-4.42395, C1=10.0, C2=-2.77,
    temp_mode="non_constant",
    L0_app=260.0, alpha_app=0.000017,
    temp_col_name="Temp(C)",
)
print("\nTest 3: Non-constant temperature mode")
check(f"Rows={len(df3)}", len(df3) == n)
# At deltaT=0 (first row), eAxis = Disp[0]/H0*100 = 0/150*100 = 0
check(f"eAxis[0]={df3['eAxis(%)'].iloc[0]:.6f} = 0", abs(df3["eAxis(%)"].iloc[0]) < 0.001)
# With temperature rise, later eAxis should differ from raw Disp/H0*100
raw_ev_last = df3["Disp.(mm)"].iloc[-1] / 150.0 * 100.0
corr_ev_last = df3["eAxis(%)"].iloc[-1]
check(f"Thermal correction applied (raw={raw_ev_last:.4f} != corr={corr_ev_last:.4f})",
      abs(raw_ev_last - corr_ev_last) > 0.0001)

# ── Test 4: read_dat_headers ─────────────────────────────────────────────────
with open(DAT, "rb") as f:
    headers = read_dat_headers(f.read())
print("\nTest 4: read_dat_headers")
check(f"Detected {len(headers)} data columns (not 17)", len(headers) == 9)
check("First col = Time(s)", headers[0] == "Time(s)")
check("Third col = Disp.(mm)", headers[2] == "Disp.(mm)")

# ── Test 5: Error on missing temp column ─────────────────────────────────────
print("\nTest 5: Error on missing Temperature column")
try:
    process_dat_file(
        io.StringIO(content[:5000]), H0=150.0, Dia=70.0, sig_3=30.0,
        C=-4.42395, C1=10.0, C2=-2.77,
        temp_mode="non_constant",
        temp_col_name="NONEXISTENT_COL",
    )
    check("Should have raised ValueError", False)
except ValueError as e:
    check(f"Raised ValueError: {str(e)[:50]}", True)

print("\nAll tests done.")
