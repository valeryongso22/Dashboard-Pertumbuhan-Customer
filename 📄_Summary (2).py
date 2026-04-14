import pathlib
import streamlit as st
import numpy as np
import pandas as pd

from datetime import datetime

# App Settings
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

# Data
def calculate_growth(df):
    df["CUSTOMER_GROWTH"] = np.where(
        df["2019_CUST_NO"] == 0,
        0,
        ((df["2024_CUST_NO"] - df["2019_CUST_NO"]) / df["2019_CUST_NO"]) * 100
    )
    df["CUSTOMER_GROWTH_UNIT"] = df["2024_CUST_NO"] - df["2019_CUST_NO"]
    df["CUST_PRODUCTIVE_RATIO"] = (df["2024_CUST_NO"] / df["Usia Produktif"]) * 100
    
    business_units = ["NMC", "REFI", "MPF", "MMU", "OTHERS"]
    for unit in business_units:
        df[f"{unit}_TOTAL_2019"] = df[f"2019_{unit}_N"] + df[f"2019_{unit}_Y"]
        df[f"{unit}_TOTAL_2024"] = df[f"2024_{unit}_N"] + df[f"2024_{unit}_Y"]
        df[f"{unit}_GROWTH"] = np.where(
            df[f"{unit}_TOTAL_2019"] == 0,
            0,
            ((df[f"{unit}_TOTAL_2024"] - df[f"{unit}_TOTAL_2019"]) / df[f"{unit}_TOTAL_2019"]) * 100
        )
        df[f"{unit}_GROWTH_UNIT"] = df[f"{unit}_TOTAL_2024"] - df[f"{unit}_TOTAL_2019"]
    
    df = df.replace([float("inf"), -float("inf")], 0).fillna(0)

    return df

@st.cache_data()
def preparing_data():
    df = pd.read_excel("Data Fix/Data Customer AGG_v2.xlsx")

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
    return df

df = preparing_data()

col1, col2 = st.columns(2)

# Initialize Session State for Sorting Preference If It Doesn't Exist
if 'sort_by_percentage' not in st.session_state:
    st.session_state.sort_by_percentage = True

# Callback Function for Toggle Change
def update_sort_preference():
    st.session_state.sort_by_percentage = not st.session_state.sort_by_percentage

# Selection Pills
selection = st.pills(
    "Pilih Level",
    ["Nasional", "Pulau", "Top N Provinsi", "Top N Kabupaten/Kota", "Top N Kecamatan"],
    default="Nasional"
)

# Initialize title and grouped_col Based on Selection
if selection == "Nasional":
    title = "Nasional"
    grouped_col = None

elif selection == "Pulau":
    title = "Pulau"
    grouped_col = "PULAU"

    sort_option = st.pills(
        "Urutkan Berdasarkan",
        ["Pertumbuhan Customer (%)", "Pertumbuhan Customer", "Rasio Customer As of 2024 terhadap Usia Produktif"],
        default="Pertumbuhan Customer (%)"
    )
    
    if sort_option == "Pertumbuhan Customer (%)":
        sort_column = "CUSTOMER_GROWTH"
    elif sort_option == "Pertumbuhan Customer":
        sort_column = "CUSTOMER_GROWTH_UNIT"
    else:
        sort_column = "CUST_PRODUCTIVE_RATIO"

elif selection == "Top N Provinsi":
    title = "Provinsi"
    grouped_col = "WADMPR"

    col1, col2 = st.columns([1.5, 1], vertical_alignment="center")
    with col1:
        sort_option = st.pills(
            "Urutkan Berdasarkan",
            ["Pertumbuhan Customer (%)", "Pertumbuhan Customer", "Rasio Customer As of 2024 terhadap Usia Produktif"],
            default="Pertumbuhan Customer (%)"
        )
        
        if sort_option == "Pertumbuhan Customer (%)":
            sort_column = "CUSTOMER_GROWTH"
        elif sort_option == "Pertumbuhan Customer":
            sort_column = "CUSTOMER_GROWTH_UNIT"
        else:
            sort_column = "CUST_PRODUCTIVE_RATIO"

    with col2:
        top_n = st.slider(
            "Pilih Jumlah Provinsi",
            min_value=1, 
            max_value=min(len(df["WADMPR"].unique()), 50),
            value=5
        )

