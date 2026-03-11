import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configuración visual
st.set_page_config(page_title="Extractor Honest Pro", layout="wide")
st.title("📦 Extractor de Inventario Pro")
st.markdown("Filtros: **HONEST** (Todo) | Otros: **Combinaciones** de palabras.")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración de Filtros")
proveedor_fijo = st.sidebar.text_input("Proveedor a incluir siempre", "HONEST")

st.sidebar.markdown("---")
st.sidebar.subheader("Palabras clave (Otros proveedores)")
palabras_extra_str = st.sidebar.text_area(
    "Grupos de palabras", 
    "STONE, TABLE ; STONE, MESA",
    help="Usa ',' para unir palabras y ';' para añadir grupos nuevos."
)

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
    try:
        idx_extra = [int(i.strip()) for i in indices_extra_str.split(",") if i.strip()]
    except:
        idx_extra = []
    
    grupos_keywords = []
    for grupo in palabras_extra_str.split(";"):
        palabras = [p.strip().upper() for p in grupo.split(",") if p.strip()]
        if palabras:
            grupos_keywords.append(palabras)

    datos_brutos = []

    with st.spinner('Analizando PDFs...'):
        for archivo in archivos_subidos:
            with pdfplumber.open(archivo) as pdf:
                for pagina in pdf.pages:
                    tabla = pagina.extract_table()
                    if tabla:
                        for fila in tabla:
                            try:
                                texto_fila = " ".join([str(c) for c in fila if c]).upper()
                                nombre_prod = str(fila[col_nombre]).replace('\n', ' ').strip()
                                
                                es_honest = False
                                if proveedor_fijo and proveedor_fijo.upper() in texto_fila:
                                    es_honest = True
                                
                                coincide_keyword = False
                                for grupo in grupos_keywords:
                                    if all(p in nombre_prod.upper() for p in grupo):
                                        coincide_keyword = True
                                        break
                                
                                if es_honest or coincide_keyword:
                                    qty_raw = str(fila[col_cantidad])
                                    qty = int(''.join(filter(str.isdigit, qty_raw))) if any(c.isdigit() for c in qty_raw) else 0
                                    
                                    if qty > 0:
                                        # Extraemos la info extra (dimensiones, color...)
                                        extras = [str(fila[i]).replace('\n', ' ').strip() if fila[i] else "" for i in idx_extra]
                                        datos_brutos.append([nombre_prod] + extras + [qty])
                            except:
                                continue

    if datos_brutos:
        columnas_nombres = ["Producto"] + [f"Info_{i}" for i in idx_extra] + ["Cantidad"]
        df = pd.DataFrame(datos_brutos, columns=columnas_nombres)

        if agrupar:
            if limpiar_num:
                df['Producto'] = df['Producto'].apply(lambda x: re.sub(r'\s*\d+\s*$', '', x))
            
            # --- CAMBIO CLAVE AQUÍ ---
            # Agrupamos por TODAS las columnas excepto 'Cantidad'
            # Esto significa que si el nombre es igual pero la Info_7 (Medida) es distinta, NO se juntan.
            columnas_para_agrupar = [c for c in df.columns if c != 'Cantidad']
            df = df.groupby(columnas_para_agrupar).agg({'Cantidad': 'sum'}).reset_index()

        if orden_alfabetico:
            df = df.sort_values(by='Producto', ascending=True)
        else:
            df = df.sort_values(by='Cantidad', ascending=False)

        cols_ordenadas = [c for c in df.columns if c != 'Cantidad'] + ['Cantidad']
        df = df[cols_ordenadas]

        st.success(f"¡Análisis completado! Se han encontrado {len(df)} variantes de productos.")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar Inventario (CSV)", csv, "inventario.csv", "text/csv")
    else:
        st.warning("No se ha encontrado ningún artículo que cumpla las condiciones.")
