import os
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

CSV_PATH = (
    "data/raw/"
    "Evaluaciones_Agropecuarias_Municipales_–_EVA._2019_-_2025._"
    "Base_Agrícola_20260905.csv"
)

OUTPUT_DIR = "exploracion_fase_2"

CHUNK_SIZE = 50_000


# ============================================================
# COLUMNAS
# ============================================================

NUMERIC_COLUMNS = [
    "Área sembrada",
    "Área cosechada",
    "Producción",
    "Rendimiento"
]

GEOGRAPHIC_COLUMNS = [
    "Código Dane departamento",
    "Departamento",
    "Código Dane municipio",
    "Municipio"
]

AGRICULTURAL_COLUMNS = [
    "Grupo cultivo",
    "Subgrupo",
    "Cultivo",
    "Desagregación cultivo",
    "Código del cultivo",
    "Nombre científico del cultivo"
]


# ============================================================
# PREPARACIÓN
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 75)
print("FASE 2 - PERFILAMIENTO ANALÍTICO Y SEMÁNTICO DEL DATASET EVA")
print("=" * 75)


if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(
        f"No se encontró el archivo:\n{CSV_PATH}"
    )


# ============================================================
# FUNCIÓN DE CONVERSIÓN NUMÉRICA
# ============================================================

def convertir_numerico(serie):
    """
    Convierte valores como:

        '127,44'
        '8,00'
        '0,30'

    a números reales.

    La conversión se realiza únicamente en memoria.
    """

    return pd.to_numeric(
        serie.astype("string")
        .str.strip()
        .str.replace(",", ".", regex=False),
        errors="coerce"
    )


# ============================================================
# 1. PERFILAMIENTO DE MÉTRICAS
# ============================================================

print("\n" + "=" * 75)
print("1. PERFILAMIENTO DE MÉTRICAS")
print("=" * 75)


metric_data = {
    column: []
    for column in NUMERIC_COLUMNS
}

conversion_errors = {
    column: 0
    for column in NUMERIC_COLUMNS
}


for chunk in pd.read_csv(
    CSV_PATH,
    sep=",",
    encoding="utf-8-sig",
    chunksize=CHUNK_SIZE,
    dtype=str
):

    for column in NUMERIC_COLUMNS:

        original = chunk[column]

        converted = convertir_numerico(original)

        invalid = (
            original.notna()
            & converted.isna()
        )

        conversion_errors[column] += invalid.sum()

        metric_data[column].extend(
            converted.dropna().tolist()
        )


metric_rows = []


for column, values in metric_data.items():

    series = pd.Series(values, dtype="float64")

    row = {
        "columna": column,
        "cantidad": len(series),
        "conversiones_fallidas": conversion_errors[column],
        "minimo": series.min(),
        "maximo": series.max(),
        "media": series.mean(),
        "mediana": series.median(),
        "desviacion_estandar": series.std(),
        "p1": series.quantile(0.01),
        "q1": series.quantile(0.25),
        "q3": series.quantile(0.75),
        "p99": series.quantile(0.99),
        "ceros": int((series == 0).sum()),
        "negativos": int((series < 0).sum())
    }

    metric_rows.append(row)

    print(f"\n{column}")
    print(f"  Cantidad:              {row['cantidad']:,}")
    print(f"  Conversiones fallidas: {row['conversiones_fallidas']:,}")
    print(f"  Mínimo:               {row['minimo']}")
    print(f"  Máximo:               {row['maximo']}")
    print(f"  Media:                {row['media']:.4f}")
    print(f"  Mediana:              {row['mediana']:.4f}")
    print(f"  Desv. estándar:       {row['desviacion_estandar']:.4f}")
    print(f"  P1:                   {row['p1']:.4f}")
    print(f"  Q1:                   {row['q1']:.4f}")
    print(f"  Q3:                   {row['q3']:.4f}")
    print(f"  P99:                  {row['p99']:.4f}")
    print(f"  Ceros:                {row['ceros']:,}")
    print(f"  Negativos:            {row['negativos']:,}")


