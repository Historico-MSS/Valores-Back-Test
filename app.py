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
st.set_page_config(page_title="Generador de Ilustraciones", page_icon="📊")

# --- 🔐 SISTEMA DE CONTRASEÑA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "prueba": 
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
# 🏦 BASE DE DATOS DE COSTOS (EU FACTORS)
# =========================================================
# Factores extraídos de costos.xlsx
# [Plazo]: (Factor Año 1, Factor Año 2)
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

st.title("💼 Generador de Ilustraciones")

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
                planes[f"MSS - {i} Años"] = (filename, i) # Guardamos nombre y años
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
    
    if plan_seleccionado == "MIS - Aporte Unico":
        monto_input = st.number_input("Inversión Única", value=10000, step=1000)
        col1, col2 = st.columns(2)
        with col1: anio_inicio = st.number_input("Año Inicio", 2000, 2024, 2015)
        with col2: mes_inicio = st.selectbox("Mes Inicio", range(1, 13))
    else:
        monto_input = st.number_input("Aporte Mensual", value=500, step=50)
        anio_inicio, mes_inicio = None, None

# --- BOTÓN DE ACCIÓN ---
if st.button("Generar Ilustración", type="primary"):
    status = st.empty()
    
    try:
        status.info("⏳ Calculando Estructura de Costos...")
        
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

        # 2. SIMULACIÓN DINÁMICA CON COSTOS
        # Aquí ignoramos el 'Valor Neto' del CSV y creamos uno nuevo con tus reglas
        
        if plan_seleccionado == "MIS - Aporte Unico":
            # --- LÓGICA MIS (1.6% Fijo primeros 5 años) ---
            fecha_filtro = pd.Timestamp(year=anio_inicio, month=mes_inicio, day=1)
            df = df[df['Date'] >= fecha_filtro].copy().reset_index(drop=True)
            
            if df.empty: 
                st.error(f"No hay datos desde {mes_inicio}/{anio_inicio}")
                st.stop()
            
            df['Year'] = df['Date'].dt.year
            saldos, aportes_sim = [], []
            saldo_act = monto_input
            precios = df['Price'].values
            
            # Costo Fijo Mensual (Primeros 60 meses) = 1.6% Anual sobre INVERSIÓN INICIAL
            deduccion_establecimiento = (monto_input * 0.016) / 12
            
            for i in range(len(df)):
                aportes_sim.append(monto_input if i==0 else 0)
                
                # Rendimiento Mercado
                if i > 0 and precios[i-1] > 0:
                    saldo_act *= (precios[i] / precios[i-1])
                
                # Deducciones
                if i < 60: # Primeros 5 años
                    saldo_act -= deduccion_establecimiento
                else: # Después del año 5 (Mantenimiento 1% sobre Saldo)
                    saldo_act -= (saldo_act * (0.01/12))
                
                saldos.append(saldo_act)
            
            df['Aporte_Simulado'] = aportes_sim
            df['Valor_Neto_Simulado'] = saldos

        else:
            # --- LÓGICA MSS (Costos de Apertura Amortizados) ---
            df['Year'] = df['Date'].dt.year
            
            # 1. Calcular el Costo Total de Apertura (Frozen Amount)
            aporte_anual = monto_input * 12
            factor1, factor2 = FACTORES_COSTOS.get(plazo_anios, (0,0))
            
            costo_total_apertura = (aporte_anual * factor1) + (aporte_anual * factor2)
            
            # 2. Calcular la Deducción Mensual Fija (Amortización)
            meses_totales = plazo_anios * 12
            deduccion_mensual = costo_total_apertura / meses_totales
            
            # Simulación
            saldos, aportes_sim = [], []
            saldo_act = 0
            precios = df['Price'].values
            
            for i in range(len(df)):
                # Solo simulamos hasta el final del plazo elegido
                if i >= meses_totales:
                    break
                    
                # Aporte Mensual
                aportes_sim.append(monto_input)
                saldo_act += monto_input
                
                # Rendimiento Mercado
                if i > 0 and precios[i-1] > 0:
                    rendimiento = precios[i] / precios[i-1]
                    saldo_act *= rendimiento
                
                # Deducción Mensual Fija (Costo Apertura)
                saldo_act -= deduccion_mensual
                
                saldos.append(saldo_act)
            
            # Recortamos el DF al tamaño de la simulación
            df = df.iloc[:len(saldos)].copy()
            df['Aporte_Simulado'] = aportes_sim
            df['Valor_Neto_Simulado'] = saldos

        # 3. TABLA Y RENDIMIENTOS (Base Total Corregida)
        status.info("⏳ Generando Informe...")
        
        datos_tabla = df.groupby('Year').agg({'Aporte_Simulado':'sum', 'Valor_Neto_Simulado':'last'}).reset_index()
        datos_tabla['Total Aporte'] = datos_tabla['Aporte_Simulado'].cumsum()
        
        datos_tabla['Saldo_Inicial'] = datos_tabla['Valor_Neto_Simulado'].shift(1).fillna(0)
        datos_tabla['Ganancia'] = datos_tabla['Valor_Neto_Simulado'] - datos_tabla['Saldo_Inicial'] - datos_tabla['Aporte_Simulado']
        
        # Base de cálculo: Saldo Inicial + Todo el aporte del año (Conservador)
        datos_tabla['Base_Calculo'] = datos_tabla['Saldo_Inicial'] + datos_tabla['Aporte_Simulado']
        datos_tabla['Base_Calculo'] = datos_tabla['Base_Calculo'].replace(0, 1)
        
        datos_tabla['Rendimiento'] = (datos_tabla['Ganancia'] / datos_tabla['Base_Calculo']) * 100

        # 4. GRAFICAR
        fig = plt.figure(figsize=(11, 14))
        plt.suptitle(f'Plan: {plan_seleccionado}\nCliente: {nombre_cliente}', fontsize=18, weight='bold', y=0.96)
        
        tot_inv = datos_tabla['Total Aporte'].iloc[-1]
        val_fin = datos_tabla['Valor_Neto_Simulado'].iloc[-1]
        roi = ((val_fin - tot_inv)/tot_inv)*100
        
        plt.figtext(0.5, 0.90, f"Inv: ${tot_inv:,.0f} | Final: ${val_fin:,.0f} | ROI: {roi:+.1f}%", 
                   ha="center", fontsize=12, bbox=dict(facecolor='#f0f8ff', edgecolor='blue'))

        ax = plt.subplot2grid((10, 1), (1, 0), rowspan=4)
        ax.plot(df['Date'], df['Valor_Neto_Simulado'], color='#004c99', lw=2, label="Valor Cuenta")
        ax.plot(df['Date'], df['Aporte_Simulado'].cumsum(), color='gray', ls='--', label="Aporte Total")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))

        ax_t = plt.subplot2grid((10, 1), (6, 0), rowspan=4)
        ax_t.axis('off')
        
        rows = [['Año', 'Aporte', 'Acumulado', 'Valor', '% Rend']]
        for _, r in datos_tabla.iterrows():
            rows.append([
                str(int(r['Year'])), 
                f"${r['Aporte_Simulado']:,.0f}", 
                f"${r['Total Aporte']:,.0f}",
                f"${r['Valor_Neto_Simulado']:,.0f}", 
                f"{r['Rendimiento']:+.1f}%"
            ])
        
        tbl = ax_t.table(cellText=rows, loc='center', cellLoc='center')
        tbl.scale(1, 1.4)
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(10)

        for (r, c), cell in tbl.get_celld().items():
            if r == 0: 
                cell.set_facecolor('#40466e')
                cell.set_text_props(color='white', weight='bold')
            elif r % 2 == 0: 
                cell.set_facecolor('#f2f2f2')
            
            if c == 4 and r > 0:
                txt = cell.get_text().get_text()
                color = 'green' if '+' in txt else ('red' if '-' in txt else 'black')
                cell.set_text_props(color=color, weight='bold')

        plt.tight_layout(rect=[0, 0.03, 1, 0.88])
        st.pyplot(fig)
        
        img = io.BytesIO()
        plt.savefig(img, format='pdf')
        img.seek(0)
        
        st.download_button("📥 Descargar PDF", data=img, file_name=f"Ilustracion_{nombre_cliente}.pdf", mime="application/pdf")
        status.success("✅ ¡PDF Generado Correctamente!")

    except Exception as e:
        status.error("❌ Error:")
        st.error(e)
        st.write(traceback.format_exc())
