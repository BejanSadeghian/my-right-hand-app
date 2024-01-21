import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from my_right_hand.models import EmailMessage, EmailReview
from icecream import ic


def render_email_fetch(default_window: int) -> st.button:
    with st.form("request_emails"):
        col1, col2, _ = st.columns((3, 3, 6))
        start_date = col1.date_input(
            "Start Date",
            datetime.now() - timedelta(days=default_window),
        )
        end_date = col2.date_input("End Date", datetime.now())
        submit_button = col2.form_submit_button("Fetch Emails")
    return submit_button, start_date, end_date


def render_email_processing(
    emails: list[EmailMessage],
    new_emails: list[EmailMessage],
    review_email_ids: list[str],
):
    ic(review_email_ids)
    with st.form("process_email"):
        col1, col2, col3 = st.columns((2, 2, 8))
        col1.metric("Emails Retrieved", value=len(emails))
        col2.metric("New Emails", value=len(new_emails))
        col2.metric(
            "Unreviewed Emails",
            value=len(review_email_ids),
        )
        with col3.expander("Retrieved Emails"):
            st.write(pd.DataFrame([x.model_dump() for x in emails]))
        process_submit = col1.form_submit_button("Process Emails")
    return process_submit


def render_email_details_options(
    default_window: int,
    boolean_fields: list[str],
    non_boolean_fields: list[str],
):
    col1, col2 = st.columns((6, 6))

    selected_field = col1.selectbox(
        "Select a boolean field to filter",
        options=["all"] + boolean_fields,
    )
    date = pd.to_datetime(
        col1.date_input(
            "Filter By Date",
            value=datetime.now() - timedelta(days=default_window),
        ),
        utc=True,
    )

    display_fields = col2.multiselect(
        "Select Fields to Show",
        default=["sender", "subject", "date"],
        options=non_boolean_fields,
    )

    only_unacknowledged = col2.checkbox("Exclude Acknowledged", value=False)
    return selected_field, date, display_fields, only_unacknowledged


def render_email_details_table(display_data: pd.DataFrame, ack_only_field_name: str):
    with st.form("acknowledge"):
        form_button = st.form_submit_button("Acknowledge Email")

        # st.session_state["filtered_data"] = filtered_data[mask]

        editor_data = st.data_editor(
            display_data,
            disabled=[
                x for x in display_data.columns.values if x != ack_only_field_name
            ],
            hide_index=True,
        )
    return form_button, editor_data
