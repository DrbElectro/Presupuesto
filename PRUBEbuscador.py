import re
from datetime import date

import pandas as pd
import streamlit as st

# ===================== AUTENTICACIÓN HARDCODEADA =====================
PASSWORD = "1224"   # ← Tu clave está aquí

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    pwd = st.text_input("🔒 Contraseña", type="password")
    if not pwd:
        st.stop()
    if pwd != PASSWORD:
        st.error("⛔️ Contraseña incorrecta")
        st.stop()
    st.session_state["authenticated"] = True
    # Rerun para ocultar el input de contraseña
    st.experimental_rerun()

# ===================== CONFIG =====================
EXCEL_PATH = "Proveedores.xlsx"

# ===================== FUNCIONES =====================
def solapa_presupuesto(precios_df, costos_df, clave_estado="presupuesto_items", titulo="Presupuesto"):
    st.subheader(titulo)
    precios_df.columns = precios_df.columns.str.strip()
    costos_df.columns  = costos_df.columns.str.strip()

    if clave_estado not in st.session_state:
        st.session_state[clave_estado] = []

    busqueda = st.text_input("Buscar modelo, marca o parte del modelo", key=titulo+"buscador").strip().upper()
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
    modelos_disp = sorted(precios_filtrados[precios_filtrados['Marca']==marca_sel]['Modelo'].dropna().unique())
    with col2:
        modelo_sel = st.selectbox("Modelo", modelos_disp, key=titulo+"modelo")

    cols = precios_df.columns.str.lower()
    prov_col    = precios_df.columns[cols.str.contains("proveedor")][0]
    precio_col  = precios_df.columns[cols.str.contains("precio")][0]
    color_col   = precios_df.columns[cols.str.contains("color")][0]
    gan_col     = precios_df.columns[cols.str.contains("ganancia")][0]

    resultado = precios_df[(precios_df['Marca']==marca_sel)&(precios_df['Modelo']==modelo_sel)]
    if resultado.empty:
        st.warning("No se encontró info para ese modelo.")
        return

    st.dataframe(resultado[[prov_col, precio_col, color_col, gan_col]],
                 hide_index=True, use_container_width=True)

    st.write("Costos:")
    costos = costos_df[(costos_df['Marca']==marca_sel)&(costos_df['Modelo']==modelo_sel)]
    provs = [c for c in costos_df.columns if c not in ["Marca","Modelo"]]
    data = []
    for p in provs:
        v = costos.get(p)
        if v is not None and pd.notna(v.iloc[0]):
            data.append({"Proveedor":p, "Costo":f"USD {int(v.iloc[0])}"})
    if data:
        st.dataframe(pd.DataFrame(data), hide_index=True, use_container_width=True)
    else:
        st.info("No hay costos para ese modelo.")

    fila = resultado.iloc[0]
    precio = str(fila[precio_col]).strip()
    colores= str(fila[color_col]).strip()
    pv     = str(fila[prov_col]).strip()
    precio = precio if precio.lower().startswith("usd") else f"USD {precio}"
    st.markdown(f"**{marca_sel} {modelo_sel} {precio} (Colores: {colores})**")

    if st.button(f"Agregar al {titulo}"):
        st.session_state[clave_estado].append({
            "Marca":marca_sel, "Modelo":modelo_sel,
            "Precio":precio,   "Colores":colores,
            "Proveedor":pv
        })

    if st.session_state[clave_estado]:
        st.markdown("---")
        total = 0
        for itm in st.session_state[clave_estado]:
            num = re.search(r"\d+", itm["Precio"].replace(",",""))
            val = int(num.group()) if num else 0
            total += val
            txt = f"{itm['Marca']} {itm['Modelo']} {itm['Precio']}"
            if itm["Colores"]:
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
tab1, tab2, tab3 = st.tabs(["Presupuesto","Revendedores","Pedido"])

with tab1:
    try:
        costos = pd.read_excel(EXCEL_PATH)
        pre10   = pd.read_excel(EXCEL_PATH, sheet_name="10%")
    except Exception as e:
        st.error(f"No se pudo leer el Excel: {e}")
        st.stop()
    solapa_presupuesto(pre10, costos, clave_estado="presupuesto_items", titulo="Presupuesto")

with tab2:
    try:
        costos = pd.read_excel(EXCEL_PATH)
        pre5    = pd.read_excel(EXCEL_PATH, sheet_name="5%")
    except Exception as e:
        st.error(f"No se pudo leer el Excel: {e}")
        st.stop()
    solapa_presupuesto(pre5, costos, clave_estado="presupuesto_revend", titulo="Presupuesto Revendedores")

