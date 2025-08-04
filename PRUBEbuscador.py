#!/usr/bin/env python3
import os
import re
from datetime import date

import pandas as pd
import streamlit as st
from streamlit.runtime.scriptrunner import RerunException, RerunData

import config
import utils

# ===================== AUTENTICACIÓN HARDCODEADA =====================
PASSWORD = "1224"   # ← Tu clave aquí

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
    raise RerunException(RerunData())

# ===================== FUNCIÓN BUSCADOR =====================
def run_buscador():
    EXCEL_PATH = str(config.CATALOGO_PATH)

    # Leer hojas de costos de proveedores y concatenar
    proveedores = ["Eze", "Di", "Ale"]
    sheets = pd.read_excel(EXCEL_PATH, sheet_name=proveedores)
    costos_list = []
    for prov, dfp in sheets.items():
        price_col = next(c for c in dfp.columns if "precio" in c.lower())
        dfp = dfp.rename(columns={price_col: "Costo USD"})
        dfp["Costo USD"] = pd.to_numeric(dfp["Costo USD"], errors="coerce").fillna(0)
        dfp["Proveedor"] = prov
        costos_list.append(dfp[["Marca", "Modelo", "Proveedor", "Costo USD"]])
    costos_df = pd.concat(costos_list, ignore_index=True)

    # Leer hojas de precios
    precios10_df = pd.read_excel(EXCEL_PATH, sheet_name="10%")
    precios5_df  = pd.read_excel(EXCEL_PATH, sheet_name="5%")

    def solapa_presupuesto(precios_df, costos_df, clave_estado, titulo):
        st.subheader(titulo)
        precios_df.columns = precios_df.columns.str.strip()

        if clave_estado not in st.session_state:
            st.session_state[clave_estado] = []

        # Buscador de modelo/marca
        busq = st.text_input("Buscar modelo o marca", key=f"{clave_estado}_buscador").strip().upper()
        df_f = precios_df.copy()
        if busq:
            df_f = df_f[
                df_f["Marca"].str.upper().str.contains(busq) |
                df_f["Modelo"].str.upper().str.contains(busq)
            ]

        # Selección Marca / Modelo
        c1, c2 = st.columns(2)
        with c1:
            marca_sel = st.selectbox(
                "Marca",
                sorted(df_f["Marca"].dropna().unique()),
                key=f"{clave_estado}_marca"
            )
        with c2:
            modelo_sel = st.selectbox(
                "Modelo",
                sorted(df_f[df_f["Marca"] == marca_sel]["Modelo"].dropna().unique()),
                key=f"{clave_estado}_modelo"
            )

        # Columnas dinámicas
        cols     = precios_df.columns.tolist()
        prov_col = next(c for c in cols if "proveedor" in c.lower())
        prec_col = next(c for c in cols if "precio"    in c.lower())
        col_col  = next(c for c in cols if "color"     in c.lower())
        gan_col  = next(c for c in cols if "ganancia"  in c.lower())

        mask_p = (
            (precios_df["Marca"] == marca_sel) &
            (precios_df["Modelo"] == modelo_sel)
        )

        # Checkbox cálculo manual
        calcular_manual = st.checkbox("Calcular manualmente", key=f"{clave_estado}_calcular")
        if calcular_manual:
            # Inputs manuales
            m1, m2 = st.columns(2)
            marca_m  = m1.text_input("Marca", value=marca_sel, key=f"{clave_estado}_man_marca")
            modelo_m = m2.text_input("Modelo", value=modelo_sel, key=f"{clave_estado}_man_modelo")

            # Proveedor, Costo USD y Dólar Blue
            opts = sorted(
                costos_df[
                    (costos_df["Marca"]  == marca_m) &
                    (costos_df["Modelo"] == modelo_m)
                ]["Proveedor"].dropna().unique()
            )
            col_p, col_cost, col_blue = st.columns(3)
            if opts:
                prov_m = col_p.selectbox("Proveedor", opts, key=f"{clave_estado}_man_prov")
            else:
                prov_m = col_p.text_input("Proveedor", key=f"{clave_estado}_man_prov")

            mask_c  = (
                (costos_df["Marca"]     == marca_m) &
                (costos_df["Modelo"]    == modelo_m) &
                (costos_df["Proveedor"] == prov_m)
            )
            mask_cm = (
                (costos_df["Marca"]  == marca_m) &
                (costos_df["Modelo"] == modelo_m)
            )
            if mask_c.any():
                default_cost = float(costos_df.loc[mask_c, "Costo USD"].iat[0])
            elif mask_cm.any():
                default_cost = float(costos_df.loc[mask_cm, "Costo USD"].iat[0])
            else:
                default_cost = 0.0

            costo_m = col_cost.number_input(
                "Costo USD", min_value=0.0, format="%.2f",
                value=default_cost, key=f"{clave_estado}_man_costo"
            )
            blue_m  = col_blue.number_input(
                "Dólar Blue", min_value=0.0, format="%.2f",
                key=f"{clave_estado}_man_blue"
            )

            g1, g2, g3 = st.columns(3)
            pct_m    = g1.number_input("% Ganancia", min_value=0.0, format="%.2f",
                                       value=10.0, key=f"{clave_estado}_man_pct")
            desc_m   = g2.number_input("Descuento USD", min_value=0.0, format="%.2f",
                                       key=f"{clave_estado}_man_desc")
            moneda_m = g3.selectbox("Moneda", ["USD", "Pesos", "Ambos"],
                                    key=f"{clave_estado}_man_moneda")

            man_with_colors = st.checkbox("Con colores", value=False,
                                          key=f"{clave_estado}_man_with_colors")

            if st.button("Calcular y Agregar", key=f"{clave_estado}_man_calc"):
                gan       = max(costo_m * pct_m / 100, 30.0)
                bruto     = costo_m + gan
                final_usd = max(round(bruto / 5) * 5 - desc_m, 0)
                final_ars = final_usd * blue_m

                if moneda_m == "USD":
                    precio_str = f"USD {final_usd:.0f}"
                elif moneda_m == "Pesos":
                    precio_str = f"$ {final_ars:,.0f}"
                else:
                    precio_str = f"USD {final_usd:.0f} / $ {final_ars:,.0f}"

                st.session_state[clave_estado].append({
                    "Marca":   marca_m,
                    "Modelo":  modelo_m,
                    "Precio":  precio_str,
                    "Colores": "" if man_with_colors else "",
                    "Proveedor": prov_m,
                })
                st.success(f"{marca_m} {modelo_m} agregado: {precio_str}")

        else:
            # Flujo automático
            if mask_p.any():
                resultado = precios_df.loc[mask_p].iloc[[0]]
                st.write("Precios:")
                st.dataframe(resultado[[prov_col, prec_col, gan_col]],
                             use_container_width=True, hide_index=True)

                costos = costos_df[
                    (costos_df["Marca"]  == marca_sel) &
                    (costos_df["Modelo"] == modelo_sel)
                ]
                if not costos.empty:
                    data_c = [
                        {"Proveedor": r["Proveedor"],
                         "Costo":      f"USD {r['Costo USD']:.2f}"}
                        for _, r in costos.iterrows()
                    ]
                    st.write("Costos:")
                    st.dataframe(pd.DataFrame(data_c),
                                 use_container_width=True, hide_index=True)

                auto_with_colors = st.checkbox("Con colores", value=False,
                                               key=f"{clave_estado}_auto_with_colors")
                if st.button(f"Agregar al {titulo}", key=f"{clave_estado}_add"):
                    raw = str(resultado[prec_col].iat[0]).strip()
                    precio_val = raw if raw.lower().startswith("usd") else f"USD {raw}"
                    color_val  = resultado[col_col].iat[0] if auto_with_colors else ""
                    st.session_state[clave_estado].append({
                        "Marca":    marca_sel,
                        "Modelo":   modelo_sel,
                        "Precio":   precio_val,
                        "Colores":  color_val,
                        "Proveedor": str(resultado[prov_col].iat[0]).strip(),
                    })
                    st.success("Ítem agregado al presupuesto.")
            else:
                st.info("Modelo no encontrado. Marca 'Calcular manualmente' para agregarlo.")

        # Detalle y total
        if st.session_state[clave_estado]:
            st.markdown("---")
            st.subheader(f"Detalle del {titulo}")
            usd_total = pes_total = 0
            hoy       = date.today().strftime("%d/%m/%Y")
            msg       = f"*Presupuesto DRB ELECTRO*\n_{hoy}_\n\n"
            for it in st.session_state[clave_estado]:
                m_usd = re.search(r"USD\s*([\d,]+)", it["Precio"])
                if m_usd:
                    usd_total += int(m_usd.group(1).replace(",", ""))
                m_pes = re.search(r"\$\s*([\d,]+)", it["Precio"])
                if m_pes:
                    pes_total += int(m_pes.group(1).replace(",", ""))

                line = f"- {it['Marca']} {it['Modelo']} • {it['Precio']}"
                if it["Colores"]:
                    line += f" • {it['Colores']}"
                st.markdown(line)
                msg += line.replace("•", "") + "\n"

            msg += "---------------------------\n"
            if pes_total > 0 and usd_total == 0:
                total_str = f"$ {pes_total:,.0f}"
            elif usd_total > 0 and pes_total == 0:
                total_str = f"USD {usd_total}"
            else:
                total_str = f"USD {usd_total} / $ {pes_total:,.0f}"

            st.markdown(f"**TOTAL: {total_str}**")
            msg += f"*TOTAL: {total_str}*"
            st.text_area("Mensaje para copiar", value=msg, height=200,
                         key=f"{clave_estado}_msg")

            if st.button("Limpiar presupuesto", key=f"{clave_estado}_clear_all"):
                st.session_state[clave_estado] = []
                raise RerunException(RerunData())

    st.title("🔎 Buscador")
    tab1, tab2 = st.tabs(["Presupuesto", "Presupuesto Revendedores"])
    with tab1:
        solapa_presupuesto(precios10_df, costos_df, "presupuesto_items", "Presupuesto")
    with tab2:
        solapa_presupuesto(precios5_df,  costos_df, "presupuesto_revend", "Presupuesto Revendedores")


