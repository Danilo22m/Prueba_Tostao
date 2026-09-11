"""Analisis univariado y estructura temporal de las ventas diarias.

Responde a cuatro preguntas de diseno:

1. Como se reparten los ceros, y si apuntan a demanda censurada.
2. Si existe ciclo intrasemanal, lo que determina si agregar a semana pierde
   informacion o solo elimina ruido.
3. Hasta que rezago llega la senal, lo que fija cuantas variables de historia
   construir mas adelante.
4. Cuanta heterogeneidad hay entre series, lo que justifica un modelo global
   con identidad de serie frente a un modelo por serie.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf, pacf

CLAVE_SERIE = ["id_tienda", "id_producto"]


def distribucion_ceros(ventas: pd.DataFrame) -> pd.DataFrame:
    """Reparto de los dias sin venta entre las series.

    Si los ceros se concentran en pocas series, apuntan a un producto que no
    rota en esa tienda. Si estan repartidos, apuntan a ruido de demanda baja.
    """
    por_serie = (
        ventas.assign(es_cero=ventas["unidades_vendidas"].eq(0))
        .groupby(CLAVE_SERIE, observed=True)["es_cero"]
        .sum()
        .rename("dias_cero")
        .reset_index()
    )
    return por_serie.sort_values("dias_cero", ascending=False)


def patron_dia_semana(ventas: pd.DataFrame) -> pd.DataFrame:
    """Demanda media por dia de la semana, en indice sobre la media general.

    Un indice de 1,20 significa que ese dia vende un 20 por ciento mas que la
    media. Cuanto mas separados esten los indices, mas fuerte es el ciclo
    intrasemanal que la agregacion a semana va a absorber.
    """
    con_dia = ventas.assign(dia=ventas["fecha"].dt.dayofweek)
    media_global = ventas["unidades_vendidas"].mean()
    resumen = (
        con_dia.groupby("dia", observed=True)["unidades_vendidas"]
        .agg(["mean", "std", "count"])
        .rename(columns={"mean": "media", "std": "desv", "count": "n"})
    )
    resumen["indice"] = resumen["media"] / media_global
    nombres = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    resumen.index = [nombres[i] for i in resumen.index]
    return resumen


def autocorrelacion_media(ventas: pd.DataFrame, max_rezago: int = 21) -> pd.DataFrame:
    """Autocorrelacion simple y parcial, promediada sobre las 160 series.

    Se calcula serie a serie y luego se promedia, en lugar de calcularla sobre
    el panel apilado, porque apilar mezclaria el final de una serie con el
    principio de la siguiente.
    """
    acfs, pacfs = [], []
    for _, grupo in ventas.sort_values("fecha").groupby(CLAVE_SERIE, observed=True):
        y = grupo["unidades_vendidas"].to_numpy(dtype=float)
        acfs.append(acf(y, nlags=max_rezago, fft=False))
        pacfs.append(pacf(y, nlags=max_rezago, method="ywm"))

    media_acf = np.vstack(acfs).mean(axis=0)
    media_pacf = np.vstack(pacfs).mean(axis=0)
    # Banda de significacion aproximada para una serie de longitud n.
    n = ventas.groupby(CLAVE_SERIE, observed=True).size().iloc[0]
    banda = 1.96 / np.sqrt(n)

    return pd.DataFrame(
        {
            "rezago": range(max_rezago + 1),
            "acf": media_acf,
            "pacf": media_pacf,
            "significativo": np.abs(media_acf) > banda,
        }
    ).set_index("rezago")


def perfil_series(ventas: pd.DataFrame) -> pd.DataFrame:
    """Estadisticos basicos de cada una de las 160 series."""
    agrupado = ventas.groupby(CLAVE_SERIE, observed=True)["unidades_vendidas"]
    perfil = agrupado.agg(["mean", "std", "min", "max"]).rename(
        columns={"mean": "media", "std": "desv", "min": "min", "max": "max"}
    )
    perfil["cv"] = perfil["desv"] / perfil["media"]
    return perfil.reset_index()


def tendencia_por_serie(ventas: pd.DataFrame) -> pd.DataFrame:
    """Pendiente de una recta ajustada a cada serie, en unidades por dia.

    Sirve para comprobar, sin usar el fichero de tendencias, si las series
    tienen deriva propia y de que magnitud.
    """
    filas = []
    for (tienda, producto), grupo in ventas.sort_values("fecha").groupby(CLAVE_SERIE, observed=True):
        y = grupo["unidades_vendidas"].to_numpy(dtype=float)
        x = np.arange(y.size, dtype=float)
        pendiente = float(np.polyfit(x, y, 1)[0])
        filas.append(
            {
                "id_tienda": tienda,
                "id_producto": producto,
                "pendiente_dia": pendiente,
                "cambio_total": pendiente * (y.size - 1),
                "media": float(y.mean()),
            }
        )
    salida = pd.DataFrame(filas)
    salida["cambio_relativo"] = salida["cambio_total"] / salida["media"]
    return salida
