import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import folium
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import datetime
import math
from folium.plugins import Fullscreen

# ==========================================
# 1. KONFIGURASI HALAMAN & STYLE
# ==========================================
st.set_page_config(page_title="SPMB SDN Pati Kidul 01", layout="centered")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
    html, body, [class*="css"], .stMarkdown, .stButton, .stTextInput {
        font-family: 'Poppins', sans-serif !important;
    }
    [data-testid="stMetricLabel"] { font-size: 14px !important; font-weight: 600 !important; }
    [data-testid="stMetricValue"] { font-size: 18px !important; white-space: nowrap !important; }
    [data-testid="stMetric"] { padding: 8px !important; background-color: #f8f9fa; border-radius: 10px; border: 1px solid #eee; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Coordinate Mapping for Pati Districts ---
KOORDINAT_KECAMATAN = {
    "Pati": [-6.7559, 111.0380], "Batangan": [-6.7333, 111.1833], "Cluwak": [-6.5500, 110.9833],
    "Dukuhseti": [-6.4500, 111.0500], "Gabus": [-6.8167, 111.0500], "Gembong": [-6.6833, 110.9500],
    "Gunungwungkal": [-6.6000, 110.9833], "Jaken": [-6.7667, 111.2000], "Jakenan": [-6.7667, 111.1333],
    "Juwana": [-6.7161, 111.1506], "Kayen": [-6.9111, 111.0114], "Margorejo": [-6.7622, 110.9856],
    "Margoyoso": [-6.5833, 111.0333], "Pucakwangi": [-6.8167, 111.1500], "Sukolilo": [-6.9167, 110.9333],
    "Tambakromo": [-6.8500, 111.0167], "Tayu": [-6.5397, 111.0483], "Tlogowungu": [-6.6833, 111.0167],
    "Trangkil": [-6.6500, 111.0500], "Wedarijaksa": [-6.6833, 111.0833], "Winong": [-6.8333, 111.0833]
}

# ==========================================
# 2. FUNGSI LOGIKA
# ==========================================


@st.cache_data(ttl=60)
def ambil_data_rekaman(_sheet):
    return _sheet.get_all_records()


def hitung_jarak(koor_siswa):
    lat_sek, lon_sek = -6.7516, 111.0321
    try:
        lat_sis, lon_sis = map(float, str(koor_siswa).split(","))
        R = 6371
        dlat = math.radians(lat_sis - lat_sek)
        dlon = math.radians(lon_sis - lon_sek)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat_sek)) * \
            math.cos(math.radians(lat_sis)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return round(R * c, 2)
    except:
        return 0


def hitung_usia_detail(tgl_lahir_str):
    try:
        target = datetime.date(2026, 7, 1)
        tgl_lahir = datetime.datetime.strptime(
            str(tgl_lahir_str), "%Y-%m-%d").date()
        tahun = target.year - tgl_lahir.year
        if target.month >= tgl_lahir.month:
            bulan = target.month - tgl_lahir.month
        else:
            tahun -= 1
            bulan = 12 + target.month - tgl_lahir.month
        if target.day < tgl_lahir.day:
            bulan -= 1
            if bulan < 0:
                tahun -= 1
                bulan = 11
        return f"{tahun} Thn, {bulan} Bln"
    except:
        return "-"


def hitung_skor_indeks(tgl_lahir_str, koordinat):
    try:
        target = datetime.date(2026, 7, 1)
        tgl_lahir = datetime.datetime.strptime(
            str(tgl_lahir_str), "%Y-%m-%d").date()
        total_hari = (target - tgl_lahir).days
        jarak = hitung_jarak(koordinat)
        bonus_jarak = 1 / (jarak + 0.01)
        return round(total_hari + bonus_jarak, 4)
    except:
        return 0


def buat_pdf_pendaftaran(nama, nik, tgl_lahir, asal, koor):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "BUKTI PENDAFTARAN SISWA BARU", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, "SDN PATI KIDUL 01", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(50, 10, f"Nama: {nama}", ln=True)
    pdf.cell(50, 10, f"NIK: {nik}", ln=True)
    pdf.cell(50, 10, f"Tgl Lahir: {tgl_lahir}", ln=True)
    pdf.cell(50, 10, f"Asal Sekolah: {asal}", ln=True)
    pdf.multi_cell(0, 10, f"Koordinat: {koor}")
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(
        0, 10, f"Dicetak pada: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", align='R')
    return pdf.output(dest='S').encode('latin-1')


def cetak_peringkat_pdf(df_sorted):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "LAPORAN HASIL PEMERINGKATAN SPMB", ln=True, align='C')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "SDN PATI KIDUL 01 - TAHUN PELAJARAN 2026/2027",
             ln=True, align='C')
    pdf.ln(10)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(15, 10, "Peringkat", 1, 0, 'C', True)
    pdf.cell(80, 10, "Nama Lengkap", 1, 0, 'C', True)
    pdf.cell(50, 10, "Usia", 1, 0, 'C', True)
    pdf.cell(45, 10, "Jarak", 1, 1, 'C', True)
    pdf.set_font("Arial", '', 10)
    for index, row in df_sorted.iterrows():
        pdf.cell(15, 8, str(row['Peringkat']), 1, 0, 'C')
        pdf.cell(80, 8, str(row['Nama'])[:35], 1, 0, 'L')
        pdf.cell(50, 8, str(row['Usia']), 1, 0, 'C')
        pdf.cell(45, 8, str(row['Jarak']), 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')


# ==========================================
# 3. KONEKSI GOOGLE SHEETS (ST.SECRETS)
# ==========================================
scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]