elif selection == "Top N Kabupaten/Kota":
    title = "Kabupaten/Kota"
    grouped_col = "WADMKK"
    df["WADMKK"] = df["WADMKK"] + ", " + df["WADMPR"]

    col1, col2 = st.columns([1.5, 1], vertical_alignment="center")
    with col1:
        sort_option = st.pills(
            "Urutkan Berdasarkan",
            ["Pertumbuhan Customer (%)", "Pertumbuhan Customer", "Rasio Customer As of 2024 terhadap Usia Produktif"],
            default="Pertumbuhan Customer (%)"
        )
        
        if sort_option == "Pertumbuhan Customer (%)":
            sort_column = "CUSTOMER_GROWTH"
        elif sort_option == "Pertumbuhan Customer":
            sort_column = "CUSTOMER_GROWTH_UNIT"
        else:
            sort_column = "CUST_PRODUCTIVE_RATIO"
    with col2:
        top_n = st.slider(
            "Pilih Jumlah Kabupaten/Kota",
            min_value=1, 
            max_value=min(len(df["WADMKK"].unique()), 50),
            value=5
        )

else:  # Top N Kecamatan
    title = "Kecamatan"
    grouped_col = "WADMKC"
    df["WADMKC"] = df["WADMKC"] + ", " + df["WADMKK"] + ", " + df["WADMPR"]

    col1, col2 = st.columns([1.5, 1], vertical_alignment="center")
    with col1:
        sort_option = st.pills(
            "Urutkan Berdasarkan",
            ["Pertumbuhan Customer (%)", "Pertumbuhan Customer", "Rasio Customer As of 2024 terhadap Usia Produktif"],
            default="Pertumbuhan Customer (%)"
        )
        
        if sort_option == "Pertumbuhan Customer (%)":
            sort_column = "CUSTOMER_GROWTH"
        elif sort_option == "Pertumbuhan Customer":
            sort_column = "CUSTOMER_GROWTH_UNIT"
        else:
            sort_column = "CUST_PRODUCTIVE_RATIO"
    with col2:
        top_n = st.slider(
            "Pilih Jumlah Kecamatan",
            min_value=1, 
            max_value=min(len(df["WADMKC"].unique()), 50),
            value=5
        )

# Process Data Based on Selection
if selection == "Nasional":
    df_grouped = df.agg({
        "2019_CUST_NO": "sum",
        "2024_CUST_NO": "sum",
        "Usia Produktif": "sum",
        "2019_NMC_N": "sum", "2019_NMC_Y": "sum",
        "2024_NMC_N": "sum", "2024_NMC_Y": "sum",
        "2019_MPF_N": "sum", "2019_MPF_Y": "sum",
        "2024_MPF_N": "sum", "2024_MPF_Y": "sum",
        "2019_REFI_N": "sum", "2019_REFI_Y": "sum",
        "2024_REFI_N": "sum", "2024_REFI_Y": "sum",
        "2019_MMU_N": "sum", "2019_MMU_Y": "sum",
        "2024_MMU_N": "sum", "2024_MMU_Y": "sum",
        "2019_OTHERS_N": "sum", "2019_OTHERS_Y": "sum",
        "2024_OTHERS_N": "sum", "2024_OTHERS_Y": "sum"
    }).to_frame().T
else:
    df_grouped = df.groupby(grouped_col).agg({
        "2019_CUST_NO": "sum",
        "2024_CUST_NO": "sum",
        "Usia Produktif": "sum",
        "2019_NMC_N": "sum", "2019_NMC_Y": "sum",
        "2024_NMC_N": "sum", "2024_NMC_Y": "sum",
        "2019_MPF_N": "sum", "2019_MPF_Y": "sum",
        "2024_MPF_N": "sum", "2024_MPF_Y": "sum",
        "2019_REFI_N": "sum", "2019_REFI_Y": "sum",
        "2024_REFI_N": "sum", "2024_REFI_Y": "sum",
        "2019_MMU_N": "sum", "2019_MMU_Y": "sum",
        "2024_MMU_N": "sum", "2024_MMU_Y": "sum",
        "2019_OTHERS_N": "sum", "2019_OTHERS_Y": "sum",
        "2024_OTHERS_N": "sum", "2024_OTHERS_Y": "sum"
    }).reset_index()

df_grouped = calculate_growth(df_grouped)

# Get Top Performers Based on Selection
if selection == "Nasional":
    top_performers = df_grouped
elif selection == "Pulau":
    top_performers = df_grouped.sort_values(sort_column, ascending=False)
else:
    top_performers = df_grouped.nlargest(top_n, sort_column)

