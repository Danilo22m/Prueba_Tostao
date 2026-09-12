"""Recalibracion conformal de los niveles de servicio.

Mide si los niveles cubren lo que prometen y, si no, los corrige. Evalua el
efecto sobre la cobertura y sobre el coste de la politica.

Genera:
    salidas/informes/08_calibracion.txt
    salidas/figuras/21_calibracion.png
    salidas/parametros/ajustes_conformales.csv

Uso:
    ./.venv/bin/python run_calibracion.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from caso_a import calibracion, costes, features, loaders, modelos  # noqa: E402
from caso_a import panel, paths, plots, politicas, rejilla, splits  # noqa: E402

ANCHO = 84
FAMILIA = "regresion cuantilica (relativo)"


def niveles_por_fila(abanico: pd.DataFrame, catalogo: pd.DataFrame,
                     escenario: costes.Escenario) -> np.ndarray:
    """Lee de cada fila la columna del nivel que le toca a su producto."""
    politica = costes.politica_por_producto(catalogo, escenario)
    return np.array([
        fila[f"q{politica[fila['id_producto']]:.2f}"] for _, fila in abanico.iterrows()
    ], dtype=float)


def main() -> int:  # noqa: PLR0915
    paths.asegurar_salidas()
    tablas = loaders.cargar_todo(validar=True)
    catalogo = tablas["catalogo"]
    pnl = panel.enriquecer(panel.a_semanal(tablas["ventas"]), catalogo, tablas["tiendas"])
    completo = features.construir(pnl)
    particion = splits.desde_panel(pnl)
    nuevas = [c for c in completo.columns if c not in pnl.columns]
    utilizable = completo.dropna(subset=nuevas)

    entrenamiento = splits.separar(utilizable, particion.entrenamiento)
    prueba = splits.separar(utilizable, particion.prueba).reset_index(drop=True)

    parametros = json.loads((paths.PARAMETROS / "hiperparametros.json").read_text(encoding="utf-8"))
    parametros = parametros["por_familia"].get(FAMILIA, {})
    niveles = costes.rejilla_niveles(catalogo)
    clase = modelos.FAMILIAS_AMBAS[FAMILIA]

    partes = ["CALIBRACION CONFORMAL - CASO A", "=" * ANCHO]
    partes += ["", f"  familia: {FAMILIA}",
               f"  niveles calibrados: {len(niveles)}",
               "",
               "  El ajuste se calcula con predicciones fuera de pliegue: cada semana de",
               "  validacion la predice un modelo que no la vio. Asi no se reserva ningun",
               "  trozo del entrenamiento y la correccion sigue siendo honesta."]

    partes += ["", "", "1. DESVIO MEDIDO EN VALIDACION", "=" * ANCHO, ""]
    fuera = calibracion.predicciones_fuera_de_pliegue(
        clase, utilizable, particion, niveles, parametros
    )
    ajustes = calibracion.calcular_ajustes(fuera)
    tabla_ajustes = calibracion.tabla_ajustes(ajustes)
    partes.append(tabla_ajustes.round(4).to_string(index=False))
    partes += ["", f"  filas de calibracion: {len(fuera)}",
               f"  desvio medio antes de corregir: {tabla_ajustes['desvio'].mean():+.4f}",
               f"  desplazamiento medio aplicado:  {tabla_ajustes['desplazamiento'].mean():+.2f} unidades"]

    partes += ["", "", "2. EFECTO SOBRE LA COBERTURA EN PRUEBA", "=" * ANCHO, ""]
    ajustados = rejilla.entrenar(clase, entrenamiento, niveles, parametros)
    sin_calibrar = rejilla.ordenar_niveles(rejilla.predecir(ajustados, prueba))
    calibrado = rejilla.ordenar_niveles(calibracion.aplicar(sin_calibrar, ajustes))

    comparacion = calibracion.comparar_cobertura(sin_calibrar, calibrado)
    partes.append(comparacion.round(4).to_string(index=False))
    mejoran = int((comparacion["mejora"] > 0).sum())
    partes += ["", f"  desvio medio absoluto antes:   {comparacion['desvio_antes'].abs().mean():.4f}",
               f"  desvio medio absoluto despues: {comparacion['desvio_despues'].abs().mean():.4f}",
               f"  niveles que mejoran: {mejoran} de {len(comparacion)}"]

    partes += ["", "", "3. EFECTO SOBRE EL COSTE DE LA POLITICA", "=" * ANCHO, ""]
    filas_coste = []
    for escenario in costes.ESCENARIOS:
        disponibles = {
            "sin calibrar": niveles_por_fila(sin_calibrar, catalogo, escenario),
            "calibrado": niveles_por_fila(calibrado, catalogo, escenario),
        }
        tabla = politicas.simular(prueba, disponibles, catalogo, escenario).set_index("politica")
        filas_coste.append({
            "escenario": escenario.nombre,
            "coste_sin_calibrar": tabla.loc["sin calibrar", "coste_total"],
            "coste_calibrado": tabla.loc["calibrado", "coste_total"],
            "diferencia": tabla.loc["sin calibrar", "coste_total"] - tabla.loc["calibrado", "coste_total"],
            "servicio_sin": tabla.loc["sin calibrar", "servicio_real"],
            "servicio_cal": tabla.loc["calibrado", "servicio_real"],
        })
    marco_coste = pd.DataFrame(filas_coste)
    partes.append(marco_coste.round(3).to_string(index=False))
    partes += ["", "  Una diferencia positiva significa que calibrar abarata la politica."]

    ruta = paths.PARAMETROS / "ajustes_conformales.csv"
    tabla_ajustes.to_csv(ruta, index=False, encoding="utf-8")
    figura = plots.calibracion(comparacion, paths.FIGURAS)

    partes += ["", "", "4. FICHEROS GENERADOS", "=" * ANCHO, ""]
    partes.append(f"  {ruta.relative_to(paths.RAIZ)}")
    partes.append(f"  {figura.relative_to(paths.RAIZ)}")

    destino = paths.INFORMES / "08_calibracion.txt"
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"Informe: {destino.relative_to(paths.RAIZ)}")
    print(f"Niveles que mejoran cobertura: {mejoran} de {len(comparacion)}")
    print(f"Efecto en coste (con merma): {marco_coste.iloc[-1]['diferencia']:+,.0f} pesos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
