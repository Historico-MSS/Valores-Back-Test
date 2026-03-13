import io
import os
import traceback
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Generador de Ilustraciones Financieras",
    page_icon="💼",
    layout="wide"
)

# --- PASSWORD ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    def password_entered():
        if st.session_state.get("password", "") == "test":
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
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
    17: (0.8415, 0.2104), 18: (0.8910, 0.2228), 19: (0.9405, 0.2351), 20: (0.9900, 0.2475)
}

LISTA_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

CACHE_DIR = "data_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Stooq diario -> luego convertimos a mensual real
STOOQ_DAILY_URL = "https://stooq.com/q/d/l/?s=%5Espx&i=d"

# AMC anual del tracker
AMC_ANUAL = 0.02


# --- UTILIDADES ---
def mes_numero(nombre_mes: str) -> int:
    return LISTA_MESES.index(nombre_mes) + 1


def fmt_usd(x):
    return f"USD {x:,.2f}"


def fmt_pct(x):
    return f"{x:+.2f}%"


def descargar_sp500_mensual() -> pd.DataFrame:
    req = urllib.request.Request(
        STOOQ_DAILY_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8")

    df = pd.read_csv(io.StringIO(raw))
    df.columns = [c.strip().title() for c in df.columns]

    if "Date" not in df.columns or "Close" not in df.columns:
        raise ValueError("Stooq no devolvió el formato esperado.")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Price"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna(subset=["Date", "Price"]).sort_values("Date").reset_index(drop=True)

    # Último cierre disponible de cada mes
    df["Month"] = df["Date"].dt.to_period("M")
    df = df.groupby("Month", as_index=False).last()
    df["Date"] = df["Month"].dt.to_timestamp("M")
    df = df[["Date", "Price"]].reset_index(drop=True)

    return df


def agregar_rendimiento_neto_tracker(df: pd.DataFrame, amc_anual: float = AMC_ANUAL) -> pd.DataFrame:
    """
    Convierte la serie mensual de precios del S&P 500 en una serie mensual neta,
    descontando un AMC anual prorrateado mensualmente y capitalizado de forma compuesta.
    """
    df = df.copy().sort_values("Date").reset_index(drop=True)

    # Retorno bruto mensual del índice
    df["Retorno_Bruto"] = df["Price"].pct_change().fillna(0.0)

    # Factor mensual equivalente del AMC anual
    factor_fee_mensual = (1 - amc_anual) ** (1 / 12)

    # Retorno neto mensual del tracker simulado
    df["Retorno_Neto"] = ((1 + df["Retorno_Bruto"]) * factor_fee_mensual) - 1

    return df


def cargar_serie_mercado(forzar_actualizacion: bool = False):
    cache_file = os.path.join(CACHE_DIR, "sp500_stooq_monthly.csv")
    origen = "cache local"

    if forzar_actualizacion or not os.path.exists(cache_file):
        try:
            df = descargar_sp500_mensual()
            df.to_csv(cache_file, index=False)
            origen = "descarga online"
        except Exception:
            if not os.path.exists(cache_file):
                raise

    df = pd.read_csv(cache_file)
    df.columns = [c.strip() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df = df.dropna(subset=["Date", "Price"]).sort_values("Date").reset_index(drop=True)

    df = agregar_rendimiento_neto_tracker(df, amc_anual=AMC_ANUAL)
    return df, origen


def detectar_planes_csv():
    archivos = [f for f in os.listdir() if f.lower().endswith(".csv")]
    planes = {}

    for f in archivos:
        nombre = f.lower()

        if "mis" in nombre:
            planes["MIS - Aporte Único"] = (f, 0, "MIS")

        elif "mss" in nombre:
            plazo = None

            for i in range(5, 21):
                patrones = [
                    f"mss - {i}",
                    f"mss-{i}",
                    f"mss {i}",
                    f" {i} años",
                    f" {i} anos",
                ]
                if any(p in nombre for p in patrones):
                    plazo = i
                    break

            if plazo is None:
                for i in range(5, 21):
                    if nombre.endswith(f"{i}.csv"):
                        plazo = i
                        break

            if plazo is not None:
                planes[f"MSS - {plazo} Años"] = (f, plazo, "MSS")

    return planes


def simular_mis(
    df_base: pd.DataFrame,
    monto_inicial: float,
    anio_inicio: int,
    mes_inicio: int,
    aportes_extra: list,
    retiros_programados: list
) -> pd.DataFrame:
    df = df_base.copy()
    fecha_filtro = pd.Timestamp(year=anio_inicio, month=mes_inicio, day=1) + pd.offsets.MonthEnd(0)
    df = df[df["Date"] >= fecha_filtro].copy().reset_index(drop=True)

    if df.empty:
        raise ValueError("No hay datos históricos disponibles desde la fecha seleccionada.")

    df["Year"] = df["Date"].dt.year
    retornos_netos = df["Retorno_Neto"].values

    cubetas = [{
        "monto": float(monto_inicial),
        "saldo": 0.0,
        "edad": 0,
        "activa": False,
        "ini": (anio_inicio, mes_inicio)
    }]

    for extra in aportes_extra:
        cubetas.append({
            "monto": float(extra["monto"]),
            "saldo": 0.0,
            "edad": 0,
            "activa": False,
            "ini": (int(extra["anio"]), int(extra["mes"]))
        })

    lista_vn, lista_vr, lista_aportes_acum, lista_retiros = [], [], [], []
    acumulado_aportes = 0.0

    for i in range(len(df)):
        fecha_act = df["Date"].iloc[i]
        anio_act, mes_act = fecha_act.year, fecha_act.month

        retiro_mes = 0.0
        for r in retiros_programados:
            if int(r["anio"]) == anio_act and int(r["mes"]) == mes_act:
                retiro_mes += float(r["monto"])
        lista_retiros.append(retiro_mes)

        saldo_total_previo = sum(c["saldo"] for c in cubetas if c["activa"])

        vn_mes_total = 0.0
        vr_mes_total = 0.0

        for c in cubetas:
            if not c["activa"] and (
                anio_act > c["ini"][0] or
                (anio_act == c["ini"][0] and mes_act >= c["ini"][1])
            ):
                c["activa"] = True
                c["saldo"] = c["monto"]
                acumulado_aportes += c["monto"]
                saldo_total_previo += c["monto"]

            if c["activa"]:
                # Interés compuesto mensual usando retorno neto del tracker
                if c["edad"] > 0:
                    c["saldo"] *= (1 + retornos_netos[i])

                if retiro_mes > 0 and saldo_total_previo > 0:
                    peso = c["saldo"] / saldo_total_previo if saldo_total_previo > 0 else 0
                    deduccion_retiro = retiro_mes * peso
                    c["saldo"] = max(0.0, c["saldo"] - deduccion_retiro)

                costo_establecimiento = (c["monto"] * 0.016) / 12.0
                if c["edad"] < 60:
                    c["saldo"] -= costo_establecimiento
                else:
                    c["saldo"] -= (c["saldo"] * (0.01 / 12.0))

                c["saldo"] = max(0.0, c["saldo"])

                penalizacion = 0.0
                if c["edad"] < 60:
                    meses_restantes = 60 - (c["edad"] + 1)
                    penalizacion = meses_restantes * costo_establecimiento

                vr_cubeta = max(0.0, c["saldo"] - penalizacion)

                vn_mes_total += c["saldo"]
                vr_mes_total += vr_cubeta
                c["edad"] += 1

        lista_vn.append(vn_mes_total)
        lista_vr.append(vr_mes_total)
        lista_aportes_acum.append(acumulado_aportes)

    df["Aporte_Acum"] = lista_aportes_acum
    df["Valor_Cuenta"] = lista_vn
    df["Valor_Rescate"] = lista_vr
    df["Retiro"] = lista_retiros
    df["Mes_Plan"] = range(1, len(df) + 1)
    return df


def simular_mss(
    df_base: pd.DataFrame,
    plazo_anios: int,
    monto_aporte: float,
    frecuencia_pago: str,
    anio_inicio: int,
    mes_inicio: int,
    retiros_programados: list
) -> pd.DataFrame:
    df = df_base.copy()
    fecha_filtro = pd.Timestamp(year=anio_inicio, month=mes_inicio, day=1) + pd.offsets.MonthEnd(0)
    df = df[df["Date"] >= fecha_filtro].copy().reset_index(drop=True)

    if df.empty:
        raise ValueError("No hay datos históricos disponibles desde la fecha seleccionada.")

    df["Year"] = df["Date"].dt.year
    retornos_netos = df["Retorno_Neto"].values

    mapa_pasos = {"Mensual": 1, "Trimestral": 3, "Semestral": 6, "Anual": 12}
    step_meses = mapa_pasos[frecuencia_pago]
    pagos_anio = 12 / step_meses
    aporte_anual = monto_aporte * pagos_anio

    factor1, factor2 = FACTORES_COSTOS.get(plazo_anios, (0, 0))
    costo_total_apertura = (aporte_anual * factor1) + (aporte_anual * factor2)
    meses_totales = plazo_anios * 12
    deduccion_mensual = costo_total_apertura / meses_totales if meses_totales > 0 else 0

    lista_vn, lista_vr, lista_aportes_acum, lista_retiros, lista_etapa = [], [], [], [], []
    saldo_actual = 0.0
    aporte_acumulado = 0.0

    for i in range(len(df)):
        fecha_act = df["Date"].iloc[i]

        # APORTES SOLO DURANTE EL PLAZO DEL PLAN
        if i < meses_totales and i % step_meses == 0:
            saldo_actual += monto_aporte
            aporte_acumulado += monto_aporte

        # Interés compuesto mensual usando retorno neto del tracker
        if i > 0:
            saldo_actual *= (1 + retornos_netos[i])

        retiro_mes = 0.0
        for r in retiros_programados:
            if int(r["anio"]) == fecha_act.year and int(r["mes"]) == fecha_act.month:
                retiro_mes += float(r["monto"])
        lista_retiros.append(retiro_mes)

        if retiro_mes > 0:
            saldo_actual = max(0.0, saldo_actual - retiro_mes)

        if i < meses_totales:
            saldo_actual -= deduccion_mensual
            meses_restantes = meses_totales - (i + 1)
            penalizacion = meses_restantes * deduccion_mensual if meses_restantes > 0 else 0
            valor_rescate = max(0.0, saldo_actual - penalizacion)
            etapa = "Acumulación"
        else:
            saldo_actual -= (saldo_actual * (0.01 / 12.0))
            valor_rescate = max(0.0, saldo_actual)
            etapa = "Post-maduración"

        saldo_actual = max(0.0, saldo_actual)

        lista_vn.append(saldo_actual)
        lista_vr.append(valor_rescate)
        lista_aportes_acum.append(aporte_acumulado)
        lista_etapa.append(etapa)

    df["Aporte_Acum"] = lista_aportes_acum
    df["Valor_Cuenta"] = lista_vn
    df["Valor_Rescate"] = lista_vr
    df["Retiro"] = lista_retiros
    df["Etapa"] = lista_etapa
    df["Mes_Plan"] = range(1, len(df) + 1)
    return df


def construir_resumen_anual(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "Mes_Plan" not in df.columns:
        df["Mes_Plan"] = range(1, len(df) + 1)

    df["Año_Plan"] = ((df["Mes_Plan"] - 1) // 12) + 1

    agg_cols = {
        "Year": "last",
        "Aporte_Acum": "last",
        "Valor_Cuenta": "last",
        "Valor_Rescate": "last",
        "Retiro": "sum"
    }

    if "Etapa" in df.columns:
        agg_cols["Etapa"] = "last"

    resumen = df.groupby("Año_Plan", as_index=False).agg(agg_cols)

    resumen["Saldo_Inicial"] = resumen["Valor_Cuenta"].shift(1).fillna(0)
    resumen["Aporte_Nuevo"] = resumen["Aporte_Acum"] - resumen["Aporte_Acum"].shift(1).fillna(0)

    resumen["Ganancia"] = (
        resumen["Valor_Cuenta"]
        - resumen["Saldo_Inicial"]
        - resumen["Aporte_Nuevo"]
        + resumen["Retiro"]
    )

    resumen["Base_Calculo"] = (resumen["Saldo_Inicial"] + resumen["Aporte_Nuevo"]).replace(0, pd.NA)
    resumen["Rendimiento"] = (resumen["Ganancia"] / resumen["Base_Calculo"]) * 100
    resumen["Rendimiento"] = resumen["Rendimiento"].fillna(0)

    resumen["Retiro_Acumulado"] = resumen["Retiro"].cumsum()
    base_acumulada = resumen["Aporte_Acum"].replace(0, pd.NA)

    resumen["Rendimiento_Acumulado"] = (
        (resumen["Valor_Cuenta"] + resumen["Retiro_Acumulado"] - resumen["Aporte_Acum"])
        / base_acumulada
    ) * 100
    resumen["Rendimiento_Acumulado"] = resumen["Rendimiento_Acumulado"].fillna(0)

    columnas_finales = [
        "Año_Plan",
        "Year",
        "Aporte_Acum",
        "Retiro",
        "Valor_Cuenta",
        "Valor_Rescate",
        "Rendimiento",
        "Rendimiento_Acumulado"
    ]

    if "Etapa" in resumen.columns:
        columnas_finales.append("Etapa")

    return resumen[columnas_finales]


def crear_figura_principal(df: pd.DataFrame, resumen: pd.DataFrame, seleccion: str, nombre_cliente: str, subtitulo: str):
    fig = plt.figure(figsize=(15, 8.8), facecolor="white")
    ax = fig.add_subplot(111)

    fig.text(
        0.5, 0.965,
        f"{seleccion}",
        ha="center", va="top",
        fontsize=22, fontweight="bold", color="#1f1f1f"
    )

    fig.text(
        0.5, 0.928,
        f"Cliente: {nombre_cliente}",
        ha="center", va="top",
        fontsize=16, fontweight="bold", color="#2f2f2f"
    )

    fig.text(
        0.5, 0.895,
        "Base de cálculo: S&P 500 mensual real con AMC 2.0% anual prorrateado mensualmente",
        ha="center", va="top",
        fontsize=10.5, color="#666666"
    )

    fig.text(
        0.5, 0.870,
        subtitulo,
        ha="center", va="top",
        fontsize=12, color="#4a4a4a"
    )

    inv_total = resumen["Aporte_Acum"].iloc[-1] if not resumen.empty else 0
    ret_total = resumen["Retiro"].sum() if not resumen.empty else 0
    val_final = resumen["Valor_Cuenta"].iloc[-1] if not resumen.empty else 0
    val_rescate_final = resumen["Valor_Rescate"].iloc[-1] if not resumen.empty else 0

    texto_resumen = (
        f"Inversión total: {fmt_usd(inv_total)}   |   "
        f"Valor en cuenta: {fmt_usd(val_final)}   |   "
        f"Valor de rescate: {fmt_usd(val_rescate_final)}"
    )
    if ret_total > 0:
        texto_resumen += f"   |   Retiros: {fmt_usd(ret_total)}"

    fig.text(
        0.5, 0.830,
        texto_resumen,
        ha="center", va="top",
        fontsize=11, fontweight="bold", color="#1f1f1f",
        bbox=dict(
            facecolor="#f7f9fc",
            edgecolor="#c7d2e3",
            boxstyle="round,pad=0.45"
        )
    )

    ax.set_facecolor("white")

    ax.plot(
        df["Date"], df["Aporte_Acum"],
        color="#2ca02c", linestyle="--", linewidth=2.2,
        label="Capital invertido"
    )
    ax.plot(
        df["Date"], df["Valor_Rescate"],
        color="#8c8c8c", linestyle="--", linewidth=2.0,
        label="Valor rescate"
    )
    ax.plot(
        df["Date"], df["Valor_Cuenta"],
        color="#0b5cad", linewidth=2.8,
        label="Valor cuenta"
    )

    ax.legend(
        loc="upper left",
        frameon=True,
        facecolor="white",
        edgecolor="#d9d9d9",
        fontsize=11
    )

    ax.grid(True, alpha=0.18, linewidth=0.8)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('USD {x:,.0f}'))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#c8c8c8")
    ax.spines["bottom"].set_color("#c8c8c8")

    ax.tick_params(axis="x", labelsize=10, colors="#444444")
    ax.tick_params(axis="y", labelsize=10, colors="#444444")

    ax.set_xlabel("")
    ax.set_ylabel("")

    plt.tight_layout(rect=[0.04, 0.06, 0.98, 0.70])

    return fig


def preparar_tabla_mostrar(resumen: pd.DataFrame) -> pd.DataFrame:
    mostrar = resumen.copy().rename(columns={
        "Año_Plan": "Año de plan",
        "Year": "Año calendario",
        "Aporte_Acum": "Aporte acumulado",
        "Retiro": "Retiro",
        "Valor_Cuenta": "Valor en cuenta",
        "Valor_Rescate": "Valor de rescate",
        "Rendimiento": "Rendimiento",
        "Rendimiento_Acumulado": "Rendimiento acumulado"
    })

    columnas_orden = [
        "Año de plan",
        "Año calendario",
        "Aporte acumulado",
        "Retiro",
        "Valor en cuenta",
        "Valor de rescate",
        "Rendimiento",
        "Rendimiento acumulado"
    ]

    if "Etapa" in mostrar.columns:
        columnas_orden.append("Etapa")

    return mostrar[columnas_orden]


def generar_tabla_excel(tabla_df: pd.DataFrame):
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        return None

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        tabla_df.to_excel(writer, index=False, sheet_name="Resumen")
    output.seek(0)
    return output.getvalue()


def generar_tabla_pdf(tabla_df: pd.DataFrame, titulo: str = "Resumen anual") -> bytes:
    output = io.BytesIO()

    fig, ax = plt.subplots(figsize=(17, max(4.5, 0.50 * len(tabla_df) + 2.4)))
    ax.axis("off")
    ax.set_title(titulo, fontsize=16, fontweight="bold", pad=20)

    tabla = ax.table(
        cellText=tabla_df.values,
        colLabels=tabla_df.columns,
        loc="center",
        cellLoc="center"
    )

    tabla.auto_set_font_size(False)
    tabla.set_fontsize(8.5)
    tabla.scale(1.18, 1.6)

    cols = list(tabla_df.columns)

    for (row, col), cell in tabla.get_celld().items():
        cell.set_edgecolor("#d8dde6")
        cell.set_linewidth(0.6)

        if row == 0:
            cell.set_facecolor("#40466e")
            cell.set_text_props(color="white", weight="bold", fontsize=9)
        elif row % 2 == 0:
            cell.set_facecolor("#f7f9fc")
        else:
            cell.set_facecolor("white")

    if "Valor de rescate" in cols and "Aporte acumulado" in cols:
        idx_rescate = cols.index("Valor de rescate")
        idx_aporte = cols.index("Aporte acumulado")

        for i in range(len(tabla_df)):
            rescate_txt = str(tabla_df.iloc[i, idx_rescate]).replace("USD", "").replace(",", "").strip()
            aporte_txt = str(tabla_df.iloc[i, idx_aporte]).replace("USD", "").replace(",", "").strip()

            try:
                rescate_val = float(rescate_txt)
                aporte_val = float(aporte_txt)
                if rescate_val < aporte_val:
                    tabla[(i + 1, idx_rescate)].set_text_props(color="#D4AC0D", weight="bold")
            except Exception:
                pass

    plt.tight_layout()
    fig.savefig(output, format="pdf", bbox_inches="tight")
    plt.close(fig)
    output.seek(0)
    return output.getvalue()


def generar_pdf_completo(fig_principal, tabla_export: pd.DataFrame, nombre_cliente: str) -> bytes:
    output = io.BytesIO()

    with PdfPages(output) as pdf:
        pdf.savefig(fig_principal, bbox_inches="tight")

        fig2, ax2 = plt.subplots(figsize=(17, max(5.5, 0.50 * len(tabla_export) + 2.8)))
        ax2.axis("off")
        ax2.set_title(f"Resumen anual - {nombre_cliente}", fontsize=16, fontweight="bold", pad=20)

        tabla = ax2.table(
            cellText=tabla_export.values,
            colLabels=tabla_export.columns,
            loc="center",
            cellLoc="center"
        )

        tabla.auto_set_font_size(False)
        tabla.set_fontsize(8.5)
        tabla.scale(1.18, 1.62)

        cols = list(tabla_export.columns)
        for (row, col), cell in tabla.get_celld().items():
            cell.set_edgecolor("#d8dde6")
            cell.set_linewidth(0.6)

            if row == 0:
                cell.set_facecolor("#40466e")
                cell.set_text_props(color="white", weight="bold", fontsize=9)
            elif row % 2 == 0:
                cell.set_facecolor("#f7f9fc")
            else:
                cell.set_facecolor("white")

        if "Valor de rescate" in cols and "Aporte acumulado" in cols:
            idx_rescate = cols.index("Valor de rescate")
            idx_aporte = cols.index("Aporte acumulado")
            for i in range(len(tabla_export)):
                rescate_txt = str(tabla_export.iloc[i, idx_rescate]).replace("USD", "").replace(",", "").strip()
                aporte_txt = str(tabla_export.iloc[i, idx_aporte]).replace("USD", "").replace(",", "").strip()
                try:
                    rescate_val = float(rescate_txt)
                    aporte_val = float(aporte_txt)
                    if rescate_val < aporte_val:
                        tabla[(i + 1, idx_rescate)].set_text_props(color="#D4AC0D", weight="bold")
                except Exception:
                    pass

        fig2.text(
            0.5, 0.03,
            "Disclaimer: esta herramienta es únicamente ilustrativa. No constituye una proyección garantizada, una oferta, ni asesoría financiera, legal o fiscal.",
            ha="center", fontsize=9, color="#666"
        )

        plt.tight_layout(rect=[0.02, 0.05, 0.98, 0.95])
        pdf.savefig(fig2, bbox_inches="tight")
        plt.close(fig2)

    output.seek(0)
    return output.getvalue()


# --- CARGA DE MERCADO ---
st.sidebar.header("Serie de mercado")
st.sidebar.caption("Base única neta: S&P 500 mensual real con AMC 2.0% anual")
forzar_actualizacion = st.sidebar.button("🔄 Actualizar base ahora")

try:
    df_mercado, origen_base = cargar_serie_mercado(forzar_actualizacion=forzar_actualizacion)
    st.sidebar.success(f"Base cargada: {len(df_mercado)} meses")
    st.sidebar.caption(
        f"Rango disponible: {df_mercado['Date'].min().strftime('%Y-%m')} a {df_mercado['Date'].max().strftime('%Y-%m')}"
    )
    st.sidebar.caption(f"Origen: {origen_base}")
except Exception:
    st.error("No se pudo cargar la base de mercado.")
    st.code(traceback.format_exc())
    st.stop()

# --- DETECCIÓN DE PLANES ---
planes_disponibles = detectar_planes_csv()

# --- UI PRINCIPAL ---
st.title("💼 Generador de Ilustraciones Financieras")
st.caption("Usando una base neta mensual con AMC 2.0% anual prorrateado mensualmente y rendimiento compuesto.")
st.info("Disclaimer: esta herramienta es únicamente ilustrativa. No constituye una proyección garantizada, una oferta, ni asesoría financiera, legal o fiscal.")

with st.sidebar:
    st.header("Tipo de Plan")

    opciones_ordenadas = []
    if "MIS - Aporte Único" in planes_disponibles:
        opciones_ordenadas.append("MIS - Aporte Único")
    for i in range(5, 21):
        nombre = f"MSS - {i} Años"
        if nombre in planes_disponibles:
            opciones_ordenadas.append(nombre)

    if not opciones_ordenadas:
        st.error("No se encontraron archivos CSV de planes en la carpeta.")
        st.stop()

    seleccion = st.selectbox("Tipo de Plan", opciones_ordenadas)

    st.subheader("📆 Fecha de Inicio")
    min_year = int(df_mercado["Date"].dt.year.min())
    max_year = int(df_mercado["Date"].dt.year.max())

    years = list(range(min_year, max_year + 1))
    default_year = 2010 if 2010 in years else min_year

    c1, c2 = st.columns(2)
    with c1:
        anio_inicio = st.selectbox("Año Inicio", years, index=years.index(default_year))
    with c2:
        mes_inicio_txt = st.selectbox("Mes Inicio", LISTA_MESES, index=0)
        mes_inicio = mes_numero(mes_inicio_txt)

    nombre_cliente = st.text_input("Nombre Cliente", value="Cliente Ejemplo")

    aportes_extra = []
    retiros_programados = []

    archivo_csv, plazo_anios, tipo_plan = planes_disponibles[seleccion]

    if tipo_plan == "MIS":
        monto_input = st.number_input("Inversión Inicial (USD)", min_value=1000, value=10000, step=1000)

        with st.expander("➕ Aportes Adicionales"):
            if st.checkbox("Habilitar aportes extra"):
                for i in range(4):
                    st.divider()
                    a1, a2, a3 = st.columns([1.3, 1, 1.2])
                    with a1:
                        m_x = st.number_input(f"Monto {i+1}", min_value=0, value=0, step=1000, key=f"mx_{i}")
                    with a2:
                        an_x = st.number_input(
                            f"Año {i+1}",
                            min_value=min_year,
                            max_value=max_year,
                            value=min(anio_inicio + 1, max_year),
                            key=f"ax_{i}"
                        )
                    with a3:
                        me_x_txt = st.selectbox(f"Mes {i+1}", LISTA_MESES, key=f"mex_{i}")
                        me_x = mes_numero(me_x_txt)

                    if m_x > 0:
                        aportes_extra.append({"monto": m_x, "anio": an_x, "mes": me_x})

    else:
        monto_input = st.number_input("Aporte periódico (USD)", min_value=150, value=500, step=50)
        frecuencia_pago = st.selectbox("Frecuencia", ["Mensual", "Trimestral", "Semestral", "Anual"])

    with st.expander("💸 Retiros Parciales"):
        if st.checkbox("Habilitar retiros"):
            for i in range(3):
                st.divider()
                r1, r2, r3 = st.columns([1.3, 1, 1.2])
                with r1:
                    m_r = st.number_input(f"Retiro {i+1}", min_value=0, value=0, step=1000, key=f"mr_{i}")
                with r2:
                    an_r = st.number_input(
                        f"Año retiro {i+1}",
                        min_value=min_year,
                        max_value=max_year,
                        value=min(anio_inicio + 5, max_year),
                        key=f"ar_{i}"
                    )
                with r3:
                    me_r_txt = st.selectbox(f"Mes retiro {i+1}", LISTA_MESES, key=f"mer_{i}")
                    me_r = mes_numero(me_r_txt)

                if m_r > 0:
                    retiros_programados.append({"monto": m_r, "anio": an_r, "mes": me_r})

generar = st.button("Generar Ilustración", type="primary")

if generar:
    try:
        if tipo_plan == "MIS":
            df_resultado = simular_mis(
                df_base=df_mercado,
                monto_inicial=float(monto_input),
                anio_inicio=int(anio_inicio),
                mes_inicio=int(mes_inicio),
                aportes_extra=aportes_extra,
                retiros_programados=retiros_programados
            )
            subtitulo = f"Estrategia ({1 + len(aportes_extra)} aportes)"
        else:
            df_resultado = simular_mss(
                df_base=df_mercado,
                plazo_anios=int(plazo_anios),
                monto_aporte=float(monto_input),
                frecuencia_pago=frecuencia_pago,
                anio_inicio=int(anio_inicio),
                mes_inicio=int(mes_inicio),
                retiros_programados=retiros_programados
            )
            subtitulo = f"Aporte {frecuencia_pago}: {fmt_usd(monto_input)}"

        resumen = construir_resumen_anual(df_resultado)
        fig_principal = crear_figura_principal(df_resultado, resumen, seleccion, nombre_cliente, subtitulo)

        st.success("✅ Ilustración generada.")
        st.pyplot(fig_principal, use_container_width=True)

        st.subheader("Resumen anual")

        mostrar = preparar_tabla_mostrar(resumen)

        styled = (
            mostrar.style
            .format({
                "Aporte acumulado": fmt_usd,
                "Retiro": fmt_usd,
                "Valor en cuenta": fmt_usd,
                "Valor de rescate": fmt_usd,
                "Rendimiento": fmt_pct,
                "Rendimiento acumulado": fmt_pct,
            })
            .set_properties(**{
                "font-size": "11px",
                "text-align": "center",
                "white-space": "nowrap"
            })
            .set_table_styles([
                {
                    "selector": "th",
                    "props": [
                        ("background-color", "#40466e"),
                        ("color", "white"),
                        ("font-weight", "bold"),
                        ("text-align", "center"),
                        ("font-size", "11px"),
                    ]
                },
                {
                    "selector": "td",
                    "props": [
                        ("padding", "6px 10px"),
                    ]
                }
            ])
            .apply(
                lambda row: [
                    "color: #D4AC0D; font-weight: bold;" if (
                        col == "Valor de rescate" and row["Valor de rescate"] < row["Aporte acumulado"]
                    ) else ""
                    for col in row.index
                ],
                axis=1
            )
        )

        st.dataframe(styled, use_container_width=True, hide_index=True)

        tabla_export = mostrar.copy()
        tabla_export["Aporte acumulado"] = tabla_export["Aporte acumulado"].map(fmt_usd)
        tabla_export["Retiro"] = tabla_export["Retiro"].map(fmt_usd)
        tabla_export["Valor en cuenta"] = tabla_export["Valor en cuenta"].map(fmt_usd)
        tabla_export["Valor de rescate"] = tabla_export["Valor de rescate"].map(fmt_usd)
        tabla_export["Rendimiento"] = tabla_export["Rendimiento"].map(fmt_pct)
        tabla_export["Rendimiento acumulado"] = tabla_export["Rendimiento acumulado"].map(fmt_pct)

        c1, c2, c3 = st.columns(3)

        with c1:
            excel_data = generar_tabla_excel(tabla_export)
            if excel_data:
                st.download_button(
                    "📥 Descargar tabla en Excel",
                    data=excel_data,
                    file_name=f"Tabla_Resumen_{nombre_cliente}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Exportación a Excel no disponible (falta instalar openpyxl).")

        with c2:
            st.download_button(
                "📥 Descargar tabla en PDF",
                data=generar_tabla_pdf(tabla_export, titulo=f"Resumen anual - {nombre_cliente}"),
                file_name=f"Tabla_Resumen_{nombre_cliente}.pdf",
                mime="application/pdf"
            )

        with c3:
            st.download_button(
                "📥 Descargar ilustración completa en PDF",
                data=generar_pdf_completo(fig_principal, tabla_export, nombre_cliente),
                file_name=f"Ilustracion_{nombre_cliente}.pdf",
                mime="application/pdf"
            )

    except Exception:
        st.error("❌ Ocurrió un error al generar la ilustración.")
        st.code(traceback.format_exc())