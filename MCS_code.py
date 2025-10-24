# Download as app.py
# Launch in terminal: streamlit run app.py
# Modificación de la primera versión del programa al añadir la hora local en los datos y una barra de control para filtrar según la hora local

import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
from io import BytesIO  # <-- Agrega esta línea

warnings.filterwarnings('ignore', category=RuntimeWarning)

# --- Configuración ---
BASE_URL = "https://atmos.nmsu.edu/PDS/data/"
CODIFICACION = "latin1"

# --- Funciones auxiliares ---
def convertir_longitud(lon):
    return lon % 360

# Calcula MROM DDR partiendo de MROM_2001 = septiembre 2006
def fecha_a_mrom_ddr(year, month):
    base_year, base_month = 2006, 9
    numero = 2001 + (year - base_year) * 12 + (month - base_month)
    return f"MROM_{numero:04d}"

def construir_url(fecha):
    y, m, d = fecha.year, fecha.month, fecha.day
    mrom = fecha_a_mrom_ddr(y, m)
    fecha_str = f"{y}{m:02d}{d:02d}"
    url = f"{BASE_URL}{mrom}/DATA/{y}/{y}{m:02d}/{fecha_str}/"
    return url

# Listar solo archivos DDR
def listar_tab_files_ddr(url):
    r = requests.get(url)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    return [url + link.get("href") for link in soup.find_all("a") 
            if link.get("href").upper().endswith("_DDR.TAB")]

# --- Descarga paralela ---
def descargar_archivos(urls, carpeta_destino):
    os.makedirs(carpeta_destino, exist_ok=True)
    paths = []
    st.write("Uploading files...")
    progreso = st.progress(0)

    def descargar(u):
        nombre = u.split("/")[-1]
        destino = os.path.join(carpeta_destino, nombre)
        r = requests.get(u)
        if r.status_code == 200:
            with open(destino, "wb") as f:
                f.write(r.content)
            return destino
        return None

    with ThreadPoolExecutor(max_workers=6) as executor:
        futuros = {executor.submit(descargar, u): u for u in urls}
        for i, futuro in enumerate(as_completed(futuros), 1):
            resultado = futuro.result()
            if resultado:
                paths.append(resultado)
            progreso.progress(i / len(urls))
    return paths

