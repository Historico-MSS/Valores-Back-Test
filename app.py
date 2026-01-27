import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import os 

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Ilustraciones", page_icon="📈")

# --- 🔐 SISTEMA DE CONTRASEÑA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "dominion2025": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Acceso Restringido")
    st.text_input("Contraseña:", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Contraseña incorrecta.")
    return False

if not check_password():
    st.stop()

# =========================================================
# 🚀 APLICACIÓN PRINCIPAL
# =========================================================

st.title("💼 Generador de Ilustraciones Financieras")

# --- DETECTIVE DE ARCHIVOS ---
all_files = os.listdir()
csv_files = [f for f in all_files if f.endswith('.csv')]

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Configuración del Plan")
    nombre_cliente = st.text_input("Nombre del Cliente", value="Cliente Ejemplo")
    
    planes = {}
    
    # 1. BUSCAR ARCHIVOS MSS (5-20 años)
    for i in range(5, 21):
        for filename in csv_files:
            if "MSS" in filename and str(i) in filename:
                # Evitar confusiones (ej: que 8 no coincida con 18)
                if i < 10 and f"1{i}" in filename:
                    continue 
                planes[f"MSS - {i} Años"] = filename
                break
            
    # 2. Plan Aporte Único
    for filename in csv_files:
        if "nico" in filename.lower() or "unique" in filename.lower():
            planes["MIS - Aporte Unico"] = filename
            break
    
    if not planes:
        st.error("🚨 NO SE ENCONTRARON ARCHIVOS CSV.")
        st.warning(f"Archivos en la carpeta: {all_files}")
        st.stop()
    
    plan_seleccionado = st.selectbox("Selecciona el Plan", list(planes.keys()))
    archivo_csv = planes[plan_seleccionado]
    st.caption(f"📂 Archivo: `{archivo_csv}`")

    # --- INPUTS DINÁMICOS ---
    if plan_seleccionado == "MIS - Aporte Unico":
        st.info("Configuración de Inversión Única")
        monto_input = st.number_input("Monto de Inversión (USD)", min_value=1000, value=10000, step=1000)
        
        st.markdown("### 📅 Fecha de Inicio")
        col1, col2 = st.columns(2)
        with col1:
            anio_inicio = st.number_input("Año", min_value=2000, max_value=2024, value=2015)
        with col2:
            mes_inicio = st.selectbox("Mes", range(1, 13), index=0)
            
    else:
        st.info("Configuración de Ahorro Regular")
        monto_input = st.number_input("Aporte Mensual (USD)", min_value=100, value=500, step=50)
        anio_inicio = None
        mes_inicio = None

    if st.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()

# --- FUNCIONES DE PROCESAMIENTO ---

def limpiar_moneda(serie):
    return serie.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()

def procesar_datos(archivo, monto_usuario, plan_nombre, anio_start, mes_start):
    try:
        df = pd.read_csv(archivo)
        df.columns = df.columns.str.strip()
        
        for col in ['Aporte', 'Valor Neto', 'Price']:
            if col in df.columns:
                df[col] = pd.to_numeric(limpiar_moneda(df[col]), errors='coerce').fillna(0)

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Date'])
            df = df.sort_values('Date')
        else:
            return None
        
        # CASO A: MIS - APORTE UNICO
        if plan_nombre == "MIS - Aporte Unico":
            fecha_filtro = pd.Timestamp(year=anio_start, month=mes_start, day=1)
            df = df[df['Date'] >= fecha_filtro].copy()
            if df.empty: return None
            
            df = df.reset_index(drop=True)
            df['Year'] = df['Date'].dt.year
            
            saldos = []
            aportes_sim = []
            saldo_actual = monto_usuario
            precios = df['Price'].values
            tasa_costo_mensual = 0.01 / 12 
            
            for i in range(len(df)):
                if i == 0:
                    aportes_sim.append(monto_usuario)
                    saldos.append(saldo_actual)
                else:
                    aportes_sim.append(0)
                    if precios[i-1] > 0:
                        rendimiento = precios[i] / precios[i-1]
                        saldo_actual = saldo_actual * rendimiento
                    
                    if i >= 60:
                        deduccion = saldo_actual * tasa_costo_mensual
                        saldo_actual = saldo_actual - deduccion
                    saldos.append(saldo_actual)
            
            df['Aporte_Simulado'] = aportes_sim
            df['Valor_Neto_Simulado'] = saldos

        # CASO B: PLANES REGULARES
        else:
            df['Year'] = df['Date'].dt.year
            df_aportes = df[df['Aporte'] > 0]
            aporte_base = df_aportes['Aporte'].iloc[0] if not df_aportes.empty else 500
            
            factor = monto_usuario / aporte_base
            df['Aporte_Simulado'] = df['Aporte'] * factor
            df['Valor_Neto_Simulado'] = df['Valor Neto'] * factor
        
        return df

    except Exception as e:
        return None

# --- GENERACIÓN DEL REPORTE ---
if st.button("Generar Ilustración", type="primary"):
    with st.spinner('Calculando rendimientos...'):
        df = procesar_datos(archivo_csv, monto_input, plan_seleccionado, anio_inicio, mes_inicio)
        
        if df is not None:
            # 1. Preparar Datos
            datos_grafico = df.copy()
            datos_grafico['Aporte Acumulado'] = datos_grafico['Aporte_Simulado'].cumsum()
            
            datos_tabla = df.groupby('Year').agg({
                'Aporte_Simulado': 'sum', 
                'Valor_Neto_Simulado': 'last'
            }).reset_index()
            datos_tabla['Total Aporte'] = datos_tabla['Aporte_Simulado'].cumsum()

            # --- CÁ
