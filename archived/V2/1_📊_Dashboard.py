
# ----------------------------------------------------------------- Setup -----------------------------------------------------------------

# Libraries
import folium
import branca
import pathlib
import streamlit as st
import numpy as np
import pandas as pd
import geopandas as gpd
import altair as alt

from datetime import datetime
from streamlit_folium import st_folium

# Page Config
st.set_page_config(    
    page_title="Dashboard Pertumbuhan Customer",    
    page_icon="Logo/FIFGROUP_KOTAK.png",
    initial_sidebar_state="collapsed"
)

st.html(
    """
    <style>
        .stMainBlockContainer {
            max-width: 95rem;
        }
        .block-container {
            padding-top: 4rem;
            padding-bottom: 4rem;
        }
    </style>
    """
)

# Custom CSS
def load_css(file_path):
    with open(file_path) as f:
        st.html(f"<style>{f.read()}</style>")

css_path = pathlib.Path("assets/styles.css")
load_css(css_path)

# ----------------------------------------------------------------- Data -----------------------------------------------------------------

# Preprocess Customer Data
def process_df(df, suffix, quarters):
    candidate_geo_cols = ["PULAU", "WADMKC", "WADMKK", "WADMPR", "Usia Produktif"]
    geo_cols = [col for col in candidate_geo_cols if col in df.columns]
    
    if "geometry" in df.columns:
        geo_cols.append("geometry")
        
    out_df = df[geo_cols].copy()
    out_df["Usia Produktif"] = out_df["Usia Produktif"].replace([float("inf"), -float("inf")], 0).fillna(0)

    new_columns = {}
    
    for i, quarter in enumerate(quarters):
        col_name = f"{quarter}_{suffix}"
        col_name_all = f"{quarter}_TOTAL"
        if col_name not in df.columns:
            continue

        if i == 0:
            new_columns[f"{quarter}_CUST_NO"] = df[col_name]
            new_columns[f"{quarter}_CUST_NO_TOTAL"] = df[col_name_all]
        else:
            prev_quarter = quarters[i-1]
            prev_col_name = f"{prev_quarter}_{suffix}"
            prev_col_name_all = f"{prev_quarter}_TOTAL"
            
            if prev_col_name not in df.columns:
                continue
            
            new_columns[f"{quarter}_CUST_NO"] = df[col_name]
            new_columns[f"{quarter}_CUST_NO_TOTAL"] = df[col_name_all]
            
            growth = ((df[col_name] - df[prev_col_name]) / df[prev_col_name]) * 100
            new_columns[f"{quarter}_GROWTH"] = growth.replace([float("inf"), -float("inf")], 0).fillna(0)
            
            growth_number = df[col_name] - df[prev_col_name]
            new_columns[f"{quarter}_GROWTH_NUMBER"] = growth_number.replace([float("inf"), -float("inf")], 0).fillna(0)

            growth_number_all = df[col_name_all] - df[prev_col_name_all]
            new_columns[f"{quarter}_GROWTH_NUMBER_ALL"] = growth_number_all.replace([float("inf"), -float("inf")], 0).fillna(0)

            prod_age_ratio = df[col_name] / df["Usia Produktif"] * 100
            new_columns[f"{quarter}_PROD_AGE_RATIO"] = prod_age_ratio.replace([float("inf"), -float("inf")], 0).fillna(0)

            cust_ratio = growth_number / growth_number_all * 100
            new_columns[f"{quarter}_CUST_RATIO"] = cust_ratio.replace([float("inf"), -float("inf")], 0).fillna(0)

    temp_df = pd.DataFrame(new_columns, index=out_df.index)
    out_df = pd.concat([out_df, temp_df], axis=1)

    selected_quarter = st.session_state.get("selected_quarter", ("2019", "2024Q4"))
    first_q, last_q = selected_quarter
    first_cust_col = f"{first_q}_CUST_NO"
    last_cust_col  = f"{last_q}_CUST_NO"
    first_cust_col_all = f"{first_q}_CUST_NO_TOTAL"
    last_cust_col_all  = f"{last_q}_CUST_NO_TOTAL"

    first_cust = out_df[first_cust_col].fillna(0).replace([float("inf"), -float("inf")], 0)
    last_cust  = out_df[last_cust_col].fillna(0).replace([float("inf"), -float("inf")], 0)
    first_cust_all = out_df[first_cust_col_all].fillna(0).replace([float("inf"), -float("inf")], 0)
    last_cust_all  = out_df[last_cust_col_all].fillna(0).replace([float("inf"), -float("inf")], 0)
    prod_age = out_df["Usia Produktif"].fillna(0).replace([float("inf"), -float("inf")], 0)
    
    map_growth = ((last_cust - first_cust) / first_cust) * 100
    map_growth = map_growth.replace([float("inf"), -float("inf")], 0).fillna(0)
    
    map_growth_number = last_cust - first_cust
    map_growth_number = map_growth_number.replace([float("inf"), -float("inf")], 0).fillna(0)

    map_growth_number_all = last_cust_all - first_cust_all
    map_growth_number_all = map_growth_number_all.replace([float("inf"), -float("inf")], 0).fillna(0)

    map_prod_age_ratio = last_cust / prod_age * 100
    map_prod_age_ratio = map_prod_age_ratio.replace([float("inf"), -float("inf")], 0).fillna(0)

    map_cust_ratio = map_growth_number / map_growth_number_all * 100
    map_cust_ratio = map_cust_ratio.replace([float("inf"), -float("inf")], 0).fillna(0)
    
    map_metrics = {
        "MAP_GROWTH": map_growth,
        "MAP_GROWTH_NUMBER": map_growth_number,
        "MAP_PROD_AGE_RATIO": map_prod_age_ratio,
        "MAP_CUST_RATIO": map_cust_ratio
    }
    
    tooltip_map_growth_number = out_df.apply(
        lambda row: f"{int(row[first_cust_col] if not pd.isna(row[first_cust_col]) else 0):,} -> {int(row[last_cust_col] if not pd.isna(row[last_cust_col]) else 0):,}", 
        axis=1
    )
    
    tooltip_growth = map_growth.apply(
        lambda x: f"{x:.2f}%"
    ) + " (" + map_growth_number.apply(lambda x: f"{int(x):,}") + ")"
    
    tooltip_prod_age_ratio = map_prod_age_ratio.apply(
        lambda x: f"{x:.2f}%"
    )
    
    tooltip_cust_ratio = map_cust_ratio.apply(
        lambda x: f"{x:.2f}%"
    )
    
    map_metrics.update({
        "TOOLTIP_MAP_GROWTH_NUMBER": tooltip_map_growth_number,
        "TOOLTIP_GROWTH": tooltip_growth,
        "TOOLTIP_PROD_AGE_RATIO": tooltip_prod_age_ratio,
        "TOOLTIP_CUST_RATIO": tooltip_cust_ratio
    })
    
    map_df = pd.DataFrame(map_metrics, index=out_df.index)
    out_df = pd.concat([out_df, map_df, df[df.columns[df.columns.str.contains("ALL")]]], axis=1)

    return out_df

def calculate_growth(df1, df2, df3, df4):
    selected_buss_unit = st.session_state.get("selected_buss_unit", "ALL")

    if selected_buss_unit == "ALL":
        suffix = "TOTAL"
    elif selected_buss_unit == "ALL (> 1x)":
        suffix = "TOTAL2"
    elif selected_buss_unit == "NMC (> 1x)":
        suffix = "NMC to NMC"
    elif selected_buss_unit == "REFI (> 1x)":
        suffix = "REFI to REFI"
    elif selected_buss_unit == "MPF (> 1x)":
        suffix = "MPF to MPF"
    else:
        suffix = selected_buss_unit

    quarters = [
        "2019",
        "2020Q1", "2020Q2", "2020Q3", "2020Q4",
        "2021Q1", "2021Q2", "2021Q3", "2021Q4",
        "2022Q1", "2022Q2", "2022Q3", "2022Q4",
        "2023Q1", "2023Q2", "2023Q3", "2023Q4",
        "2024Q1", "2024Q2", "2024Q3", "2024Q4"
    ]

    processed_df1 = process_df(df1, suffix, quarters)
    processed_df2 = process_df(df2, suffix, quarters)
    processed_df3 = process_df(df3, suffix, quarters)
    processed_df4 = process_df(df4, suffix, quarters)

    return processed_df1, processed_df2, processed_df3, processed_df4

# Preprocess Booking Data
def process_df_booking(data):
    selected_quarter = st.session_state.get("selected_quarter", ("2019", "2024Q4"))
    selected_buss_unit = st.session_state.get("selected_buss_unit", "ALL")

    df = data.copy()
    
    extracted_parts = [col.split("_") for col in df.columns]
    unique_pairs = set((parts[0], parts[1]) for parts in extracted_parts if len(parts) >= 2)
    
    result = pd.DataFrame(index=df.index)
    
    for q, bu in unique_pairs:
        if q not in selected_quarter:
            continue  

        if selected_buss_unit == "ALL":
            selected_cols = [
                col for col in df.columns 
                if col.startswith(f"{q}_{bu}") and len(col.split("_")) >= 4 and col.split("_")[3] == "TOTAL"
            ]
        else:
            if selected_buss_unit == "NMC (> 1x)":
                selected_buss_unit = "NMC to NMC"
            elif selected_buss_unit == "REFI (> 1x)":
                selected_buss_unit = "REFI to REFI"
            elif selected_buss_unit == "MPF (> 1x)":
                selected_buss_unit = "MPF to MPF"

            selected_cols = [
                col for col in df.columns 
                if col.startswith(f"{q}_{bu}") and len(col.split("_")) >= 4 and col.split("_")[3] == selected_buss_unit
            ]
        
        result[f"{q}_{bu}"] = df[selected_cols].sum(axis=1)
        
        selected_cols_y = [
            col for col in selected_cols 
            if len(col.split("_")) >= 5 and col.split("_")[4] == "Y"
        ]
        
        result[f"{q}_{bu}_BA4"] = df[selected_cols_y].sum(axis=1)
    
    join_keys = ["WADMKC", "WADMKK", "WADMPR"]
    for key in join_keys:
        if key in df.columns:
            result[key] = df[key]

    existing_keys = [key for key in join_keys if key in result.columns]
    result = result[existing_keys + [col for col in result.columns if col not in join_keys]]

    if selected_buss_unit != "ALL":
        if " to " in selected_buss_unit:
            from_bu, to_bu = selected_buss_unit.split(" to ")
            for col in result.columns:
                if col in join_keys:
                    continue
                if from_bu not in col and to_bu not in col:
                    result[col] = 0
        else:
            for col in result.columns:
                if col in join_keys:
                    continue
                if selected_buss_unit not in col:
                    result[col] = 0

    return result

