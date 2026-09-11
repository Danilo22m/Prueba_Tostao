"""Carga de las tablas de origen con tipos declarados.

Ninguna funcion de este modulo deja que pandas infiera tipos ni codificacion.
La normalizacion de nombres de columna ocurre aqui y solo aqui, de modo que el
resto del proyecto trabaja siempre con los mismos nombres.
"""

from __future__ import annotations

from typing import Final

import pandas as pd
from pandera.pandas import DataFrameSchema

from caso_a import paths, schemas

#: Los CSV vienen con tildes y ene, asi que la codificacion se declara.
CODIFICACION: Final[str] = "utf-8"

#: Formato de fecha de ventas_historicas.csv.
FORMATO_FECHA: Final[str] = "%Y-%m-%d"

#: Renombrados aplicados al cargar. La ene de "tamano" da problemas en algunos
#: entornos y obliga a escapar el nombre en cualquier expresion de consulta.
RENOMBRADOS: Final[dict[str, str]] = {"tamaño_m2": "tamano_m2"}


def _leer(tabla: str, dtypes: dict[str, str], fechas: list[str] | None = None) -> pd.DataFrame:
    """Lee un CSV de origen con tipos explicitos y nombres normalizados.

    Args:
        tabla: Clave de la tabla, segun ``paths.FICHEROS``.
        dtypes: Tipo de cada columna no temporal, con el nombre ya normalizado.
        fechas: Columnas a parsear como fecha, o ``None``.

    Returns:
        El DataFrame leido, con las columnas renombradas.
    """
    ruta = paths.ruta_datos(tabla)
    crudo = pd.read_csv(ruta, encoding=CODIFICACION, dtype=str, keep_default_na=False)
    crudo = crudo.rename(columns=RENOMBRADOS)

    for columna in fechas or []:
        crudo[columna] = pd.to_datetime(crudo[columna], format=FORMATO_FECHA)

    for columna, tipo in dtypes.items():
        if tipo != "str":
            crudo[columna] = pd.to_numeric(crudo[columna]).astype(tipo)
        else:
            crudo[columna] = crudo[columna].astype("str")

    return crudo


def cargar_ventas() -> pd.DataFrame:
    """Ventas diarias por tienda y producto, 14.560 filas esperadas."""
    return _leer(
        "ventas",
        dtypes={"id_tienda": "str", "id_producto": "str", "unidades_vendidas": "int64"},
        fechas=["fecha"],
    )


def cargar_inventario() -> pd.DataFrame:
    """Foto unica del stock por tienda y producto, 160 filas esperadas."""
    return _leer(
        "inventario",
        dtypes={"id_tienda": "str", "id_producto": "str", "stock_actual": "int64"},
    )


def cargar_catalogo() -> pd.DataFrame:
    """Maestro de los 8 SKU con sus precios y costes, en pesos por unidad."""
    return _leer(
        "catalogo",
        dtypes={
            "id_producto": "str",
            "nombre": "str",
            "categoria": "str",
            "costo_unitario": "int64",
            "precio_venta": "int64",
            "costo_almacenamiento_semanal": "int64",
        },
    )


def cargar_tiendas() -> pd.DataFrame:
    """Maestro de las 20 tiendas con ciudad y superficie."""
    return _leer(
        "tiendas",
        dtypes={"id_tienda": "str", "ciudad": "str", "tamano_m2": "int64"},
    )


def cargar_tendencias() -> pd.DataFrame:
    """Patron real con el que se genero cada serie.

    Advertencia: esta tabla describe el proceso generador durante todo el
    periodo, incluidas las semanas reservadas para prueba. Se usa solo para
    diagnostico y nunca como variable de entrada de un modelo.
    """
    return _leer(
        "tendencias",
        dtypes={"id_tienda": "str", "id_producto": "str", "trend_type": "str"},
    )


#: Funcion de carga de cada tabla, indexada como ``paths.FICHEROS``.
CARGADORES = {
    "ventas": cargar_ventas,
    "inventario": cargar_inventario,
    "catalogo": cargar_catalogo,
    "tiendas": cargar_tiendas,
    "tendencias": cargar_tendencias,
}


def cargar_todo(validar: bool = True) -> dict[str, pd.DataFrame]:
    """Carga las cinco tablas de origen.

    Args:
        validar: Si es ``True``, aplica el esquema de cada tabla y lanza
            ``SchemaError`` ante la primera desviacion.

    Returns:
        Diccionario de tabla a DataFrame.
    """
    tablas: dict[str, pd.DataFrame] = {}
    for nombre, cargador in CARGADORES.items():
        marco = cargador()
        if validar:
            esquema: DataFrameSchema = schemas.ESQUEMAS[nombre]
            marco = esquema.validate(marco, lazy=True)
        tablas[nombre] = marco
    return tablas
