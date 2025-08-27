import streamlit as st
import pandas as pd
from datetime import datetime

# =================== CONFIG INICIAL ===================
st.set_page_config(page_title="Carga SALA - Premium Numbers", layout="wide")
st.title("📊 Carga de contactos SALA para Premium Numbers")

# =================== BLOQUE DE DEPURACIÓN ===================
# Activa/desactiva el modo detallado desde la UI (barra lateral)
DEBUG = st.sidebar.toggle("🛠️ Modo depuración", value=True)

def _df_info(df: pd.DataFrame, name: str):
    """Muestra forma, nulos y 5 primeras filas."""
    if not DEBUG:
        return
    st.markdown(f"### 🔍 {name}")
    st.write("shape:", df.shape)
    if df is not None and not df.empty:
        nulls = df.isna().sum().sort_values(ascending=False)
        st.write("nulos por columna (top 10):", nulls.head(10))
        st.write(df.head(5))
    else:
        st.write("DataFrame vacío.")

def _col_check(df: pd.DataFrame, cols, ctx=""):
    """Avisa si faltan columnas clave."""
    if not DEBUG:
        return
    faltan = [c for c in cols if c not in df.columns]
    if faltan:
        st.warning(f"⚠️ Faltan columnas en {ctx}: {faltan}")

def _download(df: pd.DataFrame, name: str):
    """Botón para descargar un CSV intermedio (útil para revisar fuera)."""
    if not DEBUG or df is None or df.empty:
        return
    st.download_button(
        f"⬇️ Descargar intermedio: {name}.csv",
        df.to_csv(index=False, sep=';', encoding='utf-8-sig'),
        file_name=f"{name}.csv",
        mime="text/csv"
    )

def _normaliza_col(df: pd.DataFrame, col: str):
    """Normaliza en minúsculas/strip si existe; no rompe si falta."""
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.lower()
    return df

def _conjunto(df: pd.DataFrame, col: str):
    """Devuelve conjunto único de una columna (o vacío)."""
    if col in df.columns and not df.empty:
        return set(df[col].dropna().unique())
    return set()

def _interseccion_info(set_a, set_b, titulo):
    """Muestra tamaño de intersección entre dos conjuntos."""
    if not DEBUG:
        return
    inter = set_a & set_b
    st.write(f"🔗 {titulo}: |A|={len(set_a)}, |B|={len(set_b)}, intersección={len(inter)}")
    if len(inter) > 0:
        st.write("Ejemplos intersección:", list(inter)[:5])
# =================== FIN BLOQUE DEPURACIÓN ===================


# =================== SUBIDA DE ARCHIVOS ===================
st.header("1. Subida de archivos")
bruto_file = st.file_uploader("Sube el archivo bruto (.xlsx)", type="xlsx")
listanegra_file = st.file_uploader("Sube el archivo listanegra (.xlsx)", type="xlsx")
deduplicador_file = st.file_uploader("Sube el archivo deduplicador (.xlsx)", type="xlsx")


