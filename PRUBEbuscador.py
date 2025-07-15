import streamlit as st
import pandas as pd
import re
from datetime import date

EXCEL_PATH = "Proveedores.xlsx"

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

# ============================
#         NUEVO PEDIDO
# ============================
def pedido_online():
    st.subheader("Pedido (solo online, sin Excel)")

    if "pedido_items_online" not in st.session_state:
        st.session_state["pedido_items_online"] = []

    st.markdown("#### Agregar ítem al pedido")
    c1, c2, c3 = st.columns([2, 2, 1])
    marca    = c1.text_input("Marca", key="item_marca_online")
    modelo   = c2.text_input("Modelo", key="item_modelo_online")
    cantidad = c3.number_input("Cantidad", min_value=1, value=1, key="item_cantidad_online")

    if st.button("➕ Agregar ítem", key="add_item_btn_online"):
        st.session_state["pedido_items_online"].append({
            "marca": marca,
            "modelo": modelo,
            "cantidad": cantidad
        })
        st.success(f"{cantidad}× {marca} {modelo} agregado.")

    if st.session_state["pedido_items_online"]:
        st.markdown("**Ítems en este pedido:**")
        for i, itm in enumerate(st.session_state["pedido_items_online"], 1):
            st.write(f"{i}. {itm['cantidad']}× {itm['marca']} {itm['modelo']}")

    # Datos del pedido
    d1, d2 = st.columns(2)
    nombre  = d1.text_input("Nombre del cliente", key="np_nombre_online")
    celular = d2.text_input("Celular", key="np_celular_online")
    tipo_entrega = st.radio("Tipo de entrega", ["Envío", "Retiro"], horizontal=True, key="np_tipo_entrega_online")
    direccion = st.text_input("Dirección (si aplica)", key="np_direccion_online")
    aclaracion = st.text_area("Aclaraciones (opcional)", key="np_aclaracion_online")

    if st.button("💾 Descargar Pedido (TXT)", key="save_pedido_btn_online"):
        today_str = date.today().strftime("%d-%m-%Y")
        tipo_txt = "Envio" if tipo_entrega == "Envío" else "Retiro"
        contenido = f"{tipo_txt}:\n\n"
        for itm in st.session_state["pedido_items_online"]:
            contenido += f"{itm['cantidad']}× {itm['marca'].upper()} {itm['modelo'].upper()}\n"
        if tipo_entrega == "Envío":
            contenido += f"\nDirección: {direccion}\n"
        if aclaracion:
            contenido += f"\n{aclaracion}\n"
        contenido += f"\nCliente: {nombre} – {celular}\n"
        txt_name = f"Pedido {today_str}.txt"

        st.download_button("📄 Descargar TXT del Pedido", data=contenido, file_name=txt_name)

    if st.button("🧹 Limpiar pedido", key="clear_pedido_online"):
        st.session_state["pedido_items_online"] = []
        st.session_state["item_marca_online"] = ""
        st.session_state["item_modelo_online"] = ""
        st.session_state["item_cantidad_online"] = 1
        st.session_state["np_nombre_online"] = ""
        st.session_state["np_celular_online"] = ""
        st.session_state["np_direccion_online"] = ""
        st.session_state["np_aclaracion_online"] = ""
        st.success("Pedido limpio.")

# ================
#   MAIN TABS
# ================
try:
    costos_df = pd.read_excel(EXCEL_PATH)
    precios10_df = pd.read_excel(EXCEL_PATH, sheet_name="10%")
    precios5_df = pd.read_excel(EXCEL_PATH, sheet_name="5%")
except Exception as e:
    st.error(f"No se pudo leer el archivo: {e}")
    st.stop()

st.title("🔎 Presupuestos y Pedidos")

tab1, tab2, tab3 = st.tabs([
    "Presupuesto",
    "Presupuesto Revendedores",
    "Pedido (solo online)"
])

with tab1:
    solapa_presupuesto(precios10_df, costos_df, clave_estado="presupuesto_items", titulo="Presupuesto")

with tab2:
    solapa_presupuesto(precios5_df, costos_df, clave_estado="presupuesto_revend", titulo="Presupuesto Revendedores")

with tab3:
    pedido_online()
