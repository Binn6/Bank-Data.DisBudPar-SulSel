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
            kabupaten_list = sorted(set(item["kabupaten_kota"] for item in data if item["kabupaten_kota"] != "admin"))
            return kabupaten_list
        else:
            print(f"❌ Gagal mengambil data kabupaten: Status {res.status_code}, Error: {res.text}")
            return []
    except requests.RequestException as e:
        print(f"❌ Gagal mengambil data kabupaten: {e}")
        return []

def get_count_by_kabupaten(table_name, kabupaten_list, kab_column="Kab_Kota"):
    try:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SUPABASE_API_KEY = st.secrets["SUPABASE_API_KEY"]
    except KeyError as e:
        print(f"❌ Missing secret: {e}")
        return {kab: 0 for kab in kabupaten_list}

    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
    }

    count_by_kabupaten = {kab: 0 for kab in kabupaten_list}

    for kab in kabupaten_list:
        try:
            # Normalisasi nama kabupaten
            normalized_kab = kab.lower().replace("kabupaten ", "").replace("kab. ", "").strip()
            # Gunakan ilike untuk pencocokan fleksibel
            query = f"{kab_column}=ilike.*{urllib.parse.quote(normalized_kab)}*"
            endpoint = f"{SUPABASE_URL}/rest/v1/{table_name}?{query}&select=count"
            res = requests.get(endpoint, headers=headers)
            if res.status_code == 200:
                data = res.json()
                count_by_kabupaten[kab] = data[0]["count"] if data else 0
            else:
                print(f"❌ Gagal mengambil data dari {table_name} untuk {kab}: Status {res.status_code}, Error: {res.text}")
        except requests.RequestException as e:
            print(f"❌ Gagal mengambil data dari {table_name} untuk {kab}: {e}")

    return count_by_kabupaten