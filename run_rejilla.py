"""Entrenamiento de la rejilla de niveles con la familia elegida.

Ajusta un modelo por cada nivel de servicio que pidieron los costes, comprueba
que los niveles salgan ordenados y mide si cubren lo que prometen.

Genera:
    salidas/informes/06_rejilla_niveles.txt
    salidas/figuras/16_abanico_series.png
    salidas/figuras/17_cobertura_niveles.png
    salidas/parametros/abanico_prueba.csv

Uso:
    ./.venv/bin/python run_rejilla.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from caso_a import costes, features, loaders, metrics, modelos  # noqa: E402
from caso_a import panel, paths, plots, rejilla, splits  # noqa: E402

ANCHO = 84

#: Familia elegida en el paso de seleccion. La parametrizacion relativa
#: aprende la demanda como proporcion de la media reciente y devuelve la
#: prediccion en unidades.
FAMILIA = "regresion cuantilica (relativo)"


def cargar_hiperparametros() -> dict:
    """Lee los hiperparametros que fijo el paso de seleccion."""
    ruta = paths.PARAMETROS / "hiperparametros.json"
    if not ruta.exists():
        return {}
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    return contenido.get("por_familia", {}).get(FAMILIA, {})


def main() -> int:
    paths.asegurar_salidas()
    tablas = loaders.cargar_todo(validar=True)
    catalogo = tablas["catalogo"]
    pnl = panel.enriquecer(panel.a_semanal(tablas["ventas"]), catalogo, tablas["tiendas"])
    completo = features.construir(pnl)
    particion = splits.desde_panel(pnl)
    nuevas = [c for c in completo.columns if c not in pnl.columns]
    utilizable = completo.dropna(subset=nuevas)

    entrenamiento = splits.separar(utilizable, particion.entrenamiento)
    prueba = splits.separar(utilizable, particion.prueba)

    niveles = costes.rejilla_niveles(catalogo)
    parametros = cargar_hiperparametros()
    clase = modelos.FAMILIAS_AMBAS[FAMILIA]

    partes = ["REJILLA DE NIVELES - CASO A", "=" * ANCHO]
    partes += ["", f"  familia: {FAMILIA}",
               f"  hiperparametros: {json.dumps(parametros) if parametros else 'por defecto'}",
               f"  {particion}",
               f"  filas: {len(entrenamiento)} de entrenamiento, {len(prueba)} de prueba"]

    partes += ["", "", "1. NIVELES ENTRENADOS", "=" * ANCHO, ""]
    partes.append(f"  {len(niveles)} modelos, uno por nivel:")
    partes.append(f"  {niveles}")
    partes += ["", "  Los hiperparametros se optimizaron en el nivel de operacion y se reutilizan",
               "  en toda la rejilla. Con 960 filas, reoptimizar diecisiete veces invitaria a",
               "  ajustarse al ruido de la validacion."]

    ajustados, correcciones = rejilla.entrenar_calibrado(
        clase, utilizable, particion, niveles, parametros
    )
    abanico_bruto = rejilla.ordenar_niveles(rejilla.predecir(ajustados, prueba))
    abanico = rejilla.predecir_calibrado(ajustados, correcciones, prueba)

    partes += ["", "", "2. ORDEN DE LOS NIVELES", "=" * ANCHO, ""]
    monotonia = rejilla.verificar_monotonia(rejilla.predecir(ajustados, prueba))
    total_cruces = int(monotonia["cruces"].sum())
    partes.append(monotonia.round(3).to_string(index=False))
    partes += ["", f"  cruces totales: {total_cruces} sobre {len(abanico)} filas y "
                   f"{len(monotonia)} pares consecutivos"]
    if total_cruces:
        restantes = int(rejilla.verificar_monotonia(abanico)["cruces"].sum())
        partes.append(f"  corregidos ordenando los valores de cada fila; cruces restantes: {restantes}")
    else:
        partes.append("  no hace falta correccion")

    partes += ["", "", "3. COBERTURA DE CADA NIVEL", "=" * ANCHO, ""]
    partes += ["  Sobre el abanico ya calibrado. La correccion conformal se aplica dentro",
               "  del entrenamiento, antes de que ninguna decision use las predicciones.", ""]
    partes += ["  Proporcion de semanas en que la demanda real quedo por debajo del nivel.",
               "  Si el nivel cumple lo que promete, la cobertura se parece al propio nivel.",
               "  Un desvio negativo significa que el modelo se queda corto.", ""]
    cobertura = rejilla.cobertura_por_nivel(abanico)
    partes.append(cobertura.round(3).to_string(index=False))
    partes += ["", f"  desvio medio: {cobertura['desvio'].mean():+.3f}",
               f"  niveles que se quedan cortos: {int((cobertura['desvio'] < 0).sum())} de {len(cobertura)}"]

    partes += ["", "", "4. PERDIDA PINBALL POR NIVEL", "=" * ANCHO, ""]
    real = abanico[rejilla.OBJETIVO].to_numpy(float)
    filas_perdida = [
        {"nivel": float(c[1:]), "pinball": metrics.pinball(real, abanico[c].to_numpy(float), float(c[1:]))}
        for c in rejilla.columnas_nivel(abanico)
    ]
    partes.append(pd.DataFrame(filas_perdida).round(4).to_string(index=False))

    partes += ["", "", "5. NIVEL QUE OPERA CADA PRODUCTO", "=" * ANCHO, ""]
    mapa = catalogo[["id_producto", "nombre"]].copy()
    for escenario in costes.ESCENARIOS:
        politica = costes.politica_por_producto(catalogo, escenario)
        mapa[escenario.nombre] = mapa["id_producto"].map(politica)
    partes.append(mapa.to_string(index=False))

    ruta_abanico = paths.PARAMETROS / "abanico_prueba.csv"
    abanico.to_csv(ruta_abanico, index=False, encoding="utf-8")

    figuras = [
        plots.abanico_series(abanico, paths.FIGURAS),
        plots.cobertura_niveles(cobertura, paths.FIGURAS),
    ]

    partes += ["", "", "6. FICHEROS GENERADOS", "=" * ANCHO, ""]
    partes.append(f"  {ruta_abanico.relative_to(paths.RAIZ)}")
    partes += [f"  {f.relative_to(paths.RAIZ)}" for f in figuras]

    destino = paths.INFORMES / "06_rejilla_niveles.txt"
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"Informe: {destino.relative_to(paths.RAIZ)}")
    print(f"Figuras: {len(figuras)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