def cargar_archivo(archivo):
    try:
        st.write(f"🔍 Analyzing file: {archivo}")
        
        # Leer el archivo completo
        with open(archivo, 'r', encoding=CODIFICACION) as f:
            contenido = f.read()
        
        # Dividir en líneas
        lineas = contenido.split('\n')
        st.write(f"📊 Number of lines: {len(lineas)}")
        
        datos = []
        lineas_procesadas = 0
        lineas_ignoradas = 0
        
        # Valor de hora local asignado al bloque actual (se actualiza al encontrar una cabecera)
        local_time_actual = np.nan

        for i, linea in enumerate(lineas):
            if not linea.strip():
                continue
                
            # Saltar líneas de encabezado/metadata (las que no empiezan con número)
            if not linea.strip().startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
                lineas_ignoradas += 1
                continue
            
            # Dividir la línea por comas (el formato usa comas como separador)
            partes = [parte.strip() for parte in linea.split(',')]

            # Detectar línea de encabezado: >15 columnas y segunda columna con fecha entre comillas
            if len(partes) > 15 and partes[0] == '0' and partes[1].strip().startswith('"') and ('-' in partes[1]):
                # intenta extraer la columna 12 (índice 11) y convertirla a horas
                try:
                    raw = partes[11].strip().replace('"', '').replace("'", "")
                    try:
                        # si viene normalizado (ej: 0.5) -> multiplicar por 24
                        local_time_actual = float(raw.replace(',', '.')) * 24
                    except ValueError:
                        # si por lo que sea viniese en formato hh:mm:ss -> convertir a horas
                        if ':' in raw:
                            hh, mm, ss = raw.split(':')
                            local_time_actual = float(hh) + float(mm) / 60.0 + float(ss) / 3600.0
                        else:
                            local_time_actual = np.nan
                except Exception:
                    local_time_actual = np.nan
                
                # Esto lo consideramos una línea de encabezado (es decir, no es una fila de datos)
            
            # Solo procesar líneas que tengan exactamente 15 columnas y empiecen con "0"
            if len(partes) == 15 and partes[0] == '0':
                try:
                    # Verificar que la segunda columna sea numérica
                    float(partes[1].replace(',', '.'))
                    # Añadimos la hora local actual (se añade como string para mantener la consistencia antes de convertir)
                    lt = 'nan' if pd.isna(local_time_actual) else str(local_time_actual)
                    datos.append(partes + [lt])
                    lineas_procesadas += 1
                    
                    # Mostrar primera línea de datos como ejemplo
                    if len(datos) == 1:
                        st.write("✅ First Line:")
                        st.write(f"Raw: {linea}")
                        st.write(f"LocalTime assigned: {lt}")
                        #st.write(f"Partes: {partes}")
                        
                except (ValueError, IndexError) as e:
                    lineas_ignoradas += 1
                    if lineas_ignoradas <= 3:  # Mostrar solo primeros errores
                        st.write(f"❌ Line ignored (error): {e}")
            else:
                lineas_ignoradas += 1
                if lineas_ignoradas <= 3:  # Mostrar solo primeros ejemplos
                    st.write(f"❌ Line ignored ({len(partes)} columns, start with '{partes[0] if partes else 'N/A'}'): {linea[:100]}...")
        
        st.write(f"📈 Summary: {lineas_procesadas} processed lines, {lineas_ignoradas} ignored")
        
        if not datos:
            st.warning("⚠️ There is no valid data")
            return pd.DataFrame()
            
        # Crear DataFrame
        columnas = [
            'Descartar', 'Pres', 'T', 'T_err', 'Dust', 'Dust_err',
            'H2Ovap', 'H2Ovap_err', 'H2Oice', 'H2Oice_err',
            'CO2ice', 'CO2ice_err', 'Alt', 'Lat', 'Lon', 'LocalTime'
        ]
        
        df = pd.DataFrame(datos, columns=columnas)
        st.write(f"📊 DataFrame created with {len(df)} lines")
        
        # Convertir a numérico
        for col in columnas[1:]:  # Todas excepto la primera
            try:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
                st.write(f"✅ Column {col} converted to numeric")
            except Exception as e:
                st.error(f"❌ Error converting column {col}: {e}")
        

        
        # Filtrar valores inválidos (-9999)
        df = df.replace(-9999, np.nan)
        # Convertir longitud
        df['Lon'] = df['Lon'].apply(convertir_longitud)

        df_final = df.dropna(subset=['Pres', 'T', 'Alt', 'Lat', 'Lon'], how='any')
        
        st.write(f"🎯 Final DataFrame after processing: {len(df_final)} lines")
        
        if not df_final.empty:
            st.write("📋 First lines of the DataFrame:")
            st.dataframe(df_final.head(50))
            
            # Mostrar estadísticas básicas
            st.write("📊 Estatistics:")
            st.write(f" - Pressure: {df_final['Pres'].min():.2e} to {df_final['Pres'].max():.2e} Pa")
            st.write(f" - Temperature: {df_final['T'].min():.1f} to {df_final['T'].max():.1f} K")
            st.write(f" - Altitude: {df_final['Alt'].min():.1f} to {df_final['Alt'].max():.1f} km")
            st.write(f" - Latitude: {df_final['Lat'].min():.1f} to {df_final['Lat'].max():.1f}°")
            st.write(f" - Longitude: {df_final['Lon'].min():.1f} to {df_final['Lon'].max():.1f}°")
            st.write(f" - LocalTime: {df_final['LocalTime'].min():.1f} to {df_final['LocalTime'].max():.1f}")
        
        return df_final
    
    except Exception as e:
        st.error(f"💥 Error loading file {archivo}: {str(e)}")
        return pd.DataFrame()

def cargar_multiples_archivos(directorio):
    archivos = Path(directorio).glob("*.TAB")
    dfs = []
    for archivo in archivos:
        df = cargar_archivo(archivo)
        if not df.empty:
            dfs.append(df)
    if dfs:
        df_total = pd.concat(dfs, ignore_index=True)

        # Guardar DataFrame en un Excel - Quitar '#' para ver descargar excel con los datos
        #output_file = Path(directorio) / "datos_crudos_Streamlit.xlsx"
        #df_total.to_excel(output_file, index=False)
        return df_total
    return pd.DataFrame()

