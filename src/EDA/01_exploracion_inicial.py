import csv
import os
from collections import Counter

import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

CSV_PATH = "data/raw/Evaluaciones_Agropecuarias_Municipales_–_EVA._2019_-_2025._Base_Agrícola_20260905.csv"
OUTPUT_DIR = "exploracion_fase_1"

# Tamaño de cada bloque leído.
# Permite trabajar con archivos grandes sin cargar todo en memoria.
CHUNK_SIZE = 50_000

# Cantidad de valores de ejemplo que mostraremos
SAMPLE_VALUES = 10


# ============================================================
# PREPARACIÓN
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# 1. DETECCIÓN BÁSICA DEL ARCHIVO
# ============================================================

print("=" * 70)
print("FASE 1 - EXPLORACIÓN INICIAL DEL DATASET EVA")
print("=" * 70)

print(f"\nArchivo: {CSV_PATH}")

if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(
        f"No se encontró el archivo: {CSV_PATH}"
    )

file_size_mb = os.path.getsize(CSV_PATH) / (1024 * 1024)

print(f"Tamaño: {file_size_mb:,.2f} MB")


# ============================================================
# 2. LECTURA DEL ENCABEZADO
# ============================================================

with open(
    CSV_PATH,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    sample = file.read(10_000)

    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=",;\t|"
        )

        delimiter = dialect.delimiter

    except csv.Error:
        delimiter = ","

print(f"Separador detectado: {repr(delimiter)}")


