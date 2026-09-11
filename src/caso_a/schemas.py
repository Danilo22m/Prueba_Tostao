"""Esquemas declarativos de las tablas de origen.

Cada esquema fija tipo, nulabilidad y rango admisible de cada columna. Validar
a la entrada hace que el pipeline falle pronto y con un mensaje util, en vez
de romperse varios pasos mas adelante con un error incomprensible.

Los nombres de columna son los que produce :mod:`caso_a.loaders`, es decir
despues de normalizar ``tamano_m2`` sin la letra ene.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.pandas import Check, Column, DataFrameSchema

#: Patron de los identificadores: STORE_01, PROD_003.
_ID_TIENDA = r"^STORE_\d+$"
_ID_PRODUCTO = r"^PROD_\d+$"

VENTAS = DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]", nullable=False),
        "id_tienda": Column(str, Check.str_matches(_ID_TIENDA), nullable=False),
        "id_producto": Column(str, Check.str_matches(_ID_PRODUCTO), nullable=False),
        "unidades_vendidas": Column(
            "int64", Check.greater_than_or_equal_to(0), nullable=False
        ),
    },
    unique=["fecha", "id_tienda", "id_producto"],
    strict=True,
    name="ventas_historicas",
)

INVENTARIO = DataFrameSchema(
    {
        "id_tienda": Column(str, Check.str_matches(_ID_TIENDA), nullable=False),
        "id_producto": Column(str, Check.str_matches(_ID_PRODUCTO), nullable=False),
        "stock_actual": Column("int64", Check.greater_than_or_equal_to(0), nullable=False),
    },
    unique=["id_tienda", "id_producto"],
    strict=True,
    name="inventario_actual",
)

CATALOGO = DataFrameSchema(
    {
        "id_producto": Column(str, Check.str_matches(_ID_PRODUCTO), nullable=False),
        "nombre": Column(str, nullable=False),
        "categoria": Column(str, nullable=False),
        "costo_unitario": Column("int64", Check.greater_than(0), nullable=False),
        "precio_venta": Column("int64", Check.greater_than(0), nullable=False),
        "costo_almacenamiento_semanal": Column(
            "int64", Check.greater_than_or_equal_to(0), nullable=False
        ),
    },
    unique=["id_producto"],
    strict=True,
    name="catalogo_productos",
)

TIENDAS = DataFrameSchema(
    {
        "id_tienda": Column(str, Check.str_matches(_ID_TIENDA), nullable=False),
        "ciudad": Column(str, nullable=False),
        "tamano_m2": Column("int64", Check.greater_than(0), nullable=False),
    },
    unique=["id_tienda"],
    strict=True,
    name="maestro_tiendas",
)

TENDENCIAS = DataFrameSchema(
    {
        "id_tienda": Column(str, Check.str_matches(_ID_TIENDA), nullable=False),
        "id_producto": Column(str, Check.str_matches(_ID_PRODUCTO), nullable=False),
        "trend_type": Column(str, nullable=False),
    },
    unique=["id_tienda", "id_producto"],
    strict=True,
    name="ground_truth_trends",
)

#: Esquema de cada tabla, indexado por la misma clave que ``paths.FICHEROS``.
ESQUEMAS: dict[str, DataFrameSchema] = {
    "ventas": VENTAS,
    "inventario": INVENTARIO,
    "catalogo": CATALOGO,
    "tiendas": TIENDAS,
    "tendencias": TENDENCIAS,
}


def margen_esperado() -> Check:
    """Comprueba que el precio de venta supera al coste unitario.

    Un producto con margen negativo invalidaria la politica de pedido, porque
    el coste de quedarse corto dejaria de ser positivo.
    """
    return Check(lambda df: df["precio_venta"] > df["costo_unitario"])