# Load Data
@st.cache_data()
def preparing_data():
    # Map Data
    shp_prov = gpd.read_file("Data Fix/LapakGIS_Batas_Provinsi_2024.json")
    shp_prov[["WADMPR"]] = shp_prov[["WADMPR"]].apply(lambda x: x.str.upper())
    shp_prov.set_crs(epsg=4326, inplace=True)

    shp_kab = gpd.read_file("Data Fix/LapakGIS_Batas_Kabupaten_2024.json")
    shp_kab[["WADMKK", "WADMPR"]] = shp_kab[["WADMKK", "WADMPR"]].apply(lambda x: x.str.upper())
    shp_kab.set_crs(epsg=4326, inplace=True)

    shp_kec = gpd.read_file("Data Fix/LapakGIS_Batas_Kecamatan_2024.json")
    shp_kec[["WADMKC", "WADMKK", "WADMPR"]] = shp_kec[["WADMKC", "WADMKK", "WADMPR"]].apply(lambda x: x.str.upper())
    shp_kec.set_crs(epsg=4326, inplace=True)

    # Cabang Data
    df_cab_lat_long = pd.read_excel("Data Fix/202501 - LIST ALL NETWORK_geotagging_final.xlsx", sheet_name="List ID Network")
    df_cab_lat_long = df_cab_lat_long[df_cab_lat_long["NETWORK"].isin(["CABANG", "POS"])]
    df_cab_lat_long["FULL NAME"] = (
        df_cab_lat_long["NETWORK"] + " " + df_cab_lat_long["BRANCH NAME"] + " (" +
        df_cab_lat_long["BRANCH ID"].astype(str) + ")"
    )
    df_cab_lat_long["LAT"] = df_cab_lat_long["GEOTAGGING"].str.split(",").str[0]
    df_cab_lat_long["LONG"] = df_cab_lat_long["GEOTAGGING"].str.split(",").str[1]

    df_cab = pd.read_excel("Data Fix/202501 - LIST ALL NETWORK_geotagging_final.xlsx", sheet_name="Alamat Network")
    df_cab.columns = df_cab.columns.str.strip()
    df_cab = df_cab[df_cab["NETWORKING"].isin(["1. CABANG", "6. POS"])].reset_index(drop=True)
    df_cab["NAMA CABANG"] = df_cab["ID CABANG"].map(
        df_cab_lat_long.set_index("BRANCH ID")["BRANCH NAME"].to_dict()
    )
    df_cab["NETWORKING"] = df_cab["NETWORKING"].str.split(".").str[1].str.strip()
    df_cab["FULL NAME"] = (
        df_cab["NETWORKING"] + " " + df_cab["NAMA CABANG"] + " (" +
        df_cab["ID CABANG"].astype(str) + ")"
    )
    df_cab["LAT"] = df_cab["FULL NAME"].map(
        df_cab_lat_long.set_index("FULL NAME")["LAT"].to_dict()
    )
    df_cab["LONG"] = df_cab["FULL NAME"].map(
        df_cab_lat_long.set_index("FULL NAME")["LONG"].to_dict()
    )

    # Dealer Data
    df_dealer = pd.read_excel("Data Fix/GIS LOCATION.xlsx")
    df_dealer = df_dealer[df_dealer["CATEGORY"].isin(["DEALER", "POS DEALER", "COMPETITOR"])].reset_index(drop=True)
    df_dealer = df_dealer.drop("LOCATION_ID", axis=1)

    # Customer Data
    df = pd.read_parquet("Data Fix/Data Customer AGG_v4.parquet")
    agg_columns = df.select_dtypes(include="number").columns

    provinsi_ke_pulau = {
        "DKI JAKARTA": "JAWA", "BANTEN": "JAWA", "JAWA BARAT": "JAWA",
        "JAWA TENGAH": "JAWA", "DAERAH ISTIMEWA YOGYAKARTA": "JAWA", "JAWA TIMUR": "JAWA",
        "ACEH": "SUMATERA", "SUMATERA UTARA": "SUMATERA", "SUMATERA BARAT": "SUMATERA",
        "RIAU": "SUMATERA", "KEPULAUAN RIAU": "SUMATERA", "JAMBI": "SUMATERA",
        "SUMATERA SELATAN": "SUMATERA", "KEPULAUAN BANGKA BELITUNG": "SUMATERA",
        "BENGKULU": "SUMATERA", "LAMPUNG": "SUMATERA",
        "KALIMANTAN BARAT": "KALIMANTAN", "KALIMANTAN TENGAH": "KALIMANTAN",
        "KALIMANTAN SELATAN": "KALIMANTAN", "KALIMANTAN TIMUR": "KALIMANTAN",
        "KALIMANTAN UTARA": "KALIMANTAN",
        "SULAWESI UTARA": "SULAWESI", "GORONTALO": "SULAWESI",
        "SULAWESI TENGAH": "SULAWESI", "SULAWESI SELATAN": "SULAWESI",
        "SULAWESI BARAT": "SULAWESI", "SULAWESI TENGGARA": "SULAWESI",
        "BALI": "KEPULAUAN NUSA TENGGARA DAN BALI",
        "NUSA TENGGARA BARAT": "KEPULAUAN NUSA TENGGARA DAN BALI",
        "NUSA TENGGARA TIMUR": "KEPULAUAN NUSA TENGGARA DAN BALI",
        "MALUKU": "MALUKU DAN PAPUA", "MALUKU UTARA": "MALUKU DAN PAPUA",
        "PAPUA": "MALUKU DAN PAPUA", "PAPUA BARAT": "MALUKU DAN PAPUA",
        "PAPUA SELATAN": "MALUKU DAN PAPUA", "PAPUA TENGAH": "MALUKU DAN PAPUA",
        "PAPUA PEGUNUNGAN": "MALUKU DAN PAPUA", "PAPUA BARAT DAYA": "MALUKU DAN PAPUA"
    }

    df_prov = df.groupby("WADMPR")[agg_columns].sum().reset_index()
    df_prov = pd.merge(
        left=shp_prov[["WADMPR", "geometry"]],
        right=df_prov,
        on="WADMPR",
        how="left"
    )

    df_pulau = df_prov.copy()
    df_pulau["PULAU"] = df_pulau["WADMPR"].map(provinsi_ke_pulau)
    df_pulau = df_pulau.groupby("PULAU")[agg_columns].sum().reset_index()

    df_kab = df.groupby(["WADMKK", "WADMPR"])[agg_columns].sum().reset_index()
    df_kab = pd.merge(
        left=shp_kab[["WADMKK", "WADMPR", "geometry"]],
        right=df_kab,
        on=["WADMKK", "WADMPR"],
        how="left"
    )

    df_kec = df.groupby(["WADMKC", "WADMKK", "WADMPR"])[agg_columns].sum().reset_index()
    df_kec = pd.merge(
        left=shp_kec[["WADMKC", "WADMKK", "WADMPR", "geometry"]],
        right=df_kec,
        on=["WADMKC", "WADMKK", "WADMPR"],
        how="left"
    )

    # Booking Data
    df_book = pd.read_parquet("Data Fix/Data Booking AGG_v4.parquet")
    df_book.columns = ["_".join(map(str, col)).strip("_") for col in df_book.columns.values]

    agg_columns_book = df_book.select_dtypes(include="number").columns

    df_book_prov = df_book.groupby("WADMPR")[agg_columns_book].sum().reset_index()
    df_book_prov = pd.merge(
        left=shp_prov[["WADMPR", "geometry"]],
        right=df_book_prov,
        on="WADMPR",
        how="left"
    )

    df_book_kab = df_book.groupby(["WADMKK", "WADMPR"])[agg_columns_book].sum().reset_index()
    df_book_kab = pd.merge(
        left=shp_kab[["WADMKK", "WADMPR", "geometry"]],
        right=df_book_kab,
        on=["WADMKK", "WADMPR"],
        how="left"
    )

    df_book_kec = df_book.groupby(["WADMKC", "WADMKK", "WADMPR"])[agg_columns_book].sum().reset_index()
    df_book_kec = pd.merge(
        left=shp_kec[["WADMKC", "WADMKK", "WADMPR", "geometry"]],
        right=df_book_kec,
        on=["WADMKC", "WADMKK", "WADMPR"],
        how="left"
    )

    return df_cab, df_dealer, df_pulau, df_prov, df_kab, df_kec, df_book_prov, df_book_kab, df_book_kec

df_cab, df_dealer, df_pulau, df_prov, df_kab, df_kec, df_book_prov, df_book_kab, df_book_kec = preparing_data()

# st.dataframe(df_prov)

# ----------------------------------------------------------------- Session States -----------------------------------------------------------------

bounds_start = df_prov.geometry.total_bounds
min_longitude_start, min_latitude_start, max_longitude_start, max_latitude_start = bounds_start

center_latitude_start = (min_latitude_start + max_latitude_start) / 2
center_longitude_start = (min_longitude_start + max_longitude_start) / 2
center_start = [center_latitude_start, center_longitude_start]

zoom_start = 5

if "clicked_district" not in st.session_state:
    st.session_state.clicked_district = None
if "clicked_city" not in st.session_state:
    st.session_state.clicked_city = None
if "clicked_province" not in st.session_state:
    st.session_state.clicked_province = None
