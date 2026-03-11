import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configuración visual
st.set_page_config(page_title="Extractor Honest Final", layout="wide")
st.title("📦 Extractor de Inventario")
st.markdown("Búsqueda mejorada: Detecta 'Honest Lab' aunque esté pegado a otros textos.")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración de Filtros")
proveedor_fijo = st.sidebar.text_input("Proveedor a incluir siempre", "HONEST LAB")
palabras_extra_str = st.sidebar.text_input("Keywords obligatorias para otros proveedores", "STONE, TABLE")

st.sidebar.markdown("---")
col_nombre = st.sidebar.number_input("Columna Nombre (Índice)", value=4)
col_cantidad = st.sidebar.number_input("Columna Cantidad (Índice)", value=10)
indices_extra_str = st.sidebar.text_input("Otras columnas (ej: 6, 7)", "6, 7")

st.sidebar.markdown("---")
agrupar = st.sidebar.checkbox("Agrupar y sumar iguales", value=True)
limpiar_num = st.sidebar.checkbox("Quitar números finales (01, 02...)", value=True)
orden_alfabetico = st.sidebar.checkbox("Ordenar alfabéticamente", value=True)

# --- PROCESAMIENTO ---
archivos_subidos = st.file_uploader("Sube aquí tus PDFs", type="pdf", accept_multiple_files=True)

if archivos_subidos:
    # Preparar índices y palabras clave
    idx_extra = [int(i.strip()) for i in indices_extra_str.split(",") if i.strip()]
    keywords = [p.strip().upper() for p in palabras_extra_str.split(",") if p.strip()]
    datos_brutos = []

    with st.spinner('Procesando...'):
        for archivo in archivos_subidos:
            with pdfplumber.open(archivo) as pdf:
                for pagina in pdf.pages:
                    tabla = pagina.extract_table()
                    if tabla:
                        for fila in tabla:
                            try:
                                # Unimos TODA la fila en un texto para buscar al proveedor
                                fila_completa = " ".join([str(c) for c in fila if c]).upper()
                                # Quitamos símbolos raros para que no estorben en la búsqueda
                                fila_limpia = fila_completa.replace('\n', ' ').replace('=', ' ')
                                
                                nombre_prod = str(fila[col_nombre]).replace('\n', ' ').strip()
                                
                                # ¿Es del proveedor fijo?
                                es_honest = False
                                if proveedor_fijo.upper() in fila_limpia:
                                    es_honest = True
                                
                                # ¿Tiene las keywords?
                                tiene_keys = False
                                if keywords:
                                    tiene_keys = all(k in nombre_prod.upper() for k in keywords)

                                if es_honest or tiene_keys:
                                    qty_raw = str(fila[col_cantidad])
                                    qty = int(''.join(filter(str.isdigit, qty_raw))) if any(c.isdigit() for c in qty_raw) else 0
                                    
                                    if qty > 0:
                                        extras = [str(fila[i]).replace('\n', ' ').strip() if fila[i] else "" for i in idx_extra]
                                        datos_brutos.append([nombre_prod] + extras + [qty])
                            except:
                                continue

    if datos_brutos:
        columnas = ["Producto"] + [f"Info_{i}" for i in idx_extra] + ["Cantidad"]
        df = pd.DataFrame(datos_brutos, columns=columnas)

        if agrupar:
            if limpiar_num:
                df['Producto'] = df['Producto'].apply(lambda x: re.sub(r'\s*\d+\s*$', '', x))
            dict_agrup = {c: 'first' for c in df.columns if c != 'Producto'}
            dict_agrup['Cantidad'] = 'sum'
            df = df.groupby('Producto').agg(dict_agrup).reset_index()

        if orden_alfabetico:
            df = df.sort_values(by='Producto', ascending=True)
        else:
            df = df.sort_values(by='Cantidad', ascending=False)

        # Cantidad al final
        cols_final = [c for c in df.columns if c != 'Cantidad'] + ['Cantidad']
        df = df[cols_final]

        st.success(f"¡Análisis completado!")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar CSV", csv, "inventario.csv", "text/csv")
