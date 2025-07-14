import streamlit as st
import pandas as pd
import re

EXCEL_PATH = 'Proveedores.xlsx'

def solapa_presupuesto(precios_df, costos_df, clave_estado="presupuesto_items", titulo="Presupuesto"):
    st.subheader(titulo)
    precios_df.columns = precios_df.columns.str.strip()
    costos_df.columns = costos_df.columns.str.strip()

    if clave_estado not in st.session_state:
        st.session_state[clave_estado] = []

    # Buscador general (marca/modelo)
    busqueda = st.text_input("Buscar modelo, parte del modelo o marca", key=titulo+"buscador").strip().upper()
    precios_filtrados = precios_df.copy()
    if busqueda:
        precios_filtrados = precios_filtrados[
            precios_filtrados['Marca'].str.upper().str.contains(busqueda) |
            precios_filtrados['Modelo'].str.upper().str.contains(busqueda)
        ]

    marcas_disp = sorted(precios_filtrados['Marca'].dropna().unique())
    col1, col2 = st.columns(2)
    with col1:
        marca_sel = st.selectbox("Marca", marcas_disp, key=titulo+"marca")
    modelos_disp = sorted(precios_filtrados[precios_filtrados['Marca'] == marca_sel]['Modelo'].dropna().unique())
    with col2:
        modelo_sel = st.selectbox("Modelo", modelos_disp, key=titulo+"modelo")

    columnas_precios = list(precios_df.columns)
    posibles_col_precios = {
        "Proveedor": [c for c in columnas_precios if "proveedor" in c.lower()][0],
        "Precio": [c for c in columnas_precios if "precio" in c.lower()][0],
        "Colores": [c for c in columnas_precios if "color" in c.lower()][0],
        "Ganancia": [c for c in columnas_precios if "ganancia" in c.lower()][0]
    }
    resultado_precio = precios_df[(precios_df['Marca'] == marca_sel) & (precios_df['Modelo'] == modelo_sel)]

    if resultado_precio.empty:
        st.warning("No se encontró información para ese modelo.")
        return

    mostrar_precio = resultado_precio[[posibles_col_precios["Proveedor"], posibles_col_precios["Precio"], posibles_col_precios["Colores"], posibles_col_precios["Ganancia"]]]
    st.write("Precios:")
    st.dataframe(mostrar_precio, use_container_width=True, hide_index=True)

    st.write("Costos:")
    res_costos = costos_df[(costos_df['Marca'] == marca_sel) & (costos_df['Modelo'] == modelo_sel)]
    proveedores = [col for col in costos_df.columns if col not in ['Marca', 'Modelo']]
    if not res_costos.empty:
        fila_costos = res_costos.iloc[0]
        data_costos = []
        for prov in proveedores:
            costo = fila_costos[prov]
            if pd.notna(costo):
                data_costos.append({"Proveedor": prov, "Costo": f"USD {int(costo)}"})
        if data_costos:
            tabla_costos = pd.DataFrame(data_costos)
            st.dataframe(tabla_costos, use_container_width=True, hide_index=True)
        else:
            st.info("No hay costos disponibles para ese modelo.")
    else:
        st.info("No hay costos disponibles para ese modelo.")

    # Botón para agregar al presupuesto (toma el primer precio encontrado)
    fila = resultado_precio.iloc[0]
    precio = str(fila[posibles_col_precios["Precio"]]).strip()
    colores = str(fila[posibles_col_precios["Colores"]]).strip()
    proveedor_venta = str(fila[posibles_col_precios["Proveedor"]]).strip()
    if precio.lower().startswith("usd"):
        precio_val = precio
    else:
        precio_val = f"USD {precio}"
    st.markdown(f"**{marca_sel} {modelo_sel} {precio_val} (Colores: {colores})**")
    if st.button(f"Agregar al {titulo}"):
        st.session_state[clave_estado].append({
            "Marca": marca_sel,
            "Modelo": modelo_sel,
            "Precio": precio_val,
            "Colores": colores,
            "Proveedor": proveedor_venta
        })

    # Mostrar detalle del presupuesto
    if st.session_state[clave_estado]:
        st.markdown("---")
        st.markdown(f"### Detalle del {titulo}")
        total = 0
        for item in st.session_state[clave_estado]:
            m = re.search(r"\d+", item["Precio"].replace(",", ""))
            valor = int(m.group()) if m else 0
            total += valor
            if item["Colores"]:
                st.markdown(f"{item['Marca']} {item['Modelo']} {item['Precio']} (Colores: {item['Colores']})")
            else:
                st.markdown(f"{item['Marca']} {item['Modelo']} {item['Precio']}")
        st.markdown(f"---\n### **TOTAL: USD {total}**")
        if st.button(f"Limpiar {titulo}"):
            st.session_state[clave_estado] = []

try:
    costos_df = pd.read_excel(EXCEL_PATH)
    precios10_df = pd.read_excel(EXCEL_PATH, sheet_name="10%")
    precios5_df = pd.read_excel(EXCEL_PATH, sheet_name="5%")
except Exception as e:
    st.error(f"No se pudo leer el archivo: {e}")
    st.stop()

st.title("🔎 Presupuestos")

tab1, tab2 = st.tabs([
    "Presupuesto",
    "Presupuesto Revendedores"
])

with tab1:
    solapa_presupuesto(precios10_df, costos_df, clave_estado="presupuesto_items", titulo="Presupuesto")

with tab2:
    solapa_presupuesto(precios5_df, costos_df, clave_estado="presupuesto_revend", titulo="Presupuesto Revendedores")