if "center" not in st.session_state:
    st.session_state.center = center_start
if "zoom" not in st.session_state:
    st.session_state.zoom = zoom_start
if "show_cabang" not in st.session_state:
    st.session_state.show_cabang = False
if "show_pos" not in st.session_state:
    st.session_state.show_pos = False
if "show_dealer" not in st.session_state:
    st.session_state.show_dealer = False
if "show_pos_dealer" not in st.session_state:
    st.session_state.show_pos_dealer = False
if "show_kompetitor" not in st.session_state:
    st.session_state.show_kompetitor = False

start_quarter_clicked = st.session_state.get("selected_quarter", ("2019", "2024Q4"))[0]
end_quarter_clicked = st.session_state.get("selected_quarter", ("2019", "2024Q4"))[1]
buss_unit_clicked = st.session_state.get("selected_buss_unit", "ALL")
display_option = st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)")

# ----------------------------------------------------------------- Customer Growth Map -----------------------------------------------------------------

# Change Colormap
def change_colormap():
    st.session_state.use_percentage = st.session_state.get("toggle_state", True)

# Add Colormap
def create_colormap(data, display_option, threshold):
    if display_option == "Pertumbuhan Customer (%)":
        column = "MAP_GROWTH"
        caption = "Pertumbuhan Customer Secara Nasional (%)"
        colors = ["#ffffd9", "#41b6c4", "#081d58"]  # Blue-ish palette

        colormap = branca.colormap.LinearColormap(
            vmin=data[column].quantile(0.0),
            vmax=data[column].quantile(1.0),
            colors=colors,
            caption=caption
        )
        
    elif display_option == "Pertumbuhan Customer":
        column = "MAP_GROWTH_NUMBER"
        caption = "Pertumbuhan Customer Secara Nasional"
        colors = ["#f7fcf5", "#41ab5d", "#005a32"]  # Green-ish palette

        colormap = branca.colormap.LinearColormap(
            vmin=data[column].quantile(0.0),
            vmax=data[column].quantile(1.0),
            colors=colors,
            caption=caption
        )
        
    elif display_option == "Rasio Customer dan Usia Produktif 2024 (%)":
        column = "MAP_PROD_AGE_RATIO"
        caption = f"Rasio Customer per {end_quarter_clicked} dan Usia Produktif 2024 Secara Nasional (%)"
        colors = ["#fff5f5", "#fc9272", "#de2d26"]  # Red-ish palette

        colormap = branca.colormap.LinearColormap(
            vmin=data[column].quantile(0.0),
            vmax=data[column].quantile(1.0),
            colors=colors,
            caption=caption
        )
        
    else:
        column = "MAP_CUST_RATIO"
        caption = f"Rasio Customer {buss_unit_clicked} dan ALL per {end_quarter_clicked} Secara Nasional (%)"
        
        if threshold is not None:
            vmin = data[column].min()
            vmax = data[column].max()
            index = [vmin, threshold, threshold, vmax]
            colors = ["#de2d26", "#fc9272", "#41b6c4", "#081d58"]
            
            colormap = branca.colormap.LinearColormap(
                colors=colors,
                index=index,
                vmin=vmin,
                vmax=vmax,
                caption=caption
            )
        else:
            colors = ["#fff8e1", "#ffcc80", "#ff8a65"]
            colormap = branca.colormap.LinearColormap(
                vmin=data[column].quantile(0.0),
                vmax=data[column].quantile(1.0),
                colors=colors,
                caption=caption
            )
    
    return colormap

# Add Tooltip
def create_tooltip(level="province"):
    fields = [
        "WADMPR",
        "TOOLTIP_MAP_GROWTH_NUMBER",
        "TOOLTIP_GROWTH",
        "Usia Produktif",
        "TOOLTIP_PROD_AGE_RATIO",
        "TOOLTIP_CUST_RATIO"
    ]
    aliases = [
        "Provinsi",
        f"Jumlah Customer per {start_quarter_clicked} -> {end_quarter_clicked}",
        "Pertumbuhan Customer",
        "Jumlah Penduduk Usia Produktif 2024",
        f"Rasio Customer per {end_quarter_clicked} dan Usia Produktif 2024",
        f"Rasio Customer {buss_unit_clicked} dan ALL per {end_quarter_clicked}"
    ]

    if level == "kabupaten":
        fields.insert(1, "WADMKK")
        aliases.insert(1, "Kabupaten/Kota")
    elif level == "kecamatan":
        fields.insert(1, "WADMKK")
        fields.insert(2, "WADMKC")
        aliases.insert(1, "Kabupaten/Kota")
        aliases.insert(2, "Kecamatan")

    return folium.GeoJsonTooltip(
        fields=fields,
        aliases=aliases,
        localize=True,
        sticky=False,
        labels=True
    )

# Map Stylings
def style_function(feature, colormap, display_option):
    if display_option == "Pertumbuhan Customer (%)":
        column = "MAP_GROWTH"
    elif display_option == "Pertumbuhan Customer":
        column = "MAP_GROWTH_NUMBER"
    elif display_option == "Rasio Customer dan Usia Produktif 2024 (%)":
        column = "MAP_PROD_AGE_RATIO"
    else:
        column = "MAP_CUST_RATIO"
    
    return {
        "fillColor": colormap(feature["properties"][column])
        if feature["properties"][column] is not None else "grey",
        "color": "#000000",
        "fillOpacity": 1,
        "weight": 1
    }

def style_function2(feature):
    return {
        "fillColor": "white",
        "color": "#000000",
        "fillOpacity": 1,
        "weight": 1
    }

def highlight_function(feature):
    return {
        "fillColor": "#000000",
        "color": "#000000",
        "fillOpacity": 0.8,
        "weight": 1
    }

# Map Interactions
def callback():
    if st.session_state["province_map"].get("last_clicked"):
        last_active_drawing = st.session_state["province_map"]["last_active_drawing"]

        if last_active_drawing and "properties" in last_active_drawing:
            if "WADMKC" in last_active_drawing["properties"]:
                clicked_district = last_active_drawing["properties"]["WADMKC"]
                clicked_city = last_active_drawing["properties"]["WADMKK"]
                clicked_province = last_active_drawing["properties"]["WADMPR"]

                if clicked_district != st.session_state.get("clicked_district"):
                    st.session_state.clicked_district = clicked_district
                    st.session_state.clicked_city = clicked_city
                    st.session_state.clicked_province = clicked_province

            elif "WADMKK" in last_active_drawing["properties"]:
                clicked_city = last_active_drawing["properties"]["WADMKK"]
                clicked_province = last_active_drawing["properties"]["WADMPR"]

                if clicked_city != st.session_state.get("clicked_city"):
                    st.session_state.clicked_district = None
                    st.session_state.clicked_city = clicked_city
                    st.session_state.clicked_province = clicked_province

            elif "WADMPR" in last_active_drawing["properties"]:
                clicked_province = last_active_drawing["properties"]["WADMPR"]

                if clicked_province != st.session_state.get("clicked_province"):
                    st.session_state.clicked_district = None
                    st.session_state.clicked_city = None
                    st.session_state.clicked_province = clicked_province

# Reset Map Views
def reset_to_province_view():
    st.session_state.clicked_district = None
    st.session_state.clicked_city = None
    st.session_state.clicked_province = None
    st.session_state.center = center_start
    st.session_state.zoom = zoom_start

def reset_to_city_view():
    st.session_state.clicked_district = None
    st.session_state.clicked_city = None

def reset_to_district_view():
    st.session_state.clicked_district = None

# Calculate Zoom
class FitBounds:
    def __init__(self, bounds, padding_top_left=None, padding_bottom_right=None, padding=None, max_zoom=None):
        self.bounds = bounds
        self.options = {
            "max_zoom": max_zoom,
            "padding_top_left": padding_top_left,
            "padding_bottom_right": padding_bottom_right,
            "padding": padding
        }
    
    def calculate_zoom(self, map_width=1026.67, map_height=450):
        from math import log2, pi, cos, radians
        
        southwest, northeast = self.bounds
        
        EARTH_RADIUS = 6378137
        
        lat_span = abs(northeast[0] - southwest[0])
        lon_span = abs(northeast[1] - southwest[1])
        
        lat_meters = lat_span * (111_000)
        lon_meters = lon_span * (111_000 * abs(cos(radians(southwest[0]))))
        
        resolution_lat = lat_meters / map_height
        resolution_lon = lon_meters / map_width
        resolution = max(resolution_lat, resolution_lon)
        
        zoom = log2(2 * pi * EARTH_RADIUS / (resolution * 256))
        
        if self.options["max_zoom"] is not None:
            zoom = min(zoom, self.options["max_zoom"])
        
        # return int(max(0, min(round(zoom), 18)))
        return zoom - 0.5

