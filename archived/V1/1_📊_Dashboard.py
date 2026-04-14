import folium
import branca
import pathlib

import streamlit as st
import numpy as np
import pandas as pd
import geopandas as gpd

from datetime import datetime
from streamlit_folium import st_folium

# App Settings
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

# Load Custom CSS
def load_css(file_path):
    with open(file_path) as f:
        st.html(f"<style>{f.read()}</style>")

css_path = pathlib.Path("assets/styles.css")
load_css(css_path)

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

# Load and Prepare Data
def calculate_growth(df):
    df["CUSTOMER_GROWTH"] = ((df["2024_CUST_NO"] - df["2019_CUST_NO"]) / df["2019_CUST_NO"]) * 100
    df["CUSTOMER_GROWTH_NUMBER"] = df["2024_CUST_NO"] - df["2019_CUST_NO"]

    df["USIA_PRODUKTIF_RATIO"] = df["2024_CUST_NO"] / df["Usia Produktif"] * 100

    business_units = ["NMC", "REFI", "MPF", "MMU", "OTHERS"]

    df["2019_ALL_UNITS_TOTAL"] = 0
    df["2024_ALL_UNITS_TOTAL"] = 0

    for unit in business_units:
        df[f"2019_{unit}_TOTAL"] = df[f"2019_{unit}_N"] + df[f"2019_{unit}_Y"]
        df[f"2024_{unit}_TOTAL"] = df[f"2024_{unit}_N"] + df[f"2024_{unit}_Y"]

        df[f"{unit}_BOOKING_GROWTH"] = (
            (df[f"2024_{unit}_TOTAL"] - df[f"2019_{unit}_TOTAL"]) / df[f"2019_{unit}_TOTAL"]
        ) * 100

        df["2019_ALL_UNITS_TOTAL"] += df[f"2019_{unit}_TOTAL"]
        df["2024_ALL_UNITS_TOTAL"] += df[f"2024_{unit}_TOTAL"]

    df["ALL_UNITS_BOOKING_GROWTH"] = (
        (df["2024_ALL_UNITS_TOTAL"] - df["2019_ALL_UNITS_TOTAL"]) / df["2019_ALL_UNITS_TOTAL"]
    ) * 100
    df["ALL_UNITS_BOOKING_GROWTH_NUMBER"] = df["2024_ALL_UNITS_TOTAL"] - df["2019_ALL_UNITS_TOTAL"]

    df = df.replace([float("inf"), -float("inf")], 0).fillna(0)

    return df

