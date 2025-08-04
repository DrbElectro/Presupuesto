# utils.py
import pandas as pd
import streamlit as st
from pathlib import Path
import config

@st.cache_data
def load_catalogue():
    return pd.read_excel(config.CATALOGO_PATH).rename(columns=str.strip)
