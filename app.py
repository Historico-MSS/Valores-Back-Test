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
st.set_page_config(page_title="Generador de Ilustraciones", page_icon="💼")

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

# --- CONSTANTES ---
FACTORES_COSTOS = {
    5: (0.2475, 0.0619), 6: (0.2970, 0.0743), 7: (0.3465, 0.0866), 8: (0.3960, 0.0990),
    9: (0.4455, 0.1114), 10: (0.4950, 0.1238), 11: (0.5445, 0.1361), 12: (0.5940, 0.1485),
    13: (0.6435, 0.1609), 14: (0.6930, 0.1733), 15: (0.7425, 0.1856), 16: (0.7920, 0.1980),
    17: (0.8415, 0.2104), 18: (0.8910, 0.2228), 19: (0.9405, 0.2351), 20: (0.9900, 0.2475),
}
LISTA_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# --- APP ---
st.title("Generador de Ilustraciones con Valores Históricos")
all_files = os.listdir()
csv_files = [f for f in all_files if f.endswith('.csv')]

with st.sidebar:
    st.header("Configuración")
    nombre_cliente = st.text_input("Nombre Cliente", value="Cliente Ejemplo")
    planes = {}
    
    for i in range(5, 21):
        for f in csv_files:
            if "MSS" in f and str(i) in f:
                if i < 10 and f"1{i}" in f: continue 
                planes[f"MSS - {i} Años"] = (f, i)
                break
    for f in csv_files:
        if "nico" in f.lower() or "unique" in f.lower():
            planes["MIS - Aporte Unico"] = (f, 0)
            break
            
    if not planes:
        st.error("🚨 No encuentro archivos CSV.")
        st.stop()
        
    plan_sel = st.selectbox("Selecciona Plan", list(planes.keys()))
    archivo_csv, plazo = planes[plan_sel]
    
    aportes_extra = [] 
    retiros_prog = [] 
    
    if plan_sel == "MIS - Aporte Unico":
        st.info("Plan de Inversión (Aporte Único + Extras)")
        monto_ini = st.number_input("Inversión Inicial (USD)", 10000, step=1000)
        freq_pago = "Único"
        c1, c2 = st.columns([1.5, 1.5])
        with c1: anio_ini = st.number_input("Año Inicio", 2000, 2024, 2015)
        with c2: 
            mes_n = st.selectbox("Mes Inicio", LISTA_MESES)
            mes_ini = LISTA_MESES.index(mes_n) + 1
            
        with st.expander("➕ Aportes Adicionales"):
            if st.checkbox("Habilitar aportes extra"):
                for i in range(4):
                    st.divider()
                    st.caption(f"Aporte #{i+1}")
                    c_m, c_a, c_me = st.columns([1.5, 1, 1.3])
                    with c_m: m_ex = st.number_input("USD", 0, step=1000, key=f"m{i}")
                    with c_a: a_ex = st.number_input("Año", anio_ini, 2025, anio_ini+1, key=f"a{i}")
                    with c_me: 
                        me_n = st.selectbox("Mes", LISTA_MESES, key=f"me{i}")
                        me_ex = LISTA_MESES.index(me_n) + 1
                    if m_ex > 0: aportes_extra.append({"monto": m_ex, "anio": a_ex, "mes": me_ex})
    else:
        st.info("Plan de Ahorro Regular")
        monto_ini = st.number_input("Monto Aporte (USD)", 500, step=50)
        freq_pago = st.selectbox("Frecuencia", ["Mensual", "Trimestral", "Semestral", "Anual"])
        mapa = {"Mensual": 1, "Trimestral": 3, "Semestral": 6, "Anual": 12}
        step_meses = mapa[freq_pago]
        anio_ini, mes_ini = None, None

    with st.expander("💸 Retiros Parciales"):
        if st.checkbox("Habilitar Retiros"):
            for i in range(3):
                st.divider()
                st.caption(f"Retiro #{i+1}")
                c_mr, c_ar, c_mer = st.columns([1.5, 1, 1.3])
                with c_mr: mr = st.number_input("USD", 0, step=1000, key=f"mr{i}")
                with c_ar: 
                    min_y = anio_ini if anio_ini else 2000
                    ar = st.number_input("Año", min_y, 2035, min_y+5, key=f"ar{i}")
                with c_mer: 
                    mer_n = st.selectbox("Mes", LISTA_MESES, key=f"mer{i}")
                    mer = LISTA_MESES.index(mer_n) + 1
                if mr > 0: retiros_prog.append({"monto": mr, "anio": ar, "mes": mer})

if st.button("Generar Ilustración", type="primary"):
    status = st.empty()
    try:
        status.info("⏳ Calculando...")
        df = pd.read_csv(archivo_csv)
        df.columns = df.columns.str.strip()
        
        def cln(x): return x.astype(str).str.replace('$','',regex=False).str.replace(',','',regex=False).str.strip()
        for c in ['Aporte', 'Valor Neto', 'Price']:
            if c in df.columns: df[c] = pd.to_numeric(cln(df[c]), errors='coerce').fillna(0)
            
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date')

        # --- SIMULACIÓN ---
        if plan_sel == "MIS - Aporte Unico":
            f_filt = pd.Timestamp(year=anio_ini, month=mes_ini, day=1)
            df = df[df['Date'] >= f_filt].copy().reset_index(drop=True)
            if df.empty: st.error("Sin datos fecha inicio"); st.stop()
            
            df['Year'] = df['Date'].dt.year
            l_vn, l_vr, l_ap, l_ret = [], [], [], []
            l_ap_acum = []
            
            cubetas = [{"monto": monto_ini, "saldo": 0, "edad": 0, "on": False, "ini": (anio_ini, mes_ini)}]
            for ex in aportes_extra:
                cubetas.append({"monto": ex["monto"], "saldo": 0, "edad": 0, "on": False, "ini": (ex["anio"], ex["mes"])})
                
            precios = df['Price'].values
            acum_aportado = 0
            
            for i in range(len(df)):
                dt = df['Date'].iloc[i]
                y, m = dt.year, dt.month
                
                ap_mes, vn_mes, vr_mes = 0, 0, 0
                ret_mes = sum(r['monto'] for r in retiros_prog if r['anio']==y and r['mes']==m)
                l_ret.append(ret_mes)
                
                saldo_previo_tot = sum(c["saldo"] for c in cubetas if c["on"])
                
                for c in cubetas:
                    if not c["on"]:
                        if y == c["ini"][0] and m == c["ini"][1]:
                            c["on"] = True
                            c["saldo"] = c["monto"]
                            ap_mes += c["monto"]
                            acum_aportado += c["monto"]
                            saldo_previo_tot += c["monto"]
                            
                    if c["on"]:
                        if c["edad"] > 0 and i > 0 and precios[i-1] > 0:
                            c["saldo"] *= (precios[i] / precios[i-1])
                            
                        if ret_mes > 0 and saldo_previo_tot > 0:
                            peso = c["saldo"] / saldo_previo_tot
                            c["saldo"] = max(0, c["saldo"] - (ret_mes * peso))
                            
                        deduc = (c["monto"] * 0.016) / 12
                        if c["edad"] < 60: c["saldo"] -=
