import requests
import time
import streamlit as st
import urllib.parse

def get_kabupaten_by_email(email, retries=5, delay=1):
    try:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SERVICE_ROLE_KEY = st.secrets["SUPABASE_SERVICE_ROLE"]
    except KeyError as e:
        print(f"❌ Missing secret: {e}")
        return None

    email = email.strip().lower()
    encoded_email = urllib.parse.quote(email, safe='')
    endpoint = f"{SUPABASE_URL}/rest/v1/user_info?email=eq.{encoded_email}"

    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    }

    for attempt in range(retries):
        try:
            res = requests.get(endpoint, headers=headers)
            print(f"🧪 Coba ke-{attempt+1}: Status {res.status_code}, Respon: {res.text}")
            if res.status_code == 200:
                data = res.json()
                print(f"📦 Data ditemukan: {data}")
                if data:
                    return data[0]["kabupaten_kota"]
            else:
                print(f"❌ Gagal mengambil data: Status {res.status_code}, Error: {res.text}")
        except requests.RequestException as e:
            print(f"❌ Error pada percobaan ke-{attempt+1}: {e}")
        time.sleep(delay)

    return None

# Fungsi untuk mendapatkan email dari token JWT
def get_email_from_token(token):
    try:
        url = f"{st.secrets['SUPABASE_URL']}/auth/v1/user"
        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": st.secrets['SUPABASE_API_KEY']
        }
        res = requests.get(url, headers=headers)
        print(f"🔍 Verifikasi token: Status {res.status_code}, Respon: {res.text}")
        if res.status_code == 200:
            return res.json().get("email")
        return None
    except requests.RequestException as e:
        print(f"❌ Gagal verifikasi token: {e}")
        return None

# Fungsi untuk mengambil daftar semua kabupaten/kota dari user_info
def get_all_kabupaten():
    try:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SERVICE_ROLE_KEY = st.secrets["SUPABASE_SERVICE_ROLE"]
    except KeyError as e:
        print(f"❌ Missing secret: {e}")
        return []

    endpoint = f"{SUPABASE_URL}/rest/v1/user_info?select=kabupaten_kota"
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    }

    try:
        res = requests.get(endpoint, headers=headers)
        if res.status_code == 200:
            data = res.json()
            # Ambil daftar kabupaten/kota unik, kecualikan "admin"
            kabupaten_list = sorted(set(item["kabupaten_kota"] for item in data if item["kabupaten_kota"] != "admin"))
            return kabupaten_list
        else:
            print(f"❌ Gagal mengambil data kabupaten: Status {res.status_code}, Error: {res.text}")
            return []
    except requests.RequestException as e:
        print(f"❌ Gagal mengambil data kabupaten: {e}")
        return []

# Fungsi untuk menghitung jumlah entri per Kab/Kota dari tabel tertentu
def get_count_by_kabupaten(table_name, kabupaten_list):
    try:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SUPABASE_API_KEY = st.secrets["SUPABASE_API_KEY"]
    except KeyError as e:
        print(f"❌ Missing secret: {e}")
        return {}

    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
    }

    # Inisialisasi dictionary dengan nilai 0 untuk semua kabupaten
    count_by_kabupaten = {kab: 0 for kab in kabupaten_list}

    # Ambil data dari tabel
    endpoint = f"{SUPABASE_URL}/rest/v1/{table_name}?select=Kab/Kota"
    try:
        res = requests.get(endpoint, headers=headers)
        if res.status_code == 200:
            data = res.json()
            # Hitung jumlah entri per Kab/Kota
            for item in data:
                kab = item.get("Kab/Kota")
                if kab in count_by_kabupaten:
                    count_by_kabupaten[kab] += 1
            return count_by_kabupaten
        else:
            print(f"❌ Gagal mengambil data dari {table_name}: Status {res.status_code}, Error: {res.text}")
            return count_by_kabupaten
    except requests.RequestException as e:
        print(f"❌ Gagal mengambil data dari {table_name}: {e}")
        return count_by_kabupaten