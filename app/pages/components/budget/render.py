import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from millify import millify
from icecream import ic
from sqlalchemy.engine.base import Engine

from pages.components.budget.utils import (
    fetch_transaction_data,
    fetch_accounts,
    add_records,
    generate_hash,
)

from pages.components.budget.exceptions import MissingData


def render_overview(
    filtered_data,
    AMOUNT_FIELD,
    NEG_COLOR="#8B0000",
    POS_COLOR="#006400",
):
    COL_ORDER = [POS_COLOR, NEG_COLOR]
    filtered_data.reset_index(inplace=True)
    print(filtered_data)
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


def render_metric(
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


def render_transaction_upload(
    expected_columns_on_import: list[str],
    schema: str,
    sql_engine,
):
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        data.columns = [column.lower() for column in data.columns]
        missing_cols = [
            col for col in expected_columns_on_import if col not in data.columns
        ]
        if missing_cols:
            raise Exception(
                f"Missing columns in the uploaded file: {', '.join(missing_cols)}"
            )

        data.loc[:, "id"] = [str(x) for x in generate_hash(data)]
        new_record_ids = add_records(
            data,
            schema=schema,
            sql_engine=sql_engine,
        )
        st.toast(f"Added {len(new_record_ids)} records")


def render_account_annotation(
    schema: str,
    sql_engine,
    account_options: list[str],
):
    try:
        data = fetch_accounts(schema, sql_engine)
    except MissingData as e:
        st.toast(e)

    edited_accounts = st.data_editor(
        data,
        column_config={
            "type": st.column_config.SelectboxColumn(
                "Type",
                options=account_options,
                width="medium",
            )
        },
        disabled=("id", "name", "created_date", "edited_date"),
        hide_index=True,
    )
    return edited_accounts


def render_dropdown_menu(
    unique_accounts: list[str],
    unique_categories: list[str],
    unique_months: list[str],
    unique_years: list[str],
    ALL_VAR: str = "All",
):
    # Create dropdowns for "Account", "Category", "Month", "Year", and "Week Number"
    # account = st.selectbox("Select Account", [ALL_VAR] + unique_accounts)
    account = st.multiselect(
        "Select Accounts", [ALL_VAR] + unique_accounts, default=ALL_VAR
    )
    col1, col2, col3 = st.columns((4, 4, 4))
    category = col1.selectbox(
        "Select Category",
        [ALL_VAR] + unique_categories,
    )
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
    return account, category, month, year


def render_budget_metrics(
    budget_df: pd.DataFrame,
    month: int,
    year: int,
    ALL_VAR: str,
    AMOUNT_FIELD: str,
    unique_categories: list[str],
    schema: str,
    sql_engine: Engine,
):
    st.write(f"Showing Category Budgets for Month {month} Year {year}")
    st.caption("On This Tab Positive Means Outflow of Cash")
    monthly_budget = st.checkbox("Use Monthly Budget", value=True)

    category_cols = st.columns((4, 4, 4))
    increment = 0
    for category in unique_categories:
        try:
            col_index = increment % 3
            filtered_actual_data = fetch_transaction_data(
                accounts=[ALL_VAR],
                category=category,
                month=month,
                year=year,
                schema=schema,
                sql_engine=sql_engine,
            )
            ic(filtered_actual_data)
            render_metric(
                category_cols[col_index],
                filtered_actual_data,
                budget_df,
                category,
                AMOUNT_FIELD,
                monthly=monthly_budget,
            )
            increment += 1
        except MissingData as e:
            pass


def render_statistics_tab(
    df: pd.DataFrame,
    budget_df: pd.DataFrame,
    AMOUNT_FIELD: str,
    unique_categories: list[str],
):
    st.write("Average Monthly Statistics")
    st.caption("This tab ignores the category and month above. Uses Year and Account.")
    st.caption("On This Tab Positive Means Outflow of Cash")

    statistic = st.selectbox("Select Statistic", options=["Average", "Median", "Count"])
    # ic(df)
    monthly_totals = df.groupby(["Category", "Month"])[AMOUNT_FIELD].sum().reset_index()
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
            monthly_totals.groupby("category")[AMOUNT_FIELD]
            .apply(lambda x: len(x) * -1)
            .reset_index()
        )
    ic(monthly_totals)
    ic(monthly_stat)
    category_cols = st.columns((4, 4, 4))
    for index, category in enumerate(unique_categories):
        col_index = index % 3
        filtered_monthly_averages = monthly_stat.loc[
            monthly_stat.loc[:, "Category"] == category, :
        ]
        render_metric(
            category_cols[col_index],
            filtered_monthly_averages,
            budget_df,
            category,
            AMOUNT_FIELD,
            monthly=True,
        )
