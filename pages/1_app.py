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
                st.error("❌ Sesi tidak valid. Silakan login kembali.")
                st.switch_page("pages/0_login.py")
                st.stop()
        else:
            # Jika token tidak valid, hapus sesi dan arahkan ke login
            st.session_state.pop('user_email', None)
            st.session_state.pop('kabupaten', None)
            st.session_state.pop('auth_token', None)
            st.error("❌ Sesi telah kedaluwarsa. Silakan login kembali.")
            st.switch_page("pages/0_login.py")
            st.stop()
    else:
        # Jika tidak ada token, arahkan ke login
        st.error("❌ Anda harus login terlebih dahulu!")
        st.switch_page("pages/0_login.py")
        st.stop()

# ==============================
# 🔐 Konfigurasi Supabase (sementara pakai secrets)
# ==============================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_API_KEY = st.secrets["SUPABASE_API_KEY"]
except KeyError as e:
    st.error(f"❌ Missing secret: {e}")
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
        kabupaten_kota = ""
        kecamatan = ""
        kelurahan_desa = ""
        deskripsi = ""
        rating = 5
        gambar = None
        st.session_state.form_destinasi_reset = False
    else:
        nama = st.session_state.get("nama", "")
        kabupaten_kota = st.session_state.get("kabupaten_kota", "")
        kecamatan = st.session_state.get("kecamatan", "")
        kelurahan_desa = st.session_state.get("kelurahan_desa", "")
        deskripsi = st.session_state.get("deskripsi", "")
        rating = st.session_state.get("rating", 5)
        gambar = None

    with st.form("form_destinasi"):
        with col1:
            nama = st.text_input("Nama Destinasi", value=nama, placeholder="Masukkan Nama Destinasi", key="nama_input")
            kabupaten_kota = st.text_input("Kabupaten/Kota", value=kabupaten_kota, placeholder="Masukkan Kabupaten/Kota", key="kabupaten_kota_input")
            kecamatan = st.text_input("Kecamatan", value=kecamatan, placeholder="Masukkan Kecamatan", key="kecamatan_input")
            kelurahan_desa = st.text_input("Kelurahan/Desa", value=kelurahan_desa, placeholder="Masukkan Kelurahan/Desa", key="kelurahan_desa_input")

        with col2:
            deskripsi = st.text_area("Deskripsi Destinasi", value=deskripsi, placeholder="Masukkan Deskripsi Destinasi Wisata Anda Contoh : Pulau ini dengan daya tarik keindahan pasir putih dan air laut yang jernih beserta pepohonan yang rindang", key="deskripsi_input")
            rating = st.slider("Rating Potensi (1-10)", 1, 10, value=rating, key="rating_input")
            gambar = st.file_uploader("Upload Gambar Destinasi", type=["jpg", "jpeg", "png"], key="gambar_input")

        submit_destinasi = st.form_submit_button("Kirim Data")

    if submit_destinasi:
        # Validasi semua kolom wajib, termasuk gambar
        if not all([nama.strip(), kabupaten_kota.strip(), kecamatan.strip(), kelurahan_desa.strip(), deskripsi.strip()]) or gambar is None:
            show_notification("warning", "⚠️ Harap isi semua kolom wajib sebelum mengirim, termasuk gambar.")
        else:
            try:
                if gambar.size > 50 * 1024 * 1024:
                    show_notification("warning", "❌ Ukuran file terlalu besar! Maksimum 50MB.")
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
                            show_notification("error", f"❌ Gagal upload gambar: {res_upload.text}")
                            gambar_url = None
                    except requests.RequestException as e:
                        show_notification("error", f"❌ Gagal upload gambar: {e}")
                        gambar_url = None

                    # Jika gambar gagal diunggah, hentikan proses
                    if gambar_url is None:
                        show_notification("error", "❌ Gagal mengunggah gambar. Data tidak dikirim.")
                    else:
                        data = {
                            "Nama": nama,
                            "Kab/Kota": kabupaten_kota,
                            "Kecamatan": kecamatan,
                            "Kelurahan/Desa": kelurahan_desa,
                            "Deskripsi": deskripsi,
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
                                show_notification("success", "✅ Data berhasil dikirim ke Supabase!")
                                st.session_state.form_destinasi_reset = True
                                st.rerun()
                            else:
                                show_notification("error", f"❌ Gagal kirim data: {res.text}")
                        except requests.RequestException as e:
                            show_notification("error", f"❌ Gagal kirim data ke Supabase: {e}")
            except Exception as e:
                show_notification("error", f"❌ Terjadi kesalahan: {e}")

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
        jumlah_karyawan = 0
        alamat_usaha = ""
        gambar_industri = None
        bintang_hotel = 0  # Tambahkan default untuk bintang_hotel
    else:
        nama_usaha = st.session_state.get("nama_usaha", "")
        jenis_industri = st.session_state.get("jenis_industri", None)
        jumlah_kamar = st.session_state.get("jumlah_kamar", 0)
        fasilitas = st.session_state.get("fasilitas", "")
        jenis_kontak = st.session_state.get("jenis_kontak", None)
        kontak = st.session_state.get("kontak", "")
        jumlah_karyawan = st.session_state.get("jumlah_karyawan", 0)
        alamat_usaha = st.session_state.get("alamat_usaha", "")
        gambar_industri = None
        bintang_hotel = st.session_state.get("bintang_hotel", 0)  # Tambahkan ke session state

    col1, col2 = st.columns(2)

    with st.form("form_industri"):
        with col1:
            nama_usaha = st.text_input("Nama Usaha", value=nama_usaha, placeholder="Masukkan Nama Usaha", key="nama_usaha_input")
            jenis_industri = st.selectbox("Jenis Industri", ["Travel", "Hotel", "Penginapan", "Villa", "Homestay", "Restoran", "Rumah Makan", "Catering", "Spa", "Fitness", "Hiburan Malam"], index=None, placeholder="Pilih Jenis Industri", key="jenis_industri_input")
            jumlah_kamar = None
            fasilitas = None
            if jenis_industri in ["Hotel", "Penginapan", "Villa", "Homestay"]:
                jumlah_kamar = st.number_input("Jumlah Kamar", value=jumlah_kamar, min_value=0, key="jumlah_kamar_input")
                fasilitas = st.text_input("Fasilitas", value=fasilitas, placeholder="Masukkan Fasilitas Tersedia", key="fasilitas_input")
            # Tambahkan slider untuk Bintang Hotel jika Jenis Industri adalah Hotel
            bintang_hotel = None
            if jenis_industri == "Hotel":
                bintang_hotel = st.slider("Jumlah Bintang Hotel (0-5)", 0, 5, value=bintang_hotel, key="bintang_hotel_input")

        with col2:
            jenis_kontak = st.selectbox("Jenis Kontak", options=["Whatsapp", "Instagram", "Email"], index=None, placeholder="Pilih Jenis Kontak", key="jenis_kontak_input")
            kontak = st.text_input(f"{jenis_kontak}", value=kontak, placeholder=f"Masukkan {jenis_kontak}" if jenis_kontak else "", key="kontak_input") if jenis_kontak else None
            jumlah_karyawan = st.number_input("Jumlah Karyawan", value=jumlah_karyawan, min_value=0, key="jumlah_karyawan_input")
            alamat_usaha = st.text_area("Alamat Usaha", value=alamat_usaha, key="alamat_usaha_input")
            gambar_industri = st.file_uploader("Upload Gambar Usaha", type=["jpg", "jpeg", "png"], key="gambar_industri_input")

        submit_industri = st.form_submit_button("Kirim Data Industri")

    if submit_industri:
        required_fields = [nama_usaha.strip() if nama_usaha else "", jenis_industri, jenis_kontak, kontak.strip() if kontak else "", alamat_usaha.strip() if alamat_usaha else ""]
        if not all(required_fields) or jumlah_karyawan <= 0:
            show_notification("warning", "⚠️ Semua kolom wajib diisi. Gambar opsional.")
        else:
            try:
                check_industri = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Industri?Nama_Usaha=eq.{urllib.parse.quote(nama_usaha)}",
                    headers=headers
                )
                if check_industri.status_code == 200 and check_industri.json():
                    show_notification("warning", "⚠️ Data dengan nama usaha ini sudah ada di database!")
                elif gambar_industri and gambar_industri.size > 50 * 1024 * 1024:
                    show_notification("warning", "❌ Ukuran file terlalu besar! Maksimum 50MB.")
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
                                show_notification("error", f"❌ Gagal upload gambar: {res_upload.text}")
                                gambar_url = None
                        except requests.RequestException as e:
                            show_notification("error", f"❌ Gagal upload gambar: {e}")
                            gambar_url = None

                    data_industri = {
                        "Nama_Usaha": nama_usaha,
                        "Jenis_Industri": jenis_industri,
                        "Jumlah_Karyawan": jumlah_karyawan,
                        "Jumlah_Kamar": jumlah_kamar,
                        "Fasilitas": fasilitas,
                        "Alamat": alamat_usaha,
                        "Jenis_Kontak": jenis_kontak,
                        "Kontak": kontak,
                        "Gambar_URL": gambar_url,
                        "Bintang_Hotel": bintang_hotel,  # Tambahkan kolom Bintang_Hotel
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
                            show_notification("success", "✅ Data industri successfully sent to Supabase!")
                            st.session_state.clear_form_industri = True
                            st.rerun()
                        else:
                            show_notification("error", f"❌ Failed to send data: {res.text}")
                    except requests.RequestException as e:
                        show_notification("error", f"❌ Gagal kirim data ke Supabase: {e}")
            except Exception as e:
                show_notification("error", f"❌ An error occurred: {e}")

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
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.write("📄 Preview Data:")
            st.dataframe(df)

            # Definisikan kolom yang diharapkan untuk masing-masing tabel
            destinasi_columns = set(["Nama", "Kab/Kota", "Kecamatan", "Kelurahan/Desa", "Deskripsi", "Rating"])
            industri_columns = set([
                "Nama_Usaha", "Jenis_Industri", "Alamat",
                "Jumlah_Karyawan", "Jumlah_Kamar", "Fasilitas",
                "Jenis_Kontak", "Kontak"
            ])

            # Ambil kolom dari file yang di-upload
            uploaded_columns = set(df.columns)

            # Tentukan tabel tujuan berdasarkan kolom
            if uploaded_columns == destinasi_columns:
                table_name = "Destinasi Wisata"
                jenis_data = "Destinasi"
                required_columns = list(destinasi_columns)
                validation_rules = {
                    "Nama": lambda x: isinstance(x, str) and x.strip() != "",
                    "Kab/Kota": lambda x: isinstance(x, str) and x.strip() != "",
                    "Kecamatan": lambda x: isinstance(x, str) and x.strip() != "",
                    "Kelurahan/Desa": lambda x: isinstance(x, str) and x.strip() != "",
                    "Deskripsi": lambda x: isinstance(x, str) and x.strip() != "",
                    "Rating": lambda x: isinstance(x, (int, float)) and 1 <= x <= 10
                }
            elif uploaded_columns == industri_columns:
                table_name = "Industri"
                jenis_data = "Industri"
                required_columns = list(industri_columns)
                validation_rules = {
                    "Nama_Usaha": lambda x: isinstance(x, str) and x.strip() != "",
                    "Jenis_Industri": lambda x: isinstance(x, str) and x.strip() != "",
                    "Alamat": lambda x: isinstance(x, str) and x.strip() != "",
                    "Jumlah_Karyawan": lambda x: isinstance(x, (int, float)) and x >= 0,
                    "Jumlah_Kamar": lambda x: pd.isna(x) or (isinstance(x, (int, float)) and x >= 0),
                    "Fasilitas": lambda x: pd.isna(x) or isinstance(x, str),
                    "Jenis_Kontak": lambda x: isinstance(x, str) and x.strip() != "",
                    "Kontak": lambda x: isinstance(x, str) and x.strip() != ""
                }
            else:
                show_notification("error", "❌ Kolom file tidak sesuai dengan template Destinasi atau Industri!")
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
                
                if validation_errors:
                    show_notification("error", "❌ Validasi gagal:\n" + "\n".join(validation_errors))
                else:
                    show_notification("success", f"✅ Struktur file valid untuk {jenis_data}! Siap dikirim ke database.")

                    if st.button(f"Kirim Data ke Database"):
                        df["Tanggal_Input"] = datetime.datetime.now().isoformat()
                        if table_name == "Industri":
                            df["Jumlah_Karyawan"] = df["Jumlah_Karyawan"].astype("Int64")
                            if "Jumlah_Kamar" in df.columns:
                                df["Jumlah_Kamar"] = df["Jumlah_Kamar"].astype("Int64")

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
                                show_notification("success", "✅ Data berhasil dikirim ke Supabase!")
                            else:
                                show_notification("error", f"❌ Gagal kirim data: {res.text}")
                        except requests.RequestException as e:
                            show_notification("error", f"❌ Gagal kirim data ke Supabase: {e}")

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

        except Exception as e:
            show_notification("error", f"❌ Terjadi kesalahan saat membaca file: {str(e)}")
            st.rerun()

    st.markdown("💾 Belum punya template? Silakan download:")
    col1, col2 = st.columns(2)
    with col1:
        destinasi_template = pd.DataFrame(columns=["Nama", "Kab/Kota", "Kecamatan", "Kelurahan/Desa", "Deskripsi", "Rating"])
        buffer_destinasi = io.BytesIO()
        destinasi_template.to_excel(buffer_destinasi, index=False, engine='openpyxl')
        buffer_destinasi.seek(0)
        st.download_button("📄 Template Destinasi (Excel)", buffer_destinasi, file_name="template_destinasi.xlsx")

    with col2:
        industri_template = pd.DataFrame(columns=[
            "Nama_Usaha", "Jenis_Industri", "Alamat",
            "Jumlah_Karyawan", "Jumlah_Kamar", "Fasilitas",
            "Jenis_Kontak", "Kontak"])
        buffer_industri = io.BytesIO()
        industri_template.to_excel(buffer_industri, index=False, engine='openpyxl')
        buffer_industri.seek(0)
        st.download_button("🏨 Template Industri (Excel)", buffer_industri, file_name="template_industri.xlsx")
        
# =======================
# 📈 PROGRES UPLOAD DATA (Hanya untuk Admin)
# =======================
if is_admin:
    with tab4:
        st.subheader("📈 Progres Upload Data per Kabupaten/Kota")

        # Ambil daftar semua kabupaten/kota
        kabupaten_list = get_all_kabupaten()
        if not kabupaten_list:
            st.error("❌ Gagal mengambil daftar kabupaten/kota.")
            st.stop()

        # Ambil jumlah entri dari Destinasi Wisata dan Industri
        destinasi_counts = get_count_by_kabupaten("Destinasi%20Wisata", kabupaten_list)
        industri_counts = get_count_by_kabupaten("Industri", kabupaten_list)

        # Buat DataFrame untuk tabel progres
        progres_data = {
            "Kabupaten/Kota": kabupaten_list,
            "Jumlah Destinasi Wisata": [destinasi_counts[kab] for kab in kabupaten_list],
            "Jumlah Industri": [industri_counts[kab] for kab in kabupaten_list]
        }
        progres_df = pd.DataFrame(progres_data)

        # Tampilkan tabel progres
        st.write("**Tabel Progres Upload Data**")
        st.dataframe(progres_df, use_container_width=True)

        # Statistik Ringkas
        total_destinasi = progres_df["Jumlah Destinasi Wisata"].sum()
        total_industri = progres_df["Jumlah Industri"].sum()
        total_kabupaten = len(kabupaten_list)
        kabupaten_with_data = len(progres_df[(progres_df["Jumlah Destinasi Wisata"] > 0) | (progres_df["Jumlah Industri"] > 0)])
        percentage = (kabupaten_with_data / total_kabupaten * 100) if total_kabupaten > 0 else 0

        st.write("**Statistik Ringkas**")
        st.write(f"Total Destinasi Wisata: {total_destinasi}")
        st.write(f"Total Industri: {total_industri}")
        st.write(f"Persentase Kabupaten/Kota yang Mengunggah: {percentage:.2f}%")