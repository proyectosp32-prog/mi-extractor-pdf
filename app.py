import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configuración visual de la web
st.set_page_config(page_title="Extractor Multi-PDF Honest", layout="wide")
st.title("📦 Extractor de Inventario Multi-PDF")
st.markdown("Sube **uno o varios** PDFs y genera una lista combinada automáticamente.")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración de Filtros")
proveedor = st.sidebar.text_input("Proveedor a buscar", "HONEST LAB")
col_nombre = st.sidebar.number_input("Columna Nombre (Índice)", value=4)
col_cantidad = st.sidebar.number_input("Columna Cantidad (Índice)", value=10)
indices_extra_str = st.sidebar.text_input("Columnas extra (ej: 6, 7)", "6, 7")

st.sidebar.markdown("---")
agrupar = st.sidebar.checkbox("Agrupar y sumar todos los archivos", value=True)
limpiar_num = st.sidebar.checkbox("Quitar números finales (01, 02...)", value=True)

# --- SUBIDA DE ARCHIVOS (Ahora acepta varios) ---
archivos_subidos = st.file_uploader("Sube aquí tus PDFs", type="pdf", accept_multiple_files=True)

if archivos_subidos:
    indices_extra = [int(i.strip()) for i in indices_extra_str.split(",") if i.strip()]
    datos_brutos = []

    with st.spinner('Procesando todos los archivos...'):
        # Bucle para recorrer cada archivo subido
        for archivo in archivos_subidos:
            with pdfplumber.open(archivo) as pdf:
                for pagina in pdf.pages:
                    tabla = pagina.extract_table()
                    if tabla:
                        for fila in tabla:
                            fila_texto = [str(celda).upper() for celda in fila if celda]
                            if any(proveedor.upper() in texto for texto in fila_texto):
                                try:
                                    nombre = str(fila[col_nombre]).replace('\n', ' ').strip()
                                    qty_raw = str(fila[col_cantidad])
                                    qty = int(''.join(filter(str.isdigit, qty_raw))) if any(c.isdigit() for c in qty_raw) else 0
                                    extras = [str(fila[i]).replace('\n', ' ').strip() if fila[i] else "" for i in indices_extra]
                                    
                                    datos_brutos.append([nombre] + extras + [qty])
                                except:
                                    continue

    if datos_brutos:
        nombres_col = ["Producto"] + [f"Info_{i}" for i in indices_extra] + ["Cantidad"]
        df = pd.DataFrame(datos_brutos, columns=nombres_col)

        if agrupar:
            if limpiar_num:
                df['Producto'] = df['Producto'].apply(lambda x: re.sub(r'\s*\d+\s*$', '', x))
            
            dict_agrup = {col: 'first' for col in df.columns if col != 'Producto'}
            dict_agrup['Cantidad'] = 'sum'
            df = df.groupby('Producto').agg(dict_agrup).reset_index()
            
            cols = [c for c in df.columns if c != 'Cantidad'] + ['Cantidad']
            df = df[cols].sort_values(by='Cantidad', ascending=False)

        st.success(f"¡Hecho! Se han procesado {len(archivos_subidos)} archivos y encontrado {len(df)} tipos de productos.")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Inventario Combinado (CSV)",
            data=csv,
            file_name=f"inventario_COMBINADO_{proveedor.replace(' ','_')}.csv",
            mime='text/csv',
        )
