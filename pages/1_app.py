import streamlit as st
import pandas as pd
import datetime
import requests
import io
import urllib.parse
import time
import simplejson as json
from utils import get_kabupaten_by_email, get_email_from_token, get_all_kabupaten, get_count_by_kabupaten

# Set page config harus menjadi perintah Streamlit pertama
st.set_page_config(page_title="Input Data Pariwisata", layout="centered")

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
    @media (max-width: 600px) {
        .stSlider > div { width: 100% !important; }
        .stTextInput > div, .stTextArea > div, .stSelectbox > div {
            width: 100% !important;
        }
    }
    .stButton>button {
        background-color: #2ecc71 !important; /* hijau segar */
        color: white !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        border: none !important;
    }
    .stButton>button:hover {
        background-color: #27ae60 !important; /* hijau lebih tua pas hover */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Cek apakah pengguna sudah login
if 'user_email' not in st.session_state or 'kabupaten' not in st.session_state:
    # Coba pulihkan sesi dari auth_token
    if 'auth_token' in st.session_state:
        token = st.session_state['auth_token']
        verified_email = get_email_from_token(token)
        if verified_email:
            verified_email = verified_email.strip().lower()
            kabupaten = get_kabupaten_by_email(verified_email)
            if kabupaten:
                # Pulihkan sesi
                st.session_state['user_email'] = verified_email
                st.session_state['kabupaten'] = kabupaten
            else:
                # Jika kabupaten tidak ditemukan, hapus sesi dan arahkan ke login
                st.session_state.pop('user_email', None)
                st.session_state.pop('kabupaten', None)
                st.session_state.pop('auth_token', None)
                st.error("Sesi tidak valid. Silakan login kembali.")
                st.switch_page("pages/0_login.py")
                st.stop()
        else:
            # Jika token tidak valid, hapus sesi dan arahkan ke login
            st.session_state.pop('user_email', None)
            st.session_state.pop('kabupaten', None)
            st.session_state.pop('auth_token', None)
            st.error("Sesi telah kedaluwarsa. Silakan login kembali.")
            st.switch_page("pages/0_login.py")
            st.stop()
    else:
        # Jika tidak ada token, arahkan ke login
        st.error("Anda harus login terlebih dahulu!")
        st.switch_page("pages/0_login.py")
        st.stop()

# ==============================
# 🔐 Konfigurasi Supabase
# ==============================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_API_KEY = st.secrets["SUPABASE_API_KEY"]
except KeyError as e:
    st.error(f"Missing secret: {e}")
    st.stop()

BUCKET_NAME = "gambar.pariwisata"
SUPABASE_STORAGE_URL = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}"
SUPABASE_STORAGE_UPLOAD_URL = f"{SUPABASE_URL}/storage/v1/object"
SUPABASE_STORAGE_PUBLIC_URL = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}"

headers = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}"
}

