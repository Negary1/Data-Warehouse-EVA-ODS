# 11_precision_textual_metricas.py

import os
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO_STAGING = (
    "data/staging/eva_agricola_staging.csv"
)

CARPETA_SALIDA = (
    "data/validation/perfilamiento_staging"
)

ARCHIVO_RESUMEN = os.path.join(
    CARPETA_SALIDA,
    "11_precision_textual_metricas.csv"
)

ARCHIVO_DISTRIBUCION = os.path.join(
    CARPETA_SALIDA,
    "12_distribucion_decimales_metricas.csv"
)

COLUMNAS_METRICAS = [
    "area_sembrada",
    "area_cosechada",
    "produccion",
    "rendimiento",
]


# ============================================================
# FUNCIONES
# ============================================================

def analizar_numero_textual(valor):
    """
    Analiza la representación textual de un número.

    Devuelve:
    - cantidad de dígitos enteros
    - cantidad de decimales
    - representación textual limpia
    """

    texto = str(valor).strip()

    # Valores vacíos
    if texto == "" or texto.lower() == "nan":
        return 0, 0, texto

    # El staging utiliza punto como separador decimal.
    if "." in texto:

        parte_entera, parte_decimal = texto.split(".", 1)

        digitos_enteros = len(
            parte_entera.lstrip("-")
        )

        cantidad_decimales = len(
            parte_decimal
        )

    else:

        digitos_enteros = len(
            texto.lstrip("-")
        )

        cantidad_decimales = 0

    return (
        digitos_enteros,
        cantidad_decimales,
        texto
    )


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print("=" * 70)
    print("ANÁLISIS DE PRECISIÓN TEXTUAL DE MÉTRICAS")
    print("DATASET STAGING EVA")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. VERIFICAR ARCHIVO
    # --------------------------------------------------------

    print("\n[1/4] Verificando archivo de staging...")

    if not os.path.exists(ARCHIVO_STAGING):

        print(
            "ERROR: No existe el archivo:",
            ARCHIVO_STAGING
        )

        return

    print("OK: Archivo encontrado.")

    # --------------------------------------------------------
    # 2. LEER MÉTRICAS COMO TEXTO
    # --------------------------------------------------------

    print(
        "\n[2/4] Leyendo métricas como texto..."
    )

    df = pd.read_csv(
        ARCHIVO_STAGING,
        dtype={
            columna: str
            for columna in COLUMNAS_METRICAS
        },
        low_memory=False
    )

    print(
        f"Registros leídos: {len(df):,}"
    )

    # --------------------------------------------------------
    # 3. ANALIZAR PRECISIÓN
    # --------------------------------------------------------

    print(
        "\n[3/4] Analizando cantidad real de decimales..."
    )

    resumen = []
    distribucion = []

    for columna in COLUMNAS_METRICAS:

        serie = (
            df[columna]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        analisis = serie.apply(
            analizar_numero_textual
        )

        digitos_enteros = analisis.apply(
            lambda x: x[0]
        )

        decimales = analisis.apply(
            lambda x: x[1]
        )

        # ----------------------------------------------------
        # Estadísticas principales
        # ----------------------------------------------------

        max_enteros = int(
            digitos_enteros.max()
        )

        max_decimales = int(
            decimales.max()
        )

        # Valores máximos
        valores_numericos = pd.to_numeric(
            serie,
            errors="coerce"
        )

        valor_maximo = valores_numericos.max()

        # ----------------------------------------------------
        # Ejemplos con mayor cantidad de decimales
        # ----------------------------------------------------

        valores_max_precision = (
            serie[
                decimales == max_decimales
            ]
            .drop_duplicates()
            .head(10)
            .tolist()
        )

        # ----------------------------------------------------
        # Distribución de decimales
        # ----------------------------------------------------

        frecuencia_decimales = (
            decimales
            .value_counts()
            .sort_index()
        )

        for cantidad_decimales, cantidad_registros in (
            frecuencia_decimales.items()
        ):

            distribucion.append({
                "columna": columna,
                "cantidad_decimales": int(
                    cantidad_decimales
                ),
                "cantidad_registros": int(
                    cantidad_registros
                ),
                "porcentaje": round(
                    (
                        cantidad_registros
                        / len(serie)
                    ) * 100,
                    4
                )
            })

        resumen.append({
            "columna": columna,
            "registros": len(serie),
            "valor_maximo": valor_maximo,
            "max_digitos_enteros": max_enteros,
            "max_decimales": max_decimales,
            "ejemplos_max_decimales": " | ".join(
                valores_max_precision
            )
        })

        print(
            f"\n{columna}"
        )

        print(
            f"  Valor máximo        : {valor_maximo}"
        )

        print(
            f"  Máx. dígitos enteros: {max_enteros}"
        )

        print(
            f"  Máx. decimales     : {max_decimales}"
        )

        print(
            "  Ejemplos:"
        )

        for ejemplo in valores_max_precision:

            print(
                f"    - {ejemplo}"
            )

    # --------------------------------------------------------
    # 4. EXPORTACIÓN
    # --------------------------------------------------------

    print(
        "\n[4/4] Exportando resultados..."
    )

    os.makedirs(
        CARPETA_SALIDA,
        exist_ok=True
    )

    df_resumen = pd.DataFrame(
        resumen
    )

    df_distribucion = pd.DataFrame(
        distribucion
    )

    df_resumen.to_csv(
        ARCHIVO_RESUMEN,
        index=False,
        encoding="utf-8-sig"
    )

    df_distribucion.to_csv(
        ARCHIVO_DISTRIBUCION,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        "\nArchivos generados:"
    )

    print(
        f"- {ARCHIVO_RESUMEN}"
    )

    print(
        f"- {ARCHIVO_DISTRIBUCION}"
    )

    print("\n" + "=" * 70)
    print("ANÁLISIS FINALIZADO")
    print("=" * 70)


if __name__ == "__main__":
    main()