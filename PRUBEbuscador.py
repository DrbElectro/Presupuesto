#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from datetime import date

import pandas as pd
import streamlit as st
from streamlit.runtime.scriptrunner import RerunException, RerunData
from streamlit.components.v1 import html as st_html

import config
import utils

# ===================== AUTENTICACIÓN =====================
PASSWORD = "1224"
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

# ===================== HELPERS COMUNES =====================
def copy_to_clipboard_button(text: str, label="📋 Copiar resultado"):
    """Botón de copiado al portapapeles (sin librerías extra)."""
    import json, uuid
    uid = "btn_" + uuid.uuid4().hex
    payload = json.dumps(text)
    st_html(
        f"""
        <div style="display:flex;gap:.5rem;align-items:center;">
          <button id="{uid}" style="
              padding:.6rem 1rem;border:1px solid #ddd;border-radius:8px;
              background:#f7f7f7;cursor:pointer;font-weight:600;">
            {label}
          </button>
          <span id="{uid}_msg" style="color:#666;font-size:12px;"></span>
        </div>
        <script>
        const btn  = document.getElementById("{uid}");
        const msg  = document.getElementById("{uid}_msg");
        const text = {payload};
        btn.addEventListener('click', async () => {{
          try {{
            await navigator.clipboard.writeText(text);
            btn.textContent = "✅ Copiado";
            msg.textContent = "Listo para pegar";
            setTimeout(() => {{
              btn.textContent = "{label}";
              msg.textContent = "";
            }}, 1600);
          }} catch (e) {{
            btn.textContent = "❌ Error";
            msg.textContent = "Permití el acceso al portapapeles e intentá de nuevo";
            setTimeout(() => {{
              btn.textContent = "{label}";
              msg.textContent = "";
            }}, 2200);
          }}
        }});
        </script>
        """,
        height=60,
    )

