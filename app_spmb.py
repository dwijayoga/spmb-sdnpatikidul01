import streamlit as st
import pandas as pd
from geopy.distance import geodesic

# ==========================================
# 1. PENGATURAN TAMPILAN HALAMAN (FRONT-END)
# ==========================================
st.set_page_config(page_title="SPMB SDN Pati Kidul 1", layout="centered")

st.title("Hasil SPMB SDN Pati Kidul 01")
st.subheader("Tahun Ajaran 2026/2027")
st.markdown("---")

# --- TAMBAHAN: SEMBUNYIKAN TOMBOL DOWNLOAD & LOCK TABEL ---
st.markdown(
    """
    <style>
    /* Menyembunyikan toolbar (tombol download & search) pada tabel */
    [data-testid="stElementToolbar"] {
        display: none;
    }
    
    /* Membuat tabel hanya bisa dilihat (tidak bisa diklik/copy) */
    .stDataFrame {
        pointer-events: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 2. KONFIGURASI SISTEM (PENGATURAN UTAMA)
# ==========================================
link_rahasia = "https://docs.google.com/spreadsheets/d/1YDv4eLjesrqbbOJhEy0HfHQJm6Hii638UOu9ovJDrjk/export?format=csv"
koordinat_sekolah = (-6.7516, 111.0321)
kuota_sekolah = 3  # <--- Ubah angka ini sesuai daya tampung riil sekolah Anda


@st.cache_data(ttl=60)
def muat_data():
    return pd.read_csv(link_rahasia)


tabel_pendaftar = muat_data()

# ==========================================
# 3. OTAK ZONASI & LOGIKA SELEKSI (BACK-END)
# ==========================================


def hitung_jarak(koordinat_siswa):
    try:
        titik_siswa = tuple(map(float, str(koordinat_siswa).split(',')))
        return round(geodesic(koordinat_sekolah, titik_siswa).kilometers, 2)
    except:
        return 999.0


# A. Hitung Jarak
tabel_pendaftar['Jarak (km)'] = tabel_pendaftar['Koordinat Rumah'].apply(
    hitung_jarak)

# B. Hitung Usia (Berdasarkan waktu hari ini)
tabel_pendaftar['Tanggal Lahir'] = pd.to_datetime(
    tabel_pendaftar['Tanggal Lahir'], errors='coerce')
sekarang = pd.to_datetime('today')
tabel_pendaftar['Usia (Tahun)'] = (
    sekarang - tabel_pendaftar['Tanggal Lahir']).dt.days / 365.25
tabel_pendaftar['Usia (Tahun)'] = tabel_pendaftar['Usia (Tahun)'].round(1)

# C. Hitung Rasio & Skor Penentu Peringkat
tabel_pendaftar['Rasio'] = (
    tabel_pendaftar['Usia (Tahun)'] / (tabel_pendaftar['Jarak (km)'] + 1))

# Aturan Mutlak: Jika usia < 6 tahun, skor pinalti agar selalu di peringkat bawah
tabel_pendaftar['Skor Seleksi'] = tabel_pendaftar.apply(
    lambda x: x['Rasio'] if x['Usia (Tahun)'] >= 6.0 else -1.0, axis=1
)

# D. Urutkan berdasarkan Skor Seleksi Tertinggi (Descending)
tabel_pendaftar = tabel_pendaftar.sort_values(
    by='Skor Seleksi', ascending=False)

# E. Buat Kolom Nomor Urut (No) yang Rapi
tabel_pendaftar = tabel_pendaftar.reset_index(drop=True)
tabel_pendaftar.index += 1  # Mulai nomor urut dari 1
tabel_pendaftar = tabel_pendaftar.reset_index()
tabel_pendaftar = tabel_pendaftar.rename(columns={'index': 'No'})

# F. Tentukan Status Berdasarkan Peringkat & Aturan Umur


def tentukan_status(row):
    if row['Usia (Tahun)'] < 6.0:
        return "❌ Tidak Diterima (Usia < 6 th)"
    elif row['No'] <= kuota_sekolah:
        return "✅ Diterima"
    else:
        return "⏳ Cadangan"


tabel_pendaftar['Keterangan'] = tabel_pendaftar.apply(tentukan_status, axis=1)

# ==========================================
# 4. TAMPILKAN TABEL KE LAYAR PUBLIK
# ==========================================
# Pastikan nama kolom 'Nama' sesuai dengan yang ada di Google Sheets Anda
kolom_publik = ['No', 'Nama', 'Jarak (km)', 'Usia (Tahun)', 'Keterangan']

st.dataframe(
    tabel_pendaftar[kolom_publik],
    hide_index=True,
    width='stretch'
)

# Berikan catatan info di bawah tabel
st.info(f"Kapasitas daya tampung saat ini: **{kuota_sekolah} siswa**.")
st.caption("Catatan: Peringkat disusun otomatis oleh sistem. Prioritas diberikan kepada pendaftar dengan kombinasi jarak terdekat dan usia lebih tua. Batas usia minimal penerimaan adalah 6 tahun.")
