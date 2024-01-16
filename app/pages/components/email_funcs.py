import os
import dotenv
import streamlit as st
import pandas as pd

from icecream import ic
from datetime import datetime, timedelta
from sqlalchemy.engine.base import Engine
from sqlalchemy import text

from utils import init_app, init_emails_page
from my_right_hand.email_client import GmailRetriever
from my_right_hand.utils import redactor
from my_right_hand.agent import OpenAIAgent
from my_right_hand.models import EmailMessage, EmailReview


def fetch_present_ids(schema: str, pk_list: list[str], sql_engine: Engine) -> list[str]:
    with sql_engine.connect() as conn:
        query = f"SELECT id FROM {schema}.emails WHERE id IN %(pk_list)s"

        matching_ids = pd.read_sql_query(
            query,
            conn,
            params={"pk_list": tuple(pk_list)},
        )
    ic(matching_ids[["id"]])
    return matching_ids["id"].values


def fetch_unreviewed_ids(schema: str, sql_engine: Engine) -> list[str]:
    with sql_engine.connect() as conn:
        query = f"""
            SELECT e.id
            FROM {schema}.emails e
            LEFT JOIN {schema}.assessments a ON e.id = a.id
            WHERE a.id IS NULL
            """
        data = pd.read_sql_query(
            query,
            conn,
        )
    return data["id"].values


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


def fetch_emails(start_date: datetime, end_date: datetime) -> list[EmailMessage]:
    # if submit_button:
    print(f"{start_date}, {end_date}")
    # data = pd.read_pickle(os.getenv("DATA"))
    # data.to_csv("temp2.csv", index=False)

    email = GmailRetriever(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        credentials_json_path=os.getenv("EMAIL_CREDENTIAL_JSON"),
    )
    email.authenticate()
    email.connect()
    emails_payload = email.retrieve(start_date, end_date)
    return emails_payload


def save_new_emails(
    emails: list[EmailMessage], schema: str, sql_engine: Engine
) -> list[EmailMessage]:
    """Returns new emails that were just saved"""
    email_df = pd.DataFrame([x.model_dump() for x in emails])
    email_df.loc[:, "link"] = email_df.loc[:, "id"].apply(
        lambda x: f"https://mail.google.com/mail/u/0/#inbox/{x}"
    )

    matching_ids = fetch_present_ids(
        schema, [x for x in email_df.loc[:, "id"].values], sql_engine=sql_engine
    )
    mask = [x.id not in matching_ids for x in emails]
    email_df = email_df.loc[mask, :]

    ic(email_df.head())
    ic(mask)

    if not email_df.empty:
        email_df.to_sql(
            "emails",
            sql_engine,
            schema=schema,
            if_exists="append",
            index=False,
        )
        new_emails_payload = [email for email, passes in zip(emails, mask) if passes]
        return new_emails_payload
    else:
        return []


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


def process_emails(
    emails: list[EmailMessage],
    agent: OpenAIAgent,
    schema: str,
    sql_engine: Engine,
):
    progress_bar = st.progress(0)

    ic(emails)
    MAX_PROGRESS = len(emails)

    ids = []
    reviews = []
    for index, email_data in enumerate(emails):
        progress_bar.progress((index + 1) / MAX_PROGRESS)
        email_redacted = email_data.redact_data(redactor)
        ic(email_redacted)
        try:
            reviewed = agent.review(email_data)
            reviews.append(reviewed)
            ids.append(email_data.id)
        except Exception:
            pass
    if len(reviews) > 0:
        reviews_df = pd.DataFrame([x.model_dump() for x in reviews])
        ic(reviews_df)
        ic(ids)
        reviews_df["id"] = ids
        # reviews_df.loc[:, "id"] = ids

        ic(reviews_df.head())
        reviews_df.to_sql(
            "assessments",
            sql_engine,
            schema=schema,
            if_exists="append",
            index=False,
        )

    progress_bar.empty()
    st.success(f"Processing Complete! {len(reviews)} Emails Reviewed.")


