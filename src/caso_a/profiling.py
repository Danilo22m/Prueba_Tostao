"""Perfilado univariado de columnas numericas y categoricas.

Las funciones de este modulo no toman decisiones: describen. Las decisiones de
diseno que se derivan del perfil se documentan en el informe que las usa.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Constante que hace comparable la desviacion absoluta mediana con la
#: desviacion tipica bajo normalidad.
_ESCALA_MAD = 0.6745

#: Umbral habitual del z robusto para marcar un valor como atipico.
_UMBRAL_MAD = 3.5


def atipicos_iqr(serie: pd.Series) -> int:
    """Cuenta valores fuera de 1,5 rangos intercuartilicos.

    Es la regla clasica de la caja de bigotes. Sensible a que los propios
    atipicos ensanchen los cuartiles, por eso se acompana de la version MAD.
    """
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    return int(((serie < q1 - 1.5 * iqr) | (serie > q3 + 1.5 * iqr)).sum())


def atipicos_mad(serie: pd.Series) -> int:
    """Cuenta atipicos por desviacion absoluta mediana.

    Robusta: la mediana y la MAD no se contaminan con los valores extremos que
    se pretende detectar, al contrario que la media y la desviacion tipica.
    """
    mediana = serie.median()
    mad = (serie - mediana).abs().median()
    if mad == 0:
        return 0
    z = _ESCALA_MAD * (serie - mediana) / mad
    return int((z.abs() > _UMBRAL_MAD).sum())


def perfil_numerico(serie: pd.Series) -> dict[str, float]:
    """Devuelve el perfil completo de una columna numerica."""
    limpia = serie.dropna()
    media = float(limpia.mean())
    return {
        "n": int(limpia.size),
        "nulos": int(serie.isna().sum()),
        "distintos": int(limpia.nunique()),
        "media": media,
        "mediana": float(limpia.median()),
        "desv": float(limpia.std()),
        "cv": float(limpia.std() / media) if media else float("nan"),
        "min": float(limpia.min()),
        "p01": float(limpia.quantile(0.01)),
        "p25": float(limpia.quantile(0.25)),
        "p75": float(limpia.quantile(0.75)),
        "p99": float(limpia.quantile(0.99)),
        "max": float(limpia.max()),
        "asimetria": float(limpia.skew()),
        "curtosis": float(limpia.kurtosis()),
        "ceros": int((limpia == 0).sum()),
        "pct_ceros": float(100 * (limpia == 0).mean()),
        "atip_iqr": atipicos_iqr(limpia),
        "atip_mad": atipicos_mad(limpia),
    }


def entropia(serie: pd.Series) -> float:
    """Entropia de Shannon en bits de una columna categorica.

    Cero significa una sola categoria. El maximo, log2 del numero de
    categorias, significa reparto perfectamente uniforme.
    """
    p = serie.value_counts(normalize=True).to_numpy()
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def perfil_categorico(serie: pd.Series) -> dict[str, object]:
    """Devuelve el perfil completo de una columna categorica."""
    limpia = serie.dropna()
    conteo = limpia.value_counts()
    n_cat = int(conteo.size)
    return {
        "n": int(limpia.size),
        "nulos": int(serie.isna().sum()),
        "categorias": n_cat,
        "moda": str(conteo.index[0]) if n_cat else "",
        "pct_moda": float(100 * conteo.iloc[0] / limpia.size) if n_cat else float("nan"),
        "entropia": entropia(limpia),
        "entropia_max": float(np.log2(n_cat)) if n_cat > 1 else 0.0,
        "balanceada": bool(conteo.nunique() == 1),
    }


def perfilar(marco: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Perfila todas las columnas de un DataFrame.

    Returns:
        Par de tablas: perfil de las columnas numericas y de las categoricas.
        Las columnas de fecha se omiten.
    """
    numericas, categoricas = {}, {}
    for columna in marco.columns:
        valores = marco[columna]
        if pd.api.types.is_datetime64_any_dtype(valores):
            continue
        if pd.api.types.is_numeric_dtype(valores):
            numericas[columna] = perfil_numerico(valores)
        else:
            categoricas[columna] = perfil_categorico(valores)

    num = pd.DataFrame(numericas).T if numericas else pd.DataFrame()
    cat = pd.DataFrame(categoricas).T if categoricas else pd.DataFrame()
    return num, cat
