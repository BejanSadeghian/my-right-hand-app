import os
import dotenv
import streamlit as st
import pandas as pd
from dateutil import parser
from my_right_hand.email_client import GmailRetriever
from my_right_hand.agent import OpenAIAgent, LanguageModule
from my_right_hand.scripts import cli

dotenv.load_dotenv()

st.set_page_config(layout="wide")

ack_field = "acknowledge"
id_field = "id"
if not os.path.exists(os.getenv("LOCAL_STORE")):
    pd.DataFrame().to_pickle(os.getenv("LOCAL_STORE"))


def load_data():
    data = pd.read_pickle(os.getenv("DATA"))
    data = data.infer_objects()
    local_store = pd.read_pickle(os.getenv("LOCAL_STORE"))
    if id_field in local_store.columns.values:
        data = pd.merge(data, local_store, how="left", on=id_field)
        data.loc[:, ack_field].fillna(False, inplace=True)
    else:
        data["acknowledge"] = False
    boolean_fields = [
        col for col in data.columns if data[col].dtype == "bool" and col != ack_field
    ]
    non_boolean_fields = [
        col for col in data.columns if data[col].dtype != "bool" and col != id_field
    ]

    return data, local_store, boolean_fields, non_boolean_fields


data, local_store, boolean_fields, non_boolean_fields = load_data()

col1, col2 = st.columns((6, 6))

selected_field = col1.selectbox(
    "Select a boolean field to filter",
    options=["all"] + boolean_fields,
)
date = pd.to_datetime(
    col1.date_input(
        "Filter By Date", value=pd.to_datetime("today") - pd.DateOffset(days=7)
    ),
    utc=True,
)

display_fields = col2.multiselect(
    "Select Fields to Show",
    default=["sender", "subject", "date"],
    options=non_boolean_fields,
)

only_unacknowledged = col2.checkbox("Exclude Acknowledged", value=False)


with st.form("save_data"):
    form_button = st.form_submit_button("Save")
    if selected_field == "all":
        filtered_data = data
        display_boolean = boolean_fields
    else:
        filtered_data = data[data[selected_field]]
        display_boolean = [selected_field]
    mask = (filtered_data["date"] >= date) & filtered_data[ack_field].apply(
        lambda x: not (x and only_unacknowledged)
    )
    st.session_state["filtered_data"] = filtered_data[mask]

    displayed_data = st.data_editor(
        st.session_state["filtered_data"].loc[
            :, [id_field, ack_field] + display_fields + display_boolean
        ],
        disabled=display_boolean + display_fields + [id_field],
        hide_index=True,
    )

    if form_button:
        export = displayed_data.loc[:, [id_field, ack_field]]
        # print(export)
        for index, record in export.iterrows():
            id = record[id_field]
            new_val = record[ack_field]
            mask = local_store[id_field] == id
            if sum(mask) == 0:
                local_store = pd.concat(
                    [
                        local_store,
                        displayed_data.loc[
                            displayed_data.loc[:, id_field] == id, [id_field, ack_field]
                        ],
                    ],
                    sort=False,
                )
            else:
                local_store.loc[local_store[id_field] == id, ack_field] = new_val
        local_store.to_pickle(os.getenv("LOCAL_STORE"))
