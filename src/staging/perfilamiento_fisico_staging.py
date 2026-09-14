# 07_perfilamiento_fisico_staging.py

import os
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO_STAGING = (
    "data/staging/eva_agricola_staging.csv"
)

CARPETA_PERFILAMIENTO = "data/validation/perfilamiento_staging"


COLUMNAS_TEXTO = [
    "codigo_departamento",
    "departamento",
    "codigo_municipio",
    "municipio",
    "grupo_cultivo",
    "subgrupo",
    "cultivo",
    "desagregacion_cultivo",
    "periodo",
    "ciclo_cultivo",
    "estado_fisico_cultivo",
    "codigo_cultivo",
    "nombre_cientifico",
]

COLUMNAS_METRICAS = [
    "area_sembrada",
    "area_cosechada",
    "produccion",
    "rendimiento",
]

COLUMNAS_ESPERADAS = [
    "codigo_departamento",
    "departamento",
    "codigo_municipio",
    "municipio",
    "grupo_cultivo",
    "subgrupo",
    "cultivo",
    "desagregacion_cultivo",
    "anio",
    "periodo",
    "area_sembrada",
    "area_cosechada",
    "produccion",
    "rendimiento",
    "ciclo_cultivo",
    "estado_fisico_cultivo",
    "codigo_cultivo",
    "nombre_cientifico",
]


# ============================================================
# FUNCIONES
# ============================================================

def analizar_precision(serie):
    """
    Determina la cantidad máxima de decimales observados
    en una serie numérica.
    """

    valores = pd.to_numeric(
        serie,
        errors="coerce"
    ).dropna()

    if valores.empty:
        return 0

    max_decimales = 0

    for valor in valores:

        texto = f"{valor:.15f}".rstrip("0")

        if "." in texto:
            decimales = len(
                texto.split(".")[1]
            )
        else:
            decimales = 0

        if decimales > max_decimales:
            max_decimales = decimales

    return max_decimales


