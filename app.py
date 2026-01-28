import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import os 
import traceback

# --- CONFIG ---
st.set_page_config(page_title="Generador v11", page_icon="💼")

def check_password():
    def password_entered():
        if st.session_state["password"] == "test": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if st.session_state.get("password_correct", False): return True
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
    
    # Detector de Archivos
    for i in range(5, 21):
        for f in files:
            if "MSS" in f and str(i) in f:
                if i<10 and f"1{i}" in f: continue
                planes[f"MSS - {i} Años"] = (f, i)
    for f in files:
        if "nico" in f.lower() or "unique" in f.lower(): planes["MIS - Aporte Unico"] = (f, 0)
    
    if not planes: st.error("No hay CSVs"); st.stop()
    
    sel = st.selectbox("Plan", list(planes.keys()))
    csv, plazo = planes[sel]
    
    extras, retiros = [], []
    
    if sel == "MIS - Aporte Unico":
        st.info("Plan Inversión")
        monto = st.number_input("Inversión (USD)", 10000, step=1000)
        freq = "Único"
        c1, c2 = st.columns([1.5, 1.5])
        with c1: y_ini = st.number_input("Año Inicio", 2000, 2024, 2015)
        with c2: m_n = st.selectbox("Mes Inicio", LM); m_ini = LM.index(m_n)+1
        
        with st.expander("➕ Extras"):
            if st.checkbox("Activar Extras"):
                for i in range(4):
                    st.divider()
                    c1,c2,c3 = st.columns([1.5,1,1.3])
                    with c1: m_x = st.number_input(f"Monto {i+1}", 0, step=1000)
                    with c2: y_x = st.number_input(f"Año {i+1}", y_ini, 2025, y_ini+1)
                    with c3: mn_x = st.selectbox(f"Mes {i+1}", LM); m_x_idx = LM.index(mn_x)+1
                    if m_x > 0: extras.append({"m":m_x, "y":y_x, "mo":m_x_idx})
    else:
        st.info("Plan Ahorro")
        monto = st.number_input("Aporte (USD)", 500, step=50)
        freq = st.selectbox("Frecuencia", ["Mensual", "Trimestral", "Semestral", "Anual"])
        step = {"Mensual":1, "Trimestral":3, "Semestral":6, "Anual":12}[freq]
        y_ini, m_ini = None, None

    with st.expander("💸 Retiros"):
        if st.checkbox("Activar Retiros"):
            for i in range(3):
                st.divider()
                c1,c2,c3 = st.columns([1.5,1,1.3])
                with c1: mr = st.number_input(f"Retiro {i+1}", 0, step=1000)
                with c2: 
                    min_y = y_ini if y_ini else 2000
                    yr = st.number_input(f"Año {i+1}", min_y, 2035, min_y+5)
                with c3: mnr = st.selectbox(f"Mes {i+1}", LM); mr_idx = LM.index(mnr)+1
                if mr > 0: retiros.append({"m":mr, "y":yr, "mo":mr_idx})

