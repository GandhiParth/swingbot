import plotly.express as px
import polars as pl
import streamlit as st


def render_breadth_chart(breadth_df: pl.DataFrame):

    metric_cols = [c for c in breadth_df.columns if c != "timestamp"]

    selected_metrics = st.multiselect(
        "Select Breadth Metrics",
        metric_cols,
        default=["% ABOVE SMA 50", "% ABOVE SMA 200"],
    )

    if not selected_metrics:
        st.warning("Select at least one metric")
        return

    df = breadth_df.sort("timestamp").rename({"timestamp": "Timestamp"}).to_pandas()

    fig = px.line(
        df,
        x="Timestamp",
        y=selected_metrics,
        markers=False,
    )

    fig.update_layout(
        height=450,
        legend_title="Metrics",
        margin=dict(t=20, l=20, r=20, b=20),
    )

    st.plotly_chart(fig, width="stretch")


def render(breadth_df: pl.DataFrame, regime_df: pl.DataFrame):

    tabs = st.tabs(["BREADTH", "REGIME"])

    with tabs[0]:
        st.subheader("Market Breadth (Entire Market)")

        breadth_df = breadth_df.sort("timestamp", descending=True)
        latest_data = breadth_df.head(1)

        metric_cols = [c for c in latest_data.columns if c != "timestamp"]

        cols = st.columns(len(metric_cols))

        for col_container, col_name in zip(cols, metric_cols):
            value = latest_data[col_name].item(0)

            if col_name == "# Stocks":
                col_container.metric(col_name, f"{int(value)}")
            else:
                col_container.metric(col_name, f"{value:.2f}%")

        st.markdown("---")

        # Market Breadth Table
        st.subheader(f"Breadth History (Last {breadth_df.height} Days)")
        st.dataframe(breadth_df.head(10).to_pandas(), width="stretch", hide_index=True)

        st.markdown("---")
        # Market Breadth Graph
        render_breadth_chart(breadth_df=breadth_df)

    with tabs[1]:
        st.dataframe(
            regime_df.to_pandas(), width="stretch", hide_index=True, height="content"
        )
