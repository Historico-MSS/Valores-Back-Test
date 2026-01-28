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
st.set_page_config(page_title="Generador v10", page_icon="💼")

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

if not check_password(): st.stop()

# --- DATOS ---
FACTORES = {
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
    
    if
