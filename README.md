# Quant Developer Assignment – Real-Time Market Analytics Dashboard

## Overview
This project implements a real-time quantitative analytics system designed to ingest live market data, process it into structured time-series representations, and present actionable analytics through an interactive dashboard.

The application is built with a Python-based backend and focuses on **end-to-end system design**, covering data ingestion, storage, resampling, statistical analysis, and visualization. Emphasis has been placed on modularity, extensibility, and trader-oriented usability rather than purely academic modeling.

## Key Features

### Data Ingestion & Storage
- Real-time trade data ingestion from Binance WebSocket (Futures market)
- Persistent storage using SQLite
- Tick-level schema: timestamp, symbol, price, quantity
- Designed to run ingestion concurrently with the dashboard

### Data Processing
- Tick-to-OHLC resampling (1s, 1m, 5m)
- Volume aggregation
- Graceful handling of insufficient data (progressive analytics enablement)

### Quantitative Analytics
- Returns computation
- Rolling Z-score (single asset and pair spread)
- Rolling correlation (BTC–ETH)
- OLS hedge ratio estimation
- Robust (Huber) regression option
- Pair spread construction and mean-reversion analysis
- Augmented Dickey-Fuller (ADF) stationarity test

### Trader-Oriented Enhancements
- Signal summary (Buy / Sell / Neutral) based on spread Z-score
- Market regime indicator combining stationarity and correlation context
- User-configurable rolling window and regression type
- Threshold-based alerting system

### Visualization
- Interactive candlestick charts
- Volume bars
- Z-score, spread, and correlation plots
- Zoom, pan, and hover support via Plotly
- Widget-based layout using Streamlit

### Data Flexibility
- Optional OHLC CSV upload for offline analysis
- Application works fully without uploaded data (no dummy dependency)

## Architecture

# Quant Developer Assignment – Real-Time Market Analytics Dashboard

## Overview
This project implements a real-time quantitative analytics system designed to ingest live market data, process it into structured time-series representations, and present actionable analytics through an interactive dashboard.

The application is built with a Python-based backend and focuses on **end-to-end system design**, covering data ingestion, storage, resampling, statistical analysis, and visualization. Emphasis has been placed on modularity, extensibility, and trader-oriented usability rather than purely academic modeling.

---

## Key Features

### Data Ingestion & Storage
- Real-time trade data ingestion from Binance WebSocket (Futures market)
- Persistent storage using SQLite
- Tick-level schema: timestamp, symbol, price, quantity
- Designed to run ingestion concurrently with the dashboard

### Data Processing
- Tick-to-OHLC resampling (1s, 1m, 5m)
- Volume aggregation
- Graceful handling of insufficient data (progressive analytics enablement)

### Quantitative Analytics
- Returns computation
- Rolling Z-score (single asset and pair spread)
- Rolling correlation (BTC–ETH)
- OLS hedge ratio estimation
- Robust (Huber) regression option
- Pair spread construction and mean-reversion analysis
- Augmented Dickey-Fuller (ADF) stationarity test

### Trader-Oriented Enhancements
- Signal summary (Buy / Sell / Neutral) based on spread Z-score
- Market regime indicator combining stationarity and correlation context
- User-configurable rolling window and regression type
- Threshold-based alerting system

### Visualization
- Interactive candlestick charts
- Volume bars
- Z-score, spread, and correlation plots
- Zoom, pan, and hover support via Plotly
- Widget-based layout using Streamlit

### Data Flexibility
- Optional OHLC CSV upload for offline analysis
- Application works fully without uploaded data (no dummy dependency)


---

## Setup Instructions

### 1. Environment
- Python 3.9+
- Virtual environment recommended

  bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

2. Install Dependencies
pip install -r requirements.txt

Core libraries:
streamlit
pandas
numpy
plotly
sqlalchemy
websockets
statsmodels

3. Run the Application
   streamlit run app.py

  On launch:
  Live data ingestion starts automatically
  Analytics populate progressively as data becomes available

## Methodology & Design Rationale

Design Principles
Separation of concerns (ingestion, analytics, UI)
Real-time capability without blocking UI
Business-focused analytics over academic complexity
Explicit handling of data availability constraints

## Analytics Choices
Rolling statistics chosen to avoid dependence on long historical windows
Pair trading logic implemented to demonstrate cross-asset reasoning
Stationarity testing added to validate mean-reversion assumptions
Robust regression included to handle outliers in volatile markets

## UX Decisions
Signal summaries and regime indicators added to reduce cognitive load
Controls exposed for parameters a trader would realistically tune
Alerts prioritized over raw numerical output

## Limitations & Extensions
Currently demonstrated on BTC–ETH pair (easily extensible)
No execution or order management (analytics-only by design)
Can be extended with additional exchanges, assets, or persistence layers

## Conclusion
This project demonstrates the ability to translate a loosely defined business problem into a functional, extensible quantitative analytics system. The focus is on engineering clarity, analytical reasoning, and usability, aligning with real-world quant development workflows.


## AI Assistance Disclosure

AI-based tools were used during the development process as a productivity and learning aid, primarily for:

- Clarifying Python and library usage patterns
- Exploring alternative architectural approaches
- Reviewing edge cases and improving code robustness
- Improving technical documentation clarity

All system design decisions, analytical methodology selection, and feature prioritization were made independently. Code was iteratively written, tested, debugged, and refined, with AI assistance serving as a reference and acceleration tool rather than a source of direct solutions.

No proprietary material or confidential prompts were used, and all final implementations reflect understanding and reasoning.
