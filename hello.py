import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Business Performance & Predictive Analytics Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- Helper functions ---

def create_monthly_revenue(year=2026):
    months = pd.date_range(start=f"{year}-01-01", periods=12, freq="MS").strftime("%b %Y")
    base = np.array([120, 135, 150, 140, 165, 175, 190, 205, 220, 215, 230, 245], dtype=float)
    noise = np.random.normal(0, 8, size=12)
    values = np.round(base + noise, 2)
    return pd.DataFrame({"Month": months, "Revenue": values}).set_index("Month")


def create_region_performance():
    regions = ["North", "South", "East", "West"]
    revenue = [560_000, 430_000, 490_000, 380_000]
    growth = [6.8, 5.4, 7.2, 4.9]
    return pd.DataFrame({"Region": regions, "Revenue": revenue, "Growth %": growth})


def create_transaction_logs(rows=60):
    rng = np.random.default_rng(42)
    dates = pd.date_range(start="2026-01-01", end="2026-05-31", periods=rows).to_pydatetime().tolist()
    transaction_ids = [f"TXN-{1000 + i}" for i in range(rows)]
    regions = rng.choice(["North", "South", "East", "West"], size=rows)
    amounts = np.round(rng.uniform(150, 3200, size=rows), 2)
    statuses = rng.choice(["Completed", "Pending", "Refunded"], size=rows, p=[0.8, 0.15, 0.05])
    customers = [f"Customer {chr(65 + rng.integers(0, 20))}" for _ in range(rows)]

    return pd.DataFrame(
        {
            "Date": dates,
            "Transaction ID": transaction_ids,
            "Region": regions,
            "Customer": customers,
            "Amount": amounts,
            "Status": statuses,
        }
    )


def get_forecast(start_value, growth_pct, budget, months=6):
    forecast = []
    current = start_value
    for month in range(1, months + 1):
        current = current * (1 + growth_pct / 100) + budget / 12
        forecast.append(round(current, 2))
    future_months = pd.date_range(start="2026-06-01", periods=months, freq="MS").strftime("%b %Y")
    return pd.DataFrame({"Month": future_months, "Forecasted Revenue": forecast}).set_index("Month")


# --- Sidebar ---
with st.sidebar:
    st.markdown("# 📈 Business Performance Dashboard")
    st.markdown("---")

    view = st.radio(
        "Select view",
        ["Overview", "Deep-Dive Analytics", "Future Forecasting"],
        index=0,
    )

    st.markdown("### Filters")
    start_date, end_date = st.date_input(
        "Date range",
        value=[datetime(2026, 1, 1), datetime(2026, 5, 31)],
        min_value=datetime(2026, 1, 1),
        max_value=datetime(2026, 12, 31),
    )
    selected_region = st.selectbox("Region", ["All", "North", "South", "East", "West"])
    st.markdown("---")
    st.write("Built with Streamlit — clean analytics for business leaders.")


# --- Main content ---
st.title("Business Performance & Predictive Analytics")
st.markdown(
    "Use the sidebar to switch between views, explore performance metrics, and forecast revenue with custom inputs."
)

revenue_trend = create_monthly_revenue()
region_perf = create_region_performance()
transactions = create_transaction_logs()

if selected_region != "All":
    transactions = transactions[transactions["Region"] == selected_region]
    region_perf = region_perf[region_perf["Region"] == selected_region]

# View 1: Overview
if view == "Overview":
    st.header("Overview")

    total_revenue = revenue_trend["Revenue"].sum()
    active_users = 12_450 + np.random.randint(-200, 200)
    conversion_rate = 4.8 + np.random.normal(0, 0.2)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"${total_revenue:,.0f}", delta="+8.4%")
    col2.metric("Active Users", f"{active_users:,}", delta="+3.2%")
    col3.metric("Conversion Rate", f"{conversion_rate:.1f}%", delta="-0.1%")

    with st.container():
        st.subheader("Monthly Revenue Trend — 2026")
        st.line_chart(revenue_trend)

    with st.container():
        st.markdown("#### Snapshot")
        stats_col1, stats_col2, stats_col3 = st.columns(3)
        stats_col1.metric("Best Month", revenue_trend["Revenue"].idxmax())
        stats_col2.metric("Worst Month", revenue_trend["Revenue"].idxmin())
        stats_col3.metric("Average Monthly Revenue", f"${revenue_trend["Revenue"].mean():,.0f}")

# View 2: Deep-Dive Analytics
elif view == "Deep-Dive Analytics":
    st.header("Deep-Dive Analytics")
    st.markdown(
        "Explore regional performance and inspect transaction-level activity."
    )

    with st.container():
        st.subheader("Performance by Region")
        st.bar_chart(region_perf.set_index("Region")[["Revenue"]])

    with st.container():
        st.subheader("Transaction Log")
        search = st.text_input("Search transactions", placeholder="Search by customer, region, status...")

        if search:
            search_lower = search.lower()
            transactions = transactions[
                transactions.apply(
                    lambda row: search_lower in str(row["Transaction ID"]).lower()
                    or search_lower in str(row["Customer"]).lower()
                    or search_lower in str(row["Region"]).lower()
                    or search_lower in str(row["Status"]).lower(),
                    axis=1,
                )
            ]

        st.dataframe(transactions.reset_index(drop=True), hide_index=True)

        csv = transactions.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download transaction data as CSV",
            data=csv,
            file_name="transaction_logs.csv",
            mime="text/csv",
        )

# View 3: Future Forecasting
else:
    st.header("Future Forecasting")
    st.markdown(
        "Build a revenue projection with custom growth assumptions and budget targets."
    )

    with st.container():
        input_col1, input_col2 = st.columns(2)
        growth_rate = input_col1.number_input(
            "Expected Growth Rate (%)",
            min_value=0.0,
            max_value=25.0,
            value=6.5,
            step=0.1,
        )
        monthly_budget = input_col2.number_input(
            "Target Monthly Budget ($)",
            min_value=0,
            value=55_000,
            step=1_000,
        )

    base_revenue = revenue_trend["Revenue"].iloc[-1]
    forecast_df = get_forecast(base_revenue, growth_rate, monthly_budget, months=6)

    with st.container():
        st.subheader("Forecast Summary")
        forecast_col1, forecast_col2, forecast_col3 = st.columns(3)
        forecast_col1.metric("Current Base Revenue", f"${base_revenue:,.0f}")
        forecast_col2.metric("Growth Rate", f"{growth_rate:.1f}%")
        forecast_col3.metric("Monthly Budget", f"${monthly_budget:,.0f}")

    with st.container():
        st.line_chart(forecast_df)
        st.write(
            "This forecast shows a simple projection based on the latest revenue and your custom growth assumptions."
        )

