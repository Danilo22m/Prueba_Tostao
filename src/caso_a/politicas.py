"""Simulacion de politicas de pedido y atribucion del ahorro.

Una politica es una regla para decidir cuanto tener disponible. Se comparan
cinco, organizadas como un diseno factorial de dos por dos mas una referencia:

                          regla: pedir el centro   regla: pedir el nivel
    pronostico ingenuo            P1                       P3
    pronostico del modelo         P2                       P4

y aparte P0, repetir lo de la semana anterior, que aproxima la practica actual.

Ese diseno es lo que permite separar cuanto del ahorro viene de cambiar la regla
de pedido y cuanto de predecir mejor. Comparar solo P0 contra P4 daria una cifra
grande sin saber a que atribuirla, y con una asimetria de costes como la de este
catalogo, casi todo el merito seria de la regla.

La comparacion se hace sobre el nivel disponible y no sobre la cantidad pedida,
porque el stock inicial es comun a todas las politicas y se cancela.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from caso_a import costes

CLAVE_SERIE = ["id_tienda", "id_producto"]
OBJETIVO = "unidades_vendidas"


@dataclass(frozen=True)
class Resultado:
    """Coste y comportamiento operativo de una politica."""

    nombre: str
    coste_total: float
    ventas_perdidas: float
    merma: float
    unidades_faltantes: float
    unidades_sobrantes: float
    tasa_quiebre: float
    nivel_servicio_real: float
    nivel_medio: float

    def como_fila(self) -> dict[str, float | str]:
        return {
            "politica": self.nombre,
            "coste_total": self.coste_total,
            "ventas_perdidas": self.ventas_perdidas,
            "merma": self.merma,
            "u_faltantes": self.unidades_faltantes,
            "u_sobrantes": self.unidades_sobrantes,
            "tasa_quiebre": self.tasa_quiebre,
            "servicio_real": self.nivel_servicio_real,
            "nivel_medio": self.nivel_medio,
        }


def coste_de(
    demanda: np.ndarray,
    disponible: np.ndarray,
    coste_faltante: np.ndarray,
    coste_sobrante: np.ndarray,
    nombre: str,
) -> Resultado:
    """Coste realizado de tener ``disponible`` frente a la demanda observada.

    Si falta producto se pierde el margen de cada unidad no servida. Si sobra,
    se paga el coste del sobrante de cada unidad que queda.
    """
    disponible = np.maximum(disponible, 0.0)
    faltan = np.maximum(demanda - disponible, 0.0)
    sobran = np.maximum(disponible - demanda, 0.0)
    perdidas = float((faltan * coste_faltante).sum())
    desperdicio = float((sobran * coste_sobrante).sum())

    return Resultado(
        nombre=nombre,
        coste_total=perdidas + desperdicio,
        ventas_perdidas=perdidas,
        merma=desperdicio,
        unidades_faltantes=float(faltan.sum()),
        unidades_sobrantes=float(sobran.sum()),
        tasa_quiebre=float((faltan > 0).mean()),
        nivel_servicio_real=float(1 - faltan.sum() / demanda.sum()),
        nivel_medio=float(disponible.mean()),
    )


def simular(
    marco: pd.DataFrame,
    politicas: dict[str, np.ndarray],
    catalogo: pd.DataFrame,
    escenario: costes.Escenario,
) -> pd.DataFrame:
    """Evalua todas las politicas sobre las mismas filas y los mismos costes."""
    faltante = dict(zip(catalogo["id_producto"], costes.coste_faltante(catalogo)))
    sobrante = dict(
        zip(catalogo["id_producto"], costes.coste_sobrante(catalogo, escenario.fraccion_merma))
    )
    productos = marco["id_producto"].to_numpy()
    cf = np.array([faltante[p] for p in productos], dtype=float)
    cs = np.array([sobrante[p] for p in productos], dtype=float)
    demanda = marco[OBJETIVO].to_numpy(float)

    filas = [coste_de(demanda, valores, cf, cs, nombre).como_fila()
             for nombre, valores in politicas.items()]
    tabla = pd.DataFrame(filas)
    tabla["ahorro_vs_peor"] = tabla["coste_total"].max() - tabla["coste_total"]
    return tabla.sort_values("coste_total").reset_index(drop=True)


def atribuir(tabla: pd.DataFrame, claves: dict[str, str]) -> pd.DataFrame:
    """Descompone el ahorro entre el efecto de la regla y el del modelo.

    Args:
        tabla: Salida de :func:`simular`, indexable por nombre de politica.
        claves: Nombres de las cuatro celdas del diseno factorial, con las
            claves ``ingenuo_centro``, ``modelo_centro``, ``ingenuo_nivel`` y
            ``modelo_nivel``.

    Returns:
        Tabla con el efecto de cada factor, su interaccion y el total.
    """
    coste = tabla.set_index("politica")["coste_total"]
    a = coste[claves["ingenuo_centro"]]
    b = coste[claves["modelo_centro"]]
    c = coste[claves["ingenuo_nivel"]]
    d = coste[claves["modelo_nivel"]]

    efecto_modelo = a - b
    efecto_regla = a - c
    total = a - d
    interaccion = total - efecto_modelo - efecto_regla

    filas = [
        {"componente": "efecto del modelo", "ahorro": efecto_modelo,
         "explicacion": "predecir mejor, manteniendo la regla de pedir el centro"},
        {"componente": "efecto de la regla", "ahorro": efecto_regla,
         "explicacion": "pedir el nivel de servicio, manteniendo el pronostico ingenuo"},
        {"componente": "interaccion", "ahorro": interaccion,
         "explicacion": "lo que aporta combinarlos, mas alla de la suma"},
        {"componente": "TOTAL", "ahorro": total,
         "explicacion": "del punto de partida a la propuesta completa"},
    ]
    salida = pd.DataFrame(filas)
    salida["pct_del_total"] = 100 * salida["ahorro"] / total if total else np.nan
    return salida


def banda_ahorro(
    marco: pd.DataFrame,
    disponible_uno: np.ndarray,
    disponible_otro: np.ndarray,
    catalogo: pd.DataFrame,
    escenario: costes.Escenario,
    repeticiones: int = 2000,
    semilla: int = 0,
) -> tuple[float, float]:
    """Intervalo de confianza al 95 % del ahorro, remuestreando series.

    Se remuestrean series completas y no filas sueltas, porque las semanas de
    una misma serie no son independientes entre si.
    """
    faltante = dict(zip(catalogo["id_producto"], costes.coste_faltante(catalogo)))
    sobrante = dict(
        zip(catalogo["id_producto"], costes.coste_sobrante(catalogo, escenario.fraccion_merma))
    )
    productos = marco["id_producto"].to_numpy()
    cf = np.array([faltante[p] for p in productos], dtype=float)
    cs = np.array([sobrante[p] for p in productos], dtype=float)
    demanda = marco[OBJETIVO].to_numpy(float)

    indices_por_serie = marco.reset_index(drop=True).groupby(CLAVE_SERIE, observed=True).indices
    claves = list(indices_por_serie)
    generador = np.random.default_rng(semilla)

    diferencias = []
    for _ in range(repeticiones):
        elegidas = generador.choice(len(claves), size=len(claves), replace=True)
        idx = np.concatenate([indices_por_serie[claves[i]] for i in elegidas])
        uno = coste_de(demanda[idx], disponible_uno[idx], cf[idx], cs[idx], "a").coste_total
        otro = coste_de(demanda[idx], disponible_otro[idx], cf[idx], cs[idx], "b").coste_total
        diferencias.append(uno - otro)
    return float(np.percentile(diferencias, 2.5)), float(np.percentile(diferencias, 97.5))


def intercambio_de_unidades(
    marco: pd.DataFrame,
    politicas_: dict[str, np.ndarray],
    referencia: str,
    propuesta: str,
) -> pd.DataFrame:
    """Cuantas unidades de faltante se cambian por unidades de sobrante.

    Es la forma mas directa de explicar por que la politica ahorra: no reduce el
    error, lo desplaza de un lado al otro. Y compensa porque los dos lados no
    cuestan lo mismo.
    """
    demanda = marco[OBJETIVO].to_numpy(float)
    filas = []
    for nombre in (referencia, propuesta):
        disponible = np.maximum(politicas_[nombre], 0.0)
        filas.append({
            "politica": nombre,
            "u_faltantes": float(np.maximum(demanda - disponible, 0.0).sum()),
            "u_sobrantes": float(np.maximum(disponible - demanda, 0.0).sum()),
        })
    tabla = pd.DataFrame(filas)
    numericas = ["u_faltantes", "u_sobrantes"]
    cambio = tabla.loc[1, numericas] - tabla.loc[0, numericas]
    tabla.loc[len(tabla)] = {"politica": "cambio", **cambio.to_dict()}
    return tabla


def detalle_de_serie(
    marco: pd.DataFrame,
    politicas_: dict[str, np.ndarray],
    catalogo: pd.DataFrame,
    escenario,
    clave: tuple[str, str],
) -> pd.DataFrame:
    """Desglose semana a semana de una serie concreta, para ilustrar el calculo.

    Permite enseñar en una tabla pequena lo que ocurre en las 480 decisiones.
    """
    from caso_a import costes as costes_mod

    faltante = dict(zip(catalogo["id_producto"], costes_mod.coste_faltante(catalogo)))
    sobrante = dict(
        zip(catalogo["id_producto"], costes_mod.coste_sobrante(catalogo, escenario.fraccion_merma))
    )
    seleccion = (
        (marco["id_tienda"] == clave[0]) & (marco["id_producto"] == clave[1])
    ).to_numpy()
    sub = marco[seleccion].reset_index(drop=True)
    coste_falta, coste_sobra = faltante[clave[1]], sobrante[clave[1]]

    filas = []
    for nombre, valores in politicas_.items():
        propios = np.maximum(valores[seleccion], 0.0)
        for indice, fila in sub.iterrows():
            demanda = float(fila[OBJETIVO])
            disponible = float(propios[indice])
            falta = max(demanda - disponible, 0.0)
            sobra = max(disponible - demanda, 0.0)
            filas.append({
                "politica": nombre,
                "semana": int(fila["semana"]),
                "demanda": demanda,
                "disponible": disponible,
                "falta": falta,
                "sobra": sobra,
                "coste": falta * coste_falta + sobra * coste_sobra,
            })
    return pd.DataFrame(filas)
