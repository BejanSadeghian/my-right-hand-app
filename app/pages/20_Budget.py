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
    add_records,
    fetch_options,
)
from pages.components.budget.render import (
    render_overview,
    render_metric,
    render_data_upload,
    render_dropdown_menu,
    render_budget_metrics,
    render_statistics_tab,
)

# from dateutil import parser

dotenv.load_dotenv()

init_app()
init_budget_page()

SCHEMA = os.getenv("DB_SCHEMA")
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


if __name__ == "__main__":
    options = fetch_options(schema=SCHEMA, sql_engine=st.session_state["sql_engine"])
    accounts, category, month, year = render_dropdown_menu(
        options["accounts"],
        options["categories"],
        options["months"],
        options["years"],
    )
    tab_set = [
        "Overview",
        "Category Metrics",
        "Transactions",
        "Budget",
        "Statistics",
        "Upload Data",
    ]
    tabs = st.tabs(tab_set)
    ic(accounts, category, month, year)
    spend_df = fetch_transaction_data(
        accounts=accounts,
        category=category,
        month=month,
        year=year,
        schema=SCHEMA,
        sql_engine=st.session_state["sql_engine"],
    )
    ic(spend_df)

    budget_df = pd.read_csv(os.getenv("BUDGET_LOCAL_STORE"))
    # ic(budget_df.columns.values)

    with tabs[-1]:
        render_data_upload()

    # Create a bar chart to show the "Amount" data
    with tabs[0]:
        render_overview(spend_df, AMOUNT_FIELD)

    with tabs[1]:
        render_budget_metrics(
            budget_df,
            category,
            month,
            year,
            ALL_VAR,
            AMOUNT_FIELD,
            unique_categories=options["categories"],
            schema=SCHEMA,
            sql_engine=st.session_state["sql_engine"],
        )

    with tabs[2]:
        st.dataframe(spend_df, hide_index=True)

    with tabs[3]:
        with st.form("Edit Budget"):
            mod_budget_df = st.data_editor(budget_df, hide_index=True)
            save_mod_budget_button = st.form_submit_button("Save")
            if save_mod_budget_button:
                mod_budget_df.to_csv(os.getenv("BUDGET_LOCAL_STORE"), index=False)

    with tabs[4]:
        filtered_data = fetch_transaction_data(
            accounts=accounts,
            category=ALL_VAR,
            month=ALL_VAR,
            year=year,
            schema=SCHEMA,
            sql_engine=st.session_state["sql_engine"],
        )
        render_statistics_tab(
            df=filtered_data,
            budget_df=budget_df,
            AMOUNT_FIELD=AMOUNT_FIELD,
            unique_categories=options["categories"],
        )