# ===================== SOLAPA PRESUPUESTO =====================
def solapa_presupuesto(precios_df, costos_df, clave_estado, titulo):
    st.subheader(titulo)
    precios_df.columns = precios_df.columns.str.strip()
    if clave_estado not in st.session_state:
        st.session_state[clave_estado] = []

    # Buscador
    busq = st.text_input("Buscar modelo o marca", key=f"{clave_estado}_buscador").strip().upper()
    df_f = precios_df.copy()
    if busq:
        df_f = df_f[
            df_f["Marca"].str.upper().str.contains(busq) |
            df_f["Modelo"].str.upper().str.contains(busq)
        ]

    # Marca / Modelo
    c1, c2 = st.columns(2)
    with c1:
        marca_sel = st.selectbox("Marca", sorted(df_f["Marca"].dropna().unique()), key=f"{clave_estado}_marca")
    with c2:
        modelo_sel = st.selectbox(
            "Modelo",
            sorted(df_f[df_f["Marca"] == marca_sel]["Modelo"].dropna().unique()),
            key=f"{clave_estado}_modelo"
        )

    # Dinámicos
    cols     = precios_df.columns.tolist()
    prov_col = next(c for c in cols if "proveedor" in c.lower())
    prec_col = next(c for c in cols if "precio"    in c.lower())
    col_col  = next(c for c in cols if "color"     in c.lower())
    gan_col  = next(c for c in cols if "ganancia"  in c.lower())
    mask_p = (precios_df["Marca"] == marca_sel) & (precios_df["Modelo"] == modelo_sel)

    # Cálculo manual?
    calc_man = st.checkbox("Calcular manualmente", key=f"{clave_estado}_calcular")
    if calc_man:
        # manual inputs...
        m1, m2 = st.columns(2)
        marca_m  = m1.text_input("Marca", value=marca_sel, key=f"{clave_estado}_man_marca")
        modelo_m = m2.text_input("Modelo", value=modelo_sel, key=f"{clave_estado}_man_modelo")

        opts = sorted(
            costos_df[
                (costos_df["Marca"]  == marca_m) &
                (costos_df["Modelo"] == modelo_m)
            ]["Proveedor"].dropna().unique()
        )
        col_p, col_cost, col_blue = st.columns(3)
        # ✅ corregido: sin '}' extra y usando paréntesis
        prov_m = (
            col_p.selectbox("Proveedor", opts, key=f"{clave_estado}_man_prov")
            if opts
            else col_p.text_input("Proveedor", key=f"{clave_estado}_man_prov")
        )

        mask_c  = (costos_df["Marca"]==marca_m)&(costos_df["Modelo"]==modelo_m)&(costos_df["Proveedor"]==prov_m)
        mask_cm = (costos_df["Marca"]==marca_m)&(costos_df["Modelo"]==modelo_m)
        if mask_c.any():
            default_cost = float(costos_df.loc[mask_c, "Costo USD"].iat[0])
        elif mask_cm.any():
            default_cost = float(costos_df.loc[mask_cm, "Costo USD"].iat[0])
        else:
            default_cost = 0.0

        costo_m = col_cost.number_input("Costo USD", min_value=0.0, format="%.2f",
                                        value=default_cost, key=f"{clave_estado}_man_costo")
        blue_m  = col_blue.number_input("Dólar Blue", min_value=0.0, format="%.2f",
                                        key=f"{clave_estado}_man_blue")

        g1, g2, g3 = st.columns(3)
        pct_m    = g1.number_input("% Ganancia", min_value=0.0, format="%.2f",
                                   value=10.0, key=f"{clave_estado}_man_pct")
        # ✅ corregido: llaves balanceadas
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
                "Marca":     marca_m,
                "Modelo":    modelo_m,
                "Precio":    precio_str,
                "Colores":   "" if man_with_colors else "",
                "Proveedor": prov_m,
            })
            st.success(f"{marca_m} {modelo_m} agregado: {precio_str}")

    else:
        # automático
        if mask_p.any():
            resultado = precios_df.loc[mask_p].iloc[[0]]
            st.write("Precios:")
            st.dataframe(resultado[[prov_col, prec_col, gan_col]],
                         use_container_width=True, hide_index=True)

            costos = costos_df[(costos_df["Marca"]==marca_sel)&(costos_df["Modelo"]==modelo_sel)]
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
                raw        = str(resultado[prec_col].iat[0]).strip()
                precio_val = raw if raw.lower().startswith("usd") else f"USD {raw}"
                color_val  = resultado[col_col].iat[0] if auto_with_colors else ""
                st.session_state[clave_estado].append({
                    "Marca":     marca_sel,
                    "Modelo":    modelo_sel,
                    "Precio":    precio_val,
                    "Colores":   color_val,
                    "Proveedor": str(resultado[prov_col].iat[0]).strip(),
                })
                st.success("Ítem agregado al presupuesto.")
        else:
            st.info("Modelo no encontrado. Marca 'Calcular manualmente' para agregarlo.")

    # detalle y total
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
        st.text_area("Mensaje para copiar", value=msg, height=200, key=f"{clave_estado}_msg")

        if st.button("Limpiar presupuesto", key=f"{clave_estado}_clear_all"):
            st.session_state[clave_estado] = []
            raise RerunException(RerunData())

def run_presupuesto():
    EXCEL_PATH   = str(config.CATALOGO_PATH)
    proveedores  = ["Eze", "Di", "Ale"]
    sheets       = pd.read_excel(EXCEL_PATH, sheet_name=proveedores)
    costos_list  = []
    for prov, dfp in sheets.items():
        price_col = next(c for c in dfp.columns if "precio" in c.lower())
        dfp = dfp.rename(columns={price_col: "Costo USD"})
        dfp["Costo USD"] = pd.to_numeric(dfp["Costo USD"], errors="coerce").fillna(0)
        dfp["Proveedor"] = prov
        costos_list.append(dfp[["Marca","Modelo","Proveedor","Costo USD"]])
    costos_df    = pd.concat(costos_list, ignore_index=True)
    precios10_df = pd.read_excel(EXCEL_PATH, sheet_name="10%")
    solapa_presupuesto(precios10_df, costos_df, "presupuesto_items", "Presupuesto")

