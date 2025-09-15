# app.py
import io
import numpy as np
import pandas as pd
import streamlit as st

# --------------------------
# Configuración general
# --------------------------
st.set_page_config(page_title="Deduplicador Contactos", page_icon="🧹", layout="wide")

EXPECTED_COLUMNS = ['enlace', 'nombre', 'empresa', 'puesto', 'telefono']
SHEET_NAME = "Sheet1"  # fijo

# --------------------------
# Funciones de normalización
# --------------------------
def normalize_phone(s: pd.Series) -> pd.Series:
    s = s.astype(str)
    s = s.str.replace(r"\D+", "", regex=True)
    s = s.replace({"": np.nan})
    return s

def normalize_text(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.lower()
    s = s.str.replace(r"\s+", " ", regex=True)
    s = s.replace({"nan": np.nan, "none": np.nan, "nat": np.nan})
    return s

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]

    missing = set(EXPECTED_COLUMNS) - set(out.columns)
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {sorted(missing)}")

    out = out[EXPECTED_COLUMNS]
    for col in ['enlace', 'nombre', 'empresa', 'puesto']:
        out[col] = normalize_text(out[col])
    out['telefono'] = normalize_phone(out['telefono'])
    return out

# --------------------------
# Funciones de deduplicado
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
        df.to_excel(writer, index=False, sheet_name=SHEET_NAME)
    buf.seek(0)
    return buf.read()

# --------------------------
# Interfaz Streamlit
# --------------------------
st.title("🧹 Deduplicador de Contactos")

st.write(
    "1) **Lista negra**: elimina coincidencias exactas en todas las columnas.\n"
    "2) **Deduplicador**: elimina si coincide cualquiera de las columnas."
)

col1, col2, col3 = st.columns(3)
with col1:
    up_reparto = st.file_uploader("📥 Reparto", type=["xlsx"])
with col2:
    up_black = st.file_uploader("🗑️ Lista negra", type=["xlsx"])
with col3:
    up_dedupe = st.file_uploader("🧱 Deduplicador", type=["xlsx"])

preview = st.checkbox("👁️ Mostrar previsualización (primeras 10 filas)", value=True)

def read_excel_uploaded(uploaded):
    if not uploaded:
        return None
    try:
        return pd.read_excel(uploaded, sheet_name=SHEET_NAME)
    except Exception as e:
        st.error(f"Error leyendo el Excel: {e}")
        return None

# Previsualización
col_a, col_b, col_c = st.columns(3)
with col_a:
    if up_reparto:
        raw = read_excel_uploaded(up_reparto)
        if raw is not None:
            st.caption(f"**Reparto** ({len(raw)} filas)")
            if preview:
                st.dataframe(raw.head(10))
with col_b:
    if up_black:
        raw = read_excel_uploaded(up_black)
        if raw is not None:
            st.caption(f"**Lista negra** ({len(raw)} filas)")
            if preview:
                st.dataframe(raw.head(10))
with col_c:
    if up_dedupe:
        raw = read_excel_uploaded(up_dedupe)
        if raw is not None:
            st.caption(f"**Deduplicador** ({len(raw)} filas)")
            if preview:
                st.dataframe(raw.head(10))

st.markdown("---")

# Botón de ejecución
if st.button("🚀 Ejecutar deduplicado"):
    if not up_reparto or not up_black or not up_dedupe:
        st.error("Sube los tres archivos: Reparto, Lista negra y Deduplicador.")
        st.stop()

    try:
        # 1) Leer
        df_rep_raw = read_excel_uploaded(up_reparto)
        df_blk_raw = read_excel_uploaded(up_black)
        df_ddp_raw = read_excel_uploaded(up_dedupe)

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

        # 5) Métricas
        st.metric("Filas iniciales", before_ln)
        st.metric("Eliminadas por Lista Negra", removed_ln)
        st.metric("Eliminadas por Deduplicador", removed_dd)
        st.metric("Filas finales", len(df_final))

        st.subheader("📄 Resultado intermedio (tras Lista Negra)")
        st.dataframe(df_inter.head(50))

        st.subheader("✅ Resultado final")
        st.dataframe(df_final.head(50))

        # 6) Descargas
        inter_bytes = to_excel_bytes(df_inter)
        final_bytes = to_excel_bytes(df_final)

        st.download_button(
            "⬇️ Descargar intermedio (Lista Negra)",
            data=inter_bytes,
            file_name="contactos_reparto_deduplicado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.download_button(
            "⬇️ Descargar resultado final",
            data=final_bytes,
            file_name="contactos_reparto_final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except ValueError as ve:
        st.error(f"Validación de columnas: {ve}")
    except Exception as e:
        st.exception(e)


