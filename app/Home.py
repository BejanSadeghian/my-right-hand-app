import dotenv
import streamlit as st
from utils import init_app

dotenv.load_dotenv()

init_app()

st.write("Hello World!")
