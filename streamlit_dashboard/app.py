import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import time

# ----------------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Toronto Island Ferry — Ticket Analytics",
    page_icon="⛴️",
    layout="wide",
    initial_sidebar_state="expanded",
)

TEAL = "#0f6e6a"
CORAL = "#d9713c"
NAVY = "#1c3d5a"
GREY = "#8c8c8c"

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.7rem; }
.block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Data loading & feature engineering (cached)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading ferry ticket data…")
def load_data(path="Toronto_Island_Ferry_Tickets.csv"):
    df = pd.read_csv(path)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df.sort_values("Timestamp").reset_index(drop=True)

    df["Hour"] = df["Timestamp"].dt.hour
    df["Date"] = df["Timestamp"].dt.date
    df["DayOfWeek"] = df["Timestamp"].dt.day_name()
    df["DayNum"] = df["Timestamp"].dt.dayofweek
    df["Month"] = df["Timestamp"].dt.month
    df["Year"] = df["Timestamp"].dt.year
    df["IsWeekend"] = df["DayNum"] >= 5

    def season(m):
        if m in [12, 1, 2]:
            return "Winter"
        if m in [3, 4, 5]:
            return "Spring"
        if m in [6, 7, 8]:
            return "Summer"
        return "Fall"

    df["Season"] = df["Month"].apply(season)
    df["NetMovement"] = df["Sales Count"] - df["Redemption Count"]
    return df


df = load_data()
DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SEASON_ORDER = ["Winter", "Spring", "Summer", "Fall"]

# ----------------------------------------------------------------------------
# Sidebar — filters
# ----------------------------------------------------------------------------
st.sidebar.title("⛴️ Filters")
st.sidebar.caption("Toronto Island Park — Jack Layton Ferry Terminal")

