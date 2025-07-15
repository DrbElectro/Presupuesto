import streamlit as st
import pandas as pd
import re
from datetime import date

EXCEL_PATH = "Proveedores.xlsx"

# ========== Presupuesto ==========
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

# ========== Carga catálogo solo una vez ==========
@st.cache_data
def load_catalogue():
    df = pd.read_excel(EXCEL_PATH)
    df.columns = df.columns.str.strip()
    return df

# ========== TABS ==========
st.title("Presupuestos y Pedidos")

tab1, tab2 = st.tabs([
    "Presupuesto",
    "Pedido"
])

with tab1:
    try:
        costos_df = pd.read_excel(EXCEL_PATH)
        precios10_df = pd.read_excel(EXCEL_PATH, sheet_name="10%")
        precios5_df = pd.read_excel(EXCEL_PATH, sheet_name="5%")
    except Exception as e:
        st.error(f"No se pudo leer el archivo: {e}")
        st.stop()
    solapa_presupuesto(precios10_df, costos_df, clave_estado="presupuesto_items", titulo="Presupuesto")
    solapa_presupuesto(precios5_df, costos_df, clave_estado="presupuesto_revend", titulo="Presupuesto Revendedores")

with tab2:
    df_cat = load_catalogue()
    if "pedido_items" not in st.session_state:
        st.session_state["pedido_items"] = []

    st.markdown("#### Agregar ítem al pedido")
    c1, c2, c3, c4, c5, c6 = st.columns([2,2,2,1,2,1])
    manual = st.checkbox("Manual P/M/M", key="np_manual")
    if manual or df_cat.empty:
        marca     = c1.text_input("Marca", key="item_marca_manual")
        modelo    = c2.text_input("Modelo", key="item_modelo_manual")
        proveedor = c3.text_input("Proveedor", key="item_proveedor_manual")
        color     = c5.text_input("Color", key="item_color_manual")
        costo_usd = c6.number_input("Costo USD", 0.0, format="%.2f", key="item_costo_usd_manual")
    else:
        marcas_disponibles = sorted(df_cat["Marca"].dropna().unique())
        if marcas_disponibles:
            marca = c1.selectbox("Marca", marcas_disponibles, key="item_marca")
            modelos_disponibles = sorted(df_cat[df_cat["Marca"]==marca]["Modelo"].dropna().unique())
            if modelos_disponibles:
                modelo = c2.selectbox("Modelo", modelos_disponibles, key="item_modelo")
                row = df_cat.query("Marca==@marca and Modelo==@modelo")
                if not row.empty:
                    row = row.iloc[0]
                    provs = [p for p in ("Ale","Eze","Di") if pd.notna(row.get(p))]
                    proveedor = c3.selectbox("Proveedor", provs, key="item_proveedor")
                    color = c5.text_input("Color", key="item_color")
                    costo_usd = c6.number_input("Costo USD", float(row[proveedor]), format="%.2f", key="item_costo_usd")
                else:
                    c3.write("No hay datos para ese modelo.")
                    proveedor = color = ""
                    costo_usd = 0.0
            else:
                c2.write("No hay modelos para esa marca.")
                modelo = proveedor = color = ""
                costo_usd = 0.0
        else:
            c1.write("No hay marcas disponibles.")
            marca = modelo = proveedor = color = ""
            costo_usd = 0.0

    cantidad = c4.number_input("Cantidad", min_value=1, value=1, key="item_cantidad")

    if st.button("➕ Agregar ítem", key="add_item_btn"):
        st.session_state["pedido_items"].append({
            "proveedor": proveedor, "marca": marca,
            "modelo": modelo, "costo_usd": costo_usd,
            "color": color, "cantidad": cantidad
        })
        st.success(f"{cantidad}× {marca} {modelo} agregado.")

    if st.session_state["pedido_items"]:
        st.markdown("**Ítems en este pedido:**")
        for i, itm in enumerate(st.session_state["pedido_items"], 1):
            st.write(f"{i}. {itm['cantidad']}× {itm['marca']} {itm['modelo']} — Color {itm['color']} — USD {itm['costo_usd']:.2f}")

    d1, d2, d3, d4 = st.columns(4)
    direccion   = d1.text_input("Dirección", key="np_direccion")
    localidad   = d2.text_input("Localidad", key="np_localidad")
    horario     = d3.text_input("Horario", key="np_horario")
    costo_envio = d4.number_input("Costo de envío", 0.0, format="%.2f", key="np_costo_envio")
    m1, m2 = st.columns([2,1])
    moneda  = m1.selectbox("Moneda", ["USD","ARS"], key="np_moneda")
    importe = m2.number_input("Importe", 0.0, format="%.2f", key="np_importe")
    aclarac = st.text_input("Aclaración", key="np_aclaracion")
    n1, n2   = st.columns(2)
    nombre  = n1.text_input("Cliente", key="np_nombre")
    celular = n2.text_input("Celular destinatario", key="np_celular")
    tipo_entrega = st.radio("Tipo de entrega", ["Envío", "Retiro"], horizontal=True, key="np_tipo_entrega_online")

    if st.button("💾 Descargar Pedido (TXT)", key="save_pedido_btn"):
        prefijo = date.today().strftime("%m%Y")
        numero = 1 + st.session_state.get("num_pedido_tmp", 0)
        pedido_id = f"{prefijo}-{numero:02d}"
        st.session_state["num_pedido_tmp"] = numero

        today_str = date.today().strftime("%d-%m-%Y")
        txt_name = f"Pedido {today_str}.txt"

        txt = ""
        if tipo_entrega == "Retiro":
            txt += f"Retiro: ({pedido_id})\n\n"
        else:
            txt += f"Envío: ({pedido_id})\n\n"

        for itm in st.session_state["pedido_items"]:
            txt += f"{itm['cantidad']}× {itm['marca'].upper()} {itm['modelo'].upper()} {itm['color']}\n"

        if tipo_entrega != "Retiro":
            txt += f"\nDirección: {direccion}\nLocalidad: {localidad}\n"
        txt += f"Horario: {horario}\n\n"

        pago_str = (f"$ {int(importe):,}".replace(",", ".") if moneda == "ARS" else f"USD {int(importe)}")
        if costo_envio > 0:
            pago_str += (f" + Envío $ {int(costo_envio):,}".replace(",", ".") if moneda == "ARS"
                         else f" + Envío $ {int(costo_envio)}")
        txt += f"PAGA: {pago_str}\n\n"
        if aclarac:
            txt += aclarac + "\n"
        txt += f"Recibe: {nombre} – {celular}\n"

        st.download_button("📄 Descargar TXT del Pedido", data=txt, file_name=txt_name)
        st.success(f"Pedido {pedido_id} generado (solo en TXT, no se guarda en Excel).")
        st.session_state["pedido_items"] = []

    if st.button("🧹 Limpiar Pedido", key="clear_pedido_btn"):
        st.session_state["pedido_items"] = []
        st.success("Pedido limpiado.")
