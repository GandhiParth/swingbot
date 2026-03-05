import plotly.express as px
import streamlit as st


# ======================================================
# INIT STATE
# ======================================================
def init_state(df):

    if "index_types" not in st.session_state:
        st.session_state.index_types = ["Market", "Sector"]

    if "selected_constituent_index" not in st.session_state:
        indices = df[df["type"] == "INDEX"]["name"].tolist()
        st.session_state.selected_constituent_index = indices[0] if indices else None

    if "selected_heatmap_period" not in st.session_state:
        st.session_state.selected_heatmap_period = "1D"


# ======================================================
# MAIN ENTRY
# ======================================================
def render(df):

    init_state(df)

    # 🔥 FILTERS RENDERED ONLY ONCE
    render_filters()

    tabs = st.tabs(["Market Overview", "Heatmap"])

    # --------------------------------------------------
    # TAB 1 — TABLE
    # --------------------------------------------------
    with tabs[0]:
        render_index_table(df)
        render_constituents_section(df)

    # --------------------------------------------------
    # TAB 2 — HEATMAP
    # --------------------------------------------------
    with tabs[1]:
        st.radio(
            "Select Period",
            ["1D", "1W", "1M", "3M"],
            horizontal=True,
            key="selected_heatmap_period",
            label_visibility="collapsed",
        )

        render_heatmap(df)


# ======================================================
# FILTERS
# ======================================================
def render_filters():

    st.multiselect(
        "Index Type",
        ["Market", "Sector"],
        key="index_types",
        label_visibility="collapsed",
    )


def filtered_indices(df):

    indices = df[df["type"] == "INDEX"].copy()

    if "Market" not in st.session_state.index_types:
        indices = indices[indices["index_category"] != "Market"]

    if "Sector" not in st.session_state.index_types:
        indices = indices[indices["index_category"] != "Sector"]

    return indices


# ======================================================
# TABLE VIEW
# ======================================================
def render_index_table(df):

    st.subheader("Index Returns Overview")

    indices = filtered_indices(df)

    display_df = indices[["name", "1D", "1W", "1M", "3M"]].rename(
        columns={"name": "Name"}
    )

    inject_table_css()

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_constituents_section(df):

    st.markdown("---")
    st.subheader("Constituents Breakdown")

    indices = filtered_indices(df)["name"].tolist()

    if not indices:
        st.info("No indices selected.")
        return

    st.selectbox(
        "Select Index",
        indices,
        key="selected_constituent_index",
        label_visibility="collapsed",
    )

    constituents = df[
        (df["type"] == "STOCK")
        & (df["parent_index"] == st.session_state.selected_constituent_index)
    ]

    if not constituents.empty:
        display_df = constituents[["name", "1D", "1W", "1M", "3M"]].rename(
            columns={"name": "Stock"}
        )

        inject_table_css()

        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No constituents available.")


# ======================================================
# HEATMAP (2 LEVEL)
# ======================================================
def render_heatmap(df):

    indices = filtered_indices(df)["name"].tolist()

    stocks = df[(df["type"] == "STOCK") & (df["parent_index"].isin(indices))]

    fig = px.treemap(
        stocks,
        path=["sector", "name"],  # 2 LEVEL ONLY
        values="market_cap_weight",
        color=st.session_state.selected_heatmap_period,
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
    )

    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))

    st.plotly_chart(fig, use_container_width=True)


# ======================================================
# TABLE FONT SIZE INCREASE
# ======================================================
def inject_table_css():

    st.markdown(
        """
        <style>
        .stDataFrame table {
            font-size: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