# Obtener columnas
with open(
    CSV_PATH,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    reader = csv.reader(file, delimiter=delimiter)
    columns = next(reader)

print(f"\nNúmero de columnas: {len(columns)}")

print("\nCOLUMNAS")
print("-" * 70)

for i, column in enumerate(columns, start=1):
    print(f"{i:2}. {column}")


# ============================================================
# 3. ESTRUCTURAS PARA EL PERFILAMIENTO
# ============================================================

row_count = 0

null_counts = Counter()
empty_counts = Counter()

unique_values = {
    column: set()
    for column in columns
}

sample_values = {
    column: []
    for column in columns
}

exact_row_counter = Counter()

numeric_columns = []

numeric_stats = {}


# ============================================================
# 4. LECTURA POR CHUNKS
# ============================================================

print("\n" + "=" * 70)
print("LECTURA Y PERFILAMIENTO")
print("=" * 70)

chunk_number = 0

for chunk in pd.read_csv(
    CSV_PATH,
    sep=delimiter,
    encoding="utf-8-sig",
    chunksize=CHUNK_SIZE,
    low_memory=False
):

    chunk_number += 1

    row_count += len(chunk)

    print(
        f"Procesando bloque {chunk_number} "
        f"| registros acumulados: {row_count:,}"
    )

    # --------------------------------------------------------
    # Normalización temporal SOLO para perfilamiento
    # --------------------------------------------------------

    # No estamos modificando el dataset.
    # Simplemente eliminamos espacios externos para poder
    # detectar mejor valores vacíos.
    for column in columns:

        series = chunk[column]

        # Nulos reales
        null_counts[column] += series.isna().sum()

        # Valores vacíos
        empty_counts[column] += (
            series.astype("string")
            .str.strip()
            .eq("")
            .sum()
        )

        # Valores únicos
        #
        # Se convierten temporalmente a string para evitar
        # problemas entre NaN, números y strings.
        values = (
            series.dropna()
            .astype(str)
            .str.strip()
        )

        unique_values[column].update(values.unique())

        # Muestra de valores
        if len(sample_values[column]) < SAMPLE_VALUES:

            for value in values.unique():

                if value not in sample_values[column]:

                    sample_values[column].append(value)

                    if len(sample_values[column]) >= SAMPLE_VALUES:
                        break

    # --------------------------------------------------------
    # Duplicados exactos
    # --------------------------------------------------------

    for row in chunk.itertuples(
        index=False,
        name=None
    ):
        exact_row_counter[row] += 1


# ============================================================
# 5. RESUMEN ESTRUCTURAL
# ============================================================

print("\n" + "=" * 70)
print("RESUMEN ESTRUCTURAL")
print("=" * 70)

print(f"Registros: {row_count:,}")
print(f"Columnas:  {len(columns):,}")


# ============================================================
# 6. TIPOS DE DATOS
# ============================================================

print("\n" + "=" * 70)
print("TIPOS DE DATOS")
print("=" * 70)

# Tomamos una muestra para inferir tipos.
sample_df = pd.read_csv(
    CSV_PATH,
    sep=delimiter,
    encoding="utf-8-sig",
    nrows=10_000,
    low_memory=False
)

dtype_rows = []

for column in columns:

    dtype = str(sample_df[column].dtype)

    dtype_rows.append({
        "columna": column,
        "tipo_pandas": dtype
    })

    print(
        f"{column:<35} {dtype}"
    )

dtype_df = pd.DataFrame(dtype_rows)

dtype_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "tipos_datos.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 7. NULOS Y VACÍOS
# ============================================================

print("\n" + "=" * 70)
print("NULOS Y VALORES VACÍOS")
print("=" * 70)

quality_rows = []

for column in columns:

    null_count = null_counts[column]
    empty_count = empty_counts[column]

    null_pct = (
        null_count / row_count * 100
        if row_count > 0
        else 0
    )

    empty_pct = (
        empty_count / row_count * 100
        if row_count > 0
        else 0
    )

    quality_rows.append({
        "columna": column,
        "nulos": null_count,
        "porcentaje_nulos": round(null_pct, 4),
        "vacios": empty_count,
        "porcentaje_vacios": round(empty_pct, 4)
    })

    print(
        f"{column:<35} "
        f"Nulos: {null_count:>8,} "
        f"({null_pct:>7.3f}%) "
        f"Vacíos: {empty_count:>8,}"
    )

quality_df = pd.DataFrame(quality_rows)

quality_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "calidad_nulos_vacios.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 8. CARDINALIDAD
# ============================================================

print("\n" + "=" * 70)
print("CARDINALIDAD")
print("=" * 70)

cardinality_rows = []

for column in columns:

    count_unique = len(unique_values[column])

    cardinality_rows.append({
        "columna": column,
        "valores_unicos": count_unique
    })

    print(
        f"{column:<35} "
        f"{count_unique:>10,}"
    )

cardinality_df = pd.DataFrame(cardinality_rows)

cardinality_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "cardinalidad.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 9. VALORES DE EJEMPLO
# ============================================================

print("\n" + "=" * 70)
print("VALORES DE EJEMPLO")
print("=" * 70)

sample_rows = []

for column in columns:

    values = sample_values[column]

    print(f"\n{column}")

    for value in values:
        print(f"  - {value}")

    sample_rows.append({
        "columna": column,
        "ejemplos": " | ".join(values)
    })

samples_df = pd.DataFrame(sample_rows)

samples_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "valores_ejemplo.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 10. DUPLICADOS EXACTOS
# ============================================================

print("\n" + "=" * 70)
print("DUPLICADOS EXACTOS")
print("=" * 70)

duplicate_rows = sum(
    count - 1
    for count in exact_row_counter.values()
    if count > 1
)

duplicate_groups = sum(
    1
    for count in exact_row_counter.values()
    if count > 1
)

print(
    f"Grupos de registros duplicados: "
    f"{duplicate_groups:,}"
)

print(
    f"Registros duplicados: "
    f"{duplicate_rows:,}"
)

duplicate_summary = pd.DataFrame([{
    "registros_totales": row_count,
    "grupos_duplicados": duplicate_groups,
    "registros_duplicados": duplicate_rows
}])

duplicate_summary.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "duplicados_exactos.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 11. ESTADÍSTICAS NUMÉRICAS
# ============================================================

print("\n" + "=" * 70)
print("ESTADÍSTICAS NUMÉRICAS")
print("=" * 70)

# Volvemos a recorrer el archivo porque esta fase busca
# mantener cada proceso sencillo y explícito.

numeric_data = {}

for chunk in pd.read_csv(
    CSV_PATH,
    sep=delimiter,
    encoding="utf-8-sig",
    chunksize=CHUNK_SIZE,
    low_memory=False
):

    for column in columns:

        converted = pd.to_numeric(
            chunk[column],
            errors="coerce"
        )

        valid_count = converted.notna().sum()

        # Solo consideramos una columna numérica si
        # encontramos valores numéricos suficientes.
        if valid_count > 0:

            if column not in numeric_data:
                numeric_data[column] = []

            # Guardamos solamente para esta primera exploración.
            # Si el dataset resulta demasiado grande,
            # posteriormente sustituiremos esto por agregaciones
            # eficientes.
            numeric_data[column].extend(
                converted.dropna().tolist()
            )


for column, values in numeric_data.items():

    series = pd.Series(values)

    stats = {
        "columna": column,
        "cantidad": len(series),
        "minimo": series.min(),
        "maximo": series.max(),
        "media": series.mean(),
        "mediana": series.median(),
        "desviacion_estandar": series.std(),
        "q1": series.quantile(0.25),
        "q3": series.quantile(0.75),
        "ceros": (series == 0).sum(),
        "negativos": (series < 0).sum()
    }

    numeric_stats[column] = stats

    print(f"\n{column}")
    print(f"  Cantidad : {stats['cantidad']:,}")
    print(f"  Mínimo  : {stats['minimo']}")
    print(f"  Máximo  : {stats['maximo']}")
    print(f"  Media   : {stats['media']:.4f}")
    print(f"  Mediana : {stats['mediana']:.4f}")
    print(f"  Q1      : {stats['q1']:.4f}")
    print(f"  Q3      : {stats['q3']:.4f}")
    print(f"  Ceros   : {stats['ceros']:,}")
    print(f"  Negativos: {stats['negativos']:,}")


numeric_df = pd.DataFrame(
    numeric_stats.values()
)

numeric_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "estadisticas_numericas.csv"
    ),
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 12. RESUMEN FINAL
# ============================================================

print("\n" + "=" * 70)
print("EXPLORACIÓN FINALIZADA")
print("=" * 70)

print(f"""
Registros analizados : {row_count:,}
Columnas              : {len(columns)}
Duplicados exactos    : {duplicate_rows:,}

Resultados guardados en:

{OUTPUT_DIR}/
""")

print("""
Archivos generados:

- tipos_datos.csv
- calidad_nulos_vacios.csv
- cardinalidad.csv
- valores_ejemplo.csv
- duplicados_exactos.csv
- estadisticas_numericas.csv

IMPORTANTE:
Estos resultados son exclusivamente exploratorios.
Todavía NO se han realizado transformaciones ni limpieza.
""")