# --- Funciones para gráficas (del segundo código) ---
def calcular_presion_saturacion(T, xvvco2):
    T = np.array(T)
    logPsat = np.zeros_like(T)
    
    mask_high = T > 216.56
    mask_low = ~mask_high
    
    if np.any(mask_high):
        T_high = T[mask_high]
        logPsat[mask_high] = (3.128082 - 867.2124/T_high + 18.65612e-3*T_high - 
                              72.48820e-6*T_high**2 + 93e-9*T_high**3)
    
    if np.any(mask_low):
        T_low = T[mask_low]
        logPsat[mask_low] = (6.760956 - 1284.07/(T_low - 4.718) + 
                             1.256e-4*(T_low - 143.15))
    
    return (10**logPsat)*1.0e5/xvvco2

def calcular_presion_saturacion_H2O(T, xvvh2o):
    T = np.array(T)
    Psat = 611 * np.exp(22.5*(1 - 273.16/T))
    return Psat/xvvh2o

def crear_graficas(df_filtrado, lat_range, lon_range, local_range):
    if df_filtrado.empty:
        st.warning("There is no data for the range selected")
        return None
    
    # Crear figura nueva
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    
    # --- Gráfica 1: Temperatura vs Presión/Altitud ---
    df_temp = df_filtrado[(df_filtrado['Pres'].notna()) &
                          (df_filtrado['Alt'].notna()) & 
                         (df_filtrado['T'].notna()) &
                         (df_filtrado['Lon'].notna()) &
                         (df_filtrado['Lat'].notna())].copy()
    
    if not df_temp.empty:
        # Eliminar duplicados
        #df_temp = df_temp.drop_duplicates(subset=['Alt', 'Pres'])
        
        # CREAR EJE SECUNDARIO (como en tu código original)
        ax1b = ax1.twinx()
        
        # 1. PLOT PRINCIPAL: Temperatura vs Presión (eje izquierdo)
        ax1.errorbar(df_temp['T'], df_temp['Pres'], 
                    xerr=df_temp['T_err'], fmt='o', ms=3, elinewidth=0.5,
                    color='firebrick', alpha=0.6, zorder=2, 
                    label='Temperature Profiles')
        
        # 2. EJE SECUNDARIO: Temperatura vs Altitud (transparente, solo para escala)
        ax1b.plot(df_temp['T'], df_temp['Alt'], 'x', color='blue', alpha=0, label=None)
        
        # 3. CURVAS DE SATURACIÓN (igual que en Jupyter)
        T_range = np.linspace(50, 300, 100)
        
        PsatCO2_min = calcular_presion_saturacion(T_range, Xvv_CO2_min)
        PsatH2O_min = calcular_presion_saturacion_H2O(T_range, Xvv_H2O_min)
        PsatH2O_max = calcular_presion_saturacion_H2O(T_range, Xvv_H2O_max)
        
        ax1.semilogy(T_range, PsatCO2_min, '--', color='navy', zorder=5,
                    linewidth=2, label=f'Psat CO₂ X={Xvv_CO2_min:.2f}')
        ax1.semilogy(T_range, PsatH2O_min, '--', color='lime', zorder=5,
                    linewidth=2, label=f'Psat H₂O X_min={Xvv_H2O_min:.2e}')
        ax1.semilogy(T_range, PsatH2O_max, ':', color='lime', zorder=5,
                    linewidth=2, label=f'Psat H₂O X_max={Xvv_H2O_max:.2e}')
        
        # 4. CONFIGURACIÓN DE EJES (COPIADO DIRECTAMENTE DE JUPYTER)
        ax1.set_xlabel('Temperature [K]', fontsize=15)
        ax1.set_xlim(50, 300)
        ax1b.set_ylabel('Altitude [km]', fontsize=15)
        ax1b.yaxis.labelpad = 10
        
        # Sincronización usando relación barométrica (simplificada)
        alt_min, alt_max = df_temp['Alt'].min(), df_temp['Alt'].max()
        pres_min, pres_max = df_temp['Pres'].max(), df_temp['Pres'].min()  # ¡INVERTIDO!
        
        ax1b.set_ylim(alt_min, alt_max)
        ax1.set_ylim(pres_min, pres_max)  # Presión invertida: mayor presión abajo
        
        # Configurar eje de presión (invertido y logarítmico)
        ax1.set_yscale('log')
        ax1.set_ylabel('Pressure [Pa]', color='firebrick', fontsize=15, labelpad=10)
        ax1b.yaxis.set_label_position("right")
        
        ax1.tick_params(axis='y', labelcolor='firebrick', labelsize=14)
        ax1.tick_params(axis='x', labelsize=14)
        ax1b.tick_params(axis='y', labelsize=14)

        yticks = np.arange(np.floor(alt_min/20)*20, np.ceil(alt_max/20)*20 + 1, 20)
        ax1b.set_yticks(yticks)

        ax1.grid(True)
        
        # Leyenda
        lines1, labels1 = ax1.get_legend_handles_labels()
        ax1.legend(lines1, labels1, loc='upper right', fontsize=13)
    
    # --- Gráfica de Opacidad ---
        df_dust = df_filtrado[df_filtrado['Dust'].notna()]
        df_ice  = df_filtrado[df_filtrado['H2Oice'].notna()]

    
    if not df_dust.empty or not df_ice.empty:
        ax2.set_xscale('log')
        ax2.set_xlim(1e-5, 1)
        
        # Usar mismos límites de altitud que la primera gráfica
        if not df_temp.empty:
            ax2.set_ylim(alt_min, alt_max)
            ax2.set_yticks(yticks)
        else:
            # Si no hay datos de temp, calcular de dust/ice
            alt_data = pd.concat([df_dust['Alt'], df_ice['Alt']] if not df_ice.empty else [df_dust['Alt']])
            if not alt_data.empty:
                ax2.set_ylim(alt_data.min(), alt_data.max())
        
        ax2.tick_params(axis='both', labelsize=14)
        ax2.yaxis.labelpad = 10
        
        if not df_dust.empty:
            ax2.errorbar(df_dust['Dust'], df_dust['Alt'],
                        xerr=df_dust['Dust_err'], elinewidth=0.5,
                        fmt='o', color='sienna', ms=3, 
                        label='Dust', alpha=0.6, capsize=3)
        
        if not df_ice.empty:
            ax2.errorbar(df_ice['H2Oice'], df_ice['Alt'],
                        xerr=df_ice['H2Oice_err'], elinewidth=0.5,
                        fmt='o', color='royalblue', ms=3,
                        label='Ice H₂O', alpha=0.6, capsize=3)
        
        ax2.set_xlabel('Opacity', fontsize=15)
        ax2.set_ylabel('Altitude [km]', fontsize=15)
        ax2.grid(True)
        ax2.legend(fontsize=13)
    else:
        ax2.text(0.5, 0.5, 'No hay datos de opacidad', 
                ha='center', va='center', transform=ax2.transAxes, fontsize=12)
        ax2.set_xlabel('Opacity', fontsize=15)
        ax2.set_ylabel('Altitude [km]', fontsize=15)
    
    # Ajustar posición para alineación perfecta (como en Jupyter)
    if not df_temp.empty:
        pos1 = ax1.get_position()
        pos2 = ax2.get_position()
        ax2.set_position([pos2.x0, pos1.y0, pos2.width, pos1.height])
    
    # Título general
    fig.suptitle(
        f"Atmospheric Profiles | Latitude: {lat_range[0]:.1f} to {lat_range[1]:.1f}°N | "
        f"Longitude: {lon_range[0]:.1f} to {lon_range[1]:.1f}°E | "
        f"LTST: {local_range[0]:.1f} to {local_range[1]:.1f} hrs",
        fontsize=18, y=1.02, fontweight = 'bold'
    )
    
    plt.tight_layout()

    # === Fijar límites de altitud de manera definitiva (resuelve el problema del autoescalado dado por twinx()) ===
    if not df_temp.empty:
        ax1b.set_autoscale_on(False)
        ax1b.set_ylim(alt_min, alt_max)
        ax2.set_autoscale_on(False)
        ax2.set_ylim(alt_min, alt_max)
    return fig

