import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg") # Backend estable para servidores
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
        if st.session_state["password"] == "dominion2025": 
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
# 🚀 APLICACIÓN PRINCIPAL
# =========================================================

st.title("💼 Generador de Ilustraciones")

# --- DETECTIVE DE ARCHIVOS ---
all_files = os.listdir()
csv_files = [f for f in all_files if f.endswith('.csv')]

with st.sidebar:
    st.header("Configuración")
    nombre_cliente = st.text_input("Nombre Cliente", value="Cliente Ejemplo")
    
    # GENERADOR DE MENÚ
    planes = {}
    
    # 1. Regulares
    for i in range(5, 21):
        for filename in csv_files:
            if "MSS" in filename and str(i) in filename:
                if i < 10 and f"1{i}" in filename: continue 
                planes[f"MSS - {i} Años"] = filename
                break
            
    # 2. Aporte Único
    for filename in csv_files:
        if "nico" in filename.lower() or "unique" in filename.lower():
            planes["MIS - Aporte Unico"] = filename
            break
    
    if not planes:
        st.error("🚨 ERROR: No encuentro archivos CSV.")
        st.write("Archivos en carpeta:", all_files)
        st.stop()
    
    plan_seleccionado = st.selectbox("Selecciona Plan", list(planes.keys()))
    archivo_csv = planes[plan_seleccionado]
    
    # INPUTS
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
    
    # INICIO DEL PROCESO
    try:
        status.info("⏳ Leyendo datos...")
        
        # 1. CARGA DE DATOS
        df = pd.read_csv(archivo_csv)
        df.columns = df.columns.str.strip()
        
        # Función limpieza
        def limpiar(x):
            return x.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
            
        for col in ['Aporte', 'Valor Neto', 'Price']:
            if col in df.columns:
                df[col] = pd.to_numeric(limpiar(df[col]), errors='coerce').fillna(0)

        # 2. FECHAS
        if 'Date' not in df.columns:
            st.error("El archivo no tiene columna 'Date'")
            st.stop()
            
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date')
        
        if df.empty:
            st.error("Error: El archivo está vacío o las fechas fallaron.")
            st.stop()

        # 3. CÁLCULOS
        status.info(f"⏳ Calculando {plan_seleccionado}...")
        
        if plan_seleccionado == "MIS - Aporte Unico":
            fecha_filtro = pd.Timestamp(year=anio_inicio, month=mes_inicio, day=1)
            df = df[df['Date'] >= fecha_filtro].copy().reset_index(drop=True)
            
            if df.empty: 
                st.error(f"No hay datos desde {mes_inicio}/{anio_inicio}")
                st.stop()
            
            df['Year'] = df['Date'].dt.year
            saldos, aportes_sim = [], []
            saldo_act = monto_input
            precios = df['Price'].values
            
            for i in range(len(df)):
                aportes_sim.append(monto_input if i==0 else 0)
                if i > 0 and precios[i-1] > 0:
                    saldo_act *= (precios[i] / precios[i-1])
                if i >= 60:
                    saldo_act -= (saldo_act * (0.01/12))
                saldos.append(saldo_act)
            
            df['Aporte_Simulado'] = aportes_sim
            df['Valor_Neto_Simulado'] = saldos
        else:
            df['Year'] = df['Date'].dt.year
            df_aportes = df[df['Aporte'] > 0]
            base = df_aportes['Aporte'].iloc[0] if not df_aportes.empty else 500
            factor = monto_input / base
            df['Aporte_Simulado'] = df['Aporte'] * factor
            df['Valor_Neto_Simulado'] = df['Valor Neto'] * factor

        # 4. PREPARAR GRÁFICO Y TABLA
        status.info("⏳ Generando visualización...")
        
        datos_tabla = df.groupby('Year').agg({'Aporte_Simulado':'sum', 'Valor_Neto_Simulado':'last'}).reset_index()
        datos_tabla['Total Aporte'] = datos_tabla['Aporte_Simulado'].cumsum()
        
        # Rendimientos
        datos_tabla['Saldo_Inicial'] = datos_tabla['Valor_Neto_Simulado'].shift(1).fillna(0)
        datos_tabla['Ganancia'] = datos_tabla['Valor_Neto_Simulado'] - datos_tabla['Saldo_Inicial'] - datos_tabla['Aporte_Simulado']
        
        if plan_seleccionado == "MIS - Aporte Unico":
            base_cap = datos_tabla['Saldo_Inicial'] + datos_tabla['Aporte_Simulado']
        else:
            base_cap = datos_tabla['Saldo_Inicial'] + (datos_tabla['Aporte_Simulado']/2)
            
        datos_tabla['Rendimiento'] = (datos_tabla['Ganancia'] / base_cap.replace(0,1)) * 100

        # --- DIBUJAR ---
        fig = plt.figure(figsize=(11, 14))
        plt.suptitle(f'Plan: {plan_seleccionado}\nCliente: {nombre_cliente}', fontsize=18, weight='bold', y=0.96)
        
        # Texto Resumen
        tot_inv = datos_tabla['Total Aporte'].iloc[-1]
        val_fin = datos_tabla['Valor_Neto_Simulado'].iloc[-1]
        roi = ((val_fin - tot_inv)/tot_inv)*100
        
        plt.figtext(0.5, 0.90, f"Inv: ${tot_inv:,.0f} | Final: ${val_fin:,.0f} | ROI: {roi:+.1f}%", 
                   ha="center", fontsize=12, bbox=dict(facecolor='#f0f8ff', edgecolor='blue'))

        # Gráfico
        ax = plt.subplot2grid((10, 1), (1, 0), rowspan=4)
        ax.plot(df['Date'], df['Valor_Neto_Simulado'], color='#004c99', lw=2, label="Valor Cuenta")
        ax.plot(df['Date'], df['Aporte_Simulado'].cumsum(), color='gray', ls='--', label="Aporte Total")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))

        # Tabla
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

        # Colorear Tabla
        for (r, c), cell in tbl.get_celld().items():
            if r == 0: 
                cell.set_facecolor('#40466e')
                cell.set_text_props(color='white', weight='bold')
            elif r % 2 == 0: 
                cell.set_facecolor('#f2f2f2')
            
            if c == 4 and r > 0:
                txt = cell.get_text().get_text()
                if '+' in txt: cell.set_text_props(color='green', weight='bold')
                else: cell.set_text_props(color='red', weight='bold')

        plt.tight_layout(rect=[0, 0.03, 1, 0.88])
        st.pyplot(fig)
        
        # PDF
        status.info("⏳ Creando PDF...")
        img = io.BytesIO()
        plt.savefig(img, format='pdf')
        img.seek(0)
        
        status.success("✅ ¡Listo!")
        st.download_button("📥 Descargar PDF", data=img, file_name=f"Ilustracion_{nombre_cliente}.pdf", mime="application/pdf")

    except Exception as e:
        status.error("❌ Ocurrió un error inesperado:")
        st.error(e)
        st.write(traceback.format_exc())
