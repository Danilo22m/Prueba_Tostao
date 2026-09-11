"""Costes y niveles de servicio del Caso A.

Se ejecuta antes de entrenar: define cuantos modelos de cuantil hacen falta y
cuales.

Genera:
    salidas/informes/04_costes_y_niveles.txt
    salidas/figuras/11_niveles_por_escenario.png
    salidas/figuras/12_sensibilidad_merma.png

Uso:
    ./.venv/bin/python run_costes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from caso_a import costes, loaders, panel, paths, plots  # noqa: E402

ANCHO = 84


def main() -> int:
    paths.asegurar_salidas()
    tablas = loaders.cargar_todo(validar=True)
    catalogo = tablas["catalogo"]
    semanal = panel.a_semanal(tablas["ventas"])
    demanda = semanal.groupby("id_producto", observed=True)["unidades_vendidas"].mean()

    partes = ["COSTES Y NIVELES DE SERVICIO - CASO A", "=" * ANCHO]
    partes += ["", "Importes en pesos colombianos por unidad.",
               "El nivel de servicio es la proporcion de semanas que conviene cubrir y sale",
               "de dividir el coste de faltante entre la suma de los dos costes."]

    partes += ["", "", "1. ESCENARIOS CONSIDERADOS", "=" * ANCHO]
    for escenario in costes.ESCENARIOS:
        partes += ["", f"{escenario.nombre} - se descarta el {escenario.fraccion_merma:.0%} del sobrante",
                   "-" * ANCHO, f"  {escenario.descripcion}"]

    partes += ["", "", "2. COSTES Y NIVEL DE SERVICIO POR PRODUCTO", "=" * ANCHO]
    por_escenario = {}
    for escenario in costes.ESCENARIOS:
        tabla = costes.tabla_escenario(catalogo, escenario)
        por_escenario[escenario.nombre] = tabla
        vista = tabla[["nombre", "categoria", "faltante", "sobrante", "razon", "nivel", "prob_quiebre"]]
        partes += ["", f"2.{len(por_escenario)} {escenario.nombre}", "-" * ANCHO,
                   vista.round(3).to_string(index=False)]
        rango = tabla["nivel"].max() - tabla["nivel"].min()
        partes.append(f"  rango de niveles: {tabla['nivel'].min():.3f} a {tabla['nivel'].max():.3f} "
                      f"(amplitud {rango:.3f})")

    partes += ["", "", "3. SENSIBILIDAD AL SUPUESTO DE MERMA", "=" * ANCHO, ""]
    fracciones = np.linspace(0, 1, 21)
    sens = costes.sensibilidad(catalogo, fracciones)
    pivote = sens.pivot(index="fraccion_merma", columns="nombre", values="nivel")
    partes.append(pivote.loc[::4].round(3).to_string())
    partes += ["", f"  amplitud entre el SKU mas y menos agresivo, por fraccion de merma:"]
    amplitud = pivote.max(axis=1) - pivote.min(axis=1)
    for fraccion in (0.0, 0.25, 0.5, 0.75, 1.0):
        partes.append(f"    {fraccion:.0%} descartado -> amplitud {amplitud.loc[fraccion]:.3f}")

    partes += ["", "", "4. REJILLA DE NIVELES A ENTRENAR", "=" * ANCHO, ""]
    rejilla = costes.rejilla_niveles(catalogo)
    partes.append(f"  {len(rejilla)} niveles: {rejilla}")
    partes.append(f"  acotados al rango [{costes.NIVEL_MINIMO}, {costes.NIVEL_MAXIMO}]")
    partes += ["", "  nivel que consulta cada producto en cada escenario:"]
    politicas = {e.nombre: costes.politica_por_producto(catalogo, e) for e in costes.ESCENARIOS}
    mapa = catalogo[["id_producto", "nombre"]].copy()
    for nombre, serie in politicas.items():
        mapa[nombre] = mapa["id_producto"].map(serie)
    mapa["dem_media"] = mapa["id_producto"].map(demanda).round(1)
    partes.append(mapa.to_string(index=False))

    escritos = costes.guardar_parametros(catalogo, paths.PARAMETROS)
    partes += ["", "  parametros guardados para el optimizador:"]
    partes += [f"    {ruta.relative_to(paths.RAIZ)}" for ruta in escritos.values()]

    figuras = [
        plots.niveles_por_escenario(por_escenario, paths.FIGURAS),
        plots.sensibilidad_merma(sens, paths.FIGURAS),
    ]
    partes += ["", "", "5. GRAFICOS GENERADOS", "=" * ANCHO, ""]
    partes += [f"  {f.relative_to(paths.RAIZ)}" for f in figuras]

    destino = paths.INFORMES / "04_costes_y_niveles.txt"
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"Informe: {destino.relative_to(paths.RAIZ)}")
    print(f"Figuras: {len(figuras)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
