from datetime import datetime

import streamlit as st


def init_state():
    defaults = {
        "active_tab": "Market Overview",
        "overview_view": "Table",
        "selected_period": "1D",
        "heatmap_level": "INDEX",
        "selected_index": None,
        "expanded_indices": set(),
        "last_refresh_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
