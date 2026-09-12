"""Construccion de las variables predictoras del panel semanal.

Regla que gobierna el modulo: para predecir la semana t, toda variable se
calcula exclusivamente con informacion de t-1 hacia atras. La funcion
:func:`verificar_sin_fuga` lo comprueba de forma automatica.

El univariado mostro que la autocorrelacion semanal es despreciable, asi que el
rezago de una semana es una senal ruidosa. Las variables que deberian pesar son
las medias moviles, que promedian el ruido, y la pendiente, que mide direccion.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CLAVE_SERIE = ["id_tienda", "id_producto"]
OBJETIVO = "unidades_vendidas"

#: Semanas de historia que consume la variable mas larga. Es el parametro
#: que decide cuantas semanas iniciales se gastan y cuantas filas quedan.
MAX_REZAGO = 4


def _pendiente(valores: np.ndarray) -> float:
    """Pendiente de una recta ajustada por minimos cuadrados."""
    if np.isnan(valores).any() or valores.size < 2:
        return np.nan
    x = np.arange(valores.size, dtype=float)
    return float(np.polyfit(x, valores, 1)[0])


def construir(panel: pd.DataFrame, max_rezago: int = MAX_REZAGO) -> pd.DataFrame:
    """Anade al panel las variables de historia de cada serie.

    Args:
        panel: Panel semanal enriquecido, ordenado o no.
        max_rezago: Semanas de historia que consume la variable mas larga.
            Determina cuantas semanas iniciales quedan sin fila utilizable:
            con un maximo de 4 se pierden las cuatro primeras, con 2 solo dos.

    Returns:
        El panel con las columnas nuevas. Las primeras semanas de cada serie
        llevan valores ausentes, porque no tienen historia suficiente.
    """
    marco = panel.sort_values(CLAVE_SERIE + ["semana"]).copy()
    grupo = marco.groupby(CLAVE_SERIE, observed=True)[OBJETIVO]

    for k in range(1, max_rezago + 1):
        marco[f"rezago_{k}"] = grupo.shift(k)

    # Las ventanas se aplican sobre la serie ya desplazada una semana, para que
    # nunca incluyan el valor que se quiere predecir.
    desplazada = grupo.shift(1)
    claves = [marco["id_tienda"], marco["id_producto"]]
    ventanas = [v for v in range(2, max_rezago + 1)]

    for v in ventanas:
        marco[f"media_{v}"] = (
            desplazada.groupby(claves, observed=True)
            .rolling(v, min_periods=v).mean().reset_index(level=[0, 1], drop=True)
        )
        marco[f"desv_{v}"] = (
            desplazada.groupby(claves, observed=True)
            .rolling(v, min_periods=v).std().reset_index(level=[0, 1], drop=True)
        )

    marco["pendiente"] = (
        desplazada.groupby(claves, observed=True)
        .rolling(max_rezago, min_periods=max_rezago)
        .apply(_pendiente, raw=True)
        .reset_index(level=[0, 1], drop=True)
    )

    # Senales derivadas, referidas siempre a la ventana mas larga disponible.
    larga = max(ventanas) if ventanas else max_rezago
    marco["razon_ultima"] = marco["rezago_1"] / marco[f"media_{larga}"]
    marco["cv_reciente"] = marco[f"desv_{larga}"] / marco[f"media_{larga}"]

    return marco


def verificar_sin_fuga(panel: pd.DataFrame, semana_corte: int,
                       max_rezago: int = MAX_REZAGO) -> None:
    """Comprueba que ninguna variable usa informacion del futuro.

    Reconstruye las variables ocultando todo lo posterior al corte y exige que
    las filas hasta el corte salgan identicas. Si alguna variable mirara hacia
    adelante, los valores cambiarian.

    Raises:
        AssertionError: Si alguna columna difiere.
    """
    completo = construir(panel, max_rezago)
    recortado = construir(panel[panel["semana"] <= semana_corte], max_rezago)

    columnas = [c for c in completo.columns if c not in panel.columns]
    izq = completo[completo["semana"] <= semana_corte].sort_values(CLAVE_SERIE + ["semana"])
    der = recortado.sort_values(CLAVE_SERIE + ["semana"])

    for columna in columnas:
        a = izq[columna].to_numpy(dtype=float)
        b = der[columna].to_numpy(dtype=float)
        if not np.allclose(a, b, equal_nan=True):
            raise AssertionError(f"La variable {columna!r} usa informacion posterior al corte.")


def columnas_predictoras(marco: pd.DataFrame) -> list[str]:
    """Lista de variables que entran al modelo.

    Quedan fuera, con motivo documentado en la memoria: el objetivo, las claves,
    la semana, los atributos economicos del producto (redundantes con su
    identidad y reservados para la capa de costes) y la ciudad (sin aporte una
    vez conocida la superficie).
    """
    excluidas = {
        OBJETIVO, "semana", "id_tienda", "id_producto", "nombre",
        "costo_unitario", "precio_venta", "costo_almacenamiento_semanal", "ciudad",
    }
    return [c for c in marco.columns if c not in excluidas]


def extender_al_futuro(panel: pd.DataFrame, semana: int | None = None) -> pd.DataFrame:
    """Anade al panel una fila por serie para la semana que se va a predecir.

    Para pedir la semana siguiente hace falta una fila con sus variables, y esa
    fila no existe en el panel: la semana todavia no ha ocurrido. Se crea aqui
    heredando los atributos fijos de tienda y producto de la ultima semana
    observada, que son constantes en el tiempo, y dejando la demanda ausente.

    Al pasar el resultado por :func:`construir`, la fila nueva recibe sus
    rezagos y medias moviles de las semanas reales que la preceden, con la misma
    regla que el resto del panel. No se inventa ningun dato de demanda.

    Args:
        panel: Panel semanal enriquecido, con todas las semanas observadas.
        semana: Semana a anadir. Solo se admite la inmediatamente siguiente a la
            ultima observada; el argumento existe para que quien llama declare
            que semana cree que esta pidiendo. ``None`` la deduce.

    Raises:
        ValueError: Si la semana pedida no es la siguiente a la ultima
            observada. Saltarse una semana dejaria los rezagos desplazados.
    """
    ultima = int(panel["semana"].max())
    destino = ultima + 1 if semana is None else int(semana)
    if destino != ultima + 1:
        raise ValueError(
            f"Solo se puede extender a la semana {ultima + 1}, que es la siguiente a "
            f"la ultima observada, y se ha pedido la {destino}. Con un salto, los "
            f"rezagos apuntarian a semanas equivocadas."
        )

    futura = panel[panel["semana"] == ultima].copy()
    futura["semana"] = destino
    futura[OBJETIVO] = np.nan
    ampliado = pd.concat([panel, futura], ignore_index=True)
    return ampliado.sort_values(CLAVE_SERIE + ["semana"], ignore_index=True)


def verificar_extension(panel: pd.DataFrame, max_rezago: int = MAX_REZAGO) -> None:
    """Comprueba que anadir la fila futura no altera ninguna variable del pasado.

    Es el mismo argumento que :func:`verificar_sin_fuga`, en la otra direccion:
    alli se comprueba que las variables no miran hacia adelante, aqui que
    ampliar el panel por el final no cambia nada de lo que ya estaba calculado.
    Si una ventana estuviera mal centrada, los valores se moverian.

    Raises:
        AssertionError: Si alguna columna difiere en las semanas observadas.
    """
    ultima = int(panel["semana"].max())
    sin_futuro = construir(panel, max_rezago)
    con_futuro = construir(extender_al_futuro(panel), max_rezago)

    columnas = [c for c in sin_futuro.columns if c not in panel.columns]
    orden = CLAVE_SERIE + ["semana"]
    izq = sin_futuro.sort_values(orden)
    der = con_futuro[con_futuro["semana"] <= ultima].sort_values(orden)

    if len(izq) != len(der):
        raise AssertionError(
            f"La extension cambio el numero de filas observadas: {len(izq)} frente a {len(der)}."
        )
    for columna in columnas:
        a = izq[columna].to_numpy(dtype=float)
        b = der[columna].to_numpy(dtype=float)
        if not np.allclose(a, b, equal_nan=True):
            raise AssertionError(
                f"Anadir la semana futura altero la variable {columna!r} del pasado."
            )
