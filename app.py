import asyncio
import threading

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from backend.db import get_db, init_db
from backend.ingestion import listen_to_binance
from backend.analytics import (
    load_ticks,
    resample_candles,
    compute_zscore,
    compute_rolling_correlation,
    compute_hedge_ratio,
    compute_pair_spread,
    compute_spread_zscore,
    run_adf_test,
)

# ---------------- Helpers ----------------
def normalize_ohlc_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize OHLC column names to:
    open, high, low, close, volume
    Accepts common variants: Open/High/Low/Close/Volume and price/qty.
    """
    df = df.copy()
    column_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "price": "close",
        "qty": "volume",
    }
    df.rename(columns=column_map, inplace=True)
    return df


def ensure_required_candle_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure required candle columns exist. If volume missing, fill with 0.
    """
    df = normalize_ohlc_columns(df)

    if "close" not in df.columns:
        raise ValueError("OHLC data must contain a 'close' column (or 'Close'/'price').")

    # For uploaded OHLC, volume might be missing; allow charts by filling.
    if "volume" not in df.columns:
        df["volume"] = 0.0

    # If open/high/low missing, approximate from close (still allows charts)
    for c in ["open", "high", "low"]:
        if c not in df.columns:
            df[c] = df["close"]

    return df


# ---------------- Page ----------------
st.set_page_config(page_title="Quant Dashboard", layout="wide")
st.title("📊 Quant Developer Dashboard")

# ---------------- DB init ----------------
db = get_db()
init_db(db)

# ---------------- Auto ingestion (BTC + ETH) ----------------
@st.cache_resource
def start_ingestion():
    def run():
        async def main():
            await asyncio.gather(
                listen_to_binance("btcusdt"),
                listen_to_binance("ethusdt"),
            )
        asyncio.run(main())

    t = threading.Thread(target=run, daemon=True)
    t.start()

start_ingestion()

# ---------------- Controls ----------------
st.subheader("📂 Optional OHLC Upload (CSV)")
uploaded_file = st.file_uploader("Upload OHLC CSV (optional)", type=["csv"])

col1, col2, col3 = st.columns(3)

with col1:
    symbol = st.selectbox("Select Symbol (single-asset analytics)", ["btcusdt", "ethusdt"])

with col2:
    timeframe_label = st.selectbox("Select Timeframe", ["1 Second", "1 Minute", "5 Minutes"])

with col3:
    regression_type = st.selectbox("Regression Type (pair analytics)", ["OLS"])  # keep OLS stable here

timeframe_map = {
    "1 Second": "1s",
    "1 Minute": "1min",
    "5 Minutes": "5min",
}
timeframe = timeframe_map[timeframe_label]

rolling_window = st.slider(
    "Rolling Window (number of candles)",
    min_value=10,
    max_value=300,
    value=60,
    step=5,
)

st.subheader("🚨 Z-Score Alert Settings")
alert_threshold = st.slider(
    "Alert when |Z-score| exceeds",
    min_value=0.5,
    max_value=5.0,
    value=2.0,
    step=0.1,
)

# ---------------- Load & build candles (primary) ----------------
candles = None

if uploaded_file is not None:
    # Upload mode
    try:
        df_up = pd.read_csv(uploaded_file)
        # require a timestamp column
        # supported names: ts / timestamp / time
        ts_col = None
        for c in ["ts", "timestamp", "time", "datetime"]:
            if c in df_up.columns:
                ts_col = c
                break
        if ts_col is None:
            st.error("Uploaded CSV must contain a timestamp column: ts OR timestamp OR time OR datetime.")
            st.stop()

        df_up[ts_col] = pd.to_datetime(df_up[ts_col])
        df_up = df_up.set_index(ts_col).sort_index()

        candles = ensure_required_candle_columns(df_up)

        st.info("Using uploaded OHLC data (live ingestion still runs in background).")
    except Exception as e:
        st.error(f"Failed to read uploaded OHLC CSV: {e}")
        st.stop()
else:
    # Live DB mode
    df_ticks = load_ticks(symbol)
    if df_ticks.empty:
        st.warning("No data found yet. Live ingestion is running… wait ~5–10 seconds and rerun.")
        st.stop()

    candles = resample_candles(df_ticks, timeframe)
    candles = ensure_required_candle_columns(candles)

# Guard
if candles is None or candles.empty:
    st.warning("Not enough data to build candles yet.")
    st.stop()

# Single-asset Z-score
candles = compute_zscore(candles, window=rolling_window)

# ---------------- Pair data (always from DB) ----------------
df_ticks_eth = load_ticks("ethusdt")
eth_available = not df_ticks_eth.empty

pair_ready = False
candles_eth = None
corr_df = None
beta = None
spread_df = None

if eth_available:
    candles_eth = resample_candles(df_ticks_eth, timeframe)
    candles_eth = ensure_required_candle_columns(candles_eth)

    # Need enough points for rolling computations
    if len(candles_eth) >= rolling_window and len(candles) >= rolling_window:
        pair_ready = True
    else:
        st.warning("ETH data exists but not enough candles for pair analytics yet. Keep running for a bit.")
else:
    st.warning("ETH data not available yet. Pair analytics will appear once data arrives.")

# ---------------- Pair analytics (only if ready) ----------------
if pair_ready:
    corr_df = compute_rolling_correlation(candles, candles_eth, window=rolling_window)

    # Hedge ratio
    # (regression_type kept as OLS for stability; can be expanded)
    beta = compute_hedge_ratio(candles["close"], candles_eth["close"])

    spread_df = compute_pair_spread(candles, candles_eth, beta)
    spread_df = compute_spread_zscore(spread_df, window=rolling_window)

