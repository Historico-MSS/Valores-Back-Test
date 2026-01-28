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
                    # Activar cubeta
                    if not c["on"]:
                        if y == c["ini"][0] and m == c["ini"][1]:
                            c["on"] = True
                            c["saldo"] = c["monto"]
                            ap_mes += c["monto"]
                            acum_aportado += c["monto"]
                            saldo_previo_tot += c["monto"]
                            
                    if c["on"]:
                        # Rendimiento
                        if c["edad"] > 0 and i > 0 and precios[i-1] > 0:
                            c["saldo"] *= (precios[i] / precios[i-1])
                            
                        # Retiro Prorrateado
                        if ret_mes > 0 and saldo_previo_tot > 0:
                            peso = c["saldo"] / saldo_previo_tot
                            c["saldo"] = max(0, c["saldo"] - (ret_mes * peso))
                            
                        # Costos
                        deduc = (c["monto"] * 0.016) / 12
                        if c["edad"] < 60: c["saldo"] -= deduc
                        else: c["saldo"] -= (c["saldo"] * (0.01/12))
                        
                        c["saldo"] = max(0, c["saldo"])
                        
                        # Rescate
                        if c["edad"] < 60:
                            pena = (60 - (c["edad"] + 1)) * deduc
                            vr_cubeta = max(0, c["saldo"] - pena)
                        else:
                            vr_cubeta = c["saldo"]
                            
                        vn_mes += c["saldo"]
                        vr_mes += vr_cubeta
                        c["edad"] += 1
                        
                l_ap.append(ap_mes)
                l_ap_acum.append(acum_aportado)
                l_vn.append(vn_mes)
                l_vr.append(vr_mes)
                
            df['Aporte_Sim'] = l_ap
            df['Retiro_Sim'] = l_ret
            df['Ap_Acum'] = l_ap_acum
            df['VN_Sim'] = l_vn
            df['VR_Sim'] = l_vr
            
        else: # MSS
            df['Year'] = df['Date'].dt.year
            pagos_anio = 12 / step_meses
            ap_anual = monto_ini * pagos_anio
            f1, f2 = FACTORES_COSTOS.get(plazo, (0,0))
            costo_tot = (ap_anual * f1) + (ap_anual * f2)
            meses_tot = plazo * 12
            deduc_mensual = costo_tot / meses_tot
            
            l_vn, l_vr, l_ap, l_ret = [], [], [], []
            saldo, acum_ap = 0, 0
            precios = df['Price'].values
            
            for i in range(len(df)):
                dt = df['Date'].iloc[i]
                if i >= meses_tot: break
                
                ap_mes = monto_ini if i % step_meses == 0 else 0
                l_ap.append(ap_mes)
                saldo += ap_mes
                acum_ap += ap_mes
                
                if i > 0 and precios[i-1] > 0:
                    saldo *= (precios[i] / precios[i-1])
                    
                ret_mes = sum(r['monto'] for r in retiros_prog if r['anio']==dt.year and r['mes']==dt.month)
                l_ret.append(ret_mes)
                if ret_mes > 0: saldo = max(0, saldo - ret_mes)
                
                saldo -= deduc_mensual
                l_vn.append(saldo)
                
                rest = meses_tot - (i + 1)
                pena = rest * deduc_mensual if rest > 0 else 0
                l_vr.append(max(0, saldo - pena))
                
            df = df.iloc[:len(l_vn)].copy()
            df['Aporte_Sim'] = l_ap
            df['Retiro_Sim'] = l_ret
            df['Ap_Acum'] = df['Aporte_Sim'].cumsum()
            df['VN_Sim'] = l_vn
            df['VR_Sim'] = l_vr

        # --- DATOS FINALES ---
        status.info("⏳ Generando reporte...")
        res = df.groupby('Year').agg({
            'Aporte_Sim': 'sum', 'Retiro_Sim': 'sum', 
            'VN_Sim': 'last', 'VR_Sim': 'last', 'Ap_Acum': 'last'
        }).reset_index()
        
        res['Saldo_Ini'] = res['VN_Sim'].shift(1).fillna(0)
        res['Ganancia'] = res['VN_Sim'] - res['Saldo_Ini'] - res['Aporte_Sim'] + res['Retiro_Sim']
        res['Base'] = (res['Saldo_Ini'] + res['Aporte_Sim']).replace(0, 1)
        res['Rend'] = (res['Ganancia'] / res['Base']) * 100

        # --- GRAFICO Y PDF ---
        fig = plt.figure(figsize=(11, 14))
        plt.suptitle(f'Plan: {plan_sel}\nCliente: {nombre_cliente}', fontsize=18, weight='bold', y=0.98)
        
        sub = f"Estrategia Escalonada ({1+len(aportes_extra)} Aportes)" if plan_sel.startswith("MIS") else f"Aporte {freq_pago}: ${monto_ini:,.0f}"
        plt.figtext(0.5, 0.925, sub, ha="center", fontsize=14, color='#555')
        
        tot_inv = res['Ap_Acum'].iloc[-1]
        fin_vn = res['VN_Sim'].iloc[-1]
        fin_vr = res['VR_Sim'].iloc[-1]
        tot_ret = res['Retiro_Sim'].sum()
        
        txt_res = f"Inv. Total: ${tot_inv:,.0f} | Retiros: ${tot_ret:,.0f} | Valor Cuenta: ${fin_vn:,.0f}" if tot_ret > 0 else f"Inversión: ${tot_inv:,.0f} | Valor Cuenta: ${fin_vn:,.0f} | Valor Rescate: ${fin_vr:,.0f}"
        plt.figtext(0.5, 0.88, txt_res, ha="center", fontsize=11, weight='bold', bbox=dict(facecolor='#f0f8ff', edgecolor='blue'))

        ax = plt.subplot2grid((10, 1), (1, 0), rowspan=4)
        ax.plot(df['Date'], df['VN_Sim'], color='#004c99', lw=2, label="Valor Cuenta")
        if df['VR_Sim'].iloc[-1] < df['VN_Sim'].iloc[-1]*0.99:
            ax.plot(df['Date'], df['VR_Sim'], color='#d62728', lw=1.5, ls=':', label="Valor Rescate")
        ax.plot(df['Date'], df['Ap_Acum'], color='gray', ls='--', label="Capital Invertido", alpha=0.6)
        ax.legend(); ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))

        ax_t = plt.subplot2grid((10, 1), (6, 0), rowspan=4); ax_t.axis('off')
        rows = [['Año', 'Aporte Total', 'Retiro', 'Valor Cuenta', 'Valor Rescate', '% Rend']]
        for _, r in res.iterrows():
            rt = f"${r['Retiro_Sim']:,.0f}" if r['Retiro_Sim'] > 0 else "-"
            rows.append([
                str(int(r['Year'])), f"${r['Ap_Acum']:,.0f}", rt,
                f"${r['VN_Sim']:,.0f}", f"${r['VR_Sim']:,.0f}", f"{r['Rend']:+.1f}%"
            ])
            
        tbl = ax_t.table(cellText=rows, loc='center', cellLoc='center')
        tbl.scale(1, 1.35); tbl.auto_set_font_size(False); tbl.set_fontsize(8)
        
        for (r, c), cell in tbl.get_celld().items():
            if r==0: cell.set_facecolor('#40466e'); cell.set_text_props(color='white', weight='bold')
            elif r%2==0: cell.set_facecolor('#f2f2f2')
            if c==5 and r>0: cell.set_text_props(color='green' if '+' in cell.get_text().get_text() else 'black', weight='bold')
            if c==2 and r>0 and cell.get_text().get_text() != "-": cell.set_text_props(color='#d62728', weight='bold')
            if c==4 and r>0:
                v_res = float(cell.get_text().get_text().replace('$','').replace(',',''))
                v_cta = float(rows[r][3].replace('$','').replace(',',''))
                if v_res < v_cta*0.95: cell.set_text_props(color='#d62728')

        plt.tight_layout(rect=[0, 0.03, 1, 0.86])
        st.pyplot(fig)
        
        img = io.BytesIO()
        plt.savefig(img, format='pdf')
        img.seek(0)
        st.download_button("📥 Descargar PDF", img, f"Ilustracion_{nombre_cliente}.pdf", "application/pdf")
        status.success("✅ ¡Listo!")

    except Exception as e:
        status.error("❌ Error"); st.error(e); st.write(traceback.format_exc())
