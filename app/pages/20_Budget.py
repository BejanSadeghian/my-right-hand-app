import streamlit as st
import pandas as pd
import numpy as np
import os
import dotenv
import matplotlib.pyplot as plt
from millify import millify

# from dateutil import parser

dotenv.load_dotenv()


def init():
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        data.to_csv(
            os.getenv("BUDEGET_LOCAL_STORE"),
            index=False,
            mode="a",
            header=False,
        )

        # Remove duplicates
        df = pd.read_csv(os.getenv("BUDEGET_LOCAL_STORE"))
        df.drop_duplicates(inplace=True)
        df.to_csv(os.getenv("BUDEGET_LOCAL_STORE"), index=False)


def get_filtered_data(df, account, category, month, year, ALL_VAR):
    return df[
        ((df["Account"] == account) | (account == ALL_VAR))
        & ((df["Category"] == category) | (category == ALL_VAR))
        & ((df["Month"] == month) | (month == ALL_VAR))
        & ((df["Year"] == year) | (year == ALL_VAR))
    ]


def main(df, budget_df, ALL_VAR="All", AMOUNT_FIELD="Amount"):
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
    account = st.selectbox("Select Account", [ALL_VAR] + unique_accounts)
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

    tab_set = ["Overview", "Budget Metrics", "Transactions"]
    tabs = st.tabs(tab_set)
    # Create a bar chart to show the "Amount" data
    with tabs[0]:
        mask = filtered_data[AMOUNT_FIELD] <= 0
        outflow_data = filtered_data.loc[mask, :]
        inflow_data = filtered_data.loc[~mask, :]

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
        overview_tabs[0].bar_chart(x="Date", y=AMOUNT_FIELD, data=filtered_data)
        overview_tabs[1].bar_chart(x="Date", y=AMOUNT_FIELD, data=outflow_data)
        overview_tabs[2].bar_chart(x="Date", y=AMOUNT_FIELD, data=inflow_data)

    with tabs[1]:
        st.write(
            f"Showing Category Budgets for {month} {year} (positive means outflow)"
        )
        category_cols = st.columns((4, 4, 4))
        for index, category in enumerate(unique_categories):
            col_index = index % 3
            filtered_actual_data = get_filtered_data(
                df,
                ALL_VAR,
                category,
                month,
                year,
                ALL_VAR,
            )
            actual_value = np.nansum(filtered_actual_data[AMOUNT_FIELD]) * -1

            filtered_budget_data = budget_df[budget_df["Category"] == category]
            budget_value = np.nansum(filtered_budget_data["Monthly"])

            delta = (
                millify(100 * (actual_value - budget_value) / budget_value, precision=2)
                if budget_value != 0
                else None
            )
            delta = f"{delta}%" if delta else None

            category_cols[col_index].metric(
                category,
                millify(actual_value, precision=2),
                delta=delta,
                delta_color="inverse",
                help=f"Budget: {budget_value}, Actual: {actual_value}",
            )
    with tabs[2]:
        st.dataframe(filtered_data, hide_index=True)


# def budget(storage_file, budget_file):


if __name__ == "__main__":
    init()
    spend_df = pd.read_csv(os.getenv("SPEND_LOCAL_STORE"))
    budget_df = pd.read_csv(os.getenv("BUDGET_LOCAL_STORE"))
    main(spend_df, budget_df)
