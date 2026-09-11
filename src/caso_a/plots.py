"""Graficos del analisis exploratorio, pensados para la presentacion.

Se generan en PNG a 200 ppp sobre fondo claro, que es el que tendra la
presentacion. La paleta es categorica validada para daltonismo: azul, naranja y
verde agua como primeros tres puestos, y gris para lo que no es una categoria
real sino un residuo.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Paleta: tres primeros puestos categoricos mas tintas de texto y superficie.
AZUL = "#2a78d6"
NARANJA = "#eb6834"
AGUA = "#1baf7a"
ROJO = "#e34948"
GRIS = "#8a8a86"
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_SUAVE = "#52514e"
REJILLA = "#e4e3df"

PPP = 200


def _preparar() -> None:
    """Fija los ajustes comunes de todas las figuras."""
    plt.rcParams.update(
        {
            "figure.facecolor": SUPERFICIE,
            "axes.facecolor": SUPERFICIE,
            "axes.edgecolor": REJILLA,
            "axes.labelcolor": TINTA_SUAVE,
            "axes.titlecolor": TINTA,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": REJILLA,
            "grid.linewidth": 0.8,
            "xtick.color": TINTA_SUAVE,
            "ytick.color": TINTA_SUAVE,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.frameon": False,
            "legend.fontsize": 9,
            "font.size": 10,
        }
    )


def _limpiar(ejes: plt.Axes, rejilla: str = "y") -> None:
    """Quita los bordes superior y derecho y deja la rejilla en un solo eje."""
    ejes.spines["top"].set_visible(False)
    ejes.spines["right"].set_visible(False)
    ejes.grid(axis=rejilla)
    ejes.grid(axis="x" if rejilla == "y" else "y", visible=False)


def _guardar(figura: plt.Figure, destino: Path, nombre: str) -> Path:
    ruta = destino / f"{nombre}.png"
    figura.tight_layout()
    figura.savefig(ruta, dpi=PPP, facecolor=SUPERFICIE)
    plt.close(figura)
    return ruta


# --------------------------------------------------------------------------
# Graficos
# --------------------------------------------------------------------------

def distribucion_semanal(semanal: pd.DataFrame, destino: Path) -> Path:
    """Histograma del objetivo semanal, con media y mediana marcadas."""
    _preparar()
    y = semanal["unidades_vendidas"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.hist(y, bins=40, color=AZUL, edgecolor=SUPERFICIE, linewidth=0.6)
    ax.axvline(y.mean(), color=NARANJA, linewidth=2, label=f"media {y.mean():.0f}")
    ax.axvline(y.median(), color=TINTA, linewidth=2, linestyle="--", label=f"mediana {y.median():.0f}")
    ax.set_xlabel("Unidades por serie y semana")
    ax.set_ylabel("Nº de observaciones")
    forma = "asimetría leve" if abs(y.skew()) < 1 else "asimetría marcada"
    ceros = "sin ceros" if (y == 0).sum() == 0 else f"{int((y == 0).sum())} ceros"
    ax.set_title(f"Demanda semanal: {forma} ({y.skew():.2f}) y {ceros}")
    ax.legend()
    _limpiar(ax)
    return _guardar(fig, destino, "01_distribucion_semanal")


def ciclo_semanal(dias: pd.DataFrame, destino: Path) -> Path:
    """Indice de demanda por dia de la semana; fin de semana destacado."""
    _preparar()
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    top3 = set(dias["indice"].nlargest(3).index)
    colores = [NARANJA if nombre in top3 else AZUL for nombre in dias.index]
    barras = ax.bar(dias.index, dias["indice"], color=colores, width=0.66)
    ax.axhline(1.0, color=TINTA_SUAVE, linewidth=1)
    for barra, valor in zip(barras, dias["indice"]):
        ax.text(barra.get_x() + barra.get_width() / 2, valor + 0.02, f"{valor:.2f}",
                ha="center", va="bottom", fontsize=9, color=TINTA)
    ax.set_ylabel("Índice sobre la media diaria")
    ax.set_ylim(0, 1.45)
    altos = dias["indice"].nlargest(3)
    bajos = dias["indice"].nsmallest(len(dias) - 3)
    exceso = 100 * (altos.mean() / bajos.mean() - 1)
    nombres = [d for d in dias.index if d in set(altos.index)]
    ax.set_title(f"{", ".join(nombres)} venden un {exceso:.0f} % más que el resto")
    ax.text(0.02, 0.95, f"Naranja: los {len(altos)} días de mayor demanda",
            transform=ax.transAxes, fontsize=9, color=TINTA_SUAVE, va="top")
    _limpiar(ax)
    return _guardar(fig, destino, "02_ciclo_dia_semana")


def autocorrelaciones(acf_diaria: pd.DataFrame, acf_semanal: pd.DataFrame,
                      banda_dia: float, banda_sem: float, destino: Path) -> Path:
    """Autocorrelacion diaria y semanal, una al lado de la otra."""
    _preparar()
    fig, (izq, der) = plt.subplots(1, 2, figsize=(11.0, 4.2))

    for ax, datos, banda, titulo in (
        (izq, acf_diaria, banda_dia, "Diaria"),
        (der, acf_semanal, banda_sem, "Semanal"),
    ):
        rezagos = datos.index.to_numpy()
        valores = datos["acf"].to_numpy()
        colores = [AZUL if abs(v) > banda else GRIS for v in valores]
        colores[0] = TINTA
        ax.bar(rezagos, valores, color=colores, width=0.6)
        ax.axhspan(-banda, banda, color=REJILLA, zorder=0)
        ax.axhline(0, color=TINTA_SUAVE, linewidth=1)
        ax.set_xlabel("Rezago")
        ax.set_ylabel("Autocorrelación")
        signif = [int(r) for r in datos.index[np.abs(datos["acf"]) > banda] if r > 0]
        detalle = f"rezagos {signif}" if signif else "ningún rezago significativo"
        ax.set_title(f"{titulo}: {detalle}")
        ax.set_ylim(-0.45, 1.05)
        _limpiar(ax)

    sig_d = [int(r) for r in acf_diaria.index[np.abs(acf_diaria["acf"]) > banda_dia] if r > 0]
    sig_s = [int(r) for r in acf_semanal.index[np.abs(acf_semanal["acf"]) > banda_sem] if r > 0]
    if sig_d and not sig_s:
        mensaje = "Al agregar a semana desaparece toda la estructura temporal"
    elif sig_s:
        mensaje = f"La estructura semanal sobrevive en los rezagos {sig_s}"
    else:
        mensaje = "No se detecta estructura temporal en ninguna granularidad"
    der.text(0.5, 0.62, f"Rezago 1 semanal: {acf_semanal['acf'].iloc[1]:+.3f}\nBanda: ±{banda_sem:.3f}",
             transform=der.transAxes, fontsize=9.5, color=TINTA_SUAVE, ha="center")
    fig.suptitle(mensaje, fontsize=12.5, fontweight="bold", color=TINTA)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    ruta = destino / "03_autocorrelacion.png"
    fig.savefig(ruta, dpi=PPP, facecolor=SUPERFICIE)
    plt.close(fig)
    return ruta


def descomposicion_varianza(pct_entre: float, pct_tendencia: float,
                            pct_ruido: float, destino: Path) -> Path:
    """Barra apilada con el reparto de la varianza del objetivo.

    Las etiquetas van en una leyenda debajo y no sobre la barra, porque los dos
    ultimos segmentos son demasiado estrechos para contener texto.
    """
    _preparar()
    fig, (ax, leyenda) = plt.subplots(
        2, 1, figsize=(9.2, 3.6), gridspec_kw={"height_ratios": [2, 1]}
    )

    partes = [
        ("Diferencias entre series", pct_entre, AZUL, "una tabla de medias ya lo explica"),
        ("Tendencia de cada serie", pct_tendencia, AGUA, "aquí trabaja el modelo"),
        ("Ruido", pct_ruido, GRIS, "no es predecible"),
    ]

    izquierda = 0.0
    for _, valor, color, _ in partes:
        ax.barh([0], [valor], left=izquierda, color=color, height=0.5,
                edgecolor=SUPERFICIE, linewidth=2)
        izquierda += valor
    ax.text(pct_entre / 2, 0, f"{pct_entre:.1f} %", ha="center", va="center",
            color="white", fontsize=13, fontweight="bold")

    ax.set_xlim(0, 100)
    ax.set_ylim(-0.45, 0.45)
    ax.set_yticks([])
    ax.set_xlabel("Porcentaje de la varianza de la demanda semanal")
    ax.set_title(f"El {pct_entre:.0f} % de la variación no es pronosticable: es quién es cada serie")
    ax.spines["left"].set_visible(False)
    _limpiar(ax, rejilla="x")

    leyenda.axis("off")
    for indice, (etiqueta, valor, color, nota) in enumerate(partes):
        y = 0.78 - indice * 0.36
        leyenda.add_patch(plt.Rectangle((0.005, y - 0.10), 0.022, 0.20,
                                        color=color, transform=leyenda.transAxes))
        leyenda.text(0.042, y, f"{valor:5.1f} %   {etiqueta}", transform=leyenda.transAxes,
                     fontsize=10.5, color=TINTA, va="center", fontweight="bold")
        leyenda.text(0.042, y - 0.155, nota, transform=leyenda.transAxes,
                     fontsize=9, color=TINTA_SUAVE, va="center")

    return _guardar(fig, destino, "04_descomposicion_varianza")


def tendencias(cambios: pd.Series, destino: Path) -> Path:
    """Histograma del cambio acumulado de cada serie en trece semanas."""
    _preparar()
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bordes = np.arange(-70, 75, 5)
    for inicio, fin in zip(bordes[:-1], bordes[1:]):
        cuantos = int(cambios.between(inicio, fin, inclusive="left").sum())
        if cuantos:
            centro = (inicio + fin) / 2
            color = ROJO if centro < -5 else (AZUL if centro > 5 else GRIS)
            ax.bar(centro, cuantos, width=4.4, color=color)
    ax.axvline(0, color=TINTA_SUAVE, linewidth=1)
    ax.set_xlabel("Cambio acumulado en 13 semanas (%)")
    ax.set_ylabel("Nº de series")
    suben, bajan = int((cambios > 20).sum()), int((cambios < -20).sum())
    if suben and bajan:
        rumbo = "van en las dos direcciones"
    elif suben or bajan:
        rumbo = "van casi todas en la misma dirección"
    else:
        rumbo = "son pequeñas"
    ax.set_title(f"Las tendencias {rumbo}: {suben + bajan} series se mueven más de un 20 %")
    ax.text(0.02, 0.95,
            f"Caen más de 20 %: {int((cambios < -20).sum())}\n"
            f"Planas: {int(cambios.between(-5, 5).sum())}\n"
            f"Crecen más de 20 %: {int((cambios > 20).sum())}",
            transform=ax.transAxes, fontsize=9, color=TINTA_SUAVE, va="top")
    _limpiar(ax)
    return _guardar(fig, destino, "05_tendencias_por_serie")


def demanda_por_producto(semanal: pd.DataFrame, destino: Path) -> Path:
    """Demanda media semanal de cada SKU, ordenada de mayor a menor."""
    _preparar()
    resumen = (
        semanal.groupby("nombre", observed=True)["unidades_vendidas"]
        .agg(["mean", "std"]).sort_values("mean", ascending=True)
    )
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.barh(resumen.index, resumen["mean"], color=AZUL, height=0.62,
            xerr=resumen["std"], error_kw={"ecolor": GRIS, "elinewidth": 1.2, "capsize": 3})
    for nombre, valor in resumen["mean"].items():
        ax.text(valor + 4, nombre, f"{valor:.0f}", va="center", fontsize=9, color=TINTA)
    ax.set_xlabel("Unidades medias por tienda y semana")
    ax.set_title("Demanda media por producto, con su dispersión")
    _limpiar(ax, rejilla="x")
    return _guardar(fig, destino, "06_demanda_por_producto")


def tamano_frente_demanda(semanal: pd.DataFrame, destino: Path) -> Path:
    """Relacion entre superficie de la tienda y demanda media."""
    _preparar()
    por_tienda = semanal.groupby(["id_tienda", "ciudad", "tamano_m2"], observed=True)[
        "unidades_vendidas"
    ].mean().reset_index()
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ciudades = sorted(por_tienda["ciudad"].unique())
    colores = {c: col for c, col in zip(ciudades, (AZUL, NARANJA, AGUA))}
    for ciudad in ciudades:
        sub = por_tienda[por_tienda["ciudad"] == ciudad]
        ax.scatter(sub["tamano_m2"], sub["unidades_vendidas"], s=70,
                   color=colores[ciudad], edgecolor=SUPERFICIE, linewidth=1.5,
                   label=f"{ciudad} ({len(sub)})", zorder=3)
    coef = np.polyfit(por_tienda["tamano_m2"], por_tienda["unidades_vendidas"], 1)
    rango = np.linspace(por_tienda["tamano_m2"].min(), por_tienda["tamano_m2"].max(), 50)
    ax.plot(rango, np.polyval(coef, rango), color=TINTA_SUAVE, linewidth=1.6,
            linestyle="--", zorder=2)
    ax.set_xlabel("Superficie de la tienda (m²)")
    ax.set_ylabel("Demanda media por SKU y semana")
    rho = por_tienda["tamano_m2"].corr(por_tienda["unidades_vendidas"], method="spearman")
    relacion = "venden más" if rho > 0 else "venden menos"
    ax.set_title(f"Las tiendas grandes {relacion} (ρ = {rho:.2f}), en las {len(ciudades)} ciudades")
    ax.legend(title=None, loc="upper left")
    _limpiar(ax, rejilla="both")
    return _guardar(fig, destino, "07_tamano_vs_demanda")


def series_ejemplo(semanal: pd.DataFrame, tendencias_reales: pd.DataFrame,
                   destino: Path) -> Path:
    """Una serie de ejemplo por cada patron del fichero de tendencias."""
    _preparar()
    unido = semanal.merge(tendencias_reales, on=["id_tienda", "id_producto"], how="left")
    patrones = sorted(unido["trend_type"].unique())
    fig, ejes = plt.subplots(1, len(patrones), figsize=(3.0 * len(patrones), 3.2), sharey=True)

    for ax, patron in zip(np.atleast_1d(ejes), patrones):
        sub = unido[unido["trend_type"] == patron]
        clave = sub[["id_tienda", "id_producto"]].drop_duplicates().iloc[0]
        serie = sub[(sub.id_tienda == clave.id_tienda) & (sub.id_producto == clave.id_producto)]
        serie = serie.sort_values("semana")
        ax.plot(serie["semana"], serie["unidades_vendidas"], color=AZUL, linewidth=2,
                marker="o", markersize=4, markerfacecolor=SUPERFICIE, markeredgewidth=1.5)
        coef = np.polyfit(serie["semana"], serie["unidades_vendidas"], 1)
        ax.plot(serie["semana"], np.polyval(coef, serie["semana"]), color=NARANJA,
                linewidth=1.6, linestyle="--")
        ax.set_title(patron, fontsize=11)
        ax.set_xlabel("Semana")
        _limpiar(ax)
    np.atleast_1d(ejes)[0].set_ylabel("Unidades")
    fig.suptitle(f"Los {len(patrones)} patrones del generador, con su recta ajustada",
                 fontsize=12.5, fontweight="bold", color=TINTA)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    ruta = destino / "08_patrones_ejemplo.png"
    fig.savefig(ruta, dpi=PPP, facecolor=SUPERFICIE)
    plt.close(fig)
    return ruta


def comparacion_lineas_base(tabla: pd.DataFrame, destino: Path) -> Path:
    """Error de cada linea base en las semanas de prueba."""
    _preparar()
    datos = tabla.sort_values("WAPE", ascending=False)
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    colores = [AZUL if i == len(datos) - 1 else GRIS for i in range(len(datos))]
    ax.barh(datos.index, 100 * datos["WAPE"], color=colores, height=0.62)
    for nombre, valor in datos["WAPE"].items():
        ax.text(100 * valor + 0.12, nombre, f"{100 * valor:.2f} %", va="center",
                fontsize=9.5, color=TINTA)
    ax.set_xlabel("WAPE en las semanas de prueba (%)")
    ax.set_xlim(0, 100 * datos["WAPE"].max() * 1.14)
    ganadora = datos["WAPE"].idxmin()
    ax.set_title(f"Líneas base: gana «{ganadora}» con {100 * datos['WAPE'].min():.2f} %")
    _limpiar(ax, rejilla="x")
    return _guardar(fig, destino, "09_lineas_base")


def barrido_ventana(tabla: pd.DataFrame, destino: Path) -> Path:
    """WAPE de la media movil segun la longitud de la ventana."""
    _preparar()
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = tabla["ventana"].to_numpy()
    y = 100 * tabla["WAPE"].to_numpy()
    ax.plot(x, y, color=AZUL, linewidth=2, marker="o", markersize=7,
            markerfacecolor=SUPERFICIE, markeredgewidth=2)
    mejor = int(tabla.loc[tabla["WAPE"].idxmin(), "ventana"])
    valor = 100 * tabla["WAPE"].min()
    ax.scatter([mejor], [valor], s=150, color=NARANJA, zorder=5)
    ax.annotate(f"óptimo: {mejor} semanas\n{valor:.2f} %", xy=(mejor, valor),
                xytext=(mejor + 1.1, valor + 0.28), fontsize=9.5, color=TINTA,
                arrowprops={"arrowstyle": "->", "color": TINTA_SUAVE, "linewidth": 1})
    ax.set_xlabel("Semanas promediadas")
    ax.set_ylabel("WAPE en prueba (%)")
    ax.set_title(f"Promediar {mejor} semanas es el punto justo")
    _limpiar(ax)
    return _guardar(fig, destino, "10_barrido_ventana")


def niveles_por_escenario(tablas: dict[str, pd.DataFrame], destino: Path) -> Path:
    """Nivel de servicio de cada producto bajo cada supuesto de merma."""
    _preparar()
    orden = list(tablas.values())[-1].sort_values("nivel")["nombre"].tolist()
    colores = (AZUL, AGUA, NARANJA, ROJO)

    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    posiciones = np.arange(len(orden))
    alto = 0.8 / len(tablas)

    for indice, ((nombre, tabla), color) in enumerate(zip(tablas.items(), colores)):
        valores = tabla.set_index("nombre").loc[orden, "nivel"].to_numpy()
        desplazamiento = (indice - (len(tablas) - 1) / 2) * alto
        ax.barh(posiciones + desplazamiento, valores, height=alto * 0.92,
                color=color, label=nombre)

    ax.set_yticks(posiciones)
    ax.set_yticklabels(orden)
    ax.set_xlabel("Nivel de servicio")
    ax.set_xlim(0, 1.06)
    dispersion = {n: t["nivel"].max() - t["nivel"].min() for n, t in tablas.items()}
    mas_disperso = max(dispersion, key=dispersion.get)
    ax.set_title(f"Los niveles solo se diferencian con el supuesto «{mas_disperso}»")
    ax.legend(loc="lower right")
    _limpiar(ax, rejilla="x")
    return _guardar(fig, destino, "11_niveles_por_escenario")


def sensibilidad_merma(datos: pd.DataFrame, destino: Path) -> Path:
    """Nivel de servicio de cada producto al variar la merma supuesta."""
    _preparar()
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    finales = (
        datos[datos["fraccion_merma"] == datos["fraccion_merma"].max()]
        .set_index("nombre")["nivel"].sort_values(ascending=False)
    )

    for indice, nombre in enumerate(finales.index):
        sub = datos[datos["nombre"] == nombre].sort_values("fraccion_merma")
        opacidad = 1 - 0.55 * (indice / max(len(finales) - 1, 1))
        ax.plot(100 * sub["fraccion_merma"], sub["nivel"], linewidth=2, color=AZUL, alpha=opacidad)

    # Reparte las etiquetas a intervalos regulares y centradas sobre los valores
    # que describen, en lugar de empujarlas hacia abajo desde la primera, que
    # acabaria sacando las ultimas fuera del eje.
    inferior, superior = ax.get_ylim()
    alto = superior - inferior
    paso = min(alto * 0.055, alto * 0.8 / max(len(finales) - 1, 1))
    centro = float(finales.to_numpy().mean())
    arriba = centro + paso * (len(finales) - 1) / 2
    posiciones = [arriba - paso * i for i in range(len(finales))]

    for nombre, real, y in zip(finales.index, finales.to_numpy(), posiciones):
        ax.annotate(nombre, xy=(100, real), xytext=(106, y), fontsize=8.6,
                    va="center", color=TINTA_SUAVE,
                    arrowprops={"arrowstyle": "-", "color": REJILLA, "linewidth": 0.9})

    ax.set_xlabel("Porcentaje del sobrante que se descarta")
    ax.set_ylabel("Nivel de servicio")
    ax.set_xlim(0, 150)
    ax.set_xticks([0, 25, 50, 75, 100])
    ceros = datos[datos["fraccion_merma"] == 0]["nivel"]
    ax.set_title(
        f"De agruparse en {ceros.mean():.2f} a repartirse entre "
        f"{finales.min():.2f} y {finales.max():.2f}",
        loc="left",
    )
    _limpiar(ax, rejilla="both")
    return _guardar(fig, destino, "12_sensibilidad_merma")
