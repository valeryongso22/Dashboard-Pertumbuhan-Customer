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
from numerize.numerize import numerize
from branca.element import Template, MacroElement

# Trigger state untuk reset otomatis dari BU1–BU3
if "trigger_reset_from_bu_cycle" not in st.session_state:
    st.session_state.trigger_reset_from_bu_cycle = False

# Page Config
st.set_page_config(    
    page_title="Dashboard Pertumbuhan Customer",    
    page_icon="assets/images/FIFGROUP_KOTAK.png",
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

css_path = pathlib.Path("assets/css/styles.css")
load_css(css_path)

# Footer
st.markdown(
    """
    <style>
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: #4d77ad;
            color: white;
            text-align: center;
            padding: 10px 0;
            font-size: 14px;
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }
        .footer p {
            margin-bottom: 0px;
        }
        .footer a {
            color: #ECF0F1;
            text-decoration: none;
        }
        .footer a:hover {
            text-decoration: underline;
        }
    </style>
    <div class="footer">
        <p>Made by the <b>Risk Policy Department</b> of the <b>Risk Management Division</b></p>
    </div>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------------------- Data -----------------------------------------------------------------
# Preprocess Customer Data
def process_df(df, suffix, quarters, df_lob_first = None):
    candidate_geo_cols = ["PULAU", "WADMKC", "WADMKK", "WADMPR", "Usia Produktif"]
    geo_cols = [col for col in candidate_geo_cols if col in df.columns]
    extra_geo_cols = ["geometry", "centroid_lat", "centroid_long"]
    geo_cols.extend([col for col in extra_geo_cols if col in df.columns])
        
    out_df = df[geo_cols].copy()
    out_df["Usia Produktif"] = out_df["Usia Produktif"].replace([float("inf"), -float("inf")], 0).fillna(0)

    new_columns = {}
    
    for i, quarter in enumerate(quarters):
        col_name = f"{quarter}_{suffix}"
        col_name_all = f"{quarter}_TOTAL"
        col_name_all2 = f"{quarter}_TOTAL2"
        if col_name not in df.columns:
            continue

        col_name_all2_exists = col_name_all2 in df.columns

        if i == 0:
            new_columns[f"{quarter}_CUST_NO"] = df[col_name]
            new_columns[f"{quarter}_CUST_NO_TOTAL"] = df[col_name_all]
            if col_name_all2_exists:
                new_columns[f"{quarter}_CUST_NO_TOTAL2"] = df[col_name_all2]
            else:
                new_columns[f"{quarter}_CUST_NO_TOTAL2"] = 0
        else:
            prev_quarter = quarters[i-1]
            prev_col_name = f"{prev_quarter}_{suffix}"
            prev_col_name_all = f"{prev_quarter}_TOTAL"
            prev_col_name_all2 = f"{prev_quarter}_TOTAL2"

            if prev_col_name not in df.columns:
                continue

            prev_col_name_all2_exists = prev_col_name_all2 in df.columns

            new_columns[f"{quarter}_CUST_NO"] = df[col_name]
            new_columns[f"{quarter}_CUST_NO_TOTAL"] = df[col_name_all]
            if col_name_all2_exists:
                new_columns[f"{quarter}_CUST_NO_TOTAL2"] = df[col_name_all2]
            else:
                new_columns[f"{quarter}_CUST_NO_TOTAL2"] = 0

            with np.errstate(divide='ignore', invalid='ignore'):
                growth = ((df[col_name] - df[prev_col_name]) / df[prev_col_name]) * 100
            new_columns[f"{quarter}_GROWTH"] = growth.replace([float("inf"), -float("inf")], 0).fillna(0)

            growth_number = df[col_name] - df[prev_col_name]
            new_columns[f"{quarter}_GROWTH_NUMBER"] = growth_number.replace([float("inf"), -float("inf")], 0).fillna(0)

            growth_number_all = df[col_name_all] - df[prev_col_name_all]
            new_columns[f"{quarter}_GROWTH_NUMBER_ALL"] = growth_number_all.replace([float("inf"), -float("inf")], 0).fillna(0)

            if col_name_all2_exists and prev_col_name_all2_exists:
                growth_number_all2 = df[col_name_all2] - df[prev_col_name_all2]
                new_columns[f"{quarter}_GROWTH_NUMBER_ALL2"] = growth_number_all2.replace([float("inf"), -float("inf")], 0).fillna(0)
            else:
                new_columns[f"{quarter}_GROWTH_NUMBER_ALL2"] = 0 

            with np.errstate(divide='ignore', invalid='ignore'):
                prod_age_ratio = df[col_name] / df["Usia Produktif"] * 100
            new_columns[f"{quarter}_PROD_AGE_RATIO"] = prod_age_ratio.replace([float("inf"), -float("inf")], 0).fillna(0)

            with np.errstate(divide='ignore', invalid='ignore'):
                cust_ratio = np.where(growth_number_all != 0, (growth_number / growth_number_all) * 100, 0)
            new_columns[f"{quarter}_CUST_RATIO"] = np.nan_to_num(cust_ratio, nan=0.0, posinf=0.0, neginf=0.0)

    temp_df = pd.DataFrame(new_columns, index=out_df.index)
    out_df = pd.concat([out_df, temp_df], axis=1)

    selected_quarter = st.session_state.get("selected_quarter", ("2019", "2026Q1"))
    first_q, last_q = selected_quarter
    first_cust_col = f"{first_q}_CUST_NO"
    last_cust_col  = f"{last_q}_CUST_NO"
    first_cust_col_all = f"{first_q}_CUST_NO_TOTAL"
    last_cust_col_all  = f"{last_q}_CUST_NO_TOTAL"
    first_cust_col_all2 = f"{first_q}_CUST_NO_TOTAL2"
    last_cust_col_all2  = f"{last_q}_CUST_NO_TOTAL2"

    first_cust = out_df.get(first_cust_col, pd.Series(0, index=out_df.index)).fillna(0).replace([np.inf, -np.inf], 0)
    last_cust  = out_df.get(last_cust_col, pd.Series(0, index=out_df.index)).fillna(0).replace([np.inf, -np.inf], 0)
    first_cust_all = out_df.get(first_cust_col_all, pd.Series(0, index=out_df.index)).fillna(0).replace([np.inf, -np.inf], 0)
    last_cust_all  = out_df.get(last_cust_col_all, pd.Series(0, index=out_df.index)).fillna(0).replace([np.inf, -np.inf], 0)
    first_cust_all2 = out_df.get(first_cust_col_all2, pd.Series(0, index=out_df.index)).fillna(0).replace([np.inf, -np.inf], 0)
    last_cust_all2  = out_df.get(last_cust_col_all2, pd.Series(0, index=out_df.index)).fillna(0).replace([np.inf, -np.inf], 0)

    prod_age = out_df["Usia Produktif"].fillna(0).replace([float("inf"), -float("inf")], 0)

    with np.errstate(divide="ignore", invalid="ignore"):
        map_growth = np.where(first_cust != 0, ((last_cust - first_cust) / first_cust) * 100, 0)
    map_growth = np.nan_to_num(map_growth, nan=0.0, posinf=0.0, neginf=0.0)

    map_growth_number = last_cust - first_cust
    map_growth_number = np.nan_to_num(map_growth_number, nan=0.0, posinf=0.0, neginf=0.0)

    map_growth_number_all = last_cust_all - first_cust_all
    map_growth_number_all = np.nan_to_num(map_growth_number_all, nan=0.0, posinf=0.0, neginf=0.0)

    map_growth_number_all2 = last_cust_all2 - first_cust_all2
    map_growth_number_all2 = np.nan_to_num(map_growth_number_all2, nan=0.0, posinf=0.0, neginf=0.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        map_prod_age_ratio = np.where(prod_age != 0, (last_cust / prod_age) * 100, 0)
    map_prod_age_ratio = np.nan_to_num(map_prod_age_ratio, nan=0.0, posinf=0.0, neginf=0.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        map_cust_ratio = np.where(map_growth_number_all != 0, (map_growth_number / map_growth_number_all) * 100, 0)
    map_cust_ratio = np.nan_to_num(map_cust_ratio, nan=0.0, posinf=0.0, neginf=0.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        map_cust_ratio_default = np.where(map_growth_number_all != 0, (map_growth_number_all2 / map_growth_number_all) * 100, 0)
    map_cust_ratio_default = np.nan_to_num(map_cust_ratio_default, nan=0.0, posinf=0.0, neginf=0.0)

    if df_lob_first is None:
        df_lob_first = df

    lob_list = ["NMC", "REFI", "MPF", "MMU", "OTHERS"]
    lob_total_first = {}
    lob_ratio_to_total = {}

    for lob in lob_list:
        start_col = f"{first_q}_{lob}1"
        end_col = f"{last_q}_{lob}1"

        lob_total_first[start_col] = (
            df_lob_first[start_col].fillna(0).replace([float("inf"), -float("inf")], 0)
            if start_col in df_lob_first.columns else pd.Series([0] * len(df_lob_first), index=df_lob_first.index))

        lob_total_first[end_col] = (
            df_lob_first[end_col].fillna(0).replace([float("inf"), -float("inf")], 0)
            if end_col in df_lob_first.columns else pd.Series([0] * len(df_lob_first), index=df_lob_first.index))

        lob_total_first[f"MAP_FIRST_LOB_TOTAL_{lob}"] = (
            lob_total_first[end_col] - lob_total_first[start_col])

        total_start = f"{first_q}_TOTAL1"
        total_end = f"{last_q}_TOTAL1"
        if total_start in df_lob_first.columns and total_end in df_lob_first.columns:
            total_start_val = df_lob_first[total_start].fillna(0).replace([float("inf"), -float("inf")], 0)
            total_end_val = df_lob_first[total_end].fillna(0).replace([float("inf"), -float("inf")], 0)
            delta_total = total_end_val - total_start_val
            lob_sum = lob_total_first[f"MAP_FIRST_LOB_TOTAL_{lob}"]
            ratio = np.where(delta_total != 0, (lob_sum / delta_total) * 100, 0)
            lob_ratio_to_total[f"MAP_FIRST_LOB_RATIO_{lob}"] = np.nan_to_num(ratio, nan=0.0, posinf=0.0, neginf=0.0)
        else:
            lob_ratio_to_total[f"MAP_FIRST_LOB_RATIO_{lob}"] = 0.0

    # kelompok usia
    age_cols = [col for col in df.columns if col.startswith("AGE_") and col.endswith("_CUST")]
    age_metrics = {}  
    
    for age_col in age_cols:
        age_count = df[age_col].fillna(0).replace([float("inf"), -float("inf")], 0)
        
        total_age = (
            df["TOTAL_AGE_CUST"].fillna(1).replace([float("inf"), -float("inf")], 1)
            if "TOTAL_AGE_CUST" in df.columns
            else pd.Series(1, index=df.index))
        
        with np.errstate(divide="ignore", invalid="ignore"):
            age_ratio = np.where(total_age != 0, (age_count / total_age) * 100, 0)
        
        out_df[age_col] = age_count
        ratio_col = age_col.replace("_CUST", "_RATIO")
        out_df[ratio_col] = np.nan_to_num(age_ratio, nan=0.0, posinf=0.0, neginf=0.0)
        
        age_metrics[age_col] = np.nan_to_num(age_count, nan=0.0, posinf=0.0, neginf=0.0)
        age_metrics[ratio_col] = np.nan_to_num(age_ratio, nan=0.0, posinf=0.0, neginf=0.0)

    map_metrics = {
        "MAP_GROWTH": np.nan_to_num(map_growth),
        "MAP_GROWTH_NUMBER": np.nan_to_num(map_growth_number),
        "MAP_GROWTH_NUMBER_ALL": np.nan_to_num(map_growth_number_all),
        "MAP_GROWTH_NUMBER_ALL2": np.nan_to_num(map_growth_number_all2),
        "MAP_PROD_AGE_RATIO": np.nan_to_num(map_prod_age_ratio),
        "MAP_CUST_RATIO": np.nan_to_num(map_cust_ratio),
        "MAP_CUST_RATIO_DEFAULT": np.nan_to_num(map_cust_ratio_default),
        **lob_total_first,
        **lob_ratio_to_total,
        **age_metrics
    }

    map_df = pd.DataFrame(map_metrics, index=out_df.index)
    out_df = pd.concat([out_df, map_df], axis=1)

    return out_df

# Ambil nilai filter dari session_state
selected_buss_unit = st.session_state.get("selected_buss_unit", "ALL")
selected_buss_unit2 = st.session_state.get("selected_buss_unit2", "None")
bu1 = st.session_state.get("cycle_bu1", "None")
bu2 = st.session_state.get("cycle_bu2", "None")
bu3 = st.session_state.get("cycle_bu3", "None")
# Jika BU1–BU3 ada yang dipilih, reset age group ke "All"
if bu1 != "None" or bu2 != "None" or bu3 != "None":
    st.session_state["selected_age_group"] = "All"

# Force penggunaan data CYCLE jika BU Awal ≠ ALL atau BU Akhir ≠ None dan BU1–3 ≠ None
if selected_buss_unit != "ALL" or selected_buss_unit2 != "None":
    if bu1 != "None" or bu2 != "None" or bu3 != "None":
        # Override BU1–BU3 agar data _CYCLE digunakan
        st.session_state["use_cycle_data"] = True
    else:
        st.session_state["use_cycle_data"] = False
else:
    st.session_state["use_cycle_data"] = False

def calculate_growth(df1, df2, df3, df4):
    selected_buss_unit = st.session_state.get("selected_buss_unit", "ALL")
    selected_buss_unit2 = st.session_state.get("selected_buss_unit2", "None")

    # Ambil BU1–BU3
    bu1 = st.session_state.get("cycle_bu1", "None")
    bu2 = st.session_state.get("cycle_bu2", "None")
    bu3 = st.session_state.get("cycle_bu3", "None")

    def use_cycle_column(b1, b2, b3):
        return not (b1 == "None" and b2 == "None" and b3 == "None")

    def get_cycle_suffix(b1, b2, b3):
        parts = [b for b in [b1, b2, b3] if b != "None"]
        return " to ".join(parts) + "_CYCLE" if parts else None

    # Jika BU1–BU3 semuanya None → gunakan selected_buss_unit dan selected_buss_unit2
    if not use_cycle_column(bu1, bu2, bu3):
        if selected_buss_unit == "ALL" and selected_buss_unit2 == "None":
            suffix = "TOTAL"
        elif selected_buss_unit == "ALL" and selected_buss_unit2 == "ALL":
            suffix = "TOTAL2"
        elif selected_buss_unit2 == "None":
            suffix = selected_buss_unit
        else:
            suffix = f"{selected_buss_unit} to {selected_buss_unit2}"
    else:
        # Kalau BU1–BU3 ada isinya → pakai _CYCLE
        suffix = get_cycle_suffix(bu1, bu2, bu3)

    quarters = [
        "2019", "2020Q1", "2020Q2", "2020Q3", "2020Q4",
        "2021Q1", "2021Q2", "2021Q3", "2021Q4",
        "2022Q1", "2022Q2", "2022Q3", "2022Q4",
        "2023Q1", "2023Q2", "2023Q3", "2023Q4",
        "2024Q1", "2024Q2", "2024Q3", "2024Q4",
        "2025Q1", "2025Q2", "2025Q3", "2025Q4",
        "2026Q1"
    ]

    # Proses setiap df dengan suffix yang sudah ditentukan
    processed_df1 = process_df(df1, suffix, quarters)
    processed_df2 = process_df(df2, suffix, quarters)
    processed_df3 = process_df(df3, suffix, quarters)
    processed_df4 = process_df(df4, suffix, quarters)

    return processed_df1, processed_df2, processed_df3, processed_df4

# Preprocess Booking Data
def process_df_booking(data):
    selected_quarter = st.session_state.get("selected_quarter", ("2019", "2026Q1"))
    selected_buss_unit = st.session_state.get("selected_buss_unit", "ALL")
    selected_buss_unit2 = st.session_state.get("selected_buss_unit2", "None")

    df = data.copy()
    
    extracted_parts = [col.split("_") for col in df.columns]
    unique_pairs = set((parts[0], parts[1]) for parts in extracted_parts if len(parts) >= 2)
    
    result = pd.DataFrame(index=df.index)
    
    for q, bu in unique_pairs:
        if q not in selected_quarter:
            continue  

        if (selected_buss_unit == "ALL") and (selected_buss_unit2 == "None"):
            selected_cols = [
                col for col in df.columns 
                if col.startswith(f"{q}_{bu}") and len(col.split("_")) >= 4 and col.split("_")[3] == "TOTAL"
            ]
        elif (selected_buss_unit == "ALL") and (selected_buss_unit2 == "ALL"):
            selected_cols = [
                col for col in df.columns 
                if col.startswith(f"{q}_{bu}") and len(col.split("_")) >= 4 and col.split("_")[3] == "TOTAL2"
            ]
        elif (selected_buss_unit == "NMC") and (selected_buss_unit2 == "None"):
            selected_cols = [
                col for col in df.columns 
                if col.startswith(f"{q}_{bu}") and len(col.split("_")) >= 4 and col.split("_")[3] == "NMC"
            ]
        elif (selected_buss_unit == "REFI") and (selected_buss_unit2 == "None"):
            selected_cols = [
                col for col in df.columns 
                if col.startswith(f"{q}_{bu}") and len(col.split("_")) >= 4 and col.split("_")[3] == "REFI"
            ]
        elif (selected_buss_unit == "MPF") and (selected_buss_unit2 == "None"):
            selected_cols = [
                col for col in df.columns 
                if col.startswith(f"{q}_{bu}") and len(col.split("_")) >= 4 and col.split("_")[3] == "MPF"
            ]
        else:
            selected_cols = [
                col for col in df.columns 
                if col.startswith(f"{q}_{bu}") and len(col.split("_")) >= 4 and col.split("_")[3] == f"{selected_buss_unit} to {selected_buss_unit2}"
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

    if selected_buss_unit != "ALL" and selected_buss_unit2 != "ALL":
        for col in result.columns:
            if col in join_keys:
                continue
            if selected_buss_unit not in col and selected_buss_unit2 not in col:
                result[col] = 0

    return result

# Load Data
@st.cache_data()
def preparing_data(data_from_2010: bool):
    def normalize_geo_cols(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        rename_map = {
            # Province
            "provinsi": "WADMPR", "province": "WADMPR", "prov_name": "WADMPR",
            # Regency/City
            "kabupaten": "WADMKK", "kab_kota": "WADMKK", "kabkota": "WADMKK",
            "city": "WADMKK", "regency": "WADMKK",
            # District
            "kecamatan": "WADMKC", "district": "WADMKC", "kec": "WADMKC"
        }
        to_rename = {c: rename_map[c] for c in df.columns if c in rename_map}
        if to_rename:
            df = df.rename(columns=to_rename)
        for col in ["WADMKC", "WADMKK", "WADMPR"]:
            if col not in df.columns:
                df[col] = pd.NA
        for col in ["WADMKC", "WADMKK", "WADMPR"]:
            if col in df.columns:
                try:
                    df[col] = df[col].astype("string").str.upper()
                except Exception:
                    pass
        return df

    def fill_missing_geo_from_shapes(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        
        kab_lookup = shp_kab[["WADMKK", "WADMPR"]].drop_duplicates()
        kec_lookup = shp_kec[["WADMKC", "WADMKK", "WADMPR"]].drop_duplicates()

        if "WADMPR" in df.columns and "WADMKK" in df.columns:
            mask_need_pr = df["WADMPR"].isna() & df["WADMKK"].notna()
            if mask_need_pr.any():
                df = df.merge(kab_lookup, on="WADMKK", how="left", suffixes=("", "_LK"))
                df["WADMPR"] = df["WADMPR"].fillna(df["WADMPR_LK"])
                df = df.drop(columns=[c for c in df.columns if c.endswith("_LK")], errors="ignore")

        if "WADMKK" in df.columns and "WADMKC" in df.columns:
            mask_need_kk = df["WADMKK"].isna() & df["WADMKC"].notna()
            if mask_need_kk.any():
                df = df.merge(kec_lookup, on="WADMKC", how="left", suffixes=("", "_LK"))
                df["WADMKK"] = df["WADMKK"].fillna(df["WADMKK_LK"])
                df["WADMPR"] = df["WADMPR"].fillna(df["WADMPR_LK"])
                df = df.drop(columns=[c for c in df.columns if c.endswith("_LK")], errors="ignore")

        for col in ["WADMKC", "WADMKK", "WADMPR"]:
            if col in df.columns:
                try:
                    df[col] = df[col].astype("string").str.upper()
                except Exception:
                    pass
        return df

    def ensure_geo(df: pd.DataFrame) -> pd.DataFrame:
        df = normalize_geo_cols(df)
        df = fill_missing_geo_from_shapes(df)
        for col in ["WADMKC", "WADMKK", "WADMPR"]:
            if col not in df.columns:
                df[col] = pd.NA
        return df

    # ----------------------- Shapes -----------------------
    shp_prov = gpd.read_file("data/LapakGIS_Batas_Provinsi_2024.json")
    shp_prov[["WADMPR"]] = shp_prov[["WADMPR"]].apply(lambda x: x.str.upper())
    shp_prov["centroid"] = shp_prov["geometry"].centroid
    shp_prov["centroid_lat"] = shp_prov["centroid"].y
    shp_prov["centroid_long"] = shp_prov["centroid"].x
    shp_prov.set_crs(epsg=4326, inplace=True)

    shp_kab = gpd.read_file("data/LapakGIS_Batas_Kabupaten_2024.json")
    shp_kab[["WADMKK", "WADMPR"]] = shp_kab[["WADMKK", "WADMPR"]].apply(lambda x: x.str.upper())
    shp_kab["centroid"] = shp_kab["geometry"].centroid
    shp_kab["centroid_lat"] = shp_kab["centroid"].y
    shp_kab["centroid_long"] = shp_kab["centroid"].x
    shp_kab.set_crs(epsg=4326, inplace=True)

    shp_kec = gpd.read_file("data/LapakGIS_Batas_Kecamatan_2024.json")
    shp_kec[["WADMKC", "WADMKK", "WADMPR"]] = shp_kec[["WADMKC", "WADMKK", "WADMPR"]].apply(lambda x: x.str.upper())
    shp_kec["centroid"] = shp_kec["geometry"].centroid
    shp_kec["centroid_lat"] = shp_kec["centroid"].y
    shp_kec["centroid_long"] = shp_kec["centroid"].x
    shp_kec.set_crs(epsg=4326, inplace=True)

    # ----------------------- Static tables -----------------------
    df_cab = pd.read_excel("data_2026Q1/Data Cabang.xlsx")

    df_dealer = pd.read_excel("data_2026Q1/Data Dealer dan Kompetitor.xlsx")
    df_dealer = df_dealer[df_dealer["CATEGORY"].isin(["DEALER", "POS DEALER", "COMPETITOR CABANG", "COMPETITOR POS"])].reset_index(drop=True)
    df_dealer = df_dealer.drop("LOCATION_ID", axis=1)
    df_cab = ensure_geo(df_cab)
    df_dealer = ensure_geo(df_dealer)

    # ----------------------- Toggle sumber data -----------------------
    data_from_2010 = st.session_state.get("data_from_2010", False)
    files_2010 = {
        "customer":   "data_2026Q1/2010/Data Customer AGG 2010_2026Q1.parquet",
        "booking":    "data_2026Q1/2010/Data Booking 2010_2026Q1.parquet",
        "lob_first":  "data_2026Q1/2010/Data Customer - LoB First 2010_2026Q1.parquet",
        "age_group":  "data_2026Q1/2010/Data Customer - Age Group 2010_2026Q1.parquet",
        "cycle":      "data_2026Q1/2010/Data Customer - LoB Cycle AGG 2010_2026Q1.parquet"
    }
    # ----------------------- Customer -----------------------
    df = pd.read_parquet(files_2010["customer"] if data_from_2010 else "data_2026Q1/Data Customer AGG_2026Q1.parquet")
    df = ensure_geo(df)
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
        "BALI": "BALI", "NUSA TENGGARA BARAT": "BALI", "NUSA TENGGARA TIMUR": "BALI",
        "MALUKU": "MALUKU DAN PAPUA", "MALUKU UTARA": "MALUKU DAN PAPUA",
        "PAPUA": "MALUKU DAN PAPUA", "PAPUA BARAT": "MALUKU DAN PAPUA",
        "PAPUA SELATAN": "MALUKU DAN PAPUA", "PAPUA TENGAH": "MALUKU DAN PAPUA",
        "PAPUA PEGUNUNGAN": "MALUKU DAN PAPUA", "PAPUA BARAT DAYA": "MALUKU DAN PAPUA"
    }

    df_prov = df.groupby("WADMPR")[agg_columns].sum().reset_index()
    df_prov = pd.merge(
        left=shp_prov[["WADMPR", "geometry", "centroid", "centroid_lat", "centroid_long"]],
        right=df_prov, on="WADMPR", how="left"
    )

    df_pulau = df_prov.copy()
    df_pulau["PULAU"] = df_pulau["WADMPR"].map(provinsi_ke_pulau)
    df_pulau = df_pulau.groupby("PULAU")[agg_columns].sum().reset_index()

    df_kab = df.groupby(["WADMKK", "WADMPR"])[agg_columns].sum().reset_index()
    df_kab = pd.merge(
        left=shp_kab[["WADMKK","WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_kab, on=["WADMKK","WADMPR"], how="left"
    )

    df_kec = df.groupby(["WADMKC","WADMKK","WADMPR"])[agg_columns].sum().reset_index()
    df_kec = pd.merge(
        left=shp_kec[["WADMKC","WADMKK","WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_kec, on=["WADMKC","WADMKK","WADMPR"], how="left"
    )

    # ----------------------- Booking -----------------------
    df_book = pd.read_parquet(files_2010["booking"] if data_from_2010 else "data_2026Q1/Data Booking_2026Q1.parquet")
    df_book.columns = ["_".join(map(str, col)).strip("_") for col in df_book.columns.values]
    agg_columns_book = df_book.select_dtypes(include="number").columns

    df_book_prov = df_book.reset_index().groupby("WADMPR")[agg_columns_book].sum().reset_index()
    df_book_prov = pd.merge(
        left=shp_prov[["WADMPR", "geometry"]],
        right=df_book_prov, on="WADMPR", how="left"
    )

    df_book_kab = df_book.groupby(["WADMKK","WADMPR"])[agg_columns_book].sum().reset_index()
    df_book_kab = pd.merge(
        left=shp_kab[["WADMKK","WADMPR","geometry"]],
        right=df_book_kab, on=["WADMKK","WADMPR"], how="left"
    )

    df_book_kec = df_book.groupby(["WADMKC","WADMKK","WADMPR"])[agg_columns_book].sum().reset_index()
    df_book_kec = pd.merge(
        left=shp_kec[["WADMKC","WADMKK","WADMPR","geometry"]],
        right=df_book_kec, on=["WADMKC","WADMKK","WADMPR"], how="left"
    )

    # ----------------------- LoB First -----------------------
    df_lob_first = pd.read_parquet(files_2010["lob_first"] if data_from_2010 else "data_2026Q1/Data Customer - LoB First_2026Q1.parquet")
    df_lob_first = ensure_geo(df_lob_first)
    agg_columns_lob_first = df_lob_first.select_dtypes(include="number").columns

    df_lob_first_prov = df_lob_first.groupby("WADMPR")[agg_columns_lob_first].sum().reset_index()
    df_lob_first_prov = pd.merge(
        left=shp_prov[["WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_lob_first_prov, on="WADMPR", how="left"
    )

    df_lob_first_kab = df_lob_first.groupby(["WADMKK","WADMPR"])[agg_columns_lob_first].sum().reset_index()
    df_lob_first_kab = pd.merge(
        left=shp_kab[["WADMKK","WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_lob_first_kab, on=["WADMKK","WADMPR"], how="left"
    )

    df_lob_first_kec = df_lob_first.groupby(["WADMKC","WADMKK","WADMPR"])[agg_columns_lob_first].sum().reset_index()
    df_lob_first_kec = pd.merge(
        left=shp_kec[["WADMKC","WADMKK","WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_lob_first_kec, on=["WADMKC","WADMKK","WADMPR"], how="left"
    )

    # ----------------------- Age Group -----------------------
    df_age_group = pd.read_parquet(files_2010["age_group"] if data_from_2010 else "data_2026Q1/Data Customer - Age Group_2026Q1.parquet")
    df_age_group = ensure_geo(df_age_group)
    agg_columns_age_group = df_age_group.select_dtypes(include="number").columns

    df_age_group_prov = df_age_group.groupby("WADMPR")[agg_columns_age_group].sum().reset_index()
    df_age_group_prov = pd.merge(
        left=shp_prov[["WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_age_group_prov, on="WADMPR", how="left"
    )

    df_age_group_pulau = df_age_group_prov.copy()
    df_age_group_pulau["PULAU"] = df_age_group_pulau["WADMPR"].map(provinsi_ke_pulau)
    df_age_group_pulau = df_age_group_pulau.groupby("PULAU")[agg_columns_age_group].sum().reset_index()

    df_age_group_kab = df_age_group.groupby(["WADMKK","WADMPR"])[agg_columns_age_group].sum().reset_index()
    df_age_group_kab = pd.merge(
        left=shp_kab[["WADMKK","WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_age_group_kab, on=["WADMKK","WADMPR"], how="left"
    )

    df_age_group_kec = df_age_group.groupby(["WADMKC","WADMKK","WADMPR"])[agg_columns_age_group].sum().reset_index()
    df_age_group_kec = pd.merge(
        left=shp_kec[["WADMKC","WADMKK","WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_age_group_kec, on=["WADMKC","WADMKK","WADMPR"], how="left"
    )

    # ----------------------- Cycle -----------------------
    df_cycle = pd.read_parquet(files_2010["cycle"] if data_from_2010 else "data_2026Q1/Data Customer - LoB Cycle AGG_2026Q1.parquet")
    df_cycle = ensure_geo(df_cycle)
    agg_columns_cycle = df_cycle.select_dtypes(include="number").columns

    df_cycle_prov = df_cycle.groupby("WADMPR")[agg_columns_cycle].sum().reset_index()
    df_cycle_prov = pd.merge(
        left=shp_prov[["WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_cycle_prov, on="WADMPR", how="left")

    df_cycle_pulau = df_cycle_prov.copy()
    df_cycle_pulau["PULAU"] = df_cycle_pulau["WADMPR"].map(provinsi_ke_pulau)
    df_cycle_pulau = df_cycle_pulau.groupby("PULAU")[agg_columns_cycle].sum().reset_index()

    df_cycle_kab = df_cycle.groupby(["WADMKK","WADMPR"])[agg_columns_cycle].sum().reset_index()
    df_cycle_kab = pd.merge(
        left=shp_kab[["WADMKK","WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_cycle_kab, on=["WADMKK","WADMPR"], how="left")

    df_cycle_kec = df_cycle.groupby(["WADMKC","WADMKK","WADMPR"])[agg_columns_cycle].sum().reset_index()
    df_cycle_kec = pd.merge(
        left=shp_kec[["WADMKC","WADMKK","WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_cycle_kec, on=["WADMKC","WADMKK","WADMPR"], how="left")

    # ----------------------- Polreg Yamaha -----------------------
    df_yamaha = pd.read_excel("data/LoB/Polreg Yamaha_NMC.xlsx")
    df_yamaha = ensure_geo(df_yamaha)

    # Identify Yamaha + NMC columns
    yamaha_cols = [c for c in df_yamaha.columns if c.startswith("YAMAHA_")]
    nmc_cols    = [c for c in df_yamaha.columns if c.startswith("NMC_")]

    keep_cols = ["WADMKC", "WADMKK", "WADMPR"] + yamaha_cols + nmc_cols
    keep_cols = [c for c in keep_cols if c in df_yamaha.columns]

    df_yamaha = df_yamaha[keep_cols].copy()

    for c in yamaha_cols + nmc_cols:
        df_yamaha[c] = pd.to_numeric(df_yamaha[c], errors="coerce").fillna(0)

    agg_cols = yamaha_cols + nmc_cols
    df_yamaha_prov = df_yamaha.groupby("WADMPR")[agg_cols].sum().reset_index()

    if "WADMPR" in shp_prov.columns:
        df_yamaha_prov = shp_prov[["WADMPR","geometry","centroid","centroid_lat","centroid_long"]].merge(
            df_yamaha_prov, on="WADMPR", how="left"
        )

    df_yamaha_kab = df_yamaha.groupby(["WADMKK","WADMPR"])[agg_cols].sum().reset_index()
    if {"WADMKK","WADMPR"}.issubset(shp_kab.columns):
        df_yamaha_kab = shp_kab[["WADMKK","WADMPR","geometry","centroid","centroid_lat","centroid_long"]].merge(
            df_yamaha_kab, on=["WADMKK","WADMPR"], how="left"
        )

    # ----------------------- UFI -----------------------
    df_ufi = pd.read_excel("data_2026Q1/data ufi.xlsx", sheet_name="data")
    df_ufi.columns = df_ufi.columns.str.upper()
    df_ufi = ensure_geo(df_ufi)
    agg_columns_ufi = df_ufi.select_dtypes(include="number").columns

    for col in ["WADMPR", "WADMKK", "WADMKC"]:
        df_ufi[col] = df_ufi[col].astype(str).str.upper().str.strip()
    num_cols = [
        "RR CUSTOMER",
        "TOTAL CUSTOMER",
        "GROWTH NEW CUSTOMER",
        "NEW CUSTOMER 2024Q4",
        "OSA",
        "NSA"]
    
    for c in num_cols:
        df_ufi[c] = pd.to_numeric(df_ufi[c], errors="coerce").fillna(0)
    
    def compute_ufi_metrics(df):
        df = df.copy()
        # Hitung %
        df["% RR CUSTOMER"] = (df["RR CUSTOMER"] / df["TOTAL CUSTOMER"])
        df["%GROWTH NEW CUSTOMER"] = (df["GROWTH NEW CUSTOMER"] / df["NEW CUSTOMER 2024Q4"])
        df[["% RR CUSTOMER", "%GROWTH NEW CUSTOMER"]] = (df[["% RR CUSTOMER", "%GROWTH NEW CUSTOMER"]].replace([np.inf, -np.inf], 0))
        # Z-score
        df["Growth_Z"] = ((df["%GROWTH NEW CUSTOMER"] - df["%GROWTH NEW CUSTOMER"].mean()) / df["%GROWTH NEW CUSTOMER"].std())
        df["RR_Z"] = ((df["% RR CUSTOMER"] - df["% RR CUSTOMER"].mean()) / df["% RR CUSTOMER"].std())
        def classify_z(row):
            if row["Growth_Z"] >= 0 and row["RR_Z"] >= 0:
                return "Q1 - High Growth High RR"
            elif row["Growth_Z"] >= 0 and row["RR_Z"] < 0:
                return "Q2 - High Growth Low RR"
            elif row["Growth_Z"] < 0 and row["RR_Z"] >= 0:
                return "Q3 - Low Growth High RR"
            else:
                return "Q4 - Low Growth Low RR"

        df["QUADRANT"] = df.apply(classify_z, axis=1)
        # Tambahkan PULAU untuk normalisasi per pulau × quadrant
        _has_pulau = "PULAU" in df.columns
        if not _has_pulau and "WADMPR" in df.columns:
            df["PULAU"] = df["WADMPR"].map(provinsi_ke_pulau).fillna("LAINNYA")
        elif not _has_pulau:
            df["PULAU"] = "LAINNYA"
        # Normalisasi 0-1 per PULAU × QUADRANT
        def normalize_within_group(series):
            mn, mx = series.min(), series.max()
            if mx == mn:
                return pd.Series(0.5, index=series.index)
            return (series - mn) / (mx - mn)
        df["RR_NORM"] = df.groupby(["PULAU", "QUADRANT"])["% RR CUSTOMER"].transform(normalize_within_group)
        df["GROWTH_NORM"] = df.groupby(["PULAU", "QUADRANT"])["%GROWTH NEW CUSTOMER"].transform(normalize_within_group)
        df["UFI_SCORE"] = (0.5 * df["RR_NORM"] + 0.5 * df["GROWTH_NORM"])
        df["UFI_SCORE"] = df.groupby(["PULAU", "QUADRANT"])["UFI_SCORE"].transform(normalize_within_group)
        if not _has_pulau:
            df = df.drop(columns=["PULAU"])

        df["% RR CUSTOMER (fmt)"] = (df["% RR CUSTOMER"] * 100).round(2).astype(str) + "%"
        df["%GROWTH NEW CUSTOMER (fmt)"] = (df["%GROWTH NEW CUSTOMER"] * 100).round(2).astype(str) + "%"
        df["OSA (fmt)"] = df["OSA"].fillna(0).apply(lambda x: f"{int(x):,}")
        df["NSA (fmt)"] = df["NSA"].fillna(0).apply(lambda x: f"{int(x):,}")
        return df

    df_ufi_prov = df_ufi.groupby("WADMPR")[agg_columns_ufi].sum().reset_index()
    df_ufi_prov = pd.merge(
        left=shp_prov[["WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_ufi_prov, on="WADMPR", how="left")
    df_ufi_prov = compute_ufi_metrics(df_ufi_prov)

    # df_ufi_pulau = df_ufi_prov.copy()
    # df_ufi_pulau["PULAU"] = df_ufi_pulau["WADMPR"].map(provinsi_ke_pulau)
    # df_ufi_pulau = df_ufi_pulau.groupby("PULAU")[agg_columns_ufi].sum().reset_index()
    # df_ufi_pulau = compute_ufi_metrics(df_ufi_pulau)

    df_ufi_kab = df_ufi.groupby(["WADMKK","WADMPR"])[agg_columns_ufi].sum().reset_index()
    df_ufi_kab = pd.merge(
        left=shp_kab[["WADMKK","WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_ufi_kab, on=["WADMKK","WADMPR"], how="left")
    df_ufi_kab = compute_ufi_metrics(df_ufi_kab)

    df_ufi_kec = df_ufi.groupby(["WADMKC","WADMKK","WADMPR"])[agg_columns_ufi].sum().reset_index()
    df_ufi_kec = pd.merge(
        left=shp_kec[["WADMKC","WADMKK","WADMPR","geometry","centroid","centroid_lat","centroid_long"]],
        right=df_ufi_kec, on=["WADMKC","WADMKK","WADMPR"], how="left")
    df_ufi_kec = compute_ufi_metrics(df_ufi_kec)

    # ----------------------- NPL Computation -----------------------
    df_npl_raw = pd.read_parquet("data_2026Q1/DATA NPL2.parquet")
    df_npl_raw = ensure_geo(df_npl_raw)

    def _calc_npl_for_group(df_raw, group_cols):
        npl_bad = ["C3", "C4", "C5"]
        npl_all = ["C0", "C1", "C2", "C3", "C4", "C5", "CM", "CN"]
        df_raw = df_raw.copy()
        df_raw["CYCLE_AKHIR"] = df_raw["CYCLE_AKHIR"].str.upper()
        bad_mask = df_raw["CYCLE_AKHIR"].isin(npl_bad)
        all_mask = df_raw["CYCLE_AKHIR"].isin(npl_all)
        nsa_bad = df_raw[bad_mask].groupby(group_cols)["NSA"].sum().reset_index().rename(columns={"NSA": "_NSA_BAD"})
        nsa_all = df_raw[all_mask].groupby(group_cols)["NSA"].sum().reset_index().rename(columns={"NSA": "_NSA_ALL"})
        merged = nsa_all.merge(nsa_bad, on=group_cols, how="left").fillna(0)
        merged["MAP_NPL"] = np.where(merged["_NSA_ALL"] != 0,
                                    merged["_NSA_BAD"] / merged["_NSA_ALL"] * 100, 0)
        return merged[group_cols + ["MAP_NPL"]]

    # Provinsi
    npl_prov = _calc_npl_for_group(df_npl_raw, ["WADMPR"])
    df_npl_prov = shp_prov[["WADMPR", "geometry", "centroid_lat", "centroid_long"]].merge(
        npl_prov, on="WADMPR", how="left")
    df_npl_prov["MAP_NPL"] = df_npl_prov["MAP_NPL"].fillna(0)

    # Pulau (re-aggregate raw NSA at island level)
    df_npl_raw_pulau = df_npl_raw.copy()
    df_npl_raw_pulau["PULAU"] = df_npl_raw_pulau["WADMPR"].map(provinsi_ke_pulau)
    npl_pulau = _calc_npl_for_group(df_npl_raw_pulau, ["PULAU"])
    df_npl_pulau = npl_pulau  # no geometry needed for pulau markers

    # Kabupaten
    npl_kab = _calc_npl_for_group(df_npl_raw, ["WADMKK", "WADMPR"])
    df_npl_kab = shp_kab[["WADMKK", "WADMPR", "geometry", "centroid_lat", "centroid_long"]].merge(
        npl_kab, on=["WADMKK", "WADMPR"], how="left")
    df_npl_kab["MAP_NPL"] = df_npl_kab["MAP_NPL"].fillna(0)

    # Kecamatan
    npl_kec = _calc_npl_for_group(df_npl_raw, ["WADMKC", "WADMKK", "WADMPR"])
    df_npl_kec = shp_kec[["WADMKC", "WADMKK", "WADMPR", "geometry", "centroid_lat", "centroid_long"]].merge(
        npl_kec, on=["WADMKC", "WADMKK", "WADMPR"], how="left")
    df_npl_kec["MAP_NPL"] = df_npl_kec["MAP_NPL"].fillna(0)

    return (df_cab, df_dealer, df_pulau, df_prov, df_kab, df_kec,
        df_book_prov, df_book_kab, df_book_kec,
        df_lob_first, df_lob_first_prov, df_lob_first_kab, df_lob_first_kec,
        df_age_group, df_age_group_pulau, df_age_group_prov, df_age_group_kab, df_age_group_kec,
        df_cycle, df_cycle_pulau, df_cycle_prov, df_cycle_kab, df_cycle_kec,
        df_yamaha_prov, df_yamaha_kab,
        df_ufi, df_ufi_prov, df_ufi_kab, df_ufi_kec,
        df_npl_pulau, df_npl_prov, df_npl_kab, df_npl_kec)

df_cab, df_dealer, df_pulau, df_prov, df_kab, df_kec, df_book_prov, df_book_kab, df_book_kec, df_lob_first, df_lob_first_prov, df_lob_first_kab, df_lob_first_kec, df_age_group, df_age_group_pulau, df_age_group_prov, df_age_group_kab, df_age_group_kec, df_cycle, df_cycle_pulau, df_cycle_prov, df_cycle_kab, df_cycle_kec, df_yamaha_prov, df_yamaha_kab, df_ufi, df_ufi_prov, df_ufi_kab, df_ufi_kec, df_npl_pulau, df_npl_prov, df_npl_kab, df_npl_kec = preparing_data(
    st.session_state.get("data_from_2010", False))
# ----------------------------------------------------------------- Session States -----------------------------------------------------------------

bounds_start = df_prov.geometry.total_bounds
min_longitude_start, min_latitude_start, max_longitude_start, max_latitude_start = bounds_start

center_latitude_start = (min_latitude_start + max_latitude_start) / 2
center_longitude_start = (min_longitude_start + max_longitude_start) / 2
center_start = [center_latitude_start, center_longitude_start]

zoom_start = 4.5

for clicked in ["clicked_district", "clicked_city", "clicked_province"]:
    if clicked not in st.session_state:
        st.session_state[clicked] = None

if "center" not in st.session_state:
    st.session_state.center = center_start
if "zoom" not in st.session_state:
    st.session_state.zoom = zoom_start

for show in [
    "show_cabang", "show_pos", "show_dealer", "show_pos_dealer",
    "show_adira", "show_oto", "show_bfi", "show_bank_mega",
    "show_mandala", "show_hci", "show_bca", "show_kb", "show_aeon",
    "show_others"
]:
    if show not in st.session_state:
        st.session_state[show] = False

if "show_top_5_centroid_prov" not in st.session_state:
    st.session_state.show_top_5_centroid_prov = True
if "show_top_5_centroid_kab" not in st.session_state:
    st.session_state.show_top_5_centroid_kab = False
if "show_top_5_centroid_kec" not in st.session_state:
    st.session_state.show_top_5_centroid_kec = False

for selected_marker in ["selected_marker_keys", "selected_marker2_keys"]:
    if selected_marker not in st.session_state:
        st.session_state[selected_marker] = set()

start_quarter_clicked = st.session_state.get("selected_quarter", ("2019", "2026Q1"))[0]
end_quarter_clicked = st.session_state.get("selected_quarter", ("2019", "2026Q1"))[1]
buss_unit_clicked = st.session_state.get("selected_buss_unit", "ALL")
buss_unit2_clicked = st.session_state.get("selected_buss_unit2", "None")
display_option = st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)")

# --- competitor level (Cabang / POS) ---
if "competitor_level" not in st.session_state:
    st.session_state.competitor_level = "Cabang"
if "competitor_category" not in st.session_state:
    st.session_state.competitor_category = "COMPETITOR CABANG"

# ----------------------------------------------------------------- Customer Growth Map -----------------------------------------------------------------
def create_colormap(data, display_option, threshold):
    # 1. Polreg Yamaha (%) CASE - termasuk NMC
    if display_option == "Polreg Yamaha (%)":
        df = data.copy()
        sy = st.session_state.get("yamaha_start_selector", "2023")
        ey = st.session_state.get("yamaha_end_selector", "2024")
        # Validasi selector tahun
        if sy not in ("2023", "2024"):
            sy = "2023"
        if ey not in ("2024", "2025"):
            ey = "2024" if sy == "2023" else "2025"
        # MODE YAMAHA + NMC (4 Kuadran)
        include_nmc = st.session_state.get("yamaha_include_nmc", False)
        if include_nmc:
            # Gunakan QuadrantColormap + gunakan MAP_COMBINED_SCORE
            qmap, colname = create_yamaha_nmc_colormap(data, sy, ey)
            return qmap, colname
        else:
            # MODE YAMAHA saja
            start_col = f"YAMAHA_{sy}"
            end_col   = f"YAMAHA_{ey}"
            column    = "MAP_GROWTH_YAMAHA"

            if (start_col in df.columns) and (end_col in df.columns):
                svals = pd.to_numeric(df[start_col], errors="coerce").fillna(0)
                evals = pd.to_numeric(df[end_col], errors="coerce").fillna(0)

                with np.errstate(divide="ignore", invalid="ignore"):
                    pct = np.where(svals != 0, (evals - svals) / svals * 100.0, np.nan)

                df[column] = pd.Series(pct, index=df.index)
            else:
                df[column] = np.nan

            # Tentukan min–max
            non_na = pd.to_numeric(df[column], errors="coerce").dropna().astype(float)

            if len(non_na):
                vmin = float(non_na.min())
                vmax = float(non_na.max())
            else:
                vmin, vmax = -1.0, 1.0

            # Pastikan domain logis
            if vmin >= 0:
                vmin = min(0.0, vmin - 1.0)
            if vmax <= 0:
                vmax = max(0.0, vmax + 1.0)
            if vmin == vmax:
                vmin -= 1.0
                vmax += 1.0

            # Warna gradient (merah → putih → hijau)
            colors = ["#8B0000", "#ffffff", "#006400"]

            # Build colormap
            try:
                colormap = branca.colormap.LinearColormap(
                    colors=colors,
                    index=[vmin, 0.0, vmax],
                    vmin=vmin,
                    vmax=vmax,
                    caption=f"Pertumbuhan Polreg Yamaha (%) — {sy} → {ey}"
                )
            except Exception:
                colormap = branca.colormap.LinearColormap(
                    colors=["#8B0000", "#006400"],
                    vmin=vmin,
                    vmax=vmax,
                    caption=f"Pertumbuhan Polreg Yamaha (%) — {sy} → {ey}"
                )

            return colormap, column

    # 2. Pertumbuhan Customer (%)
    if display_option == "Pertumbuhan Customer (%)":
        column = "MAP_GROWTH"
        caption = "Pertumbuhan Customer Secara Nasional (%)"
        colors = ["#ffffd9", "#41b6c4", "#081d58"]  # blue-ish

        colormap = branca.colormap.LinearColormap(
            vmin=data[column].min() if column in data else 0,
            vmax=data[column].max() if column in data else 1,
            colors=colors,
            caption=caption
        )
        return colormap, column

    # 3. Pertumbuhan Customer (angka)
    elif display_option == "Pertumbuhan Customer":
        column = "MAP_GROWTH_NUMBER"
        caption = "Pertumbuhan Customer Secara Nasional"
        colors = ["#f7fcf5", "#41ab5d", "#005a32"]  # green-ish

        colormap = branca.colormap.LinearColormap(
            vmin=data[column].min() if column in data else 0,
            vmax=data[column].max() if column in data else 1,
            colors=colors,
            caption=caption
        )
        return colormap, column

    # 4. Rasio Customer & Usia Produktif 2024 (%)
    elif display_option == "Rasio Customer dan Usia Produktif 2024 (%)":
        end_quarter_clicked = st.session_state.get("selected_quarter", ("2019", "4"))[1]

        column = "MAP_PROD_AGE_RATIO"
        caption = f"Rasio Customer per {end_quarter_clicked} dan Usia Produktif 2024 Secara Nasional (%)"
        colors = ["#fff5f5", "#fc9272", "#de2d26"]  # red-ish

        colormap = branca.colormap.LinearColormap(
            vmin=data[column].min() if column in data else 0,
            vmax=data[column].max() if column in data else 1,
            colors=colors,
            caption=caption
        )
        return colormap, column

    # 5. Retention Rate UFI
    elif display_option == "Retention Rate UFI":

        column = "UFI_SCORE"
        caption = "Retention Rate UFI (Quadrant)"

        quadrant_index_map = {
            "Q1 - High Growth High RR": 0,
            "Q2 - High Growth Low RR": 1,
            "Q3 - Low Growth High RR": 2,
            "Q4 - Low Growth Low RR": 3,
        }

        df = data.copy()

        if "QUADRANT" in df.columns:
            df[column] = df["QUADRANT"].map(quadrant_index_map)
        else:
            df[column] = None

        colors = [
            "#006400",  # Q1
            "#FFD700",  # Q2
            "#1E90FF",  # Q3
            "#B22222"  # Q4
        ]

        colormap = branca.colormap.StepColormap(
            colors=colors,
            index=[0,1,2,3,4,5],
            vmin=0,
            vmax=4,
            caption=caption
        )

        return colormap, column
    
    # 6. NPL — red gradient (darker = higher NPL)
    elif display_option == "NPL":
        column = "MAP_NPL"
        caption = "NPL per Wilayah (%)"
        colors = ["#fff5f0", "#fc9272", "#67000d"]  # white → light red → dark red

        vmin = data[column].min() if column in data.columns else 0
        vmax = data[column].max() if column in data.columns else 1
        if vmin == vmax:
            vmax = vmin + 1

        colormap = branca.colormap.LinearColormap(
            vmin=vmin, vmax=vmax,
            colors=colors,
            caption=caption
        )
        return colormap, column

    # 7. MAP_CUST_RATIO (default)
    else:
        end_quarter_clicked = st.session_state.get("selected_quarter", ("2019", "2026Q1"))[1]
        buss_unit_clicked = st.session_state.get("selected_buss_unit", "ALL")

        column = "MAP_CUST_RATIO"
        caption = f"Rasio Customer {buss_unit_clicked} dan ALL per {end_quarter_clicked} Secara Nasional (%)"
        vmin = data[column].min() if column in data else 0
        vmax = data[column].max() if column in data else 1

        # With threshold
        if threshold is not None:
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
                vmin=vmin,
                vmax=vmax,
                colors=colors,
                caption=caption
            )

        return colormap, column

def colormap_to_html(colormap, display_option=None):
    """
    Accepts a branca colormap (LinearColormap or StepColormap) and returns a HTML snippet for the legend.

    Special-case:
      - If user is in "Polreg Yamaha (%)" mode _and_ yamaha_nmc legend data is present in session_state,
        render a discrete 4-color box legend from st.session_state["yamaha_nmc_legend_colors"]
        and labels from st.session_state["yamaha_nmc_legend_bins"].

    Otherwise, fallback to the previous gradient rendering logic.
    """
    import streamlit as _st

    # Try discrete Yamaha+NMC legend first (preferred when in that mode)
    try:
        display_now = _st.session_state.get("selected_sorter") or _st.session_state.get("display_option")
    except Exception:
        display_now = display_option

    # If in Polreg Yamaha mode and we already stored legend bins/colors, build discrete boxes
    if (display_now == "Polreg Yamaha (%)"
            and _st.session_state.get("yamaha_nmc_legend_bins") is not None
            and _st.session_state.get("yamaha_nmc_legend_colors") is not None):
        bins = _st.session_state.get("yamaha_nmc_legend_bins")
        colors = _st.session_state.get("yamaha_nmc_legend_colors")

        # Ensure lengths match (expect 4 colors, 4 bins)
        if len(colors) >= 4 and len(bins) >= 4:
            # build labels like "min — q1", "q1 — q2", "q2 — max"
            labels = []
            for i in range(len(bins) - 1):
                a = bins[i]
                b = bins[i + 1]
                try:
                    labels.append(f"{a:.2f}% — {b:.2f}%")
                except Exception:
                    labels.append(f"{a} — {b}")

            html = "<div style='font-size:12px; padding:6px; background:#fff; border-radius:6px; box-shadow:0 2px 4px rgba(0,0,0,0.08);'>"
            html += f"<div style='font-weight:600; margin-bottom:6px;'>Pertumbuhan Kombinasi Yamaha+NMC (%)</div>"
            for col, lab in zip(colors, labels):
                html += (
                    "<div style='display:flex; align-items:center; margin-bottom:6px;'>"
                    f"<div style='width:20px; height:14px; background:{col}; border:1px solid #ccc; margin-right:8px;'></div>"
                    f"<div style='font-size:11px; color:#333;'>{lab}</div>"
                    "</div>"
                )
            html += "</div>"
            return html

    # ---------- Generic/legacy rendering below ----------
    colors = getattr(colormap, "colors", None)
    bounds = getattr(colormap, "index", None)
    vmin = getattr(colormap, "vmin", None)
    vmax = getattr(colormap, "vmax", None)

    css_colors = []
    if colors:
        for c in colors:
            if isinstance(c, (list, tuple)) and all(isinstance(v, (float, int)) for v in c) and max(c) <= 1:
                css_colors.append(f"rgb({int(c[0]*255)}, {int(c[1]*255)}, {int(c[2]*255)})")
            else:
                css_colors.append(str(c))
    else:
        css_colors = ["#ffffff", "#f0f0f0"]

    def format_value(value):
        try:
            if value is None:
                return "-"
            if display_option == "Pertumbuhan Customer":
                v = float(value)
                if abs(v) >= 1_000_000:
                    return numerize(v, 2)
                return f"{v:,.0f}"
            else:
                v = float(value)
                return f"{v:.2f}%"
        except Exception:
            return str(value)

    # Build gradient and ticks (preserve previous logic)
    if bounds is not None and len(bounds) == 4 and bounds[1] == bounds[2]:
        vmin_b, thr, _, vmax_b = bounds[0], bounds[1], bounds[2], bounds[3]
        color_left = css_colors[0] if len(css_colors) > 0 else "#ffffff"
        color_mid = css_colors[1] if len(css_colors) > 1 else "#cccccc"
        color_right = css_colors[-1] if len(css_colors) > 0 else "#000000"
        color_scale_html = f"""
            <div style="width: 100%;">
                <div style="height: 10px; background: linear-gradient(to right, {color_left} 0%, {color_mid} 50%, {color_right} 100%); margin-top: 8px;"></div>
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-top:6px;">
                    <span>{format_value(vmin_b)}</span>
                    <span>{format_value(thr)}</span>
                    <span>{format_value(vmax_b)}</span>
                </div>
            </div>
        """
    else:
        gradient = ", ".join(css_colors)
        try:
            vmin_val = vmin if vmin is not None else (bounds[0] if bounds else 0)
            vmax_val = vmax if vmax is not None else (bounds[-1] if bounds else 1)
        except Exception:
            vmin_val, vmax_val = 0, 1
        mid = (float(vmin_val) + float(vmax_val)) / 2
        color_scale_html = f"""
            <div style="width:100%;">
                <div style="height:10px; background: linear-gradient(to right, {gradient}); margin-top: 8px;"></div>
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-top:6px;">
                    <span>{format_value(vmin_val)}</span>
                    <span>{format_value(mid)}</span>
                    <span>{format_value(vmax_val)}</span>
                </div>
            </div>
        """
    return color_scale_html
def create_yamaha_nmc_colormap(df, start_year, end_year):
    """
    Quadrant solid-color colormap for Polreg Yamaha (%) when NMC is checked.

    Behavior:
    - writes MAP_GROWTH_YAMAHA, MAP_GROWTH_NMC, MAP_COMBINED_SCORE, MAP_QUADRANT into df
    - returns (colormap_callable, "MAP_COMBINED_SCORE")
    - colormap_callable is called as colormap(value, quadrant) by existing style_function;
      it ignores `value` and returns solid color based on quadrant:
        quadrant mapping:
            1: yamaha >=0 and nmc >=0  -> GREEN
            2: yamaha < 0  and nmc >=0 -> ORANGE  (top-right in your table)
            3: yamaha >=0 and nmc < 0  -> YELLOW  (bottom-left)
            4: yamaha < 0  and nmc < 0  -> RED
    """
    import numpy as np
    import pandas as pd

    # helper to compute pct growth columns if they are not present
    def _ensure_growth_col(prefix):
        s_col = f"{prefix}_{start_year}"
        e_col = f"{prefix}_{end_year}"
        if s_col in df.columns and e_col in df.columns:
            # numeric coercion
            s = pd.to_numeric(df[s_col], errors="coerce").fillna(0).astype(float)
            e = pd.to_numeric(df[e_col], errors="coerce").fillna(0).astype(float)
            with np.errstate(divide='ignore', invalid='ignore'):
                growth = np.where(s != 0, (e - s) / s * 100.0, 0.0)
            return pd.Series(growth, index=df.index).astype(float)
        else:
            # missing columns -> zeros
            return pd.Series(0.0, index=df.index)

    # ensure growth columns exist (so tooltip and other logic can use them)
    df["MAP_GROWTH_YAMAHA"] = _ensure_growth_col("YAMAHA")
    df["MAP_GROWTH_NMC"] = _ensure_growth_col("NMC")

    # compute combined score with the last rule you gave previously:
    # (+,+) -> average normal; (-,-) -> average normal (negative); mixed -> average of absolutes
    gy = df["MAP_GROWTH_YAMAHA"].fillna(0.0).astype(float)
    gn = df["MAP_GROWTH_NMC"].fillna(0.0).astype(float)

    combined = []
    quadrants = []
    for y, n in zip(gy, gn):
        # determine quadrant:
        if y >= 0 and n >= 0:
            q = 1
        elif y < 0 and n >= 0:
            q = 2
        elif y >= 0 and n < 0:
            q = 3
        else:
            q = 4

        # compute combined according to rule:
        if y >= 0 and n >= 0:
            comb = (y + n) / 2.0
        elif y < 0 and n < 0:
            comb = (y + n) / 2.0
        else:
            comb = (abs(y) + abs(n)) / 2.0

        quadrants.append(q)
        combined.append(float(comb))

    df["MAP_COMBINED_SCORE"] = pd.Series(combined, index=df.index)
    df["MAP_QUADRANT"] = pd.Series(quadrants, index=df.index).astype(int)

    # color mapping — sesuai tabel Anda (NMC rows, Yamaha cols)
    # quadrant definition:
    # 1 (y>=0, n>=0) -> GREEN
    # 2 (y<0, n>=0)  -> ORANGE
    # 3 (y>=0, n<0)  -> YELLOW
    # 4 (y<0, n<0)   -> RED
    quadrant_colors = {
        1: "#66bb6a",  # green
        2: "#f57c00",  # orange
        3: "#ffeb3b",  # yellow
        4: "#de2d26",  # red
    }

    class QuadrantSolidColorMap:
        def __init__(self, q_colors):
            self.q_colors = q_colors
            # make attribute so existing style_function recognizes quadrant-capable object
            self.quadrant_ranges = {q: (0.0, 1.0) for q in q_colors.keys()}

        def __call__(self, value, quadrant=None):
            try:
                q = int(quadrant) if quadrant is not None else 1
            except:
                q = 1
            return self.q_colors.get(q, "#ffffff")

        def __repr__(self):
            return f"<QuadrantSolidColorMap colors={self.q_colors}>"

    return QuadrantSolidColorMap(quadrant_colors), "MAP_COMBINED_SCORE"

# Number Formatting
def format_number(num):
    if pd.isna(num):
        return "0"
    return f"{int(num):,}"

def format_growth(value):
    if value > 0:
        color = "#28a745"
        symbol = "▲"
    elif value == 0:
        color = "#4c5773"
        symbol = ""
    else:
        color = "#ff0000"
        symbol = "▼"
    return f'<span style="color: {color};">{symbol} {value:,.2f}%</span>'

# Add Tooltip
def format_tooltip(row, title):
    buss_unit_clicked = st.session_state.get("selected_buss_unit", "ALL")
    buss_unit2_clicked = st.session_state.get("selected_buss_unit2", "None")

    bu1 = st.session_state.get("cycle_bu1", "None")
    bu2 = st.session_state.get("cycle_bu2", "None")
    bu3 = st.session_state.get("cycle_bu3", "None")
    use_cycle = not (bu1 == "None" and bu2 == "None" and bu3 == "None")

    growth_number_field_all = ""
    if buss_unit2_clicked == "None":
        title_growth = "Rasio Pertumbuhan Customer ALL (> 1x) dan Total Customer"
        growth_number_field = "MAP_GROWTH_NUMBER_ALL2"
        growth_number_field_all = "MAP_GROWTH_NUMBER_ALL"
        cust_ratio_field = "MAP_CUST_RATIO_DEFAULT"
    else:
        title_growth = f"Rasio Pertumbuhan Customer {update_buss_unit_title()} dan Total Customer"
        growth_number_field = "MAP_GROWTH_NUMBER"
        growth_number_field_all = growth_number_field + "_ALL"
        cust_ratio_field = "MAP_CUST_RATIO"

    lob_keys = [k for k in row.keys() if k.startswith("MAP_FIRST_LOB_TOTAL_")]
    lob_list = [k.replace("MAP_FIRST_LOB_TOTAL_", "") for k in lob_keys]

    lob_rows = ""
    for lob in lob_list:
        start_val = row.get(f"{start_quarter_clicked}_{lob}1", 0)
        end_val = row.get(f"{end_quarter_clicked}_{lob}1", 0)
        delta = row.get(f"MAP_FIRST_LOB_TOTAL_{lob}", 0)
        ratio = row.get(f"MAP_FIRST_LOB_RATIO_{lob}", 0)
        lob_rows += f"""
        <tr>
            <td style='font-size: 12px; text-align: center;'>{lob}</td>
            <td style='font-size: 12px; text-align: center;'>{format_number(start_val)}</td>
            <td style='font-size: 12px; text-align: center;'>{format_number(end_val)}</td>
            <td style='font-size: 12px; text-align: center;'>{format_number(delta)}</td>
            <td style='font-size: 12px; text-align: center;'>{ratio:.2f}%</td>
        </tr>
        """

    rasio_cust_baru_html = ""
    if buss_unit_clicked == "ALL" and buss_unit2_clicked == "None" and not use_cycle:
        rasio_cust_baru_html = f"""
            <div style='border: 1px solid #0458af; border-radius: 5px; position: relative; margin-top: 15px; padding: 10px 5px 5px;'>
                <div style='position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
                            background-color: white; padding: 0 10px;'>
                    <span style='font-size: 14px; color: #0458af; font-weight: bold;'>
                        Rasio Customer Baru per Bus. Unit
                        <span style='font-size: 12px;'>({start_quarter_clicked} - {end_quarter_clicked})</span>
                    </span>
                </div>
                <table style="width: 460px; margin: 0 auto; text-align: center; font-size: 13px;">
                    <tr>
                        <th style="text-align: center; font-size: 13px;"> </th>
                        <th style="text-align: center; font-size: 13px;">As of {start_quarter_clicked}</th>
                        <th style="text-align: center; font-size: 13px;">As of {end_quarter_clicked}</th>
                        <th style="text-align: center; font-size: 13px;">Δ</th>
                        <th style="text-align: center; font-size: 13px;">Rasio (%)</th>
                    </tr>
                    {lob_rows}
                </table>
            </div>
        """

    return f"""
        <div style='text-align: center; font-size:16px; color: #0458af; margin-bottom: 8px;'>
            <b>{title}</b>
        </div>

        <div style='border: 1px solid #0458af; border-radius: 5px; position: relative; margin-top: 15px; padding: 10px 5px 5px;'>
            <div style='position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background-color: white; padding: 0 10px;'>
                <span style='font-size: 14px; color: #0458af; font-weight: bold;'>Pertumbuhan Customer {update_buss_unit_title()}</span>
            </div>
            <table style="width: 480px; table-layout: fixed; text-align: center; font-size: 13px;">
                <tr>
                    <td style="text-align: center;"><strong>As of {start_quarter_clicked}</strong><br>{format_number(row.get(f'{start_quarter_clicked}_CUST_NO', 0))}</td>
                    <td style="text-align: center;"><strong>As of {end_quarter_clicked}</strong><br>{format_number(row.get(f'{end_quarter_clicked}_CUST_NO', 0))}</td>
                    <td style="text-align: center;"><b>{format_growth(row.get('MAP_GROWTH', 0))}</b><br>({format_number(row.get('MAP_GROWTH_NUMBER', 0))})</td>
                </tr>
            </table>
        </div>

        <div style='border: 1px solid #0458af; border-radius: 5px; position: relative; margin-top: 15px; padding: 10px 5px 5px;'>
            <div style='position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background-color: white; padding: 0 10px;'>
                <span style='font-size: 14px; color: #0458af; font-weight: bold;'>Rasio Customer {update_buss_unit_title()} dan Usia Produktif</span>
            </div>
            <table style="width: 480px; text-align: center; font-size: 13px;">
                <tr>
                    <td style="text-align: center;"><strong>Customer ({end_quarter_clicked})</strong><br>{format_number(row.get(f'{end_quarter_clicked}_CUST_NO', 0))}</td>
                    <td style="text-align: center;"><strong>Usia Produktif (2024)</strong><br>{format_number(row.get('Usia Produktif', 0))}</td>
                    <td style="text-align: center;"><b>{row.get('MAP_PROD_AGE_RATIO', 0):.2f}%</b></td>
                </tr>
            </table>
        </div>

        <div style='border: 1px solid #0458af; border-radius: 5px; position: relative; margin-top: 15px; padding: 10px 5px 5px;'>
            <div style='position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background-color: white; padding: 0 10px;'>
                <span style='font-size: 14px; color: #0458af; font-weight: bold;'>{title_growth}</span>
            </div>
            <table style="width: 480px; text-align: center; font-size: 13px;">
                <tr>
                    <td style="text-align: center;"><strong>Pertumbuhan Cust.<br>({start_quarter_clicked} - {end_quarter_clicked})</strong><br>{format_number(row.get(growth_number_field, 0))}</td>
                    <td style="text-align: center;"><strong>Pertumbuhan Total Cust.<br>({start_quarter_clicked} - {end_quarter_clicked})</strong><br>{format_number(row.get(growth_number_field_all, 0))}</td>
                    <td style="text-align: center;"><b>{row.get(cust_ratio_field, 0):.2f}%</b></td>
                </tr>
            </table>
        </div>

        <div style='border: 1px solid #0458af; border-radius: 5px; position: relative; margin-top: 15px; padding: 10px 5px 5px;'>
            <div style='position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background-color: white; padding: 0 10px;'>
                <span style='font-size: 14px; color: #0458af; font-weight: bold;'>NPL</span>
            </div>
            <table style="width: 480px; text-align: center; font-size: 13px;">
                <tr>
                    <td style="text-align: center;"><strong>NSA Kolektibilitas Buruk (C3–C5)</strong><br>—</td>
                    <td style="text-align: center;"><strong>NSA Total (C0–C5, CM, CN)</strong><br>—</td>
                    <td style="text-align: center;"><b>{row.get('MAP_NPL', 0):.2f}%</b></td>
                </tr>
            </table>
        </div>

        {rasio_cust_baru_html}
    """

def create_tooltip(level):
    fields = ["TOOLTIP"]
    aliases = [""]

    tooltip = folium.GeoJsonTooltip(
        fields=fields,
        aliases=aliases,
        localize=True,
        sticky=False,
        labels=True
    )

    return tooltip

# Map Stylings
# def style_function(feature, colormap, display_option):
#     if display_option == "Pertumbuhan Customer (%)":
#         column = "MAP_GROWTH"
#     elif display_option == "Pertumbuhan Customer":
#         column = "MAP_GROWTH_NUMBER"
#     elif display_option == "Rasio Customer dan Usia Produktif 2024 (%)":
#         column = "MAP_PROD_AGE_RATIO"
#     else:
#         column = "MAP_CUST_RATIO"
    
#     return {
#         "fillColor": colormap(feature["properties"][column])
#         if feature["properties"][column] is not None else "grey",
#         "color": "#000000",
#         "fillOpacity": 1,
#         "weight": 1
#     }

def style_function(feature, colormap, colname):
    props = feature.get("properties", {})

    # ambil value
    value = props.get(colname, None)

    # cek apakah colormap adalah QuadrantColormap (punya attribute quadrant_ranges)
    is_quadrant = hasattr(colormap, "quadrant_ranges")

    if is_quadrant:
        # mode Polreg Yamaha (%) + NMC
        quadrant = props.get("MAP_QUADRANT", 1)  # ambil kuadran dari data
        try:
            color = colormap(value, quadrant)
        except Exception:
            color = "#ffffff"
    else:
        # normal mode
        try:
            color = colormap(value)
        except:
            color = "#ffffff"

    return {
        "fillColor": color,
        "color": "black",
        "weight": 0.7,
        "fillOpacity": 0.85 if value is not None else 0
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

# --- helper to remove shapely / non-serializable geometry-like columns before sending to folium ---
from shapely.geometry.base import BaseGeometry
def clean_gdf_for_geo(gdf):
    """
    Return a copy of gdf with any columns dropped that contain shapely geometry
    objects (except the main 'geometry' column). Also drop obvious centroid columns.
    This prevents "Object of type Point is not JSON serializable" when folium.GeoJson
    json.dumps() the __geo_interface__.
    """
    if gdf is None or (hasattr(gdf, 'empty') and gdf.empty):
        return gdf
    gdf = gdf.copy()
    # drop common centroid columns
    for c in ["centroid", "centroid_lat", "centroid_long"]:
        if c in gdf.columns:
            gdf = gdf.drop(columns=[c], errors="ignore")
    # drop any column (except 'geometry') which contains shapely geometries
    to_drop = []
    for col in gdf.columns:
        if col == "geometry":
            continue
        # sample a few non-null values to detect geometry objects
        col_sample = gdf[col].dropna()
        if not col_sample.empty:
            sample_val = col_sample.iloc[0]
            if isinstance(sample_val, BaseGeometry):
                to_drop.append(col)
    if to_drop:
        gdf = gdf.drop(columns=to_drop, errors="ignore")
    return gdf

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

# Add Back Button
def get_back_button_props():
    if st.session_state.clicked_district:
        return {
            # "label": "Back to City View",
            "label": "Back",
            "help": f"Klik untuk kembali ke peta {st.session_state.clicked_city}",
            "on_click": reset_to_district_view,
            "disabled": False
        }
    elif st.session_state.clicked_city:
        return {
            # "label": "Back to Province View",
            "label": "Back",
            "help": f"Klik untuk kembali ke peta {st.session_state.clicked_province}",
            "on_click": reset_to_city_view,
            "disabled": False
        }
    elif st.session_state.clicked_province:
        return {
            # "label": "Back to Country View",
            "label": "Back",
            "help": "Klik untuk kembali ke peta Indonesia",
            "on_click": reset_to_province_view,
            "disabled": False
        }
    else:
        return {
            "label": "Back",
            "help": None,
            "on_click": None,
            "disabled": True
        }

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
    
# Update Business Unit Title
def update_buss_unit_title():
    if (buss_unit_clicked == "ALL") and (buss_unit2_clicked == "None"):
        buss_unit_title = ""
    elif (buss_unit_clicked == "ALL") and (buss_unit2_clicked == "ALL"):
        buss_unit_title = "ALL (> 1x)"
    elif buss_unit2_clicked == "None":
        buss_unit_title = buss_unit_clicked
    elif buss_unit_clicked == buss_unit2_clicked:
        buss_unit_title = f"{buss_unit_clicked} (> 1x)"
    else:
        buss_unit_title = f"{buss_unit_clicked} to {buss_unit2_clicked}"
    return buss_unit_title

# Update Titles and Data
def aggregate_data(df, filters, default_series):
    if df is None:
        empty_df = pd.DataFrame()
        return default_series, empty_df
    data = df
    for col, value in filters.items():
        if col in data.columns:
            data = data[data[col] == value]
        else:
            data = data.iloc[0:0]
    if data is None or data.empty:
        return default_series, pd.DataFrame()
    try:
        numeric_sum = data.select_dtypes(include=np.number).sum(axis=0)
    except Exception:
        numeric_sum = default_series
    return numeric_sum, data

def get_top_5(df, filters, sort_col):
    data = df
    for col, value in filters.items():
        data = data[data[col] == value]
    if not data.empty:
        return data.nlargest(5, sort_col)
    return None

# Update Titles and Data
def update_titles_and_agg_vals():
    display_option_now = st.session_state.get("display_option", 
                                            st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)"))
    is_yamaha_mode = display_option_now in ["Polreg Yamaha (%)", "Retention Rate UFI", "NPL"]
    if is_yamaha_mode:
        def _blocked(*args, **kwargs):
            return None
        st.dataframe = _blocked
        st.table     = _blocked
        st.write     = (lambda *args, **kwargs: None)
        def write_safe(x):
            if not hasattr(x, "geometry"):
                st.text(str(x))
        st.write_safe = write_safe

    if is_yamaha_mode:
        st.session_state["hide_tables"] = True
    else:
        st.session_state["hide_tables"] = False

    def _norm_series(s: pd.Series) -> pd.Series:
        return s.astype(str).str.strip().str.upper()

    def _brand_counts(df_subset: pd.DataFrame) -> dict:
        brands = [
            ("ADIRA", "adira"),
            ("OTO", "oto"),
            ("BFI", "bfi"),
            ("MEGA", "mega"),
            ("MANDALA", "mandala"),
            ("HCI", "hci"),
            ("BCA FINANCE", "bca"),
            ("KB", "kb"),
            ("AEON", "aeon"),
        ]
        brand_set = {b for b, _ in brands}
        if df_subset is None or len(df_subset) == 0 or "COMPETITOR_CATEGORY" not in df_subset.columns:
            base = {k: 0 for _, k in brands}
            base["others"] = 0
            return base

        u = _norm_series(df_subset["COMPETITOR_CATEGORY"])
        out = {k: int((u == b).sum()) for b, k in brands}
        out["others"] = int((~u.isin(brand_set)).sum())
        return out

    def _count_network(df_cab_like: pd.DataFrame) -> dict:
        if df_cab_like is None or len(df_cab_like) == 0 or "NETWORKING" not in df_cab_like.columns:
            return {"cabang": 0, "pos": 0}
        net = _norm_series(df_cab_like["NETWORKING"])
        return {"cabang": int((net == "CABANG").sum()), "pos": int((net == "POS").sum())}

    def _count_dealer(df_dealer_like: pd.DataFrame) -> dict:
        if df_dealer_like is None or len(df_dealer_like) == 0 or "CATEGORY" not in df_dealer_like.columns:
            return {"dealer": 0, "pos_dealer": 0}
        cat = _norm_series(df_dealer_like["CATEGORY"])
        return {"dealer": int((cat == "DEALER").sum()), "pos_dealer": int((cat == "POS DEALER").sum())}

    # ---------- titles & aggregates ----------
    global cust_title, booking_title, agg_vals, agg_vals_book
    global top_5_centroid_prov, top_5_centroid_kab, top_5_centroid_kec

    top_5_centroid_prov = None
    top_5_centroid_kab = None
    top_5_centroid_kec = None

    default_series = pd.Series()

    buss_unit_title = update_buss_unit_title()
    filtered_df_cab = df_cab.copy()
    filtered_df_dealer = df_dealer.copy()

    # detect Yamaha special mode
    display_option = st.session_state.get("display_option",
                                      st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)"))
    is_yamaha_mode = (display_option == "Polreg Yamaha (%)")

    # ---------- selection scopes ----------
    if st.session_state.clicked_district:
        cust_title = f"Pertumbuhan Customer {buss_unit_title} di {st.session_state.clicked_district}, {st.session_state.clicked_city}, {st.session_state.clicked_province}"
        booking_title = f"Pertumbuhan Booking {buss_unit_title} di {st.session_state.clicked_district}, {st.session_state.clicked_city}, {st.session_state.clicked_province}"

        filters = {
            "WADMPR": st.session_state.clicked_province,
            "WADMKK": st.session_state.clicked_city,
            "WADMKC": st.session_state.clicked_district,
        }

        if is_yamaha_mode or display_option in ("Retention Rate UFI", "NPL"):
            st.session_state["hide_tables"] = True
            agg_vals = pd.Series({})
            agg_vals_book = pd.Series({})
        else:
            agg_vals, _ = aggregate_data(df_kec, filters, default_series)
            agg_vals_book, _ = aggregate_data(df_book_kec, filters, default_series)

        filtered_df_cab = filtered_df_cab[
            (filtered_df_cab["WADMPR"] == st.session_state.clicked_province) &
            (filtered_df_cab["WADMKK"] == st.session_state.clicked_city) &
            (filtered_df_cab["WADMKC"] == st.session_state.clicked_district)
        ]
        filtered_df_dealer = filtered_df_dealer[
            (filtered_df_dealer["WADMPR"] == st.session_state.clicked_province) &
            (filtered_df_dealer["WADMKK"] == st.session_state.clicked_city) &
            (filtered_df_dealer["WADMKC"] == st.session_state.clicked_district)
        ]

    elif st.session_state.clicked_city:
        cust_title = f"Pertumbuhan Customer {buss_unit_title} di {st.session_state.clicked_city}, {st.session_state.clicked_province}"
        booking_title = f"Pertumbuhan Booking {buss_unit_title} di {st.session_state.clicked_city}, {st.session_state.clicked_province}"

        filters = {
            "WADMPR": st.session_state.clicked_province,
            "WADMKK": st.session_state.clicked_city,
        }

        if is_yamaha_mode or display_option in ("Retention Rate UFI", "NPL"):
            agg_vals = pd.Series({})
            agg_vals_book = pd.Series({})
        else:
            agg_vals, _ = aggregate_data(df_kab, filters, default_series)
            agg_vals_book, _ = aggregate_data(df_book_kab, filters, default_series)

        filtered_df_cab = filtered_df_cab[
            (filtered_df_cab["WADMPR"] == st.session_state.clicked_province) &
            (filtered_df_cab["WADMKK"] == st.session_state.clicked_city)
        ]
        filtered_df_dealer = filtered_df_dealer[
            (filtered_df_dealer["WADMPR"] == st.session_state.clicked_province) &
            (filtered_df_dealer["WADMKK"] == st.session_state.clicked_city)
        ]

        if is_yamaha_mode:
            sy = st.session_state.get("yamaha_start_selector", "2023")
            ey = st.session_state.get("yamaha_end_selector", "2024")
            end_col = f"YAMAHA_{ey}"
            top_5_centroid_kec = get_top_5(df_kec, filters, end_col)
        elif display_option in ("Retention Rate UFI", "NPL"):
            top_5_centroid_kec = None
        else:
            top_5_centroid_kec = get_top_5(
                df_kec,
                filters,
                f"{end_quarter_clicked}_CUST_NO"
            )

    elif st.session_state.clicked_province:
        cust_title = f"Pertumbuhan Customer {buss_unit_title} di {st.session_state.clicked_province}"
        booking_title = f"Pertumbuhan Booking {buss_unit_title} di {st.session_state.clicked_province}"

        filters = {"WADMPR": st.session_state.clicked_province}
        if is_yamaha_mode or display_option in ("Retention Rate UFI", "NPL"):
            agg_vals = pd.Series({})
            agg_vals_book = pd.Series({})
        else:
            agg_vals, _ = aggregate_data(df_prov, filters, default_series)
            agg_vals_book, _ = aggregate_data(df_book_prov, filters, default_series)
        if is_yamaha_mode or display_option in ("Retention Rate UFI", "NPL"):
            try:
                sy = st.session_state.get("yamaha_start_selector") or (st.session_state.get("selected_quarter") or ("2023","2024"))[0]
                ey = st.session_state.get("yamaha_end_selector") or (st.session_state.get("selected_quarter") or ("2023","2024"))[1]
            except Exception:
                sy, ey = "2023", "2024"
            if sy not in ("2023", "2024"):
                sy = "2023"
            if ey not in ("2024", "2025"):
                ey = "2024" if sy == "2023" else "2025"

            start_col = f"YAMAHA_{sy}"
            end_col = f"YAMAHA_{ey}"

            # if user asked to include NMC, add NMC_{year} into the Yamaha counts (both prov & kab)
            include_nmc = st.session_state.get("yamaha_include_nmc", False)

            # helper to add NMC columns into Yamaha columns if present
            def add_nmc_to_yamaha(df, sy, ey):
                y_s = f"YAMAHA_{sy}"
                y_e = f"YAMAHA_{ey}"
                n_s = f"NMC_{sy}"
                n_e = f"NMC_{ey}"
                # ensure columns exist
                if n_s in df.columns:
                    df[y_s] = df.get(y_s, 0).fillna(0) + df.get(n_s, 0).fillna(0)
                if n_e in df.columns:
                    df[y_e] = df.get(y_e, 0).fillna(0) + df.get(n_e, 0).fillna(0)
                return df

            if include_nmc:
                # Update province and kab dataframes to include NMC counts into YAMAHA_{year}
                try:
                    if 'df_yamaha_prov' in locals():
                        df_yamaha_prov = add_nmc_to_yamaha(df_yamaha_prov, sy, ey)
                except Exception:
                    pass
                try:
                    if 'df_yamaha_kab' in locals():
                        df_yamaha_kab = add_nmc_to_yamaha(df_yamaha_kab, sy, ey)
                except Exception:
                    pass

            # Proceed to compute totals as before (they now include NMC if checkbox on)
            try:
                cleaned_df_prov = clean_gdf_for_geo(df_prov)
                total_start = float(cleaned_df_prov[start_col].sum()) if start_col in cleaned_df_prov.columns else 0.0
                total_end   = float(cleaned_df_prov[end_col].sum())   if end_col in cleaned_df_prov.columns else 0.0
            except Exception:
                total_start = 0.0
                total_end = 0.0


            # FIXED: For Yamaha, use actual values without cumulative logic
            agg_vals = pd.Series({
                f"{sy}_CUST_NO": total_start,
                f"{ey}_CUST_NO": total_end,
                # For Yamaha, growth should be based on the actual annual values
                f"{ey}_GROWTH_NUMBER": total_end - total_start,
                f"{ey}_GROWTH_NUMBER_ALL": total_end - total_start,
                # Add growth percentage for the title display
                "MAP_GROWTH": ((total_end - total_start) / total_start * 100) if total_start != 0 else 0,
                "Usia Produktif": 0
            })
            agg_vals_book = pd.Series({})

            # top-5: use Yamaha end column if present
            try:
                cleaned_df = clean_gdf_for_geo(df_prov)
                if end_col in cleaned_df.columns:
                    top_5_centroid_prov = cleaned_df.nlargest(5, end_col)
                else:
                    top_5_centroid_prov = None
            except Exception:
                top_5_centroid_prov = None

    else:
        cust_title = f"Pertumbuhan Customer {buss_unit_title} Secara Nasional"
        booking_title = f"Pertumbuhan Booking {buss_unit_title} Secara Nasional"

        if not is_yamaha_mode and display_option != "NPL":
            try:
                agg_vals = df_prov.select_dtypes(include=np.number).sum(axis=0)
            except Exception:
                agg_vals = pd.Series({})

            if (globals().get("df_book_prov") is None) or (not isinstance(globals().get("df_book_prov"), (pd.DataFrame, pd.Series, gpd.GeoDataFrame))):
                agg_vals_book = pd.Series({})
            else:
                try:
                    agg_vals_book = df_book_prov.select_dtypes(include=np.number).sum(axis=0)
                except Exception:
                    agg_vals_book = pd.Series({})

            try:
                top_5_centroid_prov = df_prov.nlargest(5, f"{end_quarter_clicked}_CUST_NO")
            except Exception:
                top_5_centroid_prov = None

        elif display_option == "NPL":
            agg_vals = pd.Series({})
            agg_vals_book = pd.Series({})
            top_5_centroid_prov = None

        else:
            sy, ey = None, None
            # try to recover Yamaha selectors
            sy = st.session_state.get("yamaha_start_selector") or (st.session_state.get("selected_quarter") or ("2023","2024"))[0]
            ey = st.session_state.get("yamaha_end_selector") or (st.session_state.get("selected_quarter") or ("2023","2024"))[1]
            if sy not in ("2023", "2024"):
                sy = "2023"
            if ey not in ("2024", "2025"):
                ey = "2024" if sy == "2023" else "2025"

            start_col = f"YAMAHA_{sy}"
            end_col = f"YAMAHA_{ey}"

            # If df_prov is a GeoDataFrame (yamaha), sum the numeric Yamaha columns
            try:
                # Clean the dataframe before processing
                cleaned_df_prov = clean_gdf_for_geo(df_prov)
                total_start = float(cleaned_df_prov[start_col].sum()) if start_col in cleaned_df_prov.columns else 0.0
                total_end   = float(cleaned_df_prov[end_col].sum())   if end_col in cleaned_df_prov.columns else 0.0
            except Exception:
                total_start = 0.0
                total_end = 0.0

            # FIXED: Create proper agg_vals for Yamaha mode
            agg_vals = pd.Series({
                f"{sy}_CUST_NO": total_start,
                f"{ey}_CUST_NO": total_end,
                # Use the actual growth calculation for display
                f"{ey}_GROWTH_NUMBER": total_end - total_start,
                f"{ey}_GROWTH_NUMBER_ALL": total_end - total_start,
                # Add growth percentage for the title display
                "MAP_GROWTH": ((total_end - total_start) / total_start * 100) if total_start != 0 else 0
            })

            # booking intentionally disabled in Yamaha mode
            agg_vals_book = pd.Series({})

            # top-5: use df_prov order by YAMAHA_end_col if present
            try:
                if end_col in cleaned_df_prov.columns:
                    top_5_centroid_prov = cleaned_df_prov.nlargest(5, end_col)
                else:
                    top_5_centroid_prov = None
            except Exception:
                top_5_centroid_prov = None

    # ---------- FIFGROUP counts ----------
    fif_counts = _count_network(filtered_df_cab)
    dealer_counts = _count_dealer(filtered_df_dealer)

    # ---------- Kompetitor counts (BOTH categories) ----------
    if len(filtered_df_dealer) and "CATEGORY" in filtered_df_dealer.columns:
        cat_norm = _norm_series(filtered_df_dealer["CATEGORY"])
        df_comp_cabang = filtered_df_dealer.loc[cat_norm == "COMPETITOR CABANG"].copy()
        df_comp_pos    = filtered_df_dealer.loc[cat_norm == "COMPETITOR POS"].copy()
    else:
        df_comp_cabang = filtered_df_dealer.iloc[0:0].copy()
        df_comp_pos    = filtered_df_dealer.iloc[0:0].copy()

    counts_cabang = _brand_counts(df_comp_cabang)
    counts_pos    = _brand_counts(df_comp_pos)

    st.session_state.location_counts_comp = {
        "COMPETITOR CABANG": counts_cabang,
        "COMPETITOR POS":    counts_pos,
    }

    current_cat = str(st.session_state.get("competitor_category", "COMPETITOR CABANG")).strip().upper()
    current_brand_counts = st.session_state.location_counts_comp.get(
        current_cat, {k: 0 for k in list(counts_cabang.keys())}
    )

    st.session_state.location_counts = {
        "cabang": fif_counts.get("cabang", 0),
        "pos": fif_counts.get("pos", 0),
        "dealer": dealer_counts.get("dealer", 0),
        "pos_dealer": dealer_counts.get("pos_dealer", 0),
        "adira":   int(current_brand_counts.get("adira", 0)),
        "oto":     int(current_brand_counts.get("oto", 0)),
        "bfi":     int(current_brand_counts.get("bfi", 0)),
        "mega":    int(current_brand_counts.get("mega", 0)),
        "mandala": int(current_brand_counts.get("mandala", 0)),
        "hci":     int(current_brand_counts.get("hci", 0)),
        "bca":     int(current_brand_counts.get("bca", 0)),
        "kb":      int(current_brand_counts.get("kb", 0)),
        "aeon":    int(current_brand_counts.get("aeon", 0)),
        "others":  int(current_brand_counts.get("others", 0)),
    }

# Change Marker
def change_marker():
    current_selection = st.session_state.get("marker_value", set())
    st.session_state.selected_marker_keys = set(current_selection)

    st.session_state.show_cabang = (0 in st.session_state.marker_value)
    st.session_state.show_pos = (1 in st.session_state.marker_value)
    st.session_state.show_dealer = (2 in st.session_state.marker_value)
    st.session_state.show_pos_dealer = (3 in st.session_state.marker_value)

def change_marker2():
    current_selection = st.session_state.get("marker_value2", set())
    st.session_state.selected_marker2_keys = set(current_selection)

    st.session_state.show_adira   = (0 in st.session_state.marker_value2)
    st.session_state.show_oto     = (1 in st.session_state.marker_value2)
    st.session_state.show_bfi     = (2 in st.session_state.marker_value2)
    st.session_state.show_bank_mega = (3 in st.session_state.marker_value2)
    st.session_state.show_mandala = (4 in st.session_state.marker_value2)
    st.session_state.show_hci     = (5 in st.session_state.marker_value2)
    st.session_state.show_bca     = (6 in st.session_state.marker_value2)
    st.session_state.show_kb      = (7 in st.session_state.marker_value2)
    st.session_state.show_aeon    = (8 in st.session_state.marker_value2)
    st.session_state.show_others  = (9 in st.session_state.marker_value2)
    st.session_state.active_markers_tab = "competitor"

# Add Location Marker
def add_markers(feature_group, data, category_column, category_value, name_column, address_column, lat_column, long_column, icon_url, icon_size, competitor_category=None):
    # Filter data berdasarkan kategori kompetitor jika diberikan
    if competitor_category is not None:
        data = data[data[category_column] == competitor_category]
    
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

def add_region_marker( 
    feature_group, latitude, longitude, title, region_name,
    end_quarter_clicked, df_pulau, df_age_group_pulau, end_growth_col,
    selected_age_group="All", age_col_map=None, icon_size=(165, 9),
    show_age_group=False 
):
    display_option_now = st.session_state.get("display_option", st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)"))
    is_yamaha_mode = (display_option_now == "Polreg Yamaha (%)")
    is_npl_mode = (display_option_now == "NPL")  # ADD THIS LINE
    
    # ==== FORCE HIDE ALL DATAFRAME / TABLE OUTPUTS FOR YAMAHA MODE ====
    if is_yamaha_mode:
        def _blocked(*args, **kwargs):
            return None

        st.dataframe = _blocked
        st.table     = _blocked
        st.write     = (lambda *args, **kwargs: None)

        def write_safe(x):
            if not hasattr(x, "geometry"):
                st.text(str(x))
        st.write_safe = write_safe
    
    # SKIP ADDING REGION MARKERS FOR NPL MODE OR YAMAHA MODE
    if is_yamaha_mode or is_npl_mode:  # ADD THIS CONDITION
        return
    selected_buss_unit = st.session_state.get("selected_buss_unit", "ALL")
    selected_buss_unit2 = st.session_state.get("selected_buss_unit2", "None")

    row_pulau = df_pulau[df_pulau["PULAU"] == region_name]
    if end_growth_col not in row_pulau.columns or row_pulau.empty:
        total_cust = 0
    else:
        total_cust = int(row_pulau[end_growth_col].values[0])
    usia_text = ""

    if show_age_group and selected_age_group != "All" and age_col_map:
        row_age = df_age_group_pulau[df_age_group_pulau["PULAU"] == region_name]
        age_suffix = age_col_map.get(selected_age_group, "").strip()
        col_name = None

        # Case 1: ALL -> None
        if selected_buss_unit == "ALL" and selected_buss_unit2 == "None":
            col_name = f"AGE_{age_suffix}"

        # Case 2: LOB -> ALL
        elif selected_buss_unit in ["NMC", "MPF", "REFI"] and selected_buss_unit2 == "ALL":
            col_name = f"{selected_buss_unit} to ALL_{age_suffix}"

        # Case 3: ALL -> LOB
        elif selected_buss_unit == "ALL" and selected_buss_unit2 in ["NMC", "MPF", "REFI"]:
            col_name = f"ALL to {selected_buss_unit2}_{age_suffix}"

        # Case 4: LOB -> None
        elif selected_buss_unit in ["NMC", "MPF", "REFI"] and selected_buss_unit2 == "None":
            col_name = f"{selected_buss_unit}_{age_suffix}"

        # Case 5: LOB -> LOB
        elif selected_buss_unit == selected_buss_unit2 and selected_buss_unit in ["NMC", "MPF", "REFI"]:
            col_name = f"{selected_buss_unit} to {selected_buss_unit2}_{age_suffix}"
        
        # Case 6: LOB -> LOB
        elif selected_buss_unit in ["NMC", "MPF", "REFI"] and selected_buss_unit2 in ["NMC", "MPF", "REFI"]:
            col_name = f"{selected_buss_unit} to {selected_buss_unit2}_{age_suffix}"
        
        # Case 7: ALL -> ALL (TOTAL2)
        elif selected_buss_unit == "ALL" and selected_buss_unit2 == "ALL":
            col_name = f"TOTAL2_{age_suffix}"

        if col_name and not row_age.empty and col_name in row_age.columns:
            usia_val = int(row_age[col_name].values[0])
            buss_label = (
                f"{selected_buss_unit}" if selected_buss_unit2 == "None"
                else f"{selected_buss_unit}" if selected_buss_unit == selected_buss_unit2 == "ALL"
                else f"{selected_buss_unit} to {selected_buss_unit2}"
                )
            usia_text = f'''
                <div style="font-size: 12px; color: #666; margin-top: 4px;">
                    Usia {selected_age_group} untuk {buss_label}:
                    <span style="font-size: 12px; font-weight: bold; color: #0458af;">
                        {usia_val:,}
                    </span>
                </div>
            '''

    marker = folium.Marker(
        [latitude, longitude],
        icon=folium.features.DivIcon(
            icon_size=icon_size,
            icon_anchor=(70, 9),
            html=f'''
                <div style="
                    background-color: rgba(255, 255, 255, 0.9);
                    border-radius: 8px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 8px 15px;
                    text-align: center;
                    border: 2px solid #0458af;
                ">
                    <div style="font-size: 12px; color: #666; margin-bottom: 2px;">
                        {title} ({end_quarter_clicked})
                    </div>
                    <div style="font-size: 16px; font-weight: bold; color: #0458af;">
                        {total_cust:,}
                    </div>
                    {usia_text}
                </div>
            '''
        )
    )
    feature_group.add_child(marker)

# Add Legend
legend_template = f"""
    {{% macro html(this, kwargs) %}}
        <div id='maplegend' class='maplegend' style='position: fixed; z-index: 9999; background-color: rgba(255, 255, 255, 0.5); border-radius: 8px; padding: 7px; font-size: 12px; right: 10px; top: 10px;'>     
            <div class='legend-scale'>
                <ul class='legend-labels'>
                    <li><span style='background: yellow; opacity: 0.75;'></span>Top 5 Wilayah Berdasarkan Jumlah Customer ({end_quarter_clicked})</li>
                </ul>
            </div>
        </div> 
        <style type='text/css'>
            .maplegend .legend-scale ul {{margin: 0; padding: 0; color: #0f0f0f;}}
            .maplegend .legend-scale ul li {{list-style: none; line-height: 18px; margin-bottom: 1.5px;}}
            .maplegend ul.legend-labels li span {{float: left; height: 16px; width: 16px; margin-right: 4.5px;}}
        </style>
    {{% endmacro %}}
"""

def add_quadrant_legend_solid(map_obj, position="bottomright"):
    """
    Tambah HTML legend kotak 2x2 di peta (fixed).
    position param hanya untuk reference; kita set via CSS.
    """
    legend_html = """
    <div id="quadrant-legend" style="
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index:9999;
        background: rgba(255,255,255,0.95);
        padding: 8px 10px;
        border-radius: 6px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.2);
        font-family: Arial, Helvetica, sans-serif;
        font-size: 12px;
        line-height: 1.2;
    ">
      <div style="font-weight:600; margin-bottom:6px;">Polreg Yamaha (%) + NMC</div>
      <div style="display:flex; gap:6px; align-items:center;">
        <div style="display:flex; flex-direction:column; gap:6px;">
          <div style="display:flex; gap:6px; align-items:center;">
            <div style="width:18px; height:14px; background:#66bb6a; border:1px solid #999;"></div>
            <div>Yamaha ↑  —  NMC ↑</div>
          </div>
          <div style="display:flex; gap:6px; align-items:center;">
            <div style="width:18px; height:14px; background:#ffeb3b; border:1px solid #999;"></div>
            <div>Yamaha ↑  —  NMC ↓</div>
          </div>
        </div>
        <div style="display:flex; flex-direction:column; gap:6px; margin-left:10px;">
          <div style="display:flex; gap:6px; align-items:center;">
            <div style="width:18px; height:14px; background:#f57c00; border:1px solid #999;"></div>
            <div>Yamaha ↓  —  NMC ↑</div>
          </div>
          <div style="display:flex; gap:6px; align-items:center;">
            <div style="width:18px; height:14px; background:#f44336; border:1px solid #999;"></div>
            <div>Yamaha ↓  —  NMC ↓</div>
          </div>
        </div>
      </div>
    </div>
    """

def add_ufi_legend(map_obj):
    legend_html = """
    <div id="ufi-legend" style="
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        background: rgba(255,255,255,0.95);
        padding: 10px 14px;
        border-radius: 8px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.25);
        font-family: Arial, Helvetica, sans-serif;
        font-size: 12px;
        line-height: 1.4;
        min-width: 260px;
    ">
      <div style="font-weight:700; font-size:13px; margin-bottom:8px; color:#333;">Retention Rate UFI — Quadrant</div>

      <div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:6px;">
        <div style="min-width:36px; height:14px; margin-top:2px;
                    background: linear-gradient(to right, #c8facc, #006400);
                    border:1px solid #999; border-radius:2px;"></div>
        <div><b style="color:#006400;">Q1 — High Growth, High RR</b><br>
          <span style="color:#555;">Growth new customer tinggi &amp; retention rate tinggi. Wilayah terbaik.</span></div>
      </div>

      <div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:6px;">
        <div style="min-width:36px; height:14px; margin-top:2px;
                    background: linear-gradient(to right, #fff9c4, #FFD700);
                    border:1px solid #999; border-radius:2px;"></div>
        <div><b style="color:#b8860b;">Q2 — High Growth, Low RR</b><br>
          <span style="color:#555;">Customer baru banyak, namun retention rendah. Perlu program loyalitas.</span></div>
      </div>

      <div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:6px;">
        <div style="min-width:36px; height:14px; margin-top:2px;
                    background: linear-gradient(to right, #cfe8ff, #1E90FF);
                    border:1px solid #999; border-radius:2px;"></div>
        <div><b style="color:#1E90FF;">Q3 — Low Growth, High RR</b><br>
          <span style="color:#555;">Retention bagus, namun akuisisi customer baru lambat. Perlu ekspansi.</span></div>
      </div>

      <div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:6px;">
        <div style="min-width:36px; height:14px; margin-top:2px;
                    background: linear-gradient(to right, #f8c8c8, #B22222);
                    border:1px solid #999; border-radius:2px;"></div>
        <div><b style="color:#B22222;">Q4 — Low Growth, Low RR</b><br>
          <span style="color:#555;">Performa rendah di kedua dimensi. Prioritas utama untuk perbaikan.</span></div>
      </div>

      <div style="margin-top:6px; padding-top:5px; border-top:1px solid #ddd; color:#777; font-size:11px;">
      </div>
    </div>
    """
    from folium import Element
    map_obj.get_root().html.add_child(Element(legend_html))

# ------------------------------------- UFI -------------------------------------
def build_ufi_aggregation(df, group_cols):
    agg_cols = [
        "RR CUSTOMER",
        "TOTAL CUSTOMER",
        "GROWTH NEW CUSTOMER",
        "NEW CUSTOMER 2024Q4"
    ]

    df_agg = (
        df.groupby(group_cols)[agg_cols]
        .sum()
        .reset_index()
    )

    df_agg["% RR CUSTOMER"] = (
        df_agg["RR CUSTOMER"] /
        df_agg["TOTAL CUSTOMER"]
    ).replace([np.inf, -np.inf], 0).fillna(0)

    df_agg["%GROWTH NEW CUSTOMER"] = (
        df_agg["GROWTH NEW CUSTOMER"] /
        df_agg["NEW CUSTOMER 2024Q4"]
    ).replace([np.inf, -np.inf], 0).fillna(0)

    df_agg["Growth_Z"] = (
        (df_agg["%GROWTH NEW CUSTOMER"] -
         df_agg["%GROWTH NEW CUSTOMER"].mean()) /
         df_agg["%GROWTH NEW CUSTOMER"].std()
    )

    df_agg["RR_Z"] = (
        (df_agg["% RR CUSTOMER"] -
         df_agg["% RR CUSTOMER"].mean()) /
         df_agg["% RR CUSTOMER"].std()
    )

    def classify_z(row):
        if row["Growth_Z"] >= 0 and row["RR_Z"] >= 0:
            return "Q1"
        elif row["Growth_Z"] >= 0 and row["RR_Z"] < 0:
            return "Q2"
        elif row["Growth_Z"] < 0 and row["RR_Z"] >= 0:
            return "Q3"
        else:
            return "Q4"

    df_agg["QUADRANT"] = df_agg.apply(classify_z, axis=1)

    _provinsi_ke_pulau = {
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
        "BALI": "BALI", "NUSA TENGGARA BARAT": "BALI", "NUSA TENGGARA TIMUR": "BALI",
        "MALUKU": "MALUKU DAN PAPUA", "MALUKU UTARA": "MALUKU DAN PAPUA",
        "PAPUA": "MALUKU DAN PAPUA", "PAPUA BARAT": "MALUKU DAN PAPUA",
        "PAPUA SELATAN": "MALUKU DAN PAPUA", "PAPUA TENGAH": "MALUKU DAN PAPUA",
        "PAPUA PEGUNUNGAN": "MALUKU DAN PAPUA", "PAPUA BARAT DAYA": "MALUKU DAN PAPUA"
    }
    _has_pulau = "PULAU" in df_agg.columns
    if not _has_pulau and "WADMPR" in df_agg.columns:
        df_agg["PULAU"] = df_agg["WADMPR"].map(_provinsi_ke_pulau).fillna("LAINNYA")
    elif not _has_pulau:
        df_agg["PULAU"] = "LAINNYA"

    def _norm_group(series):
        mn, mx = series.min(), series.max()
        return (series - mn) / (mx - mn) if mx != mn else pd.Series(0.5, index=series.index)

    df_agg["RR_NORM"] = df_agg.groupby(["PULAU", "QUADRANT"])["% RR CUSTOMER"].transform(_norm_group)
    df_agg["GROWTH_NORM"] = df_agg.groupby(["PULAU", "QUADRANT"])["%GROWTH NEW CUSTOMER"].transform(_norm_group)
    df_agg["UFI_SCORE"] = (0.5 * df_agg["RR_NORM"] + 0.5 * df_agg["GROWTH_NORM"])

    if not _has_pulau:
        df_agg = df_agg.drop(columns=["PULAU"])
    return df_agg

# MAP STYLE UFI
cmap_q1 = branca.colormap.LinearColormap(["#c8facc", "#006400"], vmin=0, vmax=1)
cmap_q2 = branca.colormap.LinearColormap(["#fff9c4", "#FFD700"], vmin=0, vmax=1)
cmap_q3 = branca.colormap.LinearColormap(["#cfe8ff", "#1E90FF"], vmin=0, vmax=1)
cmap_q4 = branca.colormap.LinearColormap(["#f8c8c8", "#B22222"], vmin=0, vmax=1)
cmap_nonro = branca.colormap.LinearColormap(["#e0e0e0", "#808080"], vmin=0, vmax=1)
def style_function_ufi(feature):
    props = feature.get("properties", {})
    quad = props.get("QUADRANT")
    score = props.get("UFI_SCORE")
    # Default style jika data kosong
    default_style = {
        "fillColor": "#111111",
        "color": "black",
        "weight": 0.4,
        "fillOpacity": 0.85
    }
    if quad is None or score is None:
        return default_style
    # Safe convert score
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 0
    # Clamp 0–1
    score = max(0, min(score, 1))
    quad = str(quad).upper()
    if "Q1" in quad:
        color = cmap_q1(score)
    elif "Q2" in quad:
        color = cmap_q2(score)
    elif "Q3" in quad:
        color = cmap_q3(score)
    elif "Q4" in quad:
        color = cmap_q4(score)
    elif "NON RO" in quad:
        color = cmap_nonro(score)
    else:
        return default_style

    return {
        "fillColor": color,
        "color": "black",
        "weight": 0.4,
        "fillOpacity": 0.85
    }

def display_map(threshold):
    display_option = st.session_state.display_option
    global df_cab, df_dealer
    local_df_cab = df_cab.copy()
    local_df_dealer = df_dealer.copy()
    colormap_prov_html = None
    colormap_city_html = None
    colormap_district_html = None

    if st.session_state.clicked_city:
        city_data = df_kab[
            (df_kab["WADMKK"] == st.session_state.clicked_city) &
            (df_kab["WADMPR"] == st.session_state.clicked_province)
        ]
        local_df_cab = local_df_cab[
            (local_df_cab["WADMKK"] == st.session_state.clicked_city) &
            (local_df_cab["WADMPR"] == st.session_state.clicked_province)
        ]
        local_df_dealer = local_df_dealer[
            (local_df_dealer["WADMKK"] == st.session_state.clicked_city) &
            (local_df_dealer["WADMPR"] == st.session_state.clicked_province)
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

        st.session_state.show_top_5_centroid_kec = True
        st.session_state.show_top_5_centroid_kab = False
        st.session_state.show_top_5_centroid_prov = False

    elif st.session_state.clicked_province:
        province_data = df_prov[df_prov["WADMPR"] == st.session_state.clicked_province]
        local_df_cab = local_df_cab[
            (local_df_cab["WADMPR"] == st.session_state.clicked_province)
        ]
        local_df_dealer = local_df_dealer[
            (local_df_dealer["WADMPR"] == st.session_state.clicked_province)
        ]

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

        st.session_state.show_top_5_centroid_kec = False
        st.session_state.show_top_5_centroid_kab = True
        st.session_state.show_top_5_centroid_prov = False

    else:
        current_center = center_start
        current_zoom = zoom_start
        folium_bounds = [
            [min_latitude_start, min_longitude_start],
            [max_latitude_start, max_longitude_start]
        ]

        st.session_state.show_top_5_centroid_kec = False
        st.session_state.show_top_5_centroid_kab = False
        st.session_state.show_top_5_centroid_prov = True

    m = folium.Map(location=center_start, zoom_start=zoom_start, prefer_canvas=True, zoom_control=False)
    folium.TileLayer("CartoDB positron", name="Light Map", control=True).add_to(m)
    if display_option == "Polreg Yamaha (%)" and st.session_state.get("yamaha_include_nmc", False):
        add_quadrant_legend_solid(m)
    display_option_now = st.session_state.get("display_option", "Pertumbuhan Customer (%)")
    include_nmc = st.session_state.get("yamaha_include_nmc", False)

    if display_option == "Retention Rate UFI":
        if st.session_state.clicked_city:
            df_level = df_ufi_kec[
                (df_ufi_kec["WADMKK"] == st.session_state.clicked_city) &
                (df_ufi_kec["WADMPR"] == st.session_state.clicked_province)]
            tooltip_field = "WADMKC"
        elif st.session_state.clicked_province:
            df_level = df_ufi_kab
            tooltip_field = "WADMKK"
        else:
            df_level = df_ufi_prov
            tooltip_field = "WADMPR"

        ufi_tooltip = folium.GeoJsonTooltip(
            fields=[tooltip_field, "% RR CUSTOMER (fmt)", "%GROWTH NEW CUSTOMER (fmt)", "QUADRANT", "OSA (fmt)", "NSA (fmt)"],
            aliases=["Wilayah", "RR(%)", "Growth New Customer (%)", "Quadrant", "OSA (Dec 2025)", "NSA (Dec 2025)"]
        )

        cleaned = clean_gdf_for_geo(df_level)
        cleaned_df_prov = clean_gdf_for_geo(df_ufi_prov)

        folium.GeoJson(
            cleaned,
            style_function=style_function_ufi,
            highlight_function=highlight_function,
            tooltip=ufi_tooltip
        ).add_to(m)

        feature_group_to_add = folium.FeatureGroup(name="Cities")

        if st.session_state.clicked_province:
            prov_tooltip = folium.GeoJsonTooltip(
                fields=["WADMPR", "% RR CUSTOMER (fmt)", "%GROWTH NEW CUSTOMER (fmt)", "QUADRANT", "OSA (fmt)", "NSA (fmt)"],
                aliases=["Wilayah", "RR(%)", "Growth New Customer (%)", "Quadrant", "OSA (Dec 2025)", "NSA (fmt)"]
            )
            kab_tooltip = folium.GeoJsonTooltip(
                fields=["WADMKK", "% RR CUSTOMER (fmt)", "%GROWTH NEW CUSTOMER (fmt)", "QUADRANT", "OSA (fmt)", "NSA (fmt)"],
                aliases=["Wilayah", "RR(%)", "Growth New Customer (%)", "Quadrant", "OSA (Dec 2025)", "NSA (fmt)"]
            )

            feature_group_to_add.add_child(
                folium.GeoJson(
                    cleaned_df_prov,
                    style_function=lambda x: style_function2(x),
                    highlight_function=highlight_function,
                    tooltip=prov_tooltip
                )
            )

            city_data = df_ufi_kab[df_ufi_kab["WADMPR"] == st.session_state.clicked_province]
            cleaned_city_data = clean_gdf_for_geo(city_data)

            feature_group_to_add.add_child(
                folium.GeoJson(
                    cleaned_city_data,
                    style_function=style_function_ufi,
                    highlight_function=highlight_function,
                    tooltip=kab_tooltip
                )
            )

            if st.session_state.clicked_city:
                district_data = df_ufi_kec[
                    (df_ufi_kec["WADMKK"] == st.session_state.clicked_city) &
                    (df_ufi_kec["WADMPR"] == st.session_state.clicked_province)
                ]
                cleaned_district_data = clean_gdf_for_geo(district_data)

                if not district_data.empty and district_data.geometry.notna().all():
                    kec_tooltip = folium.GeoJsonTooltip(
                        fields=["WADMKC", "% RR CUSTOMER (fmt)", "%GROWTH NEW CUSTOMER (fmt)", "QUADRANT", "OSA (fmt)", "NSA (fmt)"],
                        aliases=["Wilayah", "RR(%)", "Growth New Customer (%)", "Quadrant", "OSA (Dec 2025)", "NSA (fmt)"]
                    )
                    feature_group_to_add.add_child(
                        folium.GeoJson(
                            cleaned_city_data,
                            style_function=lambda x: style_function2(x),
                            highlight_function=highlight_function,
                            tooltip=kab_tooltip
                        )
                    )
                    feature_group_to_add.add_child(
                        folium.GeoJson(
                            cleaned_district_data,
                            style_function=style_function_ufi,
                            highlight_function=highlight_function,
                            tooltip=kec_tooltip
                        )
                    )
                else:
                    st.session_state.show_top_5_centroid_kec = False
                    st.session_state.show_top_5_centroid_kab = True

    elif display_option == "NPL":
        # Pick the right level based on drill-down state
        if st.session_state.clicked_city:
            df_level = df_npl_kec[
                (df_npl_kec["WADMKK"] == st.session_state.clicked_city) &
                (df_npl_kec["WADMPR"] == st.session_state.clicked_province)]
        elif st.session_state.clicked_province:
            df_level = df_npl_kab[df_npl_kab["WADMPR"] == st.session_state.clicked_province]
        else:
            df_level = df_npl_prov

        colormap_npl, colname_npl = create_colormap(df_level, display_option, threshold)
        colormap_prov_html = colormap_to_html(colormap_npl, display_option)
        cleaned_npl = clean_gdf_for_geo(df_level)

        # Province outline for context when drilled in
        if st.session_state.clicked_province:
            cleaned_npl_prov = clean_gdf_for_geo(df_npl_prov)
            folium.GeoJson(
                cleaned_npl_prov,
                style_function=lambda x: style_function2(x),
                highlight_function=highlight_function,
                tooltip=folium.GeoJsonTooltip(
                    fields=["TOOLTIP"], aliases=[""], labels=False, sticky=False)
            ).add_to(m)

        npl_geo_tooltip = folium.GeoJsonTooltip(
            fields=["TOOLTIP"],
            aliases=[""],
            labels=False,
            sticky=False
        )

        folium.GeoJson(
            cleaned_npl,
            style_function=lambda feat: style_function(feat, colormap_npl, colname_npl),
            highlight_function=highlight_function,
            tooltip=npl_geo_tooltip
        ).add_to(m)

        feature_group_to_add = folium.FeatureGroup(name="Cities")

    else:
        colormap_prov, colname_prov = create_colormap(
        df_prov,
        display_option,
        threshold)
        colormap_prov_html = colormap_to_html(colormap_prov, display_option)
        cleaned_df_prov = clean_gdf_for_geo(df_prov)

        folium.GeoJson(
            cleaned_df_prov,
            style_function=lambda feat: style_function(
                feat,
                colormap_prov,
                colname_prov
            ),
            highlight_function=highlight_function,
            tooltip=create_tooltip("province")
        ).add_to(m)

    if display_option not in ("Retention Rate UFI", "NPL"):
        feature_group_to_add = folium.FeatureGroup(name="Cities")

    if st.session_state.clicked_province and display_option not in ("Retention Rate UFI", "NPL"):
        city_data = df_kab[df_kab["WADMPR"] == st.session_state.clicked_province]

        # Clean city_data before using
        cleaned_city_data = clean_gdf_for_geo(city_data)
        
        feature_group_to_add.add_child(
            folium.GeoJson(
                cleaned_df_prov,
                style_function=lambda x: style_function2(x),
                highlight_function=highlight_function,
                tooltip=create_tooltip("province")
            )
        )
        
        colormap_city, colname_city = create_colormap(city_data, display_option, threshold)
        colormap_city_html = colormap_to_html(colormap_city, display_option)

        feature_group_to_add.add_child(
            folium.GeoJson(
                cleaned_city_data,
                style_function=lambda feat: style_function(feat, colormap_city, colname_city),
                highlight_function=highlight_function,
                tooltip=create_tooltip("kabupaten")
            )
        )

        if st.session_state.clicked_city:
            district_data = df_kec[
                (df_kec["WADMKK"] == st.session_state.clicked_city) &
                (df_kec["WADMPR"] == st.session_state.clicked_province)
            ]
            
            # Clean district_data before using
            cleaned_district_data = clean_gdf_for_geo(district_data)
            
            if not district_data.empty and district_data.geometry.notna().all():
                feature_group_to_add.add_child(
                    folium.GeoJson(
                        cleaned_city_data,
                        style_function=lambda x: style_function2(x),
                        highlight_function=highlight_function,
                        tooltip=create_tooltip("kabupaten")
                    )
                )

                colormap_district, colname_district = create_colormap(district_data, display_option, threshold)
                colormap_district_html = colormap_to_html(colormap_district, display_option)

                feature_group_to_add.add_child(
                    folium.GeoJson(
                        cleaned_district_data,
                        style_function=lambda feat: style_function(feat, colormap_district, colname_district),
                        highlight_function=highlight_function,
                        tooltip=create_tooltip("kecamatan")
                    )
                )
            else:
                st.session_state.show_top_5_centroid_kec = False
                st.session_state.show_top_5_centroid_kab = True

    # Clean top data before adding to map
    if st.session_state.show_top_5_centroid_prov and top_5_centroid_prov is not None and display_option not in ("Retention Rate UFI", "NPL"):
        cleaned_top_prov = clean_gdf_for_geo(top_5_centroid_prov)
        feature_group_to_add.add_child(
            folium.GeoJson(
                cleaned_top_prov,
                style_function=lambda x: {
                    "fillColor": "transparent",
                    "color": "yellow",
                    "weight": 3,
                    "dashArray": "3, 3"
                },
                highlight_function=highlight_function,
                tooltip=create_tooltip("province")
            )
        )

    if st.session_state.show_top_5_centroid_kab and top_5_centroid_kab is not None and display_option != "NPL":
        cleaned_top_kab = clean_gdf_for_geo(top_5_centroid_kab)
        feature_group_to_add.add_child(
            folium.GeoJson(
                cleaned_top_kab,
                style_function=lambda x: {
                    "fillColor": "transparent",
                    "color": "yellow",
                    "weight": 3,
                    "dashArray": "3, 3"
                },
                highlight_function=highlight_function,
                tooltip=create_tooltip("kabupaten")
            )
        )

    if st.session_state.show_top_5_centroid_kec and top_5_centroid_kec is not None and display_option not in ("Retention Rate UFI", "NPL"):
        if hasattr(top_5_centroid_kec, "geometry") and top_5_centroid_kec.geometry.notna().all():
            cleaned_top_kec = clean_gdf_for_geo(top_5_centroid_kec)
            feature_group_to_add.add_child(
                folium.GeoJson(
                    cleaned_top_kec,
                    style_function=lambda x: {
                        "fillColor": "transparent",
                        "color": "yellow",
                        "weight": 3,
                        "dashArray": "3, 3"
                    },
                    highlight_function=highlight_function,
                    tooltip=create_tooltip("kecamatan")
                )
            )

    if st.session_state.show_cabang:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_cab,
            category_column="NETWORKING",
            category_value="CABANG",
            name_column="NAMA CABANG  / POS/ KIOS",
            address_column="ALAMAT KANTOR LENGKAP + NO + RT RW",
            lat_column="LAT",
            long_column="LONG",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/cabang2.png",
            icon_size=(25, 25)
        )

    if st.session_state.show_pos:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_cab,
            category_column="NETWORKING",
            category_value="POS",
            name_column="NAMA CABANG  / POS/ KIOS",
            address_column="ALAMAT KANTOR LENGKAP + NO + RT RW",
            lat_column="LAT",
            long_column="LONG",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/pos2.png",
            icon_size=(25, 25)
        )

    if st.session_state.show_dealer:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer,
            category_column="CATEGORY",
            category_value="DEALER",
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/dealer2.png",
            icon_size=(25, 25)
        )

    if st.session_state.show_pos_dealer:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer,
            category_column="CATEGORY",
            category_value="POS DEALER",
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/posdealer2.png",
            icon_size=(25, 25)
        )

    competitor_category = st.session_state.get("competitor_category", "COMPETITOR CABANG")

    if st.session_state.show_adira:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer[(local_df_dealer["COMPETITOR_CATEGORY"] == "ADIRA") & 
                                 (local_df_dealer["CATEGORY"] == st.session_state.get("competitor_category", "COMPETITOR CABANG"))],
            category_column="CATEGORY",
            category_value=st.session_state.get("competitor_category", "COMPETITOR CABANG"),
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/adira.png",
            icon_size=(25, 25),
            competitor_category=competitor_category
        )
    if st.session_state.show_oto:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer[(local_df_dealer["COMPETITOR_CATEGORY"] == "OTO") & 
                                 (local_df_dealer["CATEGORY"] == st.session_state.get("competitor_category", "COMPETITOR CABANG"))],
            category_column="CATEGORY",
            category_value=st.session_state.get("competitor_category", "COMPETITOR CABANG"),
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/oto.png",
            icon_size=(25, 25),
            competitor_category=competitor_category
        )

    if st.session_state.show_bfi:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer[(local_df_dealer["COMPETITOR_CATEGORY"] == "BFI") & 
                                 (local_df_dealer["CATEGORY"] == st.session_state.get("competitor_category", "COMPETITOR CABANG"))],
            category_column="CATEGORY",
            category_value=st.session_state.get("competitor_category", "COMPETITOR CABANG"),
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/bfi.png",
            icon_size=(25, 25),
            competitor_category=competitor_category
        )
    if st.session_state.show_bank_mega:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer[(local_df_dealer["COMPETITOR_CATEGORY"] == "MEGA") & 
                                 (local_df_dealer["CATEGORY"] == st.session_state.get("competitor_category", "COMPETITOR CABANG"))],
            category_column="CATEGORY",
            category_value=st.session_state.get("competitor_category", "COMPETITOR CABANG"),
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/mega.png",
            icon_size=(25, 25),
            competitor_category=competitor_category
        )
    if st.session_state.show_mandala:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer[(local_df_dealer["COMPETITOR_CATEGORY"] == "MANDALA") & 
                                 (local_df_dealer["CATEGORY"] == st.session_state.get("competitor_category", "COMPETITOR CABANG"))],
            category_column="CATEGORY",
            category_value=st.session_state.get("competitor_category", "COMPETITOR CABANG"),
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/mandala.png",
            icon_size=(25, 25),
            competitor_category=competitor_category
        )
    if st.session_state.show_hci:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer[(local_df_dealer["COMPETITOR_CATEGORY"] == "HCI") & 
                                 (local_df_dealer["CATEGORY"] == st.session_state.get("competitor_category", "COMPETITOR CABANG"))],
            category_column="CATEGORY",
            category_value=st.session_state.get("competitor_category", "COMPETITOR CABANG"),
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/hci.png",
            icon_size=(25, 25),
            competitor_category=competitor_category
        )

    if st.session_state.show_bca:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer[(local_df_dealer["COMPETITOR_CATEGORY"] == "BCA FINANCE") & 
                                 (local_df_dealer["CATEGORY"] == st.session_state.get("competitor_category", "COMPETITOR CABANG"))],
            category_column="CATEGORY",
            category_value=st.session_state.get("competitor_category", "COMPETITOR CABANG"),
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/bca.png",
            icon_size=(25, 25),
            competitor_category=competitor_category
        )
    if st.session_state.show_kb:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer[(local_df_dealer["COMPETITOR_CATEGORY"] == "KB") & 
                                 (local_df_dealer["CATEGORY"] == st.session_state.get("competitor_category", "COMPETITOR CABANG"))],
            category_column="CATEGORY",
            category_value=st.session_state.get("competitor_category", "COMPETITOR CABANG"),
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/kb.png",
            icon_size=(25, 25),
            competitor_category=competitor_category
        )
    if st.session_state.show_aeon:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer[(local_df_dealer["COMPETITOR_CATEGORY"] == "AEON") & 
                                 (local_df_dealer["CATEGORY"] == st.session_state.get("competitor_category", "COMPETITOR CABANG"))],
            category_column="CATEGORY",
            category_value=st.session_state.get("competitor_category", "COMPETITOR CABANG"),
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/aeon.png",
            icon_size=(25, 25),
            competitor_category=competitor_category
        )
    if st.session_state.show_others:
        add_markers(
            feature_group=feature_group_to_add,
            data=local_df_dealer[(local_df_dealer["COMPETITOR_CATEGORY"] == "OTHERS") & 
                                 (local_df_dealer["CATEGORY"] == st.session_state.get("competitor_category", "COMPETITOR CABANG"))],
            category_column="CATEGORY",
            category_value=st.session_state.get("competitor_category", "COMPETITOR CABANG"),
            name_column="LOCATION_NAME",
            address_column="ADDRESS",
            lat_column="LATITUDE",
            long_column="LONGITUDE",
            icon_url="https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/others.png",
            icon_size=(25, 25),
            competitor_category=competitor_category
        )
    age_col_map = {
        "< 20 Tahun": "<20",
        "20 - 30 Tahun": "20-30",
        "30 - 40 Tahun": "30-40",
        "40 - 50 Tahun": "40-50",
        "> 50 Tahun": ">50"}
    
    selected_age_group = st.session_state.get("selected_age_group", "All")
    selected_buss_unit = st.session_state.get("selected_buss_unit", "ALL")
    selected_buss_unit2 = st.session_state.get("selected_buss_unit2", "None")

    show_age_group = (
        selected_age_group != "All" and (
            selected_buss_unit in ["ALL", "NMC", "MPF", "REFI"] and
            selected_buss_unit2 in ["None", "ALL", "NMC", "MPF", "REFI"]
            )
            )
    age_col_map = {
        "< 20 Tahun": "<20",
        "20 - 30 Tahun": "20-30",
        "30 - 40 Tahun": "30-40",
        "40 - 50 Tahun": "40-50",
        "> 50 Tahun": ">50"}
    
    selected_age_group = st.session_state.get("selected_age_group", "All")
    selected_buss_unit = st.session_state.get("selected_buss_unit", "ALL")
    selected_buss_unit2 = st.session_state.get("selected_buss_unit2", "None")

    show_age_group = (
        selected_age_group != "All" and (
            selected_buss_unit in ["ALL", "NMC", "MPF", "REFI"] and
            selected_buss_unit2 in ["None", "ALL", "NMC", "MPF", "REFI"]
            )
            )
    region_coords = [
        ("SUMATERA", -5.747174, 99.711047),
        ("JAWA", -9.405710, 110.870711),
        ("KALIMANTAN", 5.908332, 111.563161),
        ("SULAWESI", 4.969557, 121.953024),
        ("MALUKU DAN PAPUA", 2.791889, 133.497665),
        ("BALI", -9.095678, 129.455505)]

    display_option_now = st.session_state.get("display_option", st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)"))
    is_yamaha_mode = (display_option_now == "Polreg Yamaha (%)")
    if is_yamaha_mode:
        def _blocked(*args, **kwargs):
            return None

        st.dataframe = _blocked
        st.table     = _blocked
        st.write     = (lambda *args, **kwargs: None)

        def write_safe(x):
            if not hasattr(x, "geometry"):
                st.text(str(x))
        st.write_safe = write_safe

    if not is_yamaha_mode and display_option != "NPL":
        for region_name, lat, lon in region_coords:
            icon_sz = (210, 9) if region_name == "MALUKU DAN PAPUA" else (165, 9)
            add_region_marker(
                feature_group_to_add,
                lat,
                lon,
                region_name,
                region_name,
                end_quarter_clicked,
                df_pulau,
                df_age_group_pulau,
                end_growth_col,
                selected_age_group,
                age_col_map,
                icon_size=icon_sz,
                show_age_group=show_age_group)
    else:
        pass
        
    for region_name, lat, lon in region_coords:
        icon_sz = (210, 9) if region_name == "MALUKU DAN PAPUA" else (165, 9)
        add_region_marker(
            feature_group_to_add,
            lat,
            lon,
            region_name,
            region_name,
            end_quarter_clicked,
            df_pulau,
            df_age_group_pulau,
            end_growth_col,
            selected_age_group,
            age_col_map,
            icon_size=icon_sz,
            show_age_group=show_age_group)
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

    return m, colormap_prov_html, colormap_city_html, colormap_district_html

# ----------------------------------------------------------------- Booking Growth Metrics -----------------------------------------------------------------
# Create Metrics
def create_metric_html(data_previous, data_current, logo_url, others=False):
    total_book_previous = data_previous 
    total_book_current = data_current
    total_book_growth = ((total_book_current - total_book_previous) / total_book_previous * 100) if total_book_previous != 0 else 0  

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
# ----------------------------------------------------------------- Yamaha Mode Handler -----------------------------------------------------------------
def handle_yamaha_mode(prefix="yamaha"):
    """
    Yamaha UI: three tick choices representing the *pair* (start->end):
      - 2023 - 2024        -> "2324"
      - 2024 - 2025        -> "2425"
      - 2023 - 2025        -> "2325"
    Implemented as three checkboxes but enforced mutually-exclusive via callbacks.
    Keeps session_state keys (all keys are prefixed by `prefix` to avoid duplicate-key errors):
      - {prefix}_cb_2324, {prefix}_cb_2425, {prefix}_cb_2325  (checkbox states)
      - {prefix}_range_choice ("2324", "2425" or "2325")
      - {prefix}_start_selector, {prefix}_end_selector
      - {prefix}_selected_quarter (tuple)
    Default: 2023-2024 selected.
    """

    # helper to build full key names
    def k(name):
        return f"{prefix}_{name}"

    # --- initialize defaults once (only if none of the cb keys exist) ---
    if (
        k("cb_2324") not in st.session_state
        and k("cb_2425") not in st.session_state
        and k("cb_2325") not in st.session_state
    ):
        st.session_state[k("cb_2324")] = True
        st.session_state[k("cb_2425")] = False
        st.session_state[k("cb_2325")] = False
        st.session_state[k("range_choice")] = "2324"
        st.session_state[k("start_selector")] = "2023"
        st.session_state[k("end_selector")] = "2024"
        st.session_state[k("selected_quarter")] = ("2023", "2024")

    # map choice -> (start, end)
    choice_map = {
        "2324": ("2023", "2024"),
        "2425": ("2024", "2025"),
        "2325": ("2023", "2025"),
    }

    # --- callbacks to enforce exclusivity and prevent "none selected" ---
    def _on_2324():
        # If user turned the 2324 box ON -> turn the others OFF and set selectors
        if st.session_state.get(k("cb_2324"), False):
            st.session_state[k("cb_2425")] = False
            st.session_state[k("cb_2325")] = False
            st.session_state[k("range_choice")] = "2324"
            sy, ey = choice_map["2324"]
            st.session_state[k("start_selector")] = sy
            st.session_state[k("end_selector")] = ey
            st.session_state[k("selected_quarter")] = (sy, ey)
        else:
            # prevent unchecking the only active option -> re-enable it
            st.session_state[k("cb_2324")] = True
            st.session_state[k("range_choice")] = "2324"
            sy, ey = choice_map["2324"]
            st.session_state[k("start_selector")] = sy
            st.session_state[k("end_selector")] = ey
            st.session_state[k("selected_quarter")] = (sy, ey)

    def _on_2425():
        if st.session_state.get(k("cb_2425"), False):
            st.session_state[k("cb_2324")] = False
            st.session_state[k("cb_2325")] = False
            st.session_state[k("range_choice")] = "2425"
            sy, ey = choice_map["2425"]
            st.session_state[k("start_selector")] = sy
            st.session_state[k("end_selector")] = ey
            st.session_state[k("selected_quarter")] = (sy, ey)
        else:
            st.session_state[k("cb_2425")] = True
            st.session_state[k("range_choice")] = "2425"
            sy, ey = choice_map["2425"]
            st.session_state[k("start_selector")] = sy
            st.session_state[k("end_selector")] = ey
            st.session_state[k("selected_quarter")] = (sy, ey)

    def _on_2325():
        if st.session_state.get(k("cb_2325"), False):
            st.session_state[k("cb_2324")] = False
            st.session_state[k("cb_2425")] = False
            st.session_state[k("range_choice")] = "2325"
            sy, ey = choice_map["2325"]
            st.session_state[k("start_selector")] = sy
            st.session_state[k("end_selector")] = ey
            st.session_state[k("selected_quarter")] = (sy, ey)
        else:
            st.session_state[k("cb_2325")] = True
            st.session_state[k("range_choice")] = "2325"
            sy, ey = choice_map["2325"]
            st.session_state[k("start_selector")] = sy
            st.session_state[k("end_selector")] = ey
            st.session_state[k("selected_quarter")] = (sy, ey)

    st.markdown("<div style='font-weight:bold;'>Pilih Range Waktu (Yamaha):</div>", unsafe_allow_html=True)

    # put three choices in a row (adjust layout as needed)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.checkbox(
            "2023 - 2024",
            value=st.session_state.get(k("cb_2324"), True),
            key=k("cb_2324"),
            on_change=_on_2324,
        )
    with col2:
        st.checkbox(
            "2024 - 2025",
            value=st.session_state.get(k("cb_2425"), False),
            key=k("cb_2425"),
            on_change=_on_2425,
        )
    with col3:
        st.checkbox(
            "2023 - 2025",
            value=st.session_state.get(k("cb_2325"), False),
            key=k("cb_2325"),
            on_change=_on_2325,
        )

    # --- safety: ensure yamaha_start/end and selected_quarter are present and consistent ---
    choice = st.session_state.get(k("range_choice"), "2324")
    sy, ey = choice_map.get(choice, ("2023", "2024"))
    st.session_state[k("start_selector")] = sy
    st.session_state[k("end_selector")] = ey
    st.session_state[k("selected_quarter")] = (sy, ey)

    # --- add NMC toggle for Yamaha mode ---
    # default: False (off). User can tick to include NMC counts into Yamaha growth.
    if f"{prefix}_include_nmc" not in st.session_state:
        st.session_state[f"{prefix}_include_nmc"] = False

    # show checkbox in the Yamaha mode UI
    st.checkbox(
        "NMC",
        key=k("include_nmc"),
        help="Kontrak NMC",
        on_change=lambda: None
    )

# ----------------------------------------------------------------- Filters -----------------------------------------------------------------
def update_filter():
    bu1 = st.session_state.get("cycle_bu1", "None")
    bu2 = st.session_state.get("cycle_bu2", "None")
    bu3 = st.session_state.get("cycle_bu3", "None")
    using_cycle = any(b != "None" for b in [bu1, bu2, bu3])
    if using_cycle:
        if st.session_state.get("buss_unit", None) != "ALL":
            st.session_state["buss_unit"] = "ALL"
        if st.session_state.get("buss_unit2", None) != "None":
            st.session_state["buss_unit2"] = "None"
        if st.session_state.get("selected_age_group", None) != "All":
            st.session_state["selected_age_group"] = "All"
    st.rerun()

def trigger_reset():
    st.session_state.trigger_reset_from_bu_cycle = True
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

# ----------------------------------------------------------------- Customer Growth Prediction -----------------------------------------------------------------
def generate_prediction_html(
    df, region_col, start_year=2025, n_quarter=4, top_n=5,
    title="Prediksi Jumlah Customer", show_all=False,
    format_func=lambda x: f"{x:,.0f}" if pd.notna(x) else "-"
):
    # List historical quarters sampai 2026Q1
    historical_quarters = ["2019", *[f"{y}Q{q}" for y in range(2020, 2027) for q in range(1, 5)]]
    historical_quarters = historical_quarters[:historical_quarters.index("2026Q1") + 1]

    # Prediksi dimulai dari 2026Q1
    pred_quarters = []
    year, q = start_year, 4
    for _ in range(n_quarter):
        pred_quarters.append(f"{year}Q{q}_PRED")
        q += 1
        if q > 4:
            q = 1
            year += 1

    # Hanya ambil kolom prediksi yang tersedia
    pred_quarters = [col for col in pred_quarters if col in df.columns]

    if show_all:
        top_n = df[region_col].nunique()

    # Buat ranking berdasarkan setiap kolom
    rankings = {}
    for quarter in historical_quarters:
        col = f"{quarter}_CUST_NO"
        if col in df.columns:
            rankings[col] = df.sort_values(by=col, ascending=False)[region_col].tolist()
    for col in pred_quarters:
        if col in df.columns:
            rankings[col] = df.sort_values(by=col, ascending=False)[region_col].tolist()

    html = f"""
    <div style="margin-top: 20px; margin-bottom: 10px;">
        <div style="font-size: 15px; font-weight: bold; color: #0458af; margin-bottom: 8px;">{title}</div>
        <div class="trend-table" style="width: 100%; overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; box-shadow: 0 2px 3px rgba(0,0,0,0.1); font-size: 12px;">
                <thead>
                    <tr>
                        <th style="width: 70px; background-color: #f2f2f2; padding: 6px; text-align: center;">Ranking</th>
    """
    for quarter in historical_quarters:
        html += f"""
            <th style="width: 160px; background-color: #eaf4e5; padding: 6px; text-align: center;" colspan="2">{quarter}</th>
        """
    for col in pred_quarters:
        quarter = col.replace("_PRED", "")
        html += f"""
            <th style="width: 160px; background-color: #d9ecf5; padding: 6px; text-align: center;" colspan="2">{quarter}</th>
        """
    html += """
                    </tr>
                    <tr>
                        <th></th>
    """
    for _ in historical_quarters:
        html += """
            <th style="width: 150px; background-color: #f8f8f8; padding: 5px; text-align: left;">Wilayah</th>
            <th style="width: 140px; background-color: #f8f8f8; padding: 5px; text-align: right;">Actual</th>
        """
    for _ in pred_quarters:
        html += """
            <th style="width: 150px; background-color: #f8f8f8; padding: 5px; text-align: left;">Wilayah</th>
            <th style="width: 140px; background-color: #f8f8f8; padding: 5px; text-align: right;">Prediksi</th>
        """
    html += """
                    </tr>
                </thead>
                <tbody>
    """

    for rank in range(top_n):
        html += f"""<tr><td style="text-align: center; font-weight: bold;">{rank + 1}</td>"""
        prev_region = None

        # Historical actuals
        for quarter in historical_quarters:
            col = f"{quarter}_CUST_NO"
            growth_col = f"{quarter}_GROWTH"
            col_rankings = rankings.get(col, [])
            if rank < len(col_rankings):
                wilayah = col_rankings[rank]
                row = df[df[region_col] == wilayah].iloc[0]

                actual_val = row.get(col)
                growth_val = row.get(growth_col)
                actual_fmt = format_func(actual_val) if pd.notnull(actual_val) else "-"
                growth_fmt = f"{growth_val:.2f}%" if pd.notnull(growth_val) else "-"

                highlight = ""
                if prev_region and wilayah != prev_region:
                    highlight = "background-color: rgba(65, 182, 196, 0.3);"

                html += f"""
                    <td style="padding: 5px; text-align: left; {highlight}">{wilayah}</td>
                    <td style="padding: 5px; text-align: right; {highlight}">
                        {actual_fmt}<br><span style="font-size: 11px; color: #666;">({growth_fmt})</span>
                    </td>
                """
                prev_region = wilayah
            else:
                html += "<td>-</td><td>-</td>"
                prev_region = None

        # Prediction values
        for col in pred_quarters:
            col_rankings = rankings.get(col, [])
            if rank < len(col_rankings):
                wilayah = col_rankings[rank]
                row = df[df[region_col] == wilayah].iloc[0]
                pred_val = row.get(col)

                # Format prediksi sebagai bilangan bulat
                pred_fmt = f"{int(round(pred_val)):,}" if pd.notnull(pred_val) else "-"

                highlight = ""
                if prev_region and wilayah != prev_region:
                    highlight = "background-color: rgba(65, 182, 196, 0.3);"

                html += f"""
                    <td style="padding: 5px; text-align: left; {highlight}">{wilayah}</td>
                    <td style="padding: 5px; text-align: right; {highlight} font-weight: bold;">{pred_fmt}</td>
                """
                prev_region = wilayah
            else:
                html += "<td>-</td><td>-</td>"

        html += "</tr>"

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
    st.image("assets/images/FIFGROUP.png", use_container_width=True)    

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

specific_time = datetime(2025, 7, 11, 16, 11)    
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

display_option_now = st.session_state.get("display_option", st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)"))
is_yamaha_mode = (display_option_now == "Polreg Yamaha (%)")
# ==== FORCE HIDE ALL DATAFRAME / TABLE OUTPUTS FOR YAMAHA MODE ====
if is_yamaha_mode:

    def _blocked(*args, **kwargs):
        return None

    st.dataframe = _blocked
    st.table     = _blocked
    st.write     = (lambda *args, **kwargs: None)   # careful: hides all writes

    # If you still need normal writes (text):
    def write_safe(x):
        if not hasattr(x, "geometry"):
            st.text(str(x))
    st.write_safe = write_safe

# Filters
def reset_cycle_units():
    st.session_state["cycle_bu1"] = "None"
    st.session_state["cycle_bu2"] = "None"
    st.session_state["cycle_bu3"] = "None"

# Reset jika BU awal ≠ ALL atau BU akhir ≠ None
if (
    st.session_state.get("buss_unit", "ALL") != "ALL"
    or st.session_state.get("buss_unit2", "None") != "None"
):
    reset_cycle_units()
    
quarter_options = [
    "2019", "2020Q1", "2020Q2", "2020Q3", "2020Q4", 
    "2021Q1", "2021Q2", "2021Q3", "2021Q4", 
    "2022Q1", "2022Q2", "2022Q3", "2022Q4", 
    "2023Q1", "2023Q2", "2023Q3", "2023Q4", 
    "2024Q1", "2024Q2", "2024Q3", "2024Q4",
    "2025Q1", "2025Q2", "2025Q3", "2025Q4",
    "2026Q1"
]

buss_unit_options = ["ALL", "NMC", "REFI", "MPF"]
buss_unit2_options = ["None", "ALL", "NMC", "REFI", "MPF"]

sorter_options = [
    "Pertumbuhan Customer (%)", 
    "Pertumbuhan Customer", 
    "Rasio Customer dan Usia Produktif 2024 (%)", 
    "Rasio Pertumbuhan Cust. (> 1x) dan Total Cust. (%)",
    "Polreg Yamaha (%)",
    "Retention Rate UFI",
    "NPL"
]

# col1, col2, col3, col4, col5 = st.columns([1.2, 1.2, 1.2, 1.2, 1.2])
# col6, col7, col8 = st.columns([1.2, 1.2, 1.2])

# Fungsi untuk memperbarui state setelah filter diganti
def update_filter():
    st.session_state.selected_quarter = st.session_state.quarter
    st.session_state.selected_buss_unit = st.session_state.buss_unit
    st.session_state.selected_buss_unit2 = st.session_state.buss_unit2
    st.session_state.selected_age_group = st.session_state.selected_age_group
    st.session_state.selected_sorter = st.session_state.display_option

# Filter
quarter_options = [
    "2019", "2020Q1", "2020Q2", "2020Q3", "2020Q4",
    "2021Q1", "2021Q2", "2021Q3", "2021Q4",
    "2022Q1", "2022Q2", "2022Q3", "2022Q4",
    "2023Q1", "2023Q2", "2023Q3", "2023Q4",
    "2024Q1", "2024Q2", "2024Q3", "2024Q4",
    "2025Q1", "2025Q2", "2025Q3", "2025Q4",
    "2026Q1"
]

buss_unit_options  = ["ALL", "NMC", "REFI", "MPF"]
buss_unit2_options = ["None", "ALL", "NMC", "REFI", "MPF"]

sorter_options = [
    "Pertumbuhan Customer (%)",
    "Pertumbuhan Customer",
    "Rasio Customer dan Usia Produktif 2024 (%)",
    "Rasio Pertumbuhan Cust. (> 1x) dan Total Cust. (%)", 
    "Polreg Yamaha (%)",
    "Retention Rate UFI",
    "NPL"
]

col1, col2, col3, col4, col5 = st.columns([1.2] * 5)
col6, col7, col8 = st.columns([1.2] * 3)

if st.session_state.get("trigger_reset_from_bu_cycle", False):
    st.session_state["buss_unit"] = "ALL"
    st.session_state["buss_unit2"] = "None"
    st.session_state["selected_buss_unit"] = "ALL"
    st.session_state["selected_buss_unit2"] = "None"
    st.session_state["selected_age_group"] = "All"
    st.session_state.trigger_reset_from_bu_cycle = False
    st.rerun()

with col1:
    # Checkbox "Data from 2010"
    data_from_2010 = st.checkbox(
        "Data from 2010",
        key="data_from_2010",
        on_change=update_filter
    )
    quarter_opts = (["2010"] + quarter_options) if data_from_2010 else quarter_options

    selected_quarter = st.session_state.get("selected_quarter", ("2019", "2026Q1"))
    if not data_from_2010 and isinstance(selected_quarter, tuple) and selected_quarter[0] == "2010":
        selected_quarter = ("2019", selected_quarter[1])
    current_display_option = st.session_state.get("display_option",
                                                 st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)"))
    
    if current_display_option == "Polreg Yamaha (%)":
        handle_yamaha_mode()
    elif current_display_option == "NPL":
        st.markdown("<div style='color:#999; font-size:13px; padding-top:6px;'>Pilih Range Waktu: <i>N/A untuk NPL</i></div>", unsafe_allow_html=True)
    else:
        quarter = st.select_slider(
            label="Pilih Range Waktu:",
            options=quarter_opts,
            value=selected_quarter,
            key="quarter",
            on_change=update_filter,
            help="Geser slider ini untuk memilih range quarter"
        )

SPACER_PX = 24
spacer_html = f"<div style='height:{SPACER_PX}px'></div>"

# --- FILTERS (refactored for Yamaha mode) ---
# determine if Yamaha UI mode is active (display_option may not exist yet in first run)
display_option_current = st.session_state.get("display_option", st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)"))
is_yamaha_ui = display_option_current in ["Polreg Yamaha (%)", "Retention Rate UFI", "NPL"]
if is_yamaha_ui:
    st.session_state["buss_unit"] = "ALL"
    st.session_state["buss_unit2"] = "None"
    st.session_state["selected_age_group"] = "All"
    st.session_state["cycle_bu1"] = "None"
    st.session_state["cycle_bu2"] = "None"
    st.session_state["cycle_bu3"] = "None"

with col2:
    st.markdown(spacer_html, unsafe_allow_html=True)
    default_buss_unit = st.session_state.get("selected_buss_unit", "ALL")
    try:
        default_buss_unit_index = buss_unit_options.index(default_buss_unit)
    except Exception:
        default_buss_unit_index = 0
    buss_unit = st.selectbox(
        label="Pilih Business Unit Awal:",
        options=buss_unit_options,
        index=default_buss_unit_index,
        key="buss_unit",
        on_change=update_filter,
        help="Klik dropdown ini untuk melihat business unit awal",
        disabled=is_yamaha_ui
    )

with col3:
    st.markdown(spacer_html, unsafe_allow_html=True)
    default_buss_unit2 = st.session_state.get("selected_buss_unit2", "None")
    try:
        default_buss_unit2_index = buss_unit2_options.index(default_buss_unit2)
    except Exception:
        default_buss_unit2_index = 0
    buss_unit2 = st.selectbox(
        label="Pilih Business Unit Akhir:",
        options=buss_unit2_options,
        index=default_buss_unit2_index,
        key="buss_unit2",
        on_change=update_filter,
        help="Klik dropdown ini untuk melihat business unit akhir",
        disabled=is_yamaha_ui
    )

with col4:
    st.markdown(spacer_html, unsafe_allow_html=True)
    age_group_options = ["All", "< 20 Tahun", "20 - 30 Tahun", "30 - 40 Tahun", "40 - 50 Tahun", "> 50 Tahun"]
    default_age_group = st.session_state.get(
        "age_group_reset",
        st.session_state.get("selected_age_group", age_group_options[0])
    )
    try:
        default_age_index = age_group_options.index(default_age_group)
    except Exception:
        default_age_index = 0
    selected_age_group = st.selectbox(
        label="Pilih Kelompok Usia per 2026Q1:",
        options=age_group_options,
        index=default_age_index,
        key="selected_age_group",
        help="Pilih kelompok usia",
        disabled=is_yamaha_ui
    )

with col5:
    st.markdown(spacer_html, unsafe_allow_html=True)
    default_sorter = st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)")
    try:
        default_sorter_index = sorter_options.index(default_sorter)
    except Exception:
        default_sorter_index = 0
    # display_option must remain enabled so user can switch into/out of Yamaha mode
    display_option = st.selectbox(
        label="Pilih Metrik:",
        options=sorter_options,
        index=default_sorter_index,
        key="display_option",
        on_change=update_filter,
        help="Klik dropdown ini untuk memilih metrik"
    )
    display_option_current = st.session_state.get("display_option", "")
    st.session_state["hide_tables"] = display_option_current in ["Polreg Yamaha (%)", "Retention Rate UFI", "NPL"]

with col6:
    st.markdown(spacer_html, unsafe_allow_html=True)
    cycle_bu1 = st.selectbox(
        label="Business Unit 1:",
        options=["None", "NMC", "REFI", "MPF"],
        index=0,
        key="cycle_bu1",
        on_change=update_filter,
        help="Pilih Business Unit pertama",
        disabled=is_yamaha_ui
    )

with col7:
    st.markdown(spacer_html, unsafe_allow_html=True)
    cycle_bu2 = st.selectbox(
        label="Business Unit 2:",
        options=["None", "NMC", "REFI", "MPF"],
        index=0,
        key="cycle_bu2",
        on_change=update_filter,
        help="Pilih Business Unit kedua",
        disabled=is_yamaha_ui
    )

with col8:
    st.markdown(spacer_html, unsafe_allow_html=True)
    cycle_bu3 = st.selectbox(
        label="Business Unit 3:",
        options=["None", "NMC", "REFI", "MPF"],
        index=0,
        key="cycle_bu3",
        on_change=update_filter,
        help="Pilih Business Unit ketiga",
        disabled=is_yamaha_ui
    )

if is_yamaha_ui:
    # prefer explicit yamaha selectors (fall back to session selected_quarter)
    start_quarter_clicked = st.session_state.get("yamaha_start_selector", st.session_state.get("selected_quarter", ("2023","2024"))[0])
    end_quarter_clicked = st.session_state.get("yamaha_end_selector", st.session_state.get("selected_quarter", ("2023","2024"))[1])
else:
    # normal mode uses the generic selected_quarter
    start_quarter_clicked = st.session_state.get("selected_quarter", ("2019", "2026Q1"))[0]
    end_quarter_clicked = st.session_state.get("selected_quarter", ("2019", "2026Q1"))[1]

buss_unit_clicked = st.session_state.get("selected_buss_unit", "ALL")
buss_unit2_clicked = st.session_state.get("selected_buss_unit2", "None")
start_growth_col = f"{start_quarter_clicked}_CUST_NO"
end_growth_col = f"{end_quarter_clicked}_CUST_NO"

if (
    display_option == "Rasio Pertumbuhan Cust. (> 1x) dan Total Cust. (%)"
    and buss_unit2_clicked == "None"
):
    st.html(
        f"""
        <div style="background-color: #fff3cd; padding: 12px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
            <p style="color: #856404; font-size: 18px; text-align: center; margin: 0;">
                ⚠️ Untuk menggunakan metrik <strong>{display_option}</strong>,
                harap mengganti filter <strong>Pilih Business Unit Akhir</strong> menjadi selain <strong>None</strong>.
            </p>
        </div>
        """
    )
else:
    # ---- Data Preprocessing: normal flow OR Polreg Yamaha (%) special flow ----
    # Determine whether we are in Yamaha mode
    is_yamaha_mode = (display_option == "Polreg Yamaha (%)")

    if is_yamaha_mode:
        # Determine selected start/end years (we expect these set by the UI override earlier)
        # Fall back to selected_quarter if present in a different shape
        sy = None
        ey = None
        sy = st.session_state.get("yamaha_start_selector") or st.session_state.get("selected_quarter", ("2023","2024"))[0]
        ey = st.session_state.get("yamaha_end_selector") or st.session_state.get("selected_quarter", ("2023","2024"))[1]

        # fallback: selected_quarter might be a tuple (start, end)
        if not sy or not ey:
            sq = st.session_state.get("selected_quarter")
            if isinstance(sq, (list, tuple)) and len(sq) == 2:
                sy, ey = sq[0], sq[1]
            elif isinstance(sq, str):
                # if single string like "2023-2024", try to split
                parts = sq.replace(" ", "").replace("–", "-").split("-")
                if len(parts) >= 2:
                    sy, ey = parts[0], parts[1]

        # final fallbacks to defaults
        if sy not in ("2023", "2024"):
            sy = "2023"
        if ey not in ("2024", "2025"):
            ey = "2024" if sy == "2023" else "2025"

        start_col = f"YAMAHA_{sy}"
        end_col = f"YAMAHA_{ey}"

        # Ensure df_yamaha_prov/df_yamaha_kab exist, else create empty geo-dataframes fallback.
        try:
            df_yamaha_prov  # reference to check existence
            df_yamaha_kab
        except Exception:
            # attempt best-effort fallback using shp_prov/shp_kab if available
            try:
                df_yamaha_prov = shp_prov[["WADMPR", "geometry"]].copy()
                df_yamaha_prov[start_col] = 0
                df_yamaha_prov[end_col] = 0
            except Exception:
                # last-resort: empty DataFrame
                df_yamaha_prov = pd.DataFrame(columns=["WADMPR", "geometry", start_col, end_col])

            try:
                df_yamaha_kab = shp_kab[["WADMKK", "WADMPR", "geometry"]].copy()
                df_yamaha_kab[start_col] = 0
                df_yamaha_kab[end_col] = 0
            except Exception:
                df_yamaha_kab = pd.DataFrame(columns=["WADMKK", "WADMPR", "geometry", start_col, end_col])

        # Coerce numeric and fillna
        for gdf in [df_yamaha_prov, df_yamaha_kab]:
            if start_col not in gdf.columns:
                gdf[start_col] = 0
            if end_col not in gdf.columns:
                gdf[end_col] = 0
            gdf[start_col] = pd.to_numeric(gdf[start_col], errors="coerce").fillna(0)
            gdf[end_col]   = pd.to_numeric(gdf[end_col], errors="coerce").fillna(0)

            # --- compute Yamaha growth as before ---
            with np.errstate(divide="ignore", invalid="ignore"):
                gdf["MAP_GROWTH_YAMAHA"] = np.where(
                    gdf[start_col] != 0,
                    (gdf[end_col] - gdf[start_col]) / gdf[start_col] * 100,
                    0.0,
                )
            # sanitize
            gdf["MAP_GROWTH_YAMAHA"] = gdf["MAP_GROWTH_YAMAHA"].replace([np.inf, -np.inf, np.nan], 0.0)
            gdf["MAP_GROWTH_YAMAHA_NUMBER"] = (gdf[end_col] - gdf[start_col]).fillna(0)

            # --- compute NMC growth (if NMC columns exist) ---
            nmc_start_col = f"NMC_{sy}"
            nmc_end_col   = f"NMC_{ey}"

            # Ensure NMC columns exist (create zero if missing so code below is safe)
            if nmc_start_col not in gdf.columns:
                gdf[nmc_start_col] = 0
            if nmc_end_col not in gdf.columns:
                gdf[nmc_end_col] = 0

            with np.errstate(divide="ignore", invalid="ignore"):
                gdf["MAP_GROWTH_NMC"] = np.where(
                    gdf[nmc_start_col] != 0,
                    (gdf[nmc_end_col] - gdf[nmc_start_col]) / gdf[nmc_start_col] * 100,
                    0.0,
                )
            gdf["MAP_GROWTH_NMC"] = gdf["MAP_GROWTH_NMC"].replace([np.inf, -np.inf, np.nan], 0.0)
            gdf["MAP_GROWTH_NMC_NUMBER"] = (gdf[nmc_end_col] - gdf[nmc_start_col]).fillna(0)

            # --- compute combined growth used for coloring the map when user selects NMC inclusion ---
            # By default we keep Yamaha-only behavior. If user ticks NMC, we blend Yamaha+NMC.
            include_nmc = st.session_state.get("yamaha_include_nmc", False)

            def _sign(x):
                try:
                    x = float(x)
                    if x > 0: return 1
                    if x < 0: return -1
                    return 0
                except:
                    return 0

            # pastikan combined ada (jika NMC tidak dicentang maka fallback)
            if "MAP_GROWTH_COMBINED" not in gdf.columns:
                gdf["MAP_GROWTH_COMBINED"] = (
                    abs(gdf["MAP_GROWTH_YAMAHA"].fillna(0)) +
                    abs(gdf["MAP_GROWTH_NMC"].fillna(0))
                ) / 2

            from collections import defaultdict
            qmax = defaultdict(lambda: 0.0)

            # hitung max absolut per-kuadran
            for _, r in gdf.iterrows():
                gy = r.get("MAP_GROWTH_YAMAHA", 0)
                gn = r.get("MAP_GROWTH_NMC", 0)
                gc = r.get("MAP_GROWTH_COMBINED", 0)

                quad = (_sign(gy), _sign(gn))

                val = abs(gc) if not np.isnan(gc) else max(abs(gy), abs(gn))

                if val > qmax[quad]:
                    qmax[quad] = val

            # hindari zero division
            for k in qmax:
                if qmax[k] == 0:
                    qmax[k] = 1

            # buat kolom MAP_GROWTH_SCALED → dipakai colormap
            def _scaled(r):
                gy = r.get("MAP_GROWTH_YAMAHA", 0)
                gn = r.get("MAP_GROWTH_NMC", 0)
                gc = r.get("MAP_GROWTH_COMBINED", 0)

                quad = (_sign(gy), _sign(gn))
                denom = qmax.get(quad, 1)

                return float(gc) / float(denom)

            gdf["MAP_GROWTH_SCALED"] = gdf.apply(_scaled, axis=1)

        # tooltips for polreg yamaha
        # Revised tooltip functions: render HTML table with BU rows and columns:
        #   As of {sy} | As of {ey} | Δ | Rasio (%)
        # Shows rows for available business-units. If NMC checkbox enabled, NMC row included.

        def _fmt_int(x):
            try:
                return int(x)
            except Exception:
                return 0

        def _thousands(x):
            try:
                return f"{int(x):,}"
            except Exception:
                return "0"

        def _pct(delta, base):
            try:
                base = float(base)
                if base == 0:
                    return "—"
                return f"{(float(delta) / base * 100):.2f}%"
            except Exception:
                return "—"

        def _make_table(rows, sy, ey):
            """
            rows: list of tuples - bisa (bu_name, as_start, as_end) ATAU (bu_name, as_start, as_end, delta, growth_pct)
            returns HTML table string
            """
            # Cek mode berdasarkan panjang tuple
            is_quadrant_mode = len(rows[0]) == 5 if rows else False
            
            if is_quadrant_mode:
                # Mode 4 Kuadran (5 kolom)
                header = (
                    f"<table style='border-collapse:collapse; font-size:11px; width:100%;'>"
                    f"<thead>"
                    f"<tr style='background-color: #f8f9fa;'>"
                    f"<th style='padding:6px 8px; text-align:left; border-bottom:1px solid #ddd;'> </th>"
                    f"<th style='padding:6px 8px; text-align:right; border-bottom:1px solid #ddd;'>{sy}</th>"
                    f"<th style='padding:6px 8px; text-align:right; border-bottom:1px solid #ddd;'>{ey}</th>"
                    f"<th style='padding:6px 8px; text-align:right; border-bottom:1px solid #ddd;'>Δ</th>"
                    f"<th style='padding:6px 8px; text-align:right; border-bottom:1px solid #ddd;'>Growth (%)</th>"
                    f"</tr>"
                    f"</thead>"
                    f"<tbody>"
                )
                body = ""
                for bu, s, e, d, g in rows:
                    s_i = _fmt_int(s)
                    e_i = _fmt_int(e)
                    d_val = d
                    g_val = g
                    
                    # Format numbers
                    s_fmt = _thousands(s_i)
                    e_fmt = _thousands(e_i)
                    d_fmt = _thousands(d_val)
                    try:
                        g_fmt = f"{float(g_val):.2f}%" if g_val is not None else "—"
                    except:
                        g_fmt = "—"
                    
                    # Color coding untuk growth
                    try:
                        g_color = "#28a745" if float(g_val) > 0 else "#dc3545" if float(g_val) < 0 else "#6c757d"
                    except:
                        g_color = "#6c757d"
                    
                    body += (
                        "<tr>"
                        f"<td style='padding:4px 8px; text-align:left; border-bottom:1px solid #f2f2f2; font-weight:bold;'>{bu}</td>"
                        f"<td style='padding:4px 8px; text-align:right; border-bottom:1px solid #f2f2f2;'>{s_fmt}</td>"
                        f"<td style='padding:4px 8px; text-align:right; border-bottom:1px solid #f2f2f2;'>{e_fmt}</td>"
                        f"<td style='padding:4px 8px; text-align:right; border-bottom:1px solid #f2f2f2; font-weight:bold;'>{d_fmt}</td>"
                        f"<td style='padding:4px 8px; text-align:right; border-bottom:1px solid #f2f2f2; color:{g_color}; font-weight:bold;'>{g_fmt}</td>"
                        "</tr>"
                    )
                footer = "</tbody></table>"
                return header + body + footer
                
            else:
                # Mode Normal (3 kolom)
                header = (
                    f"<table style='border-collapse:collapse; font-size:12px;'>"
                    f"<thead>"
                    f"<tr>"
                    f"<th style='padding:6px 8px; text-align:left; border-bottom:1px solid #ddd;'> </th>"
                    f"<th style='padding:6px 8px; text-align:right; border-bottom:1px solid #ddd;'>{sy}</th>"
                    f"<th style='padding:6px 8px; text-align:right; border-bottom:1px solid #ddd;'>{ey}</th>"
                    f"<th style='padding:6px 8px; text-align:right; border-bottom:1px solid #ddd;'>Δ</th>"
                    f"<th style='padding:6px 8px; text-align:right; border-bottom:1px solid #ddd;'>Rasio (%)</th>"
                    f"</tr>"
                    f"</thead>"
                    f"<tbody>"
                )
                body = ""
                for bu, s, e in rows:
                    s_i = _fmt_int(s)
                    e_i = _fmt_int(e)
                    d = e_i - s_i
                    r = _pct(d, s_i)
                    body += (
                        "<tr>"
                        f"<td style='padding:4px 8px; text-align:left; border-bottom:1px solid #f2f2f2;'>{bu}</td>"
                        f"<td style='padding:4px 8px; text-align:right; border-bottom:1px solid #f2f2f2;'>{_thousands(s_i)}</td>"
                        f"<td style='padding:4px 8px; text-align:right; border-bottom:1px solid #f2f2f2;'>{_thousands(e_i)}</td>"
                        f"<td style='padding:4px 8px; text-align:right; border-bottom:1px solid #f2f2f2;'>{_thousands(d)}</td>"
                        f"<td style='padding:4px 8px; text-align:right; border-bottom:1px solid #f2f2f2;'>{r}</td>"
                        "</tr>"
                    )
                footer = "</tbody></table>"
                return header + body + footer
        def prov_tooltip(r):
            """
            Province tooltip — disamakan tampilannya untuk mode normal & mode Yamaha+NMC.
            """
            sy = st.session_state.get("yamaha_start_selector", "2023")
            ey = st.session_state.get("yamaha_end_selector", "2024")
            include_nmc = st.session_state.get("yamaha_include_nmc", False)
            display_option_now = st.session_state.get("display_option", "Pertumbuhan Customer (%)")

            # =============== FUNGSI BANTU ===============
            def get_growth(prefix):
                try:
                    s = float(r.get(f"{prefix}_{sy}", 0))
                    e = float(r.get(f"{prefix}_{ey}", 0))
                    return ((e - s) / s) * 100 if s != 0 else 0.0
                except:
                    return 0.0

            def get_abs(prefix, year):
                try:
                    return int(float(r.get(f"{prefix}_{year}", 0)))
                except:
                    return 0

            # =============== HITUNG NILAI ================
            y_s = get_abs("YAMAHA", sy)
            y_e = get_abs("YAMAHA", ey)
            y_d = y_e - y_s
            y_g = get_growth("YAMAHA")

            rows = [("YAMAHA", y_s, y_e, y_d, y_g)]

            # Jika NMC diaktifkan → tambahkan NMC ke tabel
            if display_option_now == "Polreg Yamaha (%)" and include_nmc:
                n_s = get_abs("NMC", sy)
                n_e = get_abs("NMC", ey)
                n_d = n_e - n_s
                n_g = get_growth("NMC")
                rows.append(("NMC", n_s, n_e, n_d, n_g))
                avg_growth = (abs(y_g) + abs(n_g)) / 2
            else:
                avg_growth = y_g

            # =============== BANGUN TABEL ===============
            table_html = _make_table(rows, sy, ey)

            # =============== RINGKASAN ===============
            summary_color = "#28a745" if avg_growth > 0 else "#dc3545" if avg_growth < 0 else "#6c757d"

            summary_html = (
                f"<div style='margin-top:8px; padding:6px; background:#f8f9fa; border-radius:6px; "
                f"border:1px solid #dee2e6; text-align:center;'>"
                f"<span style='font-weight:bold; color:{summary_color};'>"
                f"</span></div>"
            )

            # =============== WRAPPER TOOLTIP (STANDARD) ===============
            header = r.get("WADMPR", "-")

            return (
                f"<div style='min-width:380px; font-family:Arial, sans-serif; font-size:12px; "
                f"border:1px solid #0458af; border-radius:8px; padding:12px; background:#ffffff;'>"
                f"<div style='font-weight:700; color:#0458af; margin-bottom:8px; "
                f"font-size:14px; border-bottom:1px solid #e9ecef; padding-bottom:6px;'>"
                f"{header}</div>"
                f"{table_html}"
                f"{summary_html}"
                f"</div>"
            )

        def kab_tooltip(r):
            """
            Kabupaten tooltip — disamakan tampilannya untuk mode normal & Yamaha+NMC.
            """
            sy = st.session_state.get("yamaha_start_selector", "2023")
            ey = st.session_state.get("yamaha_end_selector", "2024")
            include_nmc = st.session_state.get("yamaha_include_nmc", False)
            display_option_now = st.session_state.get("display_option", "Pertumbuhan Customer (%)")

            # =============== FUNGSI BANTU ===============
            def get_growth(prefix):
                try:
                    s = float(r.get(f"{prefix}_{sy}", 0))
                    e = float(r.get(f"{prefix}_{ey}", 0))
                    return ((e - s) / s) * 100 if s != 0 else 0.0
                except:
                    return 0.0

            def get_abs(prefix, year):
                try:
                    return int(float(r.get(f"{prefix}_{year}", 0)))
                except:
                    return 0

            # =============== HITUNG NILAI ================
            y_s = get_abs("YAMAHA", sy)
            y_e = get_abs("YAMAHA", ey)
            y_d = y_e - y_s
            y_g = get_growth("YAMAHA")

            rows = [("YAMAHA", y_s, y_e, y_d, y_g)]

            if display_option_now == "Polreg Yamaha (%)" and include_nmc:
                n_s = get_abs("NMC", sy)
                n_e = get_abs("NMC", ey)
                n_d = n_e - n_s
                n_g = get_growth("NMC")
                rows.append(("NMC", n_s, n_e, n_d, n_g))
                avg_growth = (abs(y_g) + abs(n_g)) / 2
            else:
                avg_growth = y_g

            # =============== BANGUN TABEL ===============
            table_html = _make_table(rows, sy, ey)

            # =============== RINGKASAN ===============
            summary_color = "#28a745" if avg_growth > 0 else "#dc3545" if avg_growth < 0 else "#6c757d"

            summary_html = (
                f"<div style='margin-top:8px; padding:6px; background:#f8f9fa; border-radius:6px; "
                f"border:1px solid #dee2e6; text-align:center;'>"
                f"<span style='font-weight:bold; color:{summary_color};'>"
                f"</span></div>"
            )

            # =============== HEADER ====================
            kab = r.get("WADMKK", "-")
            prov = r.get("WADMPR", "-")
            header = f"{kab}, {prov}" if kab != "-" else prov

            # =============== WRAPPER TOOLTIP (STANDARD) ===============
            return (
                f"<div style='min-width:380px; font-family:Arial, sans-serif; font-size:12px; "
                f"border:1px solid #0458af; border-radius:8px; padding:12px; background:#ffffff;'>"
                f"<div style='font-weight:700; color:#0458af; margin-bottom:8px; "
                f"font-size:14px; border-bottom:1px solid #e9ecef; padding-bottom:6px;'>"
                f"{header}</div>"
                f"{table_html}"
                f"{summary_html}"
                f"</div>"
            )


        # Apply tooltips if geometry/rows exist
        if not df_yamaha_prov.empty:
            df_yamaha_prov["TOOLTIP"] = df_yamaha_prov.apply(prov_tooltip, axis=1)
        else:
            df_yamaha_prov["TOOLTIP"] = []

        if not df_yamaha_kab.empty:
            df_yamaha_kab["TOOLTIP"] = df_yamaha_kab.apply(kab_tooltip, axis=1)
        else:
            df_yamaha_kab["TOOLTIP"] = []

        df_prov = df_yamaha_prov.copy()
        df_kab  = df_yamaha_kab.copy()
        try:
            df_kec = shp_kec[["WADMKC","WADMKK","WADMPR","geometry"]].copy()
            df_kec["TOOLTIP"] = ""
            df_kec["MAP_GROWTH"] = 0.0
            df_kec["MAP_GROWTH_NUMBER"] = 0
        except Exception:
            df_kec = pd.DataFrame(columns=["WADMKC","WADMKK","WADMPR","geometry","TOOLTIP","MAP_GROWTH","MAP_GROWTH_NUMBER"])

        df_book_prov = None
        df_book_kab  = None
        df_book_kec  = None

    elif display_option == "NPL":
        # NPL uses its own dedicated dfs — no growth calculation needed
        # Add formatted NPL tooltip to each npl df
        def _fmt_npl_tooltip(row, name_field):
            name = row.get(name_field, "-")
            npl_val = row.get("MAP_NPL", 0)
            return (
                f"<div style='font-family:Arial,sans-serif; font-size:13px; padding:8px; "
                f"border:1px solid #0458af; border-radius:8px; background:#fff; min-width:200px;'>"
                f"<div style='font-weight:bold; color:#0458af; margin-bottom:6px;'>{name}</div>"
                f"<table style='width:100%; border-collapse:collapse; font-size:12px;'>"
                f"<tr><td style='padding:3px 6px;'>NPL</td>"
                f"<td style='padding:3px 6px; font-weight:bold; color:#b22222;'>{npl_val:.2f}%</td></tr>"
                f"</table></div>"
            )

        df_npl_prov["TOOLTIP"] = df_npl_prov.apply(lambda r: _fmt_npl_tooltip(r, "WADMPR"), axis=1)
        df_npl_kab["TOOLTIP"]  = df_npl_kab.apply(lambda r: _fmt_npl_tooltip(r, "WADMKK"), axis=1)
        df_npl_kec["TOOLTIP"]  = df_npl_kec.apply(lambda r: _fmt_npl_tooltip(r, "WADMKC"), axis=1)

        df_book_prov = None
        df_book_kab  = None
        df_book_kec  = None

    else:
        df_pulau, df_prov, df_kab, df_kec = calculate_growth(df_pulau, df_prov, df_kab, df_kec)

        df_book_prov = process_df_booking(df_book_prov)
        df_book_kab = process_df_booking(df_book_kab)
        df_book_kec = process_df_booking(df_book_kec)
        
        df_prov["TOOLTIP"] = df_prov.apply(lambda row: format_tooltip(row, row["WADMPR"]), axis=1)
        df_kab["TOOLTIP"] = df_kab.apply(lambda row: format_tooltip(row, row["WADMKK"]), axis=1)
        df_kec["TOOLTIP"] = df_kec.apply(lambda row: format_tooltip(row, row["WADMKC"]), axis=1)

    # Customer Growth Title
    with st.container(key="container_customer_growth_title"):
        col1 = st.columns(1)

        # update titles and agg_vals (as your code expects)
        update_titles_and_agg_vals()

        # helper safe getter for agg_vals with fallback to df_prov Yamaha columns
        def safe_agg_get(key, fallback_year=None):
            # try agg_vals first (agg_vals may be pd.Series or dict)
            try:
                if isinstance(agg_vals, (pd.Series, dict)) and key in agg_vals:
                    val = agg_vals.get(key)
                    if pd.isna(val):
                        raise KeyError
                    return float(val)
            except Exception:
                pass
            # fallback: if Yamaha style year provided, sum from df_prov
            if fallback_year is not None and 'df_prov' in globals():
                # prefer cumulative column
                cum_col = f"YAMAHA_{fallback_year}_CUM"
                ann_col = f"YAMAHA_{fallback_year}"
                try:
                    if cum_col in df_prov.columns:
                        return float(pd.to_numeric(df_prov[cum_col], errors="coerce").fillna(0).sum())
                    if ann_col in df_prov.columns:
                        return float(pd.to_numeric(df_prov[ann_col], errors="coerce").fillna(0).sum())
                except Exception:
                    return 0.0
            # final fallback
            return 0.0

        # determine whether this is Yamaha mode
        display_option_now = st.session_state.get("display_option", st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)"))
        is_yamaha_mode = (display_option_now == "Polreg Yamaha (%)")
        # ==== FORCE HIDE ALL DATAFRAME / TABLE OUTPUTS FOR YAMAHA MODE ====
        if is_yamaha_mode:
            def _blocked(*args, **kwargs):
                return None

            st.dataframe = _blocked
            st.table     = _blocked
            st.write     = (lambda *args, **kwargs: None)

            def write_safe(x):
                if not hasattr(x, "geometry"):
                    st.text(str(x))
            st.write_safe = write_safe


        start_q = start_quarter_clicked if 'start_quarter_clicked' in globals() else st.session_state.get("start_quarter_clicked", "2019")
        end_q = end_quarter_clicked if 'end_quarter_clicked' in globals() else st.session_state.get("end_quarter_clicked", "2026Q1")

        def quarter_to_year(q):
            try:
                if isinstance(q, str) and "Q" in q:
                    return q.split("Q")[0]
                if isinstance(q, str) and q.isdigit() and len(q) == 4:
                    return q
            except Exception:
                pass
            return None

        start_year_for_yamaha = quarter_to_year(start_q)
        end_year_for_yamaha = quarter_to_year(end_q)
        try:
            # start_growth_col and end_growth_col are set by update_titles_and_agg_vals() in your code
            total_cust_previous = safe_agg_get(start_growth_col, fallback_year=start_year_for_yamaha)
        except Exception:
            total_cust_previous = safe_agg_get(None, fallback_year=start_year_for_yamaha)

        try:
            total_cust_current = safe_agg_get(end_growth_col, fallback_year=end_year_for_yamaha)
        except Exception:
            total_cust_current = safe_agg_get(None, fallback_year=end_year_for_yamaha)

        # compute growth percent safely
        try:
            if total_cust_previous != 0 and not pd.isna(total_cust_previous):
                cust_growth = ((total_cust_current - total_cust_previous) / total_cust_previous) * 100.0
            else:
                cust_growth = 0.0
        except Exception:
            cust_growth = 0.0

        # attempt to get growth numbers; fallback to 0 if missing
        try:
            cust_growth_number = float(agg_vals.get(f"{end_q}_GROWTH_NUMBER", np.nan)) if isinstance(agg_vals, (pd.Series, dict)) else np.nan
        except Exception:
            cust_growth_number = np.nan
        try:
            cust_growth_number_all = float(agg_vals.get(f"{end_q}_GROWTH_NUMBER_ALL", np.nan)) if isinstance(agg_vals, (pd.Series, dict)) else np.nan
        except Exception:
            cust_growth_number_all = np.nan

        # cust ratio threshold safe compute
        try:
            if (not pd.isna(cust_growth_number_all)) and cust_growth_number_all != 0:
                cust_ratio_threshold = (cust_growth_number / cust_growth_number_all) * 100.0
            else:
                cust_ratio_threshold = 0.0
        except Exception:
            cust_ratio_threshold = 0.0

        # colors and symbols
        growth_color = "#28a745" if cust_growth > 0 else "#ff0000" if cust_growth < 0 else "#4c5773"
        growth_symbol = "▲" if cust_growth > 0 else "▼" if cust_growth < 0 else ""

        with col1[0]:
            # if Yamaha mode and you prefer to hide tables elsewhere, we still show the title summary.
            # The numbers will be fetched via fallback logic above.
            st.html(
                f'''  
                <div style="display: flex; justify-content: space-between; align-items: center;">  
                    <div style="font-size: 18px; font-weight: bold; color: #0458af;">{cust_title}</div>  
                    <div style="text-align: right; display: flex; align-items: center;">  
                        <div style="font-size: 16px; margin-right: 10px;">  
                            <strong>{start_q}</strong>: {int(total_cust_previous):,} | <strong>{end_q}</strong>: {int(total_cust_current):,}  
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
        with st.container(key="container_customer_growth_map"):
            map_col = st.columns(1)
            with map_col[0]:
                if st.session_state.get("display_option") == "Polreg Yamaha (%)":
                    note_html = """
                        <div style="
                            background-color: #fff3cd;
                            border-left: 6px solid #ffcc00;
                            padding: 10px 15px;
                            margin-bottom: 10px;
                            border-radius: 6px;
                            font-size: 14px;
                            color: #4c4a00;
                        ">
                            <b>Catatan:</b><br>
                            Angka unit Yamaha pada peta adalah jumlah unit yang melalui proses <i>Police Registration</i> 
                            pada periode tahun tersebut, <b>bukan angka penjualan</b> atau <b>merepresentasikan total market</b>. Angka 
                            tersebut merupakan hasil kumulatif dari periode yang dipilih pada filter.
                        </div>
                    """
                    if st.session_state.get("yamaha_include_nmc", False):
                        quadrant_html = """
                        <div style="
                            background:#ffffff;
                            padding:10px;
                            border-radius:8px;
                            box-shadow:0 2px 6px rgba(0,0,0,0.08);
                            font-size:13px;
                            color:#222;
                            margin-bottom:10px;
                        ">
                            <div style="font-weight:600; margin-bottom:8px;">Yamaha - NMC</div>

                            <div style="display:flex; flex-direction:column; gap:10px;">

                                <!-- Row 1 -->
                                <div style="display:flex; gap:28px; flex-wrap:wrap;">
                                    <div style="display:flex; align-items:center; gap:8px; min-width:260px;">
                                        <div style="width:18px; height:14px; background:#66bb6a; border:1px solid #ccc;"></div>
                                        <div>Yamaha <b>Meningkat</b> &nbsp;–&nbsp; NMC <b>Meningkat</b></div>
                                    </div>

                                    <div style="display:flex; align-items:center; gap:8px; min-width:260px;">
                                        <div style="width:18px; height:14px; background:#f57c00; border:1px solid #ccc;"></div>
                                        <div>Yamaha <b>Menurun</b> &nbsp;–&nbsp; NMC <b>Meningkat</b></div>
                                    </div>
                                </div>

                                <!-- Row 2 -->
                                <div style="display:flex; gap:28px; flex-wrap:wrap;">
                                    <div style="display:flex; align-items:center; gap:8px; min-width:260px;">
                                        <div style="width:18px; height:14px; background:#ffeb3b; border:1px solid #ccc;"></div>
                                        <div>Yamaha <b>Meningkat</b> &nbsp;–&nbsp; NMC <b>Menurun</b></div>
                                    </div>

                                    <div style="display:flex; align-items:center; gap:8px; min-width:260px;">
                                        <div style="width:18px; height:14px; background:#de2d26; border:1px solid #ccc;"></div>
                                        <div>Yamaha <b>Menurun</b> &nbsp;–&nbsp; NMC <b>Menurun</b></div>
                                    </div>
                                </div>

                            </div>
                        </div>
                        """
                        note_html += quadrant_html

                    st.html(note_html)

                # if st.session_state.get("display_option") == "Polreg Yamaha (%)":
                #     st.html("""
                #         <div style="
                #             background-color: #fff3cd;
                #             border-left: 6px solid #ffcc00;
                #             padding: 10px 15px;
                #             margin-bottom: 10px;
                #             border-radius: 6px;
                #             font-size: 14px;
                #             color: #4c4a00;
                #         ">
                #             <b>Catatan:</b><br>
                #             Angka unit Yamaha pada peta adalah jumlah unit yang melalui proses <i>Police Registration</i> 
                #             pada periode tahun tersebut, <b>bukan angka penjualan</b> atau <b>merepresentasikan total market</b>. Angka 
                #             tersebut merupakan hasil kumulatif dari periode yang dipilih pada filter.
                #         </div>
                #     """)
                m, colormap_prov_html, colormap_city_html, colormap_district_html = display_map(threshold=cust_ratio_threshold)
                # Note Strategi khusus untuk Polreg Yamaha(%) + NMC
                if (
                    st.session_state.get("display_option") == "Polreg Yamaha (%)"
                    and st.session_state.get("yamaha_include_nmc", False)
                ):
                    st.html("""
                        <div style="
                            background-color:#ffffff;
                            border-radius:8px;
                            padding:16px 20px;
                            margin-top:18px;
                            margin-bottom:20px;
                            box-shadow:0 2px 6px rgba(0,0,0,0.08);
                            font-size:14px;
                            color:#222;
                        ">
                            <div style="font-weight:700; margin-bottom:14px; font-size:15px;">
                                Strategi Berdasarkan Pertumbuhan Yamaha - NMC
                            </div>
                            <!-- GREEN BOX -->
                            <div style="display:flex; gap:10px; margin-bottom:10px;">
                                <div style="width:18px; height:14px; background:#66bb6a; border:1px solid #bbb;"></div>
                                <div><b>Yamaha Meningkat – NMC Meningkat</b></div>
                            </div>

                            <div style="margin-left:28px; margin-bottom:18px;">
                                <b>Insight strategis</b><br>
                                Fokus pada customer retention dan canvassing yang sudah berjalan efektif. 
                                Wilayah ini cocok dijadikan UFI Benchmark karena menunjukkan kombinasi pertumbuhan pasar.
                                <br><br>
                                <b>Arah strategi</b>
                                <ul style="margin-top:4px;">
                                    <li>Pertahankan intensitas canvassing.</li>
                                    <li>Gunakan wilayah ini sebagai rujukan best practice untuk area lain.</li>
                                    <li>Identifikasi faktor sukses, misal seperti program dealer, komunitas, promosi.</li>
                                </ul>
                            </div>
                            <!-- ORANGE BOX -->
                            <div style="display:flex; gap:10px; margin-bottom:10px;">
                                <div style="width:18px; height:14px; background:#f57c00; border:1px solid #bbb;"></div>
                                <div><b>Yamaha Menurun – NMC Meningkat</b></div>
                            </div>

                            <div style="margin-left:28px; margin-bottom:18px;">
                                <b>Insight strategis</b><br>
                                Wilayah ini masuk prioritas UFI karena NMC kuat. 
                                Dibutuhkan penguatan canvassing untuk mengembalikan awareness dan penetrasi.
                                <br><br>
                                <b>Arah strategi</b>
                                <ul style="margin-top:4px;">
                                    <li>Tingkatkan frekuensi canvassing.</li>
                                    <li>Bedah penyebab pertumbuhan NMC (leasing dominan, event lokal yang bekerja).</li>
                                    <li>Eksekusi program win-back untuk pelanggan berpotensi berpindah.</li>
                                </ul>
                            </div>


                            <!-- ====================================================== -->
                            <!-- YELLOW BOX -->
                            <!-- ====================================================== -->
                            <div style="display:flex; gap:10px; margin-bottom:10px;">
                                <div style="width:18px; height:14px; background:#ffeb3b; border:1px solid #bbb;"></div>
                                <div><b>Yamaha Meningkat – NMC Menurun</b></div>
                            </div>

                            <div style="margin-left:28px; margin-bottom:18px;">
                                <b>Insight strategis</b><br>
                                Momentum Yamaha harus diamankan dengan memperkuat sinergi dealer, 
                                karena wilayah ini menunjukkan potensi dominasi pasar.
                                <br><br>
                                <b>Arah strategi</b>
                                <ul style="margin-top:4px;">
                                    <li>Kembangkan program khusus bersama dealer.</li>
                                    <li>Dorong dealer menambah titik interaksi (roadshow, display, komunitas).</li>
                                    <li>Pastikan konversi canvassing ke booking tetap optimal.</li>
                                </ul>
                            </div>

                            <!-- ====================================================== -->
                            <!-- RED BOX -->
                            <!-- ====================================================== -->
                            <div style="display:flex; gap:10px; margin-bottom:10px;">
                                <div style="width:18px; height:14px; background:#de2d26; border:1px solid #bbb;"></div>
                                <div><b>Yamaha Menurun – NMC Menurun</b></div>
                            </div>

                            <div style="margin-left:28px;">
                                <b>Insight strategis</b><br>
                                Fokus menghidupkan kembali demand di area ini.
                                <br><br>
                                <b>Arah strategi</b>
                                <ul style="margin-top:4px;">
                                    <li>Membuat program re-activation market bersama dealer dan cabang (event lokal, bundling, promo regional).</li>
                                    <li>Evaluasi faktor lain seperti ekonomi lokal, akses dealer, isu aftersales, brand visibility).</li>
                                    <li>Perkuat aktivitas canvassing dasar (kunjungan rutin, komunitas, direct engagement).</li>
                                    <li>Identifikasi potensi demand baru.</li>
                                </ul>
                            </div>

                        </div>
                    """)
                if st.session_state.get("display_option") == "Retention Rate UFI":
                    st.html("""
                            <div style="display:flex; align-items:flex-start; gap:10px; margin-bottom:12px;">
                                <div style="min-width:36px; height:14px; margin-top:3px;
                                    background: linear-gradient(to right, #c8facc, #006400);
                                    border:1px solid #999; border-radius:2px; flex-shrink:0;"></div>
                                <div>
                                    <b style="color:#006400;">Q1 — High Growth, High RR</b><br>
                                    Growth new customer tinggi &amp; retention rate tinggi.
                                </div>
                            </div>
                            <div style="display:flex; align-items:flex-start; gap:10px; margin-bottom:12px;">
                                <div style="min-width:36px; height:14px; margin-top:3px;
                                    background: linear-gradient(to right, #fff9c4, #FFD700);
                                    border:1px solid #999; border-radius:2px; flex-shrink:0;"></div>
                                <div>
                                    <b style="color:#b8860b;">Q2 — High Growth, Low RR</b><br>
                                    Growth new customer tinggi &amp; retention rate rendah.
                                </div>
                            </div>

                            <div style="display:flex; align-items:flex-start; gap:10px; margin-bottom:12px;">
                                <div style="min-width:36px; height:14px; margin-top:3px;
                                    background: linear-gradient(to right, #cfe8ff, #1E90FF);
                                    border:1px solid #999; border-radius:2px; flex-shrink:0;"></div>
                                <div>
                                    <b style="color:#1565C0;">Q3 — Low Growth, High RR</b><br>
                                    Growth new customer rendah &amp; retention rate tinggi.
                                </div>
                            </div>

                            <div style="display:flex; align-items:flex-start; gap:10px; margin-bottom:12px;">
                                <div style="min-width:36px; height:14px; margin-top:3px;
                                    background: linear-gradient(to right, #f8c8c8, #B22222);
                                    border:1px solid #999; border-radius:2px; flex-shrink:0;"></div>
                                <div>
                                    <b style="color:#B22222;">Q4 — Low Growth, Low RR</b><br>
                                    Growth new customer rendah &amp; retention rate rendah.
                                </div>
                            </div>
                            </div>
                        </div>
                    """)

                # # Initialize session state variables
                # if "clicked_lat" not in st.session_state:
                #     st.session_state.clicked_lat = None
                # if "clicked_lng" not in st.session_state:
                #     st.session_state.clicked_lng = None

                # # Add this where you want to display the coordinates in your UI
                # if "clicked_lat" in st.session_state and "clicked_lng" in st.session_state:
                #     st.write(f"Clicked coordinates: {st.session_state.clicked_lat:.6f}, {st.session_state.clicked_lng:.6f}")

            markers, btn = st.columns([4, 1], vertical_alignment="bottom")
            
            with markers:
                tab1, tab2 = st.tabs(["FIFGROUP", "Kompetitor"])
                with tab1:
                    option_map = {
                        0: f"![Cabang](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/952a3bcfda2c2b4eb0cf9566248a500bcbaaa5da/icon/cabang2.png) Cabang ({st.session_state.location_counts['cabang']:,})",
                        1: f"![Pos](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/952a3bcfda2c2b4eb0cf9566248a500bcbaaa5da/icon/pos2.png) Pos ({st.session_state.location_counts['pos']:,})",
                        2: f"![Dealer](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/952a3bcfda2c2b4eb0cf9566248a500bcbaaa5da/icon/dealer2.png) Dealer ({st.session_state.location_counts['dealer']:,})",
                        3: f"![Pos Dealer](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/952a3bcfda2c2b4eb0cf9566248a500bcbaaa5da/icon/posdealer2.png) Pos Dealer ({st.session_state.location_counts['pos_dealer']:,})"
                    }

                    default_selection = list(st.session_state.selected_marker_keys)

                    selection = st.segmented_control(
                        "Lokasi",
                        options=option_map.keys(),
                        format_func=lambda option: option_map[option],
                        selection_mode="multi",
                        label_visibility="collapsed",
                        key="marker_value",
                        on_change=change_marker,
                        default=default_selection
                    )
                
                # with tab2:
                #     _level_map = {"Cabang": "COMPETITOR CABANG", "POS": "COMPETITOR POS"}
                #     picked_level = st.segmented_control("Jenis Kompetitor", options=["Cabang", "POS"], key="competitor_level", label_visibility="collapsed")
                #     option_map2 = {
                #         0: f"![Adira](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/adira.png) Adira ({st.session_state.location_counts['adira']:,})",                        
                #         1: f"![OTO](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/oto.png) OTO ({st.session_state.location_counts['oto']:,})",
                #         2: f"![BFI](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/bfi.png) BFI ({st.session_state.location_counts['bfi']:,})",
                #         3: f"![Mega](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/mega.png) Mega ({st.session_state.location_counts['mega']:,})",
                #         4: f"![Mandala](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/mandala.png) Mandala ({st.session_state.location_counts['mandala']:,})",
                #         5: f"![hci](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/hci.png) HCI ({st.session_state.location_counts['hci']:,})",
                #         6: f"![bca](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/bca.png) BCA FINANCE ({st.session_state.location_counts['bca']:,})",
                #         7: f"![kb](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/kb.png) KB ({st.session_state.location_counts['kb']:,})",
                #         8: f"![aeon](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/aeon.png) AEON ({st.session_state.location_counts['aeon']:,})",
                #         9: f"![Others](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/others.png) Others ({st.session_state.location_counts['others']:,})",
                #     } 

                #     default_selection2 = list(st.session_state.selected_marker2_keys)

                #     selection2 = st.segmented_control(
                #         "Lokasi",
                #         options=option_map2.keys(),
                #         format_func=lambda option: option_map2[option],
                #         selection_mode="multi",
                #         label_visibility="collapsed",
                #         key="marker_value2",
                #         on_change=change_marker2,
                #         default=default_selection2
                #     )

                with tab2:
                    _level_map = {"Cabang": "COMPETITOR CABANG", "POS": "COMPETITOR POS"}
                    picked_level = st.segmented_control("Jenis Kompetitor", options=["Cabang", "POS"], key="competitor_level", label_visibility="collapsed") or "Cabang"
                    
                    current_category = _level_map[picked_level]
                    st.session_state.competitor_category = current_category

                    comp_counts_all = st.session_state.get("location_counts_comp", {})
                    counts = comp_counts_all.get(current_category, {"adira":0,"oto":0,"bfi":0,"mega":0,"mandala":0,"hci":0,"bca finance":0,"kb":0,"aeon":0,"others":0
                                                                    })

                    option_map2 = {
                        0: f"![Adira](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/adira.png) Adira ({counts['adira']:,})",                        
                        1: f"![OTO](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/oto.png) OTO ({counts['oto']:,})",
                        2: f"![BFI](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/bfi.png) BFI ({counts['bfi']:,})",
                        3: f"![Mega](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/mega.png) Mega ({counts['mega']:,})",
                        4: f"![Mandala](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/mandala.png) Mandala ({counts['mandala']:,})",
                        5: f"![hci](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/hci.png) HCI ({counts['hci']:,})",
                        6: f"![bca](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/bca.png) BCA FINANCE ({counts['bca']:,})",
                        7: f"![kb](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/kb.png) KB ({counts['kb']:,})",
                        8: f"![aeon](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/aeon.png) AEON ({counts['aeon']:,})",
                        9: f"![Others](https://raw.githubusercontent.com/valeryongso22/Dashboard-FIFGROUP/main/icon/others.png) Others ({counts['others']:,})",
                    } 

                    default_selection2 = list(st.session_state.selected_marker2_keys)

                    selection2 = st.segmented_control(
                        "Lokasi",
                        options=option_map2.keys(),
                        format_func=lambda option: option_map2[option],
                        selection_mode="multi",
                        label_visibility="collapsed",
                        key="marker_value2",
                        on_change=change_marker2,
                        default=default_selection2
                    )

            with btn:
                with st.container(key="container_customer_growth_map_colormap"):
                    if st.session_state.clicked_district and colormap_district_html:
                        st.html(colormap_district_html)
                    elif st.session_state.clicked_city and colormap_district_html:
                        st.html(colormap_district_html)
                    elif st.session_state.clicked_province and colormap_city_html:
                        st.html(colormap_city_html)
                    elif colormap_prov_html:
                        st.html(colormap_prov_html)

                    btn_props = get_back_button_props()
                    st.button(
                        btn_props["label"],
                        disabled=btn_props["disabled"],
                        use_container_width=True,
                        on_click=btn_props["on_click"],
                        type="primary",
                        icon="↩",
                        help=btn_props["help"]
                    )

    # Booking Growth Metrics
    with col2:
        # Check if we should hide tables (Yamaha mode)
        display_option_now = st.session_state.get("display_option", st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)"))
        is_yamaha_mode = (display_option_now == "Polreg Yamaha (%)")
        is_npl_mode = (display_option_now == "NPL")
        # ==== FORCE HIDE ALL DATAFRAME / TABLE OUTPUTS FOR YAMAHA MODE ====
        if is_yamaha_mode or is_npl_mode:
            def _blocked(*args, **kwargs):
                return None

            st.dataframe = _blocked
            st.table     = _blocked
            st.write     = (lambda *args, **kwargs: None)   # careful: hides all writes

            # If you still need normal writes (text):
            def write_safe(x):
                if not hasattr(x, "geometry"):
                    st.text(str(x))
            st.write_safe = write_safe
        
        # hanya tampilkan booking growth jika bukan Polreg Yamaha (%)
        if is_yamaha_mode or (st.session_state.get("hide_tables", False) and display_option_now == "NPL"):
            agg_vals_book = {}
            st.empty()
        else:
            with st.container(key="container_booking_growth"):
                with st.container(key="container_booking_growth_title"):
                    col1 = st.columns(1)
                    with col1[0]:
                        st.html(
                            f'''  
                            <div style="font-size: 18px; font-weight: bold; color: #0458af;">Pertumbuhan Booking {update_buss_unit_title()}</div>  
                            '''
                        )

                business_units = [
                    {"key": "NMC", "logo": "https://images.seeklogo.com/logo-png/56/2/fifastra-fif-group-logo-png_seeklogo-568347.png?v=1957804521000083520"},
                    {"key": "MPF", "logo": "https://images.seeklogo.com/logo-png/56/1/spektra-fif-group-logo-png_seeklogo-568351.png?v=1957832117710626200"},
                    {"key": "REFI", "logo": "https://images.seeklogo.com/logo-png/56/1/danastra-fifgroup-logo-png_seeklogo-568382.png?v=1957832698430771696"},
                    {"key": "MMU", "logo": "https://images.seeklogo.com/logo-png/56/1/amitra-fifgroup-logo-png_seeklogo-568381.png?v=1957802152858011120"},
                    {"key": "OTHERS", "logo": "", "others": True}
                ]

                with st.container(key="container_booking_growth_metrics"):
                    for i, unit in enumerate(business_units, start=1):
                        with st.container(key=f"container_booking_growth_metrics_{i}"):
                            col1 = st.columns(1)
                            with col1[0]:
                                # pastikan agg_vals_book dan start_quarter_clicked / end_quarter_clicked tersedia di scope
                                st.html(
                                    create_metric_html(
                                        agg_vals_book[f"{start_quarter_clicked}_{unit['key']}"],
                                        agg_vals_book[f"{end_quarter_clicked}_{unit['key']}"],
                                        unit.get("logo", ""),
                                        others=unit.get("others", False)
                                    )
                                )

    # Customer Growth Trend Line Chart
    with st.container(key="container_customer_growth_trend"):
        # Check if we should hide tables (Yamaha mode)
        display_option_now = st.session_state.get("display_option", st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)"))
        is_yamaha_mode = (display_option_now == "Polreg Yamaha (%)")
        # ==== FORCE HIDE ALL DATAFRAME / TABLE OUTPUTS FOR YAMAHA MODE ====
        if is_yamaha_mode:
            def _blocked(*args, **kwargs):
                return None

            st.dataframe = _blocked
            st.table     = _blocked
            st.write     = (lambda *args, **kwargs: None)   # careful: hides all writes

            # If you still need normal writes (text):
            def write_safe(x):
                if not hasattr(x, "geometry"):
                    st.text(str(x))
            st.write_safe = write_safe
        
        if st.session_state.get("hide_tables", False) or is_yamaha_mode:
            # Skip entirely for Yamaha mode - don't render anything in this section
            pass
        else:
            col1 = st.columns(1)
            with col1[0]:
                title_text = f"Tren {display_option} {update_buss_unit_title()}"
            
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
                quarters = ["2019"] + [f"{year}Q{q}" for year in range(2020, 2027) for q in range(1, 5)]
                quarters = quarters[:quarters.index("2026Q1") + 1]
                # build altair_data defensively (gunakan agg_vals yang dibuat di atas)
                altair_data = pd.DataFrame({
                    "Quarter": quarters,
                    "Growth": [np.nan] + [ (agg_vals.get(f"{q}_CUST_NO", 0) - agg_vals.get(f"{quarters[i]}_CUST_NO", 0)) / agg_vals.get(f"{quarters[i]}_CUST_NO", np.nan) if agg_vals.get(f"{quarters[i]}_CUST_NO", 0) != 0 else np.nan for i, q in enumerate(quarters[1:])],
                    "Growth_Number": [np.nan] + [ agg_vals.get(f"{q}_CUST_NO", 0) - agg_vals.get(f"{quarters[i]}_CUST_NO", 0) for i, q in enumerate(quarters[1:])],
                    "Growth_Number_All": [np.nan] + [ agg_vals.get(f"{q}_CUST_NO_TOTAL", 0) - agg_vals.get(f"{quarters[i]}_CUST_NO_TOTAL", 0) for i, q in enumerate(quarters[1:])],
                    "Prod_Age_Ratio": [ (agg_vals.get(f"{q}_CUST_NO", 0) / agg_vals.get("Usia Produktif", 1)) if agg_vals.get("Usia Produktif", 0) != 0 else 0 for q in quarters],
                    "Current_Cust": [ agg_vals.get(f"{q}_CUST_NO", 0) for q in quarters],
                    "Previous_Cust": [np.nan] + [ agg_vals.get(f"{quarters[i]}_CUST_NO", np.nan) for i in range(len(quarters) - 1)]
                })
                # hindari pembagian oleh nol / NaN
                altair_data["Cust_Ratio"] = altair_data["Growth_Number"] / altair_data["Growth_Number_All"].replace({0: np.nan})

                altair_data = altair_data[
                    (altair_data["Quarter"] >= start_quarter_clicked) & 
                    (altair_data["Quarter"] <= end_quarter_clicked)
                ]
                filtered_data = altair_data[altair_data["Quarter"] != ""].dropna(how="all")

                if display_option == "Pertumbuhan Customer (%)":
                    metric_for_line = "Growth"
                    y_title_line = "Pertumbuhan Customer (%)"
                    y_format_line = "%"
                    max_quarter = filtered_data["Growth"].idxmax() if (not filtered_data.empty and "Growth" in filtered_data) else None
                    max_quarter = filtered_data.loc[max_quarter, "Quarter"] if max_quarter is not None else None
                elif display_option == "Pertumbuhan Customer":
                    metric_for_line = "Growth_Number"
                    y_title_line = "Pertumbuhan Customer"
                    y_format_line = "~s"
                    max_quarter = filtered_data["Growth_Number"].idxmax() if (not filtered_data.empty and "Growth_Number" in filtered_data) else None
                    max_quarter = filtered_data.loc[max_quarter, "Quarter"] if max_quarter is not None else None
                elif display_option == "Rasio Customer dan Usia Produktif 2024 (%)":
                    metric_for_line = "Prod_Age_Ratio"
                    y_title_line = "Rasio Customer dan Usia Produktif 2024 (%)"
                    y_format_line = "%"
                    max_quarter = filtered_data["Prod_Age_Ratio"].idxmax() if (not filtered_data.empty and "Prod_Age_Ratio" in filtered_data) else None
                    max_quarter = filtered_data.loc[max_quarter, "Quarter"] if max_quarter is not None else None
                else:
                    metric_for_line = "Cust_Ratio"
                    y_title_line = "Rasio Pertumbuhan Cust. (> 1x) dan Total Cust. (%)"
                    y_format_line = "%"
                    max_quarter = filtered_data["Cust_Ratio"].idxmax() if (not filtered_data.empty and "Cust_Ratio" in filtered_data) else None
                    max_quarter = filtered_data.loc[max_quarter, "Quarter"] if max_quarter is not None else None

                altair_data["Highlight"] = altair_data["Quarter"] == max_quarter

                # bar + line + points + labels (sama seperti sebelumnya)
                bar_chart = alt.Chart(altair_data).mark_bar(
                    cornerRadiusTopLeft=8,
                    cornerRadiusTopRight=8,
                    opacity=0.7
                ).encode(
                    x=alt.X("Quarter:N", title=None, axis=alt.Axis(labelAngle=0, labelOverlap=False, tickCount=len(altair_data))),
                    y=alt.Y("Current_Cust:Q", title="Jumlah Customer", axis=alt.Axis(grid=False, format="~s"), scale=alt.Scale(zero=True)),
                    color=alt.condition("datum.Highlight == true", alt.value("#023E8A"), alt.value("#41b6c4")),
                    tooltip=[
                        alt.Tooltip("Quarter:N", title="Quarter"),
                        alt.Tooltip("Current_Cust:Q", title="Jumlah Kumulatif Customer", format=",d"),
                        alt.Tooltip("Growth_Number:Q", title="Pertumbuhan Customer", format=",d"),
                        alt.Tooltip("Growth:Q", title="Pertumbuhan Customer (%)", format=".2%"),
                        alt.Tooltip("Prod_Age_Ratio:Q", title="Rasio Customer dan Usia Produktif (%)", format=".2%")
                    ]
                )

                line_base = alt.Chart(altair_data).mark_line(color="#0458af", strokeWidth=3).encode(
                    x=alt.X("Quarter:N", title=None, axis=alt.Axis(labelAngle=0, labelOverlap=False, tickCount=len(altair_data))),
                    y=alt.Y(f"{metric_for_line}:Q", title=y_title_line, axis=alt.Axis(grid=False, format=y_format_line), scale=alt.Scale(zero=True))
                )

                points = alt.Chart(altair_data).mark_circle(size=100).encode(
                    x="Quarter:N",
                    y=f"{metric_for_line}:Q",
                    color=alt.condition("datum.Highlight == true", alt.value("#023E8A"), alt.value("#0458af")),
                    tooltip=[
                        alt.Tooltip("Quarter:N", title="Quarter"),
                        alt.Tooltip("Current_Cust:Q", title="Jumlah Kumulatif Customer", format=",d"),
                        alt.Tooltip("Growth_Number:Q", title="Pertumbuhan Customer", format=",d"),
                        alt.Tooltip("Growth:Q", title="Pertumbuhan Customer (%)", format=".2%"),
                        alt.Tooltip("Prod_Age_Ratio:Q", title="Rasio Customer dan Usia Produktif 2024 (%)", format=".2%")
                    ]
                )

                text = alt.Chart(altair_data).mark_text(align="center", baseline="middle", dy=-15, fontSize=16, color="#0458af").encode(
                    x="Quarter:N",
                    y=f"{metric_for_line}:Q",
                    text=alt.Text(f"{metric_for_line}:Q", format=",.0f" if metric_for_line == "Growth_Number" else ".2%"),
                )

                line_chart = line_base + points + text
                combo_chart = alt.layer(bar_chart, line_chart).resolve_scale(y="independent").properties(height=270, background="transparent").configure_axis(labelFontSize=12, titleFontSize=14).configure_title(fontSize=16, anchor="middle")
                st.altair_chart(combo_chart, use_container_width=True)

                st.html(
                    f"""
                    <div style="display: flex; justify-content: center; align-items: center; margin-top: -20px; gap: 30px;">
                        <div style="display: flex; align-items: center;">
                            <div style="width: 12px; height: 12px; background-color: #41b6c4; margin-right: 5px;"></div>
                            <span style="font-size: 14px;">Jumlah Kumulatif Customer</span>
                        </div>
                        <div style="display: flex; align-items: center;">
                            <div style="width: 20px; height: 3px; background-color: #0458af; margin-right: 5px;"></div>
                            <span style="font-size: 14px;">{display_option}</span>
                        </div>
                    </div>
                    """
                )

                with st.expander("Lihat Tren Berdasarkan Wilayah"):
                    # Double-check we're not in Yamaha mode (should already be handled above, but just in case)
                    is_yamaha_mode_inner = st.session_state.get("display_option", st.session_state.get("selected_sorter", "")) == "Polreg Yamaha (%)"
                    if is_yamaha_mode_inner:
                        st.info("Mode Polreg Yamaha (%) aktif — tren wilayah tidak ditampilkan.")
                    else:
                        top_n_slider = st.slider("Pilih Top N:", min_value=1, max_value=50, value=5, help="Geser slider ini untuk melihat top N", key="trend_top_n")

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

                        # prepare combined columns for naming
                        if "WADMKK" in df_kab.columns and "WADMPR" in df_kab.columns:
                            df_kab["combined"] = df_kab["WADMKK"].astype(str) + ", " + df_kab["WADMPR"].astype(str)
                        if "WADMKC" in df_kec.columns and "WADMKK" in df_kec.columns and "WADMPR" in df_kec.columns:
                            df_kec["combined"] = df_kec["WADMKC"].astype(str) + ", " + df_kec["WADMKK"].astype(str) + ", " + df_kec["WADMPR"].astype(str)

                        pulau_html = generate_trend_html(df_pulau, "PULAU", column_suffix, start_quarter_clicked, end_quarter_clicked, top_n_slider, "Tren Top Pulau", show_all=True)
                        prov_html = generate_trend_html(df_prov, "WADMPR", column_suffix, start_quarter_clicked, end_quarter_clicked, top_n_slider, f"Tren Top {top_n_slider} Provinsi")
                        kab_html = generate_trend_html(df_kab, "combined", column_suffix, start_quarter_clicked, end_quarter_clicked, top_n_slider, f"Tren Top {top_n_slider} Kabupaten/Kota")
                        kec_html = generate_trend_html(df_kec, "combined", column_suffix, start_quarter_clicked, end_quarter_clicked, top_n_slider, f"Tren Top {top_n_slider} Kecamatan")

                        st.html(
                            """
                            <style>
                            .trend-table { overflow-x: auto; margin-bottom: 16px; }
                            @media screen and (max-width: 768px) {
                            .trend-table table { font-size: 11px; }
                            .trend-table th, .trend-table td { padding: 3px !important; }
                            }
                            </style>
                            """
                        )

                        st.html(pulau_html)
                        st.html(prov_html)
                        st.html(kab_html)
                        st.html(kec_html)

                # st.html(
                #     """
                #     <style>
                #         .trend-table {
                #             overflow-x: auto;
                #             margin-bottom: 16px;
                #         }
                #         @media screen and (max-width: 768px) {
                #             .trend-table table {
                #                 font-size: 11px;
                #             }
                #             .trend-table th, .trend-table td {
                #                 padding: 3px !important;
                #             }
                #         }
                #     </style>
                #     """
                # )
                
                # st.html(pulau_html)
                # st.html(prov_html)
                # st.html(kab_html)
                # st.html(kec_html)

# Customer Growth Prediction
with st.container(key="container_customer_growth_prediction"):
    # Check if we should hide tables (Yamaha mode)
    display_option_now = st.session_state.get("display_option", st.session_state.get("selected_sorter", "Pertumbuhan Customer (%)"))
    is_yamaha_mode = (display_option_now == "Polreg Yamaha (%)")
    # ==== FORCE HIDE ALL DATAFRAME / TABLE OUTPUTS FOR YAMAHA MODE ====
    if is_yamaha_mode:
        def _blocked(*args, **kwargs):
            return None

        st.dataframe = _blocked
        st.table     = _blocked
        st.write     = (lambda *args, **kwargs: None)   # careful: hides all writes

        # If you still need normal writes (text):
        def write_safe(x):
            if not hasattr(x, "geometry"):
                st.text(str(x))
        st.write_safe = write_safe

    # Jangan tampilkan prediksi jika Polreg Yamaha (%) sedang aktif
    if st.session_state.get("hide_tables", False) or is_yamaha_mode:
        # Skip entirely for Yamaha mode - don't render anything in this section
        pass
    else:
        col2 = st.columns(2)
        # gunakan kolom col1[0] yang sudah ada di scope (kolom atas)
        with col1[0]:
            title_text = f"Prediksi Jumlah Customer di Periode Mendatang"

            st.html(
                f'''
                <div style="font-size: 18px; font-weight: bold; color: #0458af;">{title_text}</div>
                '''
            )

            st.html(
                """
                <div style="background-color: #e7f3fe; border-left: 6px solid #2196F3; padding: 10px 15px; font-size: 15px; line-height: 1.5;">
                    Prediksi dilakukan berdasarkan jumlah aktual terakhir dan pertumbuhan masing-masing wilayah.
                </div>
                """
            )

            n_pred_quarter = st.slider("Jumlah Quarter yang Ingin Diprediksi", 1, 50, 4, key="pred_quarter_slider")

            def generate_quarter_names(start_year=2025, start_q=3, n=50):
                quarters = []
                year, q = start_year, start_q
                for _ in range(n):
                    quarters.append(f"{year}Q{q}_PRED")
                    q += 1
                    if q > 4:
                        q = 1
                        year += 1
                return quarters

            def predict_future_growth(df, end_quarter="2026Q1", pred_quarters=None):
                df = df.copy()

                cust_col = f"{end_quarter}_CUST_NO"
                growth_col = f"{end_quarter}_GROWTH"

                if cust_col not in df.columns or growth_col not in df.columns:
                    return df

                actual = df[cust_col].fillna(0)
                growth = df[growth_col].fillna(0).round(2) / 100
                pred = actual.copy()

                for col in pred_quarters:
                    pred = pred * (1 + growth)
                    df[col] = pred.copy()

                return df

            pred_quarters = generate_quarter_names(n=n_pred_quarter)
            df_pulau = predict_future_growth(df_pulau, end_quarter=end_quarter_clicked, pred_quarters=pred_quarters)
            df_prov = predict_future_growth(df_prov, end_quarter=end_quarter_clicked, pred_quarters=pred_quarters)
            df_kab = predict_future_growth(df_kab, end_quarter=end_quarter_clicked, pred_quarters=pred_quarters)
            df_kec = predict_future_growth(df_kec, end_quarter=end_quarter_clicked, pred_quarters=pred_quarters)

            with st.expander("Lihat Prediksi Berdasarkan Wilayah"):
                # Double-check we're not in Yamaha mode (should already be handled above, but just in case)
                is_yamaha_mode_inner = st.session_state.get("display_option", st.session_state.get("selected_sorter", "")) == "Polreg Yamaha (%)"
                
                if is_yamaha_mode_inner:
                    st.info("Mode Polreg Yamaha (%) aktif — prediksi wilayah tidak ditampilkan.")
                else:
                    top_n_pred = st.slider("Pilih Top N Wilayah untuk Prediksi", 1, 50, 5, key="pred_top_n_slider")
                    format_func = lambda x: f"{x:,.2f}" if pd.notnull(x) else "-"

                    # prepare combined columns for naming
                    if "WADMKK" in df_kab.columns and "WADMPR" in df_kab.columns:
                        df_kab["combined"] = df_kab["WADMKK"].astype(str) + ", " + df_kab["WADMPR"].astype(str)
                    if "WADMKC" in df_kec.columns and "WADMKK" in df_kec.columns and "WADMPR" in df_kec.columns:
                        df_kec["combined"] = df_kec["WADMKC"].astype(str) + ", " + df_kec["WADMKK"].astype(str) + ", " + df_kec["WADMPR"].astype(str)

                    pulau_pred_html = generate_prediction_html(df_pulau, region_col="PULAU", start_year=2026, n_quarter=n_pred_quarter, top_n=top_n_pred, title="Prediksi Top Pulau", show_all=True, format_func=format_func)
                    prov_pred_html = generate_prediction_html(df_prov, region_col="WADMPR", start_year=2026, n_quarter=n_pred_quarter, top_n=top_n_pred, title=f"Prediksi Top {top_n_pred} Provinsi", format_func=format_func)
                    kab_pred_html = generate_prediction_html(df_kab, region_col="combined", start_year=2026, n_quarter=n_pred_quarter, top_n=top_n_pred, title=f"Prediksi Top {top_n_pred} Kabupaten/Kota", format_func=format_func)
                    kec_pred_html = generate_prediction_html(df_kec, region_col="combined", start_year=2026, n_quarter=n_pred_quarter, top_n=top_n_pred, title=f"Prediksi Top {top_n_pred} Kecamatan", format_func=format_func)

                    st.html(
                        """
                        <style>
                            .trend-table { overflow-x: auto; margin-bottom: 16px; }
                            @media screen and (max-width: 768px) {
                                .trend-table table { font-size: 11px; }
                                .trend-table th, .trend-table td { padding: 3px !important; }
                            }
                        </style>
                        """
                    )

                    # Display the prediction tables
                    st.html(pulau_pred_html)
                    st.html(prov_pred_html)
                    st.html(kab_pred_html)
                    st.html(kec_pred_html)