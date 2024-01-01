import os
import dotenv
import streamlit as st
import pandas as pd
from dateutil import parser

dotenv.load_dotenv()

st.set_page_config(layout="wide")


@st.cache_data
def load_data():
    data = pd.read_pickle(os.getenv("DATA"))
    data = data.infer_objects()
    return data


data = load_data()
boolean_fields = [col for col in data.columns if data[col].dtype == "bool"]
non_boolean_fields = [col for col in data.columns if data[col].dtype != "bool"]
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
    default=non_boolean_fields,
    options=non_boolean_fields,
)
if selected_field:
    if selected_field == "all":
        filtered_data = data
        display_boolean = boolean_fields
    else:
        filtered_data = data[data[selected_field]]
        display_boolean = [selected_field]
    filtered_data = filtered_data[filtered_data["date"] >= date]

    st.write(filtered_data.loc[:, display_boolean + display_fields])