min_date, max_date = df["Date"].min(), df["Date"].max()
date_range = st.sidebar.date_input(
    "Date range",
    value=(max_date - pd.Timedelta(days=90), max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

hour_range = st.sidebar.slider("Hour of day", 0, 23, (0, 23))

day_filter = st.sidebar.multiselect(
    "Day of week", DOW_ORDER, default=DOW_ORDER
)

season_filter = st.sidebar.multiselect(
    "Season", SEASON_ORDER, default=SEASON_ORDER
)

st.sidebar.markdown("---")
rolling_window = st.sidebar.radio(
    "Time-series smoothing", ["Raw (15-min)", "1-Hour Rolling Avg", "4-Hour Rolling Avg"], index=1
)

# Apply filters
mask = (
    (df["Date"] >= start_date)
    & (df["Date"] <= end_date)
    & (df["Hour"] >= hour_range[0])
    & (df["Hour"] <= hour_range[1])
    & (df["DayOfWeek"].isin(day_filter))
    & (df["Season"].isin(season_filter))
)
fdf = df.loc[mask].copy()

st.sidebar.markdown("---")
st.sidebar.metric("Rows in current filter", f"{len(fdf):,}")

# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.title("Real-Time Ferry Ticket Sales & Redemption Analytics")
st.caption(
    f"Toronto Island Park · Centre Island · Hanlan's Point · Ward's Island · "
    f"Data: {min_date} to {max_date}"
)

if fdf.empty:
    st.warning("No data matches the current filters. Adjust the filters in the sidebar.")
    st.stop()

# ----------------------------------------------------------------------------
# KPI cards
# ----------------------------------------------------------------------------
total_sold = int(fdf["Sales Count"].sum())
total_redeemed = int(fdf["Redemption Count"].sum())
net_movement = int(fdf["NetMovement"].sum())
avg_sold_per_interval = fdf["Sales Count"].mean()
peak_hour_row = fdf.groupby("Hour")["Sales Count"].mean().idxmax()
peak_hour_val = fdf.groupby("Hour")["Sales Count"].mean().max()

weekend_avg = fdf.loc[fdf["IsWeekend"], "Sales Count"].mean() if fdf["IsWeekend"].any() else np.nan
weekday_avg = fdf.loc[~fdf["IsWeekend"], "Sales Count"].mean() if (~fdf["IsWeekend"]).any() else np.nan
off_season_idx = None
try:
    seas_avg = fdf.groupby("Season")["Sales Count"].mean()
    if "Winter" in seas_avg and "Summer" in seas_avg and seas_avg["Summer"] > 0:
        off_season_idx = seas_avg["Winter"] / seas_avg["Summer"]
except Exception:
    pass

c1, c2, c3, c4 = st.columns(4)
c1.metric("Tickets Sold", f"{total_sold:,}")
c2.metric("Tickets Redeemed", f"{total_redeemed:,}")
c3.metric("Net Passenger Movement", f"{net_movement:+,}",
          help="Sales − Redemptions over the filtered period")
c4.metric("Avg Tickets Sold / Interval", f"{avg_sold_per_interval:.1f}")

c5, c6, c7, c8 = st.columns(4)
c5.metric("Peak Demand Hour", f"{peak_hour_row:02d}:00", f"{peak_hour_val:.1f} avg tickets")
c6.metric("Weekend Avg / Interval", f"{weekend_avg:.1f}" if pd.notna(weekend_avg) else "—")
c7.metric("Weekday Avg / Interval", f"{weekday_avg:.1f}" if pd.notna(weekday_avg) else "—")
c8.metric("Off-Season Utilization Index", f"{off_season_idx:.1%}" if off_season_idx is not None else "—",
          help="Winter avg sales ÷ Summer avg sales, within current filter")

st.markdown("---")

# ----------------------------------------------------------------------------
# Time series (with rolling average option)
# ----------------------------------------------------------------------------
st.subheader("Ticket Activity Over Time")

ts = fdf.set_index("Timestamp")[["Sales Count", "Redemption Count"]].sort_index()
if rolling_window == "1-Hour Rolling Avg":
    ts_plot = ts.rolling(4, min_periods=1).mean()
elif rolling_window == "4-Hour Rolling Avg":
    ts_plot = ts.rolling(16, min_periods=1).mean()
else:
    ts_plot = ts

fig_ts = go.Figure()
fig_ts.add_trace(go.Scatter(x=ts_plot.index, y=ts_plot["Sales Count"], name="Tickets Sold",
                             line=dict(color=TEAL, width=1.6)))
fig_ts.add_trace(go.Scatter(x=ts_plot.index, y=ts_plot["Redemption Count"], name="Tickets Redeemed",
                             line=dict(color=CORAL, width=1.6)))
fig_ts.update_layout(
    height=380, margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified", plot_bgcolor="white",
)
fig_ts.update_xaxes(showgrid=False)
fig_ts.update_yaxes(showgrid=True, gridcolor="#eee")
st.plotly_chart(fig_ts, width='stretch')

st.markdown("---")

# ----------------------------------------------------------------------------
# Two-column: hourly profile + day-of-week
# ----------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Average Demand by Hour of Day")
    hourly = fdf.groupby("Hour")[["Sales Count", "Redemption Count"]].mean().reindex(range(24), fill_value=0)
    fig_h = go.Figure()
    fig_h.add_trace(go.Scatter(x=hourly.index, y=hourly["Sales Count"], name="Sold",
                                mode="lines+markers", line=dict(color=TEAL)))
    fig_h.add_trace(go.Scatter(x=hourly.index, y=hourly["Redemption Count"], name="Redeemed",
                                mode="lines+markers", line=dict(color=CORAL)))
    fig_h.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10),
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                         plot_bgcolor="white", xaxis_title="Hour", yaxis_title="Avg per interval")
    fig_h.update_xaxes(dtick=2, showgrid=False)
    fig_h.update_yaxes(showgrid=True, gridcolor="#eee")
    st.plotly_chart(fig_h, width='stretch')

