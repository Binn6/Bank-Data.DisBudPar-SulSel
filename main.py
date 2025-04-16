import streamlit as st

st.set_page_config(page_title="Redirecting...", layout="centered")

# Redirect ke halaman login saat app dibuka
if "user_email" not in st.session_state:
    st.switch_page("pages/0_login.py")
else:
    st.switch_page("pages/1_app.py")