for idx, row in top_performers.iterrows():
    st.html(
        f"""
        <div class="custom-card">
            <h3>{row[grouped_col] if selection != 'Nasional' else 'NASIONAL'}</h3>
            <div class="metric-row">
                <div>
                    <p class="metric-label">Pertumbuhan Customer:</p>
                    <p class="metric-value">
                        <strong>
                            As of 2019: {int(row['2019_CUST_NO']):,} → As of 2024: {int(row['2024_CUST_NO']):,}
                        </strong>
                        <span class="growth-indicator {'growth-positive' if row['CUSTOMER_GROWTH'] > 0 else 'growth-negative' if row['CUSTOMER_GROWTH'] < 0 else 'growth-neutral'}" style="margin-left: 15px;">
                            {' ▲ ' if row['CUSTOMER_GROWTH'] > 0 else ' ▼ ' if row['CUSTOMER_GROWTH'] < 0 else ''} 
                            {row['CUSTOMER_GROWTH']:.2f}% ({int(row['CUSTOMER_GROWTH_UNIT']):,})
                        </span>
                    </p>
                </div>
            </div>
            <div class="metric-row">
                <div>
                    <p class="metric-label">Rasio Customer As of 2024 terhadap Usia Produktif:</p>
                    <p class="metric-value">
                        <strong>
                            Usia Produktif: {int(row['Usia Produktif']):,}
                            <span style="margin-left: 15px;">Ratio: {row['CUST_PRODUCTIVE_RATIO']:.2f}%</span>
                        </strong>
                    </p>
                </div>
            </div>
            <p class="metric-label" style="margin-top: 10px;">Pertumbuhan Booking:</p>
            <div class="business-unit-metrics">
                <div>
                    <p><strong>NMC:</strong></p>
                    <p>As of 2019: {int(row['NMC_TOTAL_2019']):,}</p>
                    <p>As of 2024: {int(row['NMC_TOTAL_2024']):,}</p>
                    <p class="growth-indicator {'growth-positive' if row['NMC_GROWTH'] > 0 else 'growth-negative' if row['NMC_GROWTH'] < 0 else 'growth-neutral'}">
                        {' ▲ ' if row['NMC_GROWTH'] > 0 else ' ▼ ' if row['NMC_GROWTH'] < 0 else ''} 
                        {row['NMC_GROWTH']:.2f}% ({int(row['NMC_GROWTH_UNIT']):,})
                    </p>
                </div>
                <div>
                    <p><strong>MPF:</strong></p>
                    <p>As of 2019: {int(row['MPF_TOTAL_2019']):,}</p>
                    <p>As of 2024: {int(row['MPF_TOTAL_2024']):,}</p>
                    <p class="growth-indicator {'growth-positive' if row['MPF_GROWTH'] > 0 else 'growth-negative' if row['MPF_GROWTH'] < 0 else 'growth-neutral'}">
                        {' ▲ ' if row['MPF_GROWTH'] > 0 else ' ▼ ' if row['MPF_GROWTH'] < 0 else ''} 
                        {row['MPF_GROWTH']:.2f}% ({int(row['MPF_GROWTH_UNIT']):,})
                    </p>
                </div>
                <div>
                    <p><strong>REFI:</strong></p>
                    <p>As of 2019: {int(row['REFI_TOTAL_2019']):,}</p>
                    <p>As of 2024: {int(row['REFI_TOTAL_2024']):,}</p>
                    <p class="growth-indicator {'growth-positive' if row['REFI_GROWTH'] > 0 else 'growth-negative' if row['REFI_GROWTH'] < 0 else 'growth-neutral'}">
                        {' ▲ ' if row['REFI_GROWTH'] > 0 else ' ▼ ' if row['REFI_GROWTH'] < 0 else ''} 
                        {row['REFI_GROWTH']:.2f}% ({int(row['REFI_GROWTH_UNIT']):,})
                    </p>
                </div>
                <div>
                    <p><strong>MMU:</strong></p>
                    <p>As of 2019: {int(row['MMU_TOTAL_2019']):,}</p>
                    <p>As of 2024: {int(row['MMU_TOTAL_2024']):,}</p>
                    <p class="growth-indicator {'growth-positive' if row['MMU_GROWTH'] > 0 else 'growth-negative' if row['MMU_GROWTH'] < 0 else 'growth-neutral'}">
                        {' ▲ ' if row['MMU_GROWTH'] > 0 else ' ▼ ' if row['MMU_GROWTH'] < 0 else ''} 
                        {row['MMU_GROWTH']:.2f}% ({int(row['MMU_GROWTH_UNIT']):,})
                    </p>
                </div>
                <div>
                    <p><strong>OTHERS:</strong></p>
                    <p>As of 2019: {int(row['OTHERS_TOTAL_2019']):,}</p>
                    <p>As of 2024: {int(row['OTHERS_TOTAL_2024']):,}</p>
                    <p class="growth-indicator {'growth-positive' if row['OTHERS_GROWTH'] > 0 else 'growth-negative' if row['OTHERS_GROWTH'] < 0 else 'growth-neutral'}">
                        {' ▲ ' if row['OTHERS_GROWTH'] > 0 else ' ▼ ' if row['OTHERS_GROWTH'] < 0 else ''} 
                        {row['OTHERS_GROWTH']:.2f}% ({int(row['OTHERS_GROWTH_UNIT']):,})
                    </p>
                </div>
            </div>
        </div>
        """
    )