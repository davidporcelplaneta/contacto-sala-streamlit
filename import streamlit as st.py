import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.set_page_config(page_title="Carga SALA - Premium Numbers", layout="wide")
st.title("📊 Carga de contactos SALA para Premium Numbers")

# --- SUBIR ARCHIVOS ---
st.header("1. Subida de archivos")
bruto_file = st.file_uploader("Sube el archivo bruto (.xlsx)", type="xlsx")
listanegra_file = st.file_uploader("Sube el archivo listanegra (.xlsx)", type="xlsx")
deduplicador_file = st.file_uploader("Sube el archivo deduplicador (.xlsx)", type="xlsx")

if bruto_file and listanegra_file and deduplicador_file:
    # --- LEER CSV ---
    sample = bruto_file.read(1000).decode("utf-8", errors="replace")
    sep = ";" if ";" in sample else ("\t" if "\t" in sample else ",")
    bruto_file.seek(0)
    df = pd.read_csv(bruto_file, sep=sep, engine="python", on_bad_lines="skip")

    # --- FILTRADO INICIAL ---
    columnas_deseadas = ["enlace", "nombre", "empresa", "puesto","telefono" ]
    
    df = df.rename(columns={
    "enlace": "profile_url",
    "nombre": "nombrecompleto",
    "empresa": "current_company",
    "puesto": "current_company_position",
    "telefono": "telefono",
    
})

    df_filtrado = df[[col for col in columnas_deseadas if col in df.columns]]
    # df_filtrado["nombrecompleto"] = df_filtrado["original_first_name"].astype(str) + " " + df_filtrado["original_last_name"].astype(str)
    # df_filtrado = df_filtrado.drop(columns=["original_first_name", "original_last_name"])
    df_filtrado["tipo_registro"] = 'SALA'

    # --- LEER EXCELS ---
    df_lista_negra = pd.read_excel(listanegra_file)
    df_deduplicador = pd.read_excel(deduplicador_file)

    # --- NORMALIZAR ---
    def normalizar(df, cols):
        for col in cols:
            df[col] = df[col].astype(str).str.strip().str.lower()
        return df

    df_filtrado = normalizar(df_filtrado, ["profile_url", "current_company", "current_company_position"])
    df_lista_negra = normalizar(df_lista_negra, ["enlace", "empresa", "puesto"])
    df_deduplicador = normalizar(df_deduplicador, ["enlace", "empresa", "puesto"])

    df_filtrado['profile_url_lower'] = df_filtrado['profile_url']
    df_filtrado['current_company_lower'] = df_filtrado['current_company']
    df_filtrado['current_company_position_lower'] = df_filtrado['current_company_position']

    # --- DEDUPLICAR LISTA NEGRA ---
    con_nombre = df_filtrado[df_filtrado['nombrecompleto'].isin(df_lista_negra['nombre'])]
    sin_nombre = df_filtrado[~df_filtrado['nombrecompleto'].isin(df_lista_negra['nombre'])]
    con_nombre = con_nombre[~con_nombre['profile_url_lower'].isin(df_lista_negra['enlace'])]
    con_nombre = con_nombre[~con_nombre['current_company_lower'].isin(df_lista_negra['empresa'])]
    con_nombre = con_nombre[~con_nombre['current_company_position_lower'].isin(df_lista_negra['puesto'])]
    df_neto_v1 = pd.concat([con_nombre, sin_nombre], ignore_index=True)

    # --- DEDUPLICADOR HISTÓRICO ---
    con_nombre_1 = df_neto_v1[df_neto_v1['nombrecompleto'].isin(df_deduplicador['nombre'])]
    sin_nombre_1 = df_neto_v1[~df_neto_v1['nombrecompleto'].isin(df_deduplicador['nombre'])]
    con_nombre_1 = con_nombre_1[~con_nombre_1['profile_url_lower'].isin(df_deduplicador['enlace'])]
    con_nombre_1 = con_nombre_1[~con_nombre_1['current_company_lower'].isin(df_deduplicador['empresa'])]
    con_nombre_1 = con_nombre_1[~con_nombre_1['current_company_position_lower'].isin(df_deduplicador['puesto'])]
    df_neto_v2 = pd.concat([con_nombre_1, sin_nombre_1], ignore_index=True)
    df_neto_v2 = df_neto_v2.drop(columns=['profile_url_lower', 'current_company_lower', 'current_company_position_lower'], errors='ignore')

    # --- PROCESAR SALIDA FINAL ---
    columnas_a_eliminar = ['headline', 'location_name', 'industry', 'organization_url_1']
    df_neto_v2 = df_neto_v2.drop(columns=columnas_a_eliminar, errors='ignore')
    fecha_str = datetime.today().strftime('%d%m%Y')
    df_final_PN = pd.DataFrame({
        'Nombre': df_neto_v2['nombrecompleto'],
        'Numero': [f"{fecha_str}{str(i+1).zfill(4)}" for i in range(len(df_neto_v2))],
        'Agente': '', 'Grupo': 'Inercia', 'General (SI/NO/MOD)': 'MOD', 'Observaciones': '',
        'Numero2': df_neto_v2['telefono'], 'Numero3': '', 'Fax': '', 'Correo': '',
        'Base de Datos': 'SALA_' + datetime.today().strftime('%Y-%m-%d'),
        'GESTION LISTADO PROPIO': '', 'ENLACE LINKEDIN': df_neto_v2['profile_url'],
        'PUESTO': df_neto_v2['current_company_position'], 'TELEOPERADOR': '', 'NUMERO DATO': '',
        'EMPRESA': df_neto_v2['current_company'], 'FECHA DE CONTACTO': '',
        'FECHA DE CONTACTO (NO USAR)': '', 'FORMACION': '', 'TITULACION': '', 'EDAD': '',
        'CUALIFICA': '', 'RESULTADO': '', 'FECHA DE CITA': '', 'FECHA DE CITA (NO USAR)': '',
        'CITA': '', 'ORIGEN DATO': df_neto_v2['tipo_registro'], 'ASESOR': '',
        'RESULTADO ASESOR': '', 'OBSERVACIONES ASESOR': '', 'BUSQUEDA FECHA': ''
    })

    # --- DESCARGA DEL CSV ---
    st.header("2. Descarga del resultado")
    csv = df_final_PN.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.download_button("📥 Descargar fichero de carga SALA", csv, file_name="SALA Cargar Contactos PN.csv", mime="text/csv")

    st.success(f"✅ Registros procesados: {len(df_final_PN)}")
else:
    st.warning("⚠️ Sube los tres archivos para continuar.")


