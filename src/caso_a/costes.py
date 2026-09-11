"""Parametros de coste y niveles de servicio por producto.

Este modulo es el puente entre el negocio y el modelo, y se ejecuta antes de
entrenar nada: los costes deciden que niveles de servicio hay que estimar, y por
tanto cuantos modelos se entrenan y cuales.

El nivel de servicio optimo sale de igualar lo que se espera ganar al anadir una
unidad con lo que se espera perder:

    p * faltante = (1 - p) * sobrante        ->   p = sobrante / (faltante + sobrante)

donde p es la probabilidad de quedarse corto que se acepta. El nivel de servicio
es su complemento, faltante / (faltante + sobrante). En ninguna de las dos
expresiones aparece la demanda: el nivel depende solo de dos precios.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

#: Semanas del ano, para repartir una tasa anual de capital.
SEMANAS_ANO = 52

#: Nivel maximo que se entrena. Un nivel de 1 pedira siempre el maximo
#: imaginable, y ademas el cuantil 1 no es estimable a partir de una muestra
#: finita. Se acota para que el redondeo nunca lo alcance.
NIVEL_MAXIMO = 0.99

#: Nivel minimo, por simetria.
NIVEL_MINIMO = 0.50


@dataclass(frozen=True)
class Escenario:
    """Supuesto sobre que ocurre con el producto que sobra.

    Attributes:
        nombre: Etiqueta corta para informes y graficos.
        fraccion_merma: Proporcion del sobrante que se descarta. Cero significa
            que todo se vende mas adelante; uno, que todo se tira.
        descripcion: Justificacion del supuesto, para la memoria tecnica.
    """

    nombre: str
    fraccion_merma: float
    descripcion: str


#: Escenarios que se presentan. El del enunciado solo contempla almacenamiento.
ESCENARIOS = (
    Escenario(
        "sin merma",
        0.0,
        "El sobrante se conserva y se vende la semana siguiente. Solo se paga "
        "almacenamiento. Es el supuesto implicito del enunciado.",
    ),
    Escenario(
        "merma parcial",
        0.5,
        "La mitad del sobrante se recupera. Escenario intermedio, util para "
        "acotar la sensibilidad del resultado.",
    ),
    Escenario(
        "con merma",
        1.0,
        "El sobrante se descarta al cierre. Es lo habitual en cafeteria y "
        "bolleria, donde el producto no se conserva de un dia para otro.",
    ),
)


def _acotar(nivel: float) -> float:
    """Recorta un nivel al rango entrenable.

    El redondeo puede llevar un nivel de 0,995 hasta 1, y pedir el cuantil 1
    equivale a pedir sin limite. Se acota por arriba y, por simetria, por abajo.
    """
    return min(max(nivel, NIVEL_MINIMO), NIVEL_MAXIMO)


def coste_faltante(catalogo: pd.DataFrame) -> pd.Series:
    """Margen que se pierde por cada unidad que falta."""
    return catalogo["precio_venta"] - catalogo["costo_unitario"]


def coste_sobrante(
    catalogo: pd.DataFrame, fraccion_merma: float, tasa_capital: float = 0.0
) -> pd.Series:
    """Coste de cada unidad que sobra.

    Args:
        catalogo: Maestro de productos.
        fraccion_merma: Proporcion del sobrante que se descarta, entre 0 y 1.
        tasa_capital: Tasa anual de coste del capital inmovilizado. Se reparte
            entre las semanas del ano y se aplica sobre el coste unitario.

    Raises:
        ValueError: Si la fraccion cae fuera de [0, 1].
    """
    if not 0.0 <= fraccion_merma <= 1.0:
        raise ValueError(f"La fraccion de merma debe estar entre 0 y 1, no {fraccion_merma}.")
    capital = catalogo["costo_unitario"] * tasa_capital / SEMANAS_ANO
    return fraccion_merma * catalogo["costo_unitario"] + catalogo["costo_almacenamiento_semanal"] + capital


def nivel_servicio(
    catalogo: pd.DataFrame, fraccion_merma: float, tasa_capital: float = 0.0
) -> pd.Series:
    """Proporcion de semanas que conviene cubrir, por producto."""
    faltante = coste_faltante(catalogo)
    sobrante = coste_sobrante(catalogo, fraccion_merma, tasa_capital)
    return faltante / (faltante + sobrante)


def tabla_escenario(
    catalogo: pd.DataFrame, escenario: Escenario, tasa_capital: float = 0.0
) -> pd.DataFrame:
    """Ficha completa de costes y nivel de servicio bajo un escenario."""
    salida = catalogo[["id_producto", "nombre", "categoria"]].copy()
    salida["faltante"] = coste_faltante(catalogo)
    salida["sobrante"] = coste_sobrante(catalogo, escenario.fraccion_merma, tasa_capital)
    salida["razon"] = salida["faltante"] / salida["sobrante"]
    salida["nivel"] = nivel_servicio(catalogo, escenario.fraccion_merma, tasa_capital)
    salida["prob_quiebre"] = 1 - salida["nivel"]
    return salida.sort_values("nivel", ascending=False).reset_index(drop=True)


def sensibilidad(
    catalogo: pd.DataFrame, fracciones: np.ndarray, tasa_capital: float = 0.0
) -> pd.DataFrame:
    """Nivel de servicio de cada producto al variar la merma supuesta.

    Convierte la discusion con negocio de una pregunta binaria, si se tira o no,
    en una pregunta cuantitativa: que proporcion se tira.
    """
    filas = []
    for fraccion in fracciones:
        niveles = nivel_servicio(catalogo, float(fraccion), tasa_capital)
        for nombre, nivel in zip(catalogo["nombre"], niveles):
            filas.append({"fraccion_merma": float(fraccion), "nombre": nombre, "nivel": float(nivel)})
    return pd.DataFrame(filas)


def rejilla_niveles(
    catalogo: pd.DataFrame,
    escenarios: tuple[Escenario, ...] = ESCENARIOS,
    extras: tuple[float, ...] = (0.5, 0.9),
    decimales: int = 2,
    tasa_capital: float = 0.0,
) -> list[float]:
    """Lista de niveles de servicio que hay que entrenar.

    Reune los niveles que piden los costes en todos los escenarios, redondeados,
    y anade los auxiliares: la mediana, que es el pronostico que pide negocio, y
    un nivel alto para auditar la incertidumbre.

    Returns:
        Niveles ordenados y sin repetir.
    """
    niveles: set[float] = set(extras)
    for escenario in escenarios:
        for nivel in nivel_servicio(catalogo, escenario.fraccion_merma, tasa_capital):
            niveles.add(_acotar(round(float(nivel), decimales)))
    return sorted(niveles)


def politica_por_producto(
    catalogo: pd.DataFrame, escenario: Escenario, decimales: int = 2, tasa_capital: float = 0.0
) -> pd.Series:
    """Nivel de la rejilla que le corresponde a cada producto.

    Es la tabla de consulta que usa el optimizador: dado un SKU, que modelo de
    cuantil hay que preguntar.
    """
    niveles = nivel_servicio(catalogo, escenario.fraccion_merma, tasa_capital).round(decimales)
    acotados = [_acotar(float(n)) for n in niveles]
    return pd.Series(acotados, index=catalogo["id_producto"].to_numpy(), name="nivel")


def tabla_politica(
    catalogo: pd.DataFrame,
    escenarios: tuple[Escenario, ...] = ESCENARIOS,
    decimales: int = 2,
    tasa_capital: float = 0.0,
) -> pd.DataFrame:
    """Tabla de decision: una fila por producto y escenario.

    Es el artefacto que consulta el optimizador para saber que modelo de cuantil
    preguntar ante cada SKU, y el que se entrega a negocio para que audite de
    donde sale cada nivel.
    """
    filas = []
    for escenario in escenarios:
        tabla = tabla_escenario(catalogo, escenario, tasa_capital)
        tabla = tabla.assign(
            escenario=escenario.nombre,
            fraccion_merma=escenario.fraccion_merma,
            nivel_rejilla=[_acotar(round(float(n), decimales)) for n in tabla["nivel"]],
        )
        filas.append(tabla)
    columnas = [
        "escenario", "fraccion_merma", "id_producto", "nombre", "categoria",
        "faltante", "sobrante", "razon", "nivel", "nivel_rejilla", "prob_quiebre",
    ]
    return pd.concat(filas, ignore_index=True)[columnas]


def guardar_parametros(
    catalogo: pd.DataFrame,
    destino: Path,
    escenarios: tuple[Escenario, ...] = ESCENARIOS,
    decimales: int = 2,
    tasa_capital: float = 0.0,
) -> dict[str, Path]:
    """Escribe la tabla de politica y la rejilla en formato legible por maquina.

    El codigo posterior no lee estos ficheros: recalcula los niveles llamando a
    las funciones de este modulo, para que no puedan quedarse desfasados. Los
    ficheros existen para auditoria y para entregarselos a negocio.

    Returns:
        Rutas de los ficheros escritos, por clave.
    """
    destino.mkdir(parents=True, exist_ok=True)

    ruta_tabla = destino / "politica_costes.csv"
    tabla_politica(catalogo, escenarios, decimales, tasa_capital).to_csv(
        ruta_tabla, index=False, encoding="utf-8"
    )

    rejilla = rejilla_niveles(catalogo, escenarios, decimales=decimales, tasa_capital=tasa_capital)
    ruta_rejilla = destino / "rejilla_niveles.json"
    contenido = {
        "niveles": rejilla,
        "n_modelos": len(rejilla),
        "nivel_minimo": NIVEL_MINIMO,
        "nivel_maximo": NIVEL_MAXIMO,
        "decimales": decimales,
        "tasa_capital": tasa_capital,
        "escenarios": [
            {"nombre": e.nombre, "fraccion_merma": e.fraccion_merma, "descripcion": e.descripcion}
            for e in escenarios
        ],
    }
    ruta_rejilla.write_text(json.dumps(contenido, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"politica": ruta_tabla, "rejilla": ruta_rejilla}
