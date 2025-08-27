import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Carga SALA - Premium Numbers", layout="wide")
st.title("📊 Carga de contactos SALA para Premium Numbers")

# --- SUBIR ARCHIVOS ---
st.header("1. Subida de archivos")
bruto_file = st.file_uploader("Sube el archivo bruto (.xlsx)", type="xlsx")
listanegra_file = st.file_uploader("Sube el archivo listanegra (.xlsx)", type="xlsx")
deduplicador_file = st.file_uploader("Sube el archivo deduplicador (.xlsx)", type="xlsx")

# Helpers
def normalizar_cols(df_: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Normaliza a str, strip y lower solo las columnas existentes."""
    for c in cols:
        if c in df_.columns:
            df_[c] = df_[c].astype(str).str.strip().str.lower()
    return df_

def series_vacia_like(df_: pd.DataFrame) -> pd.Series:
    """Devuelve una serie vacía (del tamaño del df) para usar en isin sin romper."""
    return pd.Series([], dtype=str)

def get_col(df_: pd.DataFrame, col: str) -> pd.Series:
    """Obtiene la columna si existe; si no, una serie vacía."""
    return df_[col] if col in df_.columns else series_vacia_like(df_)

if bruto_file and listanegra_file and deduplicador_file:
    # --- LEER EXCELS ---
    df = pd.read_excel(bruto_file)
    df_lista_negra = pd.read_excel(listanegra_file)
    df_deduplicador = pd.read_excel(deduplicador_file)

    # --- FILTRADO + RENOMBRE (orden coherente) ---
    cols_originales = ["enlace", "nombre", "empresa", "puesto", "telefono"]
    df_filtrado = df[[c for c in cols_originales if c in df.columns]].copy()

    df_filtrado = df_filtrado.rename(columns={
        "enlace": "profile_url",
        "nombre": "nombrecompleto",
        "empresa": "current_company",
        "puesto": "current_company_position",
        # "telefono" se mantiene igual
    })

    # Asegurar que existen las columnas esenciales aunque vengan ausentes
    for needed in ["profile_url", "nombrecompleto", "current_company", "current_company_position", "telefono"]:
        if needed not in df_filtrado.columns:
            df_filtrado[needed] = ""

    df_filtrado["tipo_registro"] = "SALA"

    # --- NORMALIZAR CAMPOS QUE SE COMPARAN ---
    df_filtrado = normalizar_cols(
        df_filtrado,
        ["profile_url", "current_company", "current_company_position", "nombrecompleto"]
    )
    df_lista_negra = normalizar_cols(
        df_lista_negra,
        ["enlace", "empresa", "puesto", "nombre"]
    )
    df_deduplicador = normalizar_cols(
        df_deduplicador,
        ["enlace", "empresa", "puesto", "nombre"]
    )

    # --- EXCLUSIÓN POR LISTA NEGRA (cualquier coincidencia) ---
    mask_bl = (
        df_filtrado["nombrecompleto"].isin(get_col(df_lista_negra, "nombre")) |
        df_filtrado["profile_url"].isin(get_col(df_lista_negra, "enlace")) |
        df_filtrado["current_company"].isin(get_col(df_lista_negra, "empresa")) |
        df_filtrado["current_company_position"].isin(get_col(df_lista_negra, "puesto"))
    )
    df_neto_v1 = df_filtrado.loc[~mask_bl].copy()

    # --- EXCLUSIÓN POR DEDUPLICADOR HISTÓRICO (cualquier coincidencia) ---
    mask_hist = (
        df_neto_v1["nombrecompleto"].isin(get_col(df_deduplicador, "nombre")) |
        df_neto_v1["profile_url"].isin(get_col(df_deduplicador, "enlace")) |
        df_neto_v1["current_company"].isin(get_col(df_deduplicador, "empresa")) |
        df_neto_v1["current_company_position"].isin(get_col(df_deduplicador, "puesto"))
    )
    df_neto_v2 = df_neto_v1.loc[~mask_hist].copy()

    # --- PROCESAR SALIDA FINAL ---
    columnas_a_eliminar = ['headline', 'location_name', 'industry', 'organization_url_1']
    df_neto_v2 = df_neto_v2.drop(columns=columnas_a_eliminar, errors='ignore')

    # Asegurar columnas usadas más adelante existen
    for needed in ["nombrecompleto", "telefono", "profile_url", "current_company_position", "current_company", "tipo_registro"]:
        if needed not in df_neto_v2.columns:
            df_neto_v2[needed] = ""

    fecha_str = datetime.today().strftime('%d%m%Y')
    base_fecha = datetime.today().strftime('%Y-%m-%d')

    df_final_PN = pd.DataFrame({
        'Nombre': df_neto_v2['nombrecompleto'].fillna(''),
        'Numero': [f"{fecha_str}{str(i+1).zfill(4)}" for i in range(len(df_neto_v2))],
        'Agente': '',
        'Grupo': 'Inercia',
        'General (SI/NO/MOD)': 'MOD',
        'Observaciones': '',
        'Numero2': df_neto_v2['telefono'].astype(str).fillna(''),
        'Numero3': '',
        'Fax': '',
        'Correo': '',
        'Base de Datos': 'SALA_' + base_fecha,
        'GESTION LISTADO PROPIO': '',
        'ENLACE LINKEDIN': df_neto_v2['profile_url'].fillna(''),
        'PUESTO': df_neto_v2['current_company_position'].fillna(''),
        'TELEOPERADOR': '',
        'NUMERO DATO': '',
        'EMPRESA': df_neto_v2['current_company'].fillna(''),
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
        'ORIGEN DATO': df_neto_v2['tipo_registro'].fillna(''),
        'ASESOR': '',
        'RESULTADO ASESOR': '',
        'OBSERVACIONES ASESOR': '',
        'BUSQUEDA FECHA': ''
    })

    # --- DESCARGA DEL CSV ---
    st.header("2. Descarga del resultado")
    csv = df_final_PN.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.download_button(
        "📥 Descargar fichero de carga SALA",
        data=csv,
        file_name="SALA Cargar Contactos PN.csv",
        mime="text/csv"
    )

    st.success(f"✅ Registros procesados: {len(df_final_PN)}")

else:
    st.warning("⚠️ Sube los tres archivos para continuar.")
