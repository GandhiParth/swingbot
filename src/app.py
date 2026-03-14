import streamlit as st

from market_dashboard.modules.breadth import render as render_breadth
from market_dashboard.modules.overview import render as render_overview
from market_dashboard.services.data_loader import (
    available_dates,
    load_mkt_breadth_data,
    load_mkt_db_data,
)

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="SwingBot Market Dashboard", layout="wide")

st.title("SwingBot Market Dashboard")


# ------------------------------------------------
# DATE SELECTOR
# ------------------------------------------------

dates = available_dates()

selected_date = st.sidebar.selectbox("Select Date", dates)

# ------------------------------------------------
# LOAD DATA
# ------------------------------------------------

indices_df, stocks_df = load_mkt_db_data(selected_date)
mkt_breadth_df = load_mkt_breadth_data(selected_date)

st.caption(f"Market Data: {selected_date}")

# ------------------------------------------------
# PAGES
# ------------------------------------------------

tabs = st.tabs(["Market Overview", "Market Breadth"])

with tabs[0]:
    render_overview(stocks_df=stocks_df, indices_df=indices_df)

with tabs[1]:
    render_breadth(breadth_df=mkt_breadth_df)
