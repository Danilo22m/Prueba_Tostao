"""Metricas de error del pronostico.

Se descarta el error porcentual medio absoluto: aunque es calculable porque el
objetivo semanal no tiene ceros, penaliza mas sobrepredecir que infrapredecir, y
ese es justo el sesgo equivocado para una decision de inventario.

El error escalado usa como denominador la linea base de referencia, que aqui es
la media historica de cada serie y no la persistencia semanal. El univariado
mostro que la autocorrelacion semanal es 0,101, asi que la persistencia es un
rival debil y escalarse contra ella inflaria cualquier resultado.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def mae(real: np.ndarray, pred: np.ndarray) -> float:
    """Error absoluto medio, en unidades de producto."""
    return float(np.mean(np.abs(real - pred)))


def rmse(real: np.ndarray, pred: np.ndarray) -> float:
    """Raiz del error cuadratico medio; penaliza los errores grandes."""
    return float(np.sqrt(np.mean((real - pred) ** 2)))


def wape(real: np.ndarray, pred: np.ndarray) -> float:
    """Error porcentual ponderado: suma de errores sobre suma de demanda.

    Robusto y agregable: las series pequenas no distorsionan el total.
    """
    return float(np.sum(np.abs(real - pred)) / np.sum(np.abs(real)))


def smape(real: np.ndarray, pred: np.ndarray) -> float:
    """Error porcentual simetrico, acotado entre 0 y 2."""
    denominador = (np.abs(real) + np.abs(pred)) / 2
    return float(np.mean(np.abs(real - pred) / denominador))


def sesgo(real: np.ndarray, pred: np.ndarray) -> float:
    """Error medio con signo. Positivo significa que el modelo se queda corto.

    En inventario importa tanto como la magnitud: un modelo que infrapredice de
    forma sistematica arruina la politica aunque su error medio sea bajo.
    """
    return float(np.mean(real - pred))


def r2(real: np.ndarray, pred: np.ndarray) -> float:
    """Coeficiente de determinacion.

    Se reporta solo con advertencia: en un panel donde el 90 % de la varianza
    esta entre series, predecir la media de cada serie ya da 0,900.
    """
    sc_res = float(np.sum((real - pred) ** 2))
    sc_tot = float(np.sum((real - np.mean(real)) ** 2))
    return 1 - sc_res / sc_tot if sc_tot else float("nan")


def pinball(real: np.ndarray, pred: np.ndarray, nivel: float) -> float:
    """Perdida cuantilica en un nivel de servicio dado.

    Quedarse corto pesa ``nivel`` y pasarse pesa ``1 - nivel``. Escalada por la
    suma de los dos costes, es exactamente el coste esperado del newsvendor.
    """
    diferencia = real - pred
    return float(np.mean(np.maximum(nivel * diferencia, (nivel - 1) * diferencia)))


def cobertura(real: np.ndarray, inferior: np.ndarray, superior: np.ndarray) -> float:
    """Proporcion de observaciones dentro del intervalo."""
    return float(np.mean((real >= inferior) & (real <= superior)))


def resumen(real: np.ndarray, pred: np.ndarray, escala: float | None = None) -> dict[str, float]:
    """Calcula el juego completo de metricas puntuales.

    Args:
        real: Demanda observada.
        pred: Prediccion del modelo.
        escala: Error absoluto medio de la linea base de referencia. Si se da,
            se anade el error escalado, que vale menos de 1 cuando el modelo
            supera a esa referencia.
    """
    salida = {
        "MAE": mae(real, pred),
        "RMSE": rmse(real, pred),
        "WAPE": wape(real, pred),
        "sMAPE": smape(real, pred),
        "sesgo": sesgo(real, pred),
        "R2": r2(real, pred),
    }
    if escala:
        salida["escalado"] = salida["MAE"] / escala
    return salida


def tabla_resumen(resultados: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Ordena varios resumenes en una tabla comparable, de mejor a peor WAPE."""
    return pd.DataFrame(resultados).T.sort_values("WAPE")
