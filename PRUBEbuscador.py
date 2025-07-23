import os
import re
from datetime import date

import pandas as pd
import streamlit as st
from streamlit.runtime.scriptrunner import RerunException, RerunData

# ===================== AUTENTICACIÓN =====================
def get_password():
    # 1) Secrets.toml
    try:
        return st.secrets["credentials"]["password"]
    except Exception:
        pass
    # 2) Var de entorno opcional
    if os.getenv("APP_PASSWORD"):
        return os.getenv("APP_PASSWORD")
    # 3) Fallback (evítalo en producción)
    return None

# Estado
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

REAL_PASSWORD = get_password()   # <<< ESTA LÍNEA FALTABA

if not REAL_PASSWORD:
    st.error(
        "🔑 Error: No se encontró la contraseña.\n\n"
        "Crea `.streamlit/secrets.toml` con:\n"
        "[credentials]\npassword = \"Academia22\""
    )
    st.stop()

if not st.session_state["authenticated"]:
    pwd = st.text_input("🔒 Contraseña", type="password")
    if not pwd:
        st.stop()
    if pwd != REAL_PASSWORD:
        st.error("⛔️ Contraseña incorrecta")
        st.stop()
    st.session_state["authenticated"] = True
    # rerun para esconder el input
    raise RerunException(RerunData())

# ===================== CONFIG =====================
EXCEL_PATH = "Proveedores.xlsx"

# ===================== FUNCIONES =====================
def solapa_presupuesto(precios_df, costos_df, clave_estado="presupuesto_items", titulo="Presupuesto"):
    st.subheader(titulo)
    precios_df.columns = precios_df.columns.str.strip()
    costos_df.columns = costos_df.columns.str.strip()

    if clave_estado not in st.session_state:
        st.session_state[clave_estado] = []

    # Buscador
    busqueda = st.text_input("Buscar modelo, parte del modelo o marca", key=titulo + "buscador").strip().upper()
    precios_filtrados = precios_df.copy()
    if busqueda:
        precios_filtrados = precios_filtrados[
            precios_filtrados['Marca'].str.upper().str.contains(busqueda) |
            precios_filtrados['Modelo'].str.upper().str.contains(busqueda)
        ]

    marcas_disp = sorted(precios_filtrados['Marca'].dropna().unique())
    col1, col2 = st.columns(2)
    with col1:
        marca_sel = st.selectbox("Marca", marcas_disp, key=titulo + "marca")
    modelos_disp = sorted(precios_filtrados[precios_filtrados['Marca'] == marca_sel]['Modelo'].dropna().unique())
    with col2:
        modelo_sel = st.selectbox("Modelo", modelos_disp, key=titulo + "modelo")

    columnas_precios = list(precios_df.columns)
    posibles_col_precios = {
        "Proveedor": [c for c in columnas_precios if "proveedor" in c.lower()][0],
        "Precio":    [c for c in columnas_precios if "precio"    in c.lower()][0],
        "Colores":   [c for c in columnas_precios if "color"     in c.lower()][0],
        "Ganancia":  [c for c in columnas_precios if "ganancia"  in c.lower()][0]
    }

    resultado_precio = precios_df[
        (precios_df['Marca'] == marca_sel) &
        (precios_df['Modelo'] == modelo_sel)
    ]

    if resultado_precio.empty:
        st.warning("No se encontró información para ese modelo.")
        return

    mostrar = resultado_precio[[
        posibles_col_precios["Proveedor"],
        posibles_col_precios["Precio"],
        posibles_col_precios["Colores"],
        posibles_col_precios["Ganancia"]
    ]]
    st.dataframe(mostrar, use_container_width=True, hide_index=True)

    st.write("Costos:")
    res_costos = costos_df[(costos_df['Marca'] == marca_sel) & (costos_df['Modelo'] == modelo_sel)]
    proveedores = [c for c in costos_df.columns if c not in ['Marca', 'Modelo']]
    data_costos = []
    for prov in proveedores:
        c = res_costos.get(prov)
        if c is not None and pd.notna(c.iloc[0]):
            data_costos.append({"Proveedor": prov, "Costo": f"USD {int(c.iloc[0])}"})
    if data_costos:
        st.dataframe(pd.DataFrame(data_costos), use_container_width=True, hide_index=True)
    else:
        st.info("No hay costos disponibles para ese modelo.")

    fila = resultado_precio.iloc[0]
    precio = str(fila[posibles_col_precios["Precio"]]).strip()
    colores = str(fila[posibles_col_precios["Colores"]]).strip()
    pv = str(fila[posibles_col_precios["Proveedor"]]).strip()
    precio_val = precio if precio.lower().startswith("usd") else f"USD {precio}"
    st.markdown(f"**{marca_sel} {modelo_sel} {precio_val} (Colores: {colores})**")
    if st.button(f"Agregar al {titulo}"):
        st.session_state[clave_estado].append({
            "Marca": marca_sel, "Modelo": modelo_sel,
            "Precio": precio_val, "Colores": colores,
            "Proveedor": pv
        })

    if st.session_state[clave_estado]:
        st.markdown("---")
        total = 0
        for itm in st.session_state[clave_estado]:
            m = re.search(r"\d+", itm["Precio"].replace(",", ""))
            val = int(m.group()) if m else 0
            total += val
            txt = f"{itm['Marca']} {itm['Modelo']} {itm['Precio']}"
            if itm['Colores']:
                txt += f" (Colores: {itm['Colores']})"
            st.markdown(txt)
        st.markdown(f"---\n### **TOTAL: USD {total}**")
        if st.button(f"Limpiar {titulo}"):
            st.session_state[clave_estado] = []

