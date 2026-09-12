"""Familias candidatas para estimar un nivel de servicio.

Todas comparten la misma interfaz: se ajustan a un nivel concreto y devuelven,
para cada fila, la cantidad que la demanda no superara esa proporcion de
semanas. Asi la comparacion mide lo mismo en todos los casos.

La linea base tambien se envuelve con esta interfaz. Da un numero, no una
distribucion, asi que sus niveles se construyen con los cuantiles empiricos de
sus propios residuales. Sin eso estariamos comparando un modelo probabilistico
contra uno puntual y ganariamos por defecto, no por merito.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import QuantileRegressor
from sklearn.preprocessing import OneHotEncoder

CLAVE_SERIE = ["id_tienda", "id_producto"]
OBJETIVO = "unidades_vendidas"

#: Prefijos de las variables temporales que construye el modulo de features.
PREFIJOS_TEMPORALES = ("rezago_", "media_", "desv_", "pendiente", "razon_ultima", "cv_reciente")


def temporales_presentes(marco: pd.DataFrame) -> list[str]:
    """Variables temporales que existen en el marco, en orden estable.

    Se derivan del marco y no de una lista fija, para que los modelos funcionen
    con cualquier profundidad de historia sin tocar codigo.
    """
    return [c for c in marco.columns if c.startswith(PREFIJOS_TEMPORALES)]


def temporales_lineales(marco: pd.DataFrame) -> list[str]:
    """Subconjunto sin dependencia lineal exacta, para los modelos lineales.

    Las medias moviles son combinaciones lineales de los rezagos, y la pendiente
    por minimos cuadrados tambien. Pasarlas todas dejaria la matriz sin rango
    completo. Se conserva el rezago mas reciente, la media y la desviacion mas
    largas disponibles, y las dos senales derivadas.
    """
    presentes = temporales_presentes(marco)
    medias = sorted(c for c in presentes if c.startswith("media_"))
    desviaciones = sorted(c for c in presentes if c.startswith("desv_"))
    elegidas = ["rezago_1"]
    if medias:
        elegidas.append(medias[-1])
    if desviaciones:
        elegidas.append(desviaciones[-1])
    elegidas += [c for c in ("razon_ultima", "cv_reciente") if c in presentes]
    return [c for c in elegidas if c in presentes]

#: Atributo de tienda. Sustituye a la identidad de tienda porque la explica casi
#: por completo y ademas generaliza a locales sin historia propia.
ESTATICAS = ["tamano_m2"]

#: Variable categorica que si entra, con codificacion indicadora. La frecuencia
#: no sirve: el diseno esta balanceado y devolveria una constante.
CATEGORICAS = ["id_producto"]


class ModeloCuantil(ABC):
    """Interfaz comun de las familias candidatas."""

    nombre: str

    #: Selector de columnas temporales. Las familias lineales lo sustituyen.
    selector = staticmethod(temporales_presentes)

    def __init__(self, nivel: float) -> None:
        self.nivel = nivel
        self._codificador: OneHotEncoder | None = None
        self.temporales: list[str] = []

    def _matriz(self, marco: pd.DataFrame, ajustar: bool = False) -> np.ndarray:
        """Compone la matriz de entrada: temporales, estaticas e indicadoras."""
        if ajustar or not self.temporales:
            self.temporales = self.selector(marco)
        numericas = marco[self.temporales + ESTATICAS].to_numpy(float)
        if ajustar or self._codificador is None:
            self._codificador = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
            indicadoras = self._codificador.fit_transform(marco[CATEGORICAS])
        else:
            indicadoras = self._codificador.transform(marco[CATEGORICAS])
        return np.hstack([numericas, indicadoras])

    @staticmethod
    def _ordenar(marco: pd.DataFrame) -> pd.DataFrame:
        """Ordena las filas de forma canonica, por serie y semana.

        Los modelos con remuestreo, como el bosque, producen resultados
        distintos segun el orden en que reciben las filas. Fijar el orden aqui
        hace que el resultado no dependa de como llegue el marco desde arriba.
        """
        return marco.sort_values(CLAVE_SERIE + ["semana"], kind="stable", ignore_index=True)

    def ajustar(self, entrenamiento: pd.DataFrame) -> "ModeloCuantil":
        """Ajusta el modelo al nivel de servicio fijado en el constructor."""
        return self._ajustar(self._ordenar(entrenamiento))

    @abstractmethod
    def _ajustar(self, entrenamiento: pd.DataFrame) -> "ModeloCuantil":
        """Implementacion concreta del ajuste, con las filas ya ordenadas."""

    @abstractmethod
    def predecir(self, datos: pd.DataFrame) -> np.ndarray:
        """Devuelve la cantidad correspondiente al nivel, fila a fila."""


class MediaMovilCuantil(ModeloCuantil):
    """Linea base: media movil mas los cuantiles empiricos de sus residuales.

    El desplazamiento se estima sobre el propio entrenamiento y se suma a la
    media movil. Es la forma honesta de que una regla puntual compita en una
    metrica distribucional.
    """

    nombre = "media movil + residuales"

    #: Longitud elegida con el barrido sobre las semanas de validacion.
    VENTANA = 4

    def __init__(self, nivel: float, ventana: int | None = None) -> None:
        super().__init__(nivel)
        self.ventana = ventana if ventana is not None else self.VENTANA
        self.desplazamiento = 0.0

    def _base(self, marco: pd.DataFrame) -> np.ndarray:
        columna = f"media_{self.ventana}"
        if columna not in marco.columns:
            disponibles = sorted(c for c in marco.columns if c.startswith("media_"))
            if not disponibles:
                raise KeyError("El marco no trae ninguna media movil.")
            columna = disponibles[-1]
        return marco[columna].to_numpy(float)

    def _ajustar(self, entrenamiento: pd.DataFrame) -> "MediaMovilCuantil":
        residuales = entrenamiento[OBJETIVO].to_numpy(float) - self._base(entrenamiento)
        self.desplazamiento = float(np.quantile(residuales, self.nivel))
        return self

    def predecir(self, datos: pd.DataFrame) -> np.ndarray:
        return self._base(datos) + self.desplazamiento


class RegresionCuantil(ModeloCuantil):
    """Regresion cuantilica lineal con regularizacion L1.

    Es el candidato interpretable. Minimiza la perdida pinball directamente, al
    contrario que una regresion ordinaria, que solo sabe dar la media.
    """

    nombre = "regresion cuantilica"
    selector = staticmethod(temporales_lineales)

    def __init__(self, nivel: float, alpha: float = 0.001) -> None:
        super().__init__(nivel)
        self.alpha = alpha
        self._modelo: QuantileRegressor | None = None
        self._centro: np.ndarray | None = None
        self._escala: np.ndarray | None = None

    def _ajustar(self, entrenamiento: pd.DataFrame) -> "RegresionCuantil":
        matriz = self._matriz(entrenamiento, ajustar=True)
        self._centro = matriz.mean(axis=0)
        self._escala = np.where(matriz.std(axis=0) > 0, matriz.std(axis=0), 1.0)
        self._modelo = QuantileRegressor(
            quantile=self.nivel, alpha=self.alpha, solver="highs"
        ).fit((matriz - self._centro) / self._escala, entrenamiento[OBJETIVO])
        return self

    def predecir(self, datos: pd.DataFrame) -> np.ndarray:
        matriz = (self._matriz(datos) - self._centro) / self._escala
        return self._modelo.predict(matriz)


class BoostingCuantil(ModeloCuantil):
    """Gradient boosting con perdida pinball nativa."""

    nombre = "boosting cuantilico"

    def __init__(self, nivel: float, **parametros) -> None:
        super().__init__(nivel)
        self.parametros = {
            "max_depth": 3, "learning_rate": 0.05, "max_iter": 300,
            "min_samples_leaf": 20, "l2_regularization": 1.0, "random_state": 0,
            **parametros,
        }
        self._modelo: HistGradientBoostingRegressor | None = None

    def _ajustar(self, entrenamiento: pd.DataFrame) -> "BoostingCuantil":
        self._modelo = HistGradientBoostingRegressor(
            loss="quantile", quantile=self.nivel, **self.parametros
        ).fit(self._matriz(entrenamiento, ajustar=True), entrenamiento[OBJETIVO])
        return self

    def predecir(self, datos: pd.DataFrame) -> np.ndarray:
        return self._modelo.predict(self._matriz(datos))


class BosqueCuantil(ModeloCuantil):
    """Bosque de regresion cuantilica.

    Un unico ajuste sirve para todos los niveles: la prediccion sale del cuantil
    empirico de las observaciones de entrenamiento que caen en las mismas hojas.
    Por construccion los niveles no pueden cruzarse, porque proceden todos de la
    misma distribucion empirica.
    """

    nombre = "bosque cuantilico"

    def __init__(self, nivel: float, **parametros) -> None:
        super().__init__(nivel)
        self.parametros = {
            "n_estimators": 300, "min_samples_leaf": 10,
            "random_state": 0, "n_jobs": -1, **parametros,
        }
        self._modelo: RandomForestRegressor | None = None
        self._hojas: np.ndarray | None = None
        self._objetivo: np.ndarray | None = None

    def _ajustar(self, entrenamiento: pd.DataFrame) -> "BosqueCuantil":
        matriz = self._matriz(entrenamiento, ajustar=True)
        self._objetivo = entrenamiento[OBJETIVO].to_numpy(float)
        self._modelo = RandomForestRegressor(**self.parametros).fit(matriz, self._objetivo)
        self._hojas = self._modelo.apply(matriz)
        return self

    def predecir(self, datos: pd.DataFrame) -> np.ndarray:
        hojas = self._modelo.apply(self._matriz(datos))
        salida = np.empty(len(hojas), dtype=float)
        for fila in range(len(hojas)):
            coincidencias = (self._hojas == hojas[fila]).sum(axis=1)
            pesos = coincidencias / coincidencias.sum()
            orden = np.argsort(self._objetivo)
            acumulado = np.cumsum(pesos[orden])
            indice = int(np.searchsorted(acumulado, self.nivel))
            salida[fila] = self._objetivo[orden][min(indice, len(orden) - 1)]
        return salida


#: Familias que se comparan en la seleccion.
FAMILIAS = {
    "media movil + residuales": MediaMovilCuantil,
    "regresion cuantilica": RegresionCuantil,
    "boosting cuantilico": BoostingCuantil,
    "bosque cuantilico": BosqueCuantil,
}


class SuavizadoPorSerie:
    """Suavizado exponencial con tendencia amortiguada, ajustado serie a serie.

    No comparte la interfaz de los modelos globales porque no usa matriz de
    variables: cada serie se ajusta con su propia historia. Se incluye para
    contrastar con evidencia propia el enfoque clasico frente al global.

    Solo produce un pronostico central. Sus niveles se construyen, como en la
    linea base, con los cuantiles empiricos de sus residuales de entrenamiento.
    """

    nombre = "suavizado por serie"

    def __init__(self, nivel: float, amortiguado: bool = True) -> None:
        self.nivel = nivel
        self.amortiguado = amortiguado
        self.desplazamiento = 0.0
        self._ajustes: dict[tuple[str, str], float] = {}

    def _ajustar_serie(self, valores: np.ndarray, pasos: int) -> np.ndarray:
        """Ajusta una serie y proyecta ``pasos`` semanas. Cae a la media si falla."""
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        try:
            modelo = ExponentialSmoothing(
                valores, trend="add", damped_trend=self.amortiguado, seasonal=None,
                initialization_method="estimated",
            ).fit(optimized=True)
            return np.asarray(modelo.forecast(pasos), dtype=float)
        except Exception:
            return np.full(pasos, float(valores.mean()))

    def ajustar_predecir(
        self, historico: pd.DataFrame, objetivo: pd.DataFrame
    ) -> np.ndarray:
        """Ajusta con el historico y predice las filas de ``objetivo``.

        Args:
            historico: Semanas disponibles antes del periodo a predecir.
            objetivo: Filas a predecir, con columnas de serie y semana.
        """
        semanas = sorted(objetivo["semana"].unique())
        predicciones: dict[tuple[str, str, int], float] = {}
        residuales: list[float] = []

        for clave, grupo in historico.sort_values("semana").groupby(CLAVE_SERIE, observed=True):
            valores = grupo[OBJETIVO].to_numpy(float)
            proyeccion = self._ajustar_serie(valores, len(semanas))
            for semana, valor in zip(semanas, proyeccion):
                predicciones[(clave[0], clave[1], int(semana))] = float(valor)
            if valores.size > 4:
                dentro = self._ajustar_serie(valores[:-1], 1)[0]
                residuales.append(float(valores[-1] - dentro))

        self.desplazamiento = float(np.quantile(residuales, self.nivel)) if residuales else 0.0
        claves = zip(objetivo["id_tienda"], objetivo["id_producto"], objetivo["semana"])
        centro = np.array([predicciones.get((t, p, int(s)), np.nan) for t, p, s in claves])
        return centro + self.desplazamiento


class PuntualConResiduales(ModeloCuantil):
    """Envoltura que convierte un modelo puntual en uno de niveles.

    Ridge, el boosting ordinario y su combinacion minimizan el error al
    cuadrado, asi que solo saben estimar la media condicional. Para que compitan
    en perdida pinball se les suma el cuantil empirico de sus propios residuales
    de entrenamiento, igual que a la linea base.

    La consecuencia es la misma que en la linea base: el colchon resultante es
    plano, el mismo para todas las series. Es la unica forma honesta de que un
    modelo puntual entre en una comparacion distribucional, y evidencia por que
    un modelo puntual no puede servir la decision de pedido por si solo.
    """

    def __init__(self, nivel: float) -> None:
        super().__init__(nivel)
        self.desplazamiento = 0.0
        self._centro: np.ndarray | None = None
        self._escala: np.ndarray | None = None

    @abstractmethod
    def _crear(self):
        """Devuelve el regresor puntual sin ajustar."""

    def _normalizar(self, matriz: np.ndarray) -> np.ndarray:
        return (matriz - self._centro) / self._escala

    def _ajustar(self, entrenamiento: pd.DataFrame) -> "PuntualConResiduales":
        matriz = self._matriz(entrenamiento, ajustar=True)
        self._centro = matriz.mean(axis=0)
        self._escala = np.where(matriz.std(axis=0) > 0, matriz.std(axis=0), 1.0)
        objetivo = entrenamiento[OBJETIVO].to_numpy(float)
        self._modelo = self._crear().fit(self._normalizar(matriz), objetivo)
        residuales = objetivo - self._modelo.predict(self._normalizar(matriz))
        self.desplazamiento = float(np.quantile(residuales, self.nivel))
        return self

    def predecir(self, datos: pd.DataFrame) -> np.ndarray:
        centro = self._modelo.predict(self._normalizar(self._matriz(datos)))
        return centro + self.desplazamiento


class RidgePuntual(PuntualConResiduales):
    """Regresion lineal con penalizacion L2.

    Estima la media condicional, no un cuantil. Se incluye porque suele dar el
    mejor pronostico central en problemas con poca senal, y sirve para medir
    cuanto cuesta usar un modelo puntual en una decision distribucional.
    """

    nombre = "ridge + residuales"
    selector = staticmethod(temporales_lineales)

    def __init__(self, nivel: float, alpha: float = 1.0) -> None:
        super().__init__(nivel)
        self.alpha = alpha

    def _crear(self):
        from sklearn.linear_model import Ridge

        return Ridge(alpha=self.alpha, random_state=None)


class BoostingPuntual(PuntualConResiduales):
    """Gradient boosting con perdida cuadratica, sin objetivo cuantilico."""

    nombre = "gbr + residuales"

    def __init__(self, nivel: float, **parametros) -> None:
        super().__init__(nivel)
        self.parametros = {
            "n_estimators": 300, "max_depth": 3, "learning_rate": 0.05,
            "min_samples_leaf": 20, "subsample": 0.9, "random_state": 0, **parametros,
        }

    def _crear(self):
        from sklearn.ensemble import GradientBoostingRegressor

        return GradientBoostingRegressor(**self.parametros)


class _MediaDeDos:
    """Promedia las predicciones de dos regresores ya ajustados."""

    def __init__(self, uno, otro) -> None:
        self.uno, self.otro = uno, otro

    def fit(self, matriz, objetivo) -> "_MediaDeDos":
        self.uno.fit(matriz, objetivo)
        self.otro.fit(matriz, objetivo)
        return self

    def predict(self, matriz) -> np.ndarray:
        return (self.uno.predict(matriz) + self.otro.predict(matriz)) / 2


class EnsemblePuntual(PuntualConResiduales):
    """Media simple de Ridge y del boosting ordinario.

    Combinar un modelo lineal con uno de arboles suele reducir la varianza del
    pronostico central. Como los dos son puntuales, la combinacion tambien lo es.
    """

    nombre = "ensemble + residuales"

    def _crear(self):
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.linear_model import Ridge

        return _MediaDeDos(
            Ridge(alpha=1.0),
            GradientBoostingRegressor(
                n_estimators=300, max_depth=3, learning_rate=0.05,
                min_samples_leaf=20, subsample=0.9, random_state=0,
            ),
        )


#: Familias puntuales: estiman la media y se convierten en niveles con los
#: cuantiles empiricos de sus residuales. El colchon que producen es constante.
FAMILIAS_PUNTUALES = {
    "ridge + residuales": RidgePuntual,
    "gbr + residuales": BoostingPuntual,
    "ensemble + residuales": EnsemblePuntual,
}

#: Todas las familias que entran en la comparacion.
FAMILIAS_TODAS = {**FAMILIAS, **FAMILIAS_PUNTUALES}
