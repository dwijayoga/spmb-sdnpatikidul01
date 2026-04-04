import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import requests  # Untuk melacak link Maps

# ==========================================
# 1. PENGATURAN TAMPILAN HALAMAN (FRONT-END)
# ==========================================
st.set_page_config(page_title="SPMB SDN Pati Kidul 1", layout="centered")

st.title("Hasil SPMB SDN Pati Kidul 01")
st.subheader("Tahun Ajaran 2026/2027")
st.markdown("---")

# CSS untuk sembunyikan toolbar & kunci tabel
st.markdown(
    """
    <style>
    [data-testid="stElementToolbar"] { display: none; }
    .stDataFrame { pointer-events: none; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 2. KONFIGURASI SISTEM
# ==========================================
link_rahasia = "https://docs.google.com/spreadsheets/d/1YDv4eLjesrqbbOJhEy0HfHQJm6Hii638UOu9ovJDrjk/export?format=csv"
koordinat_sekolah = (-6.7516, 111.0321)
kuota_sekolah = 5


@st.cache_data(ttl=60)
def muat_data():
    return pd.read_csv(link_rahasia)


tabel_pendaftar = muat_data()

# ==========================================
# 3. MESIN PENERJEMAH LINK MAPS -> KOORDINAT
# ==========================================


def ekstrak_koordinat(link_maps):
    try:
        # Jika input sudah berupa koordinat (angka, angka)
        if "," in str(link_maps) and "http" not in str(link_maps):
            return tuple(map(float, str(link_maps).split(',')))

        # Jika input berupa Link Google Maps
        response = requests.get(link_maps, allow_redirects=True, timeout=5)
        final_url = response.url  # Mengambil URL asli setelah redirect

        # Mencari angka koordinat di dalam URL asli
        # Format biasanya: ...@(-6.123,111.123)...
        if "@" in final_url:
            coords_part = final_url.split("@")[1].split(",")[0:2]
            return (float(coords_part[0]), float(coords_part[1]))
        return None
    except:
        return None


def hitung_jarak(link_maps):
    titik_siswa = ekstrak_koordinat(link_maps)
    if titik_siswa:
        return round(geodesic(koordinat_sekolah, titik_siswa).kilometers, 2)
    return 999.0  # Jika link rusak/tidak terbaca


# --- EKSEKUSI DATA ---
# Ganti 'Lokasi Rumah' dengan nama kolom di Google Sheets Anda yang berisi Link Maps
tabel_pendaftar['Jarak (km)'] = tabel_pendaftar['Lokasi Rumah'].apply(
    hitung_jarak)

# Hitung Usia
tabel_pendaftar['Tanggal Lahir'] = pd.to_datetime(
    tabel_pendaftar['Tanggal Lahir'], errors='coerce')
sekarang = pd.to_datetime('today')
tabel_pendaftar['Usia (Tahun)'] = (
    (sekarang - tabel_pendaftar['Tanggal Lahir']).dt.days / 365.25).round(1)

# Hitung Rasio & Skor Seleksi
tabel_pendaftar['Rasio'] = (
    tabel_pendaftar['Usia (Tahun)'] / (tabel_pendaftar['Jarak (km)'] + 1))
tabel_pendaftar['Skor Seleksi'] = tabel_pendaftar.apply(
    lambda x: x['Rasio'] if x['Usia (Tahun)'] >= 6.0 else -1.0, axis=1
)

# Urutkan & Buat No Urut
tabel_pendaftar = tabel_pendaftar.sort_values(
    by='Skor Seleksi', ascending=False).reset_index(drop=True)
tabel_pendaftar.index += 1
tabel_pendaftar = tabel_pendaftar.reset_index().rename(columns={'index': 'No'})

# Status


def tentukan_status(row):
    if row['Usia (Tahun)'] < 6.0:
        return "❌ Tidak Diterima (Usia < 6 th)"
    return "✅ Diterima" if row['No'] <= kuota_sekolah else "⏳ Cadangan"


tabel_pendaftar['Keterangan'] = tabel_pendaftar.apply(tentukan_status, axis=1)

# ==========================================
# 4. TAMPILKAN
# ==========================================
# Pastikan nama kolom 'Nama' sesuai dengan di Google Sheets
kolom_publik = ['No', 'Nama', 'Jarak (km)', 'Usia (Tahun)', 'Keterangan']
st.dataframe(tabel_pendaftar[kolom_publik], hide_index=True, width='stretch')

st.info(f"Kapasitas daya tampung: **{kuota_sekolah} siswa**.")
