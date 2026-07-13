# Toronto Island Ferry — Ticket Analytics Dashboard

## Run locally
1. Install dependencies:
   pip install -r requirements.txt
2. Make sure `Toronto_Island_Ferry_Tickets.csv` is in the same folder as `app.py`
   (already included here).
3. Launch:
   streamlit run app.py
4. Open the URL Streamlit prints (usually http://localhost:8501).

## What's inside
- Real-time KPI cards: tickets sold, tickets redeemed, net passenger movement,
  peak demand hour, weekend/weekday averages, off-season utilization index.
- Interactive time-series plot with raw / 1-hour / 4-hour rolling average toggle.
- Filters: date range, hour-of-day range, day of week, season.
- Hourly demand profile and day-of-week totals.
- Peak (11:00-15:00) vs. off-peak comparison and seasonal demand share.
- Net passenger movement chart (Sales - Redemptions).
- Table of the 10 highest-demand intervals in the current filter.

Verified: boots cleanly with `streamlit run`, health check passes, and
renders without runtime errors (tested headlessly with an HTTP + Playwright check).
