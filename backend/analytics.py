import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller


# ===============================
# LOAD TICKS FROM DATABASE
# ===============================
def load_ticks(symbol: str) -> pd.DataFrame:
    from backend.db import get_db, fetch_recent_ticks

    db = get_db()
    rows = fetch_recent_ticks(db, symbol, limit=10000)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(
        {
            "ts": [r.ts for r in rows],
            "price": [r.price for r in rows],
            "qty": [r.qty for r in rows],
        }
    )

    df["ts"] = pd.to_datetime(df["ts"])
    df = df.set_index("ts").sort_index()
    return df


# ===============================
# RESAMPLE TICKS → OHLC
# ===============================
def resample_candles(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    ohlc = df["price"].resample(timeframe).ohlc()
    volume = df["qty"].resample(timeframe).sum()

    candles = ohlc.join(volume)
    candles.columns = ["open", "high", "low", "close", "volume"]
    candles = candles.dropna()
    return candles


# ===============================
# Z-SCORE
# ===============================
def compute_zscore(candles: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    df = candles.copy()

    mean = df["close"].rolling(window).mean()
    std = df["close"].rolling(window).std()

    df["zscore"] = (df["close"] - mean) / std
    return df


# ===============================
# ROLLING CORRELATION
# ===============================
def compute_rolling_correlation(
    df1: pd.DataFrame, df2: pd.DataFrame, window: int = 60
) -> pd.DataFrame:

    merged = pd.DataFrame(index=df1.index)
    merged["close"] = df1["close"]
    merged["other_close"] = df2["close"]

    merged = merged.dropna()

    if len(merged) < window:
        merged["rolling_corr"] = np.nan
        return merged

    merged["rolling_corr"] = merged["close"].rolling(window).corr(
        merged["other_close"]
    )
    return merged


# ===============================
# SAFE HEDGE RATIO (NO CRASH)
# ===============================
def compute_hedge_ratio(
    series_x: pd.Series,
    series_y: pd.Series,
    min_points: int = 20,
) -> float:
    """
    SAFE OLS hedge ratio.
    Returns NaN if insufficient overlapping data.
    """

    x, y = series_x.align(series_y, join="inner")
    x = x.dropna()
    y = y.dropna()

    # 🚨 ABSOLUTE SAFETY CHECK
    if len(x) < min_points or len(y) < min_points:
        return np.nan

    X = sm.add_constant(x.values)
    y_vals = y.values

    try:
        model = sm.OLS(y_vals, X).fit()
        return float(model.params[1])
    except Exception:
        return np.nan


# ===============================
# PAIR SPREAD
# ===============================
def compute_pair_spread(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    beta: float,
) -> pd.DataFrame:

    if np.isnan(beta):
        return pd.DataFrame()

    spread = df1["close"] - beta * df2["close"]
    return pd.DataFrame({"spread": spread})


def compute_spread_zscore(
    spread_df: pd.DataFrame,
    window: int = 60,
) -> pd.DataFrame:

    if spread_df.empty:
        return spread_df

    mean = spread_df["spread"].rolling(window).mean()
    std = spread_df["spread"].rolling(window).std()

    spread_df["spread_zscore"] = (spread_df["spread"] - mean) / std
    return spread_df


# ===============================
# ADF TEST
# ===============================
def run_adf_test(series: pd.Series) -> dict:
    series = series.dropna()

    if len(series) < 20:
        return {"error": "Not enough data for ADF test"}

    stat, pval, _, _, crit, _ = adfuller(series)

    return {
        "adf_statistic": stat,
        "p_value": pval,
        "critical_values": crit,
        "stationary_at_5pct": pval < 0.05,
    }