# ===================== RUN PEDIDOS =====================
def run_pedidos():
    if "pedido_items" not in st.session_state:
        st.session_state["pedido_items"] = []
    if "pedido_confirmar" not in st.session_state:
        st.session_state["pedido_confirmar"] = False
    if "contenido_txt" not in st.session_state:
        st.session_state["contenido_txt"] = ""

    st.subheader("Nuevo Pedido")

    c1, c2, c3 = st.columns(3)
    is_envio  = c1.checkbox("Envío", True, key="np_envio")
    is_retiro = c2.checkbox("Retiro", False, key="np_retiro")
    manual    = c3.checkbox("Carga Manual", key="np_manual")
    if is_envio and is_retiro:
        st.warning("Seleccione solo Envío o Retiro.")
        return

    df_cat = utils.load_catalogue()

    if not manual:
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

    # Mostrar ítems
    if st.session_state["pedido_items"]:
        st.markdown("**Ítems en este pedido:**")
        for idx, itm in enumerate(st.session_state["pedido_items"]):
            cA, cB = st.columns([8,1])
            cA.write(f"{idx+1}. {itm['Cantidad']}× {itm['Marca']} {itm['Modelo']} — Color {itm['Color']} — USD {itm['Costo USD']:.2f}")
            if cB.button("❌", key=f"del_{idx}"):
                st.session_state["pedido_items"].pop(idx)
                st.experimental_rerun()

    # Datos del pedido
    row = st.columns(9)
    direccion   = row[0].text_input("Dirección", key="np_direccion")
    localidad   = row[1].text_input("Localidad", key="np_localidad")
    horario     = row[2].text_input("Horario", key="np_horario")
    costo_envio = row[3].number_input("Costo envío", 0.0, format="%.2f", key="np_costo_envio")
    moneda      = row[4].selectbox("Moneda", ["USD","ARS"], key="np_moneda")
    importe     = row[5].number_input("Importe", 0.0, format="%.2f", key="np_importe")
    aclarac     = row[6].text_input("Aclaración", key="np_aclaracion")
    cliente     = row[7].text_input("Cliente", key="np_nombre")
    celular     = row[8].text_input("Celular", key="np_celular")

    # Preview / Copiar
    if not st.session_state["pedido_confirmar"]:
        if st.button("📝 Mostrar Pedido para Copiar", key="btn_preview"):
            txt  = ("Retiro:\n\n" if is_retiro else "Envío:\n\n")
            for itm in st.session_state["pedido_items"]:
                txt += f"{itm['Cantidad']}× {itm['Marca'].upper()} {itm['Modelo'].upper()} {itm['Color']}\n"
            if not is_retiro:
                txt += f"\nDirección: {direccion}\nLocalidad: {localidad}\n"
            txt += f"Horario: {horario}\n\n"
            pay  = (f"$ {int(importe):,}".replace(",",".") if moneda=="ARS" else f"USD {int(importe)}")
            if costo_envio > 0:
                pay += (f" + Envío $ {int(costo_envio):,}".replace(",",".") if moneda=="ARS" else f" + Envío $ {int(costo_envio)}")
            txt += f"PAGA: {pay}\n\n"
            if aclarac:
                txt += aclarac + "\n"
            txt += f"Recibe: {cliente} – {celular}\n"

            st.session_state["contenido_txt"]    = txt
            st.session_state["pedido_confirmar"] = True
            st.experimental_rerun()

    if st.session_state["pedido_confirmar"]:
        st.markdown("### Pedido listo para copiar")
        st.text_area("", value=st.session_state["contenido_txt"], height=350, key="txt_final")
        if st.button("🔄 Volver", key="btn_back"):
            st.session_state["pedido_confirmar"] = False
            st.experimental_rerun()

# ===================== LISTADOS (Ajuste de precios: SOLO precio) =====================
# --- Regex y helpers del módulo de ajuste (versión minimalista que solo reemplaza precios) ---

# Token numérico tolerante: 1.234 | 1,234 | 1200,50 | 1200.50 | 1 200
_L_NUM = r"""
    (?:
        [0-9]{1,3}(?:[.,\s][0-9]{3})+(?:[.,][0-9]+)?   # miles con opcional decimales
        |
        [0-9]+(?:[.,][0-9]+)?                          # enteros/decimales simples
    )
"""

# Monedas soportadas (incluye variantes pegadas): USD, US$, US$D, U$S, U$D, USS, $, 💲
# Soporta: USD720, 720USD, US$ 720, U$D1390, $720, 💲 720, etc. y también *USD 720*
PRICE_TOKEN_RE = re.compile(
    rf"""
    (?P<full>
        \*?\s*
        (?:
            (?:(?P<cur1>USD|US\$D|US\$|U\$S|U\$D|USS|\$|💲))\s*(?P<num1>{_L_NUM})
            |
            (?P<num2>{_L_NUM})\s*(?P<cur2>USD|US\$D|US\$|U\$S|U\$D|USS|\$|💲)
        )
        \s*\*?
    )
    """,
    re.IGNORECASE | re.VERBOSE
)

# Número pelado al FINAL de la línea (fallback si no hay símbolo)
BARE_NUMBER_AT_END_RE = re.compile(
    rf'(?<![A-Za-z])({_L_NUM})\s*$',
    re.IGNORECASE | re.VERBOSE
)