# Update Titles and Data
def update_titles_and_agg_vals():    
    global cust_title, booking_title, agg_vals, agg_vals_book  
    if st.session_state.clicked_district:    
        cust_title = f"Pertumbuhan Customer {"" if buss_unit_clicked == "ALL" else buss_unit_clicked} di {st.session_state.clicked_district}, {st.session_state.clicked_city}, {st.session_state.clicked_province}"    
        booking_title = f"Pertumbuhan Booking {"" if buss_unit_clicked == "ALL" else buss_unit_clicked} di {st.session_state.clicked_district}, {st.session_state.clicked_city}, {st.session_state.clicked_province}"    
        
        district_data = df_kec[    
            (df_kec["WADMPR"] == st.session_state.clicked_province) &     
            (df_kec["WADMKK"] == st.session_state.clicked_city) &    
            (df_kec["WADMKC"] == st.session_state.clicked_district)    
        ]    
        agg_vals = district_data.select_dtypes(include=np.number).sum(axis=0) if not district_data.empty else pd.Series({start_growth_col: 0, end_growth_col: 0})

        district_data_book = df_book_kec[    
            (df_book_kec["WADMPR"] == st.session_state.clicked_province) &     
            (df_book_kec["WADMKK"] == st.session_state.clicked_city) &    
            (df_book_kec["WADMKC"] == st.session_state.clicked_district)    
        ]    
        agg_vals_book = district_data_book.select_dtypes(include=np.number).sum(axis=0) if not district_data_book.empty else pd.Series({start_growth_col: 0, end_growth_col: 0})

    elif st.session_state.clicked_city:    
        cust_title = f"Pertumbuhan Customer {"" if buss_unit_clicked == "ALL" else buss_unit_clicked} di {st.session_state.clicked_city}, {st.session_state.clicked_province}"    
        booking_title = f"Pertumbuhan Booking {"" if buss_unit_clicked == "ALL" else buss_unit_clicked} di {st.session_state.clicked_city}, {st.session_state.clicked_province}"    
        
        city_data = df_kab[    
            (df_kab["WADMPR"] == st.session_state.clicked_province) &     
            (df_kab["WADMKK"] == st.session_state.clicked_city)    
        ]  
        agg_vals = city_data.select_dtypes(include=np.number).sum(axis=0) if not city_data.empty else pd.Series({start_growth_col: 0, end_growth_col: 0})

        city_data_book = df_book_kab[    
            (df_book_kab["WADMPR"] == st.session_state.clicked_province) &     
            (df_book_kab["WADMKK"] == st.session_state.clicked_city)    
        ]  
        agg_vals_book = city_data_book.select_dtypes(include=np.number).sum(axis=0) if not city_data_book.empty else pd.Series({start_growth_col: 0, end_growth_col: 0})

    elif st.session_state.clicked_province:    
        cust_title = f"Pertumbuhan Customer {"" if buss_unit_clicked == "ALL" else buss_unit_clicked} di {st.session_state.clicked_province}"    
        booking_title = f"Pertumbuhan Booking {"" if buss_unit_clicked == "ALL" else buss_unit_clicked} di {st.session_state.clicked_province}"
        
        province_data = df_prov[df_prov["WADMPR"] == st.session_state.clicked_province]    
        agg_vals = province_data.select_dtypes(include=np.number).sum(axis=0) if not province_data.empty else pd.Series({start_growth_col: 0, end_growth_col: 0})

        province_data_book = df_book_prov[df_book_prov["WADMPR"] == st.session_state.clicked_province]    
        agg_vals_book = province_data_book.select_dtypes(include=np.number).sum(axis=0) if not province_data_book.empty else pd.Series({start_growth_col: 0, end_growth_col: 0})
        
    else:
        cust_title = f"Pertumbuhan Customer {"" if buss_unit_clicked == "ALL" else buss_unit_clicked} Secara Nasional"    
        booking_title = f"Pertumbuhan Booking {"" if buss_unit_clicked == "ALL" else buss_unit_clicked} Secara Nasional" 
        
        agg_vals = df_prov.select_dtypes(include=np.number).sum(axis=0)
        agg_vals_book = df_book_prov.select_dtypes(include=np.number).sum(axis=0)

# Change Marker
def change_marker():
    st.session_state.show_cabang = (0 in st.session_state.marker_value)
    st.session_state.show_pos = (1 in st.session_state.marker_value)
    st.session_state.show_dealer = (2 in st.session_state.marker_value)
    st.session_state.show_pos_dealer = (3 in st.session_state.marker_value)
    st.session_state.show_kompetitor = (4 in st.session_state.marker_value)

# Add Marker
def add_markers(feature_group, data, category_column, category_value, name_column, address_column, lat_column, long_column, icon_url, icon_size):
    for row in data[data[category_column] == category_value].iterrows():
        name = row[1][name_column]
        address = row[1][address_column]

        if pd.isna(address):
            formatted_address = ""
        else:
            max_length = 50
            words = address.split(" ")
            formatted_address = ""
            current_line = ""

            for word in words:
                if len(current_line) + len(word) + 1 <= max_length:
                    current_line += f"{word} "
                else:
                    formatted_address += f"{current_line.strip()}<br>"
                    current_line = f"{word} "

            formatted_address += current_line.strip()

        tooltip = f"<b>{name}</b><br>{formatted_address}"

        feature_group.add_child(
            folium.Marker(
                [float(row[1][lat_column]), float(row[1][long_column])],
                tooltip=tooltip,
                icon=folium.features.CustomIcon(
                    icon_image=icon_url,
                    icon_size=icon_size
                )
            )
        )

