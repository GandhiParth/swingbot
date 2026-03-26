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
        st.session_state.selected_min_rss_score = long_scanner_df.get_column(
            "RSS SCORE"
        ).min()


def render_filters_long(long_scanner_df: pl.DataFrame):

    st.multiselect(
        "SECTOR",
        long_scanner_df.get_column("SECTOR").unique().to_list(),
        key="selected_sectors_long",
    )

    cols1, cols2, cols3, cols4 = st.columns(4)

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
        )
    with cols4:
        st.multiselect(
            "PULLBACK FILTER",
            options=[True, False],
            default=[True, False],  # both selected initially
            key="selected_pullback_filter_flag",
        )


def render_long_scanner(data: pl.DataFrame):
    init_state_long(long_scanner_df=data)
    render_filters_long(long_scanner_df=data)

    inital_count = data.height

    res = (
        data.lazy()
        .filter(
            (pl.col("SECTOR").is_in(st.session_state.selected_sectors_long))
            & (pl.col("ADR PCT 20") >= st.session_state.selected_min_adr)
            & (pl.col("RSS SCORE") >= st.session_state.selected_min_rss_score)
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
        .sort(["SECTOR", "SYMBOL"], descending=[False, False])
        .collect()
    )

    final_count = res.height

    st.metric("Count", f"{final_count}/{inital_count}")

    round_cols = res.select(cs.float()).columns
    int_cols = res.select(cs.integer()).columns
    display_df = res.to_pandas()
    fmt = {c: "{:.2f}" for c in round_cols}
    fmt.update({c: "{:.0f}" for c in int_cols})
    display_df = display_df.style.format(fmt)

    st.dataframe(display_df, width="content", hide_index=True, height="content")


def render_long_analysis(data: pl.DataFrame):
    sec_ind_df = (
        data.lazy()
        .select(
            [
                "ADR PCT 20",
                "1D",
                "1W",
                "1M",
                "3M",
                "6M",
                "SECTOR",
                "INDUSTRY",
                "MARKET CAP CR",
            ]
        )
        .filter(pl.col("ADR PCT 20") >= 3.5)
        .group_by("SECTOR", "INDUSTRY")
        .agg(
            [pl.len()]
            + [
                (
                    (pl.col(col) * pl.col("MARKET CAP CR")).sum()
                    / pl.col("MARKET CAP CR").sum()
                )
                .round(2)
                .alias(f"{col} WR")
                for col in [
                    "1D",
                    "1W",
                    "1M",
                    "3M",
                    "6M",
                ]
            ]
        )
        .sort("len", descending=True)
        .rename({"len": "COUNT"})
        .collect()
    )

    sec_df = (
        data.lazy()
        .select(
            [
                "ADR PCT 20",
                "1D",
                "1W",
                "1M",
                "3M",
                "6M",
                "SECTOR",
                "MARKET CAP CR",
            ]
        )
        .filter(pl.col("ADR PCT 20") >= 3.5)
        .group_by("SECTOR")
        .agg(
            [pl.len()]
            + [
                (
                    (pl.col(col) * pl.col("MARKET CAP CR")).sum()
                    / pl.col("MARKET CAP CR").sum()
                )
                .round(2)
                .alias(f"{col} WR")
                for col in [
                    "1D",
                    "1W",
                    "1M",
                    "3M",
                    "6M",
                ]
            ]
        )
        .sort("len", descending=True)
        .rename({"len": "COUNT"})
        .collect()
    )

    cols1, cols2 = st.columns(2)

    with cols1:
        round_cols = sec_ind_df.select(cs.float()).columns
        int_cols = sec_ind_df.select(cs.integer()).columns
        display_df = sec_ind_df.to_pandas()

        display_df = sec_ind_df.to_pandas()
        fmt = {c: "{:.2f}" for c in round_cols}
        fmt.update({c: "{:.0f}" for c in int_cols})
        display_df = display_df.style.format(fmt)

        st.dataframe(display_df, width="content", hide_index=True, height="content")

    with cols2:
        round_cols = sec_df.select(cs.float()).columns
        int_cols = sec_df.select(cs.integer()).columns
        display_df = sec_df.to_pandas()

        display_df = sec_df.to_pandas()
        fmt = {c: "{:.2f}" for c in round_cols}
        fmt.update({c: "{:.0f}" for c in int_cols})
        display_df = display_df.style.format(fmt)

        st.dataframe(display_df, width="content", hide_index=True, height="content")


def render(long_scanner_df: pl.DataFrame):

    tabs = st.tabs(["Long", "Long Sector Analysis"])

    with tabs[0]:
        render_long_scanner(data=long_scanner_df)

    with tabs[1]:
        render_long_analysis(data=long_scanner_df)
