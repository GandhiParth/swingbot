import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st


@st.cache_data
def load_market_data():
    np.random.seed(42)

    # -------------------------------------------------
    # Define Index Groups
    # -------------------------------------------------

    market_indices = ["NIFTY 50", "NIFTY BANK", "NIFTY MIDCAP 100"]
    sector_indices = ["NIFTY IT", "NIFTY AUTO", "NIFTY PHARMA"]

    all_indices = market_indices + sector_indices

    sectors = ["IT", "BANK", "AUTO", "PHARMA", "FINANCE"]

    data = []

    # -------------------------------------------------
    # Create Index Rows
    # -------------------------------------------------
    for idx in all_indices:
        if idx in market_indices:
            index_category = "Market"
        else:
            index_category = "Sector"

        data.append(
            {
                "symbol": idx,
                "name": idx,
                "type": "INDEX",
                "index_category": index_category,  # 🔥 NEW COLUMN
                "parent_index": None,
                "sector": "INDEX",
                "market_cap_type": "Index",
                "market_cap_weight": np.random.uniform(500, 1000),
                "1D": np.random.uniform(-3, 3),
                "1W": np.random.uniform(-5, 5),
                "1M": np.random.uniform(-10, 10),
                "3M": np.random.uniform(-15, 15),
            }
        )

        # -------------------------------------------------
        # Create Stocks Under Each Index
        # -------------------------------------------------
        for i in range(20):
            sector_name = random.choice(sectors)

            data.append(
                {
                    "symbol": f"{idx[:4]}_{i}",
                    "name": f"{idx[:4]} Stock {i + 1}",
                    "type": "STOCK",
                    "index_category": None,  # only indices have category
                    "parent_index": idx,
                    "sector": sector_name,
                    "market_cap_type": random.choice(
                        ["Large Cap", "Mid Cap", "Small Cap"]
                    ),
                    "market_cap_weight": np.random.uniform(10, 200),
                    "1D": np.random.uniform(-3, 3),
                    "1W": np.random.uniform(-5, 5),
                    "1M": np.random.uniform(-10, 10),
                    "3M": np.random.uniform(-15, 15),
                }
            )

    df = pd.DataFrame(data)

    # -------------------------------------------------
    # Breadth Fields
    # -------------------------------------------------
    df["above_20ma"] = np.random.choice([True, False], len(df))
    df["above_50ma"] = np.random.choice([True, False], len(df))
    df["above_200ma"] = np.random.choice([True, False], len(df))
    df["adv_decl_flag"] = np.where(df["1D"] > 0, "ADV", "DEC")

    # -------------------------------------------------
    # Breadth History
    # -------------------------------------------------
    dates = [datetime.now() - timedelta(days=i) for i in range(10)]
    dates.reverse()

    breadth_history = pd.DataFrame(
        {
            "date": dates,
            "pct_above_20ma": np.random.uniform(30, 80, 10),
            "pct_above_50ma": np.random.uniform(25, 75, 10),
            "pct_above_200ma": np.random.uniform(20, 70, 10),
            "advance_decline_ratio": np.random.uniform(0.5, 2.0, 10),
        }
    )

    st.session_state.last_refresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return df, breadth_history
