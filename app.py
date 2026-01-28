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
st.set_page_config(page_title="Generador de Ilustraciones", page_icon="💰")

# --- 🔐 SISTEMA DE CONTRASEÑA ---
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

st.title("💼 Generador de Ilustraciones (Aportes Múltiples)")

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
    aportes_extra_mis = [] # Lista para guardar los aportes adicionales
    
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
            
        # --- APORTES ADICIONALES (EXPANDER) ---
        with st.expander("➕ Agregar Aportes Adicionales (Opcional)"):
            st.markdown("Programa inyecciones de capital futuras.")
            activar_extras = st.checkbox("Habilitar aportes extra")
            
            if activar_extras:
                for i in range(4): # Hasta 4 aportes extra
                    st.markdown(f"**Aporte Adicional #{i+1}**")
                    c_monto, c_anio, c_mes = st.columns([2, 1.5, 1])
                    with c_monto:
                        m_extra = st.number_input(f"Monto #{i+1}", value=0, step=1000, key=f"m{i}")
                    with c_anio:
                        a_extra = st.number_input(f"Año #{i+1}", min_value=anio_inicio, max_value=2025, value=anio_inicio+1, key=f"a{i}")
                    with c_mes:
                        mes_extra = st.selectbox(f"Mes #{i+1}", range(1, 13), key=f"me{i}")
                    
                    if m_extra > 0:
                        aportes_extra_mis.append({
                            "monto": m_extra,
                            "anio": a_extra,
                            "mes": mes_extra
                        })
            
    else:
        st.info("Plan de Ahorro Regular")
        monto_input = st.number_input("Monto del Aporte (USD)", value=500, step=50)
        
        # SELECTOR DE FRECUENCIA
        frecuencia_pago = st.selectbox("Frecuencia de Aporte", ["Mensual", "Trimestral", "Semestral", "Anual"])
        mapa_meses = {"Mensual": 1, "Trimestral": 3, "Semestral": 6, "Anual": 12}
        step_meses = mapa_meses[frecuencia_pago]
        
        anio_inicio, mes_inicio = None, None

