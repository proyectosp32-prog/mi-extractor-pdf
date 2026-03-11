import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configuración visual
st.set_page_config(page_title="Extractor Honest Pro", layout="wide")
st.title("📦 Extractor de Inventario Personalizado")
st.markdown("Filtros: **HONEST** (Todo) | Otros: **Combinaciones** de palabras.")

# --- BARRA LATERAL ---
st.sidebar.header("1. Filtros de Búsqueda")
proveedor_fijo = st.sidebar.text_input("Proveedor a incluir siempre", "HONEST")
palabras_extra_str = st.sidebar.text_area(
    "Keywords (Otros proveedores)", 
    "STONE, TABLE ; STONE, MESA",
    help="Usa ',' para 'Y' y ';' para 'O'."
)

st.sidebar.markdown("---")
st.sidebar.header("2. Control de Agrupación")
agrupar = st.sidebar.checkbox("Activar agrupación inteligente", value=True)
limpiar_num = st.sidebar.checkbox("Quitar números finales (01, 02...)", value=True)

# NUEVA CASILLA DE EXCEPCIONES
productos_para_sumar_total = st.sidebar.text_area(
    "Productos a SUMAR TOTALMENTE (Ignorar medidas)", 
    "BANCO NAGA",
    help="Escribe el nombre de los productos que quieres ver en una sola fila con el total, sin importar que tengan medidas distintas."
)

st.sidebar.markdown("---")
st.sidebar.header("3. Ajustes de Columnas")
col_nombre = st.sidebar.number_input("Columna Nombre (Índice)", value=4)
col_cantidad = st.sidebar.number_input("Columna Cantidad (Índice)", value=10)
indices_extra_str = st.sidebar.text_input("Otras columnas (ej: 6, 7)", "6, 7")

st.sidebar.markdown("---")
orden_alfabetico = st.sidebar.checkbox("Ordenar alfabéticamente", value=True)

# --- PROCESAMIENTO ---
archivos_subidos = st.file_uploader("Sube aquí tus PDFs", type="pdf", accept_multiple_files=True)

if archivos_subidos:
    # Preparar parámetros
    idx_extra = [int(i.strip()) for i in indices_extra_str.split(",") if i.strip()]
    lista_sumar_total = [s.strip().upper() for s in productos_para_sumar_total.split(",") if s.strip()]
    
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
                                
                                es_honest = proveedor_fijo.upper() in texto_fila if proveedor_fijo else False
                                
                                coincide_keyword = False
                                for grupo in grupos_keywords:
                                    if all(p in nombre_prod.upper() for p in grupo):
                                        coincide_keyword = True
                                        break
                                
                                if es_honest or coincide_keyword:
                                    qty_raw = str(fila[col_cantidad])
                                    qty = int(''.join(filter(str.isdigit, qty_raw))) if any(c.isdigit() for c in qty_raw) else 0
                                    
                                    if qty > 0:
                                        extras = [str(fila[i]).replace('\n', ' ').strip() if fila[i] else "" for i in idx_extra]
                                        datos_brutos.append([nombre_prod] + extras + [qty])
                            except:
                                continue

    if datos_brutos:
        columnas_nombres = ["Producto"] + [f"Info_{i}" for i in idx_extra] + ["Cantidad"]
        df = pd.DataFrame(datos_brutos, columns=columnas_nombres)

        if agrupar:
            # 1. Limpieza inicial de nombres (quitar 01, 02...)
            if limpiar_num:
                df['Producto'] = df['Producto'].apply(lambda x: re.sub(r'\s*\d+\s*$', '', x))
            
            # 2. APLICAR EXCEPCIÓN DE SUMA TOTAL
            # Si el producto está en la lista del usuario, borramos su info extra temporalmente 
            # para que el 'groupby' lo vea como una sola cosa.
            def aplicar_excepcion(row):
                if row['Producto'].upper() in lista_sumar_total:
                    for c in df.columns:
                        if "Info_" in c:
                            row[c] = "(Suma de varias medidas)"
                return row

            df = df.apply(aplicar_excepcion, axis=1)
            
            # 3. Agrupamos por Producto y todas las Info_X
            columnas_agrupar = [c for c in df.columns if c != 'Cantidad']
            df = df.groupby(columnas_agrupar).agg({'Cantidad': 'sum'}).reset_index()

        # Ordenar y limpiar
        if orden_alfabetico:
            df = df.sort_values(by='Producto', ascending=True)
        else:
            df = df.sort_values(by='Cantidad', ascending=False)

        cols_final = [c for c in df.columns if c != 'Cantidad'] + ['Cantidad']
        df = df[cols_final]

        st.success(f"¡Hecho! Listado generado.")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar Inventario (CSV)", csv, "inventario.csv", "text/csv")
    else:
        st.warning("No se encontraron resultados.")
