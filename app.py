import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime

# Set Page Configuration
st.set_page_config(
    page_title="Online Retail Dashboard",
    page_icon="🛍️",
    layout="wide"
)

# ==========================================
# 1. LOAD DATA WITH CACHING
# ==========================================
@st.cache_data
def muat_data():
    # Membaca data dengan parsing tanggal dan tipe data spesifik
    df = pd.read_csv(
        "retail_bersih.csv.gz",
        parse_dates=["InvoiceDate"],
        dtype={
            "InvoiceNo": str,
            "StockCode": str,
            "Description": str,
            "CustomerID": "Int64",
            "Country": str
        },
        compression="gzip"
    )
    # Tambahkan fitur waktu
    df["Bulan"] = df["InvoiceDate"].dt.strftime("%Y-%m")
    df["Hari"] = df["InvoiceDate"].dt.day_of_week  # 0=Senin, ..., 6=Minggu
    df["Jam"] = df["InvoiceDate"].dt.hour
    return df

# Load dataset
df_raw = muat_data()

# ==========================================
# 2. SIDEBAR FILTER
# ==========================================
st.sidebar.header("⚙️ Pengaturan Filter")

# Checkbox untuk mengecualikan UK
kecualikan_uk = st.sidebar.checkbox("Kecualikan United Kingdom", value=False)

# List negara untuk multiselect
list_negara = sorted(df_raw["Country"].unique())
if kecualikan_uk:
    list_negara = [c for c in list_negara if c != "United Kingdom"]

# Multiselect Negara
negara_dipilih = st.sidebar.multiselect(
    "Pilih Negara (Kosongkan untuk Semua Negara):",
    options=list_negara
)

# Filter Rentang Tanggal
min_date = df_raw["InvoiceDate"].min().to_pydatetime()
max_date = df_raw["InvoiceDate"].max().to_pydatetime()

