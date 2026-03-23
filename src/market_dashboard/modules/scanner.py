import polars as pl
import polars.selectors as cs
import streamlit as st


def init_state_long(long_scanner_df: pl.DataFrame):

    if "selected_sectors_long" not in st.session_state:
        st.session_state.selected_sectors_long = (
            long_scanner_df.get_column("SECTOR").unique().to_list()
        )

    if "selected_min_adr" not in st.session_state:
        st.session_state.selected_min_adr = 3.5


def render_filters_long(long_scanner_df: pl.DataFrame):

    st.multiselect(
        "SECTOR",
        long_scanner_df.get_column("SECTOR").unique().to_list(),
        key="selected_sectors_long",
        label_visibility="collapsed",
    )

    st.slider(
        "ADR",
        min_value=long_scanner_df.get_column("ADR PCT 20").min(),
        max_value=long_scanner_df.get_column("ADR PCT 20").max(),
        key="selected_min_adr",
    )


def render_long_scanner(data: pl.DataFrame):
    init_state_long(long_scanner_df=data)
    render_filters_long(long_scanner_df=data)

    res = (
        data.lazy()
        .filter(
            (pl.col("SECTOR").is_in(st.session_state.selected_sectors_long))
            & (pl.col("ADR PCT 20") >= st.session_state.selected_min_adr)
        )
        .collect()
    )

    round_cols = res.select(cs.float()).columns
    display_df = res.to_pandas()
    display_df = display_df.style.format({c: "{:.2f}" for c in round_cols})

    st.dataframe(display_df, width="stretch", hide_index=True)


def render(long_scanner_df: pl.DataFrame):

    tabs = st.tabs(["Long"])

    with tabs[0]:
        render_long_scanner(data=long_scanner_df)
