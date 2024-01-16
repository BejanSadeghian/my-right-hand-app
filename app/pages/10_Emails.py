import os
import dotenv
import streamlit as st

from icecream import ic
from openai import OpenAI

from utils import init_app, init_emails_page
from my_right_hand.agent import OpenAIAgent

from pages.components.email_funcs import (
    render_email_fetch,
    fetch_emails,
    save_new_emails,
    render_email_processing,
    fetch_unreviewed_ids,
    process_emails,
    fetch_form_data,
    render_email_details_options,
    fetch_display_data,
    render_email_details_table,
    save_acknowledgements,
)


dotenv.load_dotenv()
init_app()
init_emails_page()

DEFAULT_WINDOW = 2
ALL_INDICATORS = ["all"]
ACKNOWLEDGE_FIELD = "acknowledge"
SCHEMA = os.getenv("DB_SCHEMA")

client = OpenAI(
    api_key=os.getenv("OAI_API_KEY"),
)
agent = OpenAIAgent(
    client=client,
    model=os.getenv("OAI_CHAT_MODEL"),
    use_snippet=False,
)

if __name__ == "__main__":
    tab_names = ["Email Details", "Retrieve New Emails"]
    tabs = st.tabs(tab_names)
    with tabs[-1]:
        fetch_email_button, start_date, end_date = render_email_fetch(DEFAULT_WINDOW)
        review_email_ids = fetch_unreviewed_ids(
            schema=SCHEMA,
            sql_engine=st.session_state["sql_engine"],
        )
        if fetch_email_button:
            st.session_state["emails"] = fetch_emails(start_date, end_date)
            st.session_state["new_emails"] = save_new_emails(
                emails=st.session_state["emails"],
                schema=SCHEMA,
                sql_engine=st.session_state["sql_engine"],
            )
            # st.rerun()

        if st.session_state["emails"]:
            process_button = render_email_processing(
                emails=st.session_state["emails"],
                new_emails=st.session_state["new_emails"],
                review_email_ids=review_email_ids,
            )
            emails_to_process = [
                email
                for email in st.session_state["emails"]
                if email.id in review_email_ids
            ]
        if "emails_to_process" in locals() and process_button:
            process_emails(
                emails=emails_to_process,
                agent=agent,
                schema=SCHEMA,
                sql_engine=st.session_state["sql_engine"],
            )

    with tabs[0]:
        boolean_fields, non_boolean_fields = fetch_form_data(
            schema=SCHEMA,
            sql_engine=st.session_state["sql_engine"],
        )
        (
            selected_field,
            date,
            display_fields,
            only_unacknowledged,
        ) = render_email_details_options(
            DEFAULT_WINDOW, boolean_fields, non_boolean_fields
        )
        if selected_field or date or display_fields or only_unacknowledged:
            ic(selected_field, date, display_fields, only_unacknowledged)
            review_filter = (
                selected_field if selected_field not in ALL_INDICATORS else None
            )
            display_data = fetch_display_data(
                review_filter=review_filter,
                boolean_fields=boolean_fields,
                date=date,
                display_fields=display_fields,
                only_unacknowledged=only_unacknowledged,
                ack_only_field_name=ACKNOWLEDGE_FIELD,
                schema=SCHEMA,
                sql_engine=st.session_state["sql_engine"],
            )
            ic(display_data)
            form_button, st.session_state["editor_data"] = render_email_details_table(
                display_data=display_data,
                ack_only_field_name=ACKNOWLEDGE_FIELD,
            )
        if not st.session_state["editor_data"].empty and form_button:
            bools = st.session_state["editor_data"].loc[:, ACKNOWLEDGE_FIELD]
            ids = list(st.session_state["editor_data"].loc[:, "id"].values)
            new_results, edited_results = save_acknowledgements(
                zip(ids, bools),
                schema=SCHEMA,
                sql_engine=st.session_state["sql_engine"],
            )
            ic(new_results)
            if len(new_results):
                st.toast(f"{len(new_results)} New Acknowledgment")
            if len(edited_results):
                st.toast(f"{len(edited_results)} Changed Acknowledgment")
