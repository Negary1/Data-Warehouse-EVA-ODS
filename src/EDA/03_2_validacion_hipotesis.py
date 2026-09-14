import os
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT_FILE = (
    "data/raw/"
    "Evaluaciones_Agropecuarias_Municipales_–_EVA._2019_-_2025._"
    "Base_Agrícola_20260905.csv"
)

OUTPUT_DIR = "data/profiling/fase_3_2"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# CONVERSIÓN NUMÉRICA EVA
# ============================================================

def convertir_numero_eva(serie):
    """
    Convierte formatos como:

        8,00       -> 8.00
        127,44     -> 127.44
        9.217,00   -> 9217.00

    También permite valores que ya vengan como números.
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


# ============================================================
# ACUMULADORES
# ============================================================

registros_mayor = []
casos_sembrada_cero = []

comparacion_anual = []
resumen_anual = []

# Para evitar cargar todo el dataset de una sola vez
chunksize = 50000


# ============================================================
# PROCESAMIENTO
# ============================================================

for chunk in pd.read_csv(
    INPUT_FILE,
    sep=",",
    dtype=str,
    chunksize=chunksize,
    encoding="utf-8"
):

    # --------------------------------------------------------
    # Conversión de métricas
    # --------------------------------------------------------

    chunk["area_sembrada_num"] = convertir_numero_eva(
        chunk["Área sembrada"]
    )

    chunk["area_cosechada_num"] = convertir_numero_eva(
        chunk["Área cosechada"]
    )

    chunk["produccion_num"] = convertir_numero_eva(
        chunk["Producción"]
    )

    chunk["rendimiento_num"] = convertir_numero_eva(
        chunk["Rendimiento"]
    )

    chunk["Año_num"] = pd.to_numeric(
        chunk["Año"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # 1. ÁREA COSECHADA > ÁREA SEMBRADA
    # --------------------------------------------------------

    condicion_mayor = (
        chunk["area_cosechada_num"]
        > chunk["area_sembrada_num"]
    )

    temp = chunk.loc[
        condicion_mayor,
        [
            "Código Dane departamento",
            "Departamento",
            "Código Dane municipio",
            "Municipio",
            "Grupo cultivo",
            "Subgrupo",
            "Cultivo",
            "Desagregación cultivo",
            "Año",
            "Periodo",
            "Ciclo del cultivo",
            "Área sembrada",
            "Área cosechada",
            "Producción",
            "Rendimiento",
            "Código del cultivo"
        ]
    ].copy()

    temp["area_sembrada_num"] = convertir_numero_eva(
        temp["Área sembrada"]
    )

    temp["area_cosechada_num"] = convertir_numero_eva(
        temp["Área cosechada"]
    )

    temp["diferencia_ha"] = (
        temp["area_cosechada_num"]
        - temp["area_sembrada_num"]
    )

    temp["ratio_cosechada_sembrada"] = np.where(
        temp["area_sembrada_num"] > 0,
        temp["area_cosechada_num"]
        / temp["area_sembrada_num"],
        np.inf
    )

    registros_mayor.append(temp)

    # --------------------------------------------------------
    # 2. ÁREA SEMBRADA = 0 Y ÁREA COSECHADA > 0
    # --------------------------------------------------------

    condicion_cero = (
        (chunk["area_sembrada_num"] == 0)
        &
        (chunk["area_cosechada_num"] > 0)
    )

    temp_cero = chunk.loc[
        condicion_cero,
        [
            "Código Dane departamento",
            "Departamento",
            "Código Dane municipio",
            "Municipio",
            "Grupo cultivo",
            "Subgrupo",
            "Cultivo",
            "Desagregación cultivo",
            "Año",
            "Periodo",
            "Ciclo del cultivo",
            "Área sembrada",
            "Área cosechada",
            "Producción",
            "Rendimiento",
            "Código del cultivo"
        ]
    ].copy()

    temp_cero["area_sembrada_num"] = convertir_numero_eva(
        temp_cero["Área sembrada"]
    )

    temp_cero["area_cosechada_num"] = convertir_numero_eva(
        temp_cero["Área cosechada"]
    )

    temp_cero["produccion_num"] = convertir_numero_eva(
        temp_cero["Producción"]
    )

    temp_cero["rendimiento_num"] = convertir_numero_eva(
        temp_cero["Rendimiento"]
    )

    casos_sembrada_cero.append(temp_cero)

    # --------------------------------------------------------
    # 3. PREPARACIÓN PARA COMPARAR ANUAL VS SEMESTRAL
    # --------------------------------------------------------

    temp_periodos = chunk[
        [
            "Código Dane municipio",
            "Código del cultivo",
            "Cultivo",
            "Año",
            "Periodo",
            "Área sembrada",
            "Área cosechada",
            "Producción",
            "Rendimiento"
        ]
    ].copy()

    temp_periodos["area_sembrada_num"] = convertir_numero_eva(
        temp_periodos["Área sembrada"]
    )

    temp_periodos["area_cosechada_num"] = convertir_numero_eva(
        temp_periodos["Área cosechada"]
    )

    temp_periodos["produccion_num"] = convertir_numero_eva(
        temp_periodos["Producción"]
    )

    temp_periodos["rendimiento_num"] = convertir_numero_eva(
        temp_periodos["Rendimiento"]
    )

    temp_periodos["Año_num"] = pd.to_numeric(
        temp_periodos["Año"],
        errors="coerce"
    )

    # Solo registros semestrales
    temp_sem = temp_periodos[
        temp_periodos["Periodo"].str.endswith(("A", "B"))
    ].copy()

    temp_sem["tipo_semestre"] = temp_sem["Periodo"].str[-1]

    # Solo registros anuales
    temp_anual = temp_periodos[
        ~temp_periodos["Periodo"].str.endswith(("A", "B"))
    ].copy()

    # --------------------------------------------------------
    # Agrupación de semestres
    # --------------------------------------------------------

    if not temp_sem.empty:

        sem_group = (
            temp_sem
            .groupby(
                [
                    "Código Dane municipio",
                    "Código del cultivo",
                    "Cultivo",
                    "Año_num"
                ],
                dropna=False
            )
            .agg(
                registros_semestres=("Periodo", "count"),
                area_sembrada_A_B=("area_sembrada_num", "sum"),
                area_cosechada_A_B=("area_cosechada_num", "sum"),
                produccion_A_B=("produccion_num", "sum")
            )
            .reset_index()
        )

        # ----------------------------------------------------
        # Unión con anual
        # ----------------------------------------------------

        if not temp_anual.empty:

            anual_group = (
                temp_anual
                .groupby(
                    [
                        "Código Dane municipio",
                        "Código del cultivo",
                        "Cultivo",
                        "Año_num"
                    ],
                    dropna=False
                )
                .agg(
                    registros_anuales=("Periodo", "count"),
                    area_sembrada_anual=("area_sembrada_num", "mean"),
                    area_cosechada_anual=("area_cosechada_num", "mean"),
                    produccion_anual=("produccion_num", "mean"),
                    rendimiento_anual=("rendimiento_num", "mean")
                )
                .reset_index()
            )

            comparacion = sem_group.merge(
                anual_group,
                on=[
                    "Código Dane municipio",
                    "Código del cultivo",
                    "Cultivo",
                    "Año_num"
                ],
                how="inner"
            )

            # Diferencias
            comparacion["dif_area_sembrada"] = (
                comparacion["area_sembrada_anual"]
                - comparacion["area_sembrada_A_B"]
            )

            comparacion["dif_area_cosechada"] = (
                comparacion["area_cosechada_anual"]
                - comparacion["area_cosechada_A_B"]
            )

            comparacion["dif_produccion"] = (
                comparacion["produccion_anual"]
                - comparacion["produccion_A_B"]
            )

            # Ratios anual / A+B
            comparacion["ratio_area_sembrada"] = np.where(
                comparacion["area_sembrada_A_B"] != 0,
                comparacion["area_sembrada_anual"]
                / comparacion["area_sembrada_A_B"],
                np.nan
            )

            comparacion["ratio_area_cosechada"] = np.where(
                comparacion["area_cosechada_A_B"] != 0,
                comparacion["area_cosechada_anual"]
                / comparacion["area_cosechada_A_B"],
                np.nan
            )

            comparacion["ratio_produccion"] = np.where(
                comparacion["produccion_A_B"] != 0,
                comparacion["produccion_anual"]
                / comparacion["produccion_A_B"],
                np.nan
            )

            comparacion_anual.append(comparacion)


# ============================================================
# 1. GUARDAR CASOS ÁREA COSECHADA > SEMBRADA
# ============================================================

if registros_mayor:

    df_mayor = pd.concat(
        registros_mayor,
        ignore_index=True
    )

    df_mayor.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "01_area_cosechada_mayor_detalle.csv"
        ),
        index=False,
        encoding="utf-8-sig"
    )

    # Resumen por año
    resumen_anio = (
        df_mayor
        .groupby("Año")
        .agg(
            registros=("Cultivo", "size"),
            diferencia_promedio_ha=("diferencia_ha", "mean"),
            diferencia_mediana_ha=("diferencia_ha", "median"),
            ratio_mediano=("ratio_cosechada_sembrada", "median")
        )
        .reset_index()
    )

    resumen_anio.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "02_area_mayor_por_anio.csv"
        ),
        index=False,
        encoding="utf-8-sig"
    )

    # Resumen por ciclo
    resumen_ciclo = (
        df_mayor
        .groupby("Ciclo del cultivo")
        .agg(
            registros=("Cultivo", "size"),
            diferencia_promedio_ha=("diferencia_ha", "mean"),
            diferencia_mediana_ha=("diferencia_ha", "median"),
            ratio_mediano=("ratio_cosechada_sembrada", "median")
        )
        .reset_index()
    )

    resumen_ciclo.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "03_area_mayor_por_ciclo.csv"
        ),
        index=False,
        encoding="utf-8-sig"
    )


# ============================================================
# 2. CASOS SEMBRADA = 0 Y COSECHADA > 0
# ============================================================

if casos_sembrada_cero:

    df_cero = pd.concat(
        casos_sembrada_cero,
        ignore_index=True
    )

    df_cero.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "04_sembrada_cero_cosechada_mayor_cero.csv"
        ),
        index=False,
        encoding="utf-8-sig"
    )

    resumen_cero = (
        df_cero
        .groupby(
            ["Año", "Ciclo del cultivo"],
            dropna=False
        )
        .agg(
            registros=("Cultivo", "size"),
            cosechada_promedio=("area_cosechada_num", "mean"),
            produccion_promedio=("produccion_num", "mean"),
            rendimiento_promedio=("rendimiento_num", "mean")
        )
        .reset_index()
    )

    resumen_cero.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "05_sembrada_cero_resumen.csv"
        ),
        index=False,
        encoding="utf-8-sig"
    )


# ============================================================
# 3. COMPARACIÓN ANUAL VS A+B
# ============================================================

if comparacion_anual:

    df_comparacion = pd.concat(
        comparacion_anual,
        ignore_index=True
    )

    df_comparacion.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "06_anual_vs_A_mas_B_detalle.csv"
        ),
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Resumen general
    # --------------------------------------------------------

    resumen = pd.DataFrame({
        "metrica": [
            "Área sembrada",
            "Área cosechada",
            "Producción"
        ],
        "promedio_ratio_anual_vs_A_B": [
            df_comparacion["ratio_area_sembrada"].mean(),
            df_comparacion["ratio_area_cosechada"].mean(),
            df_comparacion["ratio_produccion"].mean()
        ],
        "mediana_ratio_anual_vs_A_B": [
            df_comparacion["ratio_area_sembrada"].median(),
            df_comparacion["ratio_area_cosechada"].median(),
            df_comparacion["ratio_produccion"].median()
        ]
    })

    resumen.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "07_anual_vs_A_mas_B_resumen.csv"
        ),
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # ¿Qué tan cerca está el anual de A+B?
    # --------------------------------------------------------

    tolerancias = [0.01, 0.05, 0.10]

    resultados_tolerancia = []

    for tolerancia in tolerancias:

        resultados_tolerancia.append({
            "tolerancia": tolerancia,
            "area_sembrada_pct": (
                (
                    df_comparacion["ratio_area_sembrada"]
                    .between(
                        1 - tolerancia,
                        1 + tolerancia
                    )
                ).mean() * 100
            ),
            "area_cosechada_pct": (
                (
                    df_comparacion["ratio_area_cosechada"]
                    .between(
                        1 - tolerancia,
                        1 + tolerancia
                    )
                ).mean() * 100
            ),
            "produccion_pct": (
                (
                    df_comparacion["ratio_produccion"]
                    .between(
                        1 - tolerancia,
                        1 + tolerancia
                    )
                ).mean() * 100
            )
        })

    pd.DataFrame(
        resultados_tolerancia
    ).to_csv(
        os.path.join(
            OUTPUT_DIR,
            "08_coincidencia_anual_A_B.csv"
        ),
        index=False,
        encoding="utf-8-sig"
    )


# ============================================================
# FINAL
# ============================================================

print("=" * 70)
print("FASE 3.2 FINALIZADA")
print("=" * 70)
print(f"Archivos generados en: {OUTPUT_DIR}")