# Create Map
def display_map(threshold):
    display_option = st.session_state.display_option

    if st.session_state.clicked_city:
        city_data = df_kab[
            (df_kab["WADMKK"] == st.session_state.clicked_city) &
            (df_kab["WADMPR"] == st.session_state.clicked_province)
        ]
        bounds = city_data.geometry.total_bounds

        folium_bounds = [
            [bounds[1], bounds[0]],
            [bounds[3], bounds[2]]
        ]

        center_latitude = (bounds[1] + bounds[3]) / 2
        center_longitude = (bounds[0] + bounds[2]) / 2
        current_center = [center_latitude, center_longitude]

        fit_bounds = FitBounds(folium_bounds)
        current_zoom = fit_bounds.calculate_zoom()
    elif st.session_state.clicked_province:
        province_data = df_prov[df_prov["WADMPR"] == st.session_state.clicked_province]
        bounds = province_data.geometry.total_bounds

        folium_bounds = [
            [bounds[1], bounds[0]],
            [bounds[3], bounds[2]]
        ]

        center_latitude = (bounds[1] + bounds[3]) / 2
        center_longitude = (bounds[0] + bounds[2]) / 2
        current_center = [center_latitude, center_longitude]

        fit_bounds = FitBounds(folium_bounds)
        current_zoom = fit_bounds.calculate_zoom()
    else:
        current_center = center_start
        current_zoom = zoom_start
        folium_bounds = [
            [min_latitude_start, min_longitude_start],
            [max_latitude_start, max_longitude_start]
        ]

    m = folium.Map(location=center_start, zoom_start=zoom_start)
    folium.TileLayer("CartoDB positron", name="Light Map", control=True).add_to(m)

    colormap = create_colormap(df_prov, display_option, threshold)

    folium.GeoJson(
        df_prov,
        style_function=lambda x: style_function(x, colormap, display_option),
        highlight_function=highlight_function,
        tooltip=create_tooltip("province")
    ).add_to(m)

    colormap.add_to(m)

    feature_group_to_add = folium.FeatureGroup(name="Cities")

    if st.session_state.clicked_province:
        city_data = df_kab[df_kab["WADMPR"] == st.session_state.clicked_province]

        feature_group_to_add.add_child(
            folium.GeoJson(
                df_prov,
                style_function=lambda x: style_function2(x),
                highlight_function=highlight_function,
                tooltip=create_tooltip("province")
            )
        )
        
        feature_group_to_add.add_child(
            folium.GeoJson(
                city_data,
                style_function=lambda x: style_function(x, create_colormap(city_data, display_option, threshold), display_option),
                highlight_function=highlight_function,
                tooltip=create_tooltip("kabupaten")
            )
        )

        if st.session_state.clicked_city:
            district_data = df_kec[
                (df_kec["WADMKK"] == st.session_state.clicked_city) &
                (df_kec["WADMPR"] == st.session_state.clicked_province)
            ]

            feature_group_to_add.add_child(
                folium.GeoJson(
                    city_data,
                    style_function=lambda x: style_function2(x),
                    highlight_function=highlight_function,
                    tooltip=create_tooltip("kabupaten")
                )
            )

            feature_group_to_add.add_child(
                folium.GeoJson(
                    district_data,
                    style_function=lambda x: style_function(x, create_colormap(district_data, display_option, threshold), display_option),
                    highlight_function=highlight_function,
                    tooltip=create_tooltip("kecamatan")
                )
            )

    if st.session_state.show_cabang:
        add_markers(
            feature_group=feature_group_to_add,
            data=df_cab,
            category_column="NETWORKING",
            category_value="CABANG",
            name_column="NAMA CABANG  / POS/ KIOS",
            address_column="ALAMAT KANTOR LENGKAP + NO + RT RW",
            lat_column="LAT",
            long_column="LONG",
            icon_url="https://media-hosting.imagekit.io//56388e054f0345c6/location_big_red.png?Expires=1837139208&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=PAfpTKvPq2r5JYPf3vyjWcaczQ55AFlws7cRPJGxKlyKgfZVwN-bH6O9TPJqTrmDqKdVeedIqLAmXurdWQg4Zz4PYQzOziEqhkrPnoUzHPaAvZhjNOJ767EpWTSmifxdJZSAiz0pzjaiSSQctvXkRKsu-yOTfiByMcQOgh8tFrDAspczLQPUAAKYChhh7tQNtougIkBFg~kiJ72sgDDXt6ltuAPERc8eF5iANy6FA~6T74l95pl~qBn3aHFYskkO5w9r-~X2bKez-fpgySMfva5f07yHzek~vuKbWPUoKhfH7x0O-xI7RbeNjw-gP8~ich1Cs-N2rbwLzY-7lZV~7w__",
            icon_size=(25, 25)
        )

    if st.session_state.show_pos:
        add_markers(
            feature_group=feature_group_to_add,
            data=df_cab,
            category_column="NETWORKING",
            category_value="POS",
            name_column="NAMA CABANG  / POS/ KIOS",
            address_column="ALAMAT KANTOR LENGKAP + NO + RT RW",
            lat_column="LAT",
            long_column="LONG",
            icon_url="https://media-hosting.imagekit.io//916d97dc3d4a4f84/location_big_red.png?Expires=1833702568&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=mi5ngwe2yTDvzBC87r-OtkvbJwV9t5urcCXeFwUoFfCGXRG0K58CV-4S1xONn2x4POu1U~9OEvFREF~51cthZBwP204faVTytxcfCQM3vymnJIqF-nlJeIRl9DYi-E9xAqpbHRiASv2V86fo-T1t0K8c7ss-RVjAOpkJKEoHqfQQrdB0dP~2EDTXngWyZL63cgGEavb7xGXlObjGK2Bt7BLTg-0kYzkKDCWqXbht4Yd61Si4Jlp24yVh2gQUlc6Q1ITED9xRn-0UTu3c0Bbg2SlsC1jpx2G1JHnT0r5Z-aVHhaUHgF8zGD15E3tshjNrnvHgWbshtIIZiFdxLikzhw__",
            icon_size=(25, 25)
        )

    if st.session_state.show_dealer:
        add_markers(
            feature_group=feature_group_to_add,
            data=df_dealer,
            category_column="CATEGORY",
            category_value="DEALER",
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://media-hosting.imagekit.io//0e140b0571a2446f/location_big_purple.png?Expires=1837138105&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=SqMKodB28X04OzOaYP-NCVywm1zqbllP3sSmN~USf4SMikH6tPoWLXyc4thnKOf5EScX63cw0QANtxgKcHSqpN1V4mRW0Aeoki0LVVhxbS5IPKcd1fJJ9dKjtwZPCE-ENijl7KK6ueZ1JmCVbh5RMpQl7Gj49Evk67oC0p0LpvMovautCD-Tl-tNhX5CCQH4Cvf50BShgSbvV~kOwxqr81DK5-v6qDPJAHkdK1RTvrCRDn3T0TAdRn2HqGGNZRy4YNHpy2bjYA7YJYvq9-EYJAlfZdpdWmjBvfLLbh9Rb-mJKLJhGIwOdUMYqKlUIsuHqbfx1w5kRNvlsubydORePA__",
            icon_size=(25, 25)
        )

    if st.session_state.show_pos_dealer:
        add_markers(
            feature_group=feature_group_to_add,
            data=df_dealer,
            category_column="CATEGORY",
            category_value="POS DEALER",
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://media-hosting.imagekit.io//1c6d17b3eaaa450d/location_big_purple.png?Expires=1835316806&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=J5ffnNIZs8n3oMCYG02cEPoWKHNf756qw0Qo7g89a-EGXfA2BB0eSbO77ePrT3E1ZBTXUzLrbVrZxNPX0TPp08bLjqtWoD-y7WK8oRWpV7jzd3QFbpLFLD7zVMyc4yzkZxSS~JotPCGsQSXJ4neyJ0gac5TgVUaJbDFiA4LJHxVdibBDcn1prK3N3YIwHdNndOMbMoqfsXj4y81mU1aSIEm-09XrtASctdsxGK9HM~DTOUXItnXCGrNYnYAEigwH3Qx7~~H8eFPtqZzSGWR6RkqyrtIAw~YrNAfgRgRxNwwD42WzucBSdgfd690bzeMgT6axXBykhq-Y0VRAoyW1gA__",
            icon_size=(25, 25)
        )

    if st.session_state.show_kompetitor:
        competitor_categories = df_dealer[df_dealer["CATEGORY"] == "COMPETITOR"]["COMPETITOR_CATEGORY"].unique()
        
        competitor_icons = {
            "ADIRA": "https://media-hosting.imagekit.io//3ab6b63b119944f1/location_big_yellow.png?Expires=1837137696&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=tgxTHdspw3XIoTLZpI3CERhxhO9zv~bmpxb1cmh~uNNwSChozqUMwteMMTPn47v0lt0DNoG28X0X4LPaXoxr8g76GER5~BZw1Ku7ktJ95~u3PFg0nhyaqHuaxyzTdO1zTXsyd5-7~mse9HVZrzAyIzxhZ~RyOa1WZEVpjjAw2rOrKUc~rgjc0a-lobjI6Xdo6CAvr-C3z8LjEAUvuq56-REaYGAWPQ7TaXAf649nXVQw~sTNyMprefrKAQGQIh8ZFbwzphrWYNATxoWeczHGYKg4STL-kM-hGES0Lrp0TpDowMkTflTOl1v7F~JpCEGQFQ2P67EkkRRSOjOhkIfOxQ__",
            "OTO": "https://media-hosting.imagekit.io//0dbcb40b4bc547b7/location_big_green.png?Expires=1833706712&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=qpbGTUg1MQUt2RM5h9YtXJg9JO-qF6Is9PZhvlHRVhodvgZ7NY2WcHIty~RT3YmDKDgEBxLthdjLW61u~j5O8exODuAptuPGzFqrns-a7JbQP3fhc0y1j~MeNLfY1ENxszTdV5T1c~qJVITdcx73yGr-i7oE41k3ydPr22DqOKarb~-jdyrAU01UsPHD8ZpGACY5e8hnNaqRnfR7y2391grRMlHcaFqTqIvfC9gFYa54cHjnytHxemek6kEdqh5M94Fo9F0E2eUO2c6N63pnY1Z5BfSOjuYhNS7X7YSkvwiPlzBDXgSc7DoJibA4ah8CH-RgZDxjvwiAtV4S76RA2Q__",
            "MEGA": "https://media-hosting.imagekit.io//9ee4206299b74ab3/location_big_orange.png?Expires=1833706712&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=NkPAC5Qu--UtZ6lqnBKGAFstauSu01KjaBWyPFXEbU3bdJyutIGp43gVth2WfpdQ~l146-rpH1Y1kQVGJi~I5m7qFvqVKQPSV0fUnyWzoHqyo6n~jrPNzI0CfOjQobqru1j-2rYd3vVt1nmUP~RXyDIsd~489268Gkq7SUzRGnxTsDEey~MIq9Il-bW0x9qESHbrfiGcG8KTLPmnfForgnG8Mos1YzHTEMIaegE0F6BD8rZSzqPUWDAMZdayMvN8h3GcfEl~Xp1j8H8VCui9JO6B9FMOX0gXRqdhGgLTihs-C8sOpog0yzO-yjsBaWm~U-FcDIoO6nFBGEXOBUuvOQ__",
            "BFI": "https://media-hosting.imagekit.io//faa7cc29b3874a4e/location_big_blue.png?Expires=1833706000&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=cF4lfi8pfKXYIUCiO46c3hxwQkru4gnuJMDRLiPNrQIpgfxdPS~cOsE4v3zBGF-jcHeGfJlUDiJKV3SRo-zLJm8TPE6MFrkHH3UX4OAlVZIHjaL8PgrxZ21G7CJVlzeBRQhhANA45ln21F9yV8~zWzKpqqWPi1SbeRqT~YbQDRYwyqV6IgUxSKX48QkLXl-bNnkqk4s8GMFsOg7D2tBf0oeS7UQ6K2XzGcIrx7W2fqQvvQMOsiAXsJ9FPD0daqNxmvA9Wm3I-zu0dtG7i9jGOUHUOmE~P5k2QpaATtfPe1q3j0C95kDmnJ2YIslvbyNjebjpV2FIJE6j7HI88nO6LQ__",
            "OTHERS": "https://media-hosting.imagekit.io//36cb33b320a6450d/location_big_grey.png?Expires=1833706712&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=FVB81lIRNbvtgysHIbbIa~6Z-CuKZTd9wm7Q0rEe4UYWI773w0If8YVwLPfEfWNJro1xI7gSlCPOIX2yGfKy67XFG7oCFODKisUXbXqsmneAuXT3~PkRIqw5eBgMr9a3GqgVKyFMfzRVgOWSnlIx1Q~Md-gLZ4Y-Pv6lomMNeF2pUjDTMqCTSluX4xOQuU-W4NaZWHVt7ei9uoES1qoTnP6fzDKetg7bmlCTScj5MQ7wZ-6TD9EgAo35fsjnTiU-4JecrnQNNEWHOS2igO2YA3KtTR3D1KjG-SBb~qz18jpjXKxPDzzCJrNT44ZvNBzRbkjgO0kgYcIoK9ztCqBStw__"
        }
        
        competitor_data = df_dealer[df_dealer["CATEGORY"] == "COMPETITOR"]
        
        for category in competitor_categories:
            icon_url = competitor_icons.get(category, competitor_icons["OTHERS"])
            category_data = competitor_data[competitor_data["COMPETITOR_CATEGORY"] == category]
            
            add_markers(
                feature_group=feature_group_to_add,
                data=category_data,
                category_column="CATEGORY",
                category_value="COMPETITOR",
                name_column="LOCATION_NAME",
                address_column="ADDRESS",
                lat_column="LATITUDE",
                long_column="LONGITUDE",
                icon_url=icon_url,
                icon_size=(25, 25)
            )

    st_folium(
        m,
        use_container_width=True,
        height=450,
        center=current_center,
        zoom=current_zoom,
        feature_group_to_add=feature_group_to_add,
        key="province_map",
        returned_objects=["last_clicked", "last_active_drawing"],
        on_change=callback
    )

# ----------------------------------------------------------------- Booking Growth Metrics -----------------------------------------------------------------

# Number Formatting
def format_number(num):
    if pd.isna(num):
        return "0"
    return f"{int(num):,}"

# Create Metrics
def create_metric_html(data_previous, data_previous_BA4, data_current, data_current_BA4, logo_url, others=False):
    total_book_previous = data_previous 
    total_book_current = data_current
    total_book_growth = ((total_book_current - total_book_previous) / total_book_previous * 100) if total_book_previous != 0 else 0  
    
    def format_growth(value, is_bad_contract=False):
        if value > 0:
            color = "#ff0000" if is_bad_contract else "#28a745"
            symbol = "▲"
        elif value == 0:
            color = "#4c5773"
            symbol = ""
        else:
            color = "#28a745" if is_bad_contract else "#ff0000"
            symbol = "▼"
        return f'<span style="color: {color};">{symbol} {value:,.2f}%</span>'

    image_section = f"""
        <div style="flex-shrink: 0;">
            <img src="{logo_url}.jpg" alt="Descriptive text" 
                style="width: 65px; height: 65px; object-fit: cover; border-radius: 8px;">
        </div>
    """ if not others else f"""
        <div style="flex-shrink: 0; width: 65px; height: 65px; display: flex; justify-content: center; align-items: center;">
            <span style="font-size: 15px; font-weight: bold; color: #4c5773;">OTHERS</span>
        </div>
    """

    return f"""
        <div style="display: grid; grid-template-columns: 80px 1fr 1fr 100px; align-items: center; gap: 15px;">
            {image_section}
            <div style="font-size: 15px; text-align: left;">
                <strong>As of {start_quarter_clicked}</strong>
                <br>
                <span style="color: #2c3858;">{format_number(total_book_previous)}</span>
                <br>
            </div>
            <div style="font-size: 15px; text-align: left;">
                <strong>As of {end_quarter_clicked}</strong>
                <br>
                <span style="color: #2c3858;">{format_number(total_book_current)}</span>
                <br>
            </div>
            <div style="font-size: 17px; font-weight: bold; text-align: center; color: #4c5773;">
                {format_growth(total_book_growth)}
            </div>
        </div>
    """

