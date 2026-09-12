"""Diagnostico del modelo: donde falla y por que predice lo que predice.

El error global ya esta medido. Este modulo lo rompe en pedazos, porque un
error medio del 12 % puede repartirse de forma uniforme o concentrarse en unas
pocas series, y la diferencia decide si la politica se puede implantar tal cual.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox

from caso_a import metrics, modelos

CLAVE_SERIE = ["id_tienda", "id_producto"]
OBJETIVO = "unidades_vendidas"


def error_por_grupo(marco: pd.DataFrame, prediccion: str, grupo: list[str] | str) -> pd.DataFrame:
    """Metricas de error calculadas por separado en cada grupo.

    Args:
        marco: Tabla con la demanda observada y la prediccion.
        prediccion: Nombre de la columna con el pronostico central.
        grupo: Columna o columnas por las que agrupar.
    """
    filas = []
    for clave, sub in marco.groupby(grupo, observed=True):
        real = sub[OBJETIVO].to_numpy(float)
        pred = sub[prediccion].to_numpy(float)
        etiqueta = clave if isinstance(clave, str) else " / ".join(map(str, np.atleast_1d(clave)))
        filas.append({
            "grupo": etiqueta,
            "n": len(sub),
            "demanda_media": float(real.mean()),
            "MAE": metrics.mae(real, pred),
            "WAPE": metrics.wape(real, pred),
            "sesgo": metrics.sesgo(real, pred),
        })
    return pd.DataFrame(filas).sort_values("WAPE", ascending=False)


def error_por_volumen(marco: pd.DataFrame, prediccion: str, tramos: int = 4) -> pd.DataFrame:
    """Error segun el volumen de la serie.

    Un error de diez unidades es grave en una serie que vende cuarenta y casi
    irrelevante en una que vende ciento cuarenta. El error medio en unidades
    trata a las dos igual, asi que conviene separarlas.
    """
    medias = marco.groupby(CLAVE_SERIE, observed=True)[OBJETIVO].transform("mean")
    etiquetas = [f"tramo {i + 1}" for i in range(tramos)]
    con_tramo = marco.assign(tramo=pd.qcut(medias, tramos, labels=etiquetas))
    resumen = error_por_grupo(con_tramo, prediccion, "tramo")
    return resumen.sort_values("demanda_media")


def resumen_por_serie(marco: pd.DataFrame, prediccion: str) -> pd.DataFrame:
    """Error de cada una de las series, para examinar la cola."""
    return error_por_grupo(marco, prediccion, CLAVE_SERIE)


def diagnostico_residuales(marco: pd.DataFrame, prediccion: str) -> dict[str, float]:
    """Estadisticos de los residuales del pronostico central.

    Comprueba tres cosas: que esten centrados, que su dispersion no crezca con
    el nivel predicho, y que no quede autocorrelacion sin capturar.
    """
    real = marco[OBJETIVO].to_numpy(float)
    pred = marco[prediccion].to_numpy(float)
    residual = real - pred

    # Heterocedasticidad: correlacion entre el valor predicho y el error absoluto.
    correlacion = float(np.corrcoef(pred, np.abs(residual))[0, 1])

    # Autocorrelacion de los residuales dentro de cada serie.
    p_valores = []
    for _, sub in marco.assign(residual=residual).groupby(CLAVE_SERIE, observed=True):
        serie = sub.sort_values("semana")["residual"]
        if serie.size >= 3:
            prueba = acorr_ljungbox(serie, lags=[1], return_df=True)
            p_valores.append(float(prueba["lb_pvalue"].iloc[0]))

    return {
        "media": float(residual.mean()),
        "desviacion": float(residual.std()),
        "asimetria": float(pd.Series(residual).skew()),
        "corr_pred_error": correlacion,
        "series_con_autocorrelacion": int(sum(p < 0.05 for p in p_valores)),
        "series_evaluadas": len(p_valores),
    }


def importancia_permutacion(
    modelo: modelos.ModeloCuantil,
    datos: pd.DataFrame,
    nivel: float,
    repeticiones: int = 20,
    semilla: int = 0,
) -> pd.DataFrame:
    """Degradacion de la perdida al barajar cada variable.

    Se baraja la columna en los datos de evaluacion y se mide cuanto empeora la
    perdida pinball. Es robusta a la colinealidad, al contrario que los
    coeficientes o la importancia interna de los arboles, y mide lo que de
    verdad importa: el efecto sobre la metrica de la decision.
    """
    generador = np.random.default_rng(semilla)
    real = datos[OBJETIVO].to_numpy(float)
    base = metrics.pinball(real, modelo.predecir(datos), nivel)

    filas = []
    for columna in modelo.temporales + modelos.ESTATICAS:
        perdidas = []
        for _ in range(repeticiones):
            alterado = datos.copy()
            alterado[columna] = generador.permutation(alterado[columna].to_numpy())
            perdidas.append(metrics.pinball(real, modelo.predecir(alterado), nivel))
        filas.append({
            "variable": columna,
            "perdida_barajada": float(np.mean(perdidas)),
            "degradacion": float(np.mean(perdidas)) - base,
            "degradacion_pct": 100 * (float(np.mean(perdidas)) / base - 1),
            "desviacion": float(np.std(perdidas)),
        })
    return pd.DataFrame(filas).sort_values("degradacion", ascending=False)


def coeficientes(modelo: modelos.ModeloCuantil) -> pd.DataFrame:
    """Coeficientes del modelo lineal, sobre variables estandarizadas.

    Al estar estandarizadas, la magnitud del coeficiente es comparable entre
    variables: indica cuantas unidades cambia la prediccion por cada desviacion
    tipica de esa variable.
    """
    interno = getattr(modelo, "_modelo", None)
    if interno is None or not hasattr(interno, "coef_"):
        raise TypeError("El modelo no expone coeficientes lineales.")

    nombres = list(modelo.temporales) + list(modelos.ESTATICAS)
    if modelo._codificador is not None:
        nombres += list(modelo._codificador.get_feature_names_out(modelos.CATEGORICAS))

    return (
        pd.DataFrame({"variable": nombres, "coeficiente": interno.coef_})
        .assign(magnitud=lambda d: d["coeficiente"].abs())
        .sort_values("magnitud", ascending=False)
        .drop(columns="magnitud")
        .reset_index(drop=True)
    )