@st.cache_resource
def init_gspread_connection():
    gcp_credentials = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(
        gcp_credentials, scopes=scope)
    client = gspread.authorize(creds)
    return client.open("SPMB_SDN_Pati_Kidul_01")


try:
    spreadsheet = init_gspread_connection()
    sheet = spreadsheet.sheet1
    sheet_set = spreadsheet.worksheet("Pengaturan")
except Exception as e:
    st.error(f"Koneksi Gagal: {e}")
    st.stop()

# ==========================================
# 4. NAVIGASI SIDEBAR
# ==========================================
menu = st.sidebar.selectbox("Menu Utama", [
                            "Pendaftaran Baru", "Login Akun Siswa", "Hasil Pemeringkatan", "Admin SPMB"])

# ------------------------------------------
# MENU: PENDAFTARAN BARU
# ------------------------------------------
if menu == "Pendaftaran Baru":
    st.title("📝 Pendaftaran Siswa")
    st.info("Harap isi data dengan lengkap. Peta akan otomatis bergeser sesuai Kecamatan yang Anda pilih.")

    nama = st.text_input("Nama Lengkap")
    nik = st.text_input("NIK (16 Digit)", max_chars=16)
    password = st.text_input("Password Akun", type="password")
    tanggal_lahir = st.date_input(
        "Tanggal Lahir", min_value=datetime.date(2015, 1, 1))
    asal_sekolah = st.text_input("Asal TK")

    st.markdown("#### 📍 Data Alamat")
    jenis_alamat = st.selectbox("Jenis Alamat", options=[
                                "Rumah", "Domisili", "Kantor"])

    # Warning feature for specific address types
    if jenis_alamat in ["Domisili", "Kantor"]:
        st.info("ℹ️ Catatan: Mohon menyertakan surat keterangan domisili dari desa/kelurahan atau surat keterangan kerja dari instansi terkait saat verifikasi berkas offline.")

    col1, col2 = st.columns(2)
    with col1:
        kabupaten = st.text_input("Kabupaten", value="Pati", disabled=True)
        kecamatan = st.selectbox(
            "Kecamatan", options=list(KOORDINAT_KECAMATAN.keys()))
    with col2:
        desa = st.text_input("Desa / Kelurahan")
        col_rt, col_rw = st.columns(2)
        with col_rt:
            rt = st.text_input("RT", max_chars=3)
        with col_rw:
            rw = st.text_input("RW", max_chars=3)

    st.markdown("#### 🗺️ Titik Lokasi (Klik pada peta)")

    map_center = KOORDINAT_KECAMATAN.get(kecamatan, [-6.7516, 111.0321])
    m = folium.Map(location=map_center, zoom_start=14)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite').add_to(m)
    m.add_child(folium.LatLngPopup())

    map_data = st_folium(m, height=350, width="stretch")
    submit = st.button("Daftar Sekarang", type="primary", width="stretch")

    if submit:
        koordinat = f"{map_data['last_clicked']['lat']}, {map_data['last_clicked']['lng']}" if map_data and map_data['last_clicked'] else ""

        if not (nama and nik and desa and rt and rw and koordinat):
            st.error(
                "Lengkapi semua data (termasuk RT/RW/Desa) dan pilih titik lokasi di peta!")
        else:
            list_nik = sheet.col_values(2)
            if nik in list_nik:
                st.error("NIK sudah terdaftar!")
            else:
                alamat_lengkap = f"{desa} RT {rt} / RW {rw}, Kec. {kecamatan}"

                sheet.append_row([
                    nama, nik, password, str(
                        tanggal_lahir), asal_sekolah, koordinat,
                    "Belum Verifikasi", "-", hitung_jarak(
                        koordinat), hitung_usia_detail(str(tanggal_lahir)),
                    alamat_lengkap, rt, rw, desa, kecamatan, jenis_alamat
                ])
                st.cache_data.clear()
                st.success(
                    "Pendaftaran Berhasil! Verifikasi dilakukan oleh Panitia Sekolah.")

