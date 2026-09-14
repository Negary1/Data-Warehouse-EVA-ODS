import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT_FILE = Path(
    "data/raw/Evaluaciones_Agropecuarias_Municipales_–_EVA._2019_-_2025._Base_Agrícola_20260905.csv"
)

OUTPUT_DIR = Path("data/profiling/fase_3_1")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 50_000


# ============================================================
# FUNCIÓN DE CONVERSIÓN NUMÉRICA
# ============================================================

def convertir_numero_eva(serie):
    """
    Convierte valores numéricos con formato colombiano:

        127,44    -> 127.44
        9.217,00  -> 9217.00
        9.300,00  -> 9300.00

    También soporta valores que ya vengan como:
        127.44
        9217.00
    """

    texto = (
        serie.astype(str)
        .str.strip()
    )

    # Si contiene coma:
    # se asume que la coma es separador decimal
    # y los puntos son separadores de miles.
    con_coma = texto.str.contains(",", regex=False)

    resultado = texto.copy()

    resultado.loc[con_coma] = (
        resultado.loc[con_coma]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    return pd.to_numeric(
        resultado,
        errors="coerce"
    )


# ============================================================
# ACUMULADORES
# ============================================================

no_convertibles = []

area_mayor_cosechada = []

patrones_ceros = []

datos_metodologia = []

datos_periodos = []


# ============================================================
# PROCESAMIENTO
# ============================================================

print("=" * 75)
print("FASE 3.1 - INVESTIGACIÓN DE REGLAS Y ANOMALÍAS")
print("=" * 75)

for chunk_num, df in enumerate(
    pd.read_csv(INPUT_FILE, chunksize=CHUNK_SIZE),
    start=1
):

    print(f"\nProcesando chunk {chunk_num}...")

    # --------------------------------------------------------
    # CONVERSIÓN CORRECTA DE MÉTRICAS
    # --------------------------------------------------------

    df["area_sembrada_num"] = convertir_numero_eva(
        df["Área sembrada"]
    )

    df["area_cosechada_num"] = convertir_numero_eva(
        df["Área cosechada"]
    )

    df["produccion_num"] = convertir_numero_eva(
        df["Producción"]
    )

    df["rendimiento_num"] = convertir_numero_eva(
        df["Rendimiento"]
    )

    # ========================================================
    # 1. VALORES NO CONVERTIBLES
    # ========================================================

    metricas = {
        "Área sembrada": "area_sembrada_num",
        "Área cosechada": "area_cosechada_num",
        "Producción": "produccion_num",
        "Rendimiento": "rendimiento_num"
    }

    for original, numerica in metricas.items():

        mask = (
            df[original].notna()
            & df[numerica].isna()
        )

        if mask.any():

            valores = (
                df.loc[mask, original]
                .astype(str)
                .value_counts()
            )

            for valor, cantidad in valores.items():

                no_convertibles.append({
                    "metrica": original,
                    "valor_original": valor,
                    "cantidad": cantidad
                })


    # ========================================================
    # 2. ÁREA COSECHADA > ÁREA SEMBRADA
    # ========================================================

    mask_area = (
        df["area_sembrada_num"].notna()
        & df["area_cosechada_num"].notna()
        & (
            df["area_cosechada_num"]
            > df["area_sembrada_num"]
        )
    )

    if mask_area.any():

        temp = df.loc[
            mask_area,
            [
                "Código Dane departamento",
                "Departamento",
                "Código Dane municipio",
                "Municipio",
                "Código del cultivo",
                "Cultivo",
                "Desagregación cultivo",
                "Año",
                "Periodo",
                "Ciclo del cultivo",
                "Área sembrada",
                "Área cosechada",
                "Producción",
                "Rendimiento"
            ]
        ].copy()

        temp["area_cosechada_sobre_sembrada"] = (
            temp["Área cosechada"]
        )

        # Utilizamos las columnas numéricas para el cálculo.
        temp["area_cosechada_sobre_sembrada"] = (
            df.loc[
                mask_area,
                "area_cosechada_num"
            ].values
            /
            df.loc[
                mask_area,
                "area_sembrada_num"
            ].values
        )

        temp["diferencia_hectareas"] = (
            df.loc[
                mask_area,
                "area_cosechada_num"
            ].values
            -
            df.loc[
                mask_area,
                "area_sembrada_num"
            ].values
        )

        area_mayor_cosechada.append(temp)


    # ========================================================
    # 3. PATRONES DE CEROS
    # ========================================================

    validos = (
        df["area_sembrada_num"].notna()
        & df["area_cosechada_num"].notna()
        & df["produccion_num"].notna()
        & df["rendimiento_num"].notna()
    )

    temp = df.loc[
        validos,
        [
            "Código Dane municipio",
            "Municipio",
            "Código del cultivo",
            "Cultivo",
            "Año",
            "Periodo",
            "Ciclo del cultivo",
            "area_sembrada_num",
            "area_cosechada_num",
            "produccion_num",
            "rendimiento_num"
        ]
    ].copy()

    def clasificar_cero(row):

        s = row["area_sembrada_num"]
        c = row["area_cosechada_num"]
        p = row["produccion_num"]
        r = row["rendimiento_num"]

        if c == 0 and p == 0 and r == 0 and s > 0:
            return "A: sembrada > 0 / cosechada = 0 / producción = 0 / rendimiento = 0"

        if s == 0 and c == 0 and p == 0 and r == 0:
            return "B: todas las métricas = 0"

        if c == 0 and p > 0:
            return "C: cosechada = 0 / producción > 0"

        if c > 0 and p == 0:
            return "D: cosechada > 0 / producción = 0"

        if c == 0 and p == 0 and r == 0:
            return "E: cosechada = 0 / producción = 0 / rendimiento = 0"

        return "F: sin patrón especial de cero"

    temp["patron_cero"] = temp.apply(
        clasificar_cero,
        axis=1
    )

    patrones_ceros.append(temp)


    # ========================================================
    # 4. CAMBIO METODOLÓGICO 2022
    # ========================================================

    temp_met = df[
        df["Ciclo del cultivo"].astype(str).str.strip()
        .isin(["Transitorio", "Permanente"])
    ].copy()

    temp_met["periodo_metodologico"] = np.where(
        temp_met["Año"] <= 2021,
        "2019-2021",
        "2022-2025"
    )

    datos_metodologia.append(
        temp_met[
            [
                "Año",
                "Periodo",
                "Ciclo del cultivo",
                "area_sembrada_num",
                "area_cosechada_num",
                "produccion_num",
                "rendimiento_num"
            ]
        ]
    )


    # ========================================================
    # 5. PERÍODOS ANUALES VS SEMESTRALES
    # ========================================================

    temp_periodo = df.copy()

    temp_periodo["tipo_periodo"] = np.where(
        temp_periodo["Periodo"]
        .astype(str)
        .str.fullmatch(r"\d{4}"),
        "Anual",
        "Semestral"
    )

    datos_periodos.append(
        temp_periodo[
            [
                "Año",
                "Periodo",
                "tipo_periodo",
                "Ciclo del cultivo",
                "area_sembrada_num",
                "area_cosechada_num",
                "produccion_num",
                "rendimiento_num"
            ]
        ]
    )


# ============================================================
# 1. RESULTADOS DE CONVERSIÓN
# ============================================================

print("\n" + "=" * 75)
print("1. VALORES NO CONVERTIBLES")
print("=" * 75)

if no_convertibles:

    df_no_convertibles = pd.DataFrame(
        no_convertibles
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

print(
    df_no_convertibles.to_string(
        index=False
    )
)

df_no_convertibles.to_csv(
    OUTPUT_DIR / "01_no_convertibles.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 2. ÁREA COSECHADA > ÁREA SEMBRADA
# ============================================================

print("\n" + "=" * 75)
print("2. ÁREA COSECHADA > ÁREA SEMBRADA")
print("=" * 75)

df_area = pd.concat(
    area_mayor_cosechada,
    ignore_index=True
)

print(
    f"Total de registros: {len(df_area):,}"
)

if not df_area.empty:

    print("\nPor ciclo:")
    print(
        df_area["Ciclo del cultivo"]
        .value_counts()
        .to_string()
    )

    print("\nPor año:")
    print(
        df_area["Año"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nRatio cosechada / sembrada:")

    print(
        df_area[
            "area_cosechada_sobre_sembrada"
        ].describe(
            percentiles=[
                0.25,
                0.50,
                0.75,
                0.90,
                0.95,
                0.99
            ]
        ).to_string()
    )

    print("\nDiferencia en hectáreas:")

    print(
        df_area[
            "diferencia_hectareas"
        ].describe(
            percentiles=[
                0.25,
                0.50,
                0.75,
                0.90,
                0.95,
                0.99
            ]
        ).to_string()
    )

    print("\nTop 20 cultivos:")
    print(
        df_area["Cultivo"]
        .value_counts()
        .head(20)
        .to_string()
    )

df_area.to_csv(
    OUTPUT_DIR / "02_area_cosechada_mayor.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 3. PATRONES DE CEROS
# ============================================================

print("\n" + "=" * 75)
print("3. PATRONES DE CEROS")
print("=" * 75)

df_ceros = pd.concat(
    patrones_ceros,
    ignore_index=True
)

resumen_ceros = (
    df_ceros["patron_cero"]
    .value_counts()
    .rename_axis("patron")
    .reset_index(name="registros")
)

resumen_ceros["porcentaje"] = (
    resumen_ceros["registros"]
    / len(df_ceros)
    * 100
)

print(
    resumen_ceros.to_string(
        index=False
    )
)

print("\nPatrones de cero por ciclo:")

tabla_ciclo_cero = pd.crosstab(
    df_ceros["Ciclo del cultivo"],
    df_ceros["patron_cero"]
)

print(
    tabla_ciclo_cero.to_string()
)

print("\nPatrones de cero por año:")

tabla_anio_cero = pd.crosstab(
    df_ceros["Año"],
    df_ceros["patron_cero"]
)

print(
    tabla_anio_cero.to_string()
)

resumen_ceros.to_csv(
    OUTPUT_DIR / "03_resumen_patrones_ceros.csv",
    index=False,
    encoding="utf-8-sig"
)

tabla_ciclo_cero.to_csv(
    OUTPUT_DIR / "04_ceros_por_ciclo.csv",
    encoding="utf-8-sig"
)

tabla_anio_cero.to_csv(
    OUTPUT_DIR / "05_ceros_por_anio.csv",
    encoding="utf-8-sig"
)


# ============================================================
# 4. CAMBIO METODOLÓGICO
# ============================================================

print("\n" + "=" * 75)
print("4. ANÁLISIS DEL CAMBIO METODOLÓGICO 2022")
print("=" * 75)

df_met = pd.concat(
    datos_metodologia,
    ignore_index=True
)

df_met["periodo_metodologico"] = np.where(
    df_met["Año"] <= 2021,
    "2019-2021",
    "2022-2025"
)

resumen_met = (
    df_met
    .groupby(
        [
            "Ciclo del cultivo",
            "periodo_metodologico"
        ],
        as_index=False
    )
    .agg(
        registros=(
            "Año",
            "size"
        ),
        area_sembrada_promedio=(
            "area_sembrada_num",
            "mean"
        ),
        area_cosechada_promedio=(
            "area_cosechada_num",
            "mean"
        ),
        produccion_promedio=(
            "produccion_num",
            "mean"
        ),
        rendimiento_promedio=(
            "rendimiento_num",
            "mean"
        )
    )
)

print(
    resumen_met.to_string(
        index=False
    )
)

resumen_met.to_csv(
    OUTPUT_DIR / "06_cambio_metodologico_resumen.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 5. PERÍODOS ANUALES VS SEMESTRALES
# ============================================================

print("\n" + "=" * 75)
print("5. PERÍODOS ANUALES VS SEMESTRALES")
print("=" * 75)

df_periodos = pd.concat(
    datos_periodos,
    ignore_index=True
)

resumen_tipo_periodo = (
    df_periodos
    .groupby(
        [
            "Año",
            "tipo_periodo"
        ],
        as_index=False
    )
    .agg(
        registros=("Año", "size"),
        area_sembrada_promedio=(
            "area_sembrada_num",
            "mean"
        ),
        area_cosechada_promedio=(
            "area_cosechada_num",
            "mean"
        ),
        produccion_promedio=(
            "produccion_num",
            "mean"
        ),
        rendimiento_promedio=(
            "rendimiento_num",
            "mean"
        )
    )
)

print(
    resumen_tipo_periodo.to_string(
        index=False
    )
)

resumen_tipo_periodo.to_csv(
    OUTPUT_DIR / "07_anual_vs_semestral.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 75)
print("FASE 3.1 FINALIZADA")
print("=" * 75)

print(
    f"\nArchivos generados en: {OUTPUT_DIR}"
)