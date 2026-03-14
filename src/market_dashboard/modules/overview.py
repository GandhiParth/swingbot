import plotly.express as px
import polars as pl
import streamlit as st

from utils import color_returns


# ------------------------------------------------
# SESSION STATE
# ------------------------------------------------
def init_state(indices_df: pl.DataFrame):

    if "selected_heatmap_period" not in st.session_state:
        st.session_state.selected_heatmap_period = "1D"

    if "index_types" not in st.session_state:
        st.session_state.index_types = (
            indices_df.get_column("index_type").unique().to_list()
        )

    if "selected_constituent_index" not in st.session_state:
        indices = indices_df.get_column("index_name").unique().to_list()
        st.session_state.selected_constituent_index = indices[0] if indices else None


# ======================================================
# FILTERS
# ======================================================
def render_filters(indices_df: pl.DataFrame):

    st.multiselect(
        "Index Type",
        indices_df.get_column("index_type").unique().to_list(),
        key="index_types",
        label_visibility="collapsed",
    )


# ------------------------------------------------
# TABLE VIEW
# ------------------------------------------------
def render_index_table(indices_df: pl.DataFrame):

    st.subheader("Index Returns Overview")

    indices = indices_df.lazy().filter(
        pl.col("index_type").is_in(st.session_state.index_types)
    )

    display_df = (
        indices.select(
            [
                "index_name",
                "close",
                "1D",
                "1W",
                "1M",
                "3M",
                "6M",
            ]
        )
        .rename({"index_name": "Index Name", "close": "Close"})
        .sort("1D", descending=True)
        .collect()
    )

    return_cols = ["1D", "1W", "1M", "3M", "6M"]
    round_cols = return_cols + ["Close"]

    styled_df = (
        display_df.to_pandas()
        .style.map(color_returns, subset=return_cols)
        .format({c: "{:.2f}" for c in round_cols})
    )

    st.dataframe(styled_df, use_container_width=True, hide_index=True)


def render_constituents_table(stocks_df: pl.DataFrame):

    st.markdown("---")
    st.subheader("Constituents Breakdown")

    stocks = (
        stocks_df.lazy()
        .filter(pl.col("index_type").is_in(st.session_state.index_types))
        .collect()
    )

    indices = stocks.get_column("index_name").unique().to_list()

    if not indices:
        st.info("No indices selected.")
        return

    st.selectbox(
        "Select Index",
        indices,
        key="selected_constituent_index",
        label_visibility="collapsed",
    )

    constituents = (
        stocks.lazy()
        .filter(pl.col("index_name") == st.session_state.selected_constituent_index)
        .select(
            [
                "symbol",
                "close",
                "1D",
                "1W",
                "1M",
                "3M",
                "6M",
            ]
        )
        .rename({"symbol": "Symbol", "close": "Close"})
        .sort("1D", descending=True)
        .collect()
    )

    return_cols = ["1D", "1W", "1M", "3M", "6M"]
    round_cols = return_cols + ["Close"]

    display_df = constituents.to_pandas()
    styled_df = display_df.style.map(color_returns, subset=return_cols).format(
        {c: "{:.2f}" for c in round_cols}
    )

    if not constituents.is_empty():
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("No constituents available.")


# ------------------------------------------------
# HEATMAP
# ------------------------------------------------
def render_heatmap(stocks_df: pl.DataFrame):

    st.radio(
        "Select Period",
        ["1D", "1W", "1M", "3M", "6M"],
        horizontal=True,
        key="selected_heatmap_period",
    )

    indices = (
        stocks_df.filter(pl.col("index_type").is_in(st.session_state.index_types))
        .get_column("index_name")
        .unique()
        .to_list()
    )

    cols_per_row = 2

    rows = [indices[i : i + cols_per_row] for i in range(0, len(indices), cols_per_row)]

    for row in rows:
        columns = st.columns(len(row))

        for col, index in zip(columns, row):
            with col:
                st.subheader(index)

                stocks = stocks_df.filter((pl.col("index_name") == index)).to_pandas()

                fig = px.treemap(
                    stocks,
                    path=["symbol"],
                    values="market_cap_cr",
                    color=st.session_state.selected_heatmap_period,
                    color_continuous_scale="RdYlGn",
                    color_continuous_midpoint=0,
                )

                fig.update_traces(
                    text=stocks[st.session_state.selected_heatmap_period],
                    texttemplate="%{label}<br>%{text:.2f}%",
                    textfont_size=13,
                )

                fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=350)

                st.plotly_chart(fig, use_container_width=True, key=f"heatmap_{index}")


# ------------------------------------------------
# MAIN PAGE
# ------------------------------------------------
def render(stocks_df: pl.DataFrame, indices_df: pl.DataFrame):

    init_state(indices_df=indices_df)

    render_filters(indices_df=indices_df)

    tabs = st.tabs(["Table View", "Heatmap"])

    with tabs[0]:
        render_index_table(indices_df)
        render_constituents_table(stocks_df)

    with tabs[1]:
        render_heatmap(stocks_df)
