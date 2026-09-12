"""Conversion del abanico de cuantiles en una cantidad a pedir.

Es la capa de decision. Toma tres cosas que ya existen y produce el numero que
la tienda ejecuta:

1. El nivel de servicio de cada producto, que sale de sus costes.
2. La cantidad que el modelo asigna a ese nivel para esa serie y semana.
3. El inventario disponible en la estantera.

La logica es deliberadamente corta. Tiene que poder revisarla alguien de
operaciones sin leer el resto del proyecto.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from caso_a import costes, rejilla

CLAVE_SERIE = ["id_tienda", "id_producto"]


@dataclass(frozen=True)
class Restricciones:
    """Limites operativos que se aplican sobre la cantidad teorica.

    Attributes:
        multiplo: Tamano del lote del proveedor. Uno significa unidades sueltas.
        redondeo: ``"cercano"`` minimiza la distorsion; ``"arriba"`` sesga hacia
            proteger la venta, defendible cuando el faltante domina.
        maximo_por_serie: Techo fisico por serie, o ``None`` si no lo hay.
    """

    multiplo: int = 1
    redondeo: str = "cercano"
    maximo_por_serie: int | None = None

    def __post_init__(self) -> None:
        if self.multiplo < 1:
            raise ValueError("El multiplo de lote debe ser al menos 1.")
        if self.redondeo not in {"cercano", "arriba"}:
            raise ValueError(f"Redondeo desconocido: {self.redondeo!r}.")


def _redondear(valores: np.ndarray, restricciones: Restricciones) -> np.ndarray:
    """Lleva las cantidades a unidades enteras y a multiplos de lote."""
    if restricciones.redondeo == "arriba":
        enteros = np.ceil(valores)
    else:
        enteros = np.rint(valores)
    if restricciones.multiplo > 1:
        enteros = np.ceil(enteros / restricciones.multiplo) * restricciones.multiplo
    return enteros


def calcular_pedidos(
    abanico: pd.DataFrame,
    catalogo: pd.DataFrame,
    inventario: pd.DataFrame,
    escenario: costes.Escenario,
    restricciones: Restricciones | None = None,
) -> pd.DataFrame:
    """Construye la tabla de pedidos a partir del abanico de cuantiles.

    Args:
        abanico: Predicciones por nivel, con una columna ``q<nivel>`` por cada uno.
        catalogo: Maestro de productos, del que salen los niveles de servicio.
        inventario: Stock disponible por serie.
        escenario: Supuesto de coste que fija los niveles de servicio.
        restricciones: Limites operativos. Por defecto, unidades sueltas y
            redondeo al entero mas cercano.

    Returns:
        Una fila por serie y semana con todas las columnas intermedias, para que
        cualquiera pueda auditar de donde sale la cantidad final.

    Raises:
        ValueError: Si algun producto pide un nivel que no esta en el abanico, o
            si la union con el inventario pierde o duplica filas.
    """
    restricciones = restricciones or Restricciones()
    niveles = costes.politica_por_producto(catalogo, escenario)
    disponibles = {float(c[1:]) for c in rejilla.columnas_nivel(abanico)}
    faltantes = sorted(set(niveles.to_numpy()) - disponibles)
    if faltantes:
        raise ValueError(f"El abanico no contiene los niveles {faltantes}.")

    filas = len(abanico)
    salida = abanico.merge(
        inventario[CLAVE_SERIE + ["stock_actual"]], on=CLAVE_SERIE,
        how="left", validate="many_to_one",
    )
    if len(salida) != filas:
        raise ValueError("La union con el inventario altero el numero de filas.")
    if salida["stock_actual"].isna().any():
        raise ValueError("Hay series sin stock registrado.")

    salida["nivel_servicio"] = salida["id_producto"].map(niveles)
    salida["pronostico"] = salida["q0.50"].to_numpy(float)
    salida["objetivo_bruto"] = [
        fila[f"q{fila['nivel_servicio']:.2f}"] for _, fila in salida.iterrows()
    ]
    salida["objetivo"] = _redondear(
        np.maximum(salida["objetivo_bruto"].to_numpy(float), 0.0), restricciones
    )
    if restricciones.maximo_por_serie is not None:
        salida["objetivo"] = np.minimum(salida["objetivo"], restricciones.maximo_por_serie)

    salida["pedido"] = np.maximum(
        salida["objetivo"] - salida["stock_actual"].to_numpy(float), 0.0
    )
    salida["colchon"] = salida["objetivo"] - salida["pronostico"]
    salida["cubierto_por_stock"] = salida["pedido"] == 0

    columnas = CLAVE_SERIE + [
        "semana", "pronostico", "nivel_servicio", "objetivo_bruto", "objetivo",
        "stock_actual", "pedido", "colchon", "cubierto_por_stock",
    ]
    if "unidades_vendidas" in salida.columns:
        columnas.append("unidades_vendidas")
    return salida[columnas]


def verificar(pedidos: pd.DataFrame, catalogo: pd.DataFrame,
              escenario: costes.Escenario) -> list[str]:
    """Comprueba las propiedades que la tabla de pedidos debe cumplir siempre.

    Returns:
        Lista de incumplimientos. Vacia si todo esta bien.
    """
    problemas: list[str] = []

    if (pedidos["pedido"] < 0).any():
        problemas.append("hay pedidos negativos")

    if not np.allclose(pedidos["pedido"], np.rint(pedidos["pedido"])):
        problemas.append("hay pedidos que no son enteros")

    sin_stock = pedidos["objetivo"] > pedidos["stock_actual"]
    disponible = pedidos["pedido"] + pedidos["stock_actual"]
    if not (disponible[sin_stock] >= pedidos.loc[sin_stock, "objetivo"] - 1e-9).all():
        problemas.append("el pedido mas el stock no alcanza el objetivo")

    sobra = pedidos["stock_actual"] >= pedidos["objetivo"]
    if not (pedidos.loc[sobra, "pedido"] == 0).all():
        problemas.append("hay pedido positivo donde el stock ya cubre el objetivo")

    esperados = costes.politica_por_producto(catalogo, escenario)
    asignados = pedidos.groupby("id_producto", observed=True)["nivel_servicio"].unique()
    for producto, valores in asignados.items():
        if len(valores) != 1 or not np.isclose(valores[0], esperados[producto]):
            problemas.append(f"{producto} no usa su nivel de servicio, {valores}")

    margen = pedidos["objetivo"] - pedidos["pronostico"]
    if (margen < -0.5).any():
        problemas.append("hay objetivos por debajo del pronostico central")

    return problemas
