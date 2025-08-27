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

def normalizar_cols(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().str.lower()
    return df

if bruto_file and listanegra_file and deduplicador_file:
    # --- LEER EXCEL BRUTO ---
    df = pd.read_excel(bruto_file)

    # --- RENOMBRAR A NOMBRES INTERNOS CONSISTENTES ---
    # Ajusta aquí si tus columnas reales tienen otros nombres
    df = df.rename(columns={
        "enlace": "profile_url",
        "nombre": "nombrecompleto",
        "empresa": "current_company",
        "puesto": "current_company_position",
        "telefono": "telefono"
    })

    # --- SELECCIONAR COLUMNAS YA RENOMBRADAS ---
    columnas_finales = ["profile_url", "nombrecompleto", "current_company", "current_company_position", "telefono"]
    existentes = [c for c in columnas_finales if c in df.columns]
    df_filtrado = df[existentes].copy()
    df_filtrado["tipo_registro"] = "SALA"

    # --- LEER EXCELS AUXILIARES ---
    df_lista_negra = pd.read_excel(listanegra_file)
    df_deduplicador = pd.read_excel(deduplicador_file)

    # Para trabajar cómodos, renombramos posibles columnas de los auxiliares a los mismos nombres internos
    # (si existen con nombres "clásicos"). Si ya vienen con los nombres internos, no pasa nada.
    df_lista_negra = df_lista_negra.rename(columns={
        "enlace": "profile_url",
        "nombre": "nombrecompleto",
        "empresa": "current_company",
        "puesto": "current_company_position"
    })
    df_deduplicador = df_deduplicador.rename(columns={
        "enlace": "profile_url",
        "nombre": "nombrecompleto",
        "empresa": "current_company",
        "puesto": "current_company_position"
    })

    # --- NORMALIZAR (solo columnas existentes) ---
    norm_cols = ["profile_url", "nombrecompleto", "current_company", "current_company_position"]
    df_filtrado = normalizar_cols(df_filtrado, norm_cols)
    df_lista_negra = normalizar_cols(df_lista_negra, norm_cols)
    df_deduplicador = normalizar_cols(df_deduplicador, norm_cols)

    # --- APLICAR LISTA NEGRA (excluir si coincide en cualquiera de los 4 campos) ---
    # Construimos conjuntos por columna existente en ambos dataframes
    def build_sets(df_ref, cols):
        return {c: set(df_ref[c].dropna().unique()) for c in cols if c in df_ref.columns}

    sets_black = build_sets(df_lista_negra, norm_cols)
    # Filtro: conservar filas que NO estén en la lista negra por NINGÚN campo
    mask_black = pd.Series([True] * len(df_filtrado), index=df_filtrado.index)
    for c, s in sets_black.items():
        if c in df_filtrado.columns and len(s) > 0:
            mask_black &= ~df_filtrado[c].isin(s)
    df_neto_v1 = df_filtrado[mask_black].copy()

    # --- APLICAR DEDUPLICADOR HISTÓRICO ---
    sets_dedupe = build_sets(df_deduplicador, norm_cols)
    mask_dedupe = pd.Series([True] * len(df_neto_v1), index=df_neto_v1.index)
    for c, s in sets_dedupe.items():
        if c in df_neto_v1.columns and len(s) > 0:
            mask_dedupe &= ~df_neto_v1[c].isin(s)
    df_neto_v2 = df_neto_v1[mask_dedupe].copy()

    # --- PROCESAR SALIDA FINAL ---
    fecha_str = datetime.today().strftime('%d%m%Y')
    base_nombre = 'SALA_' + datetime.today().strftime('%Y-%m-%d')

    # Asegurar columnas faltantes
    for c in ["nombrecompleto", "profile_url", "current_company_position", "current_company", "telefono", "tipo_registro"]:
        if c not in df_neto_v2.columns:
            df_neto_v2[c] = ""

    df_final_PN = pd.DataFrame({
        'Nombre': df_neto_v2['nombrecompleto'],
        'Numero': [f"{fecha_str}{str(i+1).zfill(4)}" for i in range(len(df_neto_v2))],
        'Agente': '',
        'Grupo': 'Inercia',
        'General (SI/NO/MOD)': 'MOD',
        'Observaciones': '',
        'Numero2': df_neto_v2['telefono'],  # número real
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

    # --- DESCARGA DEL CSV ---
    st.header("2. Descarga del resultado")
    csv = df_final_PN.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.download_button("📥 Descargar fichero de carga SALA", csv, file_name="SALA Cargar Contactos PN.csv", mime="text/csv")

    st.success(f"✅ Registros procesados: {len(df_final_PN)}")
else:
    st.warning("⚠️ Sube los tres archivos para continuar.")