def _parse_number_general(num_str: str) -> float:
    """Convierte strings numéricos comunes en float, contemplando miles/decimales."""
    s = num_str.strip().replace(' ', '')
    has_comma = ',' in s
    has_dot   = '.' in s
    if has_comma and has_dot:
        # El último separador encontrado decide decimal
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '')
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')
    elif has_comma and not has_dot:
        parts = s.split(',')
        if len(parts) >= 2 and all(len(p) == 3 for p in parts[1:]) and 1 <= len(parts[0]) <= 3:
            s = ''.join(parts)           # 1,234 -> 1234
        else:
            s = s.replace(',', '.')      # 1200,50 -> 1200.50
    elif has_dot and not has_comma:
        parts = s.split('.')
        if len(parts) >= 2 and all(len(p) == 3 for p in parts[1:]) and 1 <= len(parts[0]) <= 3:
            s = ''.join(parts)           # 1.234 -> 1234
    return float(s)

def _round_up_to_base(x: float, base: int) -> int:
    import math
    if base <= 0:
        base = 1
    return int(math.ceil(x / base) * base)

def _apply_rules_only_price(val: float, pct: float, min_inc_usd: float, base_mult: int) -> int:
    inc_pct   = val * (pct / 100.0)
    inc_final = max(inc_pct, float(min_inc_usd))
    val_adj   = val + inc_final
    return _round_up_to_base(val_adj, base=base_mult)

def _fmt_usd_block(value_int: int) -> str:
    """Formatea como  *USD X.XXX*  (punto de miles, sin decimales)."""
    formatted = f"{value_int:,}".replace(",", ".")
    return f" *USD {formatted}*"

def _replace_symbol_prices(line: str, pct: float, min_inc_usd: float, base_mult: int) -> tuple[str, bool]:
    """Reemplaza TODOS los tokens con símbolo/moneda por *USD X.XXX* sin tocar el resto del texto."""
    changed = False

    def _repl(m: re.Match) -> str:
        nonlocal changed
        num = m.group('num1') or m.group('num2')
        try:
            val = _parse_number_general(num)
        except ValueError:
            return m.group('full')  # no tocar si no parsea
        changed = True
        new_int = _apply_rules_only_price(val, pct, min_inc_usd, base_mult)
        return _fmt_usd_block(new_int)

    out = PRICE_TOKEN_RE.sub(_repl, line)
    # Asegurar un solo espacio antes de *USD y compactar espacios
    out = re.sub(r'\s*\*USD', ' *USD', out)
    out = re.sub(r'\s{2,}', ' ', out).rstrip()
    return out, changed

def _replace_bare_trailing(line: str, pct: float, min_inc_usd: float, base_mult: int,
                           bare_min_value: float) -> tuple[str, bool]:
    """Si no había símbolo: reemplaza número pelado FINAL como precio (si supera umbral)."""
    m = BARE_NUMBER_AT_END_RE.search(line)
    if not m:
        return line, False
    num_str = m.group(1)
    try:
        val = _parse_number_general(num_str)
    except ValueError:
        return line, False
    if val < float(bare_min_value):
        return line, False
    new_int = _apply_rules_only_price(val, pct, min_inc_usd, base_mult)
    out = line[:m.start()] + _fmt_usd_block(new_int)
    out = re.sub(r'\s*\*USD', ' *USD', out)
    out = re.sub(r'\s{2,}', ' ', out).rstrip()
    return out, True

def _adjust_line_only_price(line: str, pct: float, min_inc_usd: float, base_mult: int,
                            bare_min_value: float) -> tuple[str, bool]:
    """
    SOLO toca precios. No limpia emojis, no reordena texto.
    1) Reemplaza TODOS los tokens con moneda (USD, US$, US$D, U$S, U$D, $, 💲) pegados o no.
    2) Si no encontró, intenta con número pelado al final (si supera el umbral).
    """
    out, changed = _replace_symbol_prices(line, pct, min_inc_usd, base_mult)
    if changed:
        return out, True
    return _replace_bare_trailing(out, pct, min_inc_usd, base_mult, bare_min_value)

