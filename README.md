# MCS-Atmospheric-Profiles (Mars)
This interactive tool uses Streamlit to plot atmospheric profiles of Mars. Select the date and custom latitudinal and longitudinal range to visualize data from the MRO/MCS in Mars.

## How to run
1. Download MCS_code.py and marstime folder (make sure both are in the same directory)
2. Install requirements.txt libraries:
   ```
   $ pip install -r requirements.txt
   ```
3. To launch write in the terminal:
   ```
   $ streamlit run MCS_code.py
   ```
## Run in Streamlit App Web
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://mcs-atmospheric-profiles-itr3l6tsjzinwdsc3opdyh.streamlit.app/)

## 📄 Citation
[![DOI](https://zenodo.org/badge/1067020080.svg)](https://doi.org/10.5281/zenodo.17427725)

## 📖 User Guide
### First Steps
1. **Select dates:** When you launch the app, the first step is to select a date using a date picker.
2. **Load Data:** Click the **"Find, load and process data"** button (do NOT click "Plot" first, as this will cause an error).

### Data Processing
3. **PDS directory:** After clicking **"Find, load and process data"**, you'll see a link to the PDS (Planetary Data System) directory where the MCS instrument data is downloaded from. You can explore this directory to learn more about data parameters, units, and MCS data declarations.

### Visualization Controls
4. **Display Controls:** Once data processing is complete, scroll down to the **"Display Controls"** section where you can adjust:
   - Latitudinal Range
   - Longitudinal Range
   - Local Time (LTST)

5. **Generate Plots:** After setting your parameters, click the **"Plot"** button to generate the atmospheric profile figures.

### Advanced Features
6. **Data Inspection:** After plotting, you can enable the **"display data"** checkbox to view the actual dataset used to create the graphs.
   
7. **Export Options:** Download the generated figures in multiple formats (PDF, PNG, JPEG, SVG).  
   Note: changing the format will reload the plotting code but only affects the download format.
   
8. **Atmospheric Parameters:** In the top-left sidebar, you can adjust:
   - Water vapour volume mixing ratio
   - CO2 mixing ratio  
     These parameters affect the saturation pressure curves in the plots.

### ⚠️ Important Notes
- **ALWAYS click "Plot" after making ANY changes to:**
  - Mixing ratios (water vapour or CO2)
  - Latitudinal/Longitudinal ranges
  - Local Time (LTST) settings

- While the **"display data"** table updates automatically with range changes, it's good practice to click **"Plot"** after any parameter modification to ensure proper graph rendering.



