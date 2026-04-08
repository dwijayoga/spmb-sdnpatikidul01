import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import folium
from st_supabase_connection import SupabaseConnection
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
    [data-testid="stMetric"] { background-color: #f8f9fa; border-radius: 10px; border: 1px solid #eee; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Mapping Koordinat Kecamatan ---
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
# 2. KONEKSI & DATABASE (SUPABASE)
# ==========================================
conn = st.connection("supabase", type=SupabaseConnection)


@st.cache_data(ttl=300)
def ambil_data_pendaftaran():
    res = conn.table("pendaftaran").select("*").execute()
    return pd.DataFrame(res.data)


@st.cache_data(ttl=300)
def cek_status_pengumuman():
    # Mengambil status dari tabel 'pengaturan' di Supabase
    res = conn.table("pengaturan").select("nilai").eq(
        "kunci", "status_pengumuman").execute()
    if res.data:
        return res.data[0]['nilai']
    return "TUTUP"

# ==========================================
# 3. FUNGSI LOGIKA (JARAK, USIA, PDF)
# ==========================================


def hitung_jarak(koor_siswa):
    lat_sek, lon_sek = -6.7516, 111.0321
    try:
        lat_sis, lon_sis = map(float, str(koor_siswa).split(","))
        R = 6371
        dlat, dlon = math.radians(
            lat_sis - lat_sek), math.radians(lon_sis - lon_sek)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat_sek)) * \
            math.cos(math.radians(lat_sis)) * math.sin(dlon/2)**2
        return round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a))), 2)
    except:
        return 0


def hitung_usia_detail(tgl_lahir_str):
    try:
        target = datetime.date(2026, 7, 1)
        tgl = datetime.datetime.strptime(str(tgl_lahir_str), "%Y-%m-%d").date()
        thn = target.year - tgl.year
        bln = target.month - tgl.month
        if target.day < tgl.day:
            bln -= 1
        if bln < 0:
            thn -= 1
            bln += 12
        return f"{thn} Thn, {bln} Bln"
    except:
        return "-"


def hitung_skor_indeks(tgl_lahir_str, koordinat):
    try:
        target = datetime.date(2026, 7, 1)
        tgl_lahir = datetime.datetime.strptime(
            str(tgl_lahir_str), "%Y-%m-%d").date()
        total_hari = (target - tgl_lahir).days
        jarak = hitung_jarak(koordinat)
        return round(total_hari + (1 / (jarak + 0.01)), 4)
    except:
        return 0


