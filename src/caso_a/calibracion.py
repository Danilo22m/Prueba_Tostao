"""Recalibracion conformal de los niveles de servicio.

Un modelo puede prometer cubrir el 68 % de las semanas y cubrir solo el 60. Si
eso ocurre, el nivel de servicio que se le ofrece a negocio es una etiqueta
falsa, y el pedido se queda corto justo en las semanas de demanda alta, que son
las que mas margen dejan.

La calibracion conformal corrige esa desviacion sin suponer nada sobre la
distribucion de la demanda. El procedimiento es simple: se mide en datos que el
modelo no vio cuanto se desvia la cobertura, y se desplaza la prediccion lo
justo para cerrar esa brecha.

Se usa la variante de validacion cruzada: en lugar de reservar un trozo del
entrenamiento, que con 960 filas seria caro, se aprovechan las predicciones
fuera de pliegue que ya produce la validacion con ventana expansiva. Asi ningun
dato se desperdicia y la correccion sigue calculandose sobre observaciones que
el modelo no habia visto.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from caso_a import modelos, rejilla, splits

CLAVE_SERIE = ["id_tienda", "id_producto"]
OBJETIVO = "unidades_vendidas"


@dataclass(frozen=True)
class Ajuste:
    """Correccion que se suma a las predicciones de un nivel.

    Attributes:
        nivel: Nivel de servicio al que se aplica.
        desplazamiento: Unidades que se suman. Positivo significa que el modelo
            se quedaba corto y hay que pedir mas.
        cobertura_antes: Proporcion cubierta en los datos de calibracion.
        n_calibracion: Observaciones sobre las que se calculo.
    """

    nivel: float
    desplazamiento: float
    cobertura_antes: float
    n_calibracion: int


def predicciones_fuera_de_pliegue(
    clase: type[modelos.ModeloCuantil],
    marco: pd.DataFrame,
    particion: splits.Particion,
    niveles: list[float],
    parametros: dict | None = None,
) -> pd.DataFrame:
    """Predice cada semana de validacion con un modelo que no la vio.

    Recorre los pliegues de ventana expansiva: ajusta con las semanas previas y
    predice la siguiente. El resultado es un conjunto de predicciones limpias
    sobre datos no vistos, que es lo que la calibracion necesita.
    """
    trozos = []
    for semanas_ajuste, semana_validacion in splits.pliegues_expansivos(particion.entrenamiento):
        entrena = splits.separar(marco, semanas_ajuste)
        valida = splits.separar(marco, semana_validacion)
        ajustados = rejilla.entrenar(clase, entrena, niveles, parametros)
        trozos.append(rejilla.predecir(ajustados, valida))
    return pd.concat(trozos, ignore_index=True)


def calcular_ajustes(fuera_de_pliegue: pd.DataFrame) -> dict[float, Ajuste]:
    """Calcula el desplazamiento que cierra la brecha de cobertura de cada nivel.

    Para un nivel objetivo, se toman los residuales de sus predicciones fuera de
    pliegue y se busca su cuantil en ese mismo nivel. Sumarlo hace que, sobre
    esos datos, la cobertura sea exactamente la prometida.
    """
    demanda = fuera_de_pliegue[OBJETIVO].to_numpy(float)
    ajustes: dict[float, Ajuste] = {}

    for columna in rejilla.columnas_nivel(fuera_de_pliegue):
        nivel = float(columna[1:])
        prediccion = fuera_de_pliegue[columna].to_numpy(float)
        residual = demanda - prediccion
        ajustes[nivel] = Ajuste(
            nivel=nivel,
            desplazamiento=float(np.quantile(residual, nivel)),
            cobertura_antes=float((demanda <= prediccion).mean()),
            n_calibracion=len(demanda),
        )
    return ajustes


def aplicar(abanico: pd.DataFrame, ajustes: dict[float, Ajuste]) -> pd.DataFrame:
    """Suma a cada columna de nivel su desplazamiento de calibracion."""
    salida = abanico.copy()
    for columna in rejilla.columnas_nivel(abanico):
        nivel = float(columna[1:])
        if nivel in ajustes:
            salida[columna] = abanico[columna] + ajustes[nivel].desplazamiento
    return salida


def tabla_ajustes(ajustes: dict[float, Ajuste]) -> pd.DataFrame:
    """Resume los desplazamientos calculados, para el informe."""
    filas = [
        {
            "nivel": a.nivel,
            "cobertura_fuera_pliegue": a.cobertura_antes,
            "desvio": a.cobertura_antes - a.nivel,
            "desplazamiento": a.desplazamiento,
        }
        for a in sorted(ajustes.values(), key=lambda x: x.nivel)
    ]
    return pd.DataFrame(filas)


def comparar_cobertura(
    antes: pd.DataFrame, despues: pd.DataFrame
) -> pd.DataFrame:
    """Cobertura de cada nivel antes y despues de calibrar, sobre los mismos datos."""
    uno = rejilla.cobertura_por_nivel(antes).set_index("nivel")
    otro = rejilla.cobertura_por_nivel(despues).set_index("nivel")
    salida = pd.DataFrame({
        "cobertura_antes": uno["cobertura"],
        "cobertura_despues": otro["cobertura"],
        "desvio_antes": uno["desvio"],
        "desvio_despues": otro["desvio"],
        "unidades_antes": uno["media_unidades"],
        "unidades_despues": otro["media_unidades"],
    }).reset_index()
    salida["mejora"] = salida["desvio_antes"].abs() - salida["desvio_despues"].abs()
    return salida
