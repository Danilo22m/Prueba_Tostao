"""Graficos del analisis exploratorio, pensados para la presentacion.

Se generan en PNG a 200 ppp sobre fondo claro, que es el que tendra la
presentacion. La paleta es categorica validada para daltonismo: azul, naranja y
verde agua como primeros tres puestos, y gris para lo que no es una categoria
real sino un residuo.
"""

from __future__ import annotations

import textwrap
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
    # Dos ventanas que difieren en menos de una centesima de punto son un
    # empate: se marcan las dos y se elige la mas corta, que gasta menos historia.
    valor = 100 * tabla["WAPE"].min()
    empatadas = sorted(int(v) for v in tabla.loc[100 * tabla["WAPE"] - valor < 0.01, "ventana"])
    mejor = empatadas[0]
    ax.scatter(empatadas, [100 * tabla.set_index("ventana").loc[v, "WAPE"] for v in empatadas],
               s=150, color=NARANJA, zorder=5)
    etiqueta = (f"óptimo: {mejor} semanas" if len(empatadas) == 1
                else f"empate: {' y '.join(map(str, empatadas))} semanas")
    ax.annotate(f"{etiqueta}\n{valor:.2f} %", xy=(empatadas[-1], valor),
                xytext=(empatadas[-1] + 1.1, valor + 0.28), fontsize=9.5, color=TINTA,
                arrowprops={"arrowstyle": "->", "color": TINTA_SUAVE, "linewidth": 1})
    ax.set_xlabel("Semanas promediadas")
    ax.set_ylabel("WAPE en validación (%)")
    titulo = (f"Promediar {mejor} semanas es el punto justo" if len(empatadas) == 1
              else f"Promediar {' o '.join(map(str, empatadas))} semanas da lo mismo: se toma {mejor}")
    ax.set_title(titulo)
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
    ax.set_title(f"Los niveles solo se diferencian con el supuesto «{mas_disperso}»", pad=26)
    # Las barras llegan hasta el borde derecho, asi que la leyenda va fuera del
    # area de dibujo, en una fila bajo el titulo, para no tapar ningun producto.
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=len(tablas),
              frameon=False, handlelength=1.4, columnspacing=1.6)
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


def comparacion_familias(pivote: pd.DataFrame, destino: Path) -> Path:
    """Perdida pinball de cada familia en cada nivel evaluado."""
    _preparar()
    columnas = [c for c in pivote.columns if c != "media"]
    datos = pivote.sort_values("media")
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    posiciones = np.arange(len(datos))
    ancho = 0.8 / len(columnas)

    for indice, (columna, color) in enumerate(zip(columnas, (AZUL, AGUA, NARANJA, ROJO))):
        desplazamiento = (indice - (len(columnas) - 1) / 2) * ancho
        ax.bar(posiciones + desplazamiento, datos[columna], width=ancho * 0.9,
               color=color, label=columna.replace("pinball ", "nivel "))

    ax.set_xticks(posiciones)
    ax.set_xticklabels([textwrap.fill(str(n), 13) for n in datos.index], fontsize=9)
    ax.set_ylabel("Pérdida pinball (menor es mejor)")
    ganadora = datos.index[0]
    diferencia = 100 * (datos["media"].iloc[-1] / datos["media"].iloc[0] - 1)
    ax.set_title(f"Gana «{ganadora}», con {diferencia:.1f} % de ventaja sobre la última", pad=26)
    # Las barras del nivel central llegan arriba del todo: la leyenda va fuera
    # del area de dibujo para no taparlas.
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=len(columnas),
              frameon=False, handlelength=1.4, columnspacing=1.6)
    _limpiar(ax)
    return _guardar(fig, destino, "13_comparacion_familias")