def buat_pdf_bukti(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "BUKTI PENDAFTARAN - SDN PATI KIDUL 01", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    data = [
        ("Nama Lengkap", row['Nama']), ("NIK", row['NIK']),
        ("Tanggal Lahir", row['Tanggal Lahir']
         ), ("Usia (per Juli)", row['Usia']),
        ("Asal Sekolah", row['Asal Sekolah']
         ), ("Jarak ke Sekolah", f"{row['Jarak']} KM"),
        ("Alamat Lengkap", row['Alamat Lengkap']), ("Status", row['Status'])
    ]
    for label, val in data:
        pdf.cell(50, 10, f"{label}:", 0)
        pdf.cell(0, 10, str(val), 0, 1)
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(
        0, 10, f"Dicetak pada: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", align='R')
    return pdf.output(dest='S').encode('latin-1')


# ==========================================
# 4. NAVIGASI SIDEBAR
# ==========================================
menu = st.sidebar.selectbox(
    "Menu Utama", ["Pendaftaran Baru", "Login Siswa", "Hasil Seleksi", "Admin SPMB"])

# --- MENU: PENDAFTARAN BARU ---
if menu == "Pendaftaran Baru":
    st.title("📝 Pendaftaran Siswa Baru")

    with st.container(border=True):
        nama = st.text_input("Nama Lengkap")
        nik = st.text_input("NIK (16 Digit)", max_chars=16)
        pw = st.text_input("Password Akun", type="password")
        tgl_lahir = st.date_input(
            "Tanggal Lahir", min_value=datetime.date(2015, 1, 1))
        asal = st.text_input("Asal TK")

        st.markdown("---")
        jns = st.selectbox("Jenis Alamat", ["Rumah", "Domisili", "Kantor"])
        if jns != "Rumah":
            st.info("ℹ️ Sertakan surat keterangan domisili/kerja saat verifikasi.")

        c1, c2 = st.columns(2)
        with c1:
            kec = st.selectbox("Kecamatan", options=list(
                KOORDINAT_KECAMATAN.keys()))
            desa = st.text_input("Desa")
        with c2:
            rt = st.text_input("RT", max_chars=3)
            rw = st.text_input("RW", max_chars=3)

    st.write("📍 **Klik Lokasi Rumah pada Peta**")
    m = folium.Map(location=KOORDINAT_KECAMATAN[kec], zoom_start=15)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Satellite').add_to(m)
    m.add_child(folium.LatLngPopup())
    map_res = st_folium(m, height=350, width="stretch")

    if st.button("Daftar Sekarang", type="primary", use_container_width=True):
        koor = f"{map_res['last_clicked']['lat']},{map_res['last_clicked']['lng']}" if map_res and map_res['last_clicked'] else None
        if not (nama and nik and pw and desa and koor):
            st.error("Data belum lengkap atau lokasi peta belum diklik!")
        else:
            data_baru = {
                "Nama": nama, "NIK": nik, "Password": pw, "Tanggal Lahir": str(tgl_lahir),
                "Asal Sekolah": asal, "Koordinat": koor, "Desa": desa, "RT": rt, "RW": rw,
                "Kecamatan": kec, "Jenis Alamat": jns, "Status": "Belum Verifikasi",
                "Alamat Lengkap": f"{desa} RT{rt}/RW{rw}, Kec. {kec}",
                "Jarak": hitung_jarak(koor), "Usia": hitung_usia_detail(str(tgl_lahir))
            }
            try:
                conn.table("pendaftaran").insert(data_baru).execute()
                st.cache_data.clear()
                st.success("Berhasil Mendaftar!")
            except Exception as e:
                st.error("NIK sudah terdaftar atau terjadi kesalahan sistem.")

# --- MENU: LOGIN SISWA ---
elif menu == "Login Siswa":
    st.title("🔑 Dashboard Siswa")
    l_nik = st.text_input("NIK")
    l_pw = st.text_input("Password", type="password")
    if st.button("Login"):
        df = ambil_data_pendaftaran()
        user = df[(df['NIK'] == l_nik) & (df['Password'] == l_pw)]
        if not user.empty:
            u = user.iloc[0]
            st.success(f"Halo, {u['Nama']}!")
            c1, c2, c3 = st.columns(3)
            c1.metric("Status", u['Status'])
            c2.metric("Jarak", f"{u['Jarak']} KM")
            c3.metric("Usia", u['Usia'])
            st.write(f"**Alamat:** {u['Alamat Lengkap']}")
            st.download_button("🖨️ Cetak Bukti Pendaftaran",
                               buat_pdf_bukti(u), f"Bukti_{u['Nama']}.pdf")
        else:
            st.error("NIK atau Password salah.")

# --- MENU: HASIL SELEKSI ---
elif menu == "Hasil Seleksi":
    st.title("🏆 Hasil Seleksi Real-Time")
    if cek_status_pengumuman() == "TUTUP":
        st.warning("📢 Pengumuman belum dibuka oleh Panitia.")
    else:
        df = ambil_data_pendaftaran()
        df_v = df[df['Status'] == "Terverifikasi"].copy()
        if not df_v.empty:
            df_v['Skor'] = df_v.apply(lambda x: hitung_skor_indeks(
                x['Tanggal Lahir'], x['Koordinat']), axis=1)
            df_sorted = df_v.sort_values(by="Skor", ascending=False)
            df_sorted.insert(0, 'Peringkat', range(1, len(df_sorted) + 1))
            st.dataframe(df_sorted[['Peringkat', 'Nama', 'Usia', 'Jarak']],
                         hide_index=True, use_container_width=True)
        else:
            st.info("Belum ada data terverifikasi.")

# --- MENU: ADMIN SPMB ---
elif menu == "Admin SPMB":
    st.title("👨‍💼 Panel Admin & Verifikasi")
    adm_user = st.text_input("User Admin")
    adm_pass = st.text_input("Password", type="password")

    admins = {
        "Admin": st.secrets["admins"]["admin_pw"],
        "Kepsek": st.secrets["admins"]["kepsek_pw"]
    }

    if adm_user in admins and adm_pass == admins[adm_user]:
        st.success(f"Login Berhasil sebagai {adm_user}")

        # Fitur Kepsek: Kontrol Pengumuman
        if adm_user == "Kepsek":
            st.markdown("### 📢 Kontrol Pengumuman")
            stat_skrg = cek_status_pengumuman()
            if st.button(f"{'🔒 TUTUP' if stat_skrg == 'BUKA' else '🔓 BUKA'} PENGUMUMAN"):
                n_stat = "TUTUP" if stat_skrg == "BUKA" else "BUKA"
                conn.table("pengaturan").update({"nilai": n_stat}).eq(
                    "kunci", "status_pengumuman").execute()
                st.cache_data.clear()
                st.rerun()

        # Fitur Verifikasi
        st.markdown("---")
        df_adm = ambil_data_pendaftaran()
        pilihan = st.selectbox("Pilih Siswa untuk Verifikasi:", [
                               "-- Pilih --"] + df_adm['Nama'].tolist())

        if pilihan != "-- Pilih --":
            det = df_adm[df_adm['Nama'] == pilihan].iloc[0]
            with st.expander("Detail & Verifikasi", expanded=True):
                st.write(f"**Nama:** {det['Nama']} | **NIK:** {det['NIK']}")
                st.write(f"**Alamat:** {det['Alamat Lengkap']}")

                c1, c2 = st.columns(2)
                if c1.button("✅ VERIFIKASI", use_container_width=True):
                    conn.table("pendaftaran").update(
                        {"Status": "Terverifikasi", "Verifikator": adm_user}).eq("NIK", det['NIK']).execute()
                    st.cache_data.clear()
                    st.success("Berhasil diverifikasi!")
                    st.rerun()
                if c2.button("🗑️ HAPUS DATA", type="secondary", use_container_width=True):
                    conn.table("pendaftaran").delete().eq(
                        "NIK", det['NIK']).execute()
                    st.cache_data.clear()
                    st.warning("Data dihapus.")
                    st.rerun()
    elif adm_pass:
        st.error("Akses Ditolak")
def hitung_jarak(koor_siswa):
    lat_sek, lon_sek = -6.7516, 111.0321
    try:
        lat_sis, lon_sis = map(float, str(koor_siswa).split(","))
        R = 6371
        dlat, dlon = math.radians(lat_sis - lat_sek), math.radians(lon_sis - lon_sek)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat_sek)) * \
            math.cos(math.radians(lat_sis)) * math.sin(dlon/2)**2
        return round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a))), 2)
    except:
        return 0

