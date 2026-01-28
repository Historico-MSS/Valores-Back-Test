import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import os 
import traceback

# --- 1. CONFIGURACIÓN DE PÁGINA (TÍTULO NUEVO) ---
st.set_page_config(page_title="Generador de Ilustraciones con Valores Históricos", page_icon="💼")

# --- 2. SISTEMA DE CONTRASEÑA (NUEVO PASSWORD: test) ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "test": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Acceso Restringido")
    st.text_input("Contraseña:", type="password", on_change=password_entered, key="password")
    return False

if not check_password():
    st.stop()

# =========================================================
# 🏦 FACTORES DE COSTOS (EU) - SOLO PARA MSS
# =========================================================
FACTORES_COSTOS = {
    5:  (0.2475, 0.0619),
    6:  (0.2970, 0.0743),
    7:  (0.3465, 0.0866),
    8:  (0.3960, 0.0990),
    9:  (0.4455, 0.1114),
    10: (0.4950, 0.1238),
    11: (0.5445, 0.1361),
    12: (0.5940, 0.1485),
    13: (0.6435, 0.1609),
    14: (0.6930, 0.1733),
    15: (0.7425, 0.1856),
    16: (0.7920, 0.1980),
    17: (0.8415, 0.2104),
    18: (0.8910, 0.2228),
    19: (0.9405, 0.2351),
    20: (0.9900, 0.2475),
}

# =========================================================
# 🚀 APLICACIÓN PRINCIPAL
# =========================================================

st.title("Generador de Ilustraciones con Valores Históricos")

# --- DETECTIVE DE ARCHIVOS ---
all_files = os.listdir()
csv_files = [f for f in all_files if f.endswith('.csv')]

with st.sidebar:
    st.header("Configuración")
    nombre_cliente = st.text_input("Nombre Cliente", value="Cliente Ejemplo")
    
    planes = {}
    
    # 1. Regulares (MSS)
    for i in range(5, 21):
        for filename in csv_files:
            if "MSS" in filename and str(i) in filename:
                if i < 10 and f"1{i}" in filename: continue 
                planes[f"MSS - {i} Años"] = (filename, i)
                break
            
    # 2. Aporte Único (MIS)
    for filename in csv_files:
        if "nico" in filename.lower() or "unique" in filename.lower():
            planes["MIS - Aporte Unico"] = (filename, 0)
            break
    
    if not planes:
        st.error("🚨 ERROR: No encuentro archivos CSV.")
        st.stop()
    
    plan_seleccionado = st.selectbox("Selecciona Plan", list(planes.keys()))
    archivo_csv, plazo_anios = planes[plan_seleccionado]
    
    # --- INPUTS DINÁMICOS ---
    aportes_extra_mis = [] 
    
    if plan_seleccionado == "MIS - Aporte Unico":
        st.info("Plan de Inversión (Aporte Único + Extras)")
        monto_input = st.number_input("Inversión Inicial (USD)", value=10000, step=1000)
        frecuencia_pago = "Único" 
        
        st.markdown("### 📅 Fecha de Inicio")
        col1, col2 = st.columns(2)
        with col1: 
            anio_inicio = st.number_input("Año Inicio", min_value=2000, max_value=2024, value=2015)
        with col2: 
            mes_inicio = st.selectbox("Mes Inicio", range(1, 13))
            
        # --- APORTES ADICIONALES ---
        with st.expander("➕ Agregar Aportes Adicionales"):
            st.markdown("Programa inyecciones de capital futuras.")
            activar_extras = st.checkbox("Habilitar aportes extra")
            
            if activar_extras:
                for i in range(4): 
                    st.markdown(f"**Aporte Adicional #{i+1}**")
                    c_monto, c_anio, c_mes = st.columns([2, 1.5, 1])
                    with c_monto:
                        m_extra = st.number_input(f"Monto #{i+1}", value=0, step=1000, key=f"m{i}")
                    with c_anio:
                        a_extra = st.number_input(f"Año #{i+1}", min_value=anio_inicio, max_value=2025, value=anio_inicio+1, key=f"a{i}")
                    with c_mes:
                        mes_extra = st.selectbox(f"Mes #{i+1}", range(1, 13), key=f"me{i}")
