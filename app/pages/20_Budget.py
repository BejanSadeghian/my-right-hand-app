import streamlit as st
import pandas as pd
import numpy as np
import os
import dotenv

import matplotlib.pyplot as plt

from millify import millify
from icecream import ic
from sqlalchemy.engine.base import Engine

from utils import init_app, init_budget_page
from pages.components.budget.utils import (
    fetch_transaction_data,
    get_filtered_data,
    generate_hash,
    generate_empty_budget,
    generate_empty_account,
    add_records,
    fetch_options,
    fetch_budget_data,
    fetch_accounts,
    reconcile_data,
    replace_data,
    fetch_all_transaction_categories,
)
from pages.components.budget.exceptions import MissingData
from pages.components.budget.render import (
    render_overview,
    render_metric,
    render_transaction_upload,
    render_budget_editor,
    render_account_annotation,
    render_dropdown_menu,
    render_budget_metrics,
    render_statistics_tab,
)

dotenv.load_dotenv()

init_app()
init_budget_page()

SCHEMA = os.getenv("DB_SCHEMA")
SQL_ENGINE = st.session_state["sql_engine"]
AMOUNT_FIELD = "Amount"
ALL_VAR = "All"
EXPECTED_COLS_IMPORT_TRANSACTIONS = [
    "date",
    "account",
    "description",
    "category",
    "tags",
    "amount",
]
ACCOUNT_TYPE_OPTIONS = [
    "Checking",
    "Savings",
    "Credit Card",
    "Investment",
    "Other",
]


if __name__ == "__main__":
    options = fetch_options(
        schema=SCHEMA,
        sql_engine=SQL_ENGINE,
    )
    accounts, category, month, year = render_dropdown_menu(
        options["accounts"],
        options["categories"],
        options["months"],
        options["years"],
    )

    ic(accounts, category, month, year)

    try:
        spend_df = fetch_transaction_data(
            accounts=accounts,
            category=category,
            month=month,
            year=year,
            schema=SCHEMA,
            sql_engine=SQL_ENGINE,
        )
    except MissingData as e:
        st.toast(e)
        st.stop()

    # Handle budget data
    success_flag, new_values = reconcile_data(
        fetch_func=fetch_budget_data,
        field_name="Category",
        all_values=options["categories"],
        table="budget",
        schema=SCHEMA,
        sql_engine=SQL_ENGINE,
        generator_func=generate_empty_budget,
    )
    if success_flag and new_values:
        st.toast(
            (f"Added {len(new_values)} categories to budget: {', '.join(new_values)}"),
            icon="✅",
        )
    elif not success_flag:
        st.toast("Issue while handling new categories", icon="❗")
    budget_df = fetch_budget_data(schema=SCHEMA, sql_engine=SQL_ENGINE)

    # Handle account data
    success_flag, new_values = reconcile_data(
        fetch_func=fetch_accounts,
        field_name="name",
        all_values=options["accounts"],
        table="accounts",
        schema=SCHEMA,
        sql_engine=SQL_ENGINE,
        generator_func=generate_empty_account,
    )
    if success_flag and new_values:
        st.toast(
            (f"Added {len(new_values)} accounts: {', '.join(new_values)}"),
            icon="✅",
        )
    elif not success_flag:
        st.toast("Issue while handling new accounts", icon="❗")
    account_data = fetch_accounts(SCHEMA, SQL_ENGINE)

    tab_set = [
        "Overview",
        "Category Metrics",
        "Transactions",
        "Budget",
        "Statistics",
        "Admin",
    ]
    tabs = st.tabs(tab_set)
    with tabs[-1]:
        render_transaction_upload(
            EXPECTED_COLS_IMPORT_TRANSACTIONS,
            schema=SCHEMA,
            sql_engine=SQL_ENGINE,
        )
        render_account_annotation(
            schema=SCHEMA,
            sql_engine=SQL_ENGINE,
            account_options=ACCOUNT_TYPE_OPTIONS,
        )

    # Create a bar chart to show the "Amount" data
    with tabs[0]:
        render_overview(spend_df, AMOUNT_FIELD)

    with tabs[1]:
        render_budget_metrics(
            budget_df,
            month,
            year,
            ALL_VAR,
            AMOUNT_FIELD,
            unique_categories=options["categories"],
            schema=SCHEMA,
            sql_engine=SQL_ENGINE,
        )

    with tabs[2]:
        st.dataframe(spend_df, hide_index=True)

    with tabs[3]:
        render_budget_editor(budget_df, schema=SCHEMA, sql_engine=SQL_ENGINE)

    with tabs[4]:
        filtered_data = fetch_transaction_data(
            accounts=accounts,
            category=ALL_VAR,
            month=ALL_VAR,
            year=year,
            schema=SCHEMA,
            sql_engine=SQL_ENGINE,
        )
        render_statistics_tab(
            df=filtered_data,
            budget_df=budget_df,
            AMOUNT_FIELD=AMOUNT_FIELD,
            unique_categories=options["categories"],
        )
