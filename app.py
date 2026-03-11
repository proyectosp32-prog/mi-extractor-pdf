import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configuración visual de la web
st.set_page_config(page_title="Extractor Inteligente Honest", layout="wide")
st.title("📦 Extractor de Inventario Final")
st.markdown("Filtros avanzados: Búsqueda flexible (detecta palabras pegadas o escondidas).")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración de Filtros")
proveedor_fijo = st.sidebar.text_input("Proveedor a incluir siempre", "HONEST LAB")
palabras_extra_str = st.sidebar.text_input("Keywords obligatorias para otros proveedores", "STONE, TABLE")

st.sidebar.markdown("---")
st.sidebar.subheader("Ajustes de Columnas")
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
    indices_extra = [int(i.strip()) for i in indices_extra_str.split(",") if i.strip()]
    palabras_clave = [p.strip().upper() for p in palabras_extra_str.split(",") if p.strip()]
    datos_brutos = []

    with st.spinner('Procesando datos con búsqueda profunda...'):
        for archivo in archivos_subidos:
            with pdfplumber.open(archivo) as pdf:
                for pagina in pdf.pages:
                    tabla = pagina.extract_table()
                    if tabla:
                        for fila in tabla:
                            try:
                                # 1. Limpiamos y unimos toda la fila en un solo texto para buscar
                                # Esto soluciona lo de "WOOD= HONEST LAB" o palabras pegadas
                                texto_fila_completo = " ".join([str(c) for c in fila if c]).upper()
                                texto_fila_completo = texto_fila_completo.replace('\n', ' ')
                                
                                nombre_producto = str(fila[col_nombre]).replace('\n', ' ').strip()
                                
                                # 2. Lógica de búsqueda del Proveedor (Flexible)
                                # Buscamos si el nombre del proveedor está en cualquier parte de la fila
                                es_proveedor_fijo = False
                                if proveedor_fijo:
                                    # Buscamos la frase entera (ej: "HONEST LAB")
                                    if proveedor_fijo.upper() in texto_fila_completo:
                                        es_proveedor_fijo = True
                                
                                # 3. Lógica de Keywords para otros proveedores (Deben estar TODAS)
                                tiene_todas_keywords = False
                                if palabras_clave:
                                    # Buscamos cada palabra clave en la descripción del producto
                                    tiene_todas_keywords = all(k in nombre_producto.upper() for k in palabras_clave)

                                # --- FILTRO FINAL ---
                                if es_proveedor_fijo or tiene_todas_keywords:
                                    qty_raw = str(fila[col_cantidad])
                                    qty = int(''.join(filter(str.isdigit, qty_raw))) if any(c.isdigit() for c in qty_raw) else 0
                                    
                                    if qty > 0:
                                        extras = [str(fila[i]).replace('\n', ' ').strip() if fila[i] else "" for i in indices_extra]
                                        datos_brutos.append([nombre_producto] + extras + [qty])
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

        if orden_alfabetico:
            df = df.sort_values(by='Producto', ascending=True)
        else:
            df = df.sort_values(by='Cantidad', ascending=False)

        cols = [c for c in df.columns if c != 'Cantidad'] + ['Cantidad']
        df = df[cols]

        st.success(f"¡Hecho! Se han analizado todos los archivos.")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8-sig') # Usamos utf-8-sig para que Excel lo abra bien
        st.download_button(
            label="📥 Descargar Inventario Final (CSV)",
            data=csv,
            file_name=f"inventario_completo.csv",
            mime='text/csv',
        )
    else:
        st.warning("No se encontraron elementos. Prueba a revisar el nombre del proveedor o las columnas.")