if st.button("Generar Ilustración", type="primary"):
    st.info("⏳ Procesando...")
    try:
        df = pd.read_csv(csv)
        df.columns = df.columns.str.strip()
        def cln(x): return x.astype(str).str.replace('$','',regex=False).str.replace(',','',regex=False).str.strip()
        for c in ['Aporte','Valor Neto','Price']: 
            if c in df.columns: df[c] = pd.to_numeric(cln(df[c]), errors='coerce').fillna(0)
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date')
        
        # --- CÁLCULO ---
        if sel == "MIS - Aporte Unico":
            filt = pd.Timestamp(year=y_ini, month=m_ini, day=1)
            df = df[df['Date']>=filt].reset_index(drop=True)
            if df.empty: st.error("Fecha sin datos"); st.stop()
            
            df['Year'] = df['Date'].dt.year
            l_vn, l_vr, l_ap_ac, l_ret = [], [], [], []
            
            # buckets: m=monto, s=saldo, e=edad, on=activo, ini=(año,mes)
            buckets = [{"m":monto, "s":0, "e":0, "on":False, "ini":(y_ini,m_ini)}]
            for x in extras: buckets.append({"m":x["m"], "s":0, "e":0, "on":False, "ini":(x["y"],x["mo"])})
            
            prices = df['Price'].values
            acum_ap = 0
            
            for i in range(len(df)):
                curr = df['Date'].iloc[i]
                cy, cm = curr.year, curr.month
                
                r_mes = sum(r["m"] for r in retiros if r["y"]==cy and r["mo"]==cm)
                l_ret.append(r_mes)
                
                stot_prev = sum(b["s"] for b in buckets if b["on"])
                vn_mes, vr_mes = 0, 0
                
                for b in buckets:
                    if not b["on"] and cy==b["ini"][0] and cm==b["ini"][1]:
                        b["on"] = True; b["s"] = b["m"]
                        acum_ap += b["m"]; stot_prev += b["m"]
                    
                    if b["on"]:
                        if b["e"]>0 and i>0 and prices[i-1]>0: b["s"] *= (prices[i]/prices[i-1])
                        
                        if r_mes > 0 and stot_prev > 0:
                            b["s"] = max(0, b["s"] - (r_mes * (b["s"]/stot_prev)))
                            
                        ded = (b["m"]*0.016)/12
                        if b["e"]<60: b["s"] -= ded
                        else: b["s"] -= (b["s"]*(0.01/12))
                        b["s"] = max(0, b["s"])
                        
                        pena = (60-(b["e"]+1))*ded if b["e"]<60 else 0
                        vn_mes += b["s"]
                        vr_mes += max(0, b["s"] - pena)
                        b["e"] += 1
                        
                l_vn.append(vn_mes); l_vr.append(vr_mes); l_ap_ac.append(acum_ap)
                
            df['Ap_Acum'] = l_ap_ac
            df['VN'] = l_vn
            df['VR'] = l_vr
            df['Retiro'] = l_ret

        else: # MSS
            df['Year'] = df['Date'].dt.year
            ap_anual = monto * (12/step)
            f1, f2 = FACTORES.get(plazo, (0,0))
            ded_mensual = ((ap_anual*f1) + (ap_anual*f2)) / (plazo*12)
            
            l_vn, l_vr, l_ap_ac, l_ret = [], [], [], []
            saldo, ap_acum = 0, 0
            prices = df['Price'].values
            
            for i in range(len(df)):
                curr = df['Date'].iloc[i]
                if i >= plazo*12: break
                
                if i % step == 0: saldo += monto; ap_acum += monto
                
                if i>0 and prices[i-1]>0: saldo *= (prices[i]/prices[i-1])
                
                r_mes = sum(r["m"] for r in retiros if r["y"]==curr.year and r["mo"]==curr.month)
                l_ret.append(r_mes)
                if r_mes>0: saldo = max(0, saldo-r_mes)
                
                saldo -= ded_mensual
                l_vn.append(saldo)
                
                rest = (plazo*12) - (i+1)
                pena = rest * ded_mensual if rest>0 else 0
                l_vr.append(max(0, saldo-pena))
                l_ap_ac.append(ap_acum)
                
            df = df.iloc[:len(l_vn)].copy()
            df['Ap_Acum'] = l_ap_ac
            df['VN'] = l_vn
            df['VR'] = l_vr
            df['Retiro'] = l_ret

        # --- REPORTE ---
        res = df.groupby('Year').agg({'Ap_Acum':'last', 'VN':'last', 'VR':'last', 'Retiro':'sum'}).reset_index()
        res['S_Ini'] = res['VN'].shift(1).fillna(0)
        res['Ap_Nuevo'] = res['Ap_Acum'] - res['Ap_Acum'].shift(1).fillna(0)
        res['Ganancia'] = res['VN'] - res['S_Ini'] - res['Ap_Nuevo'] + res['Retiro']
        res['Base'] = (res['S_Ini'] + res['Ap_Nuevo']).replace(0, 1)
        res['Rend'] = (res['Ganancia'] / res['Base']) * 100

        # --- PLOT ---
        fig = plt.figure(figsize=(11, 14))
        plt.suptitle(f'Plan: {sel}\nCliente: {cliente}', fontsize=18, weight='bold', y=0.98)
        
        sub = f"Estrategia ({1+len(extras)} Aportes)" if sel.startswith("MIS") else f"Aporte {freq}: ${monto:,.0f}"
        plt.figtext(0.5, 0.925, sub, ha="center", fontsize=14, color='#555')
        
        t_inv, t_ret, f_vn, f_vr = res['Ap_Acum'].iloc[-1], res['Retiro'].sum(), res['VN'].iloc[-1], res['VR'].iloc[-1]
        txt = f"Inv: ${t_inv:,.0f} | Retiros: ${t_ret:,.0f} | Valor: ${f_vn:,.0f}" if t_ret>0 else f"Inv: ${t_inv:,.0f} | Valor: ${f_vn:,.0f} | Rescate: ${f_vr:,.0f}"
        plt.figtext(0.5, 0.88, txt, ha="center", fontsize=11, weight='bold', bbox=dict(facecolor='#f0f8ff', edgecolor='blue'))

        ax = plt.subplot2grid((10, 1), (1, 0), rowspan=4)
        ax.plot(df['Date'], df['Ap_Acum'], color='#2ca02c', ls='--', label="Capital Invertido", alpha=0.9, lw=2)
        ax.plot(df['Date'], df['VR'], color='#808080', ls='--', label="Valor Rescate", alpha=0.9, lw=2)
        ax.plot(df['Date'], df['VN'], color='#004c99', lw=2.5, label="Valor Cuenta")
        ax.legend(); ax.grid(True, alpha=0.3); ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('${x:,.0f}'))

        # --- TABLA ---
        ax_t = plt.subplot2grid((10, 1), (6, 0), rowspan=4); ax_t.axis('off')
        rows = [['Año', 'Aporte Total', 'Retiro', 'Valor Cuenta', 'Valor Rescate', '% Rend']]
        for _, r in res.iterrows():
            rt = f"${r['Retiro']:,.0f}" if r['Retiro'] > 0 else "-"
            rows.append([
                str(int(r['Year'])), f"${r['Ap_Acum']:,.0f}", rt,
                f"${r['VN']:,.0f}", f"${r['VR']:,.0f}", f"{r['Rend']:+.1f}%"
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
        
        img = io.BytesIO(); plt.savefig(img, format='pdf'); img.seek(0)
        st.download_button("📥 Descargar PDF", img, f"Ilustracion_{cliente}.pdf", "application/pdf")
        st.success("✅ ¡Listo!")

    except Exception as e:
        st.error("❌ Error"); st.write(traceback.format_exc())
