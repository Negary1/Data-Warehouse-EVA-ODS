import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT_FILE = Path(
    "data/raw/Evaluaciones_Agropecuarias_Municipales_–_EVA._2019_-_2025._Base_Agrícola_20260905.csv"
)

OUTPUT_FILE = Path(
    "data/staging/eva_agricola_staging.csv"
)


# ============================================================
# FUNCIONES DE TRANSFORMACIÓN
# ============================================================

def convertir_numero_eva(serie):
    """
    Convierte valores numéricos provenientes del formato
    colombiano utilizado en el archivo EVA.

    Ejemplos:
        '128,00'    -> 128.00
        '9.217,00'  -> 9217.00
        '0,15'      -> 0.15
    """

    texto = serie.astype(str).str.strip()

    con_coma = texto.str.contains(",", regex=False)

    resultado = texto.copy()

    resultado.loc[con_coma] = (
        resultado.loc[con_coma]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    return pd.to_numeric(resultado, errors="coerce")


def limpiar_texto(serie):
    """
    Estandarización básica de campos de texto.

    No modifica el contenido semántico:
    solamente elimina espacios innecesarios.
    """

    return (
        serie.astype(str)
        .str.strip()
    )





def ejecutar_transformacion_staging():

    # ============================================================
    # PREPARACIÓN
    # ============================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    print("=" * 70)
    print("TRANSFORMACIÓN DEL DATASET EVA")
    print("=" * 70)

    print(f"\nArchivo origen:")
    print(INPUT_FILE)

    print(f"\nArchivo destino:")
    print(OUTPUT_FILE)


    # ============================================================
    # LECTURA
    # ============================================================

    print("\n[1/6] Leyendo dataset original...")

    df = pd.read_csv(
        INPUT_FILE,
        sep=",",
        encoding="utf-8",
        dtype={
            "Código Dane departamento": "string",
            "Código Dane municipio": "string",
            "Código del cultivo": "string"
        }
    )

    registros_entrada = len(df)

    print(f"Registros leídos: {registros_entrada:,}")
    print(f"Columnas leídas: {len(df.columns)}")


    # ============================================================
    # RENOMBRAMIENTO DE COLUMNAS
    # ============================================================

    print("\n[2/6] Normalizando nombres de columnas...")

    columnas = {
        "Código Dane departamento": "codigo_departamento",
        "Departamento": "departamento",
        "Código Dane municipio": "codigo_municipio",
        "Municipio": "municipio",
        "Grupo cultivo": "grupo_cultivo",
        "Subgrupo": "subgrupo",
        "Cultivo": "cultivo",
        "Desagregación cultivo": "desagregacion_cultivo",
        "Año": "anio",
        "Periodo": "periodo",
        "Área sembrada": "area_sembrada",
        "Área cosechada": "area_cosechada",
        "Producción": "produccion",
        "Rendimiento": "rendimiento",
        "Ciclo del cultivo": "ciclo_cultivo",
        "Estado físico del cultivo": "estado_fisico_cultivo",
        "Código del cultivo": "codigo_cultivo",
        "Nombre científico del cultivo": "nombre_cientifico"
    }

    df = df.rename(columns=columnas)


    # ============================================================
    # TRANSFORMACIÓN DE IDENTIFICADORES
    # ============================================================

    print("\n[3/6] Transformando identificadores...")

    # Código departamento: 2 dígitos
    df["codigo_departamento"] = (
        pd.to_numeric(
            df["codigo_departamento"],
            errors="coerce"
        )
        .astype("Int64")
        .astype("string")
        .str.zfill(2)
    )

    # Código municipio: 5 dígitos
    df["codigo_municipio"] = (
        pd.to_numeric(
            df["codigo_municipio"],
            errors="coerce"
        )
        .astype("Int64")
        .astype("string")
        .str.zfill(5)
    )

    # Código cultivo: identificador, no medida
    df["codigo_cultivo"] = (
        df["codigo_cultivo"]
        .astype("string")
        .str.strip()
    )


    # ============================================================
    # TRANSFORMACIÓN DE TEXTOS
    # ============================================================

    print("\n[4/6] Estandarizando campos de texto...")

    columnas_texto = [
        "departamento",
        "municipio",
        "grupo_cultivo",
        "subgrupo",
        "cultivo",
        "desagregacion_cultivo",
        "periodo",
        "ciclo_cultivo",
        "estado_fisico_cultivo",
        "nombre_cientifico"
    ]

    for columna in columnas_texto:
        df[columna] = limpiar_texto(df[columna])


    # ============================================================
    # TRANSFORMACIÓN DE MÉTRICAS
    # ============================================================

    print("\n[5/6] Transformando métricas numéricas...")

    columnas_numericas = [
        "area_sembrada",
        "area_cosechada",
        "produccion",
        "rendimiento"
    ]

    for columna in columnas_numericas:
        df[columna] = convertir_numero_eva(df[columna])

    # Año como entero
    df["anio"] = pd.to_numeric(
        df["anio"],
        errors="coerce"
    ).astype("Int64")


    # ============================================================
    # ORDEN FINAL DE COLUMNAS
    # ============================================================

    columnas_finales = [
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
        "nombre_cientifico"
    ]

    df = df[columnas_finales]


    # ============================================================
    # VALIDACIONES BÁSICAS
    # ============================================================

    print("\n[6/6] Ejecutando validaciones...")

    print("\n--- Volumen ---")

    print(f"Registros entrada : {registros_entrada:,}")
    print(f"Registros salida  : {len(df):,}")

    if len(df) == registros_entrada:
        print("OK: no se eliminaron registros.")
    else:
        print("ADVERTENCIA: cambió el número de registros.")


    # ------------------------------------------------------------
    # Validación de columnas
    # ------------------------------------------------------------

    print("\n--- Columnas ---")

    if list(df.columns) == columnas_finales:
        print("OK: estructura de columnas correcta.")
    else:
        print("ERROR: estructura de columnas inesperada.")


    # ------------------------------------------------------------
    # Valores no convertibles
    # ------------------------------------------------------------

    print("\n--- Métricas no convertibles ---")

    for columna in columnas_numericas:
        cantidad = df[columna].isna().sum()

        print(
            f"{columna:20} : {cantidad:,}"
        )


    # ------------------------------------------------------------
    # Validación de códigos
    # ------------------------------------------------------------

    print("\n--- Códigos ---")

    departamentos_invalidos = (
        df["codigo_departamento"]
        .notna()
        & (df["codigo_departamento"].str.len() != 2)
    ).sum()

    municipios_invalidos = (
        df["codigo_municipio"]
        .notna()
        & (df["codigo_municipio"].str.len() != 5)
    ).sum()

    print(
        f"Códigos departamento con longitud incorrecta: "
        f"{departamentos_invalidos:,}"
    )

    print(
        f"Códigos municipio con longitud incorrecta: "
        f"{municipios_invalidos:,}"
    )


    # ------------------------------------------------------------
    # Validación Año / Periodo
    # ------------------------------------------------------------

    print("\n--- Año / Periodo ---")

    anio_periodo = (
        df["periodo"]
        .str.extract(r"^(\d{4})")[0]
    )

    anio_periodo = pd.to_numeric(
        anio_periodo,
        errors="coerce"
    ).astype("Int64")

    inconsistencias_temporales = (
        df["anio"] != anio_periodo
    ).sum()

    print(
        f"Inconsistencias Año vs Periodo: "
        f"{inconsistencias_temporales:,}"
    )


    # ------------------------------------------------------------
    # Validación de granularidad
    # ------------------------------------------------------------

    print("\n--- Granularidad ---")

    columnas_granularidad = [
        "codigo_municipio",
        "codigo_cultivo",
        "anio",
        "periodo"
    ]

    duplicados_granularidad = (
        df.duplicated(
            subset=columnas_granularidad,
            keep=False
        )
    )

    cantidad_duplicados = duplicados_granularidad.sum()

    claves_unicas = (
        df[columnas_granularidad]
        .drop_duplicates()
        .shape[0]
    )

    print(
        f"Registros                 : {len(df):,}"
    )

    print(
        f"Claves únicas             : {claves_unicas:,}"
    )

    print(
        f"Registros duplicados      : {cantidad_duplicados:,}"
    )


    # ------------------------------------------------------------
    # Validación de valores negativos
    # ------------------------------------------------------------

    print("\n--- Valores negativos ---")

    for columna in columnas_numericas:

        negativos = (
            df[columna] < 0
        ).sum()

        print(
            f"{columna:20} : {negativos:,}"
        )


    # ------------------------------------------------------------
    # Condiciones semánticas informativas
    # ------------------------------------------------------------

    print("\n--- Condiciones semánticas informativas ---")

    cosechada_mayor = (
        df["area_cosechada"] >
        df["area_sembrada"]
    ).sum()

    sembrada_cero_cosechada_mayor = (
        (df["area_sembrada"] == 0) &
        (df["area_cosechada"] > 0)
    ).sum()

    print(
        "Área cosechada > área sembrada: "
        f"{cosechada_mayor:,}"
    )

    print(
        "Área sembrada = 0 y cosechada > 0: "
        f"{sembrada_cero_cosechada_mayor:,}"
    )


    # ============================================================
    # EXPORTACIÓN
    # ============================================================

    print("\nExportando staging...")

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8"
    )

    print("\n" + "=" * 70)
    print("TRANSFORMACIÓN FINALIZADA")
    print("=" * 70)

    print(f"\nArchivo generado:")
    print(OUTPUT_FILE)

    print(f"\nRegistros:")
    print(f"{len(df):,}")

    print(f"\nColumnas:")
    print(len(df.columns))

    print("\nProceso terminado.")

    return df


if __name__ == "__main__":
    ejecutar_transformacion_staging()