# ------------------------------------------
# MENU: LOGIN AKUN SISWA
# ------------------------------------------
elif menu == "Login Akun Siswa":
    st.title("🔑 Dashboard Siswa")
    if 'user_aktif' not in st.session_state:
        l_nik = st.text_input("NIK")
        l_pw = st.text_input("Password", type="password")
        if st.button("Masuk"):
            records = ambil_data_rekaman(sheet)
            data = pd.DataFrame(records)
            user = data[(data['NIK'].astype(str) == l_nik) & (
                data['Password'].astype(str) == str(l_pw))]
            if not user.empty:
                st.session_state['user_aktif'] = user.iloc[0]
                st.rerun()
            else:
                st.error("Data tidak ditemukan.")
    else:
        u = st.session_state['user_aktif']
        st.info(f"Selamat Datang, **{u['Nama']}**")
        if st.button("Keluar"):
            del st.session_state['user_aktif']
            st.rerun()

        c1, c2, c3 = st.columns(3)
        c1.metric("Status", u['Status'])
        c2.metric("Jarak", f"{hitung_jarak(u['Koordinat'])} KM")
        c3.metric("Usia", hitung_usia_detail(u['Tanggal Lahir']))

        st.markdown("---")
        st.markdown("#### 📍 Informasi Alamat")
        st.write(f"**Jenis Alamat:** {u.get('Jenis Alamat', '-')}")
        st.write(f"**Alamat Lengkap:** {u.get('Alamat Lengkap', '-')}")

# ------------------------------------------
# MENU: HASIL PEMERINGKATAN
# ------------------------------------------
elif menu == "Hasil Pemeringkatan":
    st.title("🏆 Hasil Pemeringkatan SPMB")
    status = sheet_set.cell(1, 2).value
    if status == "TUTUP":
        st.warning("### 📢 Pengumuman Belum Dibuka")
    else:
        st.success("Hasil Seleksi Berdasarkan Usia & Jarak (Real-Time)")
        records = ambil_data_rekaman(sheet)
        if len(records) > 0:
            df = pd.DataFrame(records)
            df = df[df['Status'] == "Terverifikasi"].copy()
            if not df.empty:
                df['Skor_Indeks'] = df.apply(lambda x: hitung_skor_indeks(
                    x['Tanggal Lahir'], x['Koordinat']), axis=1)
                df['Usia'] = df['Tanggal Lahir'].apply(hitung_usia_detail)
                df['Jarak'] = df['Koordinat'].apply(
                    lambda x: f"{hitung_jarak(x)} KM")
                df_sorted = df.sort_values(by='Skor_Indeks', ascending=False)
                df_sorted.insert(0, 'Peringkat', range(1, len(df_sorted) + 1))
                st.dataframe(
                    df_sorted[['Peringkat', 'Nama', 'Usia', 'Jarak']], hide_index=True, width="stretch")
            else:
                st.info("Belum ada data terverifikasi.")

