import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import os 
import traceback

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Ilustraciones", page_icon="💼")

# --- 2. SISTEMA DE CONTRASEÑA (test) ---
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
# CONSTANTES Y CONFIGURACIÓN
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

LISTA_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

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
    retiros_programados = [] 
    
    if plan_seleccionado == "MIS - Aporte Unico":
        st.info("Plan de Inversión (Aporte Único + Extras)")
        monto_input = st.number_input("Inversión Inicial (USD)", value=10000, step=1000)
        frecuencia_pago = "Único" 
        
        st.markdown("### 📅 Fecha de Inicio")
        # Ajustamos columnas para que el mes se vea bien
        col1, col2 = st.columns([1.5, 1.5])
        with col1: 
            anio_inicio = st.number_input("Año Inicio", min_value=2000, max_value=2024, value=2015)
        with col2: 
            mes_nombre = st.selectbox("Mes Inicio", LISTA_MESES)
            mes_inicio = LISTA_MESES.index(mes_nombre) + 1
            
        # --- APORTES ADICIONALES ---
        with st.expander("➕ Agregar Aportes Adicionales"):
            st.markdown("Programa inyecciones de capital futuras.")
            activar_extras = st.checkbox("Habilitar aportes extra")
            
            if activar_extras:
                for i in range(4): 
                    st.divider()
                    st.caption(f"Aporte Adicional #{i+1}")
                    # Nuevas proporciones para que el mes no se corte
                    c_monto, c_anio, c_mes = st.columns([1.5, 1, 1.3])
                    
                    with c_monto:
                        m_extra = st.number_input(f"Monto (USD)", value=0, step=1000, key=f"m{i}")
                    with c_anio:
                        a_extra = st.number_input(f"Año", min_value=anio_inicio, max_value=2025, value=anio_inicio+1, key=f"a{i}")
                    with c_mes:
                        me_nombre = st.selectbox(f"Mes", LISTA_MESES, key=f"me{i}")
                        mes_extra = LISTA_MESES.index(me_nombre) + 1
                    
                    if m_extra > 0:
                        aportes_extra_mis.append({
                            "monto": m_extra,
                            "anio": a_extra,
                            "mes": mes_extra
                        })
            
    else:
        st.info("Plan de Ahorro Regular")
        monto_input = st.number_input("Monto del Aporte (USD)", value=500, step=50)
        
        frecuencia_pago = st.selectbox("Frecuencia de Aporte", ["Mensual", "Trimestral", "Semestral", "Anual"])
        mapa_meses = {"Mensual": 1, "Trimestral": 3, "Semestral": 6, "Anual": 12}
        step_meses = mapa_meses[frecuencia_pago]
        
        anio_inicio, mes_inicio = None, None

    # --- SECCIÓN DE RETIROS (ARREGLADA) ---
    with st.expander("💸 Programar Retiros Parciales"):
        st.markdown("Retiros de capital (Sin penalización).")
        activar_retiros = st.checkbox("Habilitar Retiros")
        
        if activar_retiros:
            for i in range(3): 
                st.divider()
                st.caption(f"Retiro Programado #{i+1}")
                # Proporciones más anchas para el mes
                c_monto_r, c_anio_r, c_mes_r = st.columns([1.5, 1, 1.3])
                
                with c_monto_r:
                    m_retiro = st.number_input(f"Monto (USD)", value=0, step=1000, key=f"mr{i}")
                with c_anio_r:
                    val_min_ret = anio_inicio if anio_inicio else 2000
                    a_retiro = st.number_input(f"Año", min_value=val_min_ret, max_value=2035, value=val_min_ret+5, key=f"ar{i}")
                with c_mes_r:
                    mer_nombre = st.selectbox(f"Mes", LISTA_MESES, key=f"mer{i}")
                    mes_retiro = LISTA_MESES.index(mer_nombre) + 1
                
                if m_retiro > 0:
                    retiros_programados.append({
                        "monto": m_retiro,
                        "anio": a_retiro,
                        "mes": mes_retiro
                    })

