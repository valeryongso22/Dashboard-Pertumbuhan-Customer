# FIFGROUP Customer Growth Dashboard

## Description

This is a Streamlit web application designed to visualize and analyze customer growth trends for FIFGROUP. It provides interactive maps, charts, and metrics to explore customer data across different geographical regions (province, city/regency, district), time periods, and business unit combinations.

## Features

*   **Interactive Map Visualization:** Utilizes Folium and `streamlit-folium` to display customer growth data on an interactive map of Indonesia. Users can drill down from national view to province, city/regency, and district levels.
*   **Multiple Metrics:** Choose different metrics to visualize on the map:
    *   Pertumbuhan Customer (%)
    *   Pertumbuhan Customer (Absolute Number)
    *   Rasio Customer dan Usia Produktif 2024 (%)
    *   Rasio Pertumbuhan Customer (Selected BU vs. ALL) (%)
*   **Filtering:**
    *   Select a time range (from 2019 to 2024Q4)
    *   Filter by initial and final Business Units (ALL, NMC, REFI, MPF) to analyze customer transitions or overall growth
    *   Filter by group age (<20, 20-30, 30-40, 40-50, and >50)
*   **Location Markers:** Toggle the display of markers for:
    *   FIFGROUP Cabang (Branches) & POS
    *   Dealers & POS Dealers
    *   Competitors (Adira, OTO, BFI, Bank Mega, Mandala, Others)
*   **Key Performance Indicators (KPIs):** Displays aggregated customer counts and growth percentages for the currently viewed geographical level (National, Province, City/Regency, District).
*   **Booking Growth Metrics:** Shows aggregated booking numbers and growth for different business units (NMC, MPF, REFI, AMITRA, Others) based on the selected filters.
*   **Trend Analysis:**
    *   An interactive Altair line and bar chart showing the trend of the selected metric and cumulative customer count over the selected time period.
    *   Expandable tables showing the ranking trend (Top N) for Pulau, Provinsi, Kabupaten/Kota, and Kecamatan based on the selected metric and time range.
    *   Expandable tables showing the predictions for upcoming quarters and for the Top N regions.
*   **Custom Styling:** Includes custom CSS for enhanced visual appearance.
*   **Data Caching:** Uses Streamlit's caching (`@st.cache_data`) to speed up data loading.

## Data Requirements

The application expects the following data files to be present in a `data/` subdirectory relative to `main.py`:

*   `data/LapakGIS_Batas_Provinsi_2024.json`: GeoJSON file for province boundaries.
*   `data/LapakGIS_Batas_Kabupaten_2024.json`: GeoJSON file for city/regency boundaries.
*   `data/LapakGIS_Batas_Kecamatan_2024.json`: GeoJSON file for district boundaries.
*   `data/Data Cabang.xlsx`: Excel file containing FIFGROUP branch and POS location data.
*   `data/Data Dealer dan Kompetitor.xlsx`: Excel file containing dealer and competitor location data.
*   `data/Data Customer AGG_v4.parquet`: Parquet file with aggregated customer data per region and quarter.
*   `data/Data Booking AGG_v4.parquet`: Parquet file with aggregated booking data per region and quarter.

Additionally, assets are expected in the `assets/` directory:

*   `assets/css/styles.css`: Custom CSS file.
*   `assets/images/FIFGROUP_KOTAK.png`: Application icon.
*   `assets/images/FIFGROUP.png`: Header logo.

*(Note: Map marker icons seem to be loaded from external URLs specified in the code).*

## Setup and Installation

1.  **Prerequisites:** Ensure you have Python installed on your system.
2.  **Clone the repository (if applicable):**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```
3.  **Install `uv` (if you don't have it):**
    `uv` is a fast Python package installer and resolver. Follow the official installation instructions: [https://github.com/astral-sh/uv#installation](https://github.com/astral-sh/uv#installation)
    (Typically involves running a curl or PowerShell command).
4.  **Sync Dependencies:**
    Navigate to the project's root directory (where `pyproject.toml` is located) and run:
    ```bash
    uv sync
    ```
    This command will automatically:
    *   Create a virtual environment named `.venv` if it doesn't exist.
    *   Install the exact dependencies specified in `uv.lock` (derived from `pyproject.toml`) into the virtual environment.
5.  **Ensure Data Files:** Place the required `.json`, `.xlsx`, and `.parquet` files into the `data/` directory and the assets into the `assets/` directory as described above.

## Running the Application

1.  **Activate the virtual environment (if not already active):**
    `uv` commands often activate the environment implicitly for subsequent commands in the same session, but for clarity or new sessions:
    ```bash
    # On Windows (Command Prompt)
    .\.venv\Scripts\activate.bat
    # On Windows (PowerShell)
    .\.venv\Scripts\Activate.ps1
    # On macOS/Linux
    source .venv/bin/activate
    ```
2.  **Run Streamlit:**
    With the virtual environment activated, run:
    ```bash
    streamlit run main.py
    ```
    This will start the Streamlit server using the packages installed in the `.venv` environment and open the dashboard in your default web browser.

## Author

Developed by the **Risk Policy Department** of the **Risk Management Division** (as indicated in the application footer).
