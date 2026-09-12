"""Simulacion de politicas de pedido y atribucion del ahorro.

Es el paso que produce la cifra de negocio. Compara cinco reglas sobre las
mismas 480 decisiones y separa cuanto del ahorro viene de cambiar la regla y
cuanto de predecir mejor.

Genera:
    salidas/informes/10_politicas.txt
    salidas/figuras/23_coste_politicas.png
    salidas/figuras/24_atribucion.png

Uso:
    ./.venv/bin/python run_politicas.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from caso_a import costes, features, loaders, modelos, panel  # noqa: E402
from caso_a import paths, plots, politicas, rejilla, splits  # noqa: E402

ANCHO = 84
FAMILIA = "regresion cuantilica (relativo)"

#: Nombres de las cinco politicas, fijos para poder referenciarlos despues.
P0 = "P0 repetir la semana anterior"
P1 = "P1 media movil, pedir el centro"
P2 = "P2 modelo, pedir el centro"
P3 = "P3 media movil, pedir el nivel"
P4 = "P4 modelo, pedir el nivel"


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
    ajustados, correcciones = rejilla.entrenar_calibrado(
        modelos.FAMILIAS_AMBAS[FAMILIA], utilizable, particion, niveles, parametros
    )
    abanico = rejilla.predecir_calibrado(ajustados, correcciones, prueba)

    # Version ingenua del abanico: media movil mas cuantiles de sus residuales.
    ingenuo = {
        nivel: modelos.MediaMovilCuantil(nivel).ajustar(entrenamiento).predecir(prueba)
        for nivel in niveles
    }
    abanico_ingenuo = prueba[["id_tienda", "id_producto", "semana"]].copy()
    for nivel, valores in ingenuo.items():
        abanico_ingenuo[f"q{nivel:.2f}"] = valores

    escenario = next(e for e in costes.ESCENARIOS if e.nombre == "con merma")

    disponibles = {
        P0: prueba["rezago_1"].to_numpy(float),
        P1: abanico_ingenuo["q0.50"].to_numpy(float),
        P2: abanico["q0.50"].to_numpy(float),
        P3: niveles_por_fila(abanico_ingenuo, catalogo, escenario),
        P4: niveles_por_fila(abanico, catalogo, escenario),
    }

    partes = ["SIMULACION DE POLITICAS - CASO A", "=" * ANCHO]
    partes += ["", f"  escenario de coste: {escenario.nombre}",
               f"  decisiones simuladas: {len(prueba)} "
               f"({prueba.groupby(politicas.CLAVE_SERIE, observed=True).ngroups} series "
               f"x {prueba['semana'].nunique()} semanas)",
               f"  semanas: {list(particion.prueba)}",
               "",
               "  Demanda real, decision hipotetica. Se compara el nivel disponible y no la",
               "  cantidad pedida, porque el stock inicial es comun a todas las politicas."]

    partes += ["", "", "1. COSTE DE CADA POLITICA", "=" * ANCHO, ""]
    tabla = politicas.simular(prueba, disponibles, catalogo, escenario)
    vista = tabla[["politica", "coste_total", "ventas_perdidas", "merma",
                   "u_faltantes", "u_sobrantes", "tasa_quiebre", "servicio_real"]]
    partes.append(vista.round(3).to_string(index=False))
    partes += ["", "  Importes en pesos colombianos. servicio_real es la proporcion de unidades",
               "  demandadas que se pudo servir."]

    partes += ["", "", "2. QUE CAMBIA LA POLITICA, EN UNIDADES", "=" * ANCHO, ""]
    partes += ["  La politica no reduce el error: lo desplaza de un lado al otro. Compensa",
               "  porque quedarse corto y pasarse no cuestan lo mismo.", ""]
    intercambio = politicas.intercambio_de_unidades(prueba, disponibles, P1, P4)
    partes.append(intercambio.round(0).to_string(index=False))

    partes += ["", "  Detalle de una serie, semana a semana:"]
    demanda_serie = prueba.groupby(politicas.CLAVE_SERIE, observed=True)[politicas.OBJETIVO].mean()
    mediana = demanda_serie.sub(demanda_serie.median()).abs().idxmin()
    nombre_producto = catalogo.set_index("id_producto").loc[mediana[1], "nombre"]
    partes.append(f"  {nombre_producto} en {mediana[0]}, demanda media {demanda_serie[mediana]:.0f} unidades")
    partes.append("")
    detalle = politicas.detalle_de_serie(prueba, disponibles, catalogo, escenario, mediana)
    pivote_detalle = detalle.pivot_table(
        index=["politica"], columns="semana",
        values=["disponible", "coste"], aggfunc="first",
    ).round(0)
    partes.append(pivote_detalle.to_string())
    totales = detalle.groupby("politica", observed=True)["coste"].sum().sort_values()
    partes += ["", "  coste total de esa serie en las tres semanas:"]
    for nombre, valor in totales.items():
        partes.append(f"    {nombre:34s} {valor:>12,.0f}")

    partes += ["", "", "3. DE DONDE VIENE EL AHORRO", "=" * ANCHO, ""]
    atribucion = politicas.atribuir(tabla, {
        "ingenuo_centro": P1, "modelo_centro": P2,
        "ingenuo_nivel": P3, "modelo_nivel": P4,
    })
    partes.append(atribucion.round(1).to_string(index=False))
    partes += ["", "  El diseno es factorial: se cambia el pronostico manteniendo la regla, y",
               "  la regla manteniendo el pronostico. La interaccion es lo que aporta",
               "  combinarlos mas alla de la suma de sus efectos por separado."]

    partes += ["", "", "4. ES SIGNIFICATIVO EL AHORRO", "=" * ANCHO, ""]
    filas_banda = []
    for nombre, referencia in ((P4, P1), (P4, P3), (P3, P1), (P4, P0)):
        inferior, superior = politicas.banda_ahorro(
            prueba, disponibles[referencia], disponibles[nombre], catalogo, escenario
        )
        coste = tabla.set_index("politica")["coste_total"]
        filas_banda.append({
            "comparacion": f"{nombre} frente a {referencia}",
            "ahorro": coste[referencia] - coste[nombre],
            "inferior": inferior, "superior": superior,
            "significativo": "si" if inferior > 0 else "no",
        })
    partes.append(pd.DataFrame(filas_banda).round(1).to_string(index=False))
    partes += ["", "  Banda al 95 % remuestreando series completas. Si el limite inferior es",
               "  positivo, el ahorro no se explica por azar."]

    partes += ["", "", "5. SENSIBILIDAD AL ESCENARIO DE COSTE", "=" * ANCHO, ""]
    filas_esc = []
    for alternativo in costes.ESCENARIOS:
        disp = dict(disponibles)
        disp[P3] = niveles_por_fila(abanico_ingenuo, catalogo, alternativo)
        disp[P4] = niveles_por_fila(abanico, catalogo, alternativo)
        otra = politicas.simular(prueba, disp, catalogo, alternativo).set_index("politica")
        filas_esc.append({
            "escenario": alternativo.nombre,
            "P0_repetir": otra.loc[P0, "coste_total"],
            "P1_centro": otra.loc[P1, "coste_total"],
            "P3_mm_nivel": otra.loc[P3, "coste_total"],
            "P4_propuesta": otra.loc[P4, "coste_total"],
            "ahorro_vs_P1": otra.loc[P1, "coste_total"] - otra.loc[P4, "coste_total"],
            "pct_vs_P1": 100 * (1 - otra.loc[P4, "coste_total"] / otra.loc[P1, "coste_total"]),
            "pct_vs_P0": 100 * (1 - otra.loc[P4, "coste_total"] / otra.loc[P0, "coste_total"]),
        })
    partes.append(pd.DataFrame(filas_esc).round(1).to_string(index=False))
    partes += ["", "  Se muestran las cuatro politicas en los tres escenarios para que cualquier",
               "  cifra citada fuera del informe pueda localizarse aqui. pct_vs_P0 compara",
               "  contra repetir la semana anterior; pct_vs_P1, contra pedir el centro."]

    partes += ["", "", "6. EXTRAPOLACION ANUAL", "=" * ANCHO, ""]
    coste = tabla.set_index("politica")["coste_total"]
    semanas = prueba["semana"].nunique()
    ahorro_semanal = (coste[P1] - coste[P4]) / semanas
    partes.append(f"  ahorro medido en {semanas} semanas      {coste[P1] - coste[P4]:>14,.0f}")
    partes.append(f"  ahorro por semana                  {ahorro_semanal:>14,.0f}")
    partes.append(f"  extrapolado a 52 semanas           {ahorro_semanal * 52:>14,.0f}")
    partes += ["", "  Es una extrapolacion lineal desde tres semanas. Sirve para dar orden de",
               "  magnitud, no como compromiso. La cifra real la fija un piloto."]

    figuras = [
        plots.coste_politicas(tabla, paths.FIGURAS),
        plots.atribucion_ahorro(atribucion, paths.FIGURAS),
    ]
    partes += ["", "", "7. GRAFICOS GENERADOS", "=" * ANCHO, ""]
    partes += [f"  {f.relative_to(paths.RAIZ)}" for f in figuras]

    destino = paths.INFORMES / "10_politicas.txt"
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"Informe: {destino.relative_to(paths.RAIZ)}")
    print(f"Figuras: {len(figuras)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