# --- BOTÓN DE ACCIÓN ---
if st.button("Generar Ilustración", type="primary"):
    status = st.empty()
    
    try:
        status.info("⏳ Calculando Multi-Capas...")
        
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
            # --- MIS (SISTEMA DE CUBETAS INDEPENDIENTES) ---
            
            # Filtramos desde la fecha del PRIMER aporte
            fecha_filtro = pd.Timestamp(year=anio_inicio, month=mes_inicio, day=1)
            df = df[df['Date'] >= fecha_filtro].copy().reset_index(drop=True)
            
            if df.empty: 
                st.error(f"No hay datos desde {mes_inicio}/{anio_inicio}")
                st.stop()
            
            df['Year'] = df['Date'].dt.year
            
            # Listas finales para el DataFrame
            total_valor_neto = []
            total_valor_rescate = []
            total_aportes_acumulados = [] # Para el gráfico de línea
            flujo_aportes = [] # Para la tabla (lo que entra ese mes)
            
            # Preparamos las "Cubetas" (Buckets)
            # Cubeta 0: El aporte inicial
            cubetas = [{
                "monto_original": monto_input,
                "saldo_actual": 0, # Se inicializa cuando entremos en su fecha
                "meses_activa": 0,
                "activa": False,
                "fecha_inicio": (anio_inicio, mes_inicio)
            }]
            
            # Agregamos cubetas extra si las hay
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
            
            # --- BUCLE DE TIEMPO (MES A MES) ---
            for i in range(len(df)):
                fecha_actual = df['Date'].iloc[i]
                mes_actual = fecha_actual.month
                anio_actual = fecha_actual.year
                
                aporte_del_mes_total = 0
                valor_cuenta_mes_total = 0
                valor_rescate_mes_total = 0
                
                # Procesamos cada Cubeta individualmente
                for cubeta in cubetas:
                    # 1. ¿Toca activar esta cubeta? (Coincide fecha)
                    if not cubeta["activa"]:
                        if anio_actual == cubeta["fecha_inicio"][0] and mes_actual == cubeta["fecha_inicio"][1]:
                            cubeta["activa"] = True
                            cubeta["saldo_actual"] = cubeta["monto_original"]
                            aporte_del_mes_total += cubeta["monto_original"]
                            acumulado_aportado += cubeta["monto_original"]
                    
                    if cubeta["activa"]:
                        # 2. Rendimiento Mercado (Si no es el primer mes de vida de la cubeta)
                        # Ojo: Si acabamos de activarla, no aplicamos rendimiento del mes anterior sobre el aporte nuevo
                        if cubeta["meses_activa"] > 0 and i > 0 and precios[i-1] > 0:
                            rendimiento = precios[i] / precios[i-1]
                            cubeta["saldo_actual"] *= rendimiento
                        
                        # 3. Deducciones (Específicas de esta cubeta)
                        deduccion_establecimiento = (cubeta["monto_original"] * 0.016) / 12
                        
                        if cubeta["meses_activa"] < 60:
                            # Primeros 5 años: Costo fijo Estructura
                            cubeta["saldo_actual"] -= deduccion_establecimiento
                        else:
                            # Después: Costo Admin 1% sobre saldo
                            cubeta["saldo_actual"] -= (cubeta["saldo_actual"] * (0.01/12))
                        
                        # 4. Cálculo Rescate (Específico de esta cubeta)
                        if cubeta["meses_activa"] < 60:
                            meses_restantes = 60 - (cubeta["meses_activa"] + 1)
                            penalizacion = meses_restantes * deduccion_establecimiento
                            valor_rescate_cubeta = max(0, cubeta["saldo_actual"] - penalizacion)
                        else:
                            valor_rescate_cubeta = cubeta["saldo_actual"]
                            
                        # Sumar al total del cliente
                        valor_cuenta_mes_total += cubeta["saldo_actual"]
                        valor_rescate_mes_total += valor_rescate_cubeta
                        
                        # Avanzar contador de edad de la cubeta
                        cubeta["meses_activa"] += 1

                # Guardamos los totales del mes
                flujo_aportes.append(aporte_del_mes_total)
                total_aportes_acumulados.append(acumulado_aportado)
                total_valor_neto.append(valor_cuenta_mes_total)
                total_valor_rescate.append(valor_rescate_mes_total)
            
            # Asignamos al DF
            df['Aporte_Simulado'] = flujo_aportes
            df['Aporte_Acumulado_Total'] = total_aportes_acumulados # Columna auxiliar
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
            saldo_act = 0
            acumulado_aportado = 0
            precios = df['Price'].values
            
            for i in range(len(df)):
                if i >= meses_totales: break
                
                monto_del_mes = 0
                if i % step_meses == 0:
                    monto_del_mes = monto_input
                
                aportes_sim.append(monto_del_mes)
                saldo_act += monto_del_mes
                acumulado_aportado += monto_del_mes
                
                if i > 0 and precios[i-1] > 0:
                    saldo_act *= (precios[i] / precios[i-1])
                
                saldo_act -= deduccion_mensual
                saldos.append(saldo_act)
                
                meses_restantes = meses_totales - (i + 1)
                penalizacion = meses_restantes * deduccion_mensual if meses_restantes > 0 else 0
                valor_rescate = max(0, saldo_act - penalizacion)
                rescates.append(valor_rescate)
            
            df = df.iloc[:len(saldos)].copy()
            df['Aporte_Simulado'] = aportes_sim
            df['Aporte_Acumulado_Total'] = df['Aporte_Simulado'].cumsum()
            df['Valor_Neto_Simulado'] = saldos
            df['Valor_Rescate_Simulado'] = rescates

        # 3. DATOS TABLA
        status.info("⏳ Generando Informe Multi-Capa...")
        
        datos_tabla = df.groupby('Year').agg({
            'Aporte_Simulado': 'sum', 
            'Valor_Neto_Simulado': 'last',
            'Valor_Rescate_Simulado': 'last',
            'Aporte_Acumulado_Total': 'last' # Tomamos el último valor del año
        }).reset_index()
        
        # Rendimiento
        datos_tabla['Saldo_Inicial'] = datos_tabla['Valor_Neto_Simulado'].shift(1).fillna(0)
        datos_tabla['Ganancia'] = datos_tabla['Valor_Neto_Simulado'] - datos_tabla['Saldo_Inicial'] - datos_tabla['Aporte_Simulado']
        
        datos_tabla['Base_Calculo'] = (datos_tabla['Saldo_Inicial'] + datos_tabla['Aporte_Simulado']).replace(0, 1)
        datos_tabla['Rendimiento'] = (datos_tabla['Ganancia'] / datos_tabla['Base_Calculo']) * 100

        # 4. GRAFICAR
        fig = plt.figure(figsize=(11, 14))
        plt.suptitle(f'Plan: {plan_seleccionado}\nCliente: {nombre_cliente}', fontsize=18, weight='bold', y=0.96)
        
        # Subtitulo inteligente
        if plan_seleccionado == "MIS - Aporte Unico":
            num_aportes = 1 + len(aportes_extra_mis)
            sub_texto = f"Estrategia de Inversión Escalonada ({num_aportes} Aportes)"
        else:
            sub_texto = f"Aporte {frecuencia_pago}: ${monto_input:,.0f}"
        
        plt.figtext(0.5, 0.93, sub_texto, ha="center", fontsize=14, color='#555')

        tot_inv = datos_tabla['Aporte_Acumulado_Total'].iloc[-1]
        val_fin = datos_tabla['Valor_Neto_Simulado'].iloc[-1]
        val_rescate_fin = datos_tabla['Valor_Rescate_Simulado'].iloc[-1]
        
        resumen = f"Inversión Total: ${tot_inv:,.0f} | Valor Cuenta: ${val_fin:,.0f} | Valor Rescate: ${val_rescate_fin:,.0f}"
        
        plt.figtext(0.5, 0.90, resumen, ha="center", fontsize=11, weight='bold',
                   bbox=dict(facecolor='#f0f8ff', edgecolor='blue'))

        # Gráfico
        ax = plt.subplot2grid((10, 1), (1, 0), rowspan=4)
        ax.plot(df['Date'], df['Valor_Neto_Simulado'], color='#004c99', lw=2, label="Valor de Cuenta")
        
        if df['Valor_Rescate_Simulado'].iloc[-1] < df['Valor_Neto_Simulado'].iloc[-1] * 0.99:
             ax.plot(df['Date'], df['Valor_Rescate_Simulado'], color='#d62728', lw=1.5, ls=':', label="Valor de Rescate")
        
        ax.plot(df['Date'], df['Aporte_Acumulado_Total'], color='gray', ls='--', label="Capital Invertido", alpha=0.6)
        
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))

        # Tabla
        ax_t = plt.subplot2grid((10, 1), (6, 0), rowspan=4)
        ax_t.axis('off')
        
        rows = [['Año', 'Aporte Anual', 'Aporte Total', 'Valor Cuenta', 'Valor Rescate']]
        for _, r in datos_tabla.iterrows():
            rows.append([
                str(int(r['Year'])), 
                f"${r['Aporte_Simulado']:,.0f}", # Lo que puso ese año
                f"${r['Aporte_Acumulado_Total']:,.0f}", # Total histórico
                f"${r['Valor_Neto_Simulado']:,.0f}", 
                f"${r['Valor_Rescate_Simulado']:,.0f}"
            ])
        
        tbl = ax_t.table(cellText=rows, loc='center', cellLoc='center')
        tbl.scale(1, 1.35)
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)

        for (r, c), cell in tbl.get_celld().items():
            if r == 0: 
                cell.set_facecolor('#40466e')
                cell.set_text_props(color='white', weight='bold')
            elif r % 2 == 0: 
                cell.set_facecolor('#f2f2f2')
            
            # Resaltar Rescate si hay penalización fuerte
            if c == 4 and r > 0:
                val_res = float(cell.get_text().get_text().replace('$','').replace(',',''))
                val_cta = float(rows[r][3].replace('$','').replace(',',''))
                if val_res < val_cta * 0.95: 
                    cell.set_text_props(color='#d62728') 

        plt.tight_layout(rect=[0, 0.03, 1, 0.88])
        st.pyplot(fig)
        
        img = io.BytesIO()
        plt.savefig(img, format='pdf')
        img.seek(0)
        
        st.download_button("📥 Descargar PDF", data=img, file_name=f"Ilustracion_{nombre_cliente}.pdf", mime="application/pdf")
        status.success("✅ Generado con éxito")

    except Exception as e:
        status.error("❌ Error:")
        st.error(e)
        st.write(traceback.format_exc())
