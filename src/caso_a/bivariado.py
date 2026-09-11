"""Relacion de las variables con el objetivo y entre ellas.

Se calcula siempre sobre las semanas de entrenamiento. Mirar las semanas de
prueba para decidir que variables entran seria contaminar la evaluacion.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.feature_selection import mutual_info_regression

CLAVE_SERIE = ["id_tienda", "id_producto"]
OBJETIVO = "unidades_vendidas"


def relacion_con_objetivo(marco: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    """Correlacion marginal e informacion mutua de cada variable.

    La correlacion marginal esta dominada por el nivel de cada serie, asi que
    sale alta para cualquier variable que refleje ese nivel. Se lee junto con
    :func:`relacion_intra_serie`.
    """
    objetivo = marco[OBJETIVO].to_numpy(float)
    matriz = marco[variables].to_numpy(float)
    info = mutual_info_regression(matriz, objetivo, random_state=0)

    filas = []
    for indice, variable in enumerate(variables):
        columna = marco[variable]
        spearman, _ = stats.spearmanr(columna, objetivo)
        pearson, _ = stats.pearsonr(columna, objetivo)
        filas.append(
            {
                "variable": variable,
                "spearman": spearman,
                "pearson": pearson,
                "info_mutua": info[indice],
            }
        )
    return pd.DataFrame(filas).sort_values("spearman", key=abs, ascending=False)


def relacion_intra_serie(marco: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    """Correlacion tras restar a cada columna la media de su serie.

    Aisla la variacion dentro de cada serie, que es el 10 % del total y lo unico
    que un modelo puede aportar sobre una tabla de medias.

    Advertencia: centrar dentro de grupos con pocas observaciones introduce un
    sesgo negativo conocido en las correlaciones con variables retardadas, del
    orden de 1/(T-1). Con seis semanas por serie ese sesgo ronda -0,2, asi que
    estos valores se leen como orientativos y la conclusion se toma con la
    evaluacion fuera de muestra de las lineas base.
    """
    grupo = marco.groupby(CLAVE_SERIE, observed=True)
    centrado = pd.DataFrame(
        {c: marco[c] - grupo[c].transform("mean") for c in [OBJETIVO, *variables]}
    )
    objetivo = centrado[OBJETIVO]

    filas = []
    for variable in variables:
        spearman, p_valor = stats.spearmanr(centrado[variable], objetivo)
        pearson, _ = stats.pearsonr(centrado[variable], objetivo)
        filas.append(
            {"variable": variable, "spearman": spearman, "pearson": pearson, "p": p_valor}
        )
    return pd.DataFrame(filas).sort_values("spearman", key=abs, ascending=False)


def inflacion_varianza(marco: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    """Factor de inflacion de varianza de cada variable.

    Mide cuanta de la variable explican las demas. Por encima de 10 hay
    redundancia severa: los coeficientes de un modelo lineal se vuelven
    inestables y cambian de signo con pequenas perturbaciones.
    """
    from sklearn.linear_model import LinearRegression

    filas = []
    for variable in variables:
        resto = [v for v in variables if v != variable]
        modelo = LinearRegression().fit(marco[resto], marco[variable])
        r2 = modelo.score(marco[resto], marco[variable])
        vif = np.inf if r2 >= 1 else 1 / (1 - r2)
        filas.append({"variable": variable, "R2_contra_resto": r2, "VIF": vif})
    return pd.DataFrame(filas).sort_values("VIF", ascending=False)