@st.cache_data()
def preparing_data():
    shp_prov = gpd.read_file("Data Fix/LapakGIS_Batas_Provinsi_2024.json")
    shp_prov[["WADMPR"]] = shp_prov[["WADMPR"]].apply(lambda x: x.str.upper())
    shp_prov.set_crs(epsg=4326, inplace=True)

    shp_kab = gpd.read_file("Data Fix/LapakGIS_Batas_Kabupaten_2024.json")
    shp_kab[["WADMKK", "WADMPR"]] = shp_kab[["WADMKK", "WADMPR"]].apply(lambda x: x.str.upper())
    shp_kab.set_crs(epsg=4326, inplace=True)

    shp_kec = gpd.read_file("Data Fix/LapakGIS_Batas_Kecamatan_2024.json")
    shp_kec[["WADMKC", "WADMKK", "WADMPR"]] = shp_kec[["WADMKC", "WADMKK", "WADMPR"]].apply(lambda x: x.str.upper())
    shp_kec.set_crs(epsg=4326, inplace=True)

    df_cab_lat_long = pd.read_excel("Data Fix/202501 - LIST ALL NETWORK_geotagging_final.xlsx", sheet_name="List ID Network")
    df_cab_lat_long = df_cab_lat_long[df_cab_lat_long["NETWORK"].isin(["CABANG", "POS"])]
    df_cab_lat_long["FULL NAME"] = df_cab_lat_long["NETWORK"] + " " + df_cab_lat_long["BRANCH NAME"] + " (" + df_cab_lat_long["BRANCH ID"].astype(str) + ")"
    df_cab_lat_long["LAT"] = df_cab_lat_long["GEOTAGGING"].str.split(",").str[0]
    df_cab_lat_long["LONG"] = df_cab_lat_long["GEOTAGGING"].str.split(",").str[1]

    df_cab = pd.read_excel("Data Fix/202501 - LIST ALL NETWORK_geotagging_final.xlsx", sheet_name="Alamat Network")
    df_cab.columns = df_cab.columns.str.strip()
    df_cab = df_cab[df_cab["NETWORKING"].isin(["1. CABANG", "6. POS"])].reset_index(drop=True)
    df_cab["NAMA CABANG"] = df_cab["ID CABANG"].map(df_cab_lat_long.set_index("BRANCH ID")["BRANCH NAME"].to_dict())
    df_cab["NETWORKING"] = df_cab["NETWORKING"].str.split(".").str[1].str.strip()
    df_cab["FULL NAME"] = df_cab["NETWORKING"] + " " + df_cab["NAMA CABANG"] + " (" + df_cab["ID CABANG"].astype(str) + ")"
    df_cab["LAT"] = df_cab["FULL NAME"].map(df_cab_lat_long.set_index("FULL NAME")["LAT"].to_dict())
    df_cab["LONG"] = df_cab["FULL NAME"].map(df_cab_lat_long.set_index("FULL NAME")["LONG"].to_dict())

    df_dealer = pd.read_excel("Data Fix/GIS LOCATION.xlsx")
    df_dealer = df_dealer[df_dealer["CATEGORY"].isin(["DEALER", "POS DEALER", "COMPETITOR"])].reset_index(drop=True)
    df_dealer = df_dealer.drop("LOCATION_ID", axis=1)

    df = pd.read_excel("Data Fix/Data Customer AGG_v2.xlsx")
    agg_columns = df.columns[3:]

    df_prov = df.groupby("WADMPR")[agg_columns].sum().reset_index()
    df_prov = calculate_growth(df_prov)
    df_prov = pd.merge(
        left=shp_prov[["WADMPR", "geometry"]],
        right=df_prov,
        on="WADMPR",
        how="left"
    )

    df_kab = df.groupby(["WADMKK", "WADMPR"])[agg_columns].sum().reset_index()
    df_kab = calculate_growth(df_kab)
    df_kab = pd.merge(
        left=shp_kab[["WADMKK", "WADMPR", "geometry"]],
        right=df_kab,
        on=["WADMKK", "WADMPR"],
        how="left"
    )

    df_kec = df.groupby(["WADMKC", "WADMKK", "WADMPR"])[agg_columns].sum().reset_index()
    df_kec = calculate_growth(df_kec)
    df_kec = pd.merge(
        left=shp_kec[["WADMKC", "WADMKK", "WADMPR", "geometry"]],
        right=df_kec,
        on=["WADMKC", "WADMKK", "WADMPR"],
        how="left"
    )

    return df_cab, df_dealer, df_prov, df_kab, df_kec

df_cab, df_dealer, df_prov, df_kab, df_kec = preparing_data()

# st.dataframe(df_prov, use_container_width=True)

# Session States
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
if "display_option" not in st.session_state:
    st.session_state.display_option = "Pertumbuhan Customer (%)"
# if "reset_in_progress" not in st.session_state:
#     st.session_state.reset_in_progress = False

# Change Colormap
def change_colormap():
    st.session_state.use_percentage = st.session_state.get("toggle_state", True)

# Add Colormap
def create_colormap(data, display_option):
    if display_option == "Pertumbuhan Customer (%)":
        column = "CUSTOMER_GROWTH"
        caption = "Pertumbuhan Customer Secara Nasional (%)"
        colors = ["#ffffd9", "#41b6c4", "#081d58"]  # Blue-ish palette
    elif display_option == "Pertumbuhan Customer":
        column = "CUSTOMER_GROWTH_NUMBER"
        caption = "Pertumbuhan Customer Secara Nasional"
        colors = ["#f7fcf5", "#41ab5d", "#005a32"]  # Green-ish palette
    else:
        column = "USIA_PRODUKTIF_RATIO"
        caption = "Ratio Customer per 2024 dan Usia Produktif Secara Nasional (%)"
        colors = ["#fff5f5", "#fc9272", "#de2d26"]  # Red-ish palette
    
    return branca.colormap.LinearColormap(
        vmin=data[column].quantile(0.0),
        vmax=data[column].quantile(1.0),
        colors=colors,
        caption=caption
    )

