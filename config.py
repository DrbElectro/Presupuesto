# config.py
from pathlib import Path

# Ruta al Excel de catálogo de proveedores
CATALOGO_PATH = Path(__file__).parent / "Proveedores.xlsx"

# Carpeta donde mostrarían/guardaránse los Pedidos (aunque ahora solo mostrás)
PEDIDOS_DIR  = Path(__file__).parent / "Salida"
PEDIDOS_DIR.mkdir(exist_ok=True)

# Nombre del archivo de pedidos (para cuando quieras grabar en el futuro)
PEDIDOS_FILE = PEDIDOS_DIR / "Pedidos.xlsx"

# Encabezados que usa run_pedidos()
HEADERS_PEDIDOS = [
    "Estado",
    "Proveedor",
    "Marca",
    "Modelo",
    "Costo USD",
    "Color",
    "Cantidad",
    "Dirección",
    "Localidad",
    "Horario",
    "Moneda",
    "Importe",
    "Costo envío",
    "Aclaración",
    "Cliente",
    "Celular"
]
