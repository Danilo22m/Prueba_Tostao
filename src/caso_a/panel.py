"""Construccion del panel semanal a partir de las ventas diarias.

La decision de pedido es semanal, asi que el objetivo se modela a esa
granularidad. El calendario de origen va del lunes 1 de enero al domingo 31 de
marzo de 2024, trece semanas completas, de modo que no hay semanas parciales
que descartar.
"""

from __future__ import annotations

import pandas as pd

CLAVE_SERIE = ["id_tienda", "id_producto"]

#: Numero de semanas completas del periodo.
SEMANAS = 13


def numerar_semanas(ventas: pd.DataFrame) -> pd.Series:
    """Asigna a cada fecha su numero de semana, empezando en 1.

    Se cuenta desde la primera fecha del panel, que es lunes, en bloques de
    siete dias. Asi cada semana va de lunes a domingo sin depender de la
    convencion de numeracion ISO.
    """
    origen = ventas["fecha"].min()
    return ((ventas["fecha"] - origen).dt.days // 7) + 1


def a_semanal(ventas: pd.DataFrame) -> pd.DataFrame:
    """Agrega las ventas diarias a totales semanales por serie.

    Args:
        ventas: Tabla de ventas diarias ya validada.

    Returns:
        Panel de 2.080 filas con id_tienda, id_producto, semana y unidades.

    Raises:
        ValueError: Si la agregacion no conserva el total de unidades o si
            alguna serie no tiene las trece semanas completas.
    """
    con_semana = ventas.assign(semana=numerar_semanas(ventas))
    panel = (
        con_semana.groupby(CLAVE_SERIE + ["semana"], observed=True)["unidades_vendidas"]
        .sum()
        .reset_index()
        .sort_values(CLAVE_SERIE + ["semana"], ignore_index=True)
    )

    if int(panel["unidades_vendidas"].sum()) != int(ventas["unidades_vendidas"].sum()):
        raise ValueError("La agregacion semanal no conserva el total de unidades.")

    por_serie = panel.groupby(CLAVE_SERIE, observed=True).size()
    if not (por_serie == SEMANAS).all():
        raise ValueError(f"Hay series sin las {SEMANAS} semanas completas.")

    return panel


def enriquecer(panel: pd.DataFrame, catalogo: pd.DataFrame, tiendas: pd.DataFrame) -> pd.DataFrame:
    """Une al panel los atributos fijos de producto y tienda.

    La union es por la izquierda y se comprueba que no cambie el numero de
    filas, para que un fallo de integridad no pase inadvertido.
    """
    filas = len(panel)
    salida = panel.merge(catalogo, on="id_producto", how="left", validate="many_to_one")
    salida = salida.merge(tiendas, on="id_tienda", how="left", validate="many_to_one")
    if len(salida) != filas:
        raise ValueError("La union con los maestros altero el numero de filas.")
    if salida.isna().any().any():
        raise ValueError("La union con los maestros introdujo nulos.")
    return salida
