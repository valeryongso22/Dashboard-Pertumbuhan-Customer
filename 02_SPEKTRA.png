
# ----------------------------------------------------------------- Setup -----------------------------------------------------------------

# Libraries
import pathlib
import streamlit as st
import pandas as pd

from datetime import datetime

# Page Config
st.set_page_config(    
    page_title="Dashboard Pertumbuhan Customer",    
    page_icon="Logo/FIFGROUP_KOTAK.png",
    initial_sidebar_state="collapsed" 
)    

# Custom CSS
st.html(      
    """      
    <style>    
        .stMainBlockContainer {      
            max-width: 80rem;      
        }      
        .block-container {      
            padding-top: 4rem;      
            padding-bottom: 4rem;      
        }

        /* Custom Card Design */
        .custom-card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 12px;
            border-left: 6px solid #0458af;
            box-shadow: 0px 0px 20px 0px rgba(128, 128, 128, 0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .custom-card:hover {
            transform: translateY(-2px);
            box-shadow: 0px 0px 20px 0px rgba(4, 88, 175, 0.4);
        }

        .custom-card h3 {
            color: #0458af;
            margin: 0 0 10px 0;
            font-size: 20px;
            font-weight: 600;
        }

        .custom-card p {
            margin: 0;
            font-size: 14px;
            color: #4c5773;
        }

        .custom-card .growth-indicator {
            font-size: 16px;
            font-weight: bold;
        }

        .custom-card .growth-positive {
            color: #28a745;
        }

        .custom-card .growth-negative {
            color: #dc3545;
        }

        .custom-card .growth-neutral {
            color: #4c5773;
        }

        .custom-card .metric-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
        }

        .custom-card .metric-label {
            font-size: 14px;
            color: #4c5773;
        }

        .custom-card .metric-value {
            font-size: 16px;
            font-weight: 500;
            color: #2c3858;
        }

        .custom-card .business-unit-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }

        .custom-card .business-unit-metrics div {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            transition: border 0.2s;
            border: 2px solid transparent;
        }

        .custom-card .business-unit-metrics div:hover {
            border: 2px solid rgba(4, 88, 175, 0.4);
        }

        .custom-card .business-unit-metrics div p {
            margin: 0;
            font-size: 13px;
        }

        .custom-card .business-unit-metrics div .growth-indicator {
            font-size: 14px;
        }
    </style>      
    """      
)

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

    for i, quarter in enumerate(quarters):
        col_name = f"{quarter}_{suffix}"
        if col_name not in df.columns:
            continue

        if i == 0:
            out_df[f"{quarter}_CUST_NO"] = df[col_name]
        else:
            prev_quarter = quarters[i-1]
            prev_col_name = f"{prev_quarter}_{suffix}"
            
            if prev_col_name not in df.columns:
                continue
            
            out_df[f"{quarter}_CUST_NO"] = df[col_name]
            
            growth = ((df[col_name] - df[prev_col_name]) / df[prev_col_name]) * 100
            growth = growth.replace([float("inf"), -float("inf")], 0).fillna(0)
            out_df[f"{quarter}_GROWTH"] = growth
            
            growth_number = (df[col_name] - df[prev_col_name])
            growth_number = growth_number.replace([float("inf"), -float("inf")], 0).fillna(0)
            out_df[f"{quarter}_GROWTH_NUMBER"] = growth_number

            out_df["Usia Produktif"] = out_df["Usia Produktif"].replace([float("inf"), -float("inf")], 0).fillna(0)

    selected_quarter = st.session_state.get("selected_quarter", ("2019", "2024Q4"))
    first_q, last_q = selected_quarter
    first_cust_col = f"{first_q}_CUST_NO"
    last_cust_col  = f"{last_q}_CUST_NO"

    first_cust = out_df[first_cust_col].fillna(0).replace([float("inf"), -float("inf")], 0)
    last_cust  = out_df[last_cust_col].fillna(0).replace([float("inf"), -float("inf")], 0)
    prod_age = out_df["Usia Produktif"].fillna(0).replace([float("inf"), -float("inf")], 0)
    
    map_growth = ((last_cust - first_cust) / first_cust) * 100
    map_growth = map_growth.replace([float("inf"), -float("inf")], 0).fillna(0)
    
    map_growth_number = last_cust - first_cust
    map_growth_number = map_growth_number.replace([float("inf"), -float("inf")], 0).fillna(0)

    map_prod_age_ratio = last_cust / prod_age * 100
    map_prod_age_ratio = map_prod_age_ratio.replace([float("inf"), -float("inf")], 0).fillna(0)
    
    out_df["MAP_GROWTH"] = map_growth
    out_df["MAP_GROWTH_NUMBER"] = map_growth_number
    out_df["MAP_PROD_AGE_RATIO"] = map_prod_age_ratio
    
    return out_df

