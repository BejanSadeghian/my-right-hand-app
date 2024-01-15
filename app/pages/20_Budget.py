import streamlit as st
import pandas as pd
import numpy as np
import os
import dotenv
import matplotlib.pyplot as plt
import altair as alt
from millify import millify

from app.utils import init_budget_page

# from dateutil import parser

dotenv.load_dotenv()

init_budget_page()


def display_overview(
    filtered_data,
    AMOUNT_FIELD,
    NEG_COLOR="#8B0000",
    POS_COLOR="#006400",
):
    COL_ORDER = [POS_COLOR, NEG_COLOR]
    filtered_data.reset_index(inplace=True)
    mask = filtered_data[AMOUNT_FIELD] <= 0
    outflow_data = filtered_data.loc[mask, :]
    inflow_data = filtered_data.loc[~mask, :]
    filtered_data.loc[:, "Color"] = POS_COLOR
    filtered_data.loc[mask, "Color"] = NEG_COLOR
    # print(filtered_data.loc[:, ["Description", AMOUNT_FIELD, "Color"]])

    col1, col2, col3 = st.columns((4, 4, 4))
    col1.metric(
        "Outflow",
        millify(
            sum(outflow_data[AMOUNT_FIELD]),
            precision=2,
        ),
    )
    col2.metric(
        "Inflow",
        millify(
            sum(inflow_data[AMOUNT_FIELD]),
            precision=2,
        ),
    )
    col3.metric(
        "Net Cash Flow",
        millify(
            sum(filtered_data[AMOUNT_FIELD]),
            precision=2,
        ),
    )

    st.write("Overview")
    overview_tabs = st.tabs(["Overview", "Outflow", "Inflow"])

    c = (
        alt.Chart(filtered_data)
        .mark_bar()
        .encode(
            x="Date",
            y=AMOUNT_FIELD,
            color=alt.Color("Color", legend=None, sort=COL_ORDER),
        )
        .configure_range(category=alt.RangeScheme(COL_ORDER))
    )
    overview_tabs[0].altair_chart(c, use_container_width=True)

    overview_tabs[1].bar_chart(
        x="Date", y=AMOUNT_FIELD, data=outflow_data, color=NEG_COLOR
    )
    overview_tabs[2].bar_chart(
        x="Date", y=AMOUNT_FIELD, data=inflow_data, color=POS_COLOR
    )


def display_metric(
    st_object,
    filtered_actual_data,
    budget_df,
    category,
    AMOUNT_FIELD,
    monthly=True,
) -> None:
    actual_value = np.nansum(filtered_actual_data[AMOUNT_FIELD] * -1)

    filtered_budget_data = budget_df[budget_df["Category"] == category]
    budget_metric = "Monthly" if monthly else "Yearly"
    budget_value = np.nansum(filtered_budget_data[budget_metric])

    delta = (
        millify(100 * (actual_value - budget_value) / budget_value, precision=2)
        if budget_value != 0
        else None
    )
    delta = f"{delta}%" if delta else None

    st_object.metric(
        category,
        millify(actual_value, precision=2),
        delta=delta,
        delta_color="inverse",
        help=f"Budget: {budget_value}, Actual: {actual_value}",
    )


def get_filtered_data(df, accounts, category, month, year, ALL_VAR):
    return df[
        ((ALL_VAR in accounts) | (df["Account"].apply(lambda x: x in accounts)))
        & ((df["Category"] == category) | (category == ALL_VAR))
        & ((df["Month"] == month) | (month == ALL_VAR))
        & ((df["Year"] == year) | (year == ALL_VAR))
    ]


