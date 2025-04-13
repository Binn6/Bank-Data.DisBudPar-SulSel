import streamlit as st
import requests
import json
from utils import get_kabupaten_by_email, get_email_from_token

# Set page config harus menjadi perintah Streamlit pertama
st.set_page_config(page_title="Login - Input Data", layout="centered")

# Sembunyikan sidebar dan tombol toggle sidebar
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    [data-testid="stSidebarNavCollapsed"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ... (kode lainnya tetap sama)

st.title("🔐 Login Input Data Kab/Kota")

# Cek jika pengguna baru logout
if 'just_logged_out' in st.session_state and st.session_state['just_logged_out']:
    st.success("✅ Anda telah logout.")
    st.session_state['just_logged_out'] = False

# Cek jika sudah login
if 'user_email' in st.session_state and 'kabupaten' in st.session_state:
    st.success(f"✅ Anda sudah login sebagai {st.session_state['user_email']}")
    if st.button("Logout"):
        st.session_state.pop('user_email', None)
        st.session_state.pop('kabupaten', None)
        st.session_state.pop('auth_token', None)
        st.session_state['just_logged_out'] = True
        st.rerun()
    st.stop()

# Form Login
email = st.text_input("Email")
password = st.text_input("Password", type="password")

# Tombol Login
if st.button("Login"):
    if not email or not password:
        st.warning("⚠️ Harap isi email dan password.")
    else:
        with st.spinner("🔄 Sedang memproses login..."):
            email = email.strip().lower()
            
            SUPABASE_URL = st.secrets["SUPABASE_URL"]
            SUPABASE_AUTH = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
            API_KEY = st.secrets["SUPABASE_API_KEY"]

            headers = {
                "apikey": API_KEY,
                "Content-Type": "application/json"
            }
            data = {"email": email, "password": password}

            try:
                res = requests.post(SUPABASE_AUTH, headers=headers, data=json.dumps(data))
                print(f"🔍 Autentikasi: Status {res.status_code}, Respon: {res.text}")

                if res.status_code == 200:
                    token = res.json()["access_token"]
                    st.session_state['auth_token'] = token

                    # Verifikasi email dari token
                    verified_email = get_email_from_token(token)
                    if not verified_email:
                        st.error("❌ Gagal verifikasi token login.")
                        st.session_state.pop('auth_token', None)
                        st.stop()

                    verified_email = verified_email.strip().lower()

                    # Ambil kabupaten dari tabel user_info
                    kabupaten = get_kabupaten_by_email(verified_email)
                    if kabupaten:
                        st.session_state['user_email'] = verified_email
                        st.session_state['kabupaten'] = kabupaten
                        st.success(f"✅ Login berhasil sebagai {kabupaten}")
                        st.switch_page("pages/1_app.py")
                    else:
                        st.error("❌ Email tidak ditemukan di tabel user_info.")
                        st.session_state.pop('auth_token', None)
                else:
                    st.error(f"❌ Email atau password salah.")
            except requests.RequestException as e:
                st.error(f"❌ Gagal melakukan autentikasi: {e}")