def _process_text_block_only_price(text: str, pct: float, min_inc_usd: float, base_mult: int,
                                   only_changed: bool, bare_min_value: float) -> tuple[str, int]:
    out_lines, changed_count = [], 0
    for ln in text.splitlines():
        new_ln, changed = _adjust_line_only_price(ln, pct, min_inc_usd, base_mult, bare_min_value)
        if changed:
            changed_count += 1
            out_lines.append(new_ln)
        else:
            if not only_changed:
                out_lines.append(ln)
    return "\n".join(out_lines), changed_count

def run_listados():
    st.subheader("Listados (ajuste de precios – solo precio)")
    st.caption("No modifica el texto original. Solo detecta y reemplaza precios por  *USD X.XXX*  (punto de miles).")

    DEFAULT_MIN_INC_USD = 30.0
    DEFAULT_BASE_MULT   = 5
    DEFAULT_PCT         = 10.0
    DEFAULT_BARE_MIN    = 100.0  # evita confundir 'IPHONE 13' como precio si no hay símbolo

    # Estado para limpiar el textarea sin error
    if 'listados_textarea_nonce' not in st.session_state:
        st.session_state['listados_textarea_nonce'] = 0
    TEXTAREA_KEY = f"listados_text__{st.session_state['listados_textarea_nonce']}"

    with st.form("form_listados"):
        c1, c2, c3, c4 = st.columns(4)
        pct = c1.number_input("Porcentaje de aumento (%)", min_value=0.0, max_value=1000.0,
                              value=DEFAULT_PCT, step=0.5, format="%.2f")
        min_inc_usd = c2.number_input("Mínimo por ítem (USD)", min_value=0.0, max_value=10000.0,
                                      value=DEFAULT_MIN_INC_USD, step=1.0, format="%.0f")
        base_mult = int(c3.number_input("Múltiplo de redondeo", min_value=1, max_value=100,
                                        value=DEFAULT_BASE_MULT, step=1))
        bare_min_value = c4.number_input("Umbral núm. pelado (USD)", min_value=0.0, max_value=10000.0,
                                         value=DEFAULT_BARE_MIN, step=5.0,
                                         help="Si no hay símbolo y el número final es menor a este valor, NO lo toma como precio (evita 'iPhone 13').")

        only_changed = st.checkbox("Mostrar solo líneas con cambios", value=False)

        st.text_area(
            "Pegá aquí la lista original",
            key=TEXTAREA_KEY,
            height=280,
            placeholder=(
                "Ejemplos:\n"
                "IPHONE 13 128GB MIDNIGHT - STARLIGHT 490\n"
                "US$ 1.250\n"
                "US$D720\n"
                "U$D1390\n"
                "USD720\n"
                "💲 535\n"
                "$690\n"
                "Precio al final sin símbolo 480\n"
            )
        )
        colb = st.columns([1,1,2])
        procesar = colb[0].form_submit_button("Procesar ✅")
        limpiar  = colb[1].form_submit_button("🧹 Limpiar")

    if 'listados_output' not in st.session_state:
        st.session_state['listados_output'] = ""
        st.session_state['listados_count']  = 0

    if limpiar:
        st.session_state['listados_output'] = ""
        st.session_state['listados_count']  = 0
        st.session_state['listados_textarea_nonce'] += 1  # borra textarea
        raise RerunException(RerunData())

    if procesar:
        texto_in = st.session_state.get(TEXTAREA_KEY, "")
        if not texto_in.strip():
            st.warning("Pegá la lista en el recuadro para procesarla.")
        else:
            resultado, cant = _process_text_block_only_price(
                texto_in, pct,
                min_inc_usd=min_inc_usd,
                base_mult=base_mult,
                only_changed=only_changed,
                bare_min_value=bare_min_value
            )
            st.session_state['listados_output'] = resultado
            st.session_state['listados_count']  = cant

    if st.session_state['listados_output']:
        st.success(f"¡Listo! Se ajustaron {st.session_state['listados_count']} línea(s). Copiá o descargá.")
        st.code(st.session_state['listados_output'], language="text")
        copy_to_clipboard_button(st.session_state['listados_output'], label="📋 Copiar resultado")
        st.download_button(
            "⬇️ Descargar como TXT",
            data=st.session_state['listados_output'].encode("utf-8"),
            file_name="lista_ajustada.txt",
            mime="text/plain",
            use_container_width=True,
        )

# ===================== INTERFAZ PRINCIPAL =====================
st.title("DRB Electro")
tab1, tab2, tab3 = st.tabs(["Presupuesto", "Nuevo Pedido", "Listados"])
with tab1:
    run_presupuesto()
with tab2:
    run_pedidos()
with tab3:
    run_listados()
