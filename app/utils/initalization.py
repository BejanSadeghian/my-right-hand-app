import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine


def init_app():
    if "initialized_app" not in st.session_state:
        st.session_state["initialized_app"] = True
        st.set_page_config(layout="wide")


def init_emails_page():
    if "emails" not in st.session_state:
        st.session_state["emails"] = []
        st.session_state["new_emails"] = []
        st.session_state["emails_needing_review"] = []
        st.session_state["editor_data"] = pd.DataFrame()
    if "sql_engine" not in st.session_state:
        st.session_state["sql_engine"] = create_engine(
            os.getenv("CONN_STR"),
            echo=True,
        )


def init_budget_page():
    pass