def main(df, budget_df, ALL_VAR="All", AMOUNT_FIELD="Amount"):
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        data.to_csv(
            os.getenv("SPEND_LOCAL_STORE"),
            index=False,
            mode="a",
            header=False,
        )

        # Remove duplicates
        df = pd.read_csv(os.getenv("SPEND_LOCAL_STORE"))
        df.drop_duplicates(inplace=True)
        df.to_csv(os.getenv("SPEND_LOCAL_STORE"), index=False)

    # Add month, year, and week number columns based on the "Date"
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.month
    df["Year"] = df["Date"].dt.year
    df["Week_Number"] = df["Date"].dt.isocalendar().week

    unique_accounts = sorted(list(df["Account"].unique()))
    unique_categories = sorted(list(df["Category"].unique()))
    unique_months = sorted(list(df["Month"].unique()))
    unique_years = sorted(list(df["Year"].unique()))

    # Create dropdowns for "Account", "Category", "Month", "Year", and "Week Number"
    # account = st.selectbox("Select Account", [ALL_VAR] + unique_accounts)
    account = st.multiselect(
        "Select Accounts", [ALL_VAR] + unique_accounts, default=ALL_VAR
    )
    col1, col2, col3 = st.columns((4, 4, 4))
    category = col1.selectbox("Select Category", [ALL_VAR] + unique_categories)
    today = pd.to_datetime("today")
    try:
        index = unique_months.index(today.month) + 1  # Offset by 1 for "all"
    except:
        index = 0
    month = col2.selectbox("Select Month", [ALL_VAR] + unique_months, index=index)
    try:
        index = unique_years.index(today.year) + 1  # Offset by 1 for "all"
    except:
        index = 0
    year = col3.selectbox("Select Year", [ALL_VAR] + unique_years, index=index)

    # Filter data based on dropdown selections
    filtered_data = get_filtered_data(df, account, category, month, year, ALL_VAR)

    tab_set = ["Overview", "Category Metrics", "Transactions", "Budget", "Statistics"]
    tabs = st.tabs(tab_set)
    # Create a bar chart to show the "Amount" data
    with tabs[0]:
        display_overview(filtered_data, AMOUNT_FIELD)

    with tabs[1]:
        st.write(f"Showing Category Budgets for Month {month} Year {year}")
        st.caption("On This Tab Positive Means Outflow of Cash")
        monthly_budget = st.checkbox("Use Monthly Budget", value=True)

        category_cols = st.columns((4, 4, 4))
        for index, category in enumerate(unique_categories):
            col_index = index % 3
            filtered_actual_data = get_filtered_data(
                df,
                [ALL_VAR],
                category,
                month,
                year,
                ALL_VAR,
            )

            display_metric(
                category_cols[col_index],
                filtered_actual_data,
                budget_df,
                category,
                AMOUNT_FIELD,
                monthly=monthly_budget,
            )

    with tabs[2]:
        st.dataframe(filtered_data, hide_index=True)
    with tabs[3]:
        with st.form("Edit Budget"):
            mod_budget_df = st.data_editor(budget_df, hide_index=True)
            save_mod_budget_button = st.form_submit_button("Save")
            if save_mod_budget_button:
                mod_budget_df.to_csv(os.getenv("BUDGET_LOCAL_STORE"), index=False)

    with tabs[4]:
        st.write("Average Monthly Statistics")
        st.caption(
            "This tab ignores the category and month above. Uses Year and Account."
        )
        st.caption("On This Tab Positive Means Outflow of Cash")

        statistic = st.selectbox(
            "Select Statistic", options=["Average", "Median", "Count"]
        )
        filtered_year_data = get_filtered_data(
            df, account, ALL_VAR, ALL_VAR, year, ALL_VAR
        )
        monthly_totals = (
            filtered_year_data.groupby(["Category", "Month"])[AMOUNT_FIELD]
            .sum()
            .reset_index()
        )
        if statistic == "Average":
            monthly_stat = (
                monthly_totals.groupby("Category")[AMOUNT_FIELD]
                .apply(np.nanmean)
                .reset_index()
            )
        elif statistic == "Median":
            monthly_stat = (
                monthly_totals.groupby("Category")[AMOUNT_FIELD]
                .apply(np.nanmedian)
                .reset_index()
            )
        elif statistic == "Count":
            monthly_stat = (
                monthly_totals.groupby("Category")[AMOUNT_FIELD]
                .apply(lambda x: len(x) * -1)
                .reset_index()
            )
        print(monthly_totals)
        print(monthly_stat)
        category_cols = st.columns((4, 4, 4))
        for index, category in enumerate(unique_categories):
            col_index = index % 3
            filtered_monthly_averages = monthly_stat.loc[
                monthly_stat.loc[:, "Category"] == category, :
            ]
            display_metric(
                category_cols[col_index],
                filtered_monthly_averages,
                budget_df,
                category,
                AMOUNT_FIELD,
                monthly=monthly_budget,
            )


if __name__ == "__main__":
    init()
    spend_df = pd.read_csv(os.getenv("SPEND_LOCAL_STORE"))
    budget_df = pd.read_csv(os.getenv("BUDGET_LOCAL_STORE"))
    main(spend_df, budget_df)