@st.cache_data
def load_catalogue():
    df = pd.read_excel(EXCEL_PATH)
    df.columns = df.columns.str.strip()
    return df

# ===================== UI =====================
st.title("DRB Electro")
tab1, tab2, tab3 = st.tabs(["Presupuesto", "Presupuesto Revendedores", "Pedido"])

with tab1:
    try:
        costos = pd.read_excel(EXCEL_PATH)
        pre10 = pd.read_excel(EXCEL_PATH, sheet_name="10%")
    except Exception as e:
        st.error(f"No se pudo leer el archivo: {e}")
        st.stop()
    solapa_presupuesto(pre10, costos, clave_estado="presupuesto_items", titulo="Presupuesto")

with tab2:
    try:
        costos = pd.read_excel(EXCEL_PATH)
        pre5 = pd.read_excel(EXCEL_PATH, sheet_name="5%")
    except Exception as e:
        st.error(f"No se pudo leer el archivo: {e}")
        st.stop()
    solapa_presupuesto(pre5, costos, clave_estado="presupuesto_revend", titulo="Presupuesto Revendedores")

with tab3:
    df_cat = load_catalogue()
    if "pedido_items" not in st.session_state:
        st.session_state["pedido_items"] = []

    st.markdown("#### Agregar ítem al pedido")
    c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 2, 1, 2, 1])
    manual = st.checkbox("Manual P/M/M", key="np_manual")

    if manual or df_cat.empty:
        marca = c1.text_input("Marca", key="item_marca_manual")
        modelo = c2.text_input("Modelo", key="item_modelo_manual")
        prov = c3.text_input("Proveedor", key="item_proveedor_manual")
        cantidad = c4.number_input("Cantidad", min_value=1, value=1, key="item_cantidad")
        color = c5.text_input("Color", key="item_color_manual")
        costo_usd = c6.number_input("Costo USD", 0.0, format="%.2f", key="item_costo_usd_manual")
    else:
        marcas = sorted(df_cat["Marca"].dropna().unique())
        if marcas:
            marca = c1.selectbox("Marca", marcas, key="item_marca")
            mods = sorted(df_cat[df_cat["Marca"] == marca]["Modelo"].dropna().unique())
            if mods:
                modelo = c2.selectbox("Modelo", mods, key="item_modelo")
                row = df_cat.query("Marca==@marca and Modelo==@modelo").iloc[0]
                provs = [p for p in ("Ale", "Eze", "Di") if pd.notna(row.get(p))]
                prov = c3.selectbox("Proveedor", provs, key="item_proveedor")
                cantidad = c4.number_input("Cantidad", min_value=1, value=1, key="item_cantidad")
                color = c5.text_input("Color", key="item_color")
                costo_usd = c6.number_input("Costo USD", float(row[prov]), format="%.2f", key="item_costo_usd")
            else:
                c2.write("No hay modelos para esa marca.")
                modelo = prov = color = ""
                cantidad = 1
                costo_usd = 0.0
        else:
            c1.write("No hay marcas disponibles.")
            marca = modelo = prov = color = ""
            cantidad = 1
            costo_usd = 0.0

    if st.button("➕ Agregar ítem", key="add_item_btn"):
        st.session_state["pedido_items"].append({
            "proveedor": prov, "marca": marca, "modelo": modelo,
            "costo_usd": costo_usd, "color": color, "cantidad": cantidad
        })
        st.success(f"{cantidad}× {marca} {modelo} agregado.")

    if st.session_state["pedido_items"]:
        st.markdown("**Ítems en este pedido:**")
        for i, itm in enumerate(st.session_state["pedido_items"], 1):
            st.write(f"{i}. {itm['cantidad']}× {itm['marca']} {itm['modelo']} — Color {itm['color']} — USD {itm['costo_usd']:.2f}")

    d1, d2, d3, d4 = st.columns(4)
    direccion = d1.text_input("Dirección", key="np_direccion")
    localidad = d2.text_input("Localidad", key="np_localidad")
    horario = d3.text_input("Horario", key="np_horario")
    c_envio = d4.number_input("Costo de envío", 0.0, format="%.2f", key="np_costo_envio")

    m1, m2 = st.columns([2, 1])
    moneda = m1.selectbox("Moneda", ["USD", "ARS"], key="np_moneda")
    importe = m2.number_input("Importe", 0.0, format="%.2f", key="np_importe")

    aclarac = st.text_input("Aclaración", key="np_aclaracion")
    n1, n2 = st.columns(2)
    nombre = n1.text_input("Cliente", key="np_nombre")
    celular = n2.text_input("Celular destinatario", key="np_celular")

    tipo_entrega = st.radio("Tipo de entrega", ["Envío", "Retiro"], horizontal=True, key="np_tipo_entrega_online")

    if st.button("📋 Generar texto para copiar", key="show_pedido_btn"):
        txt = ("Retiro:\n\n" if tipo_entrega == "Retiro" else "Envío:\n\n")
        for itm in st.session_state["pedido_items"]:
            txt += f"{itm['cantidad']}× {itm['marca'].upper()} {itm['modelo'].upper()} {itm['color']}\n"
        if tipo_entrega != "Retiro":
            txt += f"\nDirección: {direccion}\nLocalidad: {localidad}\n"
        txt += f"Horario: {horario}\n\n"
        pago_str = (f"$ {int(importe):,}".replace(",", ".") if moneda == "ARS" else f"USD {int(importe)}")
        if c_envio > 0:
            pago_str += (f" + Envío $ {int(c_envio):,}".replace(",", ".") if moneda == "ARS" else f" + Envío $ {int(c_envio)}")
        txt += f"PAGA: {pago_str}\n\n" + (aclarac + "\n" if aclarac else "") + f"Recibe: {nombre} – {celular}\n"
        st.text_area("Copiar el texto generado:", value=txt, height=250)
        st.success("Texto listo para copiar.")

    if st.button("🧹 Limpiar Pedido", key="clear_pedido_btn"):
        st.session_state["pedido_items"] = []
        st.success("Pedido limpiado.")