def determinar_tipo_numerico(serie):
    """
    Determina si una serie puede representarse como
    entero o decimal.
    """

    valores = pd.to_numeric(
        serie,
        errors="coerce"
    ).dropna()

    if valores.empty:
        return "sin datos"

    son_enteros = (
        (valores % 1) == 0
    ).all()

    if son_enteros:
        return "entero"

    return "decimal"


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def ejecutar_perfilamiento_fisico():

    print("=" * 70)
    print("PERFILAMIENTO FÍSICO DEL DATASET STAGING EVA")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. VERIFICACIÓN DEL ARCHIVO
    # --------------------------------------------------------

    print("\n[1/5] Verificando archivo de staging...")

    if not os.path.exists(ARCHIVO_STAGING):

        print(
            "ERROR: No existe el archivo:",
            ARCHIVO_STAGING
        )

        return

    print(
        "OK: Archivo encontrado."
    )

    # --------------------------------------------------------
    # 2. LECTURA
    # --------------------------------------------------------

    print("\n[2/5] Leyendo staging...")

    df = pd.read_csv(
        ARCHIVO_STAGING,
        low_memory=False
    )

    print(
        f"Registros: {len(df):,}"
    )

    print(
        f"Columnas : {len(df.columns)}"
    )

    # --------------------------------------------------------
    # 3. TIPOS DE DATOS
    # --------------------------------------------------------

    print("\n[3/5] Perfilando tipos de datos...")

    tipos = []

    for columna in df.columns:

        serie = df[columna]

        tipos.append({
            "columna": columna,
            "dtype_pandas": str(serie.dtype),
            "valores_no_nulos": int(
                serie.notna().sum()
            ),
            "valores_nulos": int(
                serie.isna().sum()
            ),
            "tipo_logico_esperado": (
                "texto"
                if columna in COLUMNAS_TEXTO
                else "entero"
                if columna == "anio"
                else "decimal"
                if columna in COLUMNAS_METRICAS
                else "no definido"
            )
        })

    df_tipos = pd.DataFrame(tipos)

    # --------------------------------------------------------
    # 4. LONGITUDES DE TEXTO
    # --------------------------------------------------------

    print("\n[4/5] Perfilando longitudes de texto...")

    longitudes = []

    for columna in COLUMNAS_TEXTO:

        serie = (
            df[columna]
            .fillna("")
            .astype(str)
        )

        longitudes.append({
            "columna": columna,
            "longitud_maxima": int(
                serie.str.len().max()
            ),
            "longitud_minima": int(
                serie.str.len().min()
            ),
            "longitud_promedio": round(
                serie.str.len().mean(),
                2
            ),
            "valores_unicos": int(
                serie.nunique()
            )
        })

    df_longitudes = pd.DataFrame(
        longitudes
    )

    # --------------------------------------------------------
    # 5. PRECISIÓN DE MÉTRICAS
    # --------------------------------------------------------

    print("\n[5/5] Perfilando precisión de métricas...")

    precision = []

    for columna in COLUMNAS_METRICAS:

        serie = pd.to_numeric(
            df[columna],
            errors="coerce"
        )

        valores_validos = serie.dropna()

        if valores_validos.empty:

            minimo = None
            maximo = None
            media = None
            mediana = None
            max_decimales = 0
            tipo_numerico = "sin datos"

        else:

            minimo = valores_validos.min()
            maximo = valores_validos.max()
            media = valores_validos.mean()
            mediana = valores_validos.median()

            max_decimales = analizar_precision(
                valores_validos
            )

            tipo_numerico = determinar_tipo_numerico(
                valores_validos
            )

        precision.append({
            "columna": columna,
            "tipo_numerico_observado": tipo_numerico,
            "minimo": minimo,
            "maximo": maximo,
            "media": media,
            "mediana": mediana,
            "max_decimales_observados": max_decimales,
            "valores_nulos": int(
                serie.isna().sum()
            )
        })

    df_precision = pd.DataFrame(
        precision
    )

    # --------------------------------------------------------
    # 6. CARDINALIDADES
    # --------------------------------------------------------

    print("\n[6/6] Perfilando cardinalidades...")

    cardinalidades = []

    for columna in df.columns:

        valores_unicos = int(
            df[columna].nunique(
                dropna=True
            )
        )

        cardinalidades.append({
            "columna": columna,
            "registros": len(df),
            "valores_unicos": valores_unicos,
            "porcentaje_unicidad": round(
                (valores_unicos / len(df)) * 100,
                4
            ),
            "nulos": int(
                df[columna].isna().sum()
            )
        })

    df_cardinalidades = pd.DataFrame(
        cardinalidades
    )

    # ========================================================
    # RESUMEN EN CONSOLA
    # ========================================================

    print("\n" + "=" * 70)
    print("RESUMEN DE TIPOS")
    print("=" * 70)

    print(
        df_tipos[
            [
                "columna",
                "dtype_pandas",
                "tipo_logico_esperado"
            ]
        ].to_string(index=False)
    )

    print("\n" + "=" * 70)
    print("RESUMEN DE LONGITUDES DE TEXTO")
    print("=" * 70)

    print(
        df_longitudes.to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("RESUMEN DE MÉTRICAS")
    print("=" * 70)

    print(
        df_precision.to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("RESUMEN DE CARDINALIDADES")
    print("=" * 70)

    print(
        df_cardinalidades.to_string(
            index=False
        )
    )

    # ========================================================
    # EXPORTACIÓN
    # ========================================================

    print("\nExportando resultados...")

    os.makedirs(
        CARPETA_PERFILAMIENTO,
        exist_ok=True
    )

    archivo_tipos = os.path.join(
        CARPETA_PERFILAMIENTO,
        "07_tipos_staging.csv"
    )

    archivo_longitudes = os.path.join(
        CARPETA_PERFILAMIENTO,
        "08_longitudes_texto_staging.csv"
    )

    archivo_precision = os.path.join(
        CARPETA_PERFILAMIENTO,
        "09_precision_metricas_staging.csv"
    )

    archivo_cardinalidades = os.path.join(
        CARPETA_PERFILAMIENTO,
        "10_cardinalidades_staging.csv"
    )

    df_tipos.to_csv(
        archivo_tipos,
        index=False,
        encoding="utf-8-sig"
    )

    df_longitudes.to_csv(
        archivo_longitudes,
        index=False,
        encoding="utf-8-sig"
    )

    df_precision.to_csv(
        archivo_precision,
        index=False,
        encoding="utf-8-sig"
    )

    df_cardinalidades.to_csv(
        archivo_cardinalidades,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nArchivos generados:")

    print(
        f"- {archivo_tipos}"
    )

    print(
        f"- {archivo_longitudes}"
    )

    print(
        f"- {archivo_precision}"
    )

    print(
        f"- {archivo_cardinalidades}"
    )

    print("\n" + "=" * 70)
    print("PERFILAMIENTO FÍSICO FINALIZADO")
    print("=" * 70)


if __name__ == "__main__":
    ejecutar_perfilamiento_fisico()