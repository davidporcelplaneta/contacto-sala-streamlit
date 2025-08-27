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

def normalizar_columna(df, col):
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.lower()
    return df

if bruto_file and listanegra_file and deduplicador_file:
    # --- LEER BRUTO ---
    df = pd.read_excel(bruto_file)

    # RENOMBRAR a nombres internos
    df = df.rename(columns={
        "enlace": "profile_url",
        "nombre": "nombrecompleto",
        "empresa": "current_company",
        "puesto": "current_company_position",
        "telefono": "telefono"
    })

    # Seleccionar columnas existentes (tras renombrar)
    keep_cols = ["profile_url", "nombrecompleto", "current_company", "current_company_position", "telefono"]
    keep_cols = [c for c in keep_cols if c in df.columns]
    df_filtrado = df[keep_cols].copy()
    df_filtrado["tipo_registro"] = "SALA"

    # --- LEER LISTA NEGRA e HISTÓRICO ---
    df_lista_negra = pd.read_excel(listanegra_file).rename(columns={"enlace": "profile_url"})
    df_deduplicador = pd.read_excel(deduplicador_file).rename(columns={"enlace": "profile_url"})

    # --- NORMALIZAR SOLO 'profile_url' (enlace) ---
    df_filtrado = normalizar_columna(df_filtrado, "profile_url")
    df_lista_negra = normalizar_columna(df_lista_negra, "profile_url")
    df_deduplicador = normalizar_columna(df_deduplicador, "profile_url")

    # --- QUITAR DUPLICADOS DENTRO DEL PROPIO BRUTO (mismo enlace) ---
    if "profile_url" in df_filtrado.columns:
        df_filtrado = df_filtrado.dropna(subset=["profile_url"])
        df_filtrado = df_filtrado.drop_duplicates(subset=["profile_url"])

    # --- APLICAR LISTA NEGRA SOLO POR ENLACE ---
    if "profile_url" in df_lista_negra.columns and not df_lista_negra.empty:
        black_set = set(df_lista_negra["profile_url"].dropna().unique())
        df_neto_v1 = df_filtrado[~df_filtrado["profile_url"].isin(black_set)].copy()
    else:
        df_neto_v1 = df_filtrado.copy()

    # --- APLICAR HISTÓRICO SOLO POR ENLACE ---
    if "profile_url" in df_deduplicador.columns and not df_deduplicador.empty:
        hist_set = set(df_deduplicador["profile_url"].dropna().unique())
        df_neto_v2 = df_neto_v1[~df_neto_v1["profile_url"].isin(hist_set)].copy()
    else:
        df_neto_v2 = df_neto_v1.copy()

    # --- SALIDA FINAL ---
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
        'Numero2': df_neto_v2['telefono'],   # mantengo el teléfono real aquí
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

    st.header("2. Descarga del resultado")
    csv = df_final_PN.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.download_button("📥 Descargar fichero de carga SALA", csv, file_name="SALA Cargar Contactos PN.csv", mime="text/csv")

    st.success(f"✅ Registros procesados: {len(df_final_PN)}")
else:
    st.warning("⚠️ Sube los tres archivos para continuar.")