def fetch_form_data(
    schema: str,
    sql_engine: Engine,
    exclusions: list[str] = [
        "id",
        "created_date",
        "edited_date",
    ],
) -> tuple[list[str]]:
    with sql_engine.connect() as conn:
        query_columns = f"SELECT * FROM {schema}.assessments LIMIT 0"
        df = pd.read_sql_query(query_columns, conn)
        bool_cols = [x for x in df.columns.tolist() if x not in exclusions]

        query_columns = f"SELECT * FROM {schema}.emails LIMIT 0"
        df = pd.read_sql_query(query_columns, conn)
        non_bool_cols = [x for x in df.columns.tolist() if x not in exclusions]
    return (bool_cols, non_bool_cols)


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


def fetch_display_data(
    review_filter: str,
    boolean_fields: list[str],
    date: datetime,
    display_fields: list[str],
    only_unacknowledged: bool,
    ack_only_field_name: str,
    schema: str,
    sql_engine: Engine,
):
    if display_fields:
        fields = f"""e.id, {ack_only_field_name}, {','.join(display_fields)}, {','.join(boolean_fields)}"""
    else:
        fields = f"""e.id, {ack_only_field_name}, {','.join(boolean_fields)}"""
    with sql_engine.connect() as conn:
        query = f"""
            SELECT {fields} FROM {schema}.emails e
            JOIN {schema}.assessments a
            ON e.id = a.id
            LEFT JOIN {schema}.acknowledge ack
            ON e.id = ack.id
            WHERE CAST(e.date AS DATE) >= %(date)s
        """
        if only_unacknowledged:
            query += f" AND {ack_only_field_name} <> True"

        data = pd.read_sql_query(
            query,
            conn,
            params={"date": date},
            parse_dates=["date"],
            dtype={ack_only_field_name: bool},
        )
    if review_filter:
        data = data[data[review_filter]]
    # mask = (data["date"] >= date) & data[ack_field].apply(
    #     lambda x: not (x and only_unacknowledged)
    # )
    return data


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


def save_acknowledgements(
    email_ids: tuple[str, bool],
    schema: str,
    sql_engine: Engine,
):
    new_acknowledgements = []
    unacknowledgements = []
    for email_id, ack_bool in email_ids:
        with sql_engine.connect() as conn:
            result = conn.execute(
                text(f"SELECT * FROM {schema}.acknowledge WHERE id = '{email_id}'")
            )
            existing_record = result.fetchone()
            if existing_record is None:
                query = text(
                    (
                        f"INSERT INTO {schema}.acknowledge "
                        f"(id, acknowledge) VALUES ('{email_id}', {ack_bool})"
                    )
                )
                conn.execute(query)
                conn.commit()
                new_acknowledgements.append(email_id)
            elif existing_record[1] != ack_bool:  # Change
                query = text(
                    (
                        f"UPDATE {schema}.acknowledge "
                        f"SET acknowledge = {ack_bool} WHERE id = '{email_id}'"
                    )
                )
                conn.execute(query)
                conn.commit()
                if ack_bool:
                    new_acknowledgements.append(email_id)
                else:
                    unacknowledgements.append(email_id)

    return new_acknowledgements, unacknowledgements
    # pass
    # export = displayed_data.loc[:, [id_field, ack_field]]
    # # print(export)
    # for index, record in export.iterrows():
    #     id = record[id_field]
    #     new_val = record[ack_field]
    #     mask = local_store[id_field] == id
    #     if sum(mask) == 0:
    #         local_store = pd.concat(
    #             [
    #                 local_store,
    #                 displayed_data.loc[
    #                     displayed_data.loc[:, id_field] == id,
    #                     [id_field, ack_field],
    #                 ],
    #             ],
    #             sort=False,
    #         )
    #     else:
    #         local_store.loc[local_store[id_field] == id, ack_field] = new_val
    # local_store.to_pickle(os.getenv("LOCAL_STORE"))
