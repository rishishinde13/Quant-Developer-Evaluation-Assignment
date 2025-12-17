from backend.analytics import (
    load_ticks,
    resample_candles,
    compute_returns,
    compute_spread,
    compute_zscore,
)

symbol = "btcusdt"

df_ticks = load_ticks(symbol)
candles = resample_candles(df_ticks, "1s")

candles = compute_returns(candles)
candles = compute_spread(candles, window=20)
candles = compute_zscore(candles, window=20)

print(candles.tail(10))
