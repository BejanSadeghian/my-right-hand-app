import os
import dotenv
import streamlit as st
import pandas as pd
import my_right_hand as rh

from icecream import ic
from datetime import datetime, timedelta
from openai import OpenAI
from dateutil import parser

from utils import init_app, init_emails_page
from my_right_hand.email_client import GmailRetriever
from my_right_hand.utils import redactor, generate_dataframe
from my_right_hand.agent import OpenAIAgent

dotenv.load_dotenv()

init_app()
init_emails_page()

DEFAULT_WINDOW = 2
SCHEMA = os.getenv("DB_SCHEMA")

client = OpenAI(
    api_key=os.getenv("OAI_API_KEY"),
)
agent = OpenAIAgent(
    client=client,
    model=os.getenv("OAI_CHAT_MODEL"),
    use_snippet=False,
)


def fetch_present_ids(schema: str, pk_list: list[str]):
    with st.session_state["sql_engine"].connect() as conn:
        query = f"SELECT id FROM {SCHEMA}.emails WHERE id IN %(pk_list)s"

        matching_ids = pd.read_sql_query(
            query,
            conn,
            params={"pk_list": tuple(pk_list)},
        )
    ic(matching_ids[["id"]])
    return matching_ids["id"].values


def fetch_unreviewed_ids(schema: str):
    with st.session_state["sql_engine"].connect() as conn:
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


def render_email_fetch():
    with st.form("request_emails"):
        col1, col2, _ = st.columns((3, 3, 6))
        start_date = col1.date_input(
            "Start Date",
            datetime.now() - timedelta(days=DEFAULT_WINDOW),
        )
        end_date = col2.date_input("End Date", datetime.now())
        submit_button = col2.form_submit_button("Fetch Emails")

    if submit_button:
        print(f"{start_date}, {end_date}")
        # data = pd.read_pickle(os.getenv("DATA"))
        # data.to_csv("temp2.csv", index=False)

        email = GmailRetriever(
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            credentials_json_path=os.getenv("EMAIL_CREDENTIAL_JSON"),
        )
        email.authenticate()
        email.connect()
        st.session_state["emails"] = email.retrieve(start_date, end_date)
        email_df = pd.DataFrame([x.model_dump() for x in st.session_state["emails"]])
        email_df.loc[:, "link"] = email_df.loc[:, "id"].apply(
            lambda x: f"https://mail.google.com/mail/u/0/#inbox/{x}"
        )

        matching_ids = fetch_present_ids(
            SCHEMA,
            [x for x in email_df.loc[:, "id"].values],
        )
        mask = [x.id not in matching_ids for x in st.session_state["emails"]]
        email_df = email_df.loc[mask, :]

        ic(email_df.head())
        ic(mask)
        if not email_df.empty:
            email_df.to_sql(
                "emails",
                st.session_state["sql_engine"],
                schema=SCHEMA,
                if_exists="append",
                index=False,
            )
            st.session_state["new_emails"] = [
                email
                for email, passes in zip(st.session_state["emails"], mask)
                if passes
            ]
    return start_date, end_date


def render_email_processing():
    # st.session_state["emails_needing_review"] = fetch_unreviewed_ids(SCHEMA)
    email_ids_needing_review = fetch_unreviewed_ids(SCHEMA)
    ic(email_ids_needing_review)
    with st.form("process_email"):
        col1, col2, col3 = st.columns((2, 2, 8))
        col1.metric("Emails Retrieved", value=len(st.session_state["emails"]))
        col2.metric("New Emails", value=len(st.session_state["new_emails"]))
        col2.metric(
            "Unreviewed Emails",
            value=len(email_ids_needing_review),
        )
        with col3.expander("Retrieved Emails"):
            st.write(pd.DataFrame([x.model_dump() for x in st.session_state["emails"]]))
        process_submit = col1.form_submit_button("Process Emails")

    if process_submit:
        # if st.session_state['email_ids_needing_review'].empty:
        #     return None
        progress_bar = st.progress(0)
        emails = [
            email
            for email in st.session_state["emails"]
            if email.id in email_ids_needing_review
        ]
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
            except:
                pass
        if len(reviews) > 0:
            reviews_df = pd.DataFrame([x.model_dump() for x in reviews])
            ic(reviews_df)
            ic(ids)
            reviews_df[["id"]] = ids

            ic(reviews_df.head())
            reviews_df.to_sql(
                "assessments",
                st.session_state["sql_engine"],
                schema=SCHEMA,
                if_exists="append",
                index=False,
            )

        progress_bar.empty()
        st.toast("Done!")


start_date, end_date = render_email_fetch()

if st.session_state["emails"]:
    render_email_processing()

# col1, col2 = st.columns((6, 6))

# selected_field = col1.selectbox(
#     "Select a boolean field to filter",
#     options=["all"] + boolean_fields,
# )
# date = pd.to_datetime(
#     col1.date_input(
#         "Filter By Date", value=pd.to_datetime("today") - pd.DateOffset(days=7)
#     ),
#     utc=True,
# )

# display_fields = col2.multiselect(
#     "Select Fields to Show",
#     default=["sender", "subject", "date"],
#     options=non_boolean_fields,
# )

# only_unacknowledged = col2.checkbox("Exclude Acknowledged", value=False)


# with st.form("save_data"):
#     form_button = st.form_submit_button("Save")
#     if selected_field == "all":
#         filtered_data = data
#         display_boolean = boolean_fields
#     else:
#         filtered_data = data[data[selected_field]]
#         display_boolean = [selected_field]
#     mask = (filtered_data["date"] >= date) & filtered_data[ack_field].apply(
#         lambda x: not (x and only_unacknowledged)
#     )
#     st.session_state["filtered_data"] = filtered_data[mask]

#     displayed_data = st.data_editor(
#         st.session_state["filtered_data"].loc[
#             :, [id_field, ack_field] + display_fields + display_boolean
#         ],
#         disabled=display_boolean + display_fields + [id_field],
#         hide_index=True,
#     )

#     if form_button:
#         export = displayed_data.loc[:, [id_field, ack_field]]
#         # print(export)
#         for index, record in export.iterrows():
#             id = record[id_field]
#             new_val = record[ack_field]
#             mask = local_store[id_field] == id
#             if sum(mask) == 0:
#                 local_store = pd.concat(
#                     [
#                         local_store,
#                         displayed_data.loc[
#                             displayed_data.loc[:, id_field] == id, [id_field, ack_field]
#                         ],
#                     ],
#                     sort=False,
#                 )
#             else:
#                 local_store.loc[local_store[id_field] == id, ack_field] = new_val
#         local_store.to_pickle(os.getenv("LOCAL_STORE"))