tanggal_dipilih = st.sidebar.date_input(
    "Rentang Tanggal:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Input Cari Nama Produk
cari_produk = st.sidebar.text_input("Cari Nama Produk:", value="").strip()

# ==========================================
# 3. APPLY FILTERS TO DATASET
# ==========================================
df_filtered = df_raw.copy()

# Filter Negara
if kecualikan_uk:
    df_filtered = df_filtered[df_filtered["Country"] != "United Kingdom"]

if negara_dipilih:
    df_filtered = df_filtered[df_filtered["Country"].isin(negara_dipilih)]

# Filter Tanggal: batas akhir = awal hari SETELAH tanggal terpilih, dibandingkan dengan "<"
# (date_input mengembalikan tanggal tanpa jam, jadi tanggal akhir = pukul 00:00 hari itu)
if isinstance(tanggal_dipilih, tuple) and len(tanggal_dipilih) == 2:
    start_date = pd.to_datetime(tanggal_dipilih[0])
    end_date = pd.to_datetime(tanggal_dipilih[1]) + pd.Timedelta(days=1)
    df_filtered = df_filtered[
        (df_filtered["InvoiceDate"] >= start_date) &
        (df_filtered["InvoiceDate"] < end_date)
    ]

# Filter Cari Produk (tidak peka huruf besar/kecil)
if cari_produk:
    df_filtered = df_filtered[
        df_filtered["Description"].str.contains(cari_produk, case=False, na=False)
    ]

# ==========================================
# 4. MAIN PAGE DISPLAY
# ==========================================
st.title("🛍️ Online Retail Transaction Dashboard")
st.caption(
    f"Periode Data: {min_date.strftime('%d %b %Y')} s.d. {max_date.strftime('%d %b %Y')} | "
    f"Mata Uang yang Digunakan: GBP (£)"
)

# Jika hasil filter kosong
if df_filtered.empty:
    st.warning("⚠️ Tidak ada data transaksi yang cocok dengan kriteria filter Anda.")
    st.stop()

# ==========================================
# 5. METRICS CARDS
# ==========================================
# Hitung nilai agregat utama
pendapatan_total = df_filtered["Pendapatan"].sum()
invoice_unik = df_filtered["InvoiceNo"].nunique()
pelanggan_unik = df_filtered["CustomerID"].dropna().nunique()
rata_rata_order = pendapatan_total / invoice_unik if invoice_unik > 0 else 0

# Layout 4 Kolom
met_1, met_2, met_3, met_4 = st.columns(4)

with met_1:
    st.metric(
        label="Total Pendapatan",
        value=f"£{pendapatan_total:,.2f}"
    )
with met_2:
    st.metric(
        label="Total Invoice Unik",
        value=f"{invoice_unik:,}"
    )
with met_3:
    st.metric(
        label="Total Pelanggan Unik",
        value=f"{pelanggan_unik:,}"
    )
with met_4:
    st.metric(
        label="Rata-rata Nilai Order",
        value=f"£{rata_rata_order:,.2f}"
    )

st.markdown("--- ")

# ==========================================
# 6. VISUALISASI GRAPHIC (2 BARIS x 2 KOLOM)
# ==========================================
baris1_kol1, baris1_kol2 = st.columns(2)
baris2_kol1, baris2_kol2 = st.columns(2)

# --- BARIS 1, KOLOM 1: LINE CHART TREN BULANAN ---
with baris1_kol1:
    st.subheader("📈 Tren Pendapatan Bulanan")
    df_bulanan = (
        df_filtered.groupby("Bulan")["Pendapatan"]
        .sum()
        .reset_index()
        .sort_values("Bulan")
    )
    st.line_chart(data=df_bulanan, x="Bulan", y="Pendapatan")
    st.caption("ℹ️ Catatan: Transaksi untuk bulan Desember 2011 hanya mencakup rentang tanggal 1 s.d. 9 Desember.")

# --- BARIS 1, KOLOM 2: BAR CHART TOP 10 PRODUK ---
with baris1_kol2:
    st.subheader("🏆 10 Produk Pendapatan Tertinggi")
    df_top_prod = (
        df_filtered.groupby("Description")["Pendapatan"]
        .sum()
        .reset_index()
        .nlargest(10, "Pendapatan")
    )

    chart_prod = alt.Chart(df_top_prod).mark_bar().encode(
        x=alt.X("Pendapatan:Q", title="Pendapatan (£)"),
        y=alt.Y("Description:N", sort="-x", title="Nama Produk"),
        color=alt.Color("Pendapatan:Q", legend=None, scale=alt.Scale(scheme="blues")),
        tooltip=["Description", "Pendapatan"]
    ).properties(height=300)

    st.altair_chart(chart_prod, use_container_width=True)

# --- BARIS 2, KOLOM 1: BAR CHART TOP 10 NEGARA ---
with baris2_kol1:
    st.subheader("🌍 10 Negara Pendapatan Tertinggi")
    df_top_neg = (
        df_filtered.groupby("Country")["Pendapatan"]
        .sum()
        .reset_index()
        .nlargest(10, "Pendapatan")
    )

    chart_neg = alt.Chart(df_top_neg).mark_bar().encode(
        x=alt.X("Pendapatan:Q", title="Pendapatan (£)"),
        y=alt.Y("Country:N", sort="-x", title="Negara"),
        color=alt.Color("Pendapatan:Q", legend=None, scale=alt.Scale(scheme="tealblues")),
        tooltip=["Country", "Pendapatan"]
    ).properties(height=300)

    st.altair_chart(chart_neg, use_container_width=True)

# --- BARIS 2, KOLOM 2: HEATMAP INVOICE PER HARI DAN JAM ---
with baris2_kol2:
    st.subheader("⏰ Kepadatan Invoice (Hari vs Jam)")

    # Menyiapkan peta nama hari
    peta_hari_nama = {
        0: "1. Senin",
        1: "2. Selasa",
        2: "3. Rabu",
        3: "4. Kamis",
        4: "5. Jumat",
        5: "6. Sabtu",
        6: "7. Minggu"
    }
    df_heatmap = df_filtered.copy()
    df_heatmap["Nama_Hari"] = df_heatmap["Hari"].map(peta_hari_nama)

    # Agregasi invoice unik per Hari dan Jam
    df_dense = (
        df_heatmap.groupby(["Nama_Hari", "Jam"])["InvoiceNo"]
        .nunique()
        .reset_index()
        .rename(columns={"InvoiceNo": "Invoices"})
    )

    chart_heat = alt.Chart(df_dense).mark_rect().encode(
        x=alt.X("Jam:O", title="Jam Transaksi (24 Jam)"),
        y=alt.Y("Nama_Hari:N", title="Hari dalam Seminggu"),
        color=alt.Color("Invoices:Q", title="Invoice Unik", scale=alt.Scale(scheme="blues")),
        tooltip=["Nama_Hari", "Jam", "Invoices"]
    ).properties(height=300)

    st.altair_chart(chart_heat, use_container_width=True)

# ==========================================
# 7. TABEL RINGKASAN PRODUK & UNDUH CSV
# ==========================================
st.markdown("--- ")
st.subheader("📊 Ringkasan Penjualan per Produk")

# Agregasi Ringkasan per Produk
ringkasan_produk = (
    df_filtered.groupby("Description")
    .agg(
        Terjual=("Quantity", "sum"),
        Pendapatan=("Pendapatan", "sum"),
        Invoice=("InvoiceNo", "nunique")
    )
    .reset_index()
    .sort_values("Pendapatan", ascending=False)
)

# Menampilkan data summary produk
st.dataframe(ringkasan_produk, use_container_width=True, hide_index=True)

# Convert dataframe ke format CSV
@st.cache_data
def konversi_csv(df_input):
    return df_input.to_csv(index=False).encode("utf-8")

csv_data = konversi_csv(ringkasan_produk)

# Tombol unduh data ringkasan
st.download_button(
    label="📥 Unduh Ringkasan Produk sebagai CSV",
    data=csv_data,
    file_name="ringkasan_produk_retail.csv",
    mime="text/csv"
)