# --- Streamlit ---
st.title("Martian Atmospheric Profiles - MCS Data")

fecha_min = datetime.date(2006, 9, 1)  # MROM_2001 = Septiembre 2006
fecha_max = datetime.date(2030, 12, 31)  # Hasta diciembre 2030

fecha = st.date_input(
    "Select the observation date:",
    datetime.date(2009, 7, 25),
    min_value=fecha_min,
    max_value=fecha_max
)



if st.button("Find, load and process data"):
    url_dia = construir_url(fecha)
    st.write(f"Searching for DDR data in: {url_dia}")

    r = requests.head(url_dia)
    if r.status_code != 200:
        st.error("No DDR folder found for that date")
    else:
        archivos_tab = listar_tab_files_ddr(url_dia)
        if not archivos_tab:
            st.warning("No DDR files found for that date")
        else:
            carpeta_local = f"data/{fecha}"
            archivos_locales = descargar_archivos(archivos_tab, carpeta_local)
            st.success(f"{len(archivos_locales)} DDR files have been downloaded.")

            df_combinado = cargar_multiples_archivos(carpeta_local)
            if df_combinado.empty:
                st.error("Could not load valid data from the downloaded DDR files.")
            else:
                st.session_state.df_combinado = df_combinado
                st.success(f"Data loaded successfully: {len(df_combinado)} records")