# ----------------------------------------------------------------- Filters -----------------------------------------------------------------

def update_filter():
    st.session_state.selected_quarter = st.session_state.quarter
    st.session_state.selected_buss_unit = st.session_state.buss_unit
    st.session_state.selected_sorter = st.session_state.display_option
    
    if st.session_state.display_option == "Rasio Customer (> 1x) dan ALL (%)":
        st.session_state.filtered_buss_unit_options = [
            option for option in buss_unit_options
            if option not in ["ALL", "NMC", "REFI", "MPF"]
        ]
        
        if st.session_state.selected_buss_unit in ["ALL", "NMC", "REFI", "MPF"]:
            st.session_state.selected_buss_unit = st.session_state.filtered_buss_unit_options[0]
    else:
        st.session_state.filtered_buss_unit_options = buss_unit_options

# ----------------------------------------------------------------- Customer Growth Trend -----------------------------------------------------------------

def generate_trend_html(df, region_col, column_suffix, start_quarter, end_quarter, top_n, title, show_all=False):
    growth_cols = [col for col in df.columns if col.endswith(column_suffix) and 
                start_quarter <= col.split("_")[0] <= end_quarter and 
                "MAP" not in col and "TOOLTIP" not in col]
    
    growth_cols.sort()

    if show_all:
        actual_top_n = df[region_col].nunique()
    else:
        actual_top_n = top_n
    
    html = f"""
    <div style="margin-top: 20px; margin-bottom: 10px;">
        <div style="font-size: 15px; font-weight: bold; color: #0458af; margin-bottom: 8px;">{title}</div>
        <div class="trend-table" style="width: 100%; overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; box-shadow: 0 2px 3px rgba(0,0,0,0.1); font-size: 12px;">
                <thead>
                    <tr>
                        <th style="background-color: #f2f2f2; padding: 6px; text-align: left; border-bottom: 2px solid #dddddd; position: sticky; top: 0;">Ranking</th>
    """
    
    for col in growth_cols:
        quarter = col.split("_")[0]
        html += f"""
                        <th colspan="2" style="background-color: #f2f2f2; padding: 6px; text-align: center; border-bottom: 2px solid #dddddd; position: sticky; top: 0;">{quarter}</th>
        """
    
    html += """
                    </tr>
                    <tr>
                        <th style="background-color: #f8f8f8; padding: 5px; text-align: left; border-bottom: 1px solid #dddddd; position: sticky; top: 28px;"></th>
    """
    
    for _ in growth_cols:
        html += """
                        <th style="background-color: #f8f8f8; padding: 5px; text-align: left; border-bottom: 1px solid #dddddd; position: sticky; top: 28px;">Wilayah</th>
                        <th style="background-color: #f8f8f8; padding: 5px; text-align: right; border-bottom: 1px solid #dddddd; position: sticky; top: 28px;">Nilai</th>
        """
    
    html += """
                    </tr>
                </thead>
                <tbody>
    """
    
    for rank in range(1, actual_top_n + 1):
        html += f"""
                    <tr>
                        <td style="padding: 5px; text-align: center; border-bottom: 1px solid #eeeeee; font-weight: bold;">{rank}</td>
        """
        
        prev_region = None
        
        for col in growth_cols:
            top_regions = df.sort_values(by=col, ascending=False).head(actual_top_n)
            if rank <= len(top_regions):
                region = top_regions.iloc[rank-1][region_col]
                value = top_regions.iloc[rank-1][col]
                
                highlight = ""
                if prev_region is not None and region != prev_region:
                    highlight = "background-color: rgba(65, 182, 196, 0.3);"
                
                html += f"""
                        <td style="padding: 5px; text-align: left; border-bottom: 1px solid #eeeeee; {highlight}">{region}</td>
                        <td style="padding: 5px; text-align: right; border-bottom: 1px solid #eeeeee; {highlight} font-weight: bold;">{format_func(value)}</td>
                """
                prev_region = region
            else:
                html += """
                        <td style="padding: 5px; text-align: left; border-bottom: 1px solid #eeeeee;">-</td>
                        <td style="padding: 5px; text-align: right; border-bottom: 1px solid #eeeeee;">-</td>
                """
        
        html += """
                    </tr>
        """
    
    html += """
                </tbody>
            </table>
        </div>
    </div>
    """
    
    return html

# ----------------------------------------------------------------- Main App -----------------------------------------------------------------

# Header    
col1, col2, col3 = st.columns([0.7, 3, 1], vertical_alignment="center")    
with col1:    
    st.image("Logo/FIFGROUP.png", use_container_width=True)    

with col2:    
    st.html(    
        """    
        <p style="    
            font-size: 30px;    
            color: #0458af;    
            margin: 0;    
            font-weight: bold;  
        ">    
            Dashboard Pertumbuhan Customer FIFGROUP    
        </p>    
        """    
    )    

specific_time = datetime(2024, 12, 17, 17, 19)    
formatted_time = specific_time.strftime("%Y-%m-%d %H:%M")    

with col3:    
    st.html(    
        f"""    
        <p style="    
            font-size: 14px;    
            color: #4c5773;    
            margin: 0;    
            text-align: right;    
        ">    
            Data last updated: {formatted_time}    
        </p>    
        """    
    )    

st.write("")

# Filters
quarter_options = [
    "2019", "2020Q1", "2020Q2", "2020Q3", "2020Q4", 
    "2021Q1", "2021Q2", "2021Q3", "2021Q4", 
    "2022Q1", "2022Q2", "2022Q3", "2022Q4", 
    "2023Q1", "2023Q2", "2023Q3", "2023Q4", 
    "2024Q1", "2024Q2", "2024Q3", "2024Q4"
]

buss_unit_options = [
    "ALL", "ALL (> 1x)", "NMC", "NMC (> 1x)", "NMC to REFI", "NMC to MPF", 
    "REFI", "REFI (> 1x)", "REFI to NMC", "REFI to MPF", 
    "MPF", "MPF (> 1x)", "MPF to NMC", "MPF to REFI",
]

if "filtered_buss_unit_options" not in st.session_state:
    if st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)") == "Rasio Customer (> 1x) dan ALL (%)":
        st.session_state.filtered_buss_unit_options = [
            option for option in buss_unit_options
            if option not in ["ALL", "NMC", "REFI", "MPF"]
        ]
    else:
        st.session_state.filtered_buss_unit_options = buss_unit_options

sorter_options = [
    "Pertumbuhan Customer (%)", 
    "Pertumbuhan Customer", 
    "Rasio Customer dan Usia Produktif 2024 (%)", 
    "Rasio Customer (> 1x) dan ALL (%)"
]

col1, col2, col3 = st.columns(3)

with col1:
    quarter = st.select_slider(
        label="Pilih Range Waktu:",
        options=quarter_options,
        value=("2019", "2024Q4"),
        key="quarter",
        on_change=update_filter,
        help="Geser slider ini untuk melihat pertumbuhan pada range quarter tertentu"
    )

with col2:
    default_buss_unit = st.session_state.get("selected_buss_unit", "ALL")
    current_options = st.session_state.filtered_buss_unit_options
    
    if default_buss_unit in current_options:
        default_buss_unit_index = current_options.index(default_buss_unit)
    else:
        default_buss_unit_index = 0
    
    buss_unit = st.selectbox(
        label="Pilih Business Unit:",
        options=current_options,
        index=default_buss_unit_index,
        key="buss_unit",
        on_change=update_filter,
        help="Klik dropdown ini untuk melihat pertumbuhan pada business unit tertentu"
    )

start_growth_col = f"{start_quarter_clicked}_CUST_NO"
end_growth_col = f"{end_quarter_clicked}_CUST_NO"

with col3:
    default_sorter = st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)")
    if default_sorter in sorter_options:
        default_sorter_index = sorter_options.index(default_sorter)
    else:
        default_sorter_index = 0
    
    display_option = st.selectbox(
        label="Pilih Metrik:",
        options=sorter_options,
        index=default_sorter_index,
        key="display_option",
        on_change=update_filter,
        help="Klik dropdown ini untuk melihat pertumbuhan berdasarkan metrik tertentu"
    )

# Data Preprocessing
df_pulau, df_prov, df_kab, df_kec = calculate_growth(df_pulau, df_prov, df_kab, df_kec)

df_book_prov = process_df_booking(df_book_prov)
df_book_kab = process_df_booking(df_book_kab)
df_book_kec = process_df_booking(df_book_kec)

# st.dataframe(df_prov)

# Customer Growth Title
with st.container(key="styled_container1"):
    col1 = st.columns(1)

    update_titles_and_agg_vals()
    total_cust_previous = agg_vals[start_growth_col]  
    total_cust_current = agg_vals[end_growth_col]  
    cust_growth = ((total_cust_current - total_cust_previous) / total_cust_previous * 100) if total_cust_previous != 0 else 0

    cust_growth_number = agg_vals[f"{end_quarter_clicked}_GROWTH_NUMBER"]
    cust_growth_number_all = agg_vals[f"{end_quarter_clicked}_GROWTH_NUMBER_ALL"]
    cust_ratio_threshold = cust_growth_number / cust_growth_number_all * 100

    growth_color = '#28a745' if cust_growth > 0 else '#ff0000' if cust_growth < 0 else '#4c5773'  
    growth_symbol = "▲" if cust_growth > 0 else "▼" if cust_growth < 0 else ""  

    with col1[0]:
        st.html(
            f'''  
                <div style="display: flex; justify-content: space-between; align-items: center;">  
                    <div style="font-size: 18px; font-weight: bold; color: #0458af;">{cust_title}</div>  
                    <div style="text-align: right; display: flex; align-items: center;">  
                        <div style="font-size: 16px; margin-right: 10px;">  
                            <strong>As of {start_quarter_clicked}</strong>: {int(total_cust_previous):,} | <strong>As of {end_quarter_clicked}</strong>: {int(total_cust_current):,}  
                        </div>  
                        <div style="font-size: 18px; font-weight: bold; color: {growth_color};">  
                            {growth_symbol} {cust_growth:.2f}%  
                        </div>  
                    </div>  
                </div>  
            '''
        )

