import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import os 
import traceback

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Generador v14", page_icon="💼")

def check_pass():
    def pass_entered():
        if st.session_state["password"] == "test": 
            st.session_state["p_ok"] = True
            del st.session_state["password"]
        else: st.session_state["p_ok"] = False
    if st.session_state.get("p_ok", False): return True
    st.title("🔒 Acceso Restringido")
    st.text_input("Contraseña:", type="password", on_change=pass_entered, key="password")
    return False

if not check_pass(): st.stop()

# --- DATOS ---
FACTS = {
    5:(0.2475,0.0619), 6:(0.297,0.0743), 7:(0.3465,0.0866), 8:(0.396,0.099),
    9:(0.4455,0.1114), 10:(0.495,0.1238), 11:(0.5445,0.1361), 12:(0.594,0.1485),
    13:(0.6435,0.1609), 14:(0.693,0.1733), 15:(0.7425,0.1856), 16:(0.792,0.198),
    17:(0.8415,0.2104), 18:(0.891,0.2228), 19:(0.9405,0.2351), 20:(0.99,0.2475)
}
LM = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

# --- APP ---
st.title("Generador de Ilustraciones con Valores Históricos")
files = [f for f in os.listdir() if f.endswith('.csv')]

with st.sidebar:
    st.header("Configuración")
    cliente = st.text_input("Cliente", "Cliente Ejemplo")
    planes = {}
    for i in range(5, 21):
        for f in files:
            if "MSS" in f and str(i) in f:
                if i<10 and f"1{i}" in f: continue
                planes[f"MSS - {i} Años"] = (f, i)
    for f in files:
        if "nico" in f.lower() or "unique" in f.lower(): planes["MIS - Aporte Unico"] = (f, 0)
    
    if not planes: st.error("Faltan CSVs"); st.stop()
    sel = st.selectbox("Plan", list(planes.keys()))
    csv, plazo = planes[sel]
    
    extras, retiros = [], []
    
    if sel == "MIS - Aporte Unico":
        st.info("Plan Inversión")
        monto = st.number_input("Inversión (USD)", 1000, 1000000, 10000, 1000)
        freq = "Único"
        c1, c2 = st.columns([1.5, 1.5])
        with c1: y_ini = st.number_input("Año Inicio", 2000, 2024, 2015)
        with c2: m_n = st.selectbox("Mes Inicio", LM); m_ini = LM.index(m_n)+1
        
        with st.expander("➕ Extras"):
            if st.checkbox("Activar Extras"):
                for i in range(4):
                    st.divider(); c1,c2,c3 = st.columns([1.5,1,1.3])
                    with c1: m_x = st.number_input(f"Monto {i+1}", 0, step=1000)
                    with c2: y_x = st.number_input(f"Año {i+1}", y_ini, 2025, y_ini+1)
                    with c3: mn_x = st.selectbox(f"Mes {i+1}", LM); m_x_idx = LM.index(mn_x)+1
                    if m_x > 0: extras.append({"m":m_x, "y":y_x, "mo":m_x_idx})
    else:
        st.info("Plan Ahorro")
        # MINIMO 150
        monto = st.number_input("Aporte (USD)", min_value=150, value=500, step=50)
        freq = st.selectbox("Frecuencia", ["Mensual", "Trimestral", "Semestral", "Anual"])
        step = {"Mensual":1, "Trimestral":3, "Semestral":6, "Anual":12}[freq]
        y_ini, m_ini = None, None

    with st.expander("💸 Retiros"):
        if st.checkbox("Activar Retiros"):
            for i in range(3):
                st.divider(); c1,c2,c3 = st.columns([1.5,1,1.3])
                with c1: mr = st.number_input(f"Retiro {i+1}", 0, step=1000)
                with c2: 
                    min_y = y_ini if y_ini else 2000
                    yr = st.number_input(f"Año {i+1}", min_y, 2035, min_y+5)
                with c3: mnr = st.selectbox(f"Mes {i+1}", LM); mr_idx = LM.index(mnr)+1
                if mr > 0: retiros.append({"m":mr, "y":yr, "mo":mr_idx})

if st.button("Generar Ilustración", type="primary"):
    st.info("⏳ Procesando...")
    try:
        df = pd.read_csv(csv)
        df.columns = df.columns.str.strip()
        def cln(x): return x.astype(str).str.replace('$','',regex=False).str.replace(',','',regex=False).str.strip()
        for c in ['Aporte','Valor Neto','Price']: 
            if
