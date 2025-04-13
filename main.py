import streamlit as st

# Set page config harus menjadi perintah Streamlit pertama
st.set_page_config(page_title="Aplikasi Input Data Pariwisata", layout="centered")

# Langsung arahkan ke halaman login
st.switch_page("pages/0_login.py")