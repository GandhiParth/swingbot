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

    if "selected_min_rss_score" not in st.session_state:
        st.session_state.selected_min_adr = 70


def render_filters_long(long_scanner_df: pl.DataFrame):

    st.multiselect(
        "SECTOR",
        long_scanner_df.get_column("SECTOR").unique().to_list(),
        key="selected_sectors_long",
        label_visibility="collapsed",
    )

    cols1, cols2, cols3, cols4 = st.columns(3)

    with cols1:
        st.slider(
            "ADR",
            min_value=long_scanner_df.get_column("ADR PCT 20").min(),
            max_value=long_scanner_df.get_column("ADR PCT 20").max(),
            key="selected_min_adr",
        )

    with cols2:
        st.slider(
            "RSS SCORE",
            min_value=long_scanner_df.get_column("RSS SCORE").min(),
            max_value=long_scanner_df.get_column("RSS SCORE").max(),
            key="selected_min_rss_score",
        )

    with cols3:
        st.multiselect(
            "ADR FILTER",
            options=[True, False],
            default=[True, False],  # both selected initially
            key="selected_adr_filter_flag",
            label_visibility="collapsed",
        )
    with cols4:
        st.multiselect(
            "PULLBACK FILTER",
            options=[True, False],
            default=[True, False],  # both selected initially
            key="selected_pullback_filter_flag",
            label_visibility="collapsed",
        )


def render_long_scanner(data: pl.DataFrame):
    init_state_long(long_scanner_df=data)
    render_filters_long(long_scanner_df=data)

    res = (
        data.lazy()
        .filter(
            (pl.col("SECTOR").is_in(st.session_state.selected_sectors_long))
            & (pl.col("ADR PCT 20") >= st.session_state.selected_min_adr)
            & (
                pl.col("ADR FILTER FLAG").is_in(
                    st.session_state.selected_adr_filter_flag
                )
            )
            & (
                pl.col("PULLBACK FILTER FLAG").is_in(
                    st.session_state.selected_pullback_filter_flag
                )
            )
        )
        .collect()
    )

    round_cols = res.select(cs.float()).columns
    int_cols = res.select(cs.integer()).columns
    display_df = res.to_pandas()
    fmt = {c: "{:.2f}" for c in round_cols}
    fmt.update({c: "{:.0f}" for c in int_cols})
    display_df = display_df.style.format(fmt)

    st.dataframe(display_df, width="stretch", hide_index=True)


def render(long_scanner_df: pl.DataFrame):

    tabs = st.tabs(["Long"])

    with tabs[0]:
        render_long_scanner(data=long_scanner_df)
