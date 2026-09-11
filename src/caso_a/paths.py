"""Rutas del proyecto, resueltas desde la raiz del repositorio.

Centralizar las rutas en un unico modulo evita que los notebooks dependan
del directorio desde el que se lancen.
"""

from __future__ import annotations

from pathlib import Path

#: Raiz del repositorio: dos niveles por encima de este fichero.
RAIZ: Path = Path(__file__).resolve().parents[2]

#: Carpeta con los CSV originales del Caso A. Nunca se escribe en ella.
DATOS_CRUDOS: Path = RAIZ / "Caso A" / "01_supply_optimization"

#: Salidas generadas por el pipeline.
SALIDAS: Path = RAIZ / "salidas"
INFORMES: Path = SALIDAS / "informes"
FIGURAS: Path = SALIDAS / "figuras"

#: Nombre de fichero de cada tabla de origen.
FICHEROS: dict[str, str] = {
    "ventas": "ventas_historicas.csv",
    "inventario": "inventario_actual.csv",
    "catalogo": "catalogo_productos.csv",
    "tiendas": "maestro_tiendas.csv",
    "tendencias": "ground_truth_trends.csv",
}


def ruta_datos(tabla: str) -> Path:
    """Devuelve la ruta del CSV de una tabla.

    Args:
        tabla: Clave de la tabla, una de las de :data:`FICHEROS`.

    Returns:
        Ruta absoluta al fichero CSV.

    Raises:
        KeyError: Si la tabla no esta registrada.
        FileNotFoundError: Si el fichero no existe en disco.
    """
    if tabla not in FICHEROS:
        raise KeyError(f"Tabla desconocida: {tabla!r}. Opciones: {sorted(FICHEROS)}")
    ruta = DATOS_CRUDOS / FICHEROS[tabla]
    if not ruta.exists():
        raise FileNotFoundError(f"No se encuentra {ruta}")
    return ruta


def asegurar_salidas() -> None:
    """Crea las carpetas de salida si no existen."""
    for carpeta in (SALIDAS, INFORMES, FIGURAS):
        carpeta.mkdir(parents=True, exist_ok=True)