# ===================== FUNCIÓN PEDIDOS (solo mostrar y copiar) =====================
def run_pedidos():
    if "pedido_items" not in st.session_state:
        st.session_state["pedido_items"] = []
    if "pedido_confirmar" not in st.session_state:
        st.session_state["pedido_confirmar"] = False
    if "contenido_txt" not in st.session_state:
        st.session_state["contenido_txt"] = ""

    st.title("📋 Nuevo Pedido")

    c1, c2, c3 = st.columns(3)
    is_envio = c1.checkbox("Envío", True, key="np_envio")
    is_retiro = c2.checkbox("Retiro", False, key="np_retiro")
    manual = c3.checkbox("Carga Manual", key="np_manual")
    if is_envio and is_retiro:
        st.warning("Seleccione solo Envío o Retiro.")
        return

    df_cat = utils.load_catalogue()

    if not manual:
        st.subheader("Buscar producto")
        busq = st.text_input("Marca o modelo", key="item_busqueda").strip().upper()
        df_fil = df_cat.copy()
        if busq:
            df_fil = df_fil[
                df_fil["Marca"].str.upper().str.contains(busq) |
                df_fil["Modelo"].str.upper().str.contains(busq)
            ]
    else:
        df_fil = df_cat.copy()

    cols = st.columns([2,2,2,1,2,1])
    if manual:
        marca     = cols[0].text_input("Marca", key="item_marca_manual")
        modelo    = cols[1].text_input("Modelo", key="item_modelo_manual")
        proveedor = cols[2].text_input("Proveedor", key="item_proveedor_manual")
        cantidad  = cols[3].number_input("Cantidad", 1, 1, key="item_cantidad_manual")
        color     = cols[4].text_input("Color", key="item_color_manual")
        costo_usd = cols[5].number_input("Costo USD", 0.0, format="%.2f", key="item_costo_usd_manual")
    else:
        marcas    = sorted(df_fil["Marca"].dropna().unique())
        marca     = cols[0].selectbox("Marca", marcas, key="item_marca")
        modelos   = sorted(df_fil[df_fil["Marca"]==marca]["Modelo"].dropna().unique())
        modelo    = cols[1].selectbox("Modelo", modelos, key="item_modelo")
        row       = df_cat.query("Marca==@marca and Modelo==@modelo").iloc[0]
        provs     = [p for p in ("Ale","Eze","Di") if pd.notna(row.get(p))]
        proveedor = cols[2].selectbox("Proveedor", provs, key="item_proveedor")
        cantidad  = cols[3].number_input("Cantidad", 1, 1, key="item_cantidad")
        color     = cols[4].text_input("Color", key="item_color")
        costo_usd = cols[5].number_input("Costo USD", float(row[proveedor]), format="%.2f", key="item_costo_usd")

    if st.button("➕ Agregar ítem", key="add_item_btn"):
        st.session_state["pedido_items"].append({
            "Proveedor": proveedor,
            "Marca":      marca,
            "Modelo":     modelo,
            "Cantidad":   cantidad,
            "Color":      color,
            "Costo USD":  costo_usd
        })
        st.success(f"{cantidad}× {marca} {modelo} agregado.")

    if st.session_state["pedido_items"]:
        st.markdown("**Ítems en este pedido:**")
        for idx, itm in enumerate(st.session_state["pedido_items"]):
            cA, cB = st.columns([8,1])
            cA.write(f"{idx+1}. {itm['Cantidad']}× {itm['Marca']} {itm['Modelo']} — Color {itm['Color']} — USD {itm['Costo USD']:.2f}")
            if cB.button("❌", key=f"del_{idx}"):
                st.session_state["pedido_items"].pop(idx)
                st.experimental_rerun()

    st.subheader("Datos del pedido")
    d1, d2, d3, d4 = st.columns(4)
    direccion   = d1.text_input("Dirección", key="np_direccion")
    localidad   = d2.text_input("Localidad", key="np_localidad")
    horario     = d3.text_input("Horario", key="np_horario")
    costo_envio = d4.number_input("Costo envío", 0.0, format="%.2f", key="np_costo_envio")
    m1, m2, m3  = st.columns([1,2,3])
    moneda      = m1.selectbox("Moneda", ["USD","ARS"], key="np_moneda")
    importe     = m2.number_input("Importe", 0.0, format="%.2f", key="np_importe")
    aclarac     = m3.text_input("Aclaración", key="np_aclaracion")
    n1, n2      = st.columns(2)
    nombre      = n1.text_input("Cliente", key="np_nombre")
    celular     = n2.text_input("Celular", key="np_celular")

    if not st.session_state["pedido_confirmar"]:
        if st.button("📝 Mostrar Pedido para Copiar", key="btn_preview"):
            txt  = (f"Retiro:\n\n" if is_retiro else "Envío:\n\n")
            for itm in st.session_state["pedido_items"]:
                txt += f"{itm['Cantidad']}× {itm['Marca'].upper()} {itm['Modelo'].upper()} {itm['Color']}\n"
            if not is_retiro:
                txt += f"\nDirección: {direccion}\nLocalidad: {localidad}\n"
            txt += f"Horario: {horario}\n\n"
            pay  = (f"$ {int(importe):,}".replace(",",".") if moneda=="ARS" else f"USD {int(importe)}")
            if costo_envio>0:
                pay += (f" + Envío $ {int(costo_envio):,}".replace(",",".") if moneda=="ARS" else f" + Envío $ {int(costo_envio)}")
            txt += f"PAGA: {pay}\n\n"
            if aclarac:
                txt += aclarac + "\n"
            txt += f"Recibe: {nombre} – {celular}\n"

            st.session_state["contenido_txt"]    = txt
            st.session_state["pedido_confirmar"] = True
            st.experimental_rerun()

    if st.session_state["pedido_confirmar"]:
        st.markdown("### Pedido listo para copiar")
        st.text_area("", value=st.session_state["contenido_txt"], height=350, key="txt_final")
        if st.button("🔄 Volver", key="btn_back"):
            st.session_state["pedido_confirmar"] = False
            st.experimental_rerun()

# ===================== LLAMADO A AMBAS SECCIONES =====================
run_buscador()
run_pedidos()