# Add Tooltip
def create_tooltip(level="province"):
    fields = [
        "WADMPR",
        "2019_CUST_NO",
        "2024_CUST_NO",
        "Usia Produktif",
        "CUSTOMER_GROWTH_NUMBER",
        "CUSTOMER_GROWTH",
        "USIA_PRODUKTIF_RATIO",
        # "2019_ALL_UNITS_TOTAL",
        # "2024_ALL_UNITS_TOTAL",
        # "ALL_UNITS_BOOKING_GROWTH_NUMBER",
        # "ALL_UNITS_BOOKING_GROWTH"
    ]
    aliases = [
        "Provinsi",
        "Jumlah Customer per 2019",
        "Jumlah Customer per 2024",
        "Jumlah Penduduk Usia Produktif",
        "Pertumbuhan Customer",
        "Pertumbuhan Customer (%)",
        "Ratio Customer per 2024 dan Usia Produktif (%)",
        # "Jumlah Booking per 2019",
        # "Jumlah Booking per 2024",
        # "Pertumbuhan Booking",
        # "Pertumbuhan Booking (%)"
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
        labels=True,
        # style="""
        #     background-color: #F0EFEF;
        #     border: 2px solid black;
        #     border-radius: 3px;
        #     box-shadow: 3px;
        # """
    )

# Map Stylings
def style_function(feature, colormap, display_option):
    if display_option == "Pertumbuhan Customer (%)":
        column = "CUSTOMER_GROWTH"
    elif display_option == "Pertumbuhan Customer":
        column = "CUSTOMER_GROWTH_NUMBER"
    else:  # Ratio option
        column = "USIA_PRODUKTIF_RATIO"
    
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
    # if st.session_state.reset_in_progress:
    #     st.session_state.reset_in_progress = False
    #     return

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
    # st.session_state.reset_in_progress = True

def reset_to_city_view():
    st.session_state.clicked_district = None
    st.session_state.clicked_city = None
    # st.session_state.reset_in_progress = True

def reset_to_district_view():
    st.session_state.clicked_district = None
    # st.session_state.reset_in_progress = True

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