def hitung_usia_detail(tgl_lahir_str):
    try:
        target = datetime.date(2026, 7, 1)
        tgl = datetime.datetime.strptime(str(tgl_lahir_str), "%Y-%m-%d").date()
        thn = target.year - tgl.year
        bln = target.month - tgl.month
        if target.day < tgl.day:
            bln -= 1
        if bln < 0:
            thn -= 1
            bln += 12
        return f"{thn} Thn, {bln} Bln"
    except:
        return "-"

def hitung_skor_indeks(tgl_lahir_str, koordinat):
    try:
        target = datetime.date(2026, 7, 1)
        tgl_lahir = datetime.datetime.strptime(str(tgl_lahir_str), "%Y-%m-%d").date()
        total_hari = (target - tgl_lahir).days
        jarak = hitung_jarak(koordinat)
        return round(total_hari + (1 / (jarak + 0.01)), 4)
    except:
        return 0

def buat_pdf_bukti(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "BUKTI PENDAFTARAN - SDN PATI KIDUL 01", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    
    # Memastikan kolom tersedia di row
    data = [
        ("Nama Lengkap", row.get('Nama', '-')), 
        ("NIK", row.get('NIK', '-')),
        ("Tanggal Lahir", row.get('Tanggal Lahir', '-')), 
        ("Usia (per Juli)", row.get('Usia', '-')),
        ("Asal Sekolah", row.get('Asal Sekolah', '-')), 
        ("Jarak ke Sekolah", f"{row.get('Jarak', 0)} KM"),
        ("Alamat Lengkap", row.get('Alamat Lengkap', '-')), 
        ("Status", row.get('Status', '-'))
    ]
    for label, val in data:
        pdf.cell(50, 10, f"{label}:", 0)
        pdf.cell(0, 10, str(val), 0, 1)
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, f"Dicetak pada: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", align='R')
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. NAVIGASI SIDEBAR
# ==========================================
menu = st.sidebar.selectbox("Menu Utama", ["Pendaftaran Baru", "Login Siswa", "Hasil Seleksi", "Admin SPMB"])