with tab3:
    df_cat = load_catalogue()
    if "pedido_items" not in st.session_state:
        st.session_state["pedido_items"] = []

    st.markdown("### Agregar ítem al pedido")
    c1,c2,c3,c4,c5,c6 = st.columns([2,2,2,1,2,1])
    manual = st.checkbox("Manual", key="np_manual")

    if manual or df_cat.empty:
        marca   = c1.text_input("Marca", key="item_marca_manual")
        modelo  = c2.text_input("Modelo", key="item_modelo_manual")
        prov    = c3.text_input("Proveedor", key="item_proveedor_manual")
        cantidad= c4.number_input("Cantidad", 1, 1, key="item_cantidad")
        color   = c5.text_input("Color", key="item_color_manual")
        costo   = c6.number_input("Costo USD", 0.0, format="%.2f", key="item_costo_usd_manual")
    else:
        marcas = sorted(df_cat["Marca"].dropna().unique())
        if marcas:
            marca  = c1.selectbox("Marca", marcas, key="item_marca")
            mods   = sorted(df_cat[df_cat["Marca"]==marca]["Modelo"].dropna().unique())
            if mods:
                modelo = c2.selectbox("Modelo", mods, key="item_modelo")
                row    = df_cat.query("Marca==@marca and Modelo==@modelo").iloc[0]
                provs  = [p for p in ("Ale","Eze","Di") if pd.notna(row.get(p))]
                prov   = c3.selectbox("Proveedor", provs, key="item_proveedor")
                cantidad= c4.number_input("Cantidad", 1, 1, key="item_cantidad")
                color   = c5.text_input("Color", key="item_color")
                costo   = c6.number_input("Costo USD", float(row[prov]), format="%.2f", key="item_costo_usd")
            else:
                c2.write("No hay modelos.")
                modelo = prov = color = ""
                cantidad = 1
                costo = 0.0
        else:
            c1.write("No hay marcas.")
            marca = modelo = prov = color = ""
            cantidad = 1
            costo = 0.0

    if st.button("➕ Agregar ítem", key="add_item_btn"):
        st.session_state["pedido_items"].append({
            "proveedor":prov, "marca":marca, "modelo":modelo,
            "costo_usd":costo, "color":color, "cantidad":cantidad
        })
        st.success(f"{cantidad}× {marca} {modelo} agregado.")

    if st.session_state["pedido_items"]:
        st.markdown("**Ítems en este pedido:**")
        for i,itm in enumerate(st.session_state["pedido_items"],1):
            st.write(f"{i}. {itm['cantidad']}× {itm['marca']} {itm['modelo']} — {itm['color']} — USD {itm['costo_usd']:.2f}")

    d1,d2,d3,d4 = st.columns(4)
    direccion= d1.text_input("Dirección", key="np_direccion")
    localidad= d2.text_input("Localidad", key="np_localidad")
    horario  = d3.text_input("Horario", key="np_horario")
    envio    = d4.number_input("Costo envío",0.0,format="%.2f",key="np_costo_envio")

    m1,m2 = st.columns([2,1])
    moneda = m1.selectbox("Moneda",["USD","ARS"],key="np_moneda")
    importe= m2.number_input("Importe",0.0,format="%.2f",key="np_importe")

    aclarac= st.text_input("Aclaración",key="np_aclaracion")
    n1,n2  = st.columns(2)
    nombre = n1.text_input("Cliente",key="np_nombre")
    celular= n2.text_input("Celular",key="np_celular")

    tipo = st.radio("Tipo de entrega",["Envío","Retiro"],horizontal=True,key="np_tipo_entrega_online")

    if st.button("📋 Generar texto para copiar",key="show_pedido_btn"):
        txt = ("Retiro:\n\n" if tipo=="Retiro" else "Envío:\n\n")
        for itm in st.session_state["pedido_items"]:
            txt += f"{itm['cantidad']}× {itm['marca'].upper()} {itm['modelo'].upper()} {itm['color']}\n"
        if tipo!="Retiro":
            txt += f"\nDirección: {direccion}\nLocalidad: {localidad}\n"
        txt += f"Horario: {horario}\n\n"
        pago_str = (f"$ {int(importe):,}".replace(",",".") if moneda=="ARS" else f"USD {int(importe)}")
        if envio>0:
            pago_str += (f" + Envío $ {int(envio):,}".replace(",",".") if moneda=="ARS" else f" + Envío $ {int(envio)}")
        txt += f"PAGA: {pago_str}\n\n" + (aclarac+"\n" if aclarac else "") + f"Recibe: {nombre} – {celular}\n"
        st.text_area("Copiar el texto generado:",value=txt,height=250)
        st.success("Texto listo para copiar.")

    if st.button("🧹 Limpiar Pedido",key="clear_pedido_btn"):
        st.session_state["pedido_items"]=[]
        st.success("Pedido limpiado.")
