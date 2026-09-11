"""Lineas base: las reglas simples contra las que se mide cualquier modelo.

Ninguna aprende nada. Todas se calculan con la historia propia de cada serie
hasta la semana anterior, de modo que son directamente comparables con el
modelo sobre las mismas filas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CLAVE_SERIE = ["id_tienda", "id_producto"]
OBJETIVO = "unidades_vendidas"


def media_historica(marco: pd.DataFrame) -> pd.Series:
    """Media de todas las semanas anteriores de la serie.

    Es la referencia principal: el univariado mostro que el 90 % de la varianza
    es entre series, asi que conocer el nivel de cada una ya explica casi todo.
    """
    return (
        marco.sort_values(CLAVE_SERIE + ["semana"])
        .groupby(CLAVE_SERIE, observed=True)[OBJETIVO]
        .transform(lambda s: s.shift(1).expanding().mean())
    )


def persistencia(marco: pd.DataFrame) -> pd.Series:
    """Lo que vendio la semana anterior."""
    return (
        marco.sort_values(CLAVE_SERIE + ["semana"])
        .groupby(CLAVE_SERIE, observed=True)[OBJETIVO]
        .shift(1)
    )


def media_movil(marco: pd.DataFrame, ventana: int = 4) -> pd.Series:
    """Media de las ultimas ``ventana`` semanas."""
    return (
        marco.sort_values(CLAVE_SERIE + ["semana"])
        .groupby(CLAVE_SERIE, observed=True)[OBJETIVO]
        .transform(lambda s: s.shift(1).rolling(ventana, min_periods=ventana).mean())
    )


def deriva(marco: pd.DataFrame, ventana: int = 4) -> pd.Series:
    """Ultima observacion mas la pendiente reciente.

    Es el liston exigente para las series con tendencia, que son 69 de 160.
    """
    ordenado = marco.sort_values(CLAVE_SERIE + ["semana"])
    ultima = ordenado.groupby(CLAVE_SERIE, observed=True)[OBJETIVO].shift(1)

    def _pendiente(valores: np.ndarray) -> float:
        if np.isnan(valores).any():
            return np.nan
        x = np.arange(valores.size, dtype=float)
        return float(np.polyfit(x, valores, 1)[0])

    pendiente = (
        ordenado.groupby(CLAVE_SERIE, observed=True)[OBJETIVO]
        .transform(lambda s: s.shift(1).rolling(ventana, min_periods=ventana).apply(_pendiente, raw=True))
    )
    return ultima + pendiente


#: Linea base de cada nombre, en el orden en que se reportan.
LINEAS_BASE = {
    "media historica": media_historica,
    "media movil 4": media_movil,
    "persistencia": persistencia,
    "deriva": deriva,
}


def calcular_todas(marco: pd.DataFrame) -> pd.DataFrame:
    """Anade una columna por linea base al panel."""
    salida = marco.sort_values(CLAVE_SERIE + ["semana"]).copy()
    for nombre, funcion in LINEAS_BASE.items():
        salida[f"base: {nombre}"] = funcion(salida)
    return salida