# Titles and Data
def update_titles_and_agg_vals():    
    global cust_title, booking_title, agg_vals    
    if st.session_state.clicked_district:    
        cust_title = f"Pertumbuhan Customer di {st.session_state.clicked_district}, {st.session_state.clicked_city}, {st.session_state.clicked_province}"    
        booking_title = f"Pertumbuhan Booking di {st.session_state.clicked_district}, {st.session_state.clicked_city}, {st.session_state.clicked_province}"    
        district_data = df_kec[    
            (df_kec["WADMPR"] == st.session_state.clicked_province) &     
            (df_kec["WADMKK"] == st.session_state.clicked_city) &    
            (df_kec["WADMKC"] == st.session_state.clicked_district)    
        ]    
        agg_vals = district_data.select_dtypes(include=np.number).sum(axis=0) if not district_data.empty else pd.Series({"2019_CUST_NO": 0, "2024_CUST_NO": 0})    
    elif st.session_state.clicked_city:    
        cust_title = f"Pertumbuhan Customer di {st.session_state.clicked_city}, {st.session_state.clicked_province}"    
        booking_title = f"Pertumbuhan Booking di {st.session_state.clicked_city}, {st.session_state.clicked_province}"    
        city_data = df_kab[    
            (df_kab["WADMPR"] == st.session_state.clicked_province) &     
            (df_kab["WADMKK"] == st.session_state.clicked_city)    
        ]    
        agg_vals = city_data.select_dtypes(include=np.number).sum(axis=0) if not city_data.empty else pd.Series({"2019_CUST_NO": 0, "2024_CUST_NO": 0})    
    elif st.session_state.clicked_province:    
        cust_title = f"Pertumbuhan Customer di {st.session_state.clicked_province}"    
        booking_title = f"Pertumbuhan Booking di {st.session_state.clicked_province}"    
        province_data = df_prov[df_prov["WADMPR"] == st.session_state.clicked_province]    
        agg_vals = province_data.select_dtypes(include=np.number).sum(axis=0) if not province_data.empty else pd.Series({"2019_CUST_NO": 0, "2024_CUST_NO": 0})    
    else:
        cust_title = "Pertumbuhan Customer Secara Nasional"    
        booking_title = "Pertumbuhan Booking Secara Nasional"    
        agg_vals = df_prov.select_dtypes(include=np.number).sum(axis=0)

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
def display_map():
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

    colormap = create_colormap(df_prov, display_option)

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
                style_function=lambda x: style_function(x, create_colormap(city_data, display_option), display_option),
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
                    style_function=lambda x: style_function(x, create_colormap(district_data, display_option), display_option),
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
            icon_url="https://media-hosting.imagekit.io//916d97dc3d4a4f84/location_big_red.png?Expires=1833702568&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=mi5ngwe2yTDvzBC87r-OtkvbJwV9t5urcCXeFwUoFfCGXRG0K58CV-4S1xONn2x4POu1U~9OEvFREF~51cthZBwP204faVTytxcfCQM3vymnJIqF-nlJeIRl9DYi-E9xAqpbHRiASv2V86fo-T1t0K8c7ss-RVjAOpkJKEoHqfQQrdB0dP~2EDTXngWyZL63cgGEavb7xGXlObjGK2Bt7BLTg-0kYzkKDCWqXbht4Yd61Si4Jlp24yVh2gQUlc6Q1ITED9xRn-0UTu3c0Bbg2SlsC1jpx2G1JHnT0r5Z-aVHhaUHgF8zGD15E3tshjNrnvHgWbshtIIZiFdxLikzhw__",
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
            icon_url="https://media-hosting.imagekit.io//faa7cc29b3874a4e/location_big_blue.png?Expires=1833706000&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=cF4lfi8pfKXYIUCiO46c3hxwQkru4gnuJMDRLiPNrQIpgfxdPS~cOsE4v3zBGF-jcHeGfJlUDiJKV3SRo-zLJm8TPE6MFrkHH3UX4OAlVZIHjaL8PgrxZ21G7CJVlzeBRQhhANA45ln21F9yV8~zWzKpqqWPi1SbeRqT~YbQDRYwyqV6IgUxSKX48QkLXl-bNnkqk4s8GMFsOg7D2tBf0oeS7UQ6K2XzGcIrx7W2fqQvvQMOsiAXsJ9FPD0daqNxmvA9Wm3I-zu0dtG7i9jGOUHUOmE~P5k2QpaATtfPe1q3j0C95kDmnJ2YIslvbyNjebjpV2FIJE6j7HI88nO6LQ__",
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
            icon_url="https://media-hosting.imagekit.io//9ee4206299b74ab3/location_big_orange.png?Expires=1833706712&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=NkPAC5Qu--UtZ6lqnBKGAFstauSu01KjaBWyPFXEbU3bdJyutIGp43gVth2WfpdQ~l146-rpH1Y1kQVGJi~I5m7qFvqVKQPSV0fUnyWzoHqyo6n~jrPNzI0CfOjQobqru1j-2rYd3vVt1nmUP~RXyDIsd~489268Gkq7SUzRGnxTsDEey~MIq9Il-bW0x9qESHbrfiGcG8KTLPmnfForgnG8Mos1YzHTEMIaegE0F6BD8rZSzqPUWDAMZdayMvN8h3GcfEl~Xp1j8H8VCui9JO6B9FMOX0gXRqdhGgLTihs-C8sOpog0yzO-yjsBaWm~U-FcDIoO6nFBGEXOBUuvOQ__",
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
            icon_url="https://media-hosting.imagekit.io//0dbcb40b4bc547b7/location_big_green.png?Expires=1833706712&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=qpbGTUg1MQUt2RM5h9YtXJg9JO-qF6Is9PZhvlHRVhodvgZ7NY2WcHIty~RT3YmDKDgEBxLthdjLW61u~j5O8exODuAptuPGzFqrns-a7JbQP3fhc0y1j~MeNLfY1ENxszTdV5T1c~qJVITdcx73yGr-i7oE41k3ydPr22DqOKarb~-jdyrAU01UsPHD8ZpGACY5e8hnNaqRnfR7y2391grRMlHcaFqTqIvfC9gFYa54cHjnytHxemek6kEdqh5M94Fo9F0E2eUO2c6N63pnY1Z5BfSOjuYhNS7X7YSkvwiPlzBDXgSc7DoJibA4ah8CH-RgZDxjvwiAtV4S76RA2Q__",
            icon_size=(25, 25)
        )

    if st.session_state.show_kompetitor:
        add_markers(
            feature_group=feature_group_to_add,
            data=df_dealer,
            category_column="CATEGORY",
            category_value="COMPETITOR",
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://media-hosting.imagekit.io//36cb33b320a6450d/location_big_grey.png?Expires=1833706712&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=FVB81lIRNbvtgysHIbbIa~6Z-CuKZTd9wm7Q0rEe4UYWI773w0If8YVwLPfEfWNJro1xI7gSlCPOIX2yGfKy67XFG7oCFODKisUXbXqsmneAuXT3~PkRIqw5eBgMr9a3GqgVKyFMfzRVgOWSnlIx1Q~Md-gLZ4Y-Pv6lomMNeF2pUjDTMqCTSluX4xOQuU-W4NaZWHVt7ei9uoES1qoTnP6fzDKetg7bmlCTScj5MQ7wZ-6TD9EgAo35fsjnTiU-4JecrnQNNEWHOS2igO2YA3KtTR3D1KjG-SBb~qz18jpjXKxPDzzCJrNT44ZvNBzRbkjgO0kgYcIoK9ztCqBStw__",
            icon_size=(20, 20)
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

# Customer Title
with st.container(key="styled_container1"):
    col1 = st.columns(1)

    update_titles_and_agg_vals()
    total_cust_2019 = agg_vals["2019_CUST_NO"]  
    total_cust_2024 = agg_vals["2024_CUST_NO"]  
    cust_growth = ((total_cust_2024 - total_cust_2019) / total_cust_2019 * 100) if total_cust_2019 != 0 else 0  

    growth_color = '#28a745' if cust_growth > 0 else '#ff0000' if cust_growth < 0 else '#4c5773'  
    growth_symbol = "▲" if cust_growth > 0 else "▼" if cust_growth < 0 else ""  

    with col1[0]:
        st.html(
            f'''  
                <div style="display: flex; justify-content: space-between; align-items: center;">  
                    <div style="font-size: 18px; font-weight: bold; color: #0458af;">{cust_title}</div>  
                    <div style="text-align: right; display: flex; align-items: center;">  
                        <div style="font-size: 16px; margin-right: 10px;">  
                            <strong>As of 2019</strong>: {int(total_cust_2019):,} | <strong>As of 2024</strong>: {int(total_cust_2024):,}  
                        </div>  
                        <div style="font-size: 18px; font-weight: bold; color: {growth_color};">  
                            {growth_symbol} {cust_growth:.2f}%  
                        </div>  
                    </div>  
                </div>  
            '''
        )

# Calculate Booking
def format_number(num):
    if pd.isna(num):
        return "0"
    return f"{int(num):,}"

def create_metric_html(data_2019_n, data_2019_y, data_2024_n, data_2024_y, logo_url, others=False):
    total_2019 = data_2019_n + data_2019_y
    total_2024 = data_2024_n + data_2024_y
    total_growth = ((total_2024 - total_2019) / total_2019 * 100) if total_2019 != 0 and not pd.isna(total_2019) else 0
    
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

    ba4_2019_percent = (data_2019_y / total_2019 * 100) if total_2019 != 0 and not pd.isna(total_2019) else 0
    ba4_2024_percent = (data_2024_y / total_2024 * 100) if total_2024 != 0 and not pd.isna(total_2024) else 0

    image_section = f"""
        <div style="flex-shrink: 0;">
            <img src="{logo_url}.jpg" alt="Descriptive text" 
                style="width: 70px; height: 70px; object-fit: cover; border-radius: 8px;">
        </div>
    """ if not others else f"""
        <div style="flex-shrink: 0; width: 70px; height: 70px; display: flex; justify-content: center; align-items: center;">
            <span style="font-size: 15px; font-weight: bold; color: #4c5773;">OTHERS</span>
        </div>
    """

    return f"""
        <div style="display: grid; grid-template-columns: 80px 1fr 1fr 100px; align-items: center; gap: 15px;">
            {image_section}
            <div style="font-size: 15px; text-align: left;">
                <strong>As of 2019</strong>
                <br>
                <span style="color: #2c3858;">{format_number(total_2019)}</span>
                <br>
            </div>
            <div style="font-size: 15px; text-align: left;">
                <strong>As of 2024</strong>
                <br>
                <span style="color: #2c3858;">{format_number(total_2024)}</span>
                <br>
            </div>
            <div style="font-size: 17px; font-weight: bold; text-align: center; color: #4c5773;">
                {format_growth(total_growth)}
            </div>
        </div>
    """

# Main App
col1, col2 = st.columns([2.7, 1], vertical_alignment="center")

# Display Map
with col1:
    with st.container(key="styled_container2"):
        map_col = st.columns(1)
        with map_col[0]:
            display_map()

        display_options = st.pills(
            "Tampilkan dalam:",
            options=[
                "Pertumbuhan Customer (%)",
                "Pertumbuhan Customer",
                "Ratio Customer per 2024 dan Usia Produktif (%)"
            ],
            key="display_option",
            label_visibility="collapsed"
        )

        markers, btn1, btn2, btn3 = st.columns([1, 0.25, 0.25, 0.25], vertical_alignment="center")
        
        with markers:
            option_map = {
                0: "![Cabang](https://media-hosting.imagekit.io//d8c4bb9381014e38/location_small_red.png?Expires=1833702568&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=Hn~d3UHE6SbdU7oaVEA6j83hS0rPxVHK0lkYQtokSZalCAQmyydVjBnTgB5vix3Cxc889r3HcvFBgzW51wpQUyqj4XWvSmcNHu~2HOmFvYzAgLoSgPBglHhNv4WkYNBFqxd6Iz2fXlsNGuwrqrhYU2S5fxwzL3aOykOrM-~UlPG9Z6n8KQqUjFT0IZz2FJ7LkCPNY~gA-NzBGoJVZ2eJkMMzGaMc0t23lj1u3irJPLn3GXO2nkjdCAzSroTYa75YT-9FMrZVlZ4yavO58k36FBPbw0WnDRwIjOg67k1fLyBHk8l5Q1uNixINO6paMRtOwCMiM~I93yum6F7rQ48~MA__) Cabang",
                1: "![Pos](https://media-hosting.imagekit.io//cd6a3fee145f4f07/location_small_blue.png?Expires=1833706000&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=lvKB53sZV5x4-nlI2O0dtho6SzjEzvovev9L6nmi92KhSGhZ-Lh4SSdLINuOEP3iQqoygCkxoaxsn6pswMNgWWrv179h0IIrWBJNYp9CKAGIyDtnzaorIRUKvPJnWvfmaN2uFOcRmkyiXtwyXqAXyrT~DcRY6a7IcEylmFj1HH3fWm0cWdYOXGK4671uJ65bRcIvgKk3z1W8UJmXV9pb~yLkma5kaLWAz9PQjiEvWAVlqxk-zkGsOBw5mxRkrQSxGrqgWeD4TlQ4GwaOHmQzW6uCRdDAwdOt79Alyyo8PKQ2NfCoGWPsiMvfzxdi3tznwATJWY~b5XlYK942QYcFsw__) Pos",
                2: "![Dealer](https://media-hosting.imagekit.io//25ae9b41e34640f2/location_small_orange.png?Expires=1833706712&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=uvFjimUTjVc0FYon-R5rqqNp6A-PrShoEel1PJuFcg3uKU~STP7QfqzX0I9cB1gxiG6mZ095WR4SAbG7VpXGaF8iENUzTaLuZjfYw-tHtc4icCjyGGNhBvKwsK1VKlzhVsk2DWPKXuKrsIxERwSoWWEMH5hQNLGb51dwHWggkGTLVxRqXLuEFxQgDSn2UG67KatMzLBsDujpAgYGaDjq3oECA~eiv7ONVTuehtpuOOYP3t1ffBQ93AAR1uC-6h27tCOZKBsd0BYeh5TPL9qoM7UO735ACduj7xAP77gHWCTFvTjHvc8inUlERtDWdDBR2yoZHI3RMKKUZMuCy8Rs7A__) Dealer",
                3: "![Pos Dealer](https://media-hosting.imagekit.io//3273b550e72d4ccb/location_small_green.png?Expires=1833706712&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=a5vNObIrdw7cwgamRWoOhqxqBO3xKpkCvG5XtGUVRKhJoWVGVFeglVdAU79Egji88cCjS9awDBsX5BTyj9ymROl7QvvzJLQfCax7putKM4Irzi4jOzchKOtLlNJXVuac3Xwuj0BoOXj92yJf0pKxVr9zzxCG~fM1XzNQ~J-sdPnpkNFPq82FaWJvqPhuMoT7TQlR4w6MmkIZCo1Fq3BIrcz9MLB-AeMBaRrz41JOVAzmhIcDrHJGXDNF-hQcvW27NLvTOHNinqfjyMSNZS~vYYCS-WL6dzefUNfbLGEYikKo7CTxAHgvSd8Q2CLqlylT3Yu~IGsB8uGkiFex7JksCA__) Pos Dealer",
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

# Display Booking
with col2:
    with st.container(key="styled_container3"):
        st.html(
            f'''  
                <div style="font-size: 18px; font-weight: bold; color: #0458af;">Pertumbuhan Booking per Business Unit</div>  
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
                        agg_vals[f"2019_{unit['key']}_N"],
                        agg_vals[f"2019_{unit['key']}_Y"],
                        agg_vals[f"2024_{unit['key']}_N"],
                        agg_vals[f"2024_{unit['key']}_Y"],
                        unit.get("logo", ""),
                        others=unit.get("others", False)
                    )
                )