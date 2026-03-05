import streamlit as st
from modules.breadth import render as render_breadth
from modules.overview import render as render_overview
from modules.scanner import render as render_scanner
from services.data_loader import load_market_data

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="SwingBot Market Dashboard", layout="wide")

st.title("SwingBot Market Dashboard")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
df, breadth_history = load_market_data()

# --------------------------------------------------
# TOP LEVEL TABS (NOT RADIO)
# --------------------------------------------------
tabs = st.tabs(["Market Overview", "Market Breadth", "Scanner"])

# --------------------------------------------------
# TAB 1 — MARKET OVERVIEW (DEFAULT OPEN)
# --------------------------------------------------
with tabs[0]:
    render_overview(df)

# --------------------------------------------------
# TAB 2 — MARKET BREADTH
# --------------------------------------------------
with tabs[1]:
    render_breadth(df, breadth_history)

# --------------------------------------------------
# TAB 3 — SCANNER
# --------------------------------------------------
with tabs[2]:
    render_scanner()