# Customer Growth Map & Booking Growth Metrics
col1, col2 = st.columns([2.43, 1], vertical_alignment="center")

# Customer Growth Map
with col1:
    with st.container(key="styled_container2"):
        map_col = st.columns(1)
        with map_col[0]:
            display_map(threshold=cust_ratio_threshold)

        markers, btn1, btn2, btn3 = st.columns([1, 0.25, 0.25, 0.25], vertical_alignment="center")
        
        with markers:
            option_map = {
                0: "![Cabang](https://media-hosting.imagekit.io//092448b4fd924e0f/location_small_red.png?Expires=1837139208&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=NORj31V12WGKblE~nZZB5uJn-HVNeLbZrXrSflXPsOz8UA9DGlZfEMcoDoHjn3zY3A8Xla3yCTUXSkSDRh0IvkxrgcKnrXv1DVQ2Vdxrq2R-rBf3VkFoYo9hVcO56bZSb2nbtMiQMu5gGTkmZ~VE5016m-PLty5MCopcITF4xl13kpOgyCSKL6T-~eKB2fx2WGcb9zOqbniUWz7i14snzxAAMLG746ZPFXuupfuvnhl06GKM6xra5-R~RpNgVkWJfr7O712Qyi~H-ujp9ycadaemU6oP9Yz~Ros~7YhaXtYjacxgRAmjxtN1Vo6JOArYZwbGZvPOMYMT4LcucZXXqg__) Cabang",
                1: "![Pos](https://media-hosting.imagekit.io//d8c4bb9381014e38/location_small_red.png?Expires=1833702568&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=Hn~d3UHE6SbdU7oaVEA6j83hS0rPxVHK0lkYQtokSZalCAQmyydVjBnTgB5vix3Cxc889r3HcvFBgzW51wpQUyqj4XWvSmcNHu~2HOmFvYzAgLoSgPBglHhNv4WkYNBFqxd6Iz2fXlsNGuwrqrhYU2S5fxwzL3aOykOrM-~UlPG9Z6n8KQqUjFT0IZz2FJ7LkCPNY~gA-NzBGoJVZ2eJkMMzGaMc0t23lj1u3irJPLn3GXO2nkjdCAzSroTYa75YT-9FMrZVlZ4yavO58k36FBPbw0WnDRwIjOg67k1fLyBHk8l5Q1uNixINO6paMRtOwCMiM~I93yum6F7rQ48~MA__) Pos",
                2: "![Dealer](https://media-hosting.imagekit.io//0aa681a5d5ef4daa/location_small_purple.png?Expires=1837138105&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=GfQ3lqDCxnwkWF5sM76u15pV4Pqf3K5TBuYnIaSadtmNGiJGx7JB6eiVrZmNK69~pAPmxkp~ipwtRhA9r4cvUP0iki39M~foDxl4Pv5FC1mnlZiryNOujCKZYVvuwyXA1k07FjRK1WV1rqTk8HzQe3s3tI7G8FZPdrAT5xkXb~EBusXo-AXqiIfuH~z-wEGVewf5TVO0~uF~g2cwRYi7nEsli71ihTo18wEpFYvjRqFRmL~~wyclNL8YiYw1J9CnTptmG9jQtA8m~CYbpVpaZNqniN4o-2G89kSCgkkVJjWwjUD1sLS4WPlgcTHoQckpR7xSY7f~bMCkVqgoCBrftQ__) Dealer",
                3: "![Pos Dealer](https://media-hosting.imagekit.io//6676c198b4734566/location_small_purple.png?Expires=1835316806&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=HosAkPCzFeFkrM4A6UtW9dGbBDuODfspcOkfQJKVkSNs-LXW0TW39J3RwgB3cLkgyJB9RZsBjlDXveWYPLU~myfEW9XqLxrZHQcq6xzKwDgwZLY08o2BbGdm1TjUozxgs3RjlVcCUITXdUPx522rKdmI4c9R75kFiaMhROspnZTjpbZYdWJmRAVS3-UDLvxmLIDLNoUQtb5MIwlwxVbNA4noRPGSaZK5HG1v192kCLYRzIuN6enLYkIhEEgKTnMOnAq2aiE8Fmne8kSGbFDOUN9gGnJSc1cYU3WOaDHGCa9dlRlg4cW9-3d6sjq2r6GdsnYsIsPajfQvSI567qy-Fg__) Pos Dealer",
                4: "![Kompetitor](https://media-hosting.imagekit.io//1c7b4e580097439e/location_small_grey.png?Expires=1833706712&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=w6fvp3GzkHGSXkiZunFR5GdZ2~CwAz9zfkdsAE1yXxfn0InFqvviRQlt2nRy3q1wrOEt7qU36zcbkwUHDKEL40F4pZzcWKREU4l~fcWQLkkUDnSBPsJD-Ds6eWRl1cprz-x5oxwZ~FZh900YNOyyU3lETbC2YXOcdlWCJEQVf1fOSrzvcOjShyN0ig0GR2baepSUXyIwZ~EvuFVwupsSCc5JzWLXVeHLWxMJgFkH~7pGEWEN439EsXDwVOvB358uCyvtfHbPsbPaycWfDXiElFy7x~XgIUa~UdSEBU6Y7qAvPYovqHVPnMrnysWsIoTm~f4L~AS6qqr7HVXCk6webQ__) Kompetitor"
            }

            selection = st.segmented_control(
                "Lokasi",
                options=option_map.keys(),
                format_func=lambda option: option_map[option],
                selection_mode="multi",
                label_visibility="collapsed",
                key="marker_value",
                on_change=change_marker
            )

        with btn1:
            st.button(
                "Country",
                disabled=not st.session_state.clicked_province,
                use_container_width=True,
                on_click=reset_to_province_view,
                type="primary",
                icon="↩",
                help="Klik untuk kembali ke peta Indonesia"
            )
        
        with btn2:
            if st.session_state.clicked_city:
                btn2_help = f"Klik untuk kembali ke peta {st.session_state.clicked_province}"
            else:
                btn2_help = "Klik untuk kembali ke peta provinsi"

            st.button(
                "Province",
                disabled=not st.session_state.clicked_city,
                use_container_width=True,
                on_click=reset_to_city_view,
                type="primary",
                icon="↩",
                help=btn2_help
            )
        
        with btn3:
            if st.session_state.clicked_district:
                btn3_help = f"Klik untuk kembali ke peta {st.session_state.clicked_city}"
            else:
                btn3_help = "Klik untuk kembali ke peta kabupaten/kota"

            st.button(
                "City",
                disabled=not st.session_state.clicked_district,
                use_container_width=True,
                on_click=reset_to_district_view,
                type="primary",
                icon="↩",
                help=btn3_help
            )

# Booking Growth Metrics
with col2:
    with st.container(key="styled_container9"):
        col1 = st.columns(1)
        
        with col1[0]:
            st.html(
                f'''  
                    <div style="font-size: 18px; font-weight: bold; color: #0458af;">Pertumbuhan Booking {"" if buss_unit_clicked == "ALL" else buss_unit_clicked}</div>  
                '''
            )

    business_units = [
        {"key": "NMC", "logo": "https://images.seeklogo.com/logo-png/56/2/fifastra-fif-group-logo-png_seeklogo-568347.png?v=1957804521000083520"},
        {"key": "MPF", "logo": "https://images.seeklogo.com/logo-png/56/1/spektra-fif-group-logo-png_seeklogo-568351.png?v=1957832117710626200"},
        {"key": "REFI", "logo": "https://images.seeklogo.com/logo-png/56/1/danastra-fifgroup-logo-png_seeklogo-568382.png?v=1957832698430771696"},
        {"key": "MMU", "logo": "https://images.seeklogo.com/logo-png/56/1/amitra-fifgroup-logo-png_seeklogo-568381.png?v=1957802152858011120"},
        {"key": "OTHERS", "logo": "", "others": True}
    ]

    for i, unit in enumerate(business_units, start=4):
        with st.container(key=f"styled_container{i}"):
            col1 = st.columns(1)

            with col1[0]:
                st.html(
                    create_metric_html(
                        agg_vals_book[f"{start_quarter_clicked}_{unit['key']}"],
                        agg_vals_book[f"{start_quarter_clicked}_{unit['key']}_BA4"],
                        agg_vals_book[f"{end_quarter_clicked}_{unit['key']}"],
                        agg_vals_book[f"{end_quarter_clicked}_{unit['key']}_BA4"],
                        unit.get("logo", ""),
                        others=unit.get("others", False)
                    )
                )