# --- MENU: PENDAFTARAN BARU ---
if menu == "Pendaftaran Baru":
    st.title("📝 Pendaftaran Siswa Baru")

    with st.container(border=True):
        nama = st.text_input("Nama Lengkap")
        nik = st.text_input("NIK (16 Digit)", max_chars=16)
        pw = st.text_input("Password Akun", type="password")
        tgl_lahir = st.date_input("Tanggal Lahir", min_value=datetime.date(2015, 1, 1))
        asal = st.text_input("Asal TK")

        st.markdown("---")
        jns = st.selectbox("Jenis Alamat", ["Rumah", "Domisili", "Kantor"])
        if jns != "Rumah":
            st.info("ℹ️ Sertakan surat keterangan domisili/kerja saat verifikasi.")

        c1, c2 = st.columns(2)
        with c1:
            kec = st.selectbox("Kecamatan", options=list(KOORDINAT_KECAMATAN.keys()))
            desa = st.text_input("Desa")
        with c2:
            rt = st.text_input("RT", max_chars=3)
            rw = st.text_input("RW", max_chars=3)

    st.write("📍 **Klik Lokasi Rumah pada Peta**")
    m = folium.Map(location=KOORDINAT_KECAMATAN[kec], zoom_start=15)
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Satellite').add_to(m)
    m.add_child(folium.LatLngPopup())
    map_res = st_folium(m, height=350, width="stretch")

    if st.button("Daftar Sekarang", type="primary", use_container_width=True):
        koor = f"{map_res['last_clicked']['lat']},{map_res['last_clicked']['lng']}" if map_res and map_res['last_clicked'] else None
        if not (nama and nik and pw and desa and koor):
            st.error("Data belum lengkap atau lokasi peta belum diklik!")
        else:
            data_baru = {
                "Nama": nama, "NIK": nik, "Password": pw, "Tanggal Lahir": str(tgl_lahir),
                "Asal Sekolah": asal, "Koordinat": koor, "Desa": desa, "RT": rt, "RW": rw,
                "Kecamatan": kec, "Jenis Alamat": jns, "Status": "Belum Verifikasi",
                "Alamat Lengkap": f"{desa} RT{rt}/RW{rw}, Kec. {kec}",
                "Jarak": hitung_jarak(koor), "Usia": hitung_usia_detail(str(tgl_lahir))
            }
            try:
                conn.table("pendaftaran").insert(data_baru).execute()
                st.cache_data.clear()
                st.success("Berhasil Mendaftar!")
            except Exception as e:
                st.error("NIK sudah terdaftar atau terjadi kesalahan sistem.")

# --- MENU: LOGIN SISWA ---
elif menu == "Login Siswa":
    st.title("🔑 Dashboard Siswa")
    l_nik = st.text_input("NIK")
    l_pw = st.text_input("Password", type="password")
    if st.button("Login"):
        df = ambil_data_pendaftaran()
        if not df.empty:
            user = df[(df['NIK'].astype(str) == l_nik) & (df['Password'].astype(str) == l_pw)]
            if not user.empty:
                u = user.iloc[0]
                st.success(f"Halo, {u['Nama']}!")
                c1, c2, c3 = st.columns(3)
                c1.metric("Status", u['Status'])
                c2.metric("Jarak", f"{u['Jarak']} KM")
                c3.metric("Usia", u['Usia'])
                st.write(f"**Alamat:** {u['Alamat Lengkap']}")
                st.download_button("🖨️ Cetak Bukti Pendaftaran", buat_pdf_bukti(u), f"Bukti_{u['Nama']}.pdf")
            else:
                st.error("NIK atau Password salah.")
        else:
            st.error("Belum ada data pendaftar.")

