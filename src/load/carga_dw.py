from pathlib import Path
import os

import pandas as pd
from sqlalchemy import create_engine, text, URL


# ============================================================
# CONFIGURACIÓN
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

STAGING_PATH = (
    PROJECT_ROOT  / "data"    / "staging"     / "eva_agricola_staging.csv"
)

SQL_PATH = (
    PROJECT_ROOT
    / "sql"
    / "01_crear_esquema_dw.sql"
)

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Clon1789")

DATABASE_NAME = "dw_eva_agricola"

EXPECTED_STAGING_ROWS = 166_732
EXPECTED_GEOGRAFIA_ROWS = 1_103
EXPECTED_CULTIVO_ROWS = 194
EXPECTED_TIEMPO_ROWS = 21
EXPECTED_FACT_ROWS = 166_732

# ============================================================
# COLUMNAS ESPERADAS EN STAGING
# ============================================================

STAGING_COLUMNS = [
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
# CONEXIÓN
# ============================================================

def crear_engine(database=None):
    """
    Crea una conexión SQLAlchemy hacia MySQL.

    Si database=None, se conecta al servidor MySQL sin
    seleccionar una base de datos.
    """

    url = URL.create(
        drivername="mysql+pymysql",
        username=MYSQL_USER,
        password=MYSQL_PASSWORD,
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        database=database,
    )

    return create_engine(url, pool_pre_ping=True)


# ============================================================
# LECTURA DEL STAGING
# ============================================================

def cargar_staging():
    """
    Lee el archivo de staging preservando los códigos como texto.
    """

    print("\n[1] Leyendo staging...")

    dtype = {
        "codigo_departamento": "string",
        "departamento": "string",
        "codigo_municipio": "string",
        "municipio": "string",
        "grupo_cultivo": "string",
        "subgrupo": "string",
        "cultivo": "string",
        "desagregacion_cultivo": "string",
        "periodo": "string",
        "ciclo_cultivo": "string",
        "estado_fisico_cultivo": "string",
        "codigo_cultivo": "string",
        "nombre_cientifico": "string",
    }

    df = pd.read_csv(
        STAGING_PATH,
        dtype=dtype
    )

    print(f"    Registros leídos: {len(df):,}")
    print(f"    Columnas: {len(df.columns)}")

    return df


# ============================================================
# VALIDACIÓN DEL STAGING
# ============================================================

def validar_staging(df):
    """
    Validaciones mínimas antes de comenzar la carga.
    """

    print("\n[2] Validando staging...")

    # --------------------------------------------------------
    # Volumen
    # --------------------------------------------------------

    if len(df) != EXPECTED_STAGING_ROWS:
        raise ValueError(
            f"Volumen inesperado: {len(df):,}. "
            f"Se esperaban {EXPECTED_STAGING_ROWS:,}."
        )

    # --------------------------------------------------------
    # Estructura
    # --------------------------------------------------------

    if list(df.columns) != STAGING_COLUMNS:
        raise ValueError(
            "Las columnas del staging no coinciden "
            "con la estructura esperada."
        )

    # --------------------------------------------------------
    # Códigos
    # --------------------------------------------------------

    if df["codigo_departamento"].isna().any():
        raise ValueError("Existen códigos de departamento nulos.")

    if df["codigo_municipio"].isna().any():
        raise ValueError("Existen códigos de municipio nulos.")

    if df["codigo_cultivo"].isna().any():
        raise ValueError("Existen códigos de cultivo nulos.")

    if not (df["codigo_departamento"].str.len() == 2).all():
        raise ValueError(
            "Existen códigos de departamento que no tienen 2 caracteres."
        )

    if not (df["codigo_municipio"].str.len() == 5).all():
        raise ValueError(
            "Existen códigos de municipio que no tienen 5 caracteres."
        )

    # --------------------------------------------------------
    # Grain
    # --------------------------------------------------------

    grain = [
        "codigo_municipio",
        "codigo_cultivo",
        "anio",
        "periodo",
    ]

    duplicated = df.duplicated(
        subset=grain,
        keep=False
    )

    if duplicated.any():
        raise ValueError(
            f"Se encontraron {duplicated.sum():,} registros "
            "duplicados en el grain del negocio."
        )

    # --------------------------------------------------------
    # Métricas
    # --------------------------------------------------------

    metricas = [
        "area_sembrada",
        "area_cosechada",
        "produccion",
        "rendimiento",
    ]

    for columna in metricas:

        if df[columna].isna().any():
            raise ValueError(
                f"La métrica {columna} contiene valores nulos."
            )

        if (df[columna] < 0).any():
            raise ValueError(
                f"La métrica {columna} contiene valores negativos."
            )

    print("    ✓ Volumen correcto")
    print("    ✓ Estructura correcta")
    print("    ✓ Códigos válidos")
    print("    ✓ Grain único")
    print("    ✓ Métricas válidas")


# ============================================================
# CREACIÓN DE BASE DE DATOS
# ============================================================

def crear_database():
    """
    Crea la base de datos si todavía no existe.
    """

    print("\n[3] Creando/verificando base de datos...")

    engine = crear_engine()

    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE DATABASE IF NOT EXISTS {DATABASE_NAME}
                CHARACTER SET utf8mb4
                COLLATE utf8mb4_0900_ai_ci
                """
            )
        )

    engine.dispose()

    print(f"    ✓ Base de datos disponible: {DATABASE_NAME}")


# ============================================================
# CREACIÓN DEL ESQUEMA
# ============================================================

def crear_esquema():
    """
    Ejecuta el DDL del Data Warehouse.

    El archivo SQL ya contiene los DROP TABLE y CREATE TABLE.
    """

    print("\n[4] Creando/resetando esquema...")

    if not SQL_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo SQL: {SQL_PATH}"
        )

    sql_script = SQL_PATH.read_text(
        encoding="utf-8"
    )

    engine = crear_engine(DATABASE_NAME)

    # Ejecutamos únicamente las sentencias de creación.
    sentencias = sql_script.split(";")

    with engine.begin() as connection:

        for sentencia in sentencias:

            sentencia = sentencia.strip()

            if not sentencia:
                continue

            sentencia_upper = sentencia.upper()

            # Estas sentencias son informativas y no forman
            # parte de la creación del esquema.
            if (
                sentencia_upper.startswith("CREATE DATABASE")
                or sentencia_upper.startswith("USE ")
                or sentencia_upper.startswith("SHOW ")
                or sentencia_upper.startswith("DESCRIBE ")
            ):
                continue

            connection.execute(text(sentencia))

    engine.dispose()

    print("    ✓ Esquema creado correctamente")


# ============================================================
# TRANSFORMACIÓN DIM_GEOGRAFIA
# ============================================================

def transformar_dim_geografia(df):
    """
    Construye el DataFrame correspondiente a dim_geografia.

    Grain de la dimensión:
        1 municipio = 1 fila

    Natural key:
        codigo_municipio

    sk_geografia:
        NO se genera aquí.
        Será generado por MySQL mediante AUTO_INCREMENT.
    """

    print("\n[5] Transformando dim_geografia...")

    columnas = [
        "codigo_departamento",
        "departamento",
        "codigo_municipio",
        "municipio",
    ]

    dim = df[columnas].copy()

    # --------------------------------------------------------
    # Validar que un municipio no tenga múltiples atributos
    # --------------------------------------------------------

    atributos = [
        "codigo_departamento",
        "departamento",
        "municipio",
    ]

    for atributo in atributos:

        inconsistencias = (
            dim.groupby("codigo_municipio")[atributo]
            .nunique()
        )

        inconsistencias = inconsistencias[
            inconsistencias > 1
        ]

        if not inconsistencias.empty:
            raise ValueError(
                f"El código de municipio presenta múltiples "
                f"valores para {atributo}."
            )

    # --------------------------------------------------------
    # Eliminar repetición de observaciones agrícolas
    # --------------------------------------------------------

    dim = dim.drop_duplicates(
        subset=["codigo_municipio"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Validación de cantidad
    # --------------------------------------------------------

    if len(dim) != EXPECTED_GEOGRAFIA_ROWS:
        raise ValueError(
            f"dim_geografia debería tener "
            f"{EXPECTED_GEOGRAFIA_ROWS:,} filas, "
            f"pero tiene {len(dim):,}."
        )

    print(
        f"    ✓ Municipios únicos: {len(dim):,}"
    )

    return dim


# ============================================================
# CARGA DIM_GEOGRAFIA
# ============================================================

def cargar_dim_geografia(dim):
    """
    Inserta dim_geografia en MySQL.

    Importante:
    No incluimos sk_geografia porque MySQL lo genera.
    """

    print("\n[6] Cargando dim_geografia...")

    engine = crear_engine(DATABASE_NAME)

    dim.to_sql(
        "dim_geografia",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000,
    )

    engine.dispose()

    print("    ✓ Dimensión cargada")


# ============================================================
# VALIDACIÓN DIM_GEOGRAFIA
# ============================================================

def validar_dim_geografia():
    """
    Comprueba que MySQL haya generado correctamente
    las claves sustitutas y que la dimensión tenga
    la cardinalidad esperada.
    """

    print("\n[7] Validando dim_geografia en MySQL...")

    engine = crear_engine(DATABASE_NAME)

    consultas = {
        "filas": """
            SELECT COUNT(*) AS cantidad
            FROM dim_geografia
        """,

        "sk_distintos": """
            SELECT COUNT(DISTINCT sk_geografia) AS cantidad
            FROM dim_geografia
        """,

        "codigos_distintos": """
            SELECT COUNT(DISTINCT codigo_municipio) AS cantidad
            FROM dim_geografia
        """,

        "nulos_sk": """
            SELECT COUNT(*) AS cantidad
            FROM dim_geografia
            WHERE sk_geografia IS NULL
        """,
    }

    resultados = {}

    with engine.connect() as connection:

        for nombre, consulta in consultas.items():

            resultado = connection.execute(
                text(consulta)
            ).scalar()

            resultados[nombre] = resultado

    engine.dispose()

    print(
        f"    Filas:              {resultados['filas']:,}"
    )

    print(
        f"    SK distintos:       {resultados['sk_distintos']:,}"
    )

    print(
        f"    Códigos municipio:   "
        f"{resultados['codigos_distintos']:,}"
    )

    print(
        f"    SK nulos:            "
        f"{resultados['nulos_sk']:,}"
    )

    if resultados["filas"] != EXPECTED_GEOGRAFIA_ROWS:
        raise ValueError(
            "Cantidad incorrecta de filas en dim_geografia."
        )

    if resultados["sk_distintos"] != EXPECTED_GEOGRAFIA_ROWS:
        raise ValueError(
            "Las claves sustitutas no son únicas."
        )

    if resultados["codigos_distintos"] != EXPECTED_GEOGRAFIA_ROWS:
        raise ValueError(
            "Los códigos de municipio no son únicos."
        )

    if resultados["nulos_sk"] != 0:
        raise ValueError(
            "Existen SK de geografía nulos."
        )

    print("    ✓ dim_geografia validada correctamente")


# ============================================================
# CONSULTAR LOOKUP GEOGRAFÍA
# ============================================================

def obtener_lookup_geografia():
    """
    Obtiene la correspondencia:

        codigo_municipio → sk_geografia

    Esta tabla será necesaria posteriormente para
    construir la tabla de hechos.
    """

    print("\n[8] Obteniendo lookup de geografía...")

    engine = crear_engine(DATABASE_NAME)

    query = """
        SELECT
            codigo_municipio,
            sk_geografia
        FROM dim_geografia
    """

    lookup = pd.read_sql(
        query,
        con=engine,
    )

    engine.dispose()

    if len(lookup) != EXPECTED_GEOGRAFIA_ROWS:
        raise ValueError(
            "El lookup de geografía no tiene "
            "la cantidad esperada de registros."
        )

    print(
        f"    ✓ Lookup obtenido: {len(lookup):,} registros"
    )

    print("\n    Ejemplo:")

    print(
        lookup.head(10).to_string(index=False)
    )

    return lookup



# ============================================================
# TRANSFORMACIÓN DIM_CULTIVO
# ============================================================

def transformar_dim_cultivo(df):
    """
    Construye el DataFrame correspondiente a dim_cultivo.

    Grain de la dimensión:
        1 cultivo = 1 fila

    Natural key:
        codigo_cultivo

    sk_cultivo:
        Será generado por MySQL mediante AUTO_INCREMENT.
    """

    print("\n[9] Transformando dim_cultivo...")

    columnas = [
        "codigo_cultivo",
        "grupo_cultivo",
        "subgrupo",
        "cultivo",
        "desagregacion_cultivo",
        "nombre_cientifico",
        "ciclo_cultivo",
    ]

    dim = df[columnas].copy()

    # --------------------------------------------------------
    # Validar consistencia de los atributos del cultivo
    # --------------------------------------------------------

    atributos = [
        "grupo_cultivo",
        "subgrupo",
        "cultivo",
        "desagregacion_cultivo",
        "nombre_cientifico",
        "ciclo_cultivo",
    ]

    for atributo in atributos:

        inconsistencias = (
            dim.groupby("codigo_cultivo")[atributo]
            .nunique()
        )

        inconsistencias = inconsistencias[
            inconsistencias > 1
        ]

        if not inconsistencias.empty:
            raise ValueError(
                f"El código de cultivo presenta múltiples "
                f"valores para {atributo}."
            )

    # --------------------------------------------------------
    # Un cultivo = una fila
    # --------------------------------------------------------

    dim = dim.drop_duplicates(
        subset=["codigo_cultivo"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Validación de cantidad
    # --------------------------------------------------------

    if len(dim) != EXPECTED_CULTIVO_ROWS:
        raise ValueError(
            f"dim_cultivo debería tener "
            f"{EXPECTED_CULTIVO_ROWS:,} filas, "
            f"pero tiene {len(dim):,}."
        )

    print(
        f"    ✓ Cultivos únicos: {len(dim):,}"
    )

    return dim


# ============================================================
# CARGA DIM_CULTIVO
# ============================================================

def cargar_dim_cultivo(dim):
    """
    Inserta dim_cultivo en MySQL.

    No se incluye sk_cultivo porque MySQL
    lo genera automáticamente.
    """

    print("\n[10] Cargando dim_cultivo...")

    engine = crear_engine(DATABASE_NAME)

    dim.to_sql(
        "dim_cultivo",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000,
    )

    engine.dispose()

    print("    ✓ Dimensión cargada")


# ============================================================
# VALIDACIÓN DIM_CULTIVO
# ============================================================

def validar_dim_cultivo():
    """
    Valida las claves sustitutas y naturales
    generadas/cargadas en MySQL.
    """

    print("\n[11] Validando dim_cultivo en MySQL...")

    engine = crear_engine(DATABASE_NAME)

    consultas = {
        "filas": """
            SELECT COUNT(*) AS cantidad
            FROM dim_cultivo
        """,

        "sk_distintos": """
            SELECT COUNT(DISTINCT sk_cultivo) AS cantidad
            FROM dim_cultivo
        """,

        "codigos_distintos": """
            SELECT COUNT(DISTINCT codigo_cultivo) AS cantidad
            FROM dim_cultivo
        """,

        "nulos_sk": """
            SELECT COUNT(*) AS cantidad
            FROM dim_cultivo
            WHERE sk_cultivo IS NULL
        """,
    }

    resultados = {}

    with engine.connect() as connection:

        for nombre, consulta in consultas.items():

            resultado = connection.execute(
                text(consulta)
            ).scalar()

            resultados[nombre] = resultado

    engine.dispose()

    print(
        f"    Filas:              {resultados['filas']:,}"
    )

    print(
        f"    SK distintos:       {resultados['sk_distintos']:,}"
    )

    print(
        f"    Códigos cultivo:    "
        f"{resultados['codigos_distintos']:,}"
    )

    print(
        f"    SK nulos:           "
        f"{resultados['nulos_sk']:,}"
    )

    if resultados["filas"] != EXPECTED_CULTIVO_ROWS:
        raise ValueError(
            "Cantidad incorrecta de filas en dim_cultivo."
        )

    if resultados["sk_distintos"] != EXPECTED_CULTIVO_ROWS:
        raise ValueError(
            "Las claves sustitutas de cultivo no son únicas."
        )

    if resultados["codigos_distintos"] != EXPECTED_CULTIVO_ROWS:
        raise ValueError(
            "Los códigos de cultivo no son únicos."
        )

    if resultados["nulos_sk"] != 0:
        raise ValueError(
            "Existen SK de cultivo nulos."
        )

    print("    ✓ dim_cultivo validada correctamente")


# ============================================================
# LOOKUP DE CULTIVO
# ============================================================

def obtener_lookup_cultivo():
    """
    Obtiene la correspondencia:

        codigo_cultivo → sk_cultivo
    """

    print("\n[12] Obteniendo lookup de cultivo...")

    engine = crear_engine(DATABASE_NAME)

    query = """
        SELECT
            codigo_cultivo,
            sk_cultivo
        FROM dim_cultivo
    """

    lookup = pd.read_sql(
        query,
        con=engine,
    )

    engine.dispose()

    if len(lookup) != EXPECTED_CULTIVO_ROWS:
        raise ValueError(
            "El lookup de cultivo no tiene "
            "la cantidad esperada de registros."
        )

    print(
        f"    ✓ Lookup obtenido: {len(lookup):,} registros"
    )

    print("\n    Ejemplo:")

    print(
        lookup.head(10).to_string(index=False)
    )

    return lookup


# ============================================================
# TRANSFORMACIÓN DIM_TIEMPO
# ============================================================

def transformar_dim_tiempo(df):
    """
    Construye el DataFrame correspondiente a dim_tiempo.

    Grain de la dimensión:
        1 periodo EVA = 1 fila

    Natural key:
        periodo

    Ejemplos:
        2019  -> Anual
        2019A -> Semestral, semestre A
        2019B -> Semestral, semestre B

    sk_tiempo:
        Será generado por MySQL mediante AUTO_INCREMENT.
    """

    print("\n[13] Transformando dim_tiempo...")

    # --------------------------------------------------------
    # Obtener períodos únicos
    # --------------------------------------------------------

    dim = (
        df[["periodo"]]
        .drop_duplicates()
        .copy()
    )

    # --------------------------------------------------------
    # Validar estructura del período
    # --------------------------------------------------------

    def extraer_anio(periodo):
        return int(periodo[:4])

    def determinar_tipo(periodo):
        if len(periodo) == 4:
            return "Anual"

        if len(periodo) == 5 and periodo[-1] in ["A", "B"]:
            return "Semestral"

        raise ValueError(
            f"Período inválido: {periodo}"
        )

    def determinar_semestre(periodo):
        if len(periodo) == 4:
            return None

        if len(periodo) == 5 and periodo[-1] in ["A", "B"]:
            return periodo[-1]

        raise ValueError(
            f"Período inválido: {periodo}"
        )

    # --------------------------------------------------------
    # Derivar atributos
    # --------------------------------------------------------

    dim["anio"] = dim["periodo"].apply(
        extraer_anio
    )

    dim["tipo_periodo"] = dim["periodo"].apply(
        determinar_tipo
    )

    dim["semestre"] = dim["periodo"].apply(
        determinar_semestre
    )

    # --------------------------------------------------------
    # Validar que el año corresponda al período
    # --------------------------------------------------------

    for _, fila in dim.iterrows():

        periodo = fila["periodo"]
        anio = fila["anio"]

        if str(anio) != periodo[:4]:
            raise ValueError(
                f"Inconsistencia entre año y período: "
                f"{periodo} -> {anio}"
            )

    # --------------------------------------------------------
    # Validaciones semánticas
    # --------------------------------------------------------

    anuales = dim[
        dim["tipo_periodo"] == "Anual"
    ]

    if anuales["semestre"].notna().any():
        raise ValueError(
            "Los períodos anuales no deben tener semestre."
        )

    semestrales = dim[
        dim["tipo_periodo"] == "Semestral"
    ]

    if not semestrales["semestre"].isin(
        ["A", "B"]
    ).all():
        raise ValueError(
            "Los períodos semestrales deben tener "
            "semestre A o B."
        )

    # --------------------------------------------------------
    # Ordenar columnas
    # --------------------------------------------------------

    dim = dim[
        [
            "anio",
            "periodo",
            "tipo_periodo",
            "semestre",
        ]
    ]

    # --------------------------------------------------------
    # Ordenar cronológicamente
    # --------------------------------------------------------

    dim = (
        dim.sort_values(
            by=["anio", "periodo"]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Cantidad esperada
    # --------------------------------------------------------

    if len(dim) != EXPECTED_TIEMPO_ROWS:
        raise ValueError(
            f"dim_tiempo debería tener "
            f"{EXPECTED_TIEMPO_ROWS} filas, "
            f"pero tiene {len(dim)}."
        )

    print(
        f"    ✓ Períodos únicos: {len(dim):,}"
    )

    print("\n    Ejemplo:")

    print(
        dim.to_string(index=False)
    )

    return dim


# ============================================================
# CARGA DIM_TIEMPO
# ============================================================

def cargar_dim_tiempo(dim):
    """
    Inserta dim_tiempo en MySQL.

    No se incluye sk_tiempo porque MySQL
    lo genera mediante AUTO_INCREMENT.
    """

    print("\n[14] Cargando dim_tiempo...")

    engine = crear_engine(DATABASE_NAME)

    dim.to_sql(
        "dim_tiempo",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000,
    )

    engine.dispose()

    print("    ✓ Dimensión cargada")


# ============================================================
# VALIDACIÓN DIM_TIEMPO
# ============================================================

def validar_dim_tiempo():
    """
    Valida la dimensión directamente en MySQL.
    """

    print("\n[15] Validando dim_tiempo en MySQL...")

    engine = crear_engine(DATABASE_NAME)

    consultas = {
        "filas": """
            SELECT COUNT(*) AS cantidad
            FROM dim_tiempo
        """,

        "sk_distintos": """
            SELECT COUNT(DISTINCT sk_tiempo) AS cantidad
            FROM dim_tiempo
        """,

        "periodos_distintos": """
            SELECT COUNT(DISTINCT periodo) AS cantidad
            FROM dim_tiempo
        """,

        "nulos_sk": """
            SELECT COUNT(*) AS cantidad
            FROM dim_tiempo
            WHERE sk_tiempo IS NULL
        """,

        "anuales": """
            SELECT COUNT(*) AS cantidad
            FROM dim_tiempo
            WHERE tipo_periodo = 'Anual'
        """,

        "semestrales": """
            SELECT COUNT(*) AS cantidad
            FROM dim_tiempo
            WHERE tipo_periodo = 'Semestral'
        """,

        "anuales_con_semestre": """
            SELECT COUNT(*) AS cantidad
            FROM dim_tiempo
            WHERE tipo_periodo = 'Anual'
              AND semestre IS NOT NULL
        """,

        "semestrales_invalidos": """
            SELECT COUNT(*) AS cantidad
            FROM dim_tiempo
            WHERE tipo_periodo = 'Semestral'
              AND semestre NOT IN ('A', 'B')
        """,
    }

    resultados = {}

    with engine.connect() as connection:

        for nombre, consulta in consultas.items():

            resultados[nombre] = connection.execute(
                text(consulta)
            ).scalar()

    engine.dispose()

    print(
        f"    Filas:              {resultados['filas']:,}"
    )

    print(
        f"    SK distintas:       "
        f"{resultados['sk_distintos']:,}"
    )

    print(
        f"    Períodos distintos:  "
        f"{resultados['periodos_distintos']:,}"
    )

    print(
        f"    SK nulos:           "
        f"{resultados['nulos_sk']:,}"
    )

    print(
        f"    Períodos anuales:    "
        f"{resultados['anuales']:,}"
    )

    print(
        f"    Períodos semestrales:"
        f" {resultados['semestrales']:,}"
    )

    print(
        f"    Anuales con semestre:"
        f" {resultados['anuales_con_semestre']:,}"
    )

    print(
        f"    Semestrales inválidos:"
        f" {resultados['semestrales_invalidos']:,}"
    )

    # --------------------------------------------------------
    # Validaciones
    # --------------------------------------------------------

    if resultados["filas"] != EXPECTED_TIEMPO_ROWS:
        raise ValueError(
            "Cantidad incorrecta de filas en dim_tiempo."
        )

    if resultados["sk_distintos"] != EXPECTED_TIEMPO_ROWS:
        raise ValueError(
            "Las SK de tiempo no son únicas."
        )

    if resultados["periodos_distintos"] != EXPECTED_TIEMPO_ROWS:
        raise ValueError(
            "Los períodos no son únicos."
        )

    if resultados["nulos_sk"] != 0:
        raise ValueError(
            "Existen SK de tiempo nulas."
        )

    if resultados["anuales"] != 7:
        raise ValueError(
            "Se esperaban 7 períodos anuales."
        )

    if resultados["semestrales"] != 14:
        raise ValueError(
            "Se esperaban 14 períodos semestrales."
        )

    if resultados["anuales_con_semestre"] != 0:
        raise ValueError(
            "Existen períodos anuales con semestre."
        )

    if resultados["semestrales_invalidos"] != 0:
        raise ValueError(
            "Existen períodos semestrales inválidos."
        )

    print(
        "    ✓ dim_tiempo validada correctamente"
    )


# ============================================================
# LOOKUP DE TIEMPO
# ============================================================

def obtener_lookup_tiempo():
    """
    Obtiene la correspondencia:

        periodo → sk_tiempo

    Esta tabla será utilizada posteriormente
    para construir la tabla de hechos.
    """

    print("\n[16] Obteniendo lookup de tiempo...")

    engine = crear_engine(DATABASE_NAME)

    query = """
        SELECT
            periodo,
            sk_tiempo
        FROM dim_tiempo
    """

    lookup = pd.read_sql(
        query,
        con=engine,
    )

    engine.dispose()

    if len(lookup) != EXPECTED_TIEMPO_ROWS:
        raise ValueError(
            "El lookup de tiempo no tiene "
            "la cantidad esperada de registros."
        )

    print(
        f"    ✓ Lookup obtenido: "
        f"{len(lookup):,} registros"
    )

    print("\n    Lookup:")

    print(
        lookup.sort_values("periodo")
        .to_string(index=False)
    )

    return lookup

# ============================================================
# TRANSFORMACIÓN FACT_PRODUCCION_AGRICOLA
# ============================================================

def transformar_fact_produccion(
    df,
    lookup_geografia,
    lookup_cultivo,
    lookup_tiempo
):
    """
    Construye la tabla de hechos a partir del staging
    y de los lookups de las dimensiones.

    Grain:
        municipio + cultivo + año + período

    En la fact ese grain queda representado mediante:

        sk_geografia + sk_cultivo + sk_tiempo
    """

    print("\n[17] Transformando fact_produccion_agricola...")

    # --------------------------------------------------------
    # Trabajar sobre una copia del staging
    # --------------------------------------------------------

    fact = df.copy()

    filas_iniciales = len(fact)

    # --------------------------------------------------------
    # Lookup de geografía
    # --------------------------------------------------------

    fact = fact.merge(
        lookup_geografia,
        on="codigo_municipio",
        how="left",
        validate="many_to_one"
    )

    if len(fact) != filas_iniciales:
        raise ValueError(
            "El lookup de geografía alteró la cantidad "
            "de registros."
        )

    if fact["sk_geografia"].isna().any():
        cantidad = fact["sk_geografia"].isna().sum()

        raise ValueError(
            f"Existen {cantidad:,} registros sin "
            "correspondencia en dim_geografia."
        )

    print(
        "    ✓ Lookup geografía aplicado"
    )

    # --------------------------------------------------------
    # Lookup de cultivo
    # --------------------------------------------------------

    fact = fact.merge(
        lookup_cultivo,
        on="codigo_cultivo",
        how="left",
        validate="many_to_one"
    )

    if len(fact) != filas_iniciales:
        raise ValueError(
            "El lookup de cultivo alteró la cantidad "
            "de registros."
        )

    if fact["sk_cultivo"].isna().any():
        cantidad = fact["sk_cultivo"].isna().sum()

        raise ValueError(
            f"Existen {cantidad:,} registros sin "
            "correspondencia en dim_cultivo."
        )

    print(
        "    ✓ Lookup cultivo aplicado"
    )

    # --------------------------------------------------------
    # Lookup de tiempo
    # --------------------------------------------------------

    fact = fact.merge(
        lookup_tiempo,
        on="periodo",
        how="left",
        validate="many_to_one"
    )

    if len(fact) != filas_iniciales:
        raise ValueError(
            "El lookup de tiempo alteró la cantidad "
            "de registros."
        )

    if fact["sk_tiempo"].isna().any():
        cantidad = fact["sk_tiempo"].isna().sum()

        raise ValueError(
            f"Existen {cantidad:,} registros sin "
            "correspondencia en dim_tiempo."
        )

    print(
        "    ✓ Lookup tiempo aplicado"
    )

    # --------------------------------------------------------
    # Seleccionar únicamente las columnas de la FACT
    # --------------------------------------------------------

    fact = fact[
        [
            "sk_geografia",
            "sk_cultivo",
            "sk_tiempo",
            "area_sembrada",
            "area_cosechada",
            "produccion",
            "rendimiento",
        ]
    ].copy()

    # --------------------------------------------------------
    # Convertir SK a entero
    # --------------------------------------------------------

    fact["sk_geografia"] = (
        fact["sk_geografia"]
        .astype("int64")
    )

    fact["sk_cultivo"] = (
        fact["sk_cultivo"]
        .astype("int64")
    )

    fact["sk_tiempo"] = (
        fact["sk_tiempo"]
        .astype("int64")
    )

    # --------------------------------------------------------
    # Asegurar precisión de las métricas
    # --------------------------------------------------------

    metricas = [
        "area_sembrada",
        "area_cosechada",
        "produccion",
        "rendimiento",
    ]

    for columna in metricas:
        fact[columna] = (
            pd.to_numeric(
                fact[columna],
                errors="raise"
            )
            .round(2)
        )

    # --------------------------------------------------------
    # Validación del volumen
    # --------------------------------------------------------

    if len(fact) != EXPECTED_FACT_ROWS:
        raise ValueError(
            f"La fact debería tener "
            f"{EXPECTED_FACT_ROWS:,} registros, "
            f"pero tiene {len(fact):,}."
        )

    # --------------------------------------------------------
    # Validación del grain
    # --------------------------------------------------------

    grain = [
        "sk_geografia",
        "sk_cultivo",
        "sk_tiempo",
    ]

    duplicados = fact.duplicated(
        subset=grain,
        keep=False
    )

    if duplicados.any():

        cantidad = duplicados.sum()

        raise ValueError(
            f"Se encontraron {cantidad:,} registros "
            "duplicados en el grain de la fact."
        )

    print(
        f"    ✓ Registros conservados: "
        f"{len(fact):,}"
    )

    print(
        "    ✓ Todas las SK tienen correspondencia"
    )

    print(
        "    ✓ Grain de la fact validado"
    )

    return fact


# ============================================================
# CARGA FACT_PRODUCCION_AGRICOLA
# ============================================================

def cargar_fact_produccion(fact):
    """
    Inserta la tabla de hechos en MySQL.

    No se incluye sk_produccion_agricola porque
    MySQL lo genera mediante AUTO_INCREMENT.
    """

    print("\n[18] Cargando fact_produccion_agricola...")

    engine = crear_engine(DATABASE_NAME)

    fact.to_sql(
        "fact_produccion_agricola",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )

    engine.dispose()

    print("    ✓ Fact cargada")


# ============================================================
# VALIDACIÓN FACT_PRODUCCION_AGRICOLA
# ============================================================

def validar_fact_produccion():
    """
    Valida la tabla de hechos directamente en MySQL.
    """

    print("\n[19] Validando fact_produccion_agricola en MySQL...")

    engine = crear_engine(DATABASE_NAME)

    consultas = {
        "filas": """
            SELECT COUNT(*)
            FROM fact_produccion_agricola
        """,

        "sk_fact_distintas": """
            SELECT COUNT(DISTINCT sk_produccion_agricola)
            FROM fact_produccion_agricola
        """,

        "grain_distinto": """
            SELECT COUNT(*)
            FROM (
                SELECT
                    sk_geografia,
                    sk_cultivo,
                    sk_tiempo
                FROM fact_produccion_agricola
                GROUP BY
                    sk_geografia,
                    sk_cultivo,
                    sk_tiempo
            ) AS grain
        """,

        "fk_geografia_huerfanas": """
            SELECT COUNT(*)
            FROM fact_produccion_agricola f
            LEFT JOIN dim_geografia g
                ON f.sk_geografia = g.sk_geografia
            WHERE g.sk_geografia IS NULL
        """,

        "fk_cultivo_huerfanas": """
            SELECT COUNT(*)
            FROM fact_produccion_agricola f
            LEFT JOIN dim_cultivo c
                ON f.sk_cultivo = c.sk_cultivo
            WHERE c.sk_cultivo IS NULL
        """,

        "fk_tiempo_huerfanas": """
            SELECT COUNT(*)
            FROM fact_produccion_agricola f
            LEFT JOIN dim_tiempo t
                ON f.sk_tiempo = t.sk_tiempo
            WHERE t.sk_tiempo IS NULL
        """,

        "negativos_area_sembrada": """
            SELECT COUNT(*)
            FROM fact_produccion_agricola
            WHERE area_sembrada < 0
        """,

        "negativos_area_cosechada": """
            SELECT COUNT(*)
            FROM fact_produccion_agricola
            WHERE area_cosechada < 0
        """,

        "negativos_produccion": """
            SELECT COUNT(*)
            FROM fact_produccion_agricola
            WHERE produccion < 0
        """,

        "negativos_rendimiento": """
            SELECT COUNT(*)
            FROM fact_produccion_agricola
            WHERE rendimiento < 0
        """,

        "cosechada_mayor_sembrada": """
            SELECT COUNT(*)
            FROM fact_produccion_agricola
            WHERE area_cosechada > area_sembrada
        """,

        "sembrada_cero_cosechada_positiva": """
            SELECT COUNT(*)
            FROM fact_produccion_agricola
            WHERE area_sembrada = 0
              AND area_cosechada > 0
        """
    }

    resultados = {}

    with engine.connect() as connection:

        for nombre, consulta in consultas.items():

            resultados[nombre] = connection.execute(
                text(consulta)
            ).scalar()

    engine.dispose()

    print(
        f"    Filas:                       "
        f"{resultados['filas']:,}"
    )

    print(
        f"    SK fact distintas:           "
        f"{resultados['sk_fact_distintas']:,}"
    )

    print(
        f"    Combinaciones grain:          "
        f"{resultados['grain_distinto']:,}"
    )

    print(
        f"    FK geografía huérfanas:       "
        f"{resultados['fk_geografia_huerfanas']:,}"
    )

    print(
        f"    FK cultivo huérfanas:         "
        f"{resultados['fk_cultivo_huerfanas']:,}"
    )

    print(
        f"    FK tiempo huérfanas:          "
        f"{resultados['fk_tiempo_huerfanas']:,}"
    )

    print(
        f"    Negativos área sembrada:      "
        f"{resultados['negativos_area_sembrada']:,}"
    )

    print(
        f"    Negativos área cosechada:     "
        f"{resultados['negativos_area_cosechada']:,}"
    )

    print(
        f"    Negativos producción:          "
        f"{resultados['negativos_produccion']:,}"
    )

    print(
        f"    Negativos rendimiento:         "
        f"{resultados['negativos_rendimiento']:,}"
    )

    print(
        f"    Cosechada > sembrada:          "
        f"{resultados['cosechada_mayor_sembrada']:,}"
    )

    print(
        f"    Sembrada = 0 / cosechada > 0: "
        f"{resultados['sembrada_cero_cosechada_positiva']:,}"
    )

    # --------------------------------------------------------
    # Validaciones obligatorias
    # --------------------------------------------------------

    if resultados["filas"] != EXPECTED_FACT_ROWS:
        raise ValueError(
            "La cantidad de registros de la fact es incorrecta."
        )

    if resultados["sk_fact_distintas"] != EXPECTED_FACT_ROWS:
        raise ValueError(
            "Las SK de la fact no son únicas."
        )

    if resultados["grain_distinto"] != EXPECTED_FACT_ROWS:
        raise ValueError(
            "El grain de la fact contiene duplicados."
        )

    if resultados["fk_geografia_huerfanas"] != 0:
        raise ValueError(
            "Existen FK de geografía huérfanas."
        )

    if resultados["fk_cultivo_huerfanas"] != 0:
        raise ValueError(
            "Existen FK de cultivo huérfanas."
        )

    if resultados["fk_tiempo_huerfanas"] != 0:
        raise ValueError(
            "Existen FK de tiempo huérfanas."
        )

    if resultados["negativos_area_sembrada"] != 0:
        raise ValueError(
            "Existen áreas sembradas negativas."
        )

    if resultados["negativos_area_cosechada"] != 0:
        raise ValueError(
            "Existen áreas cosechadas negativas."
        )

    if resultados["negativos_produccion"] != 0:
        raise ValueError(
            "Existen producciones negativas."
        )

    if resultados["negativos_rendimiento"] != 0:
        raise ValueError(
            "Existen rendimientos negativos."
        )

    print(
        "\n    ✓ Fact validada correctamente"
    )


# ============================================================
# PROCESO PRINCIPAL
# ============================================================

def ejecutar_proceso():

    print("=" * 60)
    print("ETL - CARGA DATA WAREHOUSE EVA")
    print("=" * 60)

    # --------------------------------------------------------
    # STAGING
    # --------------------------------------------------------

    staging = cargar_staging()

    validar_staging(staging)

    # --------------------------------------------------------
    # ESQUEMA
    # --------------------------------------------------------

    crear_database()

    crear_esquema()

    # --------------------------------------------------------
    # DIM_GEOGRAFIA
    # --------------------------------------------------------

    dim_geografia = transformar_dim_geografia(
        staging
    )

    cargar_dim_geografia(
        dim_geografia
    )

    validar_dim_geografia()

    lookup_geografia = obtener_lookup_geografia()

    # --------------------------------------------------------
    # DIM_CULTIVO
    # --------------------------------------------------------

    dim_cultivo = transformar_dim_cultivo(
        staging
    )

    cargar_dim_cultivo(
        dim_cultivo
    )

    validar_dim_cultivo()

    lookup_cultivo = obtener_lookup_cultivo()

    # --------------------------------------------------------
    # DIM_TIEMPO
    # --------------------------------------------------------

    dim_tiempo = transformar_dim_tiempo(
        staging
    )

    cargar_dim_tiempo(
        dim_tiempo
    )

    validar_dim_tiempo()

    lookup_tiempo = obtener_lookup_tiempo()

    # --------------------------------------------------------
    # FACT
    # --------------------------------------------------------

    fact = transformar_fact_produccion(
        staging,
        lookup_geografia,
        lookup_cultivo,
        lookup_tiempo
    )

    cargar_fact_produccion(
        fact
    )

    validar_fact_produccion()

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("ETL COMPLETADO CORRECTAMENTE")
    print("=" * 60)

    return True


if __name__ == "__main__":
    ejecutar_proceso()