import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import os 
import traceback

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador v16", page_icon="💼")

# --- PASSWORD ---
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

# --- DATOS Y CONSTANTES ---
FACTORES_COSTOS = {
    5: (0.2475, 0.0619), 6: (0.2970, 0.0743), 7: (0.3465, 0.0866), 8: (0.3960, 0.0990),
    9: (0.4455, 0.1114), 10: (0.4950, 0.1238), 11: (0.5445, 0.1361), 12: (0.5940, 0.1485),
    13: (0.6435, 0.1609), 14: (0.6930, 0.1733), 15: (0.7425, 0.1856), 16: (0.7920, 0.1980),
    17: (0.8415, 0.2104), 18: (0.8910, 0.2228), 19: (0.9405, 0.2351), 20: (0.9900, 0.2475)
}

LISTA_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# --- INTERFAZ PRINCIPAL ---
st.title("Generador de Ilustraciones con Valores Históricos")

# Detectar archivos CSV
archivos = [f for f in os.listdir() if f.endswith('.csv')]

with st.sidebar:
    st.header("Configuración")
    nombre_cliente = st.text_input("Nombre Cliente", value="Cliente Ejemplo")
    
    # Mapeo de planes
    planes_disponibles = {}
    for i in range(5, 21):
        for f in archivos:
            if "MSS" in f and str(i) in f:
                if i < 10 and f"1{i}" in f: continue 
                planes_disponibles[f"MSS - {i} Años"] = (f, i)
    
    for f in archivos:
        if "nico" in f.lower() or "unique" in f.lower():
            planes_disponibles["MIS - Aporte Unico"] = (f, 0)
    
    if not planes_disponibles:
        st.error("🚨 No se encontraron archivos CSV.")
        st.stop()
        
    seleccion = st.selectbox("Selecciona Plan", list(planes_disponibles.keys()))
    archivo_csv, plazo_anios = planes_disponibles[seleccion]
    
    # Variables de entrada
    aportes_extra = [] 
    retiros_programados = [] 
    
    if seleccion == "MIS - Aporte Unico":
        st.info("Plan de Inversión")
        monto_input = st.number_input("Inversión Inicial (USD)", min_value=1000, value=10000, step=1000)
        frecuencia_pago = "Único"
        
        col1, col2 = st.columns(2)
        with col1: 
            anio_inicio = st.number_input("Año Inicio", min_value=2000, max_value=2024, value=2015)
        with col2: 
            mes_txt = st.selectbox("Mes Inicio", LISTA_MESES)
            mes_inicio = LISTA_MESES.index(mes_txt) + 1
            
        with st.expander("➕ Aportes Adicionales"):
            if st.checkbox("Habilitar Aportes Extra"):
                for i in range(4):
                    st.divider()
                    c_m, c_a, c_me = st.columns([1.5, 1, 1.3])
                    with c_m: m_x = st.number_input(f"Monto {i+1}", 0, step=1000)
                    with c_a: a_x = st.number_input(f"Año {i+1}", anio_inicio, 2025, anio_inicio+1)
                    with c_me: 
                        me_x_txt = st.selectbox(f"Mes {i+1}", LISTA_MESES, key=f"me{i}")
                        me_x = LISTA_MESES.index(me_x_txt) + 1
                    
                    if m_x > 0:
                        aportes_extra.append({"monto": m_x, "anio": a_x, "mes": me_x})
    
    else:
        st.info("Plan de Ahorro")
        # --- AQUI EL MINIMO 150 ---
        monto_input = st.number_input("Aporte (USD)", min_value=150, value=500, step=50)
        frecuencia_pago = st.selectbox("Frecuencia", ["Mensual", "Trimestral", "Semestral", "Anual"])
        mapa_pasos = {"Mensual": 1, "Trimestral": 3, "Semestral": 6, "Anual": 12}
        step_meses = mapa_pasos[frecuencia_pago]
        anio_inicio, mes_inicio = None, None

    with st.expander("💸 Retiros Parciales"):
        if st.checkbox("Habilitar Retiros"):
            for i in range(3):
                st.divider()
                c_mr, c_ar, c_mer = st.columns([1.5, 1, 1.3])
                with c_mr: m_r = st.number_input(f"Retiro {i+1}", 0, step=1000)
                with c_ar: 
                    min_y = anio_inicio if anio_inicio else 2000
                    a_r = st.number_input(f"Año {i+1}", min_y, 2035, min_y+5)
                with c_mer: 
                    mer_txt = st.selectbox(f"Mes {i+1}", LISTA_MESES, key=f"mr{i}")
                    me_r = LISTA_MESES.index(mer_txt) + 1
                
                if m_r > 0:
                    retiros_programados.append({"monto": m_r, "anio": a_r, "mes": me_r})