# Mostrar controles interactivos si hay datos cargados
if 'df_combinado' in st.session_state and not st.session_state.df_combinado.empty:
    df_combinado = st.session_state.df_combinado
    
    st.subheader("Display Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        lat_min = st.slider("Minimum latitude (°N)", -90.0, 90.0, float(df_combinado['Lat'].min()), step=0.1, format="%.2f")
        lat_max = st.slider("Maximum latitude (°N)", -90.0, 90.0, float(df_combinado['Lat'].max()), step=0.1, format="%.2f")

    
    with col2:
        lon_min = st.slider("Minimum longitude (°E)", 0.0, 360.0, float(df_combinado['Lon'].min()), step=0.1, format="%.2f")
        lon_max = st.slider("Maximum longitude (°E)", 0.0, 360.0, float(df_combinado['Lon'].max()), step=0.1, format="%.2f")
    
    with col3:
        local_min = st.slider("LTST min (hrs)", 0.0, 24.0, 0.0, step=0.1)
        local_max = st.slider("LTST max (hrs)", 0.0, 24.0, 24.0, step=0.1)

    # Parametros de Mezcla
    st.sidebar.markdown("**Mixing ratio parameters**")
    Xvv_CO2_min = st.sidebar.number_input("Xvv_CO2", min_value=0.0, max_value=1.0, value=0.95, step=0.01, format="%.3f")
    #Xvv_CO2_max = st.sidebar.number_input("Xvv_CO2 max", min_value=0.0, max_value=2.0, value=1.0, step=0.01, format="%.3f")
    Xvv_CO2_max=1 # Esto no se grafica asi que lo dejamos en uno. Si quisieramos que fuese variable descomentamos la fila superior y comentamos esta. 
    Xvv_H2O_min = st.sidebar.number_input("Xvv_H2O min", min_value=0.0, max_value=1.0, value=1.0e-5, step=1e-6, format="%.1e")
    Xvv_H2O_max = st.sidebar.number_input("Xvv_H2O max", min_value=0.0, max_value=1.0, value=9.0e-5, step=1e-6, format="%.1e")



    # Filtrar datos según los controles
    df_filtrado = df_combinado[
        (df_combinado['Lat'].between(lat_min, lat_max)) &
        (df_combinado['Lon'].between(lon_min, lon_max)) &
        (df_combinado['LocalTime'].between(local_min, local_max))
    ]
    
    # Mostrar estadísticas
    st.write(f"**Data in selected range:** {len(df_filtrado)} records")
    st.write(f"**Altitude range:** {df_filtrado['Alt'].min():.1f} to {df_filtrado['Alt'].max():.1f} km")
    st.write(f"**Pressure range:** {df_filtrado['Pres'].min():.3f} to {df_filtrado['Pres'].max():.3f} Pa")
    
    # Crear y mostrar gráficas
    if st.button("Plot"):
        fig = crear_graficas(df_filtrado, (lat_min, lat_max), (lon_min, lon_max), (local_min, local_max))
        if fig:
            st.pyplot(fig)
            
            # Opción para descargar la figura
            buf = BytesIO()
            fig.savefig(buf, format="jpeg", dpi=300, bbox_inches='tight')
            st.download_button(
                label="Download image as JPEG",
                data=buf.getvalue(),
                file_name=f"perfil_mcs_{fecha}_lat{lat_min}-{lat_max}_lon{lon_min}-{lon_max}.jpeg",
                mime="image/jpeg"
            )

    
    # Mostrar datos en tabla (opcional)
    if st.checkbox("Display data"):
        st.dataframe(df_filtrado)