# --- MENU: HASIL SELEKSI ---
elif menu == "Hasil Seleksi":
    st.title("🏆 Hasil Seleksi Real-Time")
    if cek_status_pengumuman() == "TUTUP":
        st.warning("📢 Pengumuman belum dibuka oleh Panitia.")
    else:
        df = ambil_data_pendaftaran()
        if not df.empty:
            df_v = df[df['Status'] == "Terverifikasi"].copy()
            if not df_v.empty:
                df_v['Skor'] = df_v.apply(lambda x: hitung_skor_indeks(x['Tanggal Lahir'], x['Koordinat']), axis=1)
                df_sorted = df_v.sort_values(by="Skor", ascending=False)
                df_sorted.insert(0, 'Peringkat', range(1, len(df_sorted) + 1))
                st.dataframe(df_sorted[['Peringkat', 'Nama', 'Usia', 'Jarak']], hide_index=True, use_container_width=True)
            else:
                st.info("Belum ada data terverifikasi.")
        else:
            st.info("Belum ada data.")

# --- MENU: ADMIN SPMB ---
elif menu == "Admin SPMB":
    st.title("👨‍💼 Panel Admin & Verifikasi")
    adm_user = st.text_input("User Admin")
    adm_pass = st.text_input("Password", type="password")

    if adm_user and adm_pass:
        admins = {
            "Admin": st.secrets["admins"]["admin_pw"],
            "Kepsek": st.secrets["admins"]["kepsek_pw"]
        }

        if adm_user in admins and adm_pass == admins[adm_user]:
            st.success(f"Login Berhasil sebagai {adm_user}")

            if adm_user == "Kepsek":
                st.markdown("### 📢 Kontrol Pengumuman")
                stat_skrg = cek_status_pengumuman()
                if st.button(f"{'🔒 TUTUP' if stat_skrg == 'BUKA' else '🔓 BUKA'} PENGUMUMAN"):
                    n_stat = "TUTUP" if stat_skrg == "BUKA" else "BUKA"
                    conn.table("pengaturan").update({"nilai": n_stat}).eq("kunci", "status_pengumuman").execute()
                    st.cache_data.clear()
                    st.rerun()

            st.markdown("---")
            df_adm = ambil_data_pendaftaran()
            if not df_adm.empty:
                pilihan = st.selectbox("Pilih Siswa untuk Verifikasi:", ["-- Pilih --"] + df_adm['Nama'].tolist())

                if pilihan != "-- Pilih --":
                    det = df_adm[df_adm['Nama'] == pilihan].iloc[0]
                    with st.expander("Detail & Verifikasi", expanded=True):
                        st.write(f"**Nama:** {det['Nama']} | **NIK:** {det['NIK']}")
                        st.write(f"**Alamat:** {det['Alamat Lengkap']}")

                        c1, c2 = st.columns(2)
                        if c1.button("✅ VERIFIKASI", use_container_width=True):
                            conn.table("pendaftaran").update({"Status": "Terverifikasi", "Verifikator": adm_user}).eq("NIK", str(det['NIK'])).execute()
                            st.cache_data.clear()
                            st.success("Berhasil diverifikasi!")
                            time.sleep(1)
                            st.rerun()
                        if c2.button("🗑️ HAPUS DATA", type="secondary", use_container_width=True):
                            conn.table("pendaftaran").delete().eq("NIK", str(det['NIK'])).execute()
                            st.cache_data.clear()
                            st.warning("Data dihapus.")
                            time.sleep(1)
                            st.rerun()
            else:
                st.info("Tidak ada data pendaftar.")
        else:
            st.error("Akses Ditolak")
