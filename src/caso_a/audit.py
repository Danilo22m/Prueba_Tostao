"""Auditoria de los datos de origen del Caso A.

Cada comprobacion se expresa como una afirmacion verificable, no como algo que
se mira a ojo. El resultado de una comprobacion fallida es un hallazgo, y los
hallazgos van a la memoria tecnica.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

#: Dimensiones esperadas del panel, derivadas del enunciado.
TIENDAS_ESPERADAS = 20
PRODUCTOS_ESPERADOS = 8
SERIES_ESPERADAS = TIENDAS_ESPERADAS * PRODUCTOS_ESPERADOS
DIAS_ESPERADOS = 91


@dataclass(frozen=True)
class Resultado:
    """Resultado de una comprobacion de auditoria.

    Attributes:
        nombre: Que se comprueba, en una linea.
        supera: ``True`` si el dato cumple lo esperado.
        esperado: Valor o condicion que se esperaba.
        obtenido: Lo que realmente hay en los datos.
        detalle: Contexto adicional cuando la comprobacion falla.
    """

    nombre: str
    supera: bool
    esperado: str
    obtenido: str
    detalle: str = ""


def _r(nombre: str, supera: bool, esperado: object, obtenido: object, detalle: str = "") -> Resultado:
    return Resultado(nombre, bool(supera), str(esperado), str(obtenido), detalle)


# --------------------------------------------------------------------------
# Comprobaciones de forma del panel
# --------------------------------------------------------------------------

def comprobar_dimensiones(tablas: dict[str, pd.DataFrame]) -> list[Resultado]:
    """Numero de tiendas, productos y series presentes en ventas."""
    ventas = tablas["ventas"]
    n_tiendas = ventas["id_tienda"].nunique()
    n_productos = ventas["id_producto"].nunique()
    n_series = len(ventas.groupby(["id_tienda", "id_producto"], observed=True))
    return [
        _r("Tiendas distintas en ventas", n_tiendas == TIENDAS_ESPERADAS, TIENDAS_ESPERADAS, n_tiendas),
        _r("Productos distintos en ventas", n_productos == PRODUCTOS_ESPERADOS, PRODUCTOS_ESPERADOS, n_productos),
        _r("Series tienda-producto", n_series == SERIES_ESPERADAS, SERIES_ESPERADAS, n_series),
    ]


def comprobar_longitud_series(tablas: dict[str, pd.DataFrame]) -> list[Resultado]:
    """Cada serie debe tener el mismo numero de dias, sin huecos."""
    ventas = tablas["ventas"]
    por_serie = ventas.groupby(["id_tienda", "id_producto"], observed=True)["fecha"].nunique()
    unicos = sorted(por_serie.unique().tolist())
    todas_iguales = len(unicos) == 1
    detalle = "" if todas_iguales else f"longitudes encontradas: {unicos}"
    return [
        _r("Todas las series tienen la misma longitud", todas_iguales, "un unico valor", unicos, detalle),
        _r("Dias por serie", unicos == [DIAS_ESPERADOS], DIAS_ESPERADOS, unicos),
    ]


def comprobar_rango_fechas(tablas: dict[str, pd.DataFrame]) -> list[Resultado]:
    """El calendario de ventas debe ser continuo, sin dias ausentes."""
    fechas = tablas["ventas"]["fecha"]
    inicio, fin = fechas.min(), fechas.max()
    esperadas = pd.date_range(inicio, fin, freq="D")
    presentes = pd.DatetimeIndex(sorted(fechas.unique()))
    faltan = esperadas.difference(presentes)
    return [
        _r("Calendario continuo", len(faltan) == 0, "0 dias ausentes", len(faltan),
           "" if len(faltan) == 0 else f"primeros ausentes: {list(faltan[:5])}"),
        _r("Rango de fechas", True, "informativo", f"{inicio.date()} a {fin.date()} ({len(esperadas)} dias)"),
    ]


def comprobar_duplicados(tablas: dict[str, pd.DataFrame]) -> list[Resultado]:
    """Ninguna tabla debe repetir su clave natural."""
    claves = {
        "ventas": ["fecha", "id_tienda", "id_producto"],
        "inventario": ["id_tienda", "id_producto"],
        "catalogo": ["id_producto"],
        "tiendas": ["id_tienda"],
        "tendencias": ["id_tienda", "id_producto"],
    }
    salida = []
    for tabla, clave in claves.items():
        n_dup = int(tablas[tabla].duplicated(subset=clave).sum())
        salida.append(_r(f"Clave unica en {tabla}", n_dup == 0, 0, n_dup))
    return salida


# --------------------------------------------------------------------------
# Comprobaciones de integridad entre tablas
# --------------------------------------------------------------------------

def comprobar_integridad(tablas: dict[str, pd.DataFrame]) -> list[Resultado]:
    """Toda clave usada en ventas debe existir en su maestro, y viceversa."""
    ventas, catalogo, tiendas = tablas["ventas"], tablas["catalogo"], tablas["tiendas"]
    inventario, tendencias = tablas["inventario"], tablas["tendencias"]

    prod_ventas = set(ventas["id_producto"])
    prod_catalogo = set(catalogo["id_producto"])
    tienda_ventas = set(ventas["id_tienda"])
    tienda_maestro = set(tiendas["id_tienda"])

    series_ventas = set(map(tuple, ventas[["id_tienda", "id_producto"]].drop_duplicates().to_numpy()))
    series_inv = set(map(tuple, inventario[["id_tienda", "id_producto"]].to_numpy()))
    series_tend = set(map(tuple, tendencias[["id_tienda", "id_producto"]].to_numpy()))

    return [
        _r("Productos de ventas presentes en catalogo", not (prod_ventas - prod_catalogo), 0, len(prod_ventas - prod_catalogo)),
        _r("Productos de catalogo usados en ventas", not (prod_catalogo - prod_ventas), 0, len(prod_catalogo - prod_ventas)),
        _r("Tiendas de ventas presentes en maestro", not (tienda_ventas - tienda_maestro), 0, len(tienda_ventas - tienda_maestro)),
        _r("Tiendas de maestro usadas en ventas", not (tienda_maestro - tienda_ventas), 0, len(tienda_maestro - tienda_ventas)),
        _r("Inventario cubre todas las series", series_ventas == series_inv, 0, len(series_ventas ^ series_inv)),
        _r("Tendencias cubren todas las series", series_ventas == series_tend, 0, len(series_ventas ^ series_tend)),
    ]


# --------------------------------------------------------------------------
# Comprobaciones de valores
# --------------------------------------------------------------------------

def comprobar_valores(tablas: dict[str, pd.DataFrame]) -> list[Resultado]:
    """Nulos, negativos y coherencia economica del catalogo."""
    salida = []
    for tabla, marco in tablas.items():
        n_nulos = int(marco.isna().sum().sum())
        salida.append(_r(f"Sin nulos en {tabla}", n_nulos == 0, 0, n_nulos))

    negativas = int((tablas["ventas"]["unidades_vendidas"] < 0).sum())
    salida.append(_r("Unidades vendidas no negativas", negativas == 0, 0, negativas))

    stock_neg = int((tablas["inventario"]["stock_actual"] < 0).sum())
    salida.append(_r("Stock no negativo", stock_neg == 0, 0, stock_neg))

    catalogo = tablas["catalogo"]
    sin_margen = catalogo.loc[catalogo["precio_venta"] <= catalogo["costo_unitario"], "id_producto"]
    salida.append(_r("Precio por encima del coste en todos los SKU", sin_margen.empty, 0, len(sin_margen),
                     "" if sin_margen.empty else f"SKU sin margen: {list(sin_margen)}"))
    return salida


def comprobar_balance(tablas: dict[str, pd.DataFrame]) -> list[Resultado]:
    """Si el diseno esta balanceado, la codificacion por frecuencia es inutil.

    Con el mismo numero de observaciones por categoria, codificar por
    frecuencia devuelve una constante y borra la senal de esa variable.
    """
    ventas = tablas["ventas"]
    por_producto = ventas["id_producto"].value_counts()
    por_tienda = ventas["id_tienda"].value_counts()
    bal_prod = por_producto.nunique() == 1
    bal_tienda = por_tienda.nunique() == 1
    return [
        _r("Diseno balanceado por producto", bal_prod, "misma frecuencia", f"{por_producto.min()} a {por_producto.max()}",
           "codificacion por frecuencia inservible en id_producto" if bal_prod else ""),
        _r("Diseno balanceado por tienda", bal_tienda, "misma frecuencia", f"{por_tienda.min()} a {por_tienda.max()}",
           "codificacion por frecuencia inservible en id_tienda" if bal_tienda else ""),
    ]


def comprobar_ceros(tablas: dict[str, pd.DataFrame]) -> list[Resultado]:
    """Dias sin venta: posible demanda censurada por quiebre de stock."""
    ventas = tablas["ventas"]
    n_ceros = int((ventas["unidades_vendidas"] == 0).sum())
    pct = 100 * n_ceros / len(ventas)
    return [
        _r("Dias con cero unidades", True, "informativo", f"{n_ceros} ({pct:.2f} %)",
           "Si es alto, la demanda registrada puede estar censurada por quiebres"),
    ]


#: Bloques de auditoria, en el orden en que se ejecutan.
BLOQUES: dict[str, Callable[[dict[str, pd.DataFrame]], list[Resultado]]] = {
    "Forma del panel": comprobar_dimensiones,
    "Longitud de las series": comprobar_longitud_series,
    "Calendario": comprobar_rango_fechas,
    "Claves duplicadas": comprobar_duplicados,
    "Integridad entre tablas": comprobar_integridad,
    "Valores": comprobar_valores,
    "Balance del diseno": comprobar_balance,
    "Ceros y censura": comprobar_ceros,
}


def auditar(tablas: dict[str, pd.DataFrame]) -> dict[str, list[Resultado]]:
    """Ejecuta todos los bloques de auditoria sobre las tablas cargadas."""
    return {nombre: funcion(tablas) for nombre, funcion in BLOQUES.items()}
