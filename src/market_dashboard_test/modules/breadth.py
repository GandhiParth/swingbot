import plotly.express as px
import streamlit as st


def render(df, breadth_history):

    st.subheader("Market Breadth (Entire Market)")

    stocks = df[df["type"] == "STOCK"]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("% Above 20 MA", f"{stocks['above_20ma'].mean() * 100:.1f}%")
    col2.metric("% Above 50 MA", f"{stocks['above_50ma'].mean() * 100:.1f}%")
    col3.metric("% Above 200 MA", f"{stocks['above_200ma'].mean() * 100:.1f}%")

    adv = (stocks["adv_decl_flag"] == "ADV").sum()
    dec = (stocks["adv_decl_flag"] == "DEC").sum()
    ratio = adv / dec if dec != 0 else 0

    col4.metric("Advance/Decline Ratio", f"{ratio:.2f}")

    st.markdown("---")

    # Cap segmentation chart
    cap_group = (
        stocks.groupby("market_cap_type")[
            ["above_20ma", "above_50ma", "above_200ma"]
        ].mean()
        * 100
    ).reset_index()

    fig = px.bar(
        cap_group,
        x="market_cap_type",
        y=["above_20ma", "above_50ma", "above_200ma"],
        barmode="group",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    st.subheader("Breadth History (Last 10 Days)")

    st.dataframe(breadth_history, use_container_width=True)
