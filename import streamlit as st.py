# app.py
import io
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Deduplicador Contactos", page_icon="🧹", layout="wide")

EXPECTED_COLUMNS = ['enlace']

# --------------------------
# Normalización
# --------------------------
def normalize_phone(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.replace(r"\D+", "", regex=True)
    return s.replace({"": np.nan})

def normalize_text(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.lower()
    s = s.str.replace(r"\s+", " ", regex=True)
    return s.replace({"nan": np.nan, "none": np.nan, "nat": np.nan})

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    missing = set(EXPECTED_COLUMNS) - set(out.columns)
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {sorted(missing)}")
    out = out[EXPECTED_COLUMNS]
    for col in ['enlace']:
        out[col] = normalize_text(out[col])
    out['telefono'] = normalize_phone(out['telefono'])
    return out

# --------------------------
# Deduplicado
# --------------------------
def anti_join_all_columns(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    if right is None or right.empty:
        return left.copy()
    merged = left.merge(right, on=EXPECTED_COLUMNS, how="left", indicator=True)
    return merged[merged["_merge"] == "left_only"].drop(columns="_merge")

def remove_if_any_column_matches(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    if right is None or right.empty:
        return left.copy()
    keep_mask = pd.Series(True, index=left.index)
    for col in EXPECTED_COLUMNS:
        targets = right[col].dropna().unique()
        if len(targets) == 0:
            continue
        keep_mask &= ~left[col].isin(targets)
    return left[keep_mask]

def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        # Para el archivo de salida sí usamos un nombre de hoja fijo (no afecta a la lectura)
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    buf.seek(0)
    return buf.read()

# --------------------------
# UI
# --------------------------
st.title("🧹 Deduplicador de Contactos")
st.write(
    "1) **Lista negra**: elimina coincidencias exactas en todas las columnas.\n"
    "2) **Deduplicador**: elimina si coincide cualquiera de las columnas."
)

c1, c2, c3 = st.columns(3)
with c1:
    up_reparto = st.file_uploader("📥 Reparto (.xlsx)", type=["xlsx"])
with c2:
    up_black = st.file_uploader("🗑️ Lista negra (.xlsx)", type=["xlsx"])
with c3:
    up_dedupe = st.file_uploader("🧱 Deduplicador (.xlsx)", type=["xlsx"])

preview = st.checkbox("👁️ Previsualizar (primeras 10 filas)", value=True)

def read_first_sheet(uploaded):
    if not uploaded:
        return None
    try:
        # Lee la **primera hoja** (no forzamos nombre de hoja)
        # Equivalente: pd.read_excel(uploaded, sheet_name=0)
        return pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        return None

# Previsualización
pa, pb, pc = st.columns(3)
with pa:
    if up_reparto:
        raw = read_first_sheet(up_reparto)
        if raw is not None:
            st.caption(f"**Reparto** ({len(raw)} filas)")
            if preview: st.dataframe(raw.head(10))
with pb:
    if up_black:
        raw = read_first_sheet(up_black)
        if raw is not None:
            st.caption(f"**Lista negra** ({len(raw)} filas)")
            if preview: st.dataframe(raw.head(10))
with pc:
    if up_dedupe:
        raw = read_first_sheet(up_dedupe)
        if raw is not None:
            st.caption(f"**Deduplicador** ({len(raw)} filas)")
            if preview: st.dataframe(raw.head(10))

st.markdown("---")

# Ejecutar
if st.button("🚀 Ejecutar deduplicado"):
    if not up_reparto or not up_black or not up_dedupe:
        st.error("Sube los tres archivos: Reparto, Lista negra y Deduplicador.")
        st.stop()
    try:
        # 1) Leer primera hoja de cada archivo
        df_rep_raw = read_first_sheet(up_reparto)
        df_blk_raw = read_first_sheet(up_black)
        df_ddp_raw = read_first_sheet(up_dedupe)

        # 2) Normalizar
        df_rep = normalize_df(df_rep_raw)
        df_blk = normalize_df(df_blk_raw)
        df_ddp = normalize_df(df_ddp_raw)

        # 3) Anti-join exacto (lista negra)
        before_ln = len(df_rep)
        df_inter = anti_join_all_columns(df_rep, df_blk)
        removed_ln = before_ln - len(df_inter)

        # 4) Any-column match (deduplicador)
        before_dd = len(df_inter)
        df_final = remove_if_any_column_matches(df_inter, df_ddp)
        removed_dd = before_dd - len(df_final)


        # 4.1) Formato salida PN
        fecha_str = datetime.today().strftime('%d%m%Y')
        base_nombre = 'SALA_' + datetime.today().strftime('%Y-%m-%d')
        df_final["tipo_registro"] = "SALA"
        # columnas actuales ['enlace', 'nombre', 'empresa', 'puesto', 'telefono']
        df_final_PN = pd.DataFrame({
            'Nombre': df_final['nombre'],
            'Numero': [f"{fecha_str}{str(i+1).zfill(4)}" for i in range(len(df_final))],
            'Agente': '',
            'Grupo': 'Inercia',
            'General (SI/NO/MOD)': 'MOD',
            'Observaciones': '',
            'Numero2': df_final['telefono'],   # mantengo el teléfono real aquí
            'Numero3': '',
            'Fax': '',
            'Correo': '',
            'Base de Datos': base_nombre,
            'GESTION LISTADO PROPIO': '',
            'ENLACE LINKEDIN': df_final['enlace'],
            'PUESTO': df_final['puesto'],
            'TELEOPERADOR': '',
            'NUMERO DATO': '',
            'EMPRESA': df_final['empresa'],
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
            'ORIGEN DATO': df_final['tipo_registro'],
            'ASESOR': '',
            'RESULTADO ASESOR': '',
            'OBSERVACIONES ASESOR': '',
            'BUSQUEDA FECHA': ''
        })

        # 5) Métricas y resultados
        st.metric("Filas iniciales", before_ln)
        st.metric("Eliminadas por Lista Negra", removed_ln)
        st.metric("Eliminadas por Deduplicador", removed_dd)
        st.metric("Filas finales", len(df_final_PN))



        st.subheader("✅ Resultado final")
        st.dataframe(df_final_PN.head(50))

        # 6) Descargas
        st.download_button(
            "⬇️ Descargar resultado final",
            data=to_excel_bytes(df_final),
            file_name="contactos_reparto_final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except ValueError as ve:
        st.error(f"Validación de columnas: {ve}")
    except Exception as e:
        st.exception(e)