# --- BOTÓN DE ACCIÓN ---
if st.button("Generar Ilustración", type="primary"):
    status = st.empty()
    
    try:
        status.info("⏳ Calculando flujos...")
        
        # 1. CARGA
        df = pd.read_csv(archivo_csv)
        df.columns = df.columns.str.strip()
        
        def limpiar(x):
            return x.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
            
        for col in ['Aporte', 'Valor Neto', 'Price']:
            if col in df.columns:
                df[col] = pd.to_numeric(limpiar(df[col]), errors='coerce').fillna(0)

        if 'Date' not in df.columns:
            st.error("El archivo no tiene columna 'Date'")
            st.stop()
            
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date')

        # 2. SIMULACIÓN
        if plan_seleccionado == "MIS - Aporte Unico":
            # --- MIS (SISTEMA DE CUBETAS) ---
            fecha_filtro = pd.Timestamp(year=anio_inicio, month=mes_inicio, day=1)
            df = df[df['Date'] >= fecha_filtro].copy().reset_index(drop=True)
            
            if df.empty: 
                st.error(f"No hay datos desde {mes_inicio}/{anio_inicio}")
                st.stop()
            
            df['Year'] = df['Date'].dt.year
            
            total_valor_neto = []
            total_valor_rescate = []
            total_aportes_acumulados = [] 
            flujo_aportes = [] 
            flujo_retiros = [] 
            
            cubetas = [{
                "monto_original": monto_input,
                "saldo_actual": 0, 
                "meses_activa": 0,
                "activa": False,
                "fecha_inicio": (anio_inicio, mes_inicio)
            }]
            
            for extra in aportes_extra_mis:
                cubetas.append({
                    "monto_original": extra["monto"],
                    "saldo_actual": 0,
                    "meses_activa": 0,
                    "activa": False,
                    "fecha_inicio": (extra["anio"], extra["mes"])
                })

            precios = df['Price'].values
            acumulado_aportado = 0
            
            for i in range(len(df)):
                fecha_actual = df['Date'].iloc[i]
                mes_actual = fecha_actual.month
                anio_actual = fecha_actual.year
                
                aporte_del_mes_total = 0
                valor_cuenta_mes_total = 0
                valor_rescate_mes_total = 0
                retiro_del_mes = 0
                
                # A. Retiros
                for r in retiros_programados:
                    if r['anio'] == anio_actual and r['mes'] == mes_actual:
                        retiro_del_mes += r['monto']
                
                flujo_retiros.append(retiro_del_mes)

                # B. Saldo Previo Total
                saldo_total_previo = 0
                for cubeta in cubetas:
                    if cubeta["activa"]: saldo_total_previo += cubeta["saldo_actual"]

                # C. Procesar Cubetas
                for cubeta in cubetas:
                    # Activar
                    if not cubeta["activa"]:
                        if anio_actual == cubeta["fecha_inicio"][0] and mes_actual == cubeta["fecha_inicio"][1]:
                            cubeta["activa"] = True
                            cubeta["saldo_actual"] = cubeta["monto_original"]
                            aporte_del_mes_total += cubeta["monto_original"]
                            acumulado_aportado += cubeta["monto_original"]
                            saldo_total_previo += cubeta["monto_original"]
                    
                    if cubeta["activa"]:
                        # 1. Rendimiento
                        if cubeta["meses_activa"] > 0 and i > 0 and precios[i-1] > 0:
                            rendimiento = precios[i] / precios[i-1]
                            cubeta["saldo_actual"] *= rendimiento
                        
                        # 2. Retiro Prorrateado
                        if retiro_del_mes > 0 and saldo_total_previo > 0:
                            peso_cubeta = cubeta["saldo_actual"] / saldo_total_previo
                            monto_a_quitar = retiro_del_mes * peso_cubeta
                            cubeta["saldo_actual"] = max(0, cubeta["saldo_actual"] - monto_a_quitar)

                        # 3. Costos
                        deduccion_establecimiento = (cubeta["monto_original"] * 0.016) / 12
                        
                        if cubeta["meses_activa"] < 60:
                            cubeta["saldo_actual"] -= deduccion_establecimiento
                        else:
                            cubeta["saldo_actual"] -= (cubeta["saldo_actual"] * (0.01/12))
                        
                        cubeta["saldo_actual"] = max(0, cubeta["saldo_actual"])

                        # 4. Rescate
                        if cubeta["meses_activa"] < 60:
                            meses_restantes = 60 - (cubeta["meses_activa"] + 1)
                            penalizacion = meses_restantes * deduccion_establecimiento
                            valor_rescate_cubeta = max(0, cubeta["saldo_actual"] - penalizacion)
                        else:
                            valor_rescate_cubeta = cubeta["saldo_actual"]
                            
                        valor_cuenta_mes_total += cubeta["saldo_actual"]
                        valor_rescate_mes_total += valor_rescate_cubeta
                        cubeta["meses_activa"] += 1

                flujo_aportes.append(aporte_del_mes_total)
                total_aportes_acumulados.append(acumulado_aportado)
                total_valor_neto.append(valor_cuenta_mes_total)
                total_valor_rescate.append(valor_rescate_mes_total)
            
            df['Aporte_Simulado'] = flujo_aportes
            df['Retiro_Simulado'] = flujo_retiros
            df['Aporte_Acumulado_Total'] = total_aportes_acumulados 
            df['Valor_Neto_Simulado'] = total_valor_neto
            df['Valor_Rescate_Simulado'] = total_valor_rescate

        else:
            # --- MSS (REGULAR CON FRECUENCIA) ---
            df['Year'] = df['Date'].dt.year
            
            pagos_al_anio = 12 / step_meses
            aporte_anual = monto_input * pagos_al_anio
            
            factor1, factor2 = FACTORES_COSTOS.get(plazo_anios, (0,0))
            costo_total_apertura = (aporte_anual * factor1) + (aporte_anual * factor2)
            
            meses_totales = plazo_anios * 12
            deduccion_mensual = costo_total_apertura / meses_totales
            
            saldos, rescates, aportes_sim = [], [], []
            flujo_retiros = []
            saldo_act = 0
            acumulado_aportado = 0
            precios = df['Price'].values
            
            for i in range(len(df)):
                fecha_actual = df['Date'].iloc[i]
                anio_actual = fecha_actual.year
                mes_actual = fecha_actual.month

                if i >= meses_totales: break
                
                monto_del_mes = 0
                if i % step_meses == 0:
                    monto_del_mes = monto_input
                
                aportes_sim.append(monto_del_mes)
                saldo_act += monto_del_mes
                acumulado_aportado += monto_del_mes
                
                if i > 0 and precios[i-1] > 0:
                    saldo_act *= (precios[i] / precios[i-1])
                
                # RETIRO
                retiro_del_mes = 0
                for r in retiros_programados:
                    if r['anio'] == anio_actual and r['mes'] == mes_actual:
                        retiro_del_mes += r['monto']
                
                flujo_retiros.append(retiro_del_mes)
                
                if retiro_del_mes > 0:
                    saldo_act = max(0, saldo_act - retiro_del_mes)

                saldo_act -= deduccion_mensual
                saldos.append(saldo_act)
                
                meses_restantes = meses_totales - (i + 1)
                penalizacion = meses_restantes * deduccion_mensual if meses_restantes > 0 else 0
                valor_rescate = max(0, saldo_act - penalizacion)
                rescates.append(valor_rescate)
            
            df = df.iloc[:len(saldos)].copy()
            df['Aporte_Simulado'] = aportes_sim
            df['Retiro_Simulado'] = flujo_retiros
            df['Aporte_Acumulado_Total'] = df['Aporte_Simulado'].cumsum()
            df['Valor_Neto_Simulado'] = saldos
            df['Valor_Rescate_Simulado'] = rescates

        # 3. DATOS TABLA
        status.info("⏳ Generando Informe...")
        
        datos_tabla = df.groupby('Year').agg({
            'Aporte_Simulado': 'sum', 
            'Retiro_Simulado': 'sum',
            'Valor_Neto_Simulado': 'last',
            'Valor_Rescate_Simulado': 'last',
            'Aporte_Acumulado_Total': 'last'
        }).reset_index()
        
        # Rendimiento
        datos_tabla['Saldo_Inicial'] = datos_tabla['Valor_Neto_Simulado'].shift(1).fillna(0)
        datos_tabla['Ganancia'] = datos_tabla['Valor_Neto_Simulado'] - datos_tabla['Saldo_Inicial'] - datos_tabla['Aporte_Simulado'] + datos_tabla['Retiro_Simulado']
        
        datos_tabla['Base_Calculo'] = (datos_tabla['Saldo_Inicial'] + datos_tabla['Aporte_Simulado']).replace(0, 1)
        datos_tabla['Rendimiento'] = (datos_tabla['Ganancia'] / datos_tabla['Base_Calculo']) * 100

        # 4. GRAFICAR
        fig = plt.figure(figsize=(11, 14))
        
        plt.suptitle(f'Plan: {plan_seleccionado}\nCliente: {nombre_cliente}', fontsize=18, weight='bold', y=0.98) 
        
        if plan_seleccionado == "MIS - Aporte Unico":
            num_aportes = 1 + len(aportes_extra_mis)
            sub_
