import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import os # Necesario para ver los archivos del sistema

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Ilustraciones", page_icon="📈")

# --- 🔐 SISTEMA DE CONTRASEÑA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "historico": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Acceso Restringido")
    st.text_input("Contraseña:", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Contraseña incorrecta.")
    return False

if not check_password():
    st.stop()

# =========================================================
# 🚀 APLICACIÓN PRINCIPAL
# =========================================================

st.title("💼 Generador de Ilustraciones Financieras")

# --- 🕵️‍♂️ EL DETECTIVE DE ARCHIVOS (DEBUGGER) ---
# Esto listará en la barra lateral qué archivos ve realmente el sistema
all_files = os.listdir()
csv_files = [f for f in all_files if f.endswith('.csv')]

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Configuración del Plan")
    nombre_cliente = st.text_input("Nombre del Cliente", value="Cliente Ejemplo")
    
    # --- GENERADOR INTELIGENTE DEL MENÚ ---
    planes = {}
    
    # 1. BUSCAR AUTOMÁTICAMENTE ARCHIVOS MSS (Años 5 a 20)
    # En lugar de adivinar el nombre, buscamos en los archivos reales
    for i in range(5, 21):
        found = False
        for filename in csv_files:
            # Buscamos archivos que tengan "MSS" y el número exacto (ej: "MSS" y "8")
            # Cuidado: que no confunda 8 con 18.
            # Verificamos si el numero está en el nombre
            if "MSS" in filename and str(i) in filename:
                # Verificación extra para evitar confusión (ej: 18 vs 8)
                # Si buscamos 8, aseguramos que no sea 18
                if i < 10 and f"1{i}" in filename:
                    continue 
                
                planes[f"MSS - {i} Años"] = filename
                found = True
                break
        
        # Si no encontró el archivo, no lo agrega al menú (evita errores)
        if not found:
            pass # Simplemente no aparece la opción
            
    # 2. Plan Aporte Único (Buscamos algo que diga "nico" o "unico")
    for filename in csv_files:
        if "nico" in filename.lower() or "unique" in filename.lower():
            planes["MIS - Aporte Unico"] = filename
            break
    
    if not planes:
        st.error("🚨 NO SE ENCONTRARON ARCHIVOS CSV.")
        st.warning("Archivos detectados en la carpeta:")
        st.write(all_files)
        st.stop()
    
    plan_seleccionado = st.selectbox("Selecciona el Plan", list(planes.keys()))
    archivo_csv = planes[plan_seleccionado]

    # --- DEBUGGING VISUAL (Para que veas qué archivo eligió) ---
    st.caption(f"📂 Archivo cargado: `{archivo_csv}`")

    # --- INPUTS DINÁMICOS ---
    if plan_seleccionado == "MIS - Aporte Unico":
        st.info("Configuración de Inversión Única")
        monto_input = st.number_input("Monto de Inversión (USD)", min_value=1000, value=10000, step=1000)
        
        st.markdown("### 📅 Fecha de Inicio")
        col1, col2 = st.columns(2)
        with col1:
            anio_inicio = st.number_input("Año", min_value=2000, max_value=2024, value=2015)
        with col2:
            mes_inicio = st.selectbox("Mes", range(1, 13), index=0)
            
    else:
        st.info("Configuración de Ahorro Regular")
        monto_input = st.number_input("Aporte Mensual (USD)", min_value=100, value=500, step=50)
        anio_inicio = None
        mes_inicio = None

    if st.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()

# --- FUNCIONES DE PROCESAMIENTO ---

def limpiar_moneda(serie):
    return serie.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()

def procesar_datos(archivo, monto_usuario, plan_nombre, anio_start, mes_start):
    try:
        df = pd.read_csv(archivo)
        df.columns = df.columns.str.strip()
        
        for col in ['Aporte', 'Valor Neto', 'Price']:
            if col in df.columns:
                df[col] = pd.to_numeric(limpiar_moneda(df[col]), errors='coerce').fillna(0)

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Date'])
            df = df.sort_values('Date')
        else:
            st.error("El archivo no tiene columna 'Date'.")
            return None
        
        # CASO A: MIS - APORTE UNICO
        if plan_nombre == "MIS - Aporte Unico":
            fecha_filtro = pd.Timestamp(year=anio_start, month=mes_start, day=1)
            df = df[df['Date'] >= fecha_filtro].copy()
            
            if df.empty:
                st.error(f"❌ No hay datos históricos disponibles desde {mes_start}/{anio_start}.")
                return None
            
            df = df.reset_index(drop=True)
            df['Year'] = df['Date'].dt.year
            
            saldos = []
            aportes_sim = []
            saldo_actual = monto_usuario
            precios = df['Price'].values
            tasa_costo_mensual = 0.01 / 12 
            
            for i in range(len(df)):
                if i == 0:
                    aportes_sim.append(monto_usuario)
                    saldos.append(saldo_actual)
                else:
                    aportes_sim.append(0)
                    if precios[i-1] > 0:
                        rendimiento = precios[i] / precios[i-1]
                        saldo_actual = saldo_actual * rendimiento
                    
                    if i >= 60:
                        deduccion = saldo_actual * tasa_costo_mensual
                        saldo_actual = saldo_actual - deduccion
                    saldos.append(saldo_actual)
            
            df['Aporte_Simulado'] = aportes_sim
            df['Valor_Neto_Simulado'] = saldos

        # CASO B: PLANES REGULARES
        else:
            df['Year'] = df['Date'].dt.year
            # Detección segura del aporte base
            df_aportes = df[df['Aporte'] > 0]
            if not df_aportes.empty:
                aporte_base = df_aportes['Aporte'].iloc[0]
            else:
                aporte_base = 500 # Fallback
                
            factor = monto_usuario / aporte_base
            df['Aporte_Simulado'] = df['Aporte'] * factor
            df['Valor_Neto_Simulado'] = df['Valor Neto'] * factor
        
        return df

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
        return None

# --- GENERACIÓN DEL REPORTE ---
if st.button("Generar Ilustración", type="primary"):
    with st.spinner('Calculando proyección...'):
        df = procesar_datos(archivo_csv, monto_input, plan_seleccionado, anio_inicio, mes_inicio)
        
        if df is not None:
            datos_grafico = df.copy()
            datos_grafico['Aporte Acumulado'] = datos_grafico['Aporte_Simulado'].cumsum()
            
            datos_tabla = df.groupby('Year').agg({
                'Aporte_Simulado': 'sum', 
                'Valor_Neto_Simulado': 'last'
            }).reset_index()
            datos_tabla['Total Aporte'] = datos_tabla['Aporte_Simulado'].cumsum()

            fig = plt.figure(figsize=(11, 14)) 
            plt.suptitle(f'Ilustración Plan: {plan_seleccionado}\nCliente: {nombre_cliente}', fontsize=18, weight='bold', y=0.95)
            
            if plan_seleccionado == "MIS - Aporte Unico":
                sub = f"Inversión Única: ${monto_input:,.0f} | Inicio: {mes_inicio}/{anio_inicio}"
            else:
                sub = f"Aporte Mensual: ${monto_input:,.0f}"
            plt.figtext(0.5, 0.92, sub, ha="center", fontsize=14, color='#004c99')

            ax_plot = plt.subplot2grid((10, 1), (1, 0), rowspan=4)
            ax_plot.plot(datos_grafico['Date'], datos_grafico['Valor_Neto_Simulado'], label='Valor de Cuenta Proyectado', color='#004c99', linewidth=2)
            ax_plot.plot(datos_grafico['Date'], datos_grafico['Aporte Acumulado'], label='Capital Total Aportado', color='gray', linestyle='--', alpha=0.7)
            ax_plot.set_ylabel('Valor (USD)')
            ax_plot.legend()
            ax_plot.grid(True, linestyle='--', alpha=0.3)
            ax_plot.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))

            ax_table = plt.subplot2grid((10, 1), (6, 0), rowspan=4)
            ax_table.axis('off')
            
            lista_tabla = [['Año', 'Aporte Anual', 'Aporte Total', 'Valor Cuenta']]
            for _, row in datos_tabla.iterrows():
                lista_tabla.append([
                    str(int(row['Year'])), 
                    f"${row['Aporte_Simulado']:,.0f}", 
                    f"${row['Total Aporte']:,.0f}", 
                    f"${row['Valor_Neto_Simulado']:,.0f}"
                ])

            the_table = ax_table.table(cellText=lista_tabla, colLabels=None, loc='center', cellLoc='center')
            the_table.auto_set_font_size(False)
            the_table.set_fontsize(10)
            the_table.scale(1, 1.4)
            
            for key, cell in the_table.get_celld().items():
                if key[0] == 0:
                    cell.set_facecolor('#40466e')
                    cell.set_text_props(color='white', weight='bold')
                elif key[0] % 2 == 0:
                    cell.set_facecolor('#f2f2f2')

            nota_legal = "Nota: Proyección histórica S&P 500. Rendimientos pasados no garantizan futuros."
            if plan_seleccionado == "MIS - Aporte Unico":
                nota_legal += "\nIncluye deducción administrativa del 1% anual a partir del año 6."
            plt.figtext(0.5, 0.02, nota_legal, ha="center", fontsize=9, style='italic', color='gray')
            plt.tight_layout(rect=[0, 0.03, 1, 0.90])

            st.pyplot(fig)

            fn = f"Ilustracion_{nombre_cliente.replace(' ', '_')}_{plan_seleccionado}.pdf"
            img = io.BytesIO()
            plt.savefig(img, format='pdf')
            img.seek(0)
            
            st.success("✅ Generado con éxito")
            st.download_button(label="📥 Descargar PDF", data=img, file_name=fn, mime="application/pdf")