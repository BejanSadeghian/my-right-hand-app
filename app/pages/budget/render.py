import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from millify import millify
from icecream import ic
from sqlalchemy.engine.base import Engine
from datetime import datetime, timedelta
from pages.budget.utils import (
    fetch_transaction_data,
    fetch_accounts,
    add_records,
    generate_hash,
    replace_data,
)
from pages.budget.exceptions import MissingData


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
    uploaded_file = st.file_uploader("Upload New Transaction Data", type="csv")

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
        ic(data)
        new_record_ids = add_records(
            data,
            schema=schema,
            sql_engine=sql_engine,
        )
        st.stop()
        st.toast(f"Added {len(new_record_ids)} records")


def render_budget_editor(
    budget_df: pd.DataFrame,
    schema: str,
    sql_engine: Engine,
):
    with st.form("Edit Budget"):
        mod_budget_df = st.data_editor(
            budget_df,
            disabled=("Id", "Category", "Created_date", "Edited_date"),
            hide_index=True,
        )
        save_mod_budget_button = st.form_submit_button("Save")
        if save_mod_budget_button:
            mod_budget_df.columns = [x.lower() for x in mod_budget_df.columns]
            result = replace_data(
                mod_budget_df,
                schema=schema,
                table="budget",
                sql_engine=sql_engine,
                replace_ids=mod_budget_df.loc[:, "id"].values,
            )
            if result:
                st.toast("Successfully updated budget")


def render_account_annotation(
    schema: str,
    sql_engine,
    account_options: list[str],
):
    try:
        data = fetch_accounts(schema, sql_engine)
    except MissingData as e:
        st.toast(e)
    with st.form("edit_accounts"):
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
        save_button = st.form_submit_button("Save")
        if save_button:
            success = replace_data(
                edited_accounts,
                schema=schema,
                table="accounts",
                sql_engine=sql_engine,
                replace_ids=edited_accounts["id"].to_list(),
            )
            if success:
                st.toast("Accounts Successfully Updated", icon="✅")
            else:
                st.toast("Accounts Not Updated", icon="❗")


def render_dropdown_menu(
    unique_accounts: list[str],
    unique_categories: list[str],
    unique_months: list[str],
    unique_years: list[str],
    ALL_VAR: str = "All",
):
    # Create dropdowns for "Account", "Category", "Month", "Year", and "Week Number"
    # account = st.selectbox("Select Account", [ALL_VAR] + unique_accounts)
    col1_1, col1_2 = st.columns((6, 6))
    col2_1, col2_2, col2_3, col2_4 = st.columns((3, 3, 4, 2))
    col3_1, col3_2 = st.columns((6, 6))
    filter_internal = col2_3.checkbox("Filter Inter-Account Transactions", value=True)
    use_date_range = col2_4.checkbox("Use Date Range", value=True)
    account = col1_1.multiselect(
        "Select Accounts", [ALL_VAR] + unique_accounts, default=ALL_VAR
    )
    category = col1_2.selectbox(
        "Select Category",
        [ALL_VAR] + unique_categories,
    )
    default_end = datetime.today()
    default_start = default_end.replace(day=1)
    if (default_end - default_start).days < 7:
        default_start = default_end - timedelta(days=7)
    # default_start = datetime.today() - timedelta(days=30)
    if use_date_range:
        try:
            start_date, end_date = col2_1.date_input(
                "Select date range", value=(default_start, default_end)
            )
            month, year = None, None
        except:
            st.stop()
    else:
        try:
            index = unique_months.index(default_end.month) + 1  # Offset by 1 for "all"
        except:
            index = 0
        month = col2_1.selectbox("Select Month", [ALL_VAR] + unique_months, index=index)
        try:
            index = unique_years.index(default_end.year) + 1  # Offset by 1 for "all"
        except:
            index = 0
        year = col2_2.selectbox("Select Year", [ALL_VAR] + unique_years, index=index)
        start_date, end_date = None, None
    return (
        account,
        category,
        month,
        year,
        filter_internal,
        use_date_range,
        start_date,
        end_date,
        col3_2,
    )


def render_date_selection(use_date_range: bool):
    pass


def render_budget_metrics(
    budget_df: pd.DataFrame,
    spend_df: pd.DataFrame,
    # month: int,
    # year: int,
    ALL_VAR: str,
    AMOUNT_FIELD: str,
    unique_categories: list[str],
    schema: str,
    sql_engine: Engine,
):
    st.write(f"Showing Category Budgets")
    st.caption("On This Tab Positive Means Outflow of Cash")
    monthly_budget = st.checkbox("Use Monthly Budget", value=True)

    category_cols = st.columns((4, 4, 4))
    increment = 0
    for category in unique_categories:
        try:
            col_index = increment % 3
            # spend_df = fetch_transaction_data(
            #     accounts=[ALL_VAR],
            #     category=category,
            #     month=month,
            #     year=year,
            #     schema=schema,
            #     sql_engine=sql_engine,
            # )
            # filtered_actual_data = spend_df
            filtered_actual_data = spend_df[spend_df["Category"] == category]
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