def calculate_growth(df):
    selected_buss_unit = st.session_state.get("selected_buss_unit", "ALL")

    if selected_buss_unit == "ALL":
        suffix = "TOTAL"
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

    processed_df = process_df(df, suffix, quarters)

    return processed_df

# Preprocess Booking Data
def process_df_booking(data):
    selected_quarter = st.session_state.get("selected_quarter", ("2019", "2024Q4"))
    selected_buss_unit = st.session_state.get("selected_buss_unit", "ALL")

    df = data.copy()
    df.columns = ["_".join(col) if isinstance(col, tuple) else str(col) for col in df.columns]
    
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
    
    join_keys = ["PULAU", "WADMKC", "WADMKK", "WADMPR"]
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
    df = pd.read_parquet("Data Fix/Data Customer AGG_v4.parquet")
    df_book = pd.read_parquet("Data Fix/Data Booking AGG_v4.parquet").reset_index(0).reset_index()
    df_book.columns = ["_".join(map(str, col)).strip("_") for col in df_book.columns.values]

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

    df["PULAU"] = df["WADMPR"].map(provinsi_ke_pulau)
    df_book["PULAU"] = df_book["WADMPR"].map(provinsi_ke_pulau)
    
    return df, df_book

df, df_book = preparing_data()

# Preprocess Aggregated Data
def calculate_growth_and_unit(current_value, previous_value):
    if previous_value == 0:
        growth = 0
        growth_unit = 0
    else:
        growth = ((current_value - previous_value) / previous_value) * 100
        growth_unit = current_value - previous_value

    if pd.isna(growth) or growth == float("inf") or growth == float("-inf"):
        growth = 0
    if pd.isna(growth_unit) or growth_unit == float("inf") or growth_unit == float("-inf"):
        growth_unit = 0

    return growth, growth_unit

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
            Summary Pertumbuhan Customer FIFGROUP    
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
            color: #31333F;    
            margin: 0;    
            text-align: right;    
        ">    
            Data last updated: {formatted_time}    
        </p>    
        """    
    )    

st.write("")

# First Filter
def update_filter():
    st.session_state.selected_quarter = st.session_state.quarter
    st.session_state.selected_buss_unit = st.session_state.buss_unit
    st.session_state.selected_level = st.session_state.level

quarter_options = [
    "2019",
    "2020Q1", "2020Q2", "2020Q3", "2020Q4",
    "2021Q1", "2021Q2", "2021Q3", "2021Q4",
    "2022Q1", "2022Q2", "2022Q3", "2022Q4",
    "2023Q1", "2023Q2", "2023Q3", "2023Q4",
    "2024Q1", "2024Q2", "2024Q3", "2024Q4"
]

buss_unit_options = [
    "ALL",
    "NMC", "NMC (> 1x)", "NMC to REFI", "NMC to MPF",
    "REFI", "REFI (> 1x)", "REFI to NMC", "REFI to MPF",
    "MPF", "MPF (> 1x)", "MPF to NMC", "MPF to REFI",
]

level_options = ["Nasional", "Pulau", "Top N Provinsi", "Top N Kabupaten/Kota", "Top N Kecamatan"]

col1, col2, col3 = st.columns(3)
with col1:
    quarter = st.select_slider(
        label="Pilih range waktu:",
        options=quarter_options,
        value=("2019", "2024Q4"),
        key="quarter",
        on_change=update_filter
    )

default_buss_unit = st.session_state.get("selected_buss_unit", "ALL")
if default_buss_unit in buss_unit_options:
    default_index = buss_unit_options.index(default_buss_unit)
else:
    default_index = 0

with col2:
    buss_unit = st.selectbox(
        label="Pilih business unit:",
        options=buss_unit_options,
        index=default_index,
        key="buss_unit",
        on_change=update_filter
    )

default_level = st.session_state.get("selected_level", "Nasional")
if default_level in level_options:
    default_index = level_options.index(default_level)
else:
    default_index = 0

with col3:
    selection = st.selectbox(
        label="Pilih level:",
        options=level_options,
        index=default_index,
        key="level",
        on_change=update_filter
    )

# Second Filter
if "sort_by_percentage" not in st.session_state:
    st.session_state.sort_by_percentage = True

def update_sort_preference():
    st.session_state.sort_by_percentage = not st.session_state.sort_by_percentage

if st.session_state.get("selected_level", "Nasional") == "Nasional":
    title = "Nasional"
    grouped_col = None
elif st.session_state.get("selected_level", "Nasional") == "Pulau":
    title = "Pulau"
    grouped_col = "PULAU"   

    sort_option = st.pills(
        "Urutkan Berdasarkan",
        ["Pertumbuhan Customer (%)", "Pertumbuhan Customer", f"Rasio Customer As of {quarter[1]} terhadap Usia Produktif"],
        default="Pertumbuhan Customer (%)"
    )
    
    if sort_option == "Pertumbuhan Customer (%)":
        sort_column = "MAP_GROWTH"
    elif sort_option == "Pertumbuhan Customer":
        sort_column = "MAP_GROWTH_NUMBER"
    else:
        sort_column = "MAP_PROD_AGE_RATIO"
elif st.session_state.get("selected_level", "Nasional") == "Top N Provinsi":
    title = "Provinsi"
    grouped_col = "WADMPR"

    col1, col2 = st.columns([1.5, 1], vertical_alignment="center")
    with col1:
        sort_option = st.pills(
            "Urutkan Berdasarkan",
            ["Pertumbuhan Customer (%)", "Pertumbuhan Customer", f"Rasio Customer As of {quarter[1]} terhadap Usia Produktif"],
            default="Pertumbuhan Customer (%)"
        )
        
        if sort_option == "Pertumbuhan Customer (%)":
            sort_column = "MAP_GROWTH"
        elif sort_option == "Pertumbuhan Customer":
            sort_column = "MAP_GROWTH_NUMBER"
        else:
            sort_column = "MAP_PROD_AGE_RATIO"

    with col2:
        top_n = st.slider(
            "Pilih Jumlah Provinsi",
            min_value=1, 
            max_value=min(len(df["WADMPR"].unique()), 50),
            value=5
        )
elif st.session_state.get("selected_level", "Nasional") == "Top N Kabupaten/Kota":
    title = "Kabupaten/Kota"
    grouped_col = "WADMKK"
    df["WADMKK"] = df["WADMKK"] + ", " + df["WADMPR"]
    df_book["WADMKK"] = df_book["WADMKK"] + ", " + df_book["WADMPR"]

    col1, col2 = st.columns([1.5, 1], vertical_alignment="center")
    with col1:
        sort_option = st.pills(
            "Urutkan Berdasarkan",
            ["Pertumbuhan Customer (%)", "Pertumbuhan Customer", f"Rasio Customer As of {quarter[1]} terhadap Usia Produktif"],
            default="Pertumbuhan Customer (%)"
        )
        
        if sort_option == "Pertumbuhan Customer (%)":
            sort_column = "MAP_GROWTH"
        elif sort_option == "Pertumbuhan Customer":
            sort_column = "MAP_GROWTH_NUMBER"
        else:
            sort_column = "MAP_PROD_AGE_RATIO"

    with col2:
        top_n = st.slider(
            "Pilih Jumlah Kabupaten/Kota",
            min_value=1, 
            max_value=min(len(df["WADMKK"].unique()), 50),
            value=5
        )
else:
    title = "Kecamatan"
    grouped_col = "WADMKC"
    df["WADMKC"] = df["WADMKC"] + ", " + df["WADMKK"] + ", " + df["WADMPR"]
    df_book["WADMKC"] = df_book["WADMKC"] + ", " + df_book["WADMKK"] + ", " + df_book["WADMPR"]

    col1, col2 = st.columns([1.5, 1], vertical_alignment="center")
    with col1:
        sort_option = st.pills(
            "Urutkan Berdasarkan",
            ["Pertumbuhan Customer (%)", "Pertumbuhan Customer", f"Rasio Customer As of {quarter[1]} terhadap Usia Produktif"],
            default="Pertumbuhan Customer (%)"
        )
        
        if sort_option == "Pertumbuhan Customer (%)":
            sort_column = "MAP_GROWTH"
        elif sort_option == "Pertumbuhan Customer":
            sort_column = "MAP_GROWTH_NUMBER"
        else:
            sort_column = "MAP_PROD_AGE_RATIO"
            
    with col2:
        top_n = st.slider(
            "Pilih Jumlah Kecamatan",
            min_value=1, 
            max_value=min(len(df["WADMKC"].unique()), 50),
            value=5
        )

# Preprocess Data Based on Selection
if st.session_state.get("selected_level", "Nasional") == "Nasional":
    df_grouped = df.select_dtypes(include="number").sum(axis=0).to_frame().T
    df_grouped[grouped_col] = None
    df_grouped = calculate_growth(df_grouped)

    df_book_grouped = df_book.select_dtypes(include="number").sum(axis=0).to_frame().T
    df_book_grouped[grouped_col] = None
    df_book_grouped = process_df_booking(df_book_grouped)
else:
    numerical_columns = df.select_dtypes(include="number").columns
    df_grouped = df.groupby(grouped_col)[numerical_columns].sum().reset_index()
    df_grouped = calculate_growth(df_grouped)

    numerical_columns_book = df_book.select_dtypes(include="number").columns
    df_book_grouped = df_book.groupby(grouped_col)[numerical_columns_book].sum().reset_index()
    df_book_grouped = process_df_booking(df_book_grouped)

# Get Top Performers Based on Selection
if st.session_state.get("selected_level", "Nasional") == "Nasional":
    top_performers = df_grouped
    top_performers_merged = pd.concat([top_performers, df_book_grouped], axis=1)
elif st.session_state.get("selected_level", "Nasional") == "Pulau":
    top_performers = df_grouped.sort_values(sort_column, ascending=False)
    top_performers_book = df_book_grouped[df_book_grouped[grouped_col].isin(top_performers[grouped_col])]
    top_performers_merged = pd.merge(top_performers, top_performers_book, on=grouped_col, how="inner")
else:
    top_performers = df_grouped.nlargest(top_n, sort_column)
    top_performers_book = df_book_grouped[df_book_grouped[grouped_col].isin(top_performers[grouped_col])]
    top_performers_merged = pd.merge(top_performers, top_performers_book, on=grouped_col, how="inner")

# Customer & Booking Growth Metrics
for idx, row in top_performers_merged.iterrows():
    row_book = row

    nmc_growth, nmc_growth_unit = calculate_growth_and_unit(
        row[f"{quarter[1]}_NMC"], row[f"{quarter[0]}_NMC"])
    mpf_growth, mpf_growth_unit = calculate_growth_and_unit(
        row[f"{quarter[1]}_MPF"], row[f"{quarter[0]}_MPF"])
    refi_growth, refi_growth_unit = calculate_growth_and_unit(
        row[f"{quarter[1]}_REFI"], row[f"{quarter[0]}_REFI"])
    mmu_growth, mmu_growth_unit = calculate_growth_and_unit(
        row[f"{quarter[1]}_MMU"], row[f"{quarter[0]}_MMU"])
    others_growth, others_growth_unit = calculate_growth_and_unit(
        row[f"{quarter[1]}_OTHERS"], row[f"{quarter[0]}_OTHERS"])

    st.html(
        f"""
        <div class="custom-card">
            <h3>{row[grouped_col] if selection != 'Nasional' else 'NASIONAL'}</h3>
            <div class="metric-row">
                <div>
                    <p class="metric-label">Pertumbuhan Customer:</p>
                    <p class="metric-value">
                        <strong>
                            As of {quarter[0]}: {int(row[f'{quarter[0]}_CUST_NO']):,} → As of {quarter[1]}: {int(row[f'{quarter[1]}_CUST_NO']):,}
                        </strong>
                        <span class="growth-indicator {'growth-positive' if row['MAP_GROWTH'] > 0 else 'growth-negative' if row['MAP_GROWTH'] < 0 else 'growth-neutral'}" style="margin-left: 15px;">
                            {' ▲ ' if row['MAP_GROWTH'] > 0 else ' ▼ ' if row['MAP_GROWTH'] < 0 else ''} 
                            {row['MAP_GROWTH']:.2f}% ({int(row['MAP_GROWTH_NUMBER']):,})
                        </span>
                    </p>
                </div>
            </div>
            <div class="metric-row">
                <div>
                    <p class="metric-label">Rasio Customer As of {quarter[1]} terhadap Usia Produktif:</p>
                    <p class="metric-value">
                        <strong>
                            Usia Produktif: {int(row['Usia Produktif']):,}
                            <span style="margin-left: 15px;">Ratio: {row['MAP_PROD_AGE_RATIO']:.2f}%</span>
                        </strong>
                    </p>
                </div>
            </div>
            <p class="metric-label" style="margin-top: 10px;">Pertumbuhan Booking:</p>
            <div class="business-unit-metrics">
                <div>
                    <p><strong>NMC:</strong></p>
                    <p>As of {quarter[0]}: {int(row[f'{quarter[0]}_NMC']):,}</p>
                    <p>As of {quarter[1]}: {int(row[f'{quarter[1]}_NMC']):,}</p>
                    <p class="growth-indicator {'growth-positive' if nmc_growth > 0 else 'growth-negative' if nmc_growth < 0 else 'growth-neutral'}">
                        {' ▲ ' if nmc_growth > 0 else ' ▼ ' if nmc_growth < 0 else ''} 
                        {nmc_growth:.2f}% ({int(nmc_growth_unit):,})
                    </p>
                </div>
                <div>
                    <p><strong>MPF:</strong></p>
                    <p>As of {quarter[0]}: {int(row[f'{quarter[0]}_MPF']):,}</p>
                    <p>As of {quarter[1]}: {int(row[f'{quarter[1]}_MPF']):,}</p>
                    <p class="growth-indicator {'growth-positive' if mpf_growth > 0 else 'growth-negative' if mpf_growth < 0 else 'growth-neutral'}">
                        {' ▲ ' if mpf_growth > 0 else ' ▼ ' if mpf_growth < 0 else ''} 
                        {mpf_growth:.2f}% ({int(mpf_growth_unit):,})
                    </p>
                </div>
                <div>
                    <p><strong>REFI:</strong></p>
                    <p>As of {quarter[0]}: {int(row[f'{quarter[0]}_REFI']):,}</p>
                    <p>As of {quarter[1]}: {int(row[f'{quarter[1]}_REFI']):,}</p>
                    <p class="growth-indicator {'growth-positive' if refi_growth > 0 else 'growth-negative' if refi_growth < 0 else 'growth-neutral'}">
                        {' ▲ ' if refi_growth > 0 else ' ▼ ' if refi_growth < 0 else ''} 
                        {refi_growth:.2f}% ({int(refi_growth_unit):,})
                    </p>
                </div>
                <div>
                    <p><strong>MMU:</strong></p>
                    <p>As of {quarter[0]}: {int(row[f'{quarter[0]}_MMU']):,}</p>
                    <p>As of {quarter[1]}: {int(row[f'{quarter[1]}_MMU']):,}</p>
                    <p class="growth-indicator {'growth-positive' if mmu_growth > 0 else 'growth-negative' if mmu_growth < 0 else 'growth-neutral'}">
                        {' ▲ ' if mmu_growth > 0 else ' ▼ ' if mmu_growth < 0 else ''} 
                        {mmu_growth:.2f}% ({int(mmu_growth_unit):,})
                    </p>
                </div>
                <div>
                    <p><strong>OTHERS:</strong></p>
                    <p>As of {quarter[0]}: {int(row[f'{quarter[0]}_OTHERS']):,}</p>
                    <p>As of {quarter[1]}: {int(row[f'{quarter[1]}_OTHERS']):,}</p>
                    <p class="growth-indicator {'growth-positive' if others_growth > 0 else 'growth-negative' if others_growth < 0 else 'growth-neutral'}">
                        {' ▲ ' if others_growth > 0 else ' ▼ ' if others_growth < 0 else ''} 
                        {others_growth:.2f}% ({int(others_growth_unit):,})
                    </p>
                </div>
            </div>
        </div>
        """
    )