# Customer Growth Trend Line Chart
with st.container(key="styled_container3"):
    col1 = st.columns(1)
    with col1[0]:
        title_text = f"Tren {display_option} {"" if buss_unit_clicked == "ALL" else buss_unit_clicked}"
        
        st.html(
            f'''
            <div style="font-size: 18px; font-weight: bold; color: #0458af;">{title_text}</div>
            '''
        )

        st.html(
            """
            <div style="background-color: #e7f3fe; border-left: 6px solid #2196F3; padding: 10px 15px; font-size: 15px; line-height: 1.5;">
                Pada 13 April 2020 (2020Q2), Presiden Jokowi menetapkan kondisi pandemi COVID-19 di Indonesia sebagai bencana nonalam nasional melalui Keppres Nomor 12 Tahun 2020.
            </div>
            """
        )

        quarters = [f"2019"] + [f"{year}Q{quarter}" for year in range(2020, 2025) for quarter in range(1, 5)]
        altair_data = pd.DataFrame({
            "Quarter": quarters,
            "Growth": [np.nan] + [(agg_vals[f"{q}_CUST_NO"] - agg_vals[f"{quarters[i]}_CUST_NO"]) / agg_vals[f"{quarters[i]}_CUST_NO"] if agg_vals[f"{quarters[i]}_CUST_NO"] != 0 else np.nan for i, q in enumerate(quarters[1:])],
            "Growth_Number": [np.nan] + [agg_vals[f"{q}_CUST_NO"] - agg_vals[f"{quarters[i]}_CUST_NO"] for i, q in enumerate(quarters[1:])],
            "Growth_Number_All": [np.nan] + [agg_vals[f"{q}_CUST_NO_TOTAL"] - agg_vals[f"{quarters[i]}_CUST_NO_TOTAL"] for i, q in enumerate(quarters[1:])],
            "Prod_Age_Ratio": [agg_vals[f"{q}_CUST_NO"] / agg_vals["Usia Produktif"] for q in quarters],
            "Current_Cust": [agg_vals[f"{q}_CUST_NO"] for q in quarters],
            "Previous_Cust": [np.nan] + [agg_vals[f"{quarters[i]}_CUST_NO"] for i in range(len(quarters) - 1)]
        })
        altair_data["Cust_Ratio"] = altair_data["Growth_Number"] / altair_data["Growth_Number_All"]

        altair_data = altair_data[
            (altair_data["Quarter"] >= start_quarter_clicked) & 
            (altair_data["Quarter"] <= end_quarter_clicked)
        ]
        
        filtered_data = altair_data[altair_data["Quarter"] != ""].dropna()
        
        if display_option == "Pertumbuhan Customer (%)":
            metric_for_line = "Growth"
            y_title_line = "Pertumbuhan Customer (%)"
            y_format_line = "%"
            if not filtered_data.empty:
                max_idx = filtered_data["Growth"].idxmax()
                max_quarter = filtered_data.loc[max_idx, "Quarter"]
            else:
                max_quarter = None
        elif display_option == "Pertumbuhan Customer":
            metric_for_line = "Growth_Number"
            y_title_line = "Pertumbuhan Customer"
            y_format_line = "~s"
            if not filtered_data.empty:
                max_idx = filtered_data["Growth_Number"].idxmax()
                max_quarter = filtered_data.loc[max_idx, "Quarter"]
            else:
                max_quarter = None
        elif display_option == "Rasio Customer dan Usia Produktif 2024 (%)":
            metric_for_line = "Prod_Age_Ratio"
            y_title_line = "Rasio Customer dan Usia Produktif 2024 (%)"
            y_format_line = "%"
            if not filtered_data.empty:
                max_idx = filtered_data["Prod_Age_Ratio"].idxmax()
                max_quarter = filtered_data.loc[max_idx, "Quarter"]
            else:
                max_quarter = None
        else:
            metric_for_line = "Cust_Ratio"
            y_title_line = "Rasio Customer (> 1x) dan ALL (%)"
            y_format_line = "%"
            if not filtered_data.empty:
                max_idx = filtered_data["Cust_Ratio"].idxmax()
                max_quarter = filtered_data.loc[max_idx, "Quarter"]
            else:
                max_quarter = None
        
        altair_data["Highlight"] = altair_data["Quarter"] == max_quarter
        
        bar_chart = alt.Chart(altair_data).mark_bar(
            cornerRadiusTopLeft=8,
            cornerRadiusTopRight=8,
            opacity=0.7
        ).encode(
            x=alt.X(
                "Quarter:N",
                title=None,
                axis=alt.Axis(labelAngle=0, labelOverlap=False, tickCount=len(altair_data))
            ),
            y=alt.Y(
                "Current_Cust:Q",
                title="Jumlah Customer",
                axis=alt.Axis(grid=False, format="~s"),
                scale=alt.Scale(zero=True)
            ),
            color=alt.condition(
                "datum.Highlight == true",
                alt.value("#023E8A"),
                alt.value("#41b6c4")
            ),
            tooltip=[
                alt.Tooltip("Quarter:N", title="Quarter"),
                alt.Tooltip("Current_Cust:Q", title="Jumlah Kumulatif Customer", format=",d"),
                alt.Tooltip("Growth_Number:Q", title="Pertumbuhan Customer", format=",d"),
                alt.Tooltip("Growth:Q", title="Pertumbuhan Customer (%)", format=".2%"),
                alt.Tooltip("Prod_Age_Ratio:Q", title="Rasio Customer dan Usia Produktif (%)", format=".2%")
            ]
        )

        line_base = alt.Chart(altair_data).mark_line(
            color="#0458af",
            strokeWidth=3
        ).encode(
            x=alt.X(
                "Quarter:N",
                title=None,
                axis=alt.Axis(labelAngle=0, labelOverlap=False, tickCount=len(altair_data))
            ),
            y=alt.Y(
                f"{metric_for_line}:Q",
                title=y_title_line,
                axis=alt.Axis(grid=False, format=y_format_line),
                scale=alt.Scale(zero=True)
            )
        )
        
        points = alt.Chart(altair_data).mark_circle(size=100).encode(
            x="Quarter:N",
            y=f"{metric_for_line}:Q",
            color=alt.condition(
                "datum.Highlight == true",
                alt.value("#023E8A"),
                alt.value("#0458af")
            ),
            tooltip=[
                alt.Tooltip("Quarter:N", title="Quarter"),
                alt.Tooltip("Current_Cust:Q", title="Jumlah Kumulatif Customer", format=",d"),
                alt.Tooltip("Growth_Number:Q", title="Pertumbuhan Customer", format=",d"),
                alt.Tooltip("Growth:Q", title="Pertumbuhan Customer (%)", format=".2%"),
                alt.Tooltip("Prod_Age_Ratio:Q", title="Rasio Customer dan Usia Produktif 2024 (%)", format=".2%")
            ]
        )

        text = alt.Chart(altair_data).mark_text(
            align="center",
            baseline="middle",
            dy=-15,
            fontSize=16,
            color="#0458af",
        ).encode(
            x="Quarter:N",
            y=f"{metric_for_line}:Q",
            text=alt.Text(
                f"{metric_for_line}:Q",
                format=",.0f" if metric_for_line == "Growth_Number" else ".2%"
            ),
            tooltip=[
                alt.Tooltip("Quarter:N", title="Quarter"),
                alt.Tooltip("Current_Cust:Q", title="Jumlah Kumulatif Customer", format=",d"),
                alt.Tooltip("Growth_Number:Q", title="Pertumbuhan Customer", format=",d"),
                alt.Tooltip("Growth:Q", title="Pertumbuhan Customer (%)", format=".2%"),
                alt.Tooltip("Prod_Age_Ratio:Q", title="Rasio Customer dan Usia Produktif 2024 (%)", format=".2%")
            ]
        )
        
        line_chart = line_base + points + text
        
        combo_chart = alt.layer(bar_chart, line_chart).resolve_scale(
            y="independent"
        ).properties(
            height=270,
            background="transparent"
        ).configure_axis(
            labelFontSize=12,
            titleFontSize=14
        ).configure_title(
            fontSize=16,
            anchor="middle"
        )
        
        st.altair_chart(combo_chart, use_container_width=True)

        with st.expander("Lihat Tren Berdasarkan Wilayah"):
            top_n_slider = st.slider(
                "Pilih Top N:",
                min_value=1, 
                max_value=50,
                value=5,
                help="Geser slider ini untuk melihat top N"
            )
            

            if display_option == "Pertumbuhan Customer (%)":
                column_suffix = "_GROWTH"
                format_func = lambda x: f"{x/100:.2%}"
            elif display_option == "Pertumbuhan Customer":
                column_suffix = "_GROWTH_NUMBER"
                format_func = lambda x: f"{int(x):,}"
            elif display_option == "Rasio Customer dan Usia Produktif 2024 (%)":
                column_suffix = "_PROD_AGE_RATIO"
                format_func = lambda x: f"{x/100:.2%}"
            else:
                column_suffix = "_CUST_RATIO"
                format_func = lambda x: f"{x/100:.2%}"

            df_kab["combined"] = df_kab["WADMKK"] + ", " + df_kab["WADMPR"]
            df_kec["combined"] = df_kec["WADMKC"] + ", " + df_kec["WADMKK"] + ", " + df_kec["WADMPR"]
            
            pulau_html = generate_trend_html(
                df_pulau, "PULAU", column_suffix, 
                start_quarter_clicked, end_quarter_clicked, 
                top_n_slider, "Tren Top Pulau", 
                show_all=True
            )
            
            prov_html = generate_trend_html(
                df_prov, "WADMPR", column_suffix, 
                start_quarter_clicked, end_quarter_clicked, 
                top_n_slider, f"Tren Top {top_n_slider} Provinsi"
            )
            
            kab_html = generate_trend_html(
                df_kab, "combined", column_suffix, 
                start_quarter_clicked, end_quarter_clicked, 
                top_n_slider, f"Tren Top {top_n_slider} Kabupaten/Kota"
            )
            
            kec_html = generate_trend_html(
                df_kec, "combined", column_suffix, 
                start_quarter_clicked, end_quarter_clicked, 
                top_n_slider, f"Tren Top {top_n_slider} Kecamatan"
            )
            
            st.html("""
            <style>
                .trend-table {
                    overflow-x: auto;
                    margin-bottom: 16px;
                }
                @media screen and (max-width: 768px) {
                    .trend-table table {
                        font-size: 11px;
                    }
                    .trend-table th, .trend-table td {
                        padding: 3px !important;
                    }
                }
            </style>
            """)
            
            st.html(pulau_html)
            st.html(prov_html)
            st.html(kab_html)
            st.html(kec_html)