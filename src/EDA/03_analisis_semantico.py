import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT_FILE = Path(
    "data/raw/Evaluaciones_Agropecuarias_Municipales_–_EVA._2019_-_2025._Base_Agrícola_20260905.csv"
)

OUTPUT_DIR = Path("data/profiling/fase_3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 50_000

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def convertir_numerico(serie):
    """
    Convierte números con coma decimal a float.

    Ejemplos:
    '127,44' -> 127.44
    '8,00'   -> 8.00
    """
    return pd.to_numeric(
        serie.astype(str)
        .str.strip()
        .str.replace(",", ".", regex=False),
        errors="coerce"
    )


def porcentaje(valor, total):
    if total == 0:
        return 0
    return (valor / total) * 100


# ============================================================
# ACUMULADORES
# ============================================================

registros_no_convertibles = []

relacion_rendimiento = []
inconsistencias_area = []

ceros_detalle = []

cambio_metodologico = []

periodos_anuales = []
periodos_semestrales = []

validacion_granularidad = []

# ============================================================
# LECTURA POR CHUNKS
# ============================================================

print("=" * 75)
print("FASE 3 - ANÁLISIS SEMÁNTICO Y REGLAS DE NEGOCIO")
print("=" * 75)

for chunk_num, df in enumerate(
    pd.read_csv(INPUT_FILE, chunksize=CHUNK_SIZE),
    start=1
):

    print(f"\nProcesando chunk {chunk_num}...")

    # --------------------------------------------------------
    # CONVERSIÓN TEMPORAL DE MÉTRICAS
    # --------------------------------------------------------

    df["area_sembrada_num"] = convertir_numerico(df["Área sembrada"])
    df["area_cosechada_num"] = convertir_numerico(df["Área cosechada"])
    df["produccion_num"] = convertir_numerico(df["Producción"])
    df["rendimiento_num"] = convertir_numerico(df["Rendimiento"])

    # ========================================================
    # 1. VALORES NO CONVERTIBLES
    # ========================================================

    columnas_metricas = {
        "Área sembrada": "area_sembrada_num",
        "Área cosechada": "area_cosechada_num",
        "Producción": "produccion_num",
        "Rendimiento": "rendimiento_num"
    }

    for columna_original, columna_num in columnas_metricas.items():

        mask = (
            df[columna_original].notna()
            & df[columna_num].isna()
        )

        if mask.any():

            valores = (
                df.loc[mask, columna_original]
                .astype(str)
                .value_counts()
            )

            for valor, cantidad in valores.items():
                registros_no_convertibles.append({
                    "metrica": columna_original,
                    "valor_original": valor,
                    "cantidad": cantidad
                })

    # ========================================================
    # 2. VALIDACIÓN DEL RENDIMIENTO
    # ========================================================

    mask_validos = (
        df["area_cosechada_num"].notna()
        & df["produccion_num"].notna()
        & df["rendimiento_num"].notna()
        & (df["area_cosechada_num"] > 0)
    )

    calculado = (
        df.loc[mask_validos, "produccion_num"]
        / df.loc[mask_validos, "area_cosechada_num"]
    )

    informado = df.loc[mask_validos, "rendimiento_num"]

    diferencia = (calculado - informado).abs()

    temp_rendimiento = df.loc[
        mask_validos,
        [
            "Código Dane municipio",
            "Municipio",
            "Código del cultivo",
            "Cultivo",
            "Año",
            "Periodo",
            "Área cosechada",
            "Producción",
            "Rendimiento"
        ]
    ].copy()

    temp_rendimiento["rendimiento_calculado"] = calculado.values
    temp_rendimiento["diferencia_absoluta"] = diferencia.values

    relacion_rendimiento.append(temp_rendimiento)

    # ========================================================
    # 3. COHERENCIA ÁREA SEMBRADA VS COSECHADA
    # ========================================================

    mask_area = (
        df["area_sembrada_num"].notna()
        & df["area_cosechada_num"].notna()
    )

    inconsistentes = df.loc[
        mask_area
        & (
            df["area_cosechada_num"]
            > df["area_sembrada_num"]
        ),
        [
            "Código Dane municipio",
            "Municipio",
            "Código del cultivo",
            "Cultivo",
            "Año",
            "Periodo",
            "Ciclo del cultivo",
            "Área sembrada",
            "Área cosechada",
            "Producción",
            "Rendimiento"
        ]
    ].copy()

    if not inconsistentes.empty:
        inconsistencias_area.append(inconsistentes)

    # ========================================================
    # 4. ANÁLISIS DE CEROS
    # ========================================================

    columnas_cero = [
        "area_sembrada_num",
        "area_cosechada_num",
        "produccion_num",
        "rendimiento_num"
    ]

    for columna in columnas_cero:

        mask_cero = df[columna] == 0

        if mask_cero.any():

            temp_ceros = df.loc[
                mask_cero,
                [
                    "Código Dane municipio",
                    "Municipio",
                    "Código del cultivo",
                    "Cultivo",
                    "Año",
                    "Periodo",
                    "Ciclo del cultivo",
                    "Área sembrada",
                    "Área cosechada",
                    "Producción",
                    "Rendimiento"
                ]
            ].copy()

            temp_ceros["metrica_cero"] = columna

            ceros_detalle.append(temp_ceros)

    # ========================================================
    # 5. CAMBIO METODOLÓGICO 2022
    # ========================================================

    # Nos interesa especialmente TRANSITORIO.
    mask_transitorio = (
        df["Ciclo del cultivo"].astype(str).str.strip()
        == "Transitorio"
    )

    mask_periodo = df["Año"].isin([2019, 2020, 2021, 2022, 2023, 2024, 2025])

    temp_cambio = df.loc[
        mask_transitorio & mask_periodo,
        [
            "Año",
            "Periodo",
            "Código Dane municipio",
            "Código del cultivo",
            "Cultivo",
            "Área sembrada",
            "Área cosechada",
            "Producción",
            "Rendimiento"
        ]
    ].copy()

    cambio_metodologico.append(temp_cambio)

    # ========================================================
    # 6. PERIODOS ANUALES VS SEMESTRALES
    # ========================================================

    periodo = df["Periodo"].astype(str).str.strip()

    mask_anual = periodo.str.fullmatch(r"\d{4}")
    mask_semestral = periodo.str.fullmatch(r"\d{4}[AB]")

    temp_periodos = df[
        mask_anual | mask_semestral
    ].copy()

    temp_periodos["tipo_periodo"] = np.where(
        mask_anual.loc[temp_periodos.index],
        "Anual",
        "Semestral"
    )

    periodos_anuales.append(
        temp_periodos[
            temp_periodos["tipo_periodo"] == "Anual"
        ]
    )

    periodos_semestrales.append(
        temp_periodos[
            temp_periodos["tipo_periodo"] == "Semestral"
        ]
    )

    # ========================================================
    # 7. VALIDACIÓN DE GRANULARIDAD
    # ========================================================

    claves = [
        "Código Dane municipio",
        "Código del cultivo",
        "Año",
        "Periodo"
    ]

    temp_grano = (
        df.groupby(claves, dropna=False)
        .size()
        .reset_index(name="cantidad")
    )

    duplicados = temp_grano[
        temp_grano["cantidad"] > 1
    ].copy()

    if not duplicados.empty:
        validacion_granularidad.append(duplicados)


# ============================================================
# RESULTADOS
# ============================================================

print("\n" + "=" * 75)
print("RESULTADOS")
print("=" * 75)

# ============================================================
# 1. VALORES NO CONVERTIBLES
# ============================================================

if registros_no_convertibles:

    df_no_convertibles = pd.DataFrame(
        registros_no_convertibles
    )

    df_no_convertibles = (
        df_no_convertibles
        .groupby(
            ["metrica", "valor_original"],
            as_index=False
        )["cantidad"]
        .sum()
        .sort_values(
            ["metrica", "cantidad"],
            ascending=[True, False]
        )
    )

else:

    df_no_convertibles = pd.DataFrame(
        columns=[
            "metrica",
            "valor_original",
            "cantidad"
        ]
    )

df_no_convertibles.to_csv(
    OUTPUT_DIR / "valores_no_convertibles.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n1. VALORES NO CONVERTIBLES")
print(df_no_convertibles.to_string(index=False))


# ============================================================
# 2. RENDIMIENTO
# ============================================================

if relacion_rendimiento:

    df_rendimiento = pd.concat(
        relacion_rendimiento,
        ignore_index=True
    )

    total_validos = len(df_rendimiento)

    tolerancias = [0.01, 0.1, 0.5, 1.0]

    print("\n2. VALIDACIÓN DEL RENDIMIENTO")

    for tolerancia in tolerancias:

        coincidencias = (
            df_rendimiento["diferencia_absoluta"]
            <= tolerancia
        ).sum()

        print(
            f"Diferencia <= {tolerancia}: "
            f"{coincidencias:,} / {total_validos:,} "
            f"({porcentaje(coincidencias, total_validos):.2f}%)"
        )

    df_rendimiento.to_csv(
        OUTPUT_DIR / "validacion_rendimiento.csv",
        index=False,
        encoding="utf-8-sig"
    )


# ============================================================
# 3. ÁREA SEMBRADA VS COSECHADA
# ============================================================

if inconsistencias_area:

    df_area = pd.concat(
        inconsistencias_area,
        ignore_index=True
    )

else:

    df_area = pd.DataFrame()

df_area.to_csv(
    OUTPUT_DIR / "inconsistencias_area.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n3. ÁREA COSECHADA > ÁREA SEMBRADA")
print(f"Registros encontrados: {len(df_area):,}")


# ============================================================
# 4. CEROS
# ============================================================

if ceros_detalle:

    df_ceros = pd.concat(
        ceros_detalle,
        ignore_index=True
    )

else:

    df_ceros = pd.DataFrame()

df_ceros.to_csv(
    OUTPUT_DIR / "detalle_ceros.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n4. CEROS")

if not df_ceros.empty:

    print(
        df_ceros["metrica_cero"]
        .value_counts()
        .to_string()
    )

    # Patrón de los tres indicadores principales
    columnas = [
        "area_cosechada_num",
        "produccion_num",
        "rendimiento_num"
    ]

    # Esta información será calculada directamente
    # sobre los registros originales acumulados posteriormente.


# ============================================================
# 5. CAMBIO METODOLÓGICO
# ============================================================

df_cambio = pd.concat(
    cambio_metodologico,
    ignore_index=True
)

resumen_cambio = (
    df_cambio
    .groupby(
        ["Año", "Periodo"],
        as_index=False
    )
    .agg(
        registros=("Código del cultivo", "size"),
        area_sembrada_promedio=("Área sembrada", "count"),
        area_cosechada_registros=("Área cosechada", "count"),
        produccion_registros=("Producción", "count"),
        rendimiento_registros=("Rendimiento", "count")
    )
)

resumen_cambio.to_csv(
    OUTPUT_DIR / "cambio_metodologico_transitorios.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n5. CAMBIO METODOLÓGICO")
print(resumen_cambio.to_string(index=False))


# ============================================================
# 6. PERIODOS
# ============================================================

df_anuales = pd.concat(
    periodos_anuales,
    ignore_index=True
)

df_semestrales = pd.concat(
    periodos_semestrales,
    ignore_index=True
)

resumen_periodos = pd.DataFrame({
    "tipo_periodo": [
        "Anual",
        "Semestral"
    ],
    "registros": [
        len(df_anuales),
        len(df_semestrales)
    ]
})

resumen_periodos["porcentaje"] = (
    resumen_periodos["registros"]
    / resumen_periodos["registros"].sum()
    * 100
)

resumen_periodos.to_csv(
    OUTPUT_DIR / "resumen_periodos.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n6. PERIODOS")
print(resumen_periodos.to_string(index=False))


# ============================================================
# 7. GRANULARIDAD
# ============================================================

if validacion_granularidad:

    df_granularidad = pd.concat(
        validacion_granularidad,
        ignore_index=True
    )

else:

    df_granularidad = pd.DataFrame(
        columns=[
            "Código Dane municipio",
            "Código del cultivo",
            "Año",
            "Periodo",
            "cantidad"
        ]
    )

df_granularidad.to_csv(
    OUTPUT_DIR / "duplicados_granularidad.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n7. VALIDACIÓN DE GRANULARIDAD")
print(
    f"Combinaciones repetidas: "
    f"{len(df_granularidad):,}"
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 75)
print("FASE 3 FINALIZADA")
print("=" * 75)

print(f"\nArchivos generados en:")
print(OUTPUT_DIR)   