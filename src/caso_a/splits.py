"""Particion temporal del panel semanal.

El diseno se congela antes de modelar y no se vuelve a tocar. Ajustarlo despues
de ver resultados invalidaria la evaluacion.

Las semanas se deducen del propio panel. No hay ninguna constante con el numero
de semanas: si el panel crece, la particion se recalcula sola.

Reparto:

    primeras semanas   historia que consumen los rezagos, no generan filas
    intermedias        entrenamiento
    ultimas            prueba, intacta hasta el final
    siguiente          prediccion real, sin demanda con la que compararse

Dentro de entrenamiento se valida con ventana expansiva: cada pliegue ajusta con
todas las semanas anteriores y valida con la siguiente.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: Semanas reservadas por defecto para la prueba final.
SEMANAS_PRUEBA = 3

#: Semanas de historia que consume la variable de rezago mas larga.
HISTORIA_MINIMA = 4

#: Semanas minimas de ajuste en el primer pliegue de validacion.
MINIMO_PLIEGUE = 3


@dataclass(frozen=True)
class Particion:
    """Semanas que componen cada parte del diseno.

    Attributes:
        entrenamiento: Semanas con las que aprende el modelo.
        prueba: Semanas reservadas para la evaluacion final.
        prediccion: Semana que se entrega, sin observacion real.
    """

    entrenamiento: tuple[int, ...]
    prueba: tuple[int, ...]
    prediccion: int

    def __str__(self) -> str:
        parte = (
            f"entrenamiento {self.entrenamiento[0]}-{self.entrenamiento[-1]} "
            f"({len(self.entrenamiento)} semanas)"
        )
        if self.prueba:
            parte += f", prueba {self.prueba[0]}-{self.prueba[-1]} ({len(self.prueba)} semanas)"
        else:
            parte += ", sin semanas de prueba"
        return f"{parte}, prediccion semana {self.prediccion}"


def construir(
    ultima_semana: int,
    historia_minima: int = HISTORIA_MINIMA,
    semanas_prueba: int = SEMANAS_PRUEBA,
) -> Particion:
    """Construye la particion a partir de la ultima semana observada.

    Args:
        ultima_semana: Numero de la ultima semana con datos.
        historia_minima: Semanas iniciales que consumen los rezagos.
        semanas_prueba: Semanas finales reservadas para la evaluacion.

    Raises:
        ValueError: Si no quedan semanas de entrenamiento suficientes para
            formar al menos un pliegue de validacion.
    """
    primera_util = historia_minima + 1
    inicio_prueba = ultima_semana - semanas_prueba + 1
    entrenamiento = tuple(range(primera_util, inicio_prueba))
    prueba = tuple(range(inicio_prueba, ultima_semana + 1))

    if len(entrenamiento) <= MINIMO_PLIEGUE:
        raise ValueError(
            f"Con {ultima_semana} semanas, {historia_minima} de historia y "
            f"{semanas_prueba} de prueba solo quedan {len(entrenamiento)} semanas de "
            f"entrenamiento, y hacen falta mas de {MINIMO_PLIEGUE} para validar."
        )
    return Particion(entrenamiento, prueba, ultima_semana + 1)


def desde_panel(
    panel: pd.DataFrame,
    historia_minima: int = HISTORIA_MINIMA,
    semanas_prueba: int = SEMANAS_PRUEBA,
) -> Particion:
    """Deduce la particion del panel, sin suponer cuantas semanas tiene.

    Comprueba ademas que el calendario de semanas sea continuo, porque un hueco
    haria que los rezagos cruzaran periodos sin que nadie se entere.
    """
    return construir(_ultima_semana(panel), historia_minima, semanas_prueba)


def _ultima_semana(panel: pd.DataFrame) -> int:
    """Ultima semana del panel, tras comprobar que el calendario no tiene huecos.

    Un hueco haria que los rezagos cruzaran periodos sin que nadie se entere.
    """
    semanas = sorted(int(s) for s in panel["semana"].unique())
    esperadas = list(range(semanas[0], semanas[-1] + 1))
    if semanas != esperadas:
        faltan = sorted(set(esperadas) - set(semanas))
        raise ValueError(f"El calendario de semanas tiene huecos: faltan {faltan}.")
    return semanas[-1]


def para_entrega(panel: pd.DataFrame, historia_minima: int = HISTORIA_MINIMA) -> Particion:
    """Particion de la entrega final: se entrena con todas las semanas observadas.

    La evaluacion ya ocurrio con la particion de :func:`desde_panel`, y su
    veredicto no cambia. Para el pedido que la tienda ejecuta no se reserva
    nada: cada semana retenida seria una semana de historia desperdiciada, y no
    queda nada que medir con ella.

    La particion resultante no tiene semanas de prueba. Cualquier metrica
    calculada sobre ella estaria medida en los mismos datos del ajuste, asi que
    el codigo que la usa no debe calcular ninguna.
    """
    return construir(_ultima_semana(panel), historia_minima, semanas_prueba=0)


def pliegues_expansivos(
    semanas: tuple[int, ...], minimo_entrenamiento: int = MINIMO_PLIEGUE
) -> list[tuple[tuple[int, ...], int]]:
    """Genera pliegues de validacion con ventana expansiva.

    Returns:
        Lista de pares (semanas de ajuste, semana de validacion).
    """
    return [(semanas[:corte], semanas[corte]) for corte in range(minimo_entrenamiento, len(semanas))]


def separar(marco: pd.DataFrame, semanas: tuple[int, ...] | int) -> pd.DataFrame:
    """Devuelve las filas del panel que caen en las semanas indicadas."""
    objetivo = (semanas,) if isinstance(semanas, int) else semanas
    return marco[marco["semana"].isin(objetivo)].copy()