# --- LÓGICA DE CÁLCULO ---
if st.button("Generar Ilustración", type="primary"):
    status = st.empty()
    try:
        status.info("⏳ Procesando datos...")
        
        # Carga y limpieza segura
        df = pd.read_csv(archivo_csv)
        df.columns = df.columns.str.strip()
        
        # Limpieza paso a paso para evitar errores de linea larga
        for col in ['Aporte', 'Valor Neto', 'Price']:
            if col in df.columns:
                # 1. Convertir a string
                serie_limpia = df[col].astype(str)
                # 2. Quitar simbolo $
                serie_limpia = serie_limpia.str.replace('$', '', regex=False)
                # 3. Quitar comas
                serie_limpia = serie_limpia.str.replace(',', '', regex=False)
                # 4. Convertir a numero
                df[col] = pd.to_numeric(serie_limpia, errors='coerce').fillna(0)

        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date')

        # --- SIMULACIÓN ---
        if seleccion == "MIS - Aporte Unico":
            fecha_filtro = pd.Timestamp(year=anio_inicio, month=mes_inicio, day=1)
            df = df[df['Date'] >= fecha_filtro].copy().reset_index(drop=True)
            
            if df.empty:
                st.error("No hay datos históricos para la fecha seleccionada.")
                st.stop()
            
            df['Year'] = df['Date'].dt.year
            
            # Listas de resultados
            lista_vn, lista_vr, lista_aportes_acum, lista_retiros = [], [], [], []
            
            # Inicializar cubetas
            cubetas = [{"monto": monto_input, "saldo": 0, "edad": 0, "activa": False, "ini": (anio_inicio, mes_inicio)}]
            for extra in aportes_extra:
                cubetas.append({"monto": extra["monto"], "saldo": 0, "edad": 0, "activa": False, "ini": (extra["anio"], extra["mes"])})
            
            precios = df['Price'].values
            acumulado_aportes = 0
            
            for i in range(len(df)):
                fecha_act = df['Date'].iloc[i]
                anio_act, mes_act = fecha_act.year, fecha_act.month
                
                # Calcular Retiros del mes
                retiro_mes = 0
                for r in retiros_programados:
                    if r["anio"] == anio_act and r["mes"] == mes_act:
                        retiro_mes += r["monto"]
                lista_retiros.append(retiro_mes)
                
                # Calcular saldo total previo (para prorratear retiros)
                saldo_total_previo = sum(c["saldo"] for c in cubetas if c["activa"])
                
                vn_mes_total = 0
                vr_mes_total = 0
                
                for c in cubetas:
                    # Activar cubeta si toca
                    if not c["activa"]:
                        if anio_act == c["ini"][0] and mes_act == c["ini"][1]:
                            c["activa"] = True
                            c["saldo"] = c["monto"]
                            acumulado_aportes += c["monto"]
                            saldo_total_previo += c["monto"]
                    
                    if c["activa"]:
                        # 1. Rendimiento
                        if c["edad"] > 0 and i > 0 and precios[i-1] > 0:
                            rendimiento = precios[i] / precios[i-1]
                            c["saldo"] *= rendimiento
                        
                        # 2. Retiro Prorrateado
                        if retiro_mes > 0 and saldo_total_previo > 0:
                            peso = c["saldo"] / saldo_total_previo
                            deduccion_retiro = retiro_mes * peso
                            c["saldo"] = max(0, c["saldo"] - deduccion_retiro)
                        
                        # 3. Costos
                        costo_establecimiento = (c["monto"] * 0.016) / 12
                        if c["edad"] < 60:
                            c["saldo"] -= costo_establecimiento
                        else:
                            c["saldo"] -= (c["saldo"] * (0.01 / 12)) # Costo Admin
                        
                        c["saldo"] = max(0, c["saldo"])
                        
                        # 4. Rescate
                        penalizacion = 0
                        if c["edad"] < 60:
                            meses_restantes = 60 - (c["edad"] + 1)
                            penalizacion = meses_restantes * costo_establecimiento
                        
                        vr_cubeta = max(0, c["saldo"] - penalizacion)
                        
                        vn_mes_total += c["saldo"]
                        vr_mes_total += vr_cubeta
                        c["edad"] += 1
                
                lista_vn.append(vn_mes_total)
                lista_vr.append(vr_mes_total)
                lista_aportes_acum.append(acumulado_aportes)
            
            df['Aporte_Acum'] = lista_aportes_acum
            df['Valor_Cuenta'] = lista_vn
            df['Valor_Rescate'] = lista_vr
            df['Retiro'] = lista_retiros

        else: # Lógica MSS
            df['Year'] = df['Date'].dt.year
            
            pagos_anio = 12 / step_meses
            aporte_anual = monto_input * pagos_anio
            
            factor1, factor2 = FACTORES_COSTOS.get(plazo_anios, (0, 0))
            costo_total_apertura = (aporte_anual * factor1) + (aporte_anual * factor2)
            meses_totales = plazo_anios * 12
            deduccion_mensual = costo_total_apertura / meses_totales
            
            lista_vn, lista_vr, lista_aportes_acum, lista_retiros = [], [], [], []
            saldo_actual = 0
            aporte_acumulado = 0
            precios = df['Price'].values
            
            for i in range(len(df)):
                fecha_act = df['Date'].iloc[i]
                if i >= meses_totales: break
                
                # Aporte
                if i % step_meses == 0:
                    saldo_actual += monto_input
                    aporte_acumulado += monto_input
                
                # Rendimiento
                if i > 0 and precios[i-1] > 0:
                    rendimiento = precios[i] / precios[i-1]
                    saldo_actual *= rendimiento
                
                # Retiro
                retiro_mes = 0
                for r in retiros_programados:
                    if r["anio"] == fecha_act.year and r["mes"] == fecha_act.month:
                        retiro_mes += r["monto"]
                lista_retiros.append(retiro_mes)
                
                if retiro_mes > 0:
                    saldo_actual = max(0, saldo_actual - retiro_mes)
                
                # Costos
                saldo_actual -= deduccion_mensual
                lista_vn.append(saldo_actual)
                
                # Rescate
                meses_restantes = meses_totales - (i + 1)
                penalizacion = 0
                if meses_restantes > 0:
                    penalizacion = meses_restantes * deduccion_mensual
                
                lista_vr.append(max(0, saldo_actual - penalizacion))
                lista_aportes_acum.append(aporte_acumulado)
            
            df = df.iloc[:len(lista_vn)].copy()
            df['Aporte_Acum'] = lista_aportes_acum
            df['Valor_Cuenta'] = lista_vn
            df['Valor_Rescate'] = lista_vr
            df['Retiro'] = lista_retiros

        # --- GENERACIÓN DE REPORTE ---
        resumen = df.groupby('Year').agg({
            'Aporte_Acum': 'last',
            'Valor_Cuenta': 'last',
            'Valor_Rescate': 'last',
            'Retiro': 'sum'
        }).reset_index()
        
        # Cálculo Rendimiento
        resumen['Saldo_Inicial'] = resumen['Valor_Cuenta'].shift(1).fillna(0)
        resumen['Aporte_Nuevo'] = resumen['Aporte_Acum'] - resumen['Aporte_Acum'].shift(1).fillna(0)
        
        # Ganancia = Final - Inicial - Aportes + Retiros
        resumen['Ganancia'] = resumen['Valor_Cuenta'] - resumen['Saldo_Inicial'] - resumen['Aporte_Nuevo'] + resumen['Retiro']
        resumen['Base_Calculo'] = (resumen['Saldo_Inicial'] + resumen['Aporte_Nuevo']).replace(0, 1)
        resumen['Rendimiento'] = (resumen['Ganancia'] / resumen['Base_Calculo']) * 100

        # --- GRÁFICO ---
        fig = plt.figure(figsize=(11, 14))
        plt.suptitle(f'Plan: {seleccion}\nCliente: {nombre_cliente}', fontsize=18, weight='bold', y=0.98)
        
        subtitulo = f"Estrategia ({1+len(aportes_extra)} Aportes)" if seleccion.startswith("MIS") else f"Aporte {frecuencia_pago}: ${monto_input:,.0f}"
        plt.figtext(0.5, 0.925, subtitulo, ha="center", fontsize=14, color='#555')
        
        inv_total = resumen['Aporte_Acum'].iloc[-1]
        ret_total = resumen['Retiro'].sum()
        val_final = resumen['Valor_Cuenta'].iloc[-1]
        val_rescate_final = resumen['Valor_Rescate'].iloc[-1]
        
        if ret_total > 0:
            texto_resumen = f"Inv. Total: ${inv_total:,.0f} | Retiros: ${ret_total:,.0f} | Valor Cuenta: ${val_final:,.0f}"
        else:
            texto_resumen = f"Inv. Total: ${inv_total:,.0f} | Valor Cuenta: ${val_final:,.0f} | Valor Rescate: ${val_rescate_final:,.0f}"
            
        plt.figtext(0.5, 0.88, texto_resumen, ha="center", fontsize=11, weight='bold', bbox=dict(facecolor='#f0f8ff', edgecolor='blue'))

        ax = plt.subplot2grid((10, 1), (1, 0), rowspan=4)
        
        # COLORES DEFINITIVOS
        # 1. Aporte: Verde Punteado
        ax.plot(df['Date'], df['Aporte_Acum'], color='#2ca02c', ls='--', label="Capital Invertido", alpha=0.9, lw=2)
        # 2. Rescate: Gris Punteado
        ax.plot(df['Date'], df['Valor_Rescate'], color='#808080', ls='--', label="Valor Rescate", alpha=0.9, lw=2)
        # 3. Cuenta: Azul Solido
        ax.plot(df['Date'], df['Valor_Cuenta'], color='#004c99', lw=2.5, label="Valor Cuenta")
        
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))

        # --- TABLA ---
        ax_tabla = plt.subplot2grid((10, 1), (6, 0), rowspan=4)
        ax_tabla.axis('off')
        
        filas = [['Año', 'Aporte Total', 'Retiro', 'Valor Cuenta', 'Valor Rescate', '% Rend']]
        
        for _, r in resumen.iterrows():
            txt_retiro = f"${r['Retiro']:,.0f}" if r['Retiro'] > 0 else "-"
            filas.append([
                str(int(r['Year'])), 
                f"${r['Aporte_Acum']:,.0f}", 
                txt_retiro,
                f"${r['Valor_Cuenta']:,.0f}", 
                f"${r['Valor_Rescate']:,.0f}", 
                f"{r['Rendimiento']:+.1f}%"
            ])
            
        tabla = ax_tabla.table(cellText=filas, loc='center', cellLoc='center')
        tabla.scale(1, 1.35)
        tabla.auto_set_font_size(False)
        tabla.set_fontsize(8)
        
        for (fila, col), celda in tabla.get_celld().items():
            if fila == 0: 
                celda.set_facecolor('#40466e')
                celda.set_text_props(color='white', weight='bold')
            elif fila % 2 == 0: 
                celda.set_facecolor('#f2f2f2')
            
            # Color Rendimiento (Col 5)
            if col == 5 and fila > 0:
                texto = celda.get_text().get_text()
                color_texto = 'green' if '+' in texto else 'black'
                celda.set_text_props(color=color_texto, weight='bold')
            
            # Color Retiro (Col 2)
            if col == 2 and fila > 0 and celda.get_text().get_text() != "-":
                celda.set_text_props(color='#d62728', weight='bold')
            
            # Color Rescate (Col 4) - ALERTA ORO
            if col == 4 and fila > 0:
                val_rescate = float(celda.get_text().get_text().replace('$','').replace(',',''))
                # Comparamos con Aporte Total (Columna 1)
                val_inversion = float(filas[fila][1].replace('$','').replace(',',''))
                
                # Si Rescate es MENOR que lo Invertido -> AMARILLO ORO
                if val_rescate < val_inversion:
                    celda.set_text_props(color='#D4AC0D', weight='bold')

        plt.tight_layout(rect=[0, 0.03, 1, 0.86])
        st.pyplot(fig)
        
        # Descarga
        buffer = io.BytesIO()
        plt.savefig(buffer, format='pdf')
        buffer.seek(0)
        st.download_button("📥 Descargar PDF", buffer, f"Ilustracion_{nombre_cliente}.pdf", "application/pdf")
        status.success("✅ ¡Ilustración Generada!")

    except Exception as e:
        status.error("❌ Ocurrió un error")
        st.write(traceback.format_exc())
