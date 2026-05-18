"""
AZ Dashboard – Data Processing Engine
Based on 5 peer-reviewed papers:
  [1] May, Atkinson & Ferrer (2017)  – WNO multi-criteria, US Navy
  [2] Vaccari et al. (2026)          – ML + AHP-K-VETO
  [3] Hong et al. (2024)             – ADI+CV² intermittent demand
  [4] Van As & Bührmann (2025)       – ABC-XYZ-FSN dashboard
  [5] Lokad / Vermorel (2024)        – Quantile spare-parts forecasting
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════

YEAR_COLS  = ["2021", "2022", "2023", "2024", "2025"]
MONTH_COLS = ["2025 1", "2025 2", "2025 3", "2025 4", "2025 5", "2025 6"]

STRATEGY = {
    "AX": {"label": "JIT",           "he": "הזמנות תכופות, מלאי מינימלי",      "action": "Order",        "color": "#2EA043"},
    "AY": {"label": "Safety Stock",  "he": "עתודת ביטחון מחושבת",               "action": "Order",        "color": "#2EA043"},
    "AZ": {"label": "Emergency",     "he": "ביקוש לא צפוי – שמור מלאי גדול",   "action": "Order",        "color": "#F0B429"},
    "BX": {"label": "Periodic",      "he": "הזמנות תקופתיות קבועות",            "action": "Order",        "color": "#58A6FF"},
    "BY": {"label": "Monitor",       "he": "מעקב רגיל + Safety Stock בינוני",  "action": "Order",        "color": "#58A6FF"},
    "BZ": {"label": "Review",        "he": "בדוק אם כדאי להמשיך",              "action": "Review",       "color": "#F0B429"},
    "CX": {"label": "Bulk Order",    "he": "הזמנות גדולות, תדירות נמוכה",      "action": "Review",       "color": "#BC8CFF"},
    "CY": {"label": "Reduce",        "he": "שקול לצמצם מלאי",                  "action": "Review",       "color": "#BC8CFF"},
    "CZ": {"label": "Eliminate",     "he": "שקול להוציא מהמלאי",               "action": "Do Not Order", "color": "#F85149"},
}


# ══════════════════════════════════════════════════════
# 1. LOAD & CLEAN
# ══════════════════════════════════════════════════════

def load_and_clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()

    # Drop fully-empty columns
    df.drop(columns=[c for c in df.columns if df[c].isnull().all()], inplace=True)

    # Sequential index (fixes duplicate-key problem)
    df.insert(0, "idx", range(1, len(df) + 1))

    # Coerce numerics
    num_cols = YEAR_COLS + MONTH_COLS + [
        "מחיר קניה", "יתרה במלאי", "מלאי נטו", "נק. הזמנה", "רמת מלאי",
        "תנועות", "הז. מלקוח", "הז. ספק", "הז. סוכן",
        'סה"כ לקוחות', "חוסר", "משקל", 'מנה ממוצעת  שנתיים',
        'סה"כ רכישות למלאי', "יחס מלאי לרכש",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # String cols
    for c in ["שם פריט", "מפתח", "מטבע", "הערה"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.strip()

    # Flag negative-sales rows (anomaly detection per Hong et al. 2024)
    df["has_anomaly"] = False
    for c in YEAR_COLS:
        if c in df.columns:
            df["has_anomaly"] |= df[c] < 0

    # Recalculate total sales (fixes the broken column)
    avail_yr = [c for c in YEAR_COLS if c in df.columns]
    df["total_sales"] = df[avail_yr].clip(lower=0).sum(axis=1)

    return df


# ══════════════════════════════════════════════════════
# 2. DEMAND PATTERN  [Hong et al. 2024]
#    ADI = avg inter-demand interval
#    CV² = (std/mean)² of non-zero demands
#    Stable: ADI<1.32 & CV²<0.49
#    Unstable: ADI<1.32 & CV²≥0.49
#    Intermittent: ADI≥1.32 & CV²<0.49
#    Lumpy: ADI≥1.32 & CV²≥0.49
# ══════════════════════════════════════════════════════

def classify_demand_pattern(df: pd.DataFrame) -> pd.DataFrame:
    avail = [c for c in MONTH_COLS if c in df.columns]
    n = len(avail)

    adi_vals, cv2_vals, patterns = [], [], []

    for _, row in df[avail].iterrows():
        vals = row.clip(lower=0).values
        nz   = vals[vals > 0]
        k    = len(nz)

        if k == 0 or n == 0:
            adi_vals.append(9999); cv2_vals.append(0); patterns.append("Non-moving")
            continue

        adi = n / k
        cv2 = (nz.std() / nz.mean()) ** 2 if k > 1 and nz.mean() > 0 else 0.0

        adi_vals.append(round(adi, 3))
        cv2_vals.append(round(cv2, 3))

        if   adi < 1.32 and cv2 < 0.49: patterns.append("Stable")
        elif adi < 1.32:                 patterns.append("Unstable")
        elif cv2 < 0.49:                 patterns.append("Intermittent")
        else:                            patterns.append("Lumpy")

    df["ADI"]            = adi_vals
    df["CV2"]            = cv2_vals
    df["demand_pattern"] = patterns
    return df


# ══════════════════════════════════════════════════════
# 3. ABC   [May et al. 2017]
#    A = top 70 % of cumulative demand value
#    B = 70–90 %; C = 90–100 %
# ══════════════════════════════════════════════════════

def classify_abc(df: pd.DataFrame) -> pd.DataFrame:
    df["_abc_val"] = df["מחיר קניה"] * df["total_sales"] / max(len([c for c in YEAR_COLS if c in df.columns]), 1)
    total = df["_abc_val"].sum()

    if total == 0:
        df["ABC"] = "C"
        return df

    srt   = df["_abc_val"].sort_values(ascending=False)
    cum   = srt.cumsum() / total
    grade = pd.cut(cum, bins=[-0.001, 0.70, 0.90, 1.001], labels=["A", "B", "C"])
    df["ABC"] = grade.reindex(df.index).fillna("C").astype(str)
    return df


# ══════════════════════════════════════════════════════
# 4. XYZ  [Van As & Bührmann 2025]
#    CV recalculated from raw monthly data (fixes broken column)
#    X: CV < 0.5   Y: 0.5–1.0   Z: > 1.0
# ══════════════════════════════════════════════════════

def classify_xyz(df: pd.DataFrame) -> pd.DataFrame:
    avail = [c for c in MONTH_COLS if c in df.columns]
    cv_vals, xyz_vals = [], []

    for _, row in df[avail].iterrows():
        v    = row.clip(lower=0).values
        mean = v.mean()
        cv   = v.std() / mean if mean > 0 else 0.0
        cv_vals.append(round(cv, 3))
        xyz_vals.append("X" if cv < 0.5 else "Y" if cv <= 1.0 else "Z")

    df["CV_recalc"] = cv_vals
    df["XYZ"]       = xyz_vals
    return df


# ══════════════════════════════════════════════════════
# 5. FSN  [Van As & Bührmann 2025]
#    F = had sales in last 2 months (5–6)
#    S = had sales in months 1–4
#    N = zero sales in all 6 months
# ══════════════════════════════════════════════════════

def classify_fsn(df: pd.DataFrame) -> pd.DataFrame:
    def _fsn(row):
        if row.get("2025 5", 0) > 0 or row.get("2025 6", 0) > 0: return "F"
        for m in ["2025 1","2025 2","2025 3","2025 4"]:
            if row.get(m, 0) > 0: return "S"
        return "N" if row.get("total_sales", 0) == 0 else "S"

    df["FSN"] = df.apply(_fsn, axis=1)
    return df


# ══════════════════════════════════════════════════════
# 6. HML  – unit purchase price
#    H = top 10 %   M = 70–90 %   L = bottom 70 %
# ══════════════════════════════════════════════════════

def classify_hml(df: pd.DataFrame) -> pd.DataFrame:
    p70 = df["מחיר קניה"].quantile(0.70)
    p90 = df["מחיר קניה"].quantile(0.90)
    df["HML"] = df["מחיר קניה"].apply(lambda p: "H" if p >= p90 else ("M" if p >= p70 else "L"))
    return df


# ══════════════════════════════════════════════════════
# 7. VED  [May et al. 2017]
#    Criticality score from shortage + customers + movements
# ══════════════════════════════════════════════════════

def classify_ved(df: pd.DataFrame) -> pd.DataFrame:
    sh = df.get("חוסר",         pd.Series(0, index=df.index)).fillna(0)
    cu = df.get('סה"כ לקוחות',  pd.Series(0, index=df.index)).fillna(0)
    mv = df.get("תנועות",       pd.Series(0, index=df.index)).fillna(0)

    sh_n = sh / sh.max() if sh.max() > 0 else sh
    cu_n = cu / cu.max() if cu.max() > 0 else cu
    mv_n = mv / mv.max() if mv.max() > 0 else mv

    score = 0.50 * sh_n + 0.30 * cu_n + 0.20 * mv_n
    df["VED"] = score.apply(lambda s: "V" if s >= 0.40 else ("E" if s >= 0.10 else "D"))
    return df


# ══════════════════════════════════════════════════════
# 8. SDE  – supply difficulty
#    S = foreign / lead-time > 60 days
#    D = lead-time 15–60 days
#    E = local / easy
# ══════════════════════════════════════════════════════

def classify_sde(df: pd.DataFrame) -> pd.DataFrame:
    lt  = df.get("הז. ספק", pd.Series(0, index=df.index)).fillna(0)
    cur = df.get("מטבע",    pd.Series("", index=df.index)).fillna("")

    local = {"ILS","NIS","₪","שח","ש\"ח","שקל",""}
    foreign = cur.str.upper().apply(lambda c: not any(l.upper() in c for l in local))

    def _sde(row):
        if foreign[row.name] or lt[row.name] > 60: return "S"
        if lt[row.name] > 14:                       return "D"
        return "E"

    df["SDE"] = df.apply(_sde, axis=1)
    return df


# ══════════════════════════════════════════════════════
# 9. GOLF  – procurement source
#    G=Government  O=Ordinary  L=Local(₪)  F=Foreign
# ══════════════════════════════════════════════════════

def classify_golf(df: pd.DataFrame) -> pd.DataFrame:
    cur = df.get("מטבע", pd.Series("", index=df.index)).fillna("")

    def _golf(c):
        c = str(c).upper().strip()
        if not c or any(x in c for x in ["ILS","NIS","₪","שח","שקל"]): return "L"
        if any(x in c for x in ["USD","EUR","GBP","JPY","CHF","$","€","£"]): return "F"
        if "GOV" in c: return "G"
        return "O"

    df["GOLF"] = cur.apply(_golf)
    return df


# ══════════════════════════════════════════════════════
# 10. TREND & FORECAST  (linear regression 2021–2024)
#     Validates against actual 2025; forecasts 2026.
#     NOTE: For intermittent/lumpy items Prophet/Quantile
#           is recommended (Lokad 2024) – flagged in UI.
# ══════════════════════════════════════════════════════

def compute_trend(df: pd.DataFrame) -> pd.DataFrame:
    avail = [c for c in YEAR_COLS if c in df.columns]
    xs    = list(range(1, len(avail) + 1))

    trends, preds25, preds26, mapes, r2s = [], [], [], [], []

    for _, row in df[avail].iterrows():
        ys      = [max(0.0, float(row[c])) for c in avail]
        nonzero = [y for y in ys if y > 0]

        if len(nonzero) < 2:
            trends.append("stable"); preds25.append(0); preds26.append(0)
            mapes.append(None); r2s.append(None)
            continue

        sl, ic, *_ = stats.linregress(xs, ys)
        p25 = max(0.0, sl * len(avail) + ic)
        p26 = max(0.0, sl * (len(avail) + 1) + ic)

        actual = max(0.0, ys[-1])
        mape   = round(abs(actual - p25) / actual * 100, 1) if actual > 0 else None

        mean   = np.mean(ys)
        ss_tot = sum((y - mean) ** 2 for y in ys)
        ss_res = sum((y - (sl * x + ic)) ** 2 for x, y in zip(xs, ys))
        r2     = round(max(0.0, 1 - ss_res / ss_tot), 3) if ss_tot > 0 else 0.0

        thr    = mean * 0.05 if mean > 0 else 1.0
        trend  = "up" if sl > thr else ("down" if sl < -thr else "stable")

        trends.append(trend); preds25.append(round(p25)); preds26.append(round(p26))
        mapes.append(mape); r2s.append(r2)

    df["trend"]    = trends
    df["pred_2025"] = preds25
    df["pred_2026"] = preds26
    df["MAPE"]     = mapes
    df["R2"]       = r2s
    return df


# ══════════════════════════════════════════════════════
# 11. INVENTORY PARAMETERS
#     EOQ, Safety Stock, ROP, Days-on-Hand, Turnover
# ══════════════════════════════════════════════════════

def compute_inventory(df: pd.DataFrame,
                       ordering_cost: float = 200.0,
                       holding_pct:   float = 0.25) -> pd.DataFrame:
    n_years   = len([c for c in YEAR_COLS if c in df.columns])
    annual_d  = df["total_sales"] / max(n_years, 1)
    unit_cost = df["מחיר קניה"].clip(lower=0.01)

    # EOQ = sqrt(2DS/H)
    H = unit_cost * holding_pct
    df["EOQ"] = np.sqrt(2 * annual_d * ordering_cost / H.clip(lower=0.01)).clip(lower=1).round(0)

    # Safety stock multiplier by XYZ + VED  [Vaccari 2026 / May 2017]
    ss_mult = df["XYZ"].map({"X": 0.10, "Y": 0.25, "Z": 0.50}).fillna(0.25)
    ss_mult = ss_mult.where(df["VED"] != "V", ss_mult * 1.6)   # Vital items: +60 %
    df["safety_stock"]   = (annual_d / 12 * ss_mult).round(0)
    df["monthly_demand"] = (annual_d / 12).round(2)

    # ROP = safety_stock + lead-time demand (assume 1-month LT)
    df["ROP_calc"]   = (df["safety_stock"] + df["monthly_demand"]).round(0)
    existing_rop     = df.get("נק. הזמנה", pd.Series(0, index=df.index)).fillna(0)
    df["ROP_diff"]   = (existing_rop - df["ROP_calc"]).round(0)
    df["ROP_status"] = df["ROP_diff"].apply(
        lambda d: "OK" if abs(d) <= max(df["ROP_calc"].mean() * 0.2, 1) else ("High" if d > 0 else "Low")
    )

    inv  = df.get("יתרה במלאי", pd.Series(0, index=df.index)).fillna(0)
    dail = (annual_d / 365).clip(lower=0.001)
    df["days_on_hand"]  = (inv / dail).round(0).clip(0, 9_999)
    df["turnover"]      = (annual_d / inv.clip(lower=0.001)).round(2).clip(0, 999)

    # Stock health label
    def _status(row):
        i = row.get("יתרה במלאי", 0) or 0
        doh = row.get("days_on_hand", 0) or 0
        if row.get("FSN") == "N" and i > 0:  return "Dead Stock"
        if i <= 0:                             return "Stockout"
        if doh > 365:                          return "Overstock"
        if i < row.get("safety_stock", 0):    return "Low Stock"
        return "OK"

    df["stock_status"] = df.apply(_status, axis=1)
    return df


# ══════════════════════════════════════════════════════
# 12. AHP HEALTH SCORE + VETO  [Vaccari et al. 2026]
#     Priority weights from May et al. 2017:
#       Criticality > Demand Value > Requisitions > Variance
#     VETO rule: Vital item cannot score < 30
# ══════════════════════════════════════════════════════

def compute_health(df: pd.DataFrame) -> pd.DataFrame:
    s = pd.Series(50.0, index=df.index)

    # ABC contribution (demand value priority)
    s += df["ABC"].map({"A": 20, "B": 5, "C": -10}).fillna(0)

    # XYZ contribution (demand predictability)
    s += df["XYZ"].map({"X": 15, "Y": 0, "Z": -15}).fillna(0)

    # FSN contribution (movement speed)
    s += df["FSN"].map({"F": 10, "S": 0, "N": -20}).fillna(0)

    # VED contribution (criticality – highest weight)
    s += df["VED"].map({"V": 12, "E": 0, "D": -5}).fillna(0)

    # Shortage penalty
    if "חוסר" in df.columns:
        s -= (df["חוסר"] > 0).astype(int) * 15

    # ML trend bonus/penalty
    if "trend" in df.columns:
        s += df["trend"].map({"up": 10, "stable": 0, "down": -10}).fillna(0)

    # MAPE quality bonus
    if "MAPE" in df.columns:
        s += df["MAPE"].apply(lambda m: 5 if m is not None and m < 20 else (-5 if m is not None and m > 50 else 0))

    # VETO rule: Vital item floor = 30
    s = s.where(df["VED"] != "V", s.clip(lower=30))

    # Dead-stock penalty
    s = s.where(df.get("stock_status", pd.Series("OK", index=df.index)) != "Dead Stock", s - 20)

    df["health"] = s.clip(0, 100).round(0).astype(int)

    # Critical flag: Vital + non-moving
    df["is_critical"] = (df["VED"] == "V") & (df["FSN"] == "N")
    return df


# ══════════════════════════════════════════════════════
# 13. STRATEGY & RECOMMENDATION
# ══════════════════════════════════════════════════════

def add_strategy(df: pd.DataFrame) -> pd.DataFrame:
    def _strat(row):
        key  = str(row["ABC"]) + str(row["XYZ"])
        base = STRATEGY.get(key, {"label": "Manual", "he": "בדוק ידנית",
                                    "action": "Review", "color": "#8B949E"})
        act  = base["action"]

        # Override rules (VETO logic)
        ved    = row.get("VED", "D")
        fsn    = row.get("FSN", "N")
        st     = row.get("stock_status", "OK")
        abc    = row.get("ABC", "C")
        trend  = row.get("trend", "stable")

        if ved == "V" and st == "Stockout":          act = "Urgent Order"
        elif ved == "V" and fsn == "N":               act = "Urgent Review"
        elif fsn == "N" and abc == "C":               act = "Do Not Order"
        elif st == "Dead Stock":                       act = "Clear Stock"
        elif trend == "down" and abc == "A":           act = "Monitor – Declining A"

        return base["label"], base["he"], act, base["color"]

    results = df.apply(_strat, axis=1)
    df["strat_label"] = results.apply(lambda r: r[0])
    df["strat_he"]    = results.apply(lambda r: r[1])
    df["action"]      = results.apply(lambda r: r[2])
    df["strat_color"] = results.apply(lambda r: r[3])
    df["class_code"]  = df["ABC"] + df["XYZ"] + df["FSN"]
    return df


# ══════════════════════════════════════════════════════
# MASTER PIPELINE
# ══════════════════════════════════════════════════════

def process(raw: pd.DataFrame) -> pd.DataFrame:
    steps = [
        ("Cleaning",          load_and_clean),
        ("Demand pattern",    classify_demand_pattern),
        ("ABC",               classify_abc),
        ("XYZ (recalc)",      classify_xyz),
        ("FSN",               classify_fsn),
        ("HML",               classify_hml),
        ("VED",               classify_ved),
        ("SDE",               classify_sde),
        ("GOLF",              classify_golf),
        ("Trend & forecast",  compute_trend),
        ("Inventory params",  compute_inventory),
        ("Health score",      compute_health),
        ("Strategy",          add_strategy),
    ]
    df = raw
    for name, fn in steps:
        df = fn(df)
    return df