if bruto_file and listanegra_file and deduplicador_file:
    # ---------- LEER BRUTO ----------
    df = pd.read_excel(bruto_file)
    _df_info(df, "Bruto (antes de renombrar)")
    _col_check(df, ["enlace", "nombre", "empresa", "puesto", "telefono"], "Bruto original")

    # ---------- RENOMBRAR A NOMBRES INTERNOS ----------
    df = df.rename(columns={
        "enlace": "profile_url",
        "nombre": "nombrecompleto",
        "empresa": "current_company",
        "puesto": "current_company_position",
        "telefono": "telefono"
    })

    # ---------- SELECCIONAR COLUMNAS EXISTENTES ----------
    keep_cols = ["profile_url", "nombrecompleto", "current_company", "current_company_position", "telefono"]
    keep_cols = [c for c in keep_cols if c in df.columns]
    df_filtrado = df[keep_cols].copy()
    df_filtrado["tipo_registro"] = "SALA"

    _df_info(df_filtrado, "Filtrado (tras renombrar/seleccionar)")
    _col_check(df_filtrado, ["profile_url", "nombrecompleto", "current_company", "current_company_position", "telefono"], "Filtrado")

    # ---------- NORMALIZAR SOLO ENLACE ----------
    df_filtrado = _normaliza_col(df_filtrado, "profile_url")
    _df_info(df_filtrado, "Filtrado normalizado (profile_url)")
    _download(df_filtrado, "intermedio_filtrado")

    # ---------- LEER LISTA NEGRA E HISTÓRICO ----------
    df_lista_negra = pd.read_excel(listanegra_file).rename(columns={"enlace": "profile_url"})
    df_deduplicador = pd.read_excel(deduplicador_file).rename(columns={"enlace": "profile_url"})
    _df_info(df_lista_negra, "Lista negra (cruda)")
    _df_info(df_deduplicador, "Histórico (crudo)")

    # ---------- NORMALIZAR SOLO ENLACE EN AUXILIARES ----------
    df_lista_negra = _normaliza_col(df_lista_negra, "profile_url")
    df_deduplicador = _normaliza_col(df_deduplicador, "profile_url")
    _df_info(df_lista_negra, "Lista negra (normalizada)")
    _df_info(df_deduplicador, "Histórico (normalizado)")

    # ---------- LIMPIEZA INTERNA: DROPNA + DEDUP POR ENLACE ----------
    if "profile_url" in df_filtrado.columns:
        antes = df_filtrado.shape[0]
        df_filtrado = df_filtrado.dropna(subset=["profile_url"]).drop_duplicates(subset=["profile_url"])
        despues = df_filtrado.shape[0]
        if DEBUG:
            st.info(f"🧹 Duplicados internos por profile_url: {antes} → {despues}")
    _df_info(df_filtrado, "Tras dropna+drop_duplicates (profile_url)")

    # ---------- INTERSECCIONES (para medir recorte antes de filtrar) ----------
    set_bruto = _conjunto(df_filtrado, "profile_url")
    set_black = _conjunto(df_lista_negra, "profile_url")
    set_hist  = _conjunto(df_deduplicador, "profile_url")
    _interseccion_info(set_bruto, set_black, "Bruto vs Lista Negra (profile_url)")
    _interseccion_info(set_bruto, set_hist,  "Bruto vs Histórico (profile_url)")

    # ---------- APLICAR LISTA NEGRA (SOLO ENLACE) ----------
    if "profile_url" in df_lista_negra.columns and not df_lista_negra.empty:
        black_set = set(df_lista_negra["profile_url"].dropna().unique())
        df_neto_v1 = df_filtrado[~df_filtrado["profile_url"].isin(black_set)].copy()
    else:
        df_neto_v1 = df_filtrado.copy()
    _df_info(df_neto_v1, "Tras filtrar Lista Negra")
    _download(df_neto_v1, "intermedio_post_lista_negra")

    # ---------- APLICAR HISTÓRICO (SOLO ENLACE) ----------
    if "profile_url" in df_deduplicador.columns and not df_deduplicador.empty:
        hist_set = set(df_deduplicador["profile_url"].dropna().unique())
        df_neto_v2 = df_neto_v1[~df_neto_v1["profile_url"].isin(hist_set)].copy()
    else:
        df_neto_v2 = df_neto_v1.copy()
    _df_info(df_neto_v2, "Tras filtrar Histórico")
    _download(df_neto_v2, "intermedio_post_historico")

    # ---------- PREVIO A SALIDA FINAL ----------
    _col_check(df_neto_v2, ["profile_url", "nombrecompleto", "telefono", "current_company", "current_company_position", "tipo_registro"], "Previo CSV")
    _df_info(df_neto_v2, "Previo a salida final")

    # ---------- CONSTRUIR SALIDA FINAL ----------
    # Asegurar columnas para evitar KeyError
    for c in ["nombrecompleto", "profile_url", "current_company_position", "current_company", "telefono", "tipo_registro"]:
        if c not in df_neto_v2.columns:
            df_neto_v2[c] = ""

    fecha_str = datetime.today().strftime('%d%m%Y')
    base_nombre = 'SALA_' + datetime.today().strftime('%Y-%m-%d')

    df_final_PN = pd.DataFrame({
        'Nombre': df_neto_v2['nombrecompleto'],
        'Numero': [f"{fecha_str}{str(i+1).zfill(4)}" for i in range(len(df_neto_v2))],
        'Agente': '',
        'Grupo': 'Inercia',
        'General (SI/NO/MOD)': 'MOD',
        'Observaciones': '',
        'Numero2': df_neto_v2['telefono'],   # teléfono real
        'Numero3': '',
        'Fax': '',
        'Correo': '',
        'Base de Datos': base_nombre,
        'GESTION LISTADO PROPIO': '',
        'ENLACE LINKEDIN': df_neto_v2['profile_url'],
        'PUESTO': df_neto_v2['current_company_position'],
        'TELEOPERADOR': '',
        'NUMERO DATO': '',
        'EMPRESA': df_neto_v2['current_company'],
        'FECHA DE CONTACTO': '',
        'FECHA DE CONTACTO (NO USAR)': '',
        'FORMACION': '',
        'TITULACION': '',
        'EDAD': '',
        'CUALIFICA': '',
        'RESULTADO': '',
        'FECHA DE CITA': '',
        'FECHA DE CITA (NO USAR)': '',
        'CITA': '',
        'ORIGEN DATO': df_neto_v2['tipo_registro'],
        'ASESOR': '',
        'RESULTADO ASESOR': '',
        'OBSERVACIONES ASESOR': '',
        'BUSQUEDA FECHA': ''
    })

    # Vista previa opcional del resultado
    _df_info(df_final_PN, "Vista previa resultado final")
    _download(df_final_PN, "resultado_final_previo_descarga")

    # ---------- DESCARGA DEL CSV ----------
    st.header("2. Descarga del resultado")
    csv = df_final_PN.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.download_button("📥 Descargar fichero de carga SALA", csv, file_name="SALA Cargar Contactos PN.csv", mime="text/csv")

    st.success(f"✅ Registros procesados: {len(df_final_PN)}")

else:
    st.warning("⚠️ Sube los tres archivos para continuar.")