with col2:
    st.subheader("Total Activity by Day of Week")
    dow = fdf.groupby("DayOfWeek")[["Sales Count", "Redemption Count"]].sum().reindex(DOW_ORDER, fill_value=0)
    fig_d = go.Figure()
    fig_d.add_trace(go.Bar(x=dow.index, y=dow["Sales Count"], name="Sold", marker_color=TEAL))
    fig_d.add_trace(go.Bar(x=dow.index, y=dow["Redemption Count"], name="Redeemed", marker_color=CORAL))
    fig_d.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), barmode="group",
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                         plot_bgcolor="white", yaxis_title="Total tickets")
    fig_d.update_xaxes(showgrid=False)
    fig_d.update_yaxes(showgrid=True, gridcolor="#eee")
    st.plotly_chart(fig_d, width='stretch')

st.markdown("---")

# ----------------------------------------------------------------------------
# Peak vs off-peak comparison + seasonal
# ----------------------------------------------------------------------------
col3, col4 = st.columns(2)

with col3:
    st.subheader("Peak vs. Off-Peak Comparison")
    fdf["PeakWindow"] = np.where(fdf["Hour"].between(11, 14), "Peak (11:00–15:00)", "Off-Peak")
    peak_cmp = fdf.groupby("PeakWindow")[["Sales Count", "Redemption Count"]].mean()
    fig_p = go.Figure()
    fig_p.add_trace(go.Bar(x=peak_cmp.index, y=peak_cmp["Sales Count"], name="Sold", marker_color=TEAL))
    fig_p.add_trace(go.Bar(x=peak_cmp.index, y=peak_cmp["Redemption Count"], name="Redeemed", marker_color=CORAL))
    fig_p.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), barmode="group",
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                         plot_bgcolor="white", yaxis_title="Avg tickets per interval")
    fig_p.update_yaxes(showgrid=True, gridcolor="#eee")
    st.plotly_chart(fig_p, width='stretch')

with col4:
    st.subheader("Seasonal Demand Share")
    seas = fdf.groupby("Season")["Sales Count"].sum().reindex(SEASON_ORDER, fill_value=0)
    fig_s = px.pie(values=seas.values, names=seas.index, hole=0.5,
                    color=seas.index,
                    color_discrete_map={"Winter": "#6f9dc9", "Spring": "#8fbf7f",
                                         "Summer": TEAL, "Fall": CORAL})
    fig_s.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_s, width='stretch')

st.markdown("---")

# ----------------------------------------------------------------------------
# Net passenger movement
# ----------------------------------------------------------------------------
st.subheader("Net Passenger Movement (Sales − Redemptions)")
net_ts = fdf.set_index("Timestamp")["NetMovement"].sort_index()
colors = np.where(net_ts.values >= 0, TEAL, CORAL)
fig_net = go.Figure()
fig_net.add_trace(go.Bar(x=net_ts.index, y=net_ts.values, marker_color=colors, name="Net Movement"))
fig_net.add_hline(y=0, line_color="black", line_width=1)
fig_net.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white",
                       yaxis_title="Net tickets")
fig_net.update_yaxes(showgrid=True, gridcolor="#eee")
st.plotly_chart(fig_net, width='stretch')

# ----------------------------------------------------------------------------
# Anomaly / peak interval table
# ----------------------------------------------------------------------------
st.subheader("Top 10 Highest-Demand Intervals (Current Filter)")
top10 = fdf.nlargest(10, "Sales Count")[["Timestamp", "Sales Count", "Redemption Count", "NetMovement"]]
top10 = top10.rename(columns={"NetMovement": "Net Movement"})
st.dataframe(top10, width='stretch', hide_index=True)

st.caption(
    "Dashboard modules: real-time KPI cards · interactive time-series plots · date/hour/day/season filters · "
    "peak vs. off-peak comparison · anomaly table. Built for Operations, Policy Planning, and Management stakeholders."
)
