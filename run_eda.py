"""Analisis univariado del Caso A: hechos, tablas y graficos.

El informe no interpreta. Describe lo que hay en los datos y deja la
lectura de esos hechos para la memoria tecnica, que se escribe aparte.

Genera:
    salidas/informes/02_univariado.txt
    salidas/figuras/*.png

Uso:
    ./.venv/bin/python run_eda.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from caso_a import eda_diario as ed  # noqa: E402
from caso_a import loaders, panel, paths, plots, profiling, tablas  # noqa: E402

ANCHO = 84


class Informe:
    """Acumula el texto del informe con un formato uniforme."""

    def __init__(self, titulo: str) -> None:
        self.partes: list[str] = [titulo.upper(), "=" * ANCHO]

    def seccion(self, texto: str) -> None:
        self.partes += ["", "", texto.upper(), "=" * ANCHO]

    def bloque(self, texto: str) -> None:
        self.partes += ["", texto, "-" * ANCHO]

    def texto(self, texto: str = "") -> None:
        self.partes.append(texto)

    def tabla(self, marco: pd.DataFrame, indice: bool = False) -> None:
        self.partes.append(marco.to_string(index=indice))

    def render(self) -> str:
        return "\n".join(self.partes) + "\n"


def _perfil(serie: pd.Series) -> str:
    perfil = profiling.perfil_numerico(serie)
    filas = [
        f"  media {perfil['media']:8.2f}    mediana {perfil['mediana']:8.2f}    desviacion {perfil['desv']:8.2f}",
        f"  minimo{perfil['min']:8.2f}    maximo  {perfil['max']:8.2f}    coef. variacion {perfil['cv']:6.3f}",
        f"  asimetria {perfil['asimetria']:6.3f}  curtosis {perfil['curtosis']:6.3f}"
        f"  ceros {perfil['ceros']} ({perfil['pct_ceros']:.2f} %)",
        f"  atipicos: {perfil['atip_iqr']} por rango intercuartilico, {perfil['atip_mad']} por metodo robusto",
    ]
    return "\n".join(filas)


def main() -> int:  # noqa: PLR0915
    paths.asegurar_salidas()
    tabs = loaders.cargar_todo(validar=True)
    ventas = tabs["ventas"]
    semanal = panel.a_semanal(ventas)
    completo = panel.enriquecer(semanal, tabs["catalogo"], tabs["tiendas"])

    inf = Informe("Analisis univariado - Caso A - Optimizacion de abastecimiento")
    inf.texto(f"Panel: {ventas.shape[0]} filas diarias, {semanal.shape[0]} filas semanales, "
              f"{semanal.groupby(panel.CLAVE_SERIE, observed=True).ngroups} series, "
              f"{semanal['semana'].nunique()} semanas.")
    inf.texto(f"Periodo: {ventas['fecha'].min().date()} a {ventas['fecha'].max().date()}.")

    # ---------------- 1. El objetivo ----------------
    inf.seccion("1. El objetivo")

    inf.bloque("1.1 Unidades vendidas por dia")
    inf.texto(_perfil(ventas["unidades_vendidas"]))
    ceros = ed.distribucion_ceros(ventas)
    con_cero = int((ceros["dias_cero"] > 0).sum())
    inf.texto(f"  dias sin venta: {int(ceros['dias_cero'].sum())}, repartidos en {con_cero} series de 160")

    inf.bloque("1.2 Unidades vendidas por semana (el objetivo que se va a modelar)")
    inf.texto(_perfil(semanal["unidades_vendidas"]))

    # ---------------- 2. Estructura temporal ----------------
    inf.seccion("2. Estructura temporal")

    inf.bloque("2.1 Ciclo dentro de la semana")
    dias = ed.patron_dia_semana(ventas)
    inf.tabla(dias[["media", "desv", "indice"]].round(3), indice=True)
    amplitud = dias["indice"].max() / dias["indice"].min()

    inf.bloque("2.2 Autocorrelacion diaria, promedio de las 160 series")
    auto_d = ed.autocorrelacion_media(ventas, max_rezago=21)
    banda_d = 1.96 / np.sqrt(91)
    inf.tabla(auto_d[["acf", "pacf"]].round(3), indice=True)
    signif = [int(r) for r in auto_d.index[auto_d["significativo"]] if r > 0]
    inf.texto(f"  banda de significacion: +-{banda_d:.3f}")

    inf.bloque("2.3 Autocorrelacion semanal, promedio de las 160 series")
    acs = [acf(g.sort_values("semana")["unidades_vendidas"].to_numpy(float), nlags=5, fft=False)
           for _, g in semanal.groupby(panel.CLAVE_SERIE, observed=True)]
    media_acf = np.vstack(acs).mean(axis=0)
    banda_s = 1.96 / np.sqrt(panel.SEMANAS)
    auto_s = pd.DataFrame({"acf": media_acf}, index=pd.RangeIndex(len(media_acf), name="rezago"))
    inf.tabla(auto_s.round(3), indice=True)
    inf.texto(f"  banda de significacion con 13 puntos: +-{banda_s:.3f}")

    # ---------------- 3. Cuanto se puede predecir ----------------
    inf.seccion("3. Cuanto se puede predecir")

    inf.bloque("3.1 De donde viene la variacion de la demanda semanal")
    objetivo = semanal["unidades_vendidas"]
    agrupado = semanal.groupby(panel.CLAVE_SERIE, observed=True)["unidades_vendidas"]
    var_total = float(objetivo.var(ddof=0))
    var_entre = float(agrupado.mean().var(ddof=0))
    var_dentro = float(agrupado.var(ddof=0).mean())
    pct_entre = 100 * var_entre / var_total
    inf.texto(f"  varianza total             {var_total:10.1f}")
    inf.texto(f"  entre series               {var_entre:10.1f}   {pct_entre:5.1f} %")
    inf.texto(f"  dentro de cada serie       {var_dentro:10.1f}   {100 - pct_entre:5.1f} %")

    sc_total = float(((objetivo - objetivo.mean()) ** 2).sum())
    sc_media = sc_recta = 0.0
    for _, grupo in semanal.sort_values("semana").groupby(panel.CLAVE_SERIE, observed=True):
        y = grupo["unidades_vendidas"].to_numpy(float)
        x = np.arange(y.size, dtype=float)
        sc_media += float(((y - y.mean()) ** 2).sum())
        sc_recta += float(((y - np.polyval(np.polyfit(x, y, 1), x)) ** 2).sum())
    r2_media = 1 - sc_media / sc_total
    r2_recta = 1 - sc_recta / sc_total
    pct_intra = 100 * (1 - sc_recta / sc_media)
    pct_tendencia = 100 * (sc_media - sc_recta) / sc_total
    pct_ruido = 100 - pct_entre - pct_tendencia

    inf.bloque("3.2 Techo de ajuste, dentro de muestra")
    inf.texto(f"  prediciendo el mismo numero para todo        R2 = 0.000")
    inf.texto(f"  prediciendo la media de cada serie           R2 = {r2_media:.3f}")
    inf.texto(f"  anadiendo la recta de cada serie             R2 = {r2_recta:.3f}")
    inf.texto(f"  la recta explica el {pct_intra:.1f} % de la variacion intra-serie")

    inf.bloque("3.3 Tendencia de cada serie en las 13 semanas")
    tend = ed.tendencia_por_serie(semanal.rename(columns={"semana": "fecha"}))
    cambio = 100 * tend["cambio_relativo"]
    inf.texto(f"  mediana {cambio.median():+6.1f} %    desviacion {cambio.std():5.1f} puntos"
              f"    rango {cambio.min():+.0f} % a {cambio.max():+.0f} %")
    inf.texto(f"  crecen mas de 20 %: {int((cambio > 20).sum())} series")
    inf.texto(f"  caen mas de 20 %:   {int((cambio < -20).sum())} series")
    inf.texto(f"  planas, entre -5 y +5 %: {int(cambio.between(-5, 5).sum())} series")

    # ---------------- 4. Las variables de contexto ----------------
    inf.seccion("4. Las variables de contexto")

    inf.bloque("4.1 Los 8 productos")
    prod = tablas.tabla_productos(semanal, tabs["catalogo"])
    vista = prod[["id_producto", "nombre", "categoria", "costo_unitario", "precio_venta",
                  "margen", "margen_pct", "costo_almacenamiento_semanal",
                  "dem_media", "cv", "nivel_sin_merma", "nivel_con_merma"]].copy()
    vista.columns = ["id", "nombre", "categoria", "coste", "precio", "margen", "margen%",
                     "almacen", "dem.media", "cv", "nivel s/merma", "nivel c/merma"]
    inf.tabla(vista.round(3))

    inf.bloque("4.2 Las 20 tiendas")
    tie = tablas.tabla_tiendas(semanal, tabs["tiendas"])
    vista_t = tie[["id_tienda", "ciudad", "tamano_m2", "dem_media_sku", "unidades_total", "unidades_por_m2"]].copy()
    vista_t.columns = ["id", "ciudad", "m2", "dem.media/SKU", "unidades", "unid/m2"]
    inf.tabla(vista_t.round(1))
    corr = tie[["tamano_m2", "dem_media_sku"]].corr(method="spearman").iloc[0, 1]

    inf.bloque("4.3 Las 3 ciudades")
    ciu = tablas.tabla_ciudades(semanal, tabs["tiendas"])
    vista_c = ciu.copy()
    vista_c.columns = ["ciudad", "tiendas", "m2 medio", "dem.media/SKU", "unidades"]
    inf.tabla(vista_c.round(1))

    inf.bloque("4.4 Los patrones del generador (solo diagnostico)")
    pat = tablas.tabla_patrones(semanal, tabs["tendencias"])
    vista_p = pat.copy()
    vista_p.columns = ["patron", "series", "cambio mediano %", "min %", "max %", "dem.media"]
    inf.tabla(vista_p.round(1))

    inf.bloque("4.5 Balance de las variables categoricas")
    _, cat = profiling.perfilar(completo[["id_tienda", "id_producto", "categoria", "ciudad"]])
    inf.tabla(cat[["categorias", "moda", "pct_moda", "entropia", "balanceada"]].round(3), indice=True)

    # ---------------- Graficos ----------------
    figuras = [
        plots.distribucion_semanal(semanal, paths.FIGURAS),
        plots.ciclo_semanal(dias, paths.FIGURAS),
        plots.autocorrelaciones(auto_d, auto_s, banda_d, banda_s, paths.FIGURAS),
        plots.descomposicion_varianza(pct_entre, pct_tendencia, pct_ruido, paths.FIGURAS),
        plots.tendencias(cambio, paths.FIGURAS),
        plots.demanda_por_producto(completo, paths.FIGURAS),
        plots.tamano_frente_demanda(completo, paths.FIGURAS),
        plots.series_ejemplo(semanal, tabs["tendencias"], paths.FIGURAS),
    ]

    inf.seccion("5. Graficos generados")
    for figura in figuras:
        inf.texto(f"  {figura.relative_to(paths.RAIZ)}")

    destino = paths.INFORMES / "02_univariado.txt"
    destino.write_text(inf.render(), encoding="utf-8")
    print(f"Informe: {destino.relative_to(paths.RAIZ)}")
    print(f"Figuras: {len(figuras)} en {paths.FIGURAS.relative_to(paths.RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