# ==============================
# 🎨 Styling CSS + Responsiveness
# ==============================
st.markdown("""
    <style>
    @media (max-width: 600px) {
        .stSlider > div { width: 100% !important; }
        .stTextInput > div, .stTextArea > div, .stSelectbox > div {
            width: 100% !important;
        }
    }
    .stButton>button {
        background-color: #2ecc71 !important; /* hijau segar */
        color: white !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        border: none !important;
    }
    .stButton>button:hover {
        background-color: #27ae60 !important; /* hijau lebih tua pas hover */
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Pemutakhiran Data Industri Pariwisata Tahun 2025 Sulawesi Selatan")

# Tambahkan tombol logout
if st.button("Logout"):
    st.session_state.pop('user_email', None)
    st.session_state.pop('kabupaten', None)
    st.session_state.pop('auth_token', None)
    st.session_state['just_logged_out'] = True
    st.switch_page("pages/0_login.py")

# Inisialisasi session state untuk notifikasi dan form
if 'notification' not in st.session_state:
    st.session_state.notification = None
if 'form_destinasi_reset' not in st.session_state:
    st.session_state.form_destinasi_reset = False
if 'clear_form_industri' not in st.session_state:
    st.session_state.clear_form_industri = False

# Fungsi untuk menampilkan notifikasi
def show_notification(type, message, delay=2):
    st.session_state.notification = {"type": type, "message": message}
    if type == "success":
        st.success(message)
    elif type == "error":
        st.error(message)
    elif type == "warning":
        st.warning(message)
    elif type == "info":
        st.info(message)
    time.sleep(delay)  # Berikan waktu untuk pengguna melihat notifikasi
    st.session_state.notification = None

# =======================
# 🚀 TAB NAVIGATION
# =======================
# Cek apakah pengguna adalah admin
is_admin = st.session_state['user_email'] == "sulsel.disbudpar@gmail.com"

# Tampilkan tab berdasarkan status admin
if is_admin:
    tab1, tab2, tab3, tab4 = st.tabs(["📍 Form Destinasi", "🏨 Form Industri", "📁 Upload Excel/CSV", "📈 Progres Upload Data"])
else:
    tab1, tab2, tab3 = st.tabs(["📍 Form Destinasi", "🏨 Form Industri", "📁 Upload Excel/CSV"])

# =======================
# 📍 FORM DESTINASI
# =======================
with tab1:
    st.subheader("📍 Form Input Destinasi Wisata")

    col1, col2 = st.columns(2)

    # Inisialisasi nilai default untuk form menggunakan session state
    if st.session_state.form_destinasi_reset:
        nama = ""
        kab_kota = ""
        kecamatan = ""
        kelurahan_desa = ""
        deskripsi = ""
        rating = 5
        fasilitas_umum = ""
        jarak_ibukota = ""
        pengelola = None
        gambar = None
        st.session_state.form_destinasi_reset = False
    else:
        nama = st.session_state.get("nama", "")
        kab_kota = st.session_state.get("kab_kota", "")
        kecamatan = st.session_state.get("kecamatan", "")
        kelurahan_desa = st.session_state.get("kelurahan_desa", "")
        deskripsi = st.session_state.get("deskripsi", "")
        rating = st.session_state.get("rating", 5)
        fasilitas_umum = st.session_state.get("fasilitas_umum", "")
        jarak_ibukota = st.session_state.get("jarak_ibukota", "")
        pengelola = st.session_state.get("pengelola", None)
        gambar = None

    with st.form("form_destinasi"):
        with col1:
            nama = st.text_input("Nama Destinasi", value=nama, placeholder="Masukkan Nama Destinasi", key="nama_input")
            kab_kota = st.text_input("Kabupaten/Kota", value=kab_kota, placeholder="Masukkan Kabupaten/Kota", key="kab_kota_input")
            kecamatan = st.text_input("Kecamatan", value=kecamatan, placeholder="Masukkan Kecamatan", key="kecamatan_input")
            kelurahan_desa = st.text_input("Kelurahan/Desa", value=kelurahan_desa, placeholder="Masukkan Kelurahan/Desa", key="kelurahan_desa_input")
            pengelola = st.selectbox("Pengelola", ["Pemerintah", "Swasta", "Lainnya"], index=None, placeholder="Pilih Pengelola", key="pengelola_input")

        with col2:
            deskripsi = st.text_area("Deskripsi Destinasi", value=deskripsi, placeholder="Masukkan Deskripsi Destinasi Wisata Anda", key="deskripsi_input")
            fasilitas_umum = st.text_area("Fasilitas Umum", value=fasilitas_umum, placeholder="Masukkan Fasilitas Umum (toilet, musholla, dll)", key="fasilitas_umum_input")
            jarak_ibukota = st.text_input("Jarak ke Ibukota Kab/Kota", value=jarak_ibukota, placeholder="Masukkan Jarak (contoh: 5 km atau 30 menit)", key="jarak_ibukota_input")
            rating = st.slider("Rating Potensi (1-10)", 1, 10, value=rating, key="rating_input")
            gambar = st.file_uploader("Upload Gambar Destinasi", type=["jpg", "jpeg", "png"], key="gambar_input")

        submit_destinasi = st.form_submit_button("Kirim Data")

    if submit_destinasi:
        # Validasi semua kolom wajib, termasuk gambar
        if not all([nama.strip(), kab_kota.strip(), kecamatan.strip(), kelurahan_desa.strip(), deskripsi.strip(), pengelola, gambar]):
            show_notification("warning", "Harap isi semua kolom wajib sebelum mengirim, termasuk gambar dan pengelola.")
        else:
            try:
                if gambar.size > 50 * 1024 * 1024:
                    show_notification("warning", "Ukuran file terlalu besar! Maksimum 50MB.")
                else:
                    gambar_url = None
                    file_name = f"{nama.replace(' ', '_')}_{gambar.name}"
                    file_path = f"Destinasi_Wisata/{file_name}"
                    upload_url = f"{SUPABASE_STORAGE_UPLOAD_URL}/{BUCKET_NAME}/{file_path}"
                    
                    try:
                        res_upload = requests.post(
                            upload_url,
                            data=gambar.getvalue(),
                            headers={
                                **headers,
                                "Content-Type": gambar.type,
                                "x-upsert": "true"
                            }
                        )
                        if res_upload.status_code in [200, 201]:
                            encoded_file_path = urllib.parse.quote(file_path)
                            gambar_url = f"{SUPABASE_STORAGE_PUBLIC_URL}/{encoded_file_path}"
                            show_notification("info", f"URL Gambar: {gambar_url}")
                        else:
                            show_notification("error", f"Gagal upload gambar: {res_upload.text}")
                            gambar_url = None
                    except requests.RequestException as e:
                        show_notification("error", f"Gagal upload gambar: {e}")
                        gambar_url = None

                    # Jika gambar gagal diunggah, hentikan proses
                    if gambar_url is None:
                        show_notification("error", "Gagal mengunggah gambar. Data tidak dikirim.")
                    else:
                        data = {
                            "Nama": nama,
                            "Kab_Kota": kab_kota,
                            "Kecamatan": kecamatan,
                            "Kelurahan_Desa": kelurahan_desa,
                            "Deskripsi": deskripsi,
                            "Fasilitas_Umum": fasilitas_umum,
                            "Jarak_Ibukota": jarak_ibukota,
                            "Pengelola": pengelola,
                            "Rating": rating,
                            "Gambar_URL": gambar_url,
                            "Tanggal_Input": datetime.datetime.now().isoformat()
                        }
                        try:
                            res = requests.post(
                                f"{SUPABASE_URL}/rest/v1/Destinasi%20Wisata",
                                json=data,
                                headers={
                                    **headers,
                                    "Content-Type": "application/json",
                                    "Prefer": "return=minimal"
                                }
                            )
                            if res.status_code == 201:
                                show_notification("success", "Data berhasil dikirim ke Supabase!")
                                st.session_state.form_destinasi_reset = True
                                st.rerun()
                            else:
                                show_notification("error", f"Gagal kirim data: {res.text}")
                        except requests.RequestException as e:
                            show_notification("error", f"Gagal kirim data ke Supabase: {e}")
            except Exception as e:
                show_notification("error", f"Terjadi kesalahan: {e}")

# =======================
# 🏨 FORM INDUSTRI
# =======================
with tab2:
    st.subheader("🏨 Form Input Industri Pariwisata")

    if st.session_state.clear_form_industri:
        st.session_state.clear_form_industri = False
        nama_usaha = ""
        jenis_industri = None
        jumlah_kamar = 0
        fasilitas = ""
        jenis_kontak = None
        kontak = ""
        jumlah_karyawan_pria = 0
        jumlah_karyawan_wanita = 0
        kab_kota = ""
        kecamatan = ""
        kelurahan_desa = ""
        gambar_industri = None
        bintang_hotel = 0
        nib_available = None
        nib = ""
        chse = None
        jumlah_bed = 0
        dapur_halal = None
        jumlah_kursi = 0
        sertifikat_halal = None
        standar_available = None
        sertifikat_standar = ""
        trapis_available = None
        trapis = ""
        jenis_hiburan = None
    else:
        nama_usaha = st.session_state.get("nama_usaha", "")
        jenis_industri = st.session_state.get("jenis_industri", None)
        jumlah_kamar = st.session_state.get("jumlah_kamar", 0)
        fasilitas = st.session_state.get("fasilitas", "")
        jenis_kontak = st.session_state.get("jenis_kontak", None)
        kontak = st.session_state.get("kontak", "")
        jumlah_karyawan_pria = st.session_state.get("jumlah_karyawan_pria", 0)
        jumlah_karyawan_wanita = st.session_state.get("jumlah_karyawan_wanita", 0)
        kab_kota = st.session_state.get("kab_kota_industri", "")
        kecamatan = st.session_state.get("kecamatan_industri", "")
        kelurahan_desa = st.session_state.get("kelurahan_desa_industri", "")
        gambar_industri = None
        bintang_hotel = st.session_state.get("bintang_hotel", 0)
        nib_available = st.session_state.get("nib_available", None)
        nib = st.session_state.get("nib", "")
        chse = st.session_state.get("chse", None)
        jumlah_bed = st.session_state.get("jumlah_bed", 0)
        dapur_halal = st.session_state.get("dapur_halal", None)
        jumlah_kursi = st.session_state.get("jumlah_kursi", 0)
        sertifikat_halal = st.session_state.get("sertifikat_halal", None)
        standar_available = st.session_state.get("standar_available", None)
        sertifikat_standar = st.session_state.get("sertifikat_standar", "")
        trapis_available = st.session_state.get("trapis_available", None)
        trapis = st.session_state.get("trapis", "")
        jenis_hiburan = st.session_state.get("jenis_hiburan", None)

    col1, col2 = st.columns(2)

    with st.form("form_industri"):
        with col1:
            nama_usaha = st.text_input("Nama Usaha", value=nama_usaha, placeholder="Masukkan Nama Usaha", key="nama_usaha_input")
            jenis_industri = st.selectbox(
                "Jenis Industri",
                ["Travel", "Hotel", "Wisma", "Villa", "Homestay", "Restoran", "Rumah Makan", "Catering", "Spa", "Usaha Hiburan"],
                index=None,
                placeholder="Pilih Jenis Industri",
                key="jenis_industri_input"
            )
            jumlah_karyawan_pria = st.number_input("Jumlah Karyawan Pria", value=jumlah_karyawan_pria, min_value=0, key="jumlah_karyawan_pria_input")
            jumlah_karyawan_wanita = st.number_input("Jumlah Karyawan Wanita", value=jumlah_karyawan_wanita, min_value=0, key="jumlah_karyawan_wanita_input")
            
            # Kolom untuk Hotel, Wisma, Villa, Homestay
            if jenis_industri in ["Hotel", "Wisma", "Villa", "Homestay"]:
                jumlah_kamar = st.number_input("Jumlah Kamar", value=jumlah_kamar, min_value=0, key="jumlah_kamar_input")
                jumlah_bed = st.number_input("Jumlah Bed", value=jumlah_bed, min_value=0, key="jumlah_bed_input")
                fasilitas = st.text_area("Fasilitas", value=fasilitas, placeholder="Masukkan Fasilitas Tersedia (wifi, parkir, dll)", key="fasilitas_input")
                dapur_halal = st.selectbox("Dapur Halal", ["Ya", "Tidak"], index=None, placeholder="Pilih Status Dapur Halal", key="dapur_halal_input")
                sertifikat_halal = st.selectbox("Sertifikat Halal", ["Ya", "Tidak"], index=None, placeholder="Pilih Status Sertifikat Halal (opsional)", key="sertifikat_halal_input")
            
            # Kolom untuk Hotel
            if jenis_industri == "Hotel":
                bintang_hotel = st.slider("Jumlah Bintang Hotel (0-5)", 0, 5, value=bintang_hotel, key="bintang_hotel_input")
            
            # Kolom untuk Restoran dan Rumah Makan
            if jenis_industri in ["Restoran", "Rumah Makan"]:
                jumlah_kursi = st.number_input("Jumlah Kursi", value=jumlah_kursi, min_value=0, key="jumlah_kursi_input")
                fasilitas = st.text_area("Fasilitas", value=fasilitas, placeholder="Masukkan Fasilitas Tersedia (wifi, parkir, dll)", key="fasilitas_input")
                sertifikat_halal = st.selectbox("Sertifikat Halal", ["Ya", "Tidak"], index=None, placeholder="Pilih Status Sertifikat Halal (opsional)", key="sertifikat_halal_input")
            
            # Kolom untuk Catering
            if jenis_industri == "Catering":
                sertifikat_halal = st.selectbox("Sertifikat Halal", ["Ya", "Tidak"], index=None, placeholder="Pilih Status Sertifikat Halal (opsional)", key="sertifikat_halal_input")
            
            # Kolom untuk Spa
            if jenis_industri == "Spa":
                sertifikat_halal = st.selectbox("Sertifikat Halal", ["Ya", "Tidak"], index=None, placeholder="Pilih Status Sertifikat Halal (opsional)", key="sertifikat_halal_input")
            
            # Kolom untuk Usaha Hiburan
            if jenis_industri == "Usaha Hiburan":
                jenis_hiburan = st.selectbox(
                    "Jenis Hiburan",
                    ["Club Malam", "Karaoke", "Diskotik", "Billiard"],
                    index=None,
                    placeholder="Pilih Jenis Hiburan",
                    key="jenis_hiburan_input"
                )

        with col2:
            jenis_kontak = st.selectbox("Jenis Kontak", options=["Whatsapp", "Instagram", "Email"], index=None, placeholder="Pilih Jenis Kontak", key="jenis_kontak_input")
            kontak = st.text_input(f"{jenis_kontak}", value=kontak, placeholder=f"Masukkan {jenis_kontak}" if jenis_kontak else "", key="kontak_input") if jenis_kontak else None
            kab_kota = st.text_input("Kabupaten/Kota", value=kab_kota, placeholder="Masukkan Kabupaten/Kota", key="kab_kota_industri_input")
            kecamatan = st.text_input("Kecamatan", value=kecamatan, placeholder="Masukkan Kecamatan", key="kecamatan_industri_input")
            kelurahan_desa = st.text_input("Kelurahan/Desa", value=kelurahan_desa, placeholder="Masukkan Kelurahan/Desa", key="kelurahan_desa_industri_input")
            
            # Kolom NIB untuk Travel, Spa, Catering, Hotel, Wisma, Villa, Homestay, Restoran, Rumah Makan, Usaha Hiburan
            if jenis_industri in ["Travel", "Spa", "Catering", "Hotel", "Wisma", "Villa", "Homestay", "Restoran", "Rumah Makan", "Usaha Hiburan"]:
                nib_available = st.selectbox("Nomor Induk Berusaha (NIB) Tersedia?", ["Ya", "Tidak"], index=None, placeholder="Pilih Status NIB", key="nib_available_input")
                if nib_available == "Ya":
                    nib = st.text_input("Nomor Induk Berusaha (NIB)", value=nib, placeholder="Masukkan NIB", key="nib_input")
            
            # Kolom CHSE untuk Hotel, Wisma, Villa, Homestay, Restoran, Rumah Makan
            if jenis_industri in ["Hotel", "Wisma", "Villa", "Homestay", "Restoran", "Rumah Makan"]:
                chse = st.selectbox("CHSE", ["Ya", "Tidak"], index=None, placeholder="Pilih Status CHSE", key="chse_input")
            
            # Kolom Standar untuk Spa dan Usaha Hiburan
            if jenis_industri in ["Spa", "Usaha Hiburan"]:
                standar_available = st.selectbox("Standar Tersedia?", ["Ya", "Tidak"], index=None, placeholder="Pilih Status Standar", key="standar_available_input")
                if standar_available == "Ya":
                    sertifikat_standar = st.text_input("Sertifikat Standar", value=sertifikat_standar, placeholder="Masukkan Sertifikat Standar", key="sertifikat_standar_input")
            
            # Kolom Trapis untuk Catering
            if jenis_industri == "Catering":
                trapis_available = st.selectbox("Trapis Tersedia?", ["Ya", "Tidak"], index=None, placeholder="Pilih Status Trapis", key="trapis_available_input")
                if trapis_available == "Ya":
                    trapis = st.text_input("Trapis", value=trapis, placeholder="Masukkan Trapis", key="trapis_input")
            
            gambar_industri = st.file_uploader("Upload Gambar Usaha", type=["jpg", "jpeg", "png"], key="gambar_industri_input")

        submit_industri = st.form_submit_button("Kirim Data Industri")

    if submit_industri:
        required_fields = [
            nama_usaha.strip() if nama_usaha else "",
            jenis_industri,
            jenis_kontak,
            kontak.strip() if kontak else "",
            kab_kota.strip() if kab_kota else "",
            kecamatan.strip() if kecamatan else "",
            kelurahan_desa.strip() if kelurahan_desa else ""
        ]
        
        # Validasi tambahan berdasarkan jenis industri
        if jenis_industri in ["Hotel", "Wisma", "Villa", "Homestay"]:
            required_fields.extend([
                dapur_halal,
                nib_available,
                chse,
                fasilitas.strip() if fasilitas else "",
                jumlah_kamar,
                jumlah_bed
            ])
            if nib_available == "Ya":
                required_fields.append(nib.strip() if nib else "")
        
        if jenis_industri in ["Restoran", "Rumah Makan"]:
            required_fields.extend([
                nib_available,
                chse,
                fasilitas.strip() if fasilitas else "",
                jumlah_kursi
            ])
            if nib_available == "Ya":
                required_fields.append(nib.strip() if nib else "")
        
        if jenis_industri == "Spa":
            required_fields.extend([
                nib_available,
                standar_available
            ])
            if nib_available == "Ya":
                required_fields.append(nib.strip() if nib else "")
            if standar_available == "Ya":
                required_fields.append(sertifikat_standar.strip() if sertifikat_standar else "")
        
        if jenis_industri == "Catering":
            required_fields.extend([
                nib_available,
                trapis_available
            ])
            if nib_available == "Ya":
                required_fields.append(nib.strip() if nib else "")
            if trapis_available == "Ya":
                required_fields.append(trapis.strip() if trapis else "")
        
        if jenis_industri == "Travel":
            required_fields.append(nib_available)
            if nib_available == "Ya":
                required_fields.append(nib.strip() if nib else "")
        
        if jenis_industri == "Usaha Hiburan":
            required_fields.extend([
                nib_available,
                standar_available,
                jenis_hiburan
            ])
            if nib_available == "Ya":
                required_fields.append(nib.strip() if nib else "")
            if standar_available == "Ya":
                required_fields.append(sertifikat_standar.strip() if sertifikat_standar else "")

        if not all(required_fields):
            show_notification("warning", "Semua kolom wajib diisi. Gambar dan Sertifikat Halal opsional.")
        else:
            try:
                check_industri = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Industri?Nama_Usaha=eq.{urllib.parse.quote(nama_usaha)}",
                    headers=headers
                )
                if check_industri.status_code == 200 and check_industri.json():
                    show_notification("warning", "Data dengan nama usaha ini sudah ada di database!")
                elif gambar_industri and gambar_industri.size > 50 * 1024 * 1024:
                    show_notification("warning", "Ukuran file terlalu besar! Maksimum 50MB.")
                else:
                    gambar_url = None
                    if gambar_industri:
                        file_name = f"{nama_usaha.replace(' ', '_')}_{gambar_industri.name}"
                        file_path = f"Industri/{file_name}"
                        upload_url = f"{SUPABASE_STORAGE_UPLOAD_URL}/{BUCKET_NAME}/{file_path}"
                        
                        try:
                            res_upload = requests.post(
                                upload_url,
                                data=gambar_industri.getvalue(),
                                headers={
                                    **headers,
                                    "Content-Type": gambar_industri.type,
                                    "x-upsert": "true"
                                }
                            )
                            if res_upload.status_code in [200, 201]:
                                encoded_file_path = urllib.parse.quote(file_path)
                                gambar_url = f"{SUPABASE_STORAGE_PUBLIC_URL}/{encoded_file_path}"
                                show_notification("info", f"URL Gambar: {gambar_url}")
                            else:
                                show_notification("error", f"Gagal upload gambar: {res_upload.text}")
                                gambar_url = None
                        except requests.RequestException as e:
                            show_notification("error", f"Gagal upload gambar: {e}")
                            gambar_url = None

                    data_industri = {
                        "Nama_Usaha": nama_usaha,
                        "Jenis_Industri": jenis_industri,
                        "Karyawan_Pria": jumlah_karyawan_pria,
                        "Karyawan_Wanita": jumlah_karyawan_wanita,
                        "Jumlah_Kamar": jumlah_kamar if jenis_industri in ["Hotel", "Wisma", "Villa", "Homestay"] else None,
                        "Jumlah_Bed": jumlah_bed if jenis_industri in ["Hotel", "Wisma", "Villa", "Homestay"] else None,
                        "Fasilitas": fasilitas if jenis_industri in ["Hotel", "Wisma", "Villa", "Homestay", "Restoran", "Rumah Makan"] else None,
                        "Kab_Kota": kab_kota,
                        "Kecamatan": kecamatan,
                        "Kelurahan_Desa": kelurahan_desa,
                        "Jenis_Kontak": jenis_kontak,
                        "Kontak": kontak,
                        "Gambar_URL": gambar_url,
                        "Bintang_Hotel": bintang_hotel if jenis_industri == "Hotel" else None,
                        "NIB_Available": nib_available == "Ya" if nib_available else None,
                        "NIB": nib if nib_available == "Ya" else None,
                        "CHSE": chse == "Ya" if chse else None,
                        "Dapur_Halal": dapur_halal == "Ya" if dapur_halal else None,
                        "Jumlah_Kursi": jumlah_kursi if jenis_industri in ["Restoran", "Rumah Makan"] else None,
                        "Sertifikat_Halal": sertifikat_halal == "Ya" if sertifikat_halal else None,
                        "Standar_Available": standar_available == "Ya" if standar_available else None,
                        "Sertifikat_Standar": sertifikat_standar if standar_available == "Ya" else None,
                        "Trapis_Available": trapis_available == "Ya" if trapis_available else None,
                        "Trapis": trapis if trapis_available == "Ya" else None,
                        "Jenis_Hiburan": jenis_hiburan if jenis_industri == "Usaha Hiburan" else None,
                        "Tanggal_Input": datetime.datetime.now().isoformat()
                    }
                    try:
                        res = requests.post(
                            f"{SUPABASE_URL}/rest/v1/Industri",
                            json=data_industri,
                            headers={
                                **headers,
                                "Content-Type": "application/json",
                                "Prefer": "return=minimal"
                            }
                        )
                        if res.status_code == 201:
                            show_notification("success", "Data industri berhasil dikirim ke Supabase!")
                            st.session_state.clear_form_industri = True
                            st.rerun()
                        else:
                            show_notification("error", f"Gagal kirim data: {res.text}")
                    except requests.RequestException as e:
                        show_notification("error", f"Gagal kirim data ke Supabase: {e}")
            except Exception as e:
                show_notification("error", f"Terjadi kesalahan: {e}")

# =======================
# 📁 UPLOAD EXCEL/CSV
# =======================
with tab3:
    st.subheader("📁 Upload File Excel/CSV")

    st.markdown("🎯 Upload file data destinasi/industri dalam format .xlsx atau .csv sesuai template.")

    uploaded_file = st.file_uploader("Unggah File Excel atau CSV", type=["xlsx", "csv"])

    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file, encoding="utf-8", errors="replace")
            else:
                df = pd.read_excel(uploaded_file, engine="openpyxl")

            # Konversi kolom boolean
            boolean_columns = ["NIB_Available", "Trapis_Available", "CHSE", "Dapur_Halal", "Sertifikat_Halal", "Standar_Available"]
            for col in boolean_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: True if str(x).lower() in ["true", "1", "ya"] else False if str(x).lower() in ["false", "0", "tidak"] else None)

            # Konversi kolom NIB, Sertifikat_Standar, Trapis ke string
            for col in ["NIB", "Sertifikat_Standar", "Trapis"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace("nan", None)

            st.write("📄 Preview Data:")
            st.dataframe(df)

            # Definisikan kolom yang diharapkan untuk masing-masing tabel
            destinasi_columns = set(["Nama", "Kab_Kota", "Kecamatan", "Kelurahan_Desa", "Deskripsi", "Fasilitas_Umum", "Jarak_Ibukota", "Pengelola", "Rating"])
            industri_columns = set([
                "Nama_Usaha", "Jenis_Industri", "Kab_Kota", "Kecamatan", "Kelurahan_Desa",
                "Karyawan_Pria", "Karyawan_Wanita", "Bintang_Hotel", "Jumlah_Kamar", "Jumlah_Bed",
                "Fasilitas", "Jenis_Kontak", "Kontak", "NIB_Available", "NIB", "CHSE",
                "Dapur_Halal", "Jumlah_Kursi", "Sertifikat_Halal", "Standar_Available",
                "Sertifikat_Standar", "Trapis_Available", "Trapis", "Jenis_Hiburan"
            ])

            # Ambil kolom dari file yang di-upload
            uploaded_columns = set(df.columns)

            # Tentukan tabel tujuan berdasarkan kolom
            if destinasi_columns.issubset(uploaded_columns):
                table_name = "Destinasi Wisata"
                jenis_data = "Destinasi"
                required_columns = list(destinasi_columns)
                validation_rules = {
                    "Nama": lambda x: not pd.isna(x) and isinstance(x, str) and x.strip() != "",
                    "Kab_Kota": lambda x: not pd.isna(x) and isinstance(x, str) and x.strip() != "",
                    "Kecamatan": lambda x: not pd.isna(x) and isinstance(x, str) and x.strip() != "",
                    "Kelurahan_Desa": lambda x: not pd.isna(x) and isinstance(x, str) and x.strip() != "",
                    "Deskripsi": lambda x: not pd.isna(x) and isinstance(x, str) and x.strip() != "",
                    "Fasilitas_Umum": lambda x: pd.isna(x) or isinstance(x, str),
                    "Jarak_Ibukota": lambda x: pd.isna(x) or isinstance(x, str),
                    "Pengelola": lambda x: not pd.isna(x) and isinstance(x, str) and x in ["Pemerintah", "Swasta", "Lainnya"],
                    "Rating": lambda x: not pd.isna(x) and isinstance(x, (int, float)) and 1 <= x <= 10
                }
            elif industri_columns.issubset(uploaded_columns):
                table_name = "Industri"
                jenis_data = "Industri"
                required_columns = list(industri_columns)
                validation_rules = {
                    "Nama_Usaha": lambda x: not pd.isna(x) and isinstance(x, str) and x.strip() != "",
                    "Jenis_Industri": lambda x: not pd.isna(x) and isinstance(x, str) and x in ["Travel", "Hotel", "Wisma", "Villa", "Homestay", "Restoran", "Rumah Makan", "Catering", "Spa", "Usaha Hiburan"],
                    "Kab_Kota": lambda x: not pd.isna(x) and isinstance(x, str) and x.strip() != "",
                    "Kecamatan": lambda x: not pd.isna(x) and isinstance(x, str) and x.strip() != "",
                    "Kelurahan_Desa": lambda x: not pd.isna(x) and isinstance(x, str) and x.strip() != "",
                    "Karyawan_Pria": lambda x: not pd.isna(x) and isinstance(x, (int, float)) and x >= 0,
                    "Karyawan_Wanita": lambda x: not pd.isna(x) and isinstance(x, (int, float)) and x >= 0,
                    "Bintang_Hotel": lambda x: pd.isna(x) or (isinstance(x, (int, float)) and x >= 0),
                    "Jumlah_Kamar": lambda x: pd.isna(x) or (isinstance(x, (int, float)) and x >= 0),
                    "Jumlah_Bed": lambda x: pd.isna(x) or (isinstance(x, (int, float)) and x >= 0),
                    "Fasilitas": lambda x: pd.isna(x) or isinstance(x, str),
                    "Jenis_Kontak": lambda x: not pd.isna(x) and isinstance(x, str) and x.strip() != "",
                    "Kontak": lambda x: not pd.isna(x) and str(x).strip() != "",
                    "NIB_Available": lambda x: pd.isna(x) or x in [True, False],
                    "NIB": lambda x: pd.isna(x) or isinstance(x, (str, int, float)),
                    "CHSE": lambda x: pd.isna(x) or x in [True, False],
                    "Dapur_Halal": lambda x: pd.isna(x) or x in [True, False],
                    "Jumlah_Kursi": lambda x: pd.isna(x) or (isinstance(x, (int, float)) and x >= 0),
                    "Sertifikat_Halal": lambda x: pd.isna(x) or x in [True, False],
                    "Standar_Available": lambda x: pd.isna(x) or x in [True, False],
                    "Sertifikat_Standar": lambda x: pd.isna(x) or isinstance(x, (str, int, float)),
                    "Trapis_Available": lambda x: pd.isna(x) or x in [True, False],
                    "Trapis": lambda x: pd.isna(x) or isinstance(x, (str, int, float)),
                    "Jenis_Hiburan": lambda x: pd.isna(x) or x in ["Club Malam", "Karaoke", "Diskotik", "Billiard", ""]
                }
            else:
                show_notification("error", "Kolom file tidak sesuai dengan template Destinasi (" + ", ".join(destinasi_columns) + ") atau Industri (" + ", ".join(industri_columns) + ")")
                table_name = None
                jenis_data = None
                required_columns = []
                validation_rules = {}

            if table_name:
                # Validasi data
                validation_errors = []
                for index, row in df.iterrows():
                    for col, rule in validation_rules.items():
                        value = row[col]
                        if not rule(value):
                            validation_errors.append(f"Baris {index + 2}, Kolom {col}: Nilai tidak valid ({value})")
                    # Validasi tambahan untuk Industri
                    if table_name == "Industri":
                        jenis_industri = row["Jenis_Industri"]
                        if jenis_industri in ["Hotel", "Wisma", "Villa", "Homestay"]:
                            if pd.isna(row["Dapur_Halal"]) or pd.isna(row["NIB_Available"]) or pd.isna(row["CHSE"]) or pd.isna(row["Fasilitas"]) or pd.isna(row["Jumlah_Kamar"]) or pd.isna(row["Jumlah_Bed"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom Dapur_Halal, NIB_Available, CHSE, Fasilitas, Jumlah_Kamar, dan Jumlah_Bed wajib diisi untuk {jenis_industri}")
                            if row["NIB_Available"] and pd.isna(row["NIB"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom NIB wajib diisi jika NIB_Available adalah True")
                        if jenis_industri in ["Restoran", "Rumah Makan"]:
                            if pd.isna(row["NIB_Available"]) or pd.isna(row["CHSE"]) or pd.isna(row["Fasilitas"]) or pd.isna(row["Jumlah_Kursi"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom NIB_Available, CHSE, Fasilitas, dan Jumlah_Kursi wajib diisi untuk {jenis_industri}")
                            if row["NIB_Available"] and pd.isna(row["NIB"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom NIB wajib diisi jika NIB_Available adalah True")
                        if jenis_industri == "Spa":
                            if pd.isna(row["NIB_Available"]) or pd.isna(row["Standar_Available"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom NIB_Available dan Standar_Available wajib diisi untuk Spa")
                            if row["NIB_Available"] and pd.isna(row["NIB"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom NIB wajib diisi jika NIB_Available adalah True")
                            if row["Standar_Available"] and pd.isna(row["Sertifikat_Standar"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom Sertifikat_Standar wajib diisi jika Standar_Available adalah True")
                        if jenis_industri == "Catering":
                            if pd.isna(row["NIB_Available"]) or pd.isna(row["Trapis_Available"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom NIB_Available dan Trapis_Available wajib diisi untuk Catering")
                            if row["NIB_Available"] and pd.isna(row["NIB"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom NIB wajib diisi jika NIB_Available adalah True")
                            if row["Trapis_Available"] and pd.isna(row["Trapis"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom Trapis wajib diisi jika Trapis_Available adalah True")
                        if jenis_industri == "Travel":
                            if pd.isna(row["NIB_Available"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom NIB_Available wajib diisi untuk Travel")
                            if row["NIB_Available"] and pd.isna(row["NIB"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom NIB wajib diisi jika NIB_Available adalah True")
                        if jenis_industri == "Usaha Hiburan":
                            if pd.isna(row["NIB_Available"]) or pd.isna(row["Standar_Available"]) or pd.isna(row["Jenis_Hiburan"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom NIB_Available, Standar_Available, dan Jenis_Hiburan wajib diisi untuk Usaha Hiburan")
                            if row["NIB_Available"] and pd.isna(row["NIB"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom NIB wajib diisi jika NIB_Available adalah True")
                            if row["Standar_Available"] and pd.isna(row["Sertifikat_Standar"]):
                                validation_errors.append(f"Baris {index + 2}: Kolom Sertifikat_Standar wajib diisi jika Standar_Available adalah True")

                if validation_errors:
                    show_notification("error", "Validasi gagal:\n" + "\n".join(validation_errors))
                else:
                    show_notification("success", f"Struktur file valid untuk {jenis_data}! Siap dikirim ke database.")

                    if st.button(f"Kirim Data ke Database"):
                        df["Tanggal_Input"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        if table_name == "Industri":
                            df["Karyawan_Pria"] = df["Karyawan_Pria"].astype("Int64")
                            df["Karyawan_Wanita"] = df["Karyawan_Wanita"].astype("Int64")
                            if "Jumlah_Kamar" in df.columns:
                                df["Jumlah_Kamar"] = df["Jumlah_Kamar"].astype("Int64")
                            if "Jumlah_Bed" in df.columns:
                                df["Jumlah_Bed"] = df["Jumlah_Bed"].astype("Int64")
                            if "Bintang_Hotel" in df.columns:
                                df["Bintang_Hotel"] = df["Bintang_Hotel"].astype("Int64")
                            if "Jumlah_Kursi" in df.columns:
                                df["Jumlah_Kursi"] = df["Jumlah_Kursi"].astype("Int64")

                        df = df.where(pd.notnull(df), None)  # Replace NaN with None
                        data = df.to_dict(orient="records")

                        try:
                            res = requests.post(
                                f"{SUPABASE_URL}/rest/v1/{table_name}",
                                data=json.dumps(data, ignore_nan=True),
                                headers={
                                    "apikey": SUPABASE_API_KEY,
                                    "Authorization": f"Bearer {SUPABASE_API_KEY}",
                                    "Content-Type": "application/json",
                                    "Prefer": "return=representation"
                                }
                            )
                            if res.status_code == 201:
                                show_notification("success", "Data berhasil dikirim ke Supabase!")
                            else:
                                error_message = res.json().get("message", res.text) if res.text else "Unknown error"
                                show_notification("error", f"Gagal kirim data: {res.status_code} - {error_message}")
                        except requests.RequestException as e:
                            show_notification("error", f"Gagal kirim data ke Supabase: {str(e)}")

            # Download ulang file sebagai Excel
            towrite = io.BytesIO()
            df.to_excel(towrite, index=False, engine='openpyxl')
            towrite.seek(0)
            st.download_button(
                label="📥 Download Ulang File (Excel)",
                data=towrite,
                file_name="data_upload.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except UnicodeDecodeError:
            show_notification("error", "Gagal membaca file CSV: Encoding tidak didukung. Harap gunakan encoding UTF-8.")
        except Exception as e:
            show_notification("error", f"Terjadi kesalahan saat membaca file: {str(e)}")

    st.markdown("💾 Belum punya template? Silakan download:")
    industri_template = pd.DataFrame(columns=[
        "Nama_Usaha", "Jenis_Industri", "Kab_Kota", "Kecamatan", "Kelurahan_Desa",
        "Karyawan_Pria", "Karyawan_Wanita", "Bintang_Hotel", "Jumlah_Kamar", "Jumlah_Bed",
        "Fasilitas", "Jenis_Kontak", "Kontak", "NIB_Available", "NIB", "CHSE",
        "Dapur_Halal", "Jumlah_Kursi", "Sertifikat_Halal", "Standar_Available",
        "Sertifikat_Standar", "Trapis_Available", "Trapis", "Jenis_Hiburan"
    ])
    buffer_industri = io.BytesIO()
    industri_template.to_excel(buffer_industri, index=False, engine='openpyxl')
    buffer_industri.seek(0)
    st.download_button(
        label="🏨 Template Industri (Excel)",
        data=buffer_industri,
        file_name="template_industri.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# =======================
# 📈 PROGRES UPLOAD DATA (Hanya untuk Admin)
# =======================
if is_admin:
    with tab4:
        st.subheader("📈 Progres Upload Data per Kabupaten/Kota")

        kabupaten_list = get_all_kabupaten()
        if not kabupaten_list:
            st.error("Gagal mengambil daftar kabupaten/kota.")
            st.stop()

        # Normalisasi daftar kabupaten untuk pencocokan
        normalized_kabupaten_list = [kab.lower().replace("kabupaten ", "").replace("kab. ", "").strip() for kab in kabupaten_list]

        # Hitung jumlah data dengan mempertimbangkan variasi penulisan
        destinasi_counts = {}
        industri_counts = {}
        for kab, norm_kab in zip(kabupaten_list, normalized_kabupaten_list):
            # Gunakan ilike dengan pola *nama_kabupaten*
            query_destinasi = f"Kab_Kota=ilike.*{urllib.parse.quote(norm_kab)}*"
            query_industri = f"Kab_Kota=ilike.*{urllib.parse.quote(norm_kab)}*"

            try:
                # Hitung untuk Destinasi Wisata
                res_destinasi = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Destinasi%20Wisata?{query_destinasi}&select=count",
                    headers={
                        "apikey": SUPABASE_API_KEY,
                        "Authorization": f"Bearer {SUPABASE_API_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                if res_destinasi.status_code == 200:
                    count_data = res_destinasi.json()
                    destinasi_counts[kab] = count_data[0]["count"] if count_data else 0
                else:
                    destinasi_counts[kab] = 0

                # Hitung untuk Industri
                res_industri = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Industri?{query_industri}&select=count",
                    headers={
                        "apikey": SUPABASE_API_KEY,
                        "Authorization": f"Bearer {SUPABASE_API_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                if res_industri.status_code == 200:
                    count_data = res_industri.json()
                    industri_counts[kab] = count_data[0]["count"] if count_data else 0
                else:
                    industri_counts[kab] = 0

            except Exception:
                destinasi_counts[kab] = 0
                industri_counts[kab] = 0

        progres_data = {
            "Kabupaten_Kota": kabupaten_list,
            "Jumlah_Destinasi_Wisata": [destinasi_counts[kab] for kab in kabupaten_list],
            "Jumlah_Industri": [industri_counts[kab] for kab in kabupaten_list]
        }
        progres_df = pd.DataFrame(progres_data)

        st.write("**Tabel Progres Upload Data**")
        st.dataframe(progres_df, use_container_width=True)

        total_destinasi = progres_df["Jumlah_Destinasi_Wisata"].sum()
        total_industri = progres_df["Jumlah_Industri"].sum()
        total_kabupaten = len(kabupaten_list)
        kabupaten_with_data = len(progres_df[(progres_df["Jumlah_Destinasi_Wisata"] > 0) | (progres_df["Jumlah_Industri"] > 0)])
        percentage = (kabupaten_with_data / total_kabupaten * 100) if total_kabupaten > 0 else 0

        st.write("**Statistik Ringkas**")
        st.write(f"Total Destinasi Wisata: {total_destinasi}")
        st.write(f"Total Industri: {total_industri}")
        st.write(f"Persentase Kabupaten/Kota yang Mengunggah: {percentage:.2f}%")