pd.DataFrame(metric_rows).to_csv(
    os.path.join(
        OUTPUT_DIR,
        "metricas_estadisticas.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 2. PERFILAMIENTO TEMPORAL
# ============================================================

print("\n" + "=" * 75)
print("2. PERFILAMIENTO TEMPORAL")
print("=" * 75)


temporal_data = []

for chunk in pd.read_csv(
    CSV_PATH,
    sep=",",
    encoding="utf-8-sig",
    chunksize=CHUNK_SIZE,
    dtype=str
):

    temporal_data.append(
        chunk[
            [
                "Año",
                "Periodo"
            ]
        ]
    )


temporal_df = pd.concat(
    temporal_data,
    ignore_index=True
)

temporal_df["Año"] = pd.to_numeric(
    temporal_df["Año"],
    errors="coerce"
)

print("\nValores de Periodo:")

period_counts = (
    temporal_df["Periodo"]
    .value_counts()
    .sort_index()
)

for period, count in period_counts.items():

    print(
        f"  {period}: {count:,}"
    )


period_summary = (
    temporal_df
    .groupby(["Año", "Periodo"])
    .size()
    .reset_index(name="registros")
    .sort_values(["Año", "Periodo"])
)

period_summary.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "distribucion_temporal.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 3. VALIDACIÓN AÑO VS PERIODO
# ============================================================

print("\n" + "=" * 75)
print("3. VALIDACIÓN AÑO VS PERIODO")
print("=" * 75)


temporal_df["Año_periodo_extraido"] = pd.to_numeric(
    temporal_df["Periodo"]
    .astype("string")
    .str.extract(r"^(\d{4})")[0],
    errors="coerce"
)


temporal_df["periodo_coincide"] = (
    temporal_df["Año"]
    ==
    temporal_df["Año_periodo_extraido"]
)


inconsistencias_temporales = (
    ~temporal_df["periodo_coincide"]
).sum()


print(
    f"Registros con inconsistencia Año/Periodo: "
    f"{inconsistencias_temporales:,}"
)


# ============================================================
# 4. PERFILAMIENTO GEOGRÁFICO
# ============================================================

print("\n" + "=" * 75)
print("4. VALIDACIÓN GEOGRÁFICA")
print("=" * 75)


geo_data = []

for chunk in pd.read_csv(
    CSV_PATH,
    sep=",",
    encoding="utf-8-sig",
    chunksize=CHUNK_SIZE,
    dtype=str
):

    geo_data.append(
        chunk[GEOGRAPHIC_COLUMNS]
    )


geo_df = pd.concat(
    geo_data,
    ignore_index=True
)


# ------------------------------------------------------------
# Código departamento → múltiples nombres
# ------------------------------------------------------------

dept_code_names = (
    geo_df
    .groupby("Código Dane departamento")["Departamento"]
    .nunique()
)

dept_inconsistent = (
    dept_code_names[dept_code_names > 1]
)


# ------------------------------------------------------------
# Código municipio → múltiples nombres
# ------------------------------------------------------------

mun_code_names = (
    geo_df
    .groupby("Código Dane municipio")["Municipio"]
    .nunique()
)

mun_inconsistent = (
    mun_code_names[mun_code_names > 1]
)


# ------------------------------------------------------------
# Municipio → múltiples códigos
# ------------------------------------------------------------

mun_name_codes = (
    geo_df
    .groupby("Municipio")["Código Dane municipio"]
    .nunique()
)

mun_name_multiple_codes = (
    mun_name_codes[mun_name_codes > 1]
)


print(
    "Códigos de departamento con múltiples nombres: "
    f"{len(dept_inconsistent)}"
)

print(
    "Códigos de municipio con múltiples nombres: "
    f"{len(mun_inconsistent)}"
)

print(
    "Nombres de municipio con múltiples códigos: "
    f"{len(mun_name_multiple_codes)}"
)


# Guardar inconsistencias

geo_issues = []

for code in dept_inconsistent.index:

    names = (
        geo_df[
            geo_df["Código Dane departamento"] == code
        ]["Departamento"]
        .drop_duplicates()
        .tolist()
    )

    geo_issues.append({
        "tipo": "departamento_codigo_multiples_nombres",
        "codigo": code,
        "valor": " | ".join(names)
    })


for code in mun_inconsistent.index:

    names = (
        geo_df[
            geo_df["Código Dane municipio"] == code
        ]["Municipio"]
        .drop_duplicates()
        .tolist()
    )

    geo_issues.append({
        "tipo": "municipio_codigo_multiples_nombres",
        "codigo": code,
        "valor": " | ".join(names)
    })


for name in mun_name_multiple_codes.index:

    codes = (
        geo_df[
            geo_df["Municipio"] == name
        ]["Código Dane municipio"]
        .drop_duplicates()
        .tolist()
    )

    geo_issues.append({
        "tipo": "municipio_nombre_multiples_codigos",
        "codigo": " | ".join(codes),
        "valor": name
    })


pd.DataFrame(geo_issues).to_csv(
    os.path.join(
        OUTPUT_DIR,
        "problemas_geograficos.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 5. VALIDACIÓN JERARQUÍA AGRÍCOLA
# ============================================================

print("\n" + "=" * 75)
print("5. VALIDACIÓN DE JERARQUÍA AGRÍCOLA")
print("=" * 75)


agri_data = []

for chunk in pd.read_csv(
    CSV_PATH,
    sep=",",
    encoding="utf-8-sig",
    chunksize=CHUNK_SIZE,
    dtype=str
):

    agri_data.append(
        chunk[AGRICULTURAL_COLUMNS]
    )


agri_df = pd.concat(
    agri_data,
    ignore_index=True
)


def analizar_relacion(df, columna_origen, columna_destino):

    relation = (
        df
        .groupby(columna_origen)[columna_destino]
        .nunique()
    )

    problematic = relation[relation > 1]

    print(
        f"\n{columna_origen} → {columna_destino}"
    )

    print(
        f"  Valores origen: {relation.shape[0]:,}"
    )

    print(
        f"  Orígenes con múltiples destinos: "
        f"{len(problematic):,}"
    )

    return problematic


# Relaciones que queremos estudiar

relations = [
    ("Código del cultivo", "Desagregación cultivo"),
    ("Desagregación cultivo", "Código del cultivo"),
    ("Desagregación cultivo", "Cultivo"),
    ("Cultivo", "Grupo cultivo"),
    ("Cultivo", "Subgrupo"),
    ("Código del cultivo", "Nombre científico del cultivo"),
    ("Desagregación cultivo", "Nombre científico del cultivo"),
]


agri_issues = []


for source, target in relations:

    problematic = analizar_relacion(
        agri_df,
        source,
        target
    )

    for value, count in problematic.items():

        destinations = (
            agri_df[
                agri_df[source] == value
            ][target]
            .drop_duplicates()
            .tolist()
        )

        agri_issues.append({
            "origen": source,
            "valor_origen": value,
            "destino": target,
            "cantidad_destinos": count,
            "valores_destino": " | ".join(destinations)
        })


pd.DataFrame(agri_issues).to_csv(
    os.path.join(
        OUTPUT_DIR,
        "problemas_jerarquia_agricola.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 6. DISTRIBUCIÓN POR CICLO
# ============================================================

print("\n" + "=" * 75)
print("6. CICLO DEL CULTIVO")
print("=" * 75)


cycle_counts = (
    agri_df["Código del cultivo"]
    .to_frame()
    .join(
        pd.read_csv(
            CSV_PATH,
            sep=",",
            encoding="utf-8-sig",
            usecols=["Ciclo del cultivo"],
            dtype=str
        )
    )
)


# Lectura directa para evitar depender de índices

cycle_data = []

for chunk in pd.read_csv(
    CSV_PATH,
    sep=",",
    encoding="utf-8-sig",
    chunksize=CHUNK_SIZE,
    dtype=str
):

    cycle_data.append(
        chunk[
            [
                "Código del cultivo",
                "Ciclo del cultivo"
            ]
        ]
    )


cycle_df = pd.concat(
    cycle_data,
    ignore_index=True
)


cycle_summary = (
    cycle_df["Ciclo del cultivo"]
    .value_counts()
)

for cycle, count in cycle_summary.items():

    print(
        f"  {cycle}: {count:,}"
    )


cycle_summary.rename(
    "registros"
).reset_index(
    name="ciclo"
).to_csv(
    os.path.join(
        OUTPUT_DIR,
        "distribucion_ciclos.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 7. ESTADOS FÍSICOS
# ============================================================

print("\n" + "=" * 75)
print("7. ESTADO FÍSICO DEL CULTIVO")
print("=" * 75)


physical_data = []

for chunk in pd.read_csv(
    CSV_PATH,
    sep=",",
    encoding="utf-8-sig",
    chunksize=CHUNK_SIZE,
    dtype=str
):

    physical_data.append(
        chunk[
            [
                "Estado físico del cultivo",
                "Código del cultivo"
            ]
        ]
    )


physical_df = pd.concat(
    physical_data,
    ignore_index=True
)


physical_summary = (
    physical_df["Estado físico del cultivo"]
    .value_counts()
)

for state, count in physical_summary.items():

    print(
        f"  {state}: {count:,}"
    )


physical_summary.rename(
    "registros"
).reset_index(
    name="estado_fisico"
).to_csv(
    os.path.join(
        OUTPUT_DIR,
        "distribucion_estado_fisico.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 8. PRIMERA INVESTIGACIÓN DE GRANULARIDAD
# ============================================================

print("\n" + "=" * 75)
print("8. PRIMERA INVESTIGACIÓN DE GRANULARIDAD")
print("=" * 75)


grain_columns = [
    "Código Dane municipio",
    "Código del cultivo",
    "Año",
    "Periodo"
]


grain_data = []

for chunk in pd.read_csv(
    CSV_PATH,
    sep=",",
    encoding="utf-8-sig",
    chunksize=CHUNK_SIZE,
    dtype=str
):

    grain_data.append(
        chunk[grain_columns]
    )


grain_df = pd.concat(
    grain_data,
    ignore_index=True
)


candidate_counts = (
    grain_df
    .groupby(grain_columns)
    .size()
)


duplicated_candidates = (
    candidate_counts[candidate_counts > 1]
)


print(
    "Combinación candidata:"
)

print(
    "Código municipio + Código cultivo + Año + Periodo"
)

print(
    f"Combinaciones únicas: "
    f"{candidate_counts.shape[0]:,}"
)

print(
    f"Combinaciones repetidas: "
    f"{len(duplicated_candidates):,}"
)

print(
    f"Registros involucrados en repeticiones: "
    f"{duplicated_candidates.sum():,}"
)


# ============================================================
# 9. GRANULARIDAD CON DESAGREGACIÓN
# ============================================================

grain_columns_2 = [
    "Código Dane municipio",
    "Código del cultivo",
    "Desagregación cultivo",
    "Año",
    "Periodo"
]


grain_data_2 = []

for chunk in pd.read_csv(
    CSV_PATH,
    sep=",",
    encoding="utf-8-sig",
    chunksize=CHUNK_SIZE,
    dtype=str
):

    grain_data_2.append(
        chunk[grain_columns_2]
    )


grain_df_2 = pd.concat(
    grain_data_2,
    ignore_index=True
)


candidate_counts_2 = (
    grain_df_2
    .groupby(grain_columns_2)
    .size()
)


duplicated_candidates_2 = (
    candidate_counts_2[
        candidate_counts_2 > 1
    ]
)


print("\nSegunda combinación candidata:")

print(
    "Código municipio + Código cultivo + "
    "Desagregación + Año + Periodo"
)

print(
    f"Combinaciones únicas: "
    f"{candidate_counts_2.shape[0]:,}"
)

print(
    f"Combinaciones repetidas: "
    f"{len(duplicated_candidates_2):,}"
)


# ============================================================
# 10. RESUMEN
# ============================================================

print("\n" + "=" * 75)
print("FASE 2 FINALIZADA")
print("=" * 75)