# ------------------------------------------
# MENU: ADMIN & KEPALA SEKOLAH
# ------------------------------------------
elif menu == "Admin SPMB":
    admins = {
        "Admin": {"pw": st.secrets["admins"]["admin_pw"], "role": "Panitia"},
        "Verifikator_1": {"pw": st.secrets["admins"]["verifikator1_pw"], "role": "Panitia"},
        "KepalaSekolah": {"pw": st.secrets["admins"]["kepsek_pw"], "role": "Kepala Sekolah"}
    }

    if 'admin_in' not in st.session_state:
        with st.form("login_admin"):
            u = st.text_input("User")
            p = st.text_input("Pass", type="password")
            if st.form_submit_button("Login"):
                if u in admins and p == admins[u]["pw"]:
                    st.session_state['admin_in'] = True
                    st.session_state['admin_user'] = u
                    st.session_state['admin_role'] = admins[u]["role"]
                    st.rerun()
                else:
                    st.error("Akses Ditolak")
        st.stop()

    role = st.session_state['admin_role']
    st.title(f"👨‍💼 Panel {role}")
    if st.button("Logout"):
        del st.session_state['admin_in']
        st.rerun()

    st.markdown("### 📊 Statistik Real-time")
    records_stat = ambil_data_rekaman(sheet)
    if len(records_stat) > 0:
        df_stat = pd.DataFrame(records_stat)
        total = len(df_stat)
        terverif = len(df_stat[df_stat['Status'] == "Terverifikasi"])
        belum = total - terverif

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Pendaftar", f"{total} Siswa")
        m2.metric("Terverifikasi", f"{terverif} Siswa")
        m3.metric("Belum Verifikasi", f"{belum} Siswa")

    if role == "Kepala Sekolah":
        st.markdown("---")
        st.markdown("### 📢 Kontrol Publikasi & Cetak")
        st_skrg = sheet_set.cell(1, 2).value
        cs1, cs2, cs3 = st.columns([2, 1, 1])
        cs1.write(f"Status Saat Ini: **{st_skrg}**")
        if st_skrg == "TUTUP":
            if cs2.button("🔓 BUKA HASIL"):
                sheet_set.update_cell(1, 2, "BUKA")
                st.rerun()
        else:
            if cs2.button("🔒 KUNCI HASIL"):
                sheet_set.update_cell(1, 2, "TUTUP")
                st.rerun()

        df_p = df_stat[df_stat['Status'] == "Terverifikasi"].copy()
        if not df_p.empty:
            df_p['Skor_Indeks'] = df_p.apply(lambda x: hitung_skor_indeks(
                x['Tanggal Lahir'], x['Koordinat']), axis=1)
            df_p['Usia'] = df_p['Tanggal Lahir'].apply(hitung_usia_detail)
            df_p['Jarak'] = df_p['Koordinat'].apply(
                lambda x: f"{hitung_jarak(x)} KM")
            df_p_sorted = df_p.sort_values(by='Skor_Indeks', ascending=False)
            df_p_sorted.insert(0, 'Peringkat', range(1, len(df_p_sorted) + 1))
            pdf_laporan = cetak_peringkat_pdf(df_p_sorted)
            cs3.download_button("🖨️ CETAK PERINGKAT",
                                pdf_laporan, "Laporan_Peringkat_SPMB.pdf")

    st.markdown("---")

    try:
        if len(records_stat) > 0:
            df_a = pd.DataFrame(records_stat)
            pilihan = st.selectbox("Pilih Siswa untuk Verifikasi:", [
                                   "-- Pilih --"] + df_a['Nama'].tolist())

            if pilihan != "-- Pilih --":
                det = df_a[df_a['Nama'] == pilihan].iloc[0]

                if det['Status'] == "Terverifikasi":
                    st.success(
                        f"✅ Siswa ini sudah diverifikasi oleh: **{det.get('Verifikator', 'Admin')}**")
                else:
                    st.warning("⚠️ Siswa ini belum diverifikasi.")

                st.subheader(f"Data Detail: {det['Nama']}")
                pdf_bukti = buat_pdf_pendaftaran(
                    det['Nama'], det['NIK'], det['Tanggal Lahir'], det['Asal Sekolah'], det['Koordinat'])
                st.download_button(
                    f"📥 Cetak Bukti Pendaftaran {det['Nama']}", pdf_bukti, f"Bukti_{det['Nama']}.pdf")

                c1, c2 = st.columns(2)
                c1.metric("Usia", hitung_usia_detail(det['Tanggal Lahir']))
                c2.metric("Jarak", f"{hitung_jarak(det['Koordinat'])} KM")

                st.markdown("**Detail Alamat:**")
                st.write(
                    f"Jenis: **{det.get('Jenis Alamat', '-')}** | {det.get('Alamat Lengkap', '-')}")
                st.markdown("---")

                with st.expander("Update & Verifikasi Data", expanded=True):
                    v_nama = st.text_input("Nama", value=det['Nama'])
                    v_nik = st.text_input("NIK", value=det['NIK'])

                    st.markdown("##### Update Alamat")
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        kecamatan_list = list(KOORDINAT_KECAMATAN.keys())
                        default_kec_index = kecamatan_list.index(
                            det.get('Kecamatan', 'Pati')) if det.get('Kecamatan') in kecamatan_list else 0
                        v_kec = st.selectbox(
                            "Kecamatan", options=kecamatan_list, index=default_kec_index)
                        v_desa = st.text_input(
                            "Desa / Kelurahan", value=str(det.get('Desa', '')))
                    with col_a2:
                        col_rt, col_rw = st.columns(2)
                        with col_rt:
                            v_rt = st.text_input(
                                "RT", value=str(det.get('RT', '')))
                        with col_rw:
                            v_rw = st.text_input(
                                "RW", value=str(det.get('RW', '')))

                        jenis_list = ["Rumah", "Domisili", "Kantor"]
                        default_jenis_index = jenis_list.index(det.get(
                            'Jenis Alamat', 'Rumah')) if det.get('Jenis Alamat') in jenis_list else 0
                        v_jenis = st.selectbox(
                            "Update Jenis Alamat", options=jenis_list, index=default_jenis_index)

                    st.markdown("##### Update Peta")
                    v_koor = det['Koordinat']
                    lat, lon = det['Koordinat'].split(",")
                    mv = folium.Map(
                        location=[float(lat), float(lon)], zoom_start=18)
                    folium.TileLayer(
                        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite').add_to(mv)
                    folium.Marker([float(lat), float(lon)],
                                  icon=folium.Icon(color='red')).add_to(mv)
                    Fullscreen().add_to(mv)
                    map_v = st_folium(mv, height=300, width="stretch")
                    if map_v and map_v['last_clicked']:
                        v_koor = f"{map_v['last_clicked']['lat']}, {map_v['last_clicked']['lng']}"

                    col_v1, col_v2 = st.columns(2)

                    with col_v1:
                        if st.button("✅ SIMPAN & VERIFIKASI", width="stretch"):
                            cell = sheet.find(str(det['NIK']))
                            v_alamat_lengkap = f"{v_desa} RT {v_rt} / RW {v_rw}, Kec. {v_kec}"

                            sheet.update_cell(cell.row, 1, v_nama)
                            sheet.update_cell(cell.row, 2, v_nik)
                            sheet.update_cell(cell.row, 6, v_koor)
                            sheet.update_cell(cell.row, 7, "Terverifikasi")
                            sheet.update_cell(
                                cell.row, 8, st.session_state['admin_user'])
                            sheet.update_cell(
                                cell.row, 9, hitung_jarak(v_koor))
                            sheet.update_cell(
                                cell.row, 10, hitung_usia_detail(det['Tanggal Lahir']))

                            # Updates the 6 new address columns
                            sheet.update_cell(cell.row, 11, v_alamat_lengkap)
                            sheet.update_cell(cell.row, 12, v_rt)
                            sheet.update_cell(cell.row, 13, v_rw)
                            sheet.update_cell(cell.row, 14, v_desa)
                            sheet.update_cell(cell.row, 15, v_kec)
                            sheet.update_cell(cell.row, 16, v_jenis)

                            st.cache_data.clear()
                            st.success(
                                "Data Berhasil Diverifikasi & Diperbarui!")
                            st.rerun()

                    with col_v2:
                        if st.button("🗑️ HAPUS AKUN", width="stretch", type="secondary"):
                            cell_hapus = sheet.find(str(det['NIK']))
                            if cell_hapus:
                                sheet.delete_rows(cell_hapus.row)
                                st.cache_data.clear()
                                st.warning(f"Akun {det['Nama']} dihapus.")
                                st.rerun()
    except Exception as e:
        st.error(f"Gagal memproses data: {e}")
