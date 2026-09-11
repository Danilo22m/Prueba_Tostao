"""Tablas descriptivas de producto, tienda y patron, para informe y PPT."""

from __future__ import annotations

import numpy as np
import pandas as pd

CLAVE_SERIE = ["id_tienda", "id_producto"]


def tabla_productos(semanal: pd.DataFrame, catalogo: pd.DataFrame) -> pd.DataFrame:
    """Ficha economica de cada SKU con su demanda media observada.

    Incluye el nivel de servicio que dictan los costes en los dos escenarios:
    suponiendo que el sobrante se guarda y suponiendo que se tira.
    """
    demanda = (
        semanal.groupby("id_producto", observed=True)["unidades_vendidas"]
        .agg(["mean", "std", "min", "max"])
        .rename(columns={"mean": "dem_media", "std": "dem_desv", "min": "dem_min", "max": "dem_max"})
    )
    ficha = catalogo.set_index("id_producto").join(demanda)
    ficha["margen"] = ficha["precio_venta"] - ficha["costo_unitario"]
    ficha["margen_pct"] = 100 * ficha["margen"] / ficha["precio_venta"]
    ficha["nivel_sin_merma"] = ficha["margen"] / (ficha["margen"] + ficha["costo_almacenamiento_semanal"])
    sobrante_merma = ficha["costo_unitario"] + ficha["costo_almacenamiento_semanal"]
    ficha["nivel_con_merma"] = ficha["margen"] / (ficha["margen"] + sobrante_merma)
    ficha["cv"] = ficha["dem_desv"] / ficha["dem_media"]
    return ficha.reset_index()


def tabla_tiendas(semanal: pd.DataFrame, tiendas: pd.DataFrame) -> pd.DataFrame:
    """Ficha de cada tienda con su demanda media por SKU y semana."""
    demanda = (
        semanal.groupby("id_tienda", observed=True)["unidades_vendidas"]
        .agg(["mean", "sum"])
        .rename(columns={"mean": "dem_media_sku", "sum": "unidades_total"})
    )
    ficha = tiendas.set_index("id_tienda").join(demanda)
    ficha["unidades_por_m2"] = ficha["unidades_total"] / ficha["tamano_m2"]
    return ficha.reset_index().sort_values("tamano_m2", ascending=False)


def tabla_ciudades(semanal: pd.DataFrame, tiendas: pd.DataFrame) -> pd.DataFrame:
    """Reparto de tiendas y demanda por ciudad."""
    unido = semanal.merge(tiendas, on="id_tienda", how="left")
    return (
        unido.groupby("ciudad", observed=True)
        .agg(
            tiendas=("id_tienda", "nunique"),
            tamano_medio=("tamano_m2", "mean"),
            dem_media_sku=("unidades_vendidas", "mean"),
            unidades_total=("unidades_vendidas", "sum"),
        )
        .sort_values("tiendas", ascending=False)
        .reset_index()
    )


def tabla_patrones(semanal: pd.DataFrame, tendencias: pd.DataFrame) -> pd.DataFrame:
    """Reparto de series por patron real, con su cambio observado.

    El patron procede del fichero de ground truth y se usa solo como
    diagnostico: nunca entra como variable de un modelo.
    """
    cambios = []
    for (tienda, producto), grupo in semanal.sort_values("semana").groupby(CLAVE_SERIE, observed=True):
        y = grupo["unidades_vendidas"].to_numpy(float)
        x = np.arange(y.size, dtype=float)
        pendiente = float(np.polyfit(x, y, 1)[0])
        cambios.append(
            {
                "id_tienda": tienda,
                "id_producto": producto,
                "cambio_pct": 100 * pendiente * (y.size - 1) / y.mean(),
                "media": y.mean(),
            }
        )
    marco = pd.DataFrame(cambios).merge(tendencias, on=CLAVE_SERIE, how="left")
    return (
        marco.groupby("trend_type", observed=True)
        .agg(
            series=("cambio_pct", "size"),
            cambio_mediano=("cambio_pct", "median"),
            cambio_min=("cambio_pct", "min"),
            cambio_max=("cambio_pct", "max"),
            dem_media=("media", "mean"),
        )
        .sort_values("series", ascending=False)
        .reset_index()
    )
