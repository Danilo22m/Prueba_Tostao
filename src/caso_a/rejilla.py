"""Entrenamiento de la rejilla de niveles con la familia elegida.

Cada nivel de servicio necesita su propio modelo: un estimador solo sabe
devolver el cuantil para el que fue entrenado. La rejilla salio del paso de
costes y contiene los niveles que piden los ocho productos en los tres
escenarios, mas la mediana y un nivel alto para auditar la incertidumbre.

Como los niveles se ajustan por separado, nada garantiza que salgan ordenados
en todas las series. Un cuantil 0,90 por debajo del 0,50 es imposible en la
realidad, asi que se comprueba y se corrige.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from caso_a import modelos

CLAVE_SERIE = ["id_tienda", "id_producto"]
OBJETIVO = "unidades_vendidas"


def entrenar(
    clase: type[modelos.ModeloCuantil],
    entrenamiento: pd.DataFrame,
    niveles: list[float],
    parametros: dict | None = None,
) -> dict[float, modelos.ModeloCuantil]:
    """Ajusta un modelo por cada nivel de la rejilla.

    Args:
        clase: Familia elegida en el paso de seleccion.
        entrenamiento: Filas con las que aprende, sin tocar la prueba.
        niveles: Niveles de servicio a estimar.
        parametros: Hiperparametros comunes a todos los niveles. Se reutilizan
            los del nivel de operacion en lugar de reoptimizar en cada uno:
            con 960 filas, reoptimizar diecisiete veces invitaria a ajustarse
            al ruido de la validacion.

    Returns:
        Diccionario de nivel a modelo ajustado.
    """
    return {
        nivel: clase(nivel, **(parametros or {})).ajustar(entrenamiento)
        for nivel in niveles
    }


def predecir(
    ajustados: dict[float, modelos.ModeloCuantil], datos: pd.DataFrame
) -> pd.DataFrame:
    """Devuelve el abanico completo: una columna por nivel.

    Conserva las claves de serie, la semana y la demanda observada, para que la
    tabla sea autosuficiente al auditarla.
    """
    salida = datos[CLAVE_SERIE + ["semana", OBJETIVO]].reset_index(drop=True).copy()
    for nivel, modelo in sorted(ajustados.items()):
        salida[f"q{nivel:.2f}"] = modelo.predecir(datos)
    return salida


def columnas_nivel(abanico: pd.DataFrame) -> list[str]:
    """Columnas de cuantil presentes, ordenadas de menor a mayor nivel."""
    return sorted(c for c in abanico.columns if c.startswith("q0") or c.startswith("q1"))


def verificar_monotonia(abanico: pd.DataFrame) -> pd.DataFrame:
    """Localiza las filas donde un nivel superior queda por debajo de otro.

    Returns:
        Tabla con el numero de cruces por par consecutivo de niveles y la
        magnitud maxima del cruce, en unidades.
    """
    columnas = columnas_nivel(abanico)
    filas = []
    for bajo, alto in zip(columnas[:-1], columnas[1:]):
        diferencia = abanico[alto] - abanico[bajo]
        cruces = int((diferencia < 0).sum())
        filas.append({
            "par": f"{bajo} -> {alto}",
            "cruces": cruces,
            "pct_filas": 100 * cruces / len(abanico),
            "cruce_maximo": float(-diferencia.min()) if cruces else 0.0,
        })
    return pd.DataFrame(filas)


def ordenar_niveles(abanico: pd.DataFrame) -> pd.DataFrame:
    """Fuerza que los niveles crezcan, ordenando los valores de cada fila.

    Es la correccion habitual del cruce de cuantiles: reordenar no cambia el
    conjunto de valores estimados, solo su asignacion a niveles, y garantiza
    que pedir con mas proteccion nunca devuelva menos unidades.
    """
    columnas = columnas_nivel(abanico)
    salida = abanico.copy()
    salida[columnas] = np.sort(abanico[columnas].to_numpy(), axis=1)
    return salida


def cobertura_por_nivel(abanico: pd.DataFrame) -> pd.DataFrame:
    """Proporcion de observaciones que quedan por debajo de cada nivel.

    Si el nivel cumple lo que promete, la cobertura empirica se parece al propio
    nivel. Una cobertura sistematicamente menor significa que el modelo se queda
    corto y el nivel de servicio prometido a negocio seria falso.
    """
    demanda = abanico[OBJETIVO].to_numpy(float)
    filas = []
    for columna in columnas_nivel(abanico):
        nivel = float(columna[1:])
        empirica = float((demanda <= abanico[columna].to_numpy(float)).mean())
        filas.append({
            "nivel": nivel,
            "cobertura": empirica,
            "desvio": empirica - nivel,
            "media_unidades": float(abanico[columna].mean()),
        })
    return pd.DataFrame(filas)


def entrenar_calibrado(
    clase: type[modelos.ModeloCuantil],
    marco: pd.DataFrame,
    particion,
    niveles: list[float],
    parametros: dict | None = None,
) -> tuple[dict[float, modelos.ModeloCuantil], dict]:
    """Entrena la rejilla y calcula su correccion conformal.

    Es el punto unico desde el que el resto del pipeline obtiene el modelo. La
    calibracion se aplica aqui, antes de que nadie use las predicciones, porque
    es una correccion al modelo y no un analisis posterior.

    Los ajustes se calculan con predicciones fuera de pliegue, asi que ninguna
    semana de prueba interviene.

    Returns:
        Los modelos ajustados y el diccionario de correcciones por nivel.
    """
    from caso_a import calibracion

    entrenamiento = splits_separar(marco, particion.entrenamiento)
    ajustados = entrenar(clase, entrenamiento, niveles, parametros)
    fuera = calibracion.predicciones_fuera_de_pliegue(
        clase, marco, particion, niveles, parametros
    )
    return ajustados, calibracion.calcular_ajustes(fuera)


def predecir_calibrado(
    ajustados: dict[float, modelos.ModeloCuantil],
    correcciones: dict,
    datos: pd.DataFrame,
) -> pd.DataFrame:
    """Devuelve el abanico calibrado y ordenado, listo para decidir."""
    from caso_a import calibracion

    bruto = predecir(ajustados, datos)
    return ordenar_niveles(calibracion.aplicar(bruto, correcciones))


def splits_separar(marco: pd.DataFrame, semanas):
    """Atajo local para no crear una dependencia circular con splits."""
    objetivo = (semanas,) if isinstance(semanas, int) else semanas
    return marco[marco["semana"].isin(objetivo)].copy()