def significacion(banda: pd.DataFrame, destino: Path) -> Path:
    """Perdida de cada familia con su banda de confianza al 95 %."""
    _preparar()
    datos = banda.sort_values("pinball", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    posiciones = np.arange(len(datos))

    ax.hlines(posiciones, datos["inferior"], datos["superior"], color=REJILLA, linewidth=7)
    ax.scatter(datos["pinball"], posiciones, s=90, color=AZUL, zorder=3)
    ax.set_yticks(posiciones)
    ax.set_yticklabels(datos["familia"], fontsize=9.5)
    ax.set_xlabel("Pérdida pinball en el nivel de operación, con banda al 95 %")

    solapan = datos["inferior"].max() <= datos["superior"].min()
    veredicto = "se solapan: no hay ganador estadístico" if solapan else "no se solapan: hay ganador"
    ax.set_title(f"Las bandas {veredicto}")
    _limpiar(ax, rejilla="x")
    return _guardar(fig, destino, "14_significacion")


def colchon_por_serie(predicciones: dict, destino: Path, alto: float = 0.9, bajo: float = 0.5) -> Path:
    """Distribucion del ancho del colchon que asigna cada familia.

    El colchon es la distancia entre el nivel alto y el central. Si una familia
    lo aplica plano, su nube se reduce a una linea vertical: esa familia no
    distingue una serie estable de una volatil.
    """
    _preparar()
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    nombres = list(predicciones)

    # Una fila por familia; la etiqueta del eje ya identifica cada una, asi que
    # un solo color basta y la figura admite cualquier numero de familias.
    planas = []
    for indice, nombre in enumerate(nombres):
        colchon = predicciones[nombre][alto] - predicciones[nombre][bajo]
        dispersion = float(np.std(colchon))
        if dispersion < 0.01:
            planas.append(nombre)
        ruido = np.random.default_rng(indice).normal(0, 0.06, size=len(colchon))
        ax.scatter(colchon, np.full(len(colchon), indice) + ruido, s=9, alpha=0.32,
                   color=AZUL, edgecolor="none")
        ax.scatter([float(np.mean(colchon))], [indice], s=110, color=NARANJA,
                   edgecolor=SUPERFICIE, linewidth=2, zorder=4)

    ax.axvline(0, color=ROJO, linewidth=1.2, linestyle="--")
    ax.set_yticks(range(len(nombres)))
    ax.set_yticklabels(nombres, fontsize=9.5)
    ax.set_xlabel(f"Unidades entre el nivel {bajo} y el {alto}")
    if planas:
        mensaje = f"«{planas[0]}» aplica el mismo colchón a todas las series"
    else:
        mensaje = "Todas las familias gradúan el colchón por serie"
    ax.set_title(mensaje)
    _limpiar(ax, rejilla="x")
    return _guardar(fig, destino, "15_colchon_por_serie")


def abanico_series(
    abanico: pd.DataFrame,
    destino: Path,
    niveles_por_producto: pd.Series,
    n_mejores: int = 3,
) -> Path:
    """Pedido frente a venta real en las series mejor cubiertas y en la peor.

    La franja va del pronostico central al nivel que opera cada producto, y su
    borde superior es la cantidad que se pediria. Las series se eligen por la
    perdida pinball en ese nivel, relativa a la demanda media de cada una, para
    que una serie grande y una pequena comparen en igualdad. Se muestran las
    mejores y la peor, y el titulo lo declara.
    """
    _preparar()
    claves = ["id_tienda", "id_producto"]
    nivel_fila = abanico["id_producto"].map(niveles_por_producto).to_numpy(float)
    columna = [f"q{n:.2f}" for n in nivel_fila]
    pedido = np.array([abanico.loc[i, c] for i, c in zip(abanico.index, columna)], dtype=float)
    real = abanico["unidades_vendidas"].to_numpy(float)
    diferencia = real - pedido
    perdida = np.where(diferencia >= 0, nivel_fila * diferencia, (nivel_fila - 1) * diferencia)

    por_serie = (
        abanico[claves].assign(perdida=perdida, real=real)
        .groupby(claves, observed=True).agg(perdida=("perdida", "mean"), media=("real", "mean"))
    )
    por_serie["relativa"] = por_serie["perdida"] / por_serie["media"]
    orden = por_serie.sort_values("relativa")
    elegidas = list(orden.index[:n_mejores]) + [orden.index[-1]]

    fig, ejes = plt.subplots(1, len(elegidas), figsize=(3.1 * len(elegidas), 3.7), sharey=False)
    for posicion, (ax, clave) in enumerate(zip(np.atleast_1d(ejes), elegidas)):
        nivel = float(niveles_por_producto[clave[1]])
        alto = f"q{nivel:.2f}"
        sub = abanico[
            (abanico["id_tienda"] == clave[0]) & (abanico["id_producto"] == clave[1])
        ].sort_values("semana")
        ax.fill_between(sub["semana"], sub["q0.50"], sub[alto], color=AZUL, alpha=0.16,
                        label="colchón" if posicion == 0 else None)
        ax.plot(sub["semana"], sub["q0.50"], color=AZUL, linewidth=1.8,
                label="pronóstico central" if posicion == 0 else None)
        ax.plot(sub["semana"], sub[alto], color=TINTA, linewidth=1.8, linestyle="--",
                label="pedido al nivel de servicio" if posicion == 0 else None)
        ax.plot(sub["semana"], sub["unidades_vendidas"], color=NARANJA, linewidth=2,
                marker="o", markersize=5, markerfacecolor=SUPERFICIE, markeredgewidth=1.6,
                label="venta real" if posicion == 0 else None)
        etiqueta = "la peor de %d" % len(orden) if posicion == len(elegidas) - 1 else "entre las mejores"
        ax.set_title(f"{clave[1]} · {clave[0]}\nnivel {nivel:.2f} · {etiqueta}", fontsize=10)
        ax.set_xlabel("Semana")
        ax.set_xticks(sorted(sub["semana"].unique()))
        _limpiar(ax)
    np.atleast_1d(ejes)[0].set_ylabel("Unidades")

    fig.suptitle(
        f"Pedido frente a venta real: {n_mejores} de las series mejor cubiertas y la peor de {len(orden)}",
        fontsize=12.5, fontweight="bold", color=TINTA, y=0.99,
    )
    fig.legend(loc="lower center", ncol=4, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    ruta = destino / "16_abanico_series.png"
    fig.savefig(ruta, dpi=PPP, facecolor=SUPERFICIE)
    plt.close(fig)
    return ruta


def cobertura_niveles(cobertura: pd.DataFrame, destino: Path) -> Path:
    """Cobertura empirica de cada nivel frente a la que promete."""
    _preparar()
    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    ax.plot([0.45, 1.0], [0.45, 1.0], color=TINTA_SUAVE, linestyle="--", linewidth=1.4,
            label="cobertura perfecta")
    cortos = cobertura["desvio"] < 0
    ax.scatter(cobertura.loc[~cortos, "nivel"], cobertura.loc[~cortos, "cobertura"],
               s=80, color=AZUL, zorder=3, label="cubre lo prometido")
    if cortos.any():
        ax.scatter(cobertura.loc[cortos, "nivel"], cobertura.loc[cortos, "cobertura"],
                   s=80, color=ROJO, zorder=3, label="se queda corto")
    ax.set_xlabel("Nivel de servicio prometido")
    ax.set_ylabel("Proporción de semanas cubiertas")
    ax.set_xlim(0.45, 1.02)
    ax.set_ylim(0.45, 1.02)
    desvio = cobertura["desvio"].mean()
    peor = cobertura["desvio"].abs().max()
    if abs(desvio) < 0.005:
        titulo = f"Cobertura alineada con lo prometido; desvío máximo {peor:.3f}"
    else:
        sentido = "por encima" if desvio > 0 else "por debajo"
        titulo = f"Cobertura media {abs(desvio):.3f} {sentido} de lo prometido"
    ax.set_title(titulo)
    ax.legend(loc="upper left")
    _limpiar(ax, rejilla="both")
    return _guardar(fig, destino, "17_cobertura_niveles")


def error_por_grupo(por_producto: pd.DataFrame, por_tienda: pd.DataFrame, destino: Path) -> Path:
    """Error porcentual por producto y por tienda, uno al lado del otro."""
    _preparar()
    fig, (izq, der) = plt.subplots(1, 2, figsize=(11.0, 4.6))

    for ax, datos, titulo in (
        (izq, por_producto.sort_values("WAPE"), "Por producto"),
        (der, por_tienda.sort_values("WAPE"), "Por tienda"),
    ):
        valores = 100 * datos["WAPE"]
        media = valores.mean()
        colores = [ROJO if v > media * 1.25 else AZUL for v in valores]
        ax.barh(datos["grupo"], valores, color=colores, height=0.68)
        ax.axvline(media, color=TINTA_SUAVE, linestyle="--", linewidth=1.2)
        ax.set_xlabel("Error porcentual ponderado (%)")
        ax.set_title(f"{titulo}: de {valores.min():.1f} % a {valores.max():.1f} %")
        ax.tick_params(axis="y", labelsize=8.5)
        _limpiar(ax, rejilla="x")

    fig.tight_layout()
    ruta = destino / "18_error_por_grupo.png"
    fig.savefig(ruta, dpi=PPP, facecolor=SUPERFICIE)
    plt.close(fig)
    return ruta


def residuales(marco: pd.DataFrame, prediccion: str, destino: Path) -> Path:
    """Tres diagnosticos clasicos de los residuales."""
    _preparar()
    real = marco["unidades_vendidas"].to_numpy(float)
    pred = marco[prediccion].to_numpy(float)
    residual = real - pred

    fig, (uno, dos, tres) = plt.subplots(1, 3, figsize=(12.0, 3.9))

    limite = [min(real.min(), pred.min()), max(real.max(), pred.max())]
    uno.scatter(pred, real, s=14, color=AZUL, alpha=0.4, edgecolor="none")
    uno.plot(limite, limite, color=TINTA_SUAVE, linestyle="--", linewidth=1.3)
    uno.set_xlabel("Predicho"); uno.set_ylabel("Real")
    uno.set_title("Predicho frente a real")
    _limpiar(uno, rejilla="both")

    dos.scatter(pred, residual, s=14, color=AZUL, alpha=0.4, edgecolor="none")
    dos.axhline(0, color=TINTA_SUAVE, linewidth=1.2)
    correlacion = float(np.corrcoef(pred, np.abs(residual))[0, 1])
    dos.set_xlabel("Predicho"); dos.set_ylabel("Residual")
    dos.set_title(f"Residual frente a predicho (ρ = {correlacion:+.2f})")
    _limpiar(dos, rejilla="both")

    tres.hist(residual, bins=35, color=AZUL, edgecolor=SUPERFICIE, linewidth=0.6)
    tres.axvline(0, color=TINTA_SUAVE, linewidth=1.2)
    tres.axvline(residual.mean(), color=NARANJA, linewidth=2)
    tres.set_xlabel("Residual"); tres.set_ylabel("Frecuencia")
    tres.set_title(f"Distribución, media {residual.mean():+.2f}")
    _limpiar(tres)

    fig.tight_layout()
    ruta = destino / "19_residuales.png"
    fig.savefig(ruta, dpi=PPP, facecolor=SUPERFICIE)
    plt.close(fig)
    return ruta


def importancia(datos: pd.DataFrame, destino: Path) -> Path:
    """Degradacion de la perdida al barajar cada variable."""
    _preparar()
    orden = datos.sort_values("degradacion")
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    colores = [AZUL if v > 0 else GRIS for v in orden["degradacion"]]
    ax.barh(orden["variable"], orden["degradacion"], color=colores, height=0.66,
            xerr=orden["desviacion"], error_kw={"ecolor": REJILLA, "elinewidth": 1.2})
    ax.axvline(0, color=TINTA_SUAVE, linewidth=1.2)
    ax.set_xlabel("Aumento de la pérdida al barajar la variable")
    lider = orden.iloc[-1]
    utiles = int((orden["degradacion"] > 0.001).sum())
    ax.set_title(f"«{lider['variable']}» lidera; {utiles} de {len(orden)} variables aportan algo")
    _limpiar(ax, rejilla="x")
    return _guardar(fig, destino, "20_importancia")


def composicion_pedido(por_producto: pd.DataFrame, destino: Path) -> Path:
    """Pronostico y colchon de cada producto, apilados."""
    _preparar()
    datos = por_producto.sort_values("nivel")
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    posiciones = np.arange(len(datos))

    ax.barh(posiciones, datos["pronostico"], color=AZUL, height=0.62, label="pronóstico")
    ax.barh(posiciones, datos["colchon"], left=datos["pronostico"], color=NARANJA,
            height=0.62, label="colchón", edgecolor=SUPERFICIE, linewidth=2)

    for indice, fila in enumerate(datos.itertuples()):
        ax.text(fila.objetivo + 1.5, indice,
                f"nivel {fila.nivel:.2f}   +{fila.colchon:.1f} u",
                va="center", fontsize=8.8, color=TINTA_SUAVE)

    ax.set_yticks(posiciones)
    ax.set_yticklabels(datos["nombre"], fontsize=9.5)
    ax.set_xlabel("Unidades medias por tienda y semana")
    ax.set_xlim(0, datos["objetivo"].max() * 1.32)
    menor, mayor = datos.iloc[0], datos.iloc[-1]
    ax.set_title(
        f"El colchón sigue al margen: {mayor.colchon:.1f} u en {mayor.nombre}, "
        f"{menor.colchon:.1f} u en {menor.nombre}"
    )
    ax.legend(loc="lower right")
    _limpiar(ax, rejilla="x")
    return _guardar(fig, destino, "22_composicion_pedido")


def coste_politicas(tabla: pd.DataFrame, destino: Path) -> Path:
    """Coste de cada politica, separado en ventas perdidas y merma."""
    _preparar()
    datos = tabla.sort_values("coste_total", ascending=False)
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    posiciones = np.arange(len(datos))

    ax.barh(posiciones, datos["ventas_perdidas"], color=ROJO, height=0.62,
            label="ventas perdidas")
    ax.barh(posiciones, datos["merma"], left=datos["ventas_perdidas"], color=NARANJA,
            height=0.62, label="merma", edgecolor=SUPERFICIE, linewidth=2)

    for indice, fila in enumerate(datos.itertuples()):
        ax.text(fila.coste_total * 1.01, indice, f"{fila.coste_total / 1e6:.2f} M",
                va="center", fontsize=9, color=TINTA)

    ax.set_yticks(posiciones)
    ax.set_yticklabels(datos["politica"], fontsize=9)
    ax.set_xlabel("Coste en pesos sobre las semanas de prueba")
    ax.set_xlim(0, datos["coste_total"].max() * 1.16)
    mejor, peor = datos.iloc[-1], datos.iloc[0]
    ahorro = 100 * (1 - mejor["coste_total"] / peor["coste_total"])
    ax.set_title(f"«{mejor['politica']}» cuesta un {ahorro:.0f} % menos que la peor")
    ax.legend(loc="lower right")
    _limpiar(ax, rejilla="x")
    return _guardar(fig, destino, "23_coste_politicas")


def atribucion_ahorro(atribucion: pd.DataFrame, destino: Path) -> Path:
    """Reparto del ahorro entre el efecto de la regla y el del modelo."""
    _preparar()
    componentes = atribucion[atribucion["componente"] != "TOTAL"].copy()
    total = float(atribucion.loc[atribucion["componente"] == "TOTAL", "ahorro"].iloc[0])

    fig, ax = plt.subplots(figsize=(9.2, 3.4))
    izquierda = 0.0
    colores = (AZUL, AGUA, GRIS)
    for (_, fila), color in zip(componentes.iterrows(), colores):
        ancho = max(fila["ahorro"], 0)
        ax.barh([0], [ancho], left=izquierda, color=color, height=0.42,
                edgecolor=SUPERFICIE, linewidth=2)
        if ancho > total * 0.06:
            ax.text(izquierda + ancho / 2, 0, f"{100 * fila['ahorro'] / total:.0f} %",
                    ha="center", va="center", color="white", fontsize=11, fontweight="bold")
        izquierda += ancho

    ax.set_yticks([])
    ax.set_xlim(0, max(izquierda, total) * 1.02)
    ax.set_xlabel("Ahorro en pesos")
    ax.spines["left"].set_visible(False)

    etiquetas = "    ".join(
        f"{'■'} {fila['componente']}" for _, fila in componentes.iterrows()
    )
    dominante = componentes.loc[componentes["ahorro"].idxmax(), "componente"]
    peso = 100 * componentes["ahorro"].max() / total
    ax.set_title(f"El {peso:.0f} % del ahorro viene del «{dominante}»")
    ax.text(0, -0.42, etiquetas, fontsize=9, color=TINTA_SUAVE)
    _limpiar(ax, rejilla="x")
    return _guardar(fig, destino, "24_atribucion")


def calibracion(comparacion: pd.DataFrame, destino: Path) -> Path:
    """Cobertura de cada nivel antes y despues de calibrar."""
    _preparar()
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    ax.plot([0.45, 1.0], [0.45, 1.0], color=TINTA_SUAVE, linestyle="--", linewidth=1.4,
            label="cobertura perfecta")
    ax.scatter(comparacion["nivel"], comparacion["cobertura_antes"], s=70, color=GRIS,
               zorder=3, label="sin calibrar")
    ax.scatter(comparacion["nivel"], comparacion["cobertura_despues"], s=70, color=AZUL,
               zorder=4, label="calibrado")
    for _, fila in comparacion.iterrows():
        ax.plot([fila["nivel"], fila["nivel"]],
                [fila["cobertura_antes"], fila["cobertura_despues"]],
                color=REJILLA, linewidth=1.4, zorder=2)

    ax.set_xlabel("Nivel de servicio prometido")
    ax.set_ylabel("Proporción de semanas cubiertas")
    ax.set_xlim(0.45, 1.02)
    ax.set_ylim(0.45, 1.02)
    antes = comparacion["desvio_antes"].abs().mean()
    despues = comparacion["desvio_despues"].abs().mean()
    verbo = "mejora" if despues < antes else "no mejora"
    ax.set_title(f"La calibración {verbo}: desvío medio de {antes:.3f} a {despues:.3f}")
    ax.legend(loc="upper left")
    _limpiar(ax, rejilla="both")
    return _guardar(fig, destino, "21_calibracion")


def pedido_por_tienda(pedidos: pd.DataFrame, destino: Path) -> Path:
    """Unidades a pedir en cada tienda, separando lo que ya cubre el inventario."""
    _preparar()
    datos = (
        pedidos.groupby("id_tienda", observed=True)
        .agg(pedido=("pedido", "sum"), stock=("stock_actual", "sum"))
        .reset_index()
        .sort_values("pedido")
    )
    fig, ax = plt.subplots(figsize=(8.4, 5.6))
    posiciones = np.arange(len(datos))

    # Lo que se pide va anclado al cero para que las barras se comparen entre
    # si; el stock se apila despues, como contexto.
    ax.barh(posiciones, datos["pedido"], color=AZUL, height=0.64, label="a pedir")
    ax.barh(posiciones, datos["stock"], left=datos["pedido"], color=GRIS, height=0.64,
            label="ya en estantería", edgecolor=SUPERFICIE, linewidth=2)

    ax.set_yticks(posiciones)
    ax.set_yticklabels(datos["id_tienda"], fontsize=8.8)
    ax.set_xlabel("Unidades")
    ax.set_xlim(0, (datos["stock"] + datos["pedido"]).max() * 1.06)
    mayor, menor = datos.iloc[-1], datos.iloc[0]
    ax.set_title(
        f"El pedido va de {int(menor.pedido)} unidades en {menor.id_tienda} a "
        f"{int(mayor.pedido)} en {mayor.id_tienda}"
    )
    ax.legend(loc="lower right")
    _limpiar(ax, rejilla="x")
    return _guardar(fig, destino, "25_pedido_por_tienda")
