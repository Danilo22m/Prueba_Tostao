"""Optimizacion de hiperparametros con busqueda bayesiana.

Se optimiza la perdida pinball en el nivel que se va a operar, evaluada sobre
los pliegues de ventana expansiva. Optimizar el error del pronostico central
seria ajustar para una metrica que la decision no usa.

Con 960 filas de entrenamiento y tres pliegues, el riesgo real no es quedarse
corto de busqueda sino ajustarse al ruido de la validacion. Por eso el numero de
ensayos es modesto y el espacio de busqueda, estrecho.
"""

from __future__ import annotations

from typing import Callable

import optuna
import pandas as pd

from caso_a import metrics, modelos, splits

optuna.logging.set_verbosity(optuna.logging.WARNING)

#: Ensayos por familia. Mas que esto solo compra sobreajuste de validacion.
ENSAYOS = 30


def _perdida_en_pliegues(
    constructor: Callable[[float], modelos.ModeloCuantil],
    marco: pd.DataFrame,
    particion: splits.Particion,
    nivel: float,
) -> float:
    """Perdida pinball media sobre los pliegues de ventana expansiva."""
    perdidas = []
    for ajuste, validacion in splits.pliegues_expansivos(particion.entrenamiento):
        entrena = splits.separar(marco, ajuste)
        valida = splits.separar(marco, validacion)
        prediccion = constructor(nivel).ajustar(entrena).predecir(valida)
        real = valida[modelos.OBJETIVO].to_numpy(float)
        perdidas.append(metrics.pinball(real, prediccion, nivel))
    return float(sum(perdidas) / len(perdidas))


ESPACIOS: dict[str, Callable[[optuna.Trial], dict]] = {
    "regresion cuantilica": lambda t: {
        "alpha": t.suggest_float("alpha", 1e-5, 1.0, log=True),
    },
    "boosting cuantilico": lambda t: {
        "max_depth": t.suggest_int("max_depth", 2, 5),
        "learning_rate": t.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "max_iter": t.suggest_int("max_iter", 100, 500, step=50),
        "min_samples_leaf": t.suggest_int("min_samples_leaf", 10, 60, step=10),
        "l2_regularization": t.suggest_float("l2_regularization", 1e-3, 10.0, log=True),
    },
    "bosque cuantilico": lambda t: {
        "n_estimators": t.suggest_int("n_estimators", 100, 400, step=100),
        "min_samples_leaf": t.suggest_int("min_samples_leaf", 5, 40, step=5),
        "max_features": t.suggest_float("max_features", 0.3, 1.0),
    },
    "ridge + residuales": lambda t: {
        "alpha": t.suggest_float("alpha", 1e-3, 100.0, log=True),
    },
    "gbr + residuales": lambda t: {
        "n_estimators": t.suggest_int("n_estimators", 100, 500, step=100),
        "max_depth": t.suggest_int("max_depth", 2, 5),
        "learning_rate": t.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "min_samples_leaf": t.suggest_int("min_samples_leaf", 10, 60, step=10),
    },
}


def optimizar(
    nombre: str,
    clase: type[modelos.ModeloCuantil],
    marco: pd.DataFrame,
    particion: splits.Particion,
    nivel: float,
    ensayos: int = ENSAYOS,
    semilla: int = 0,
) -> tuple[dict, float]:
    """Busca los mejores hiperparametros de una familia.

    Returns:
        Par de mejores parametros y perdida alcanzada. Si la familia no tiene
        espacio de busqueda definido, devuelve parametros vacios y su perdida
        con los valores por defecto.
    """
    if nombre not in ESPACIOS:
        return {}, _perdida_en_pliegues(clase, marco, particion, nivel)

    espacio = ESPACIOS[nombre]

    def objetivo(ensayo: optuna.Trial) -> float:
        parametros = espacio(ensayo)
        return _perdida_en_pliegues(
            lambda n: clase(n, **parametros), marco, particion, nivel
        )

    estudio = optuna.create_study(
        direction="minimize", sampler=optuna.samplers.TPESampler(seed=semilla)
    )
    estudio.optimize(objetivo, n_trials=ensayos, show_progress_bar=False)
    return estudio.best_params, float(estudio.best_value)