# ---------------- Charts: Single asset ----------------
st.subheader(f"Price Candles — {symbol.upper()} ({timeframe})")
fig = go.Figure()
fig.add_trace(
    go.Candlestick(
        x=candles.index,
        open=candles["open"],
        high=candles["high"],
        low=candles["low"],
        close=candles["close"],
        name="Price",
    )
)
fig.update_layout(height=520, xaxis_title="Time", yaxis_title="Price")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Volume")
vol_fig = go.Figure()
vol_fig.add_trace(go.Bar(x=candles.index, y=candles["volume"], name="Volume"))
vol_fig.update_layout(height=260, xaxis_title="Time", yaxis_title="Volume")
st.plotly_chart(vol_fig, use_container_width=True)

st.subheader("Z-Score (Rolling)")
z_fig = go.Figure()
z_fig.add_trace(
    go.Scatter(
        x=candles.index,
        y=candles["zscore"],
        mode="lines",
        name="Z-Score",
    )
)
z_fig.add_hline(y=2, line_dash="dash")
z_fig.add_hline(y=-2, line_dash="dash")
z_fig.add_hline(y=0, line_dash="dot")
z_fig.update_layout(height=260, xaxis_title="Time", yaxis_title="Z-Score")
st.plotly_chart(z_fig, use_container_width=True)

# Alerts (single asset)
latest_z = float(candles["zscore"].iloc[-1])
if abs(latest_z) >= alert_threshold:
    st.error(f"🚨 ALERT: |Z-score| = {latest_z:.2f} exceeds threshold {alert_threshold}")
else:
    st.success(f"Z-score normal: {latest_z:.2f}")

# ---------------- Pair section (only show if ready) ----------------
st.divider()
st.subheader("Pair Analytics (BTC vs ETH)")

if not pair_ready:
    st.info("Pair analytics will appear automatically once ETH candles are available and sufficient for the rolling window.")
    st.stop()

# Hedge ratio metric
st.subheader("📐 Hedge Ratio (OLS)")
if beta is None or pd.isna(beta):
    st.metric("BTC ~ β × ETH", "Waiting…")
else:
    st.metric("BTC ~ β × ETH", f"{beta:.4f}")

# Trading signal summary (brownie points)
st.subheader("🧠 Trading Signal Summary")
latest_spread_z = float(spread_df["spread_zscore"].iloc[-1])

if latest_spread_z <= -2:
    st.success(
        f"📈 MEAN-REVERSION BUY SIGNAL\n\n"
        f"Spread Z-Score = {latest_spread_z:.2f}\n"
        f"Interpretation: Spread is significantly BELOW mean."
    )
elif latest_spread_z >= 2:
    st.error(
        f"📉 MEAN-REVERSION SELL SIGNAL\n\n"
        f"Spread Z-Score = {latest_spread_z:.2f}\n"
        f"Interpretation: Spread is significantly ABOVE mean."
    )
else:
    st.info(
        f"⚖️ NEUTRAL / NO-TRADE ZONE\n\n"
        f"Spread Z-Score = {latest_spread_z:.2f}\n"
        f"Interpretation: Spread within normal range."
    )

# Rolling correlation chart
st.subheader("Rolling Correlation (BTC vs ETH)")
corr_fig = go.Figure()
corr_fig.add_trace(go.Scatter(x=corr_df.index, y=corr_df["rolling_corr"], mode="lines", name="Rolling Corr"))
corr_fig.add_hline(y=0, line_dash="dot")
corr_fig.update_layout(height=260, xaxis_title="Time", yaxis_title="Correlation")
st.plotly_chart(corr_fig, use_container_width=True)

# Pair spread chart
st.subheader("Pair Spread (BTC − β × ETH)")
spread_fig = go.Figure()
spread_fig.add_trace(go.Scatter(x=spread_df.index, y=spread_df["spread"], mode="lines", name="Spread"))
spread_fig.update_layout(height=260, xaxis_title="Time", yaxis_title="Spread")
st.plotly_chart(spread_fig, use_container_width=True)

# Spread z-score chart
st.subheader("Pair Spread Z-Score")
pz_fig = go.Figure()
pz_fig.add_trace(go.Scatter(x=spread_df.index, y=spread_df["spread_zscore"], mode="lines", name="Spread Z"))
pz_fig.add_hline(y=2, line_dash="dash")
pz_fig.add_hline(y=-2, line_dash="dash")
pz_fig.add_hline(y=0, line_dash="dot")
pz_fig.update_layout(height=260, xaxis_title="Time", yaxis_title="Z-Score")
st.plotly_chart(pz_fig, use_container_width=True)

# ADF test trigger
st.subheader("ADF Test (Stationarity Check)")
if st.button("Run ADF test on Pair Spread"):
    adf_out = run_adf_test(spread_df["spread"])
    if "error" in adf_out:
        st.warning(adf_out["error"])
    else:
        st.json(adf_out)
        if adf_out.get("stationary_at_5pct", False):
            st.success("✅ Spread looks stationary at 5% significance (p < 0.05).")
        else:
            st.error("❌ Spread does NOT look stationary at 5% significance (p >= 0.05).")

# Market regime indicator (only if ADF run)
if "adf_out" in locals():
    st.subheader("📊 Market Regime Indicator")
    msgs = []
    if adf_out.get("stationary_at_5pct", False):
        msgs.append("✔ Spread appears stationary (mean-reverting regime).")
    else:
        msgs.append("⚠ Spread may NOT be stationary (trend/unstable regime).")

    latest_corr = float(corr_df["rolling_corr"].iloc[-1])
    if abs(latest_corr) > 0.7:
        msgs.append("✔ Strong BTC–ETH correlation (pair logic more reliable).")
    else:
        msgs.append("⚠ Weak correlation (pair logic less reliable).")

    for m in msgs:
        st.write(m)
