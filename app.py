import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io, os, traceback

st.set_page_config(page_title="Generador v15", page_icon="💼")

def check_pass():
    if st.session_state.get("p_ok", False): return True
    def v():
        if st.session_state["pw"]=="test": st.session_state["p_ok"]=True
        else: st.session_state["p_ok"]=False
    st.title("🔒 Acceso"); st.text_input("Password:", type="password", key="pw", on_change=v)
    return False

if not check_pass(): st.stop()

# --- DATA ---
FACTS={5:(0.2475,0.0619),6:(0.297,0.0743),7:(0.3465,0.0866),8:(0.396,0.099),9:(0.4455,0.1114),
10:(0.495,0.1238),11:(0.5445,0.1361),12:(0.594,0.1485),13:(0.6435,0.1609),14:(0.693,0.1733),
15:(0.7425,0.1856),16:(0.792,0.198),17:(0.8415,0.2104),18:(0.891,0.2228),19:(0.9405,0.2351),20:(0.99,0.2475)}
LM=["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

# --- UI ---
st.title("Generador de Ilustraciones")
files=[f for f in os.listdir() if f.endswith('.csv')]
with st.sidebar:
    st.header("Config"); cli=st.text_input("Cliente","Ejemplo")
    plan_map={}
    for i in range(5,21):
        for f in files:
            if "MSS" in f and str(i) in f:
                if i<10 and f"1{i}" in f: continue
                plan_map[f"MSS - {i} Años"]=(f,i)
    for f in files:
        if "nico" in f.lower() or "unique" in f.lower(): plan_map["MIS - Aporte Unico"]=(f,0)
    
    if not plan_map: st.error("No CSV"); st.stop()
    sel=st.selectbox("Plan",list(plan_map.keys())); csv,plazo=plan_map[sel]
    x_in, r_in=[],[]

    if sel=="MIS - Aporte Unico":
        st.info("Plan Inversión")
        monto=st.number_input("Inversión",1000,step=1000,value=10000); freq="Único"
        c1,c2=st.columns(2); y_ini=c1.number_input("Año",2000,2025,2015)
        m_n=c2.selectbox("Mes",LM); m_ini=LM.index(m_n)+1
        if st.checkbox("Extras"):
            for i in range(4):
                st.divider(); c1,c2,c3=st.columns([1.5,1,1.3])
                mx=c1.number_input(f"M{i+1}",0,step=1000)
                yx=c2.number_input(f"A{i+1}",y_ini,2030,y_ini+1)
                mnx=c3.selectbox(f"Me{i+1}",LM); mix=LM.index(mnx)+1
                if mx>0: x_in.append({"m":mx,"y":yx,"mo":mix})
    else:
        st.info("Plan Ahorro")
        # MINIMO 150
        monto=st.number_input("Aporte",min_value=150,value=500,step=50)
        freq=st.selectbox("Frecuencia",["Mensual","Trimestral","Semestral","Anual"])
        step={"Mensual":1,"Trimestral":3,"Semestral":6,"Anual":12}[freq]; y_ini,m_ini=None,None

    if st.checkbox("Retiros"):
        for i in range(3):
            st.divider(); c1,c2,c3=st.columns([1.5,1,1.3])
            mr=c1.number_input(f"R{i+1}",0,step=1000)
            yr=c2.number_input(f"Yr{i+1}",2000,2040,2020)
            mnr=c3.selectbox(f"Mr{i+1}",LM); mri=LM.index(mnr)+1
            if mr>0: r_in.append({"m":mr,"y":yr,"mo":mri})

if st.button("Generar"):
    try:
        df=pd.read_csv(csv); df.columns=df.columns.str.strip()
        for c in ['Aporte','Valor Neto','Price']:
            if c in df.columns:
                df[c]=pd.to_numeric(
