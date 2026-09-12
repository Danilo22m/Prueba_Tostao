"""Comparacion de familias con criterio alineado a la decision.

La familia no se elige por el error del pronostico central, porque la decision
de pedido no usa la mediana. Se elige por la perdida pinball evaluada en los
niveles que se van a operar de verdad.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from caso_a import metrics, modelos, splits

CLAVE_SERIE = ["id_tienda", "id_producto"]
OBJETIVO = "unidades_vendidas"


def evaluar_familia(
    clase: type[modelos.ModeloCuantil],
    entrenamiento: pd.DataFrame,
    evaluacion: pd.DataFrame,
    niveles: tuple[float, ...],
    parametros: dict | None = None,
) -> dict[float, np.ndarray]:
    """Ajusta y predice una familia en cada nivel pedido."""
    extras = parametros or {}
    return {
        nivel: clase(nivel, **extras).ajustar(entrenamiento).predecir(evaluacion)
        for nivel in niveles
    }


def comparar(
    familias: dict[str, type[modelos.ModeloCuantil]],
    entrenamiento: pd.DataFrame,
    evaluacion: pd.DataFrame,
    niveles: tuple[float, ...],
    parametros: dict[str, dict] | None = None,
) -> tuple[pd.DataFrame, dict[str, dict[float, np.ndarray]]]:
    """Compara las familias en todos los niveles.

    Returns:
        Tabla de metricas por familia y nivel, y las predicciones crudas, que
        hacen falta para los contrastes estadisticos posteriores.
    """
    real = evaluacion[OBJETIVO].to_numpy(float)
    predicciones: dict[str, dict[float, np.ndarray]] = {}
    filas = []

    for nombre, clase in familias.items():
        predicciones[nombre] = evaluar_familia(
            clase, entrenamiento, evaluacion, niveles, (parametros or {}).get(nombre)
        )
        for nivel, prediccion in predicciones[nombre].items():
            fila = {
                "familia": nombre,
                "nivel": nivel,
                "pinball": metrics.pinball(real, prediccion, nivel),
            }
            if nivel == 0.5:
                fila |= {
                    "WAPE": metrics.wape(real, prediccion),
                    "MAE": metrics.mae(real, prediccion),
                    "sesgo": metrics.sesgo(real, prediccion),
                }
            filas.append(fila)

    return pd.DataFrame(filas), predicciones


def diebold_mariano(
    real: np.ndarray, uno: np.ndarray, otro: np.ndarray, nivel: float
) -> tuple[float, float]:
    """Contrasta si dos pronosticos difieren de forma significativa.

    Compara la perdida pinball observacion a observacion. La hipotesis nula es
    que la diferencia media de perdida es cero, es decir que los dos pronosticos
    son igual de buenos.

    Returns:
        Estadistico y p-valor. Un p-valor alto significa que no hay evidencia
        para declarar un ganador.
    """
    def perdida(prediccion: np.ndarray) -> np.ndarray:
        diferencia = real - prediccion
        return np.maximum(nivel * diferencia, (nivel - 1) * diferencia)

    diferencial = perdida(uno) - perdida(otro)
    if np.allclose(diferencial, 0):
        return 0.0, 1.0
    estadistico = diferencial.mean() / (diferencial.std(ddof=1) / np.sqrt(diferencial.size))
    p_valor = 2 * (1 - stats.norm.cdf(abs(estadistico)))
    return float(estadistico), float(p_valor)


def banda_remuestreo(
    real: np.ndarray,
    prediccion: np.ndarray,
    nivel: float,
    series: pd.DataFrame,
    repeticiones: int = 2000,
    semilla: int = 0,
) -> tuple[float, float]:
    """Intervalo de confianza al 95 % de la perdida, remuestreando series.

    Se remuestrean series completas y no filas sueltas, porque las semanas de una
    misma serie no son independientes entre si.
    """
    generador = np.random.default_rng(semilla)
    indices_por_serie = series.groupby(CLAVE_SERIE, observed=True).indices
    claves = list(indices_por_serie)

    muestras = []
    for _ in range(repeticiones):
        elegidas = generador.choice(len(claves), size=len(claves), replace=True)
        indices = np.concatenate([indices_por_serie[claves[i]] for i in elegidas])
        muestras.append(metrics.pinball(real[indices], prediccion[indices], nivel))
    return float(np.percentile(muestras, 2.5)), float(np.percentile(muestras, 97.5))


def validacion_avance(
    familias: dict[str, type[modelos.ModeloCuantil]],
    marco: pd.DataFrame,
    particion: splits.Particion,
    niveles: tuple[float, ...],
) -> pd.DataFrame:
    """Evalua las familias en cada pliegue de ventana expansiva."""
    filas = []
    for ajuste, validacion in splits.pliegues_expansivos(particion.entrenamiento):
        entrena = splits.separar(marco, ajuste)
        valida = splits.separar(marco, validacion)
        tabla, _ = comparar(familias, entrena, valida, niveles)
        filas.append(tabla.assign(pliegue=validacion))
    return pd.concat(filas, ignore_index=True)


def coste_politica(
    clase: type[modelos.ModeloCuantil],
    entrenamiento: pd.DataFrame,
    evaluacion_: pd.DataFrame,
    catalogo: pd.DataFrame,
    escenario,
    parametros: dict | None = None,
) -> dict[str, float]:
    """Coste en pesos de aplicar la politica de pedido con una familia.

    Para cada fila se toma el nivel de servicio que le corresponde a su producto,
    se pide hasta ese nivel y se enfrenta a la demanda real. El coste es el
    margen perdido por quedarse corto mas el coste del sobrante.

    Se compara el nivel objetivo y no la cantidad pedida, porque el stock inicial
    es comun a todos los modelos y se cancela en la comparacion.

    Pertenece al paso de simulacion de la politica y no al de seleccion de
    familia: usarla para elegir modelo obligaria a evaluarla sobre las semanas
    de prueba, que deben quedar intactas hasta el final. Aqui queda disponible
    para ese paso posterior, donde se comparan cuatro politicas y se atribuye el
    ahorro entre el efecto de la regla y el del modelo.
    """
    from caso_a import costes as costes_mod

    nivel_de = costes_mod.politica_por_producto(catalogo, escenario)
    faltante = dict(zip(catalogo["id_producto"], costes_mod.coste_faltante(catalogo)))
    sobrante = dict(
        zip(catalogo["id_producto"], costes_mod.coste_sobrante(catalogo, escenario.fraccion_merma))
    )
    niveles = sorted(set(nivel_de.tolist()))

    predicciones = {
        nivel: clase(nivel, **(parametros or {})).ajustar(entrenamiento).predecir(evaluacion_)
        for nivel in niveles
    }
    productos = evaluacion_["id_producto"].to_numpy()
    objetivo = np.maximum(
        np.array([predicciones[nivel_de[p]][i] for i, p in enumerate(productos)]), 0.0
    )

    demanda = evaluacion_[OBJETIVO].to_numpy(float)
    coste_falta = np.array([faltante[p] for p in productos])
    coste_sobra = np.array([sobrante[p] for p in productos])

    perdidas = np.where(demanda > objetivo, (demanda - objetivo) * coste_falta, 0.0)
    merma = np.where(demanda <= objetivo, (objetivo - demanda) * coste_sobra, 0.0)

    return {
        "ventas_perdidas": float(perdidas.sum()),
        "merma": float(merma.sum()),
        "coste_total": float(perdidas.sum() + merma.sum()),
        "tasa_quiebre": float((demanda > objetivo).mean()),
        "nivel_medio": float(objetivo.mean()),
    }
