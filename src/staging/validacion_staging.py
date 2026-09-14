# 06_validacion_staging.py

import os
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO_STAGING = (
    "data/staging/eva_agricola_staging.csv"
)

CARPETA_VALIDACION = "data/validation"

ARCHIVO_REPORTE = os.path.join(
    CARPETA_VALIDACION,
    "validacion_staging.csv"
)

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

COLUMNAS_CLAVE = [
    "codigo_municipio",
    "codigo_cultivo",
    "anio",
    "periodo",
]


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def registrar_resultado(resultados, categoria, validacion, estado, detalle):
    resultados.append({
        "categoria": categoria,
        "validacion": validacion,
        "estado": estado,
        "detalle": detalle
    })


def imprimir_resultado(estado, mensaje):
    print(f"{estado}: {mensaje}")


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def ejecutar_validacion_staging():

    print("=" * 70)
    print("VALIDACIÓN DEL DATASET STAGING EVA")
    print("=" * 70)

    resultados = []

    # --------------------------------------------------------
    # 1. EXISTENCIA DEL ARCHIVO
    # --------------------------------------------------------

    print("\n[1/10] Verificando archivo...")

    if not os.path.exists(ARCHIVO_STAGING):
        print("ERROR: No existe el archivo de staging.")
        return

    imprimir_resultado(
        "OK",
        f"Archivo encontrado: {ARCHIVO_STAGING}"
    )

    registrar_resultado(
        resultados,
        "Archivo",
        "Existencia del archivo",
        "OK",
        "El archivo de staging existe."
    )

    # --------------------------------------------------------
    # 2. LECTURA DEL DATASET
    # --------------------------------------------------------

    print("\n[2/10] Leyendo dataset staging...")

    df = pd.read_csv(
        ARCHIVO_STAGING,
        dtype=str,
        low_memory=False
    )

    registros = len(df)
    columnas = len(df.columns)

    print(f"Registros leídos: {registros:,}")
    print(f"Columnas leídas : {columnas}")

    # --------------------------------------------------------
    # 3. VOLUMEN
    # --------------------------------------------------------

    print("\n[3/10] Validando volumen...")

    if registros == 166732:
        imprimir_resultado(
            "OK",
            f"Cantidad de registros: {registros:,}"
        )

        registrar_resultado(
            resultados,
            "Volumen",
            "Cantidad de registros",
            "OK",
            f"{registros:,} registros."
        )

    else:
        imprimir_resultado(
            "ADVERTENCIA",
            f"Se esperaban 166,732 registros y se encontraron {registros:,}."
        )

        registrar_resultado(
            resultados,
            "Volumen",
            "Cantidad de registros",
            "ADVERTENCIA",
            f"Esperados: 166,732. Encontrados: {registros:,}."
        )

    # --------------------------------------------------------
    # 4. ESTRUCTURA
    # --------------------------------------------------------

    print("\n[4/10] Validando estructura de columnas...")

    columnas_actuales = list(df.columns)

    if columnas_actuales == COLUMNAS_ESPERADAS:

        imprimir_resultado(
            "OK",
            "Las 18 columnas coinciden en nombre y orden."
        )

        registrar_resultado(
            resultados,
            "Estructura",
            "Columnas esperadas",
            "OK",
            "Las columnas coinciden en nombre y orden."
        )

    else:

        imprimir_resultado(
            "ERROR",
            "La estructura de columnas no coincide."
        )

        faltantes = [
            c for c in COLUMNAS_ESPERADAS
            if c not in columnas_actuales
        ]

        adicionales = [
            c for c in columnas_actuales
            if c not in COLUMNAS_ESPERADAS
        ]

        print(f"Columnas faltantes : {faltantes}")
        print(f"Columnas adicionales: {adicionales}")

        registrar_resultado(
            resultados,
            "Estructura",
            "Columnas esperadas",
            "ERROR",
            f"Faltantes: {faltantes}. Adicionales: {adicionales}."
        )

    # --------------------------------------------------------
    # 5. TIPOS DE DATOS
    # --------------------------------------------------------

    print("\n[5/10] Validando tipos de datos...")

    # Los códigos y textos deben poder tratarse como strings.
    tipos_ok = True

    for columna in COLUMNAS_TEXTO:

        if not pd.api.types.is_string_dtype(df[columna]):
            tipos_ok = False

            print(
                f"ERROR: {columna} no está almacenada como texto."
            )

    # anio debe ser convertible a entero.
    anio_convertido = pd.to_numeric(
        df["anio"],
        errors="coerce"
    )

    anio_no_convertible = anio_convertido.isna().sum()

    if anio_no_convertible > 0:

        tipos_ok = False

        print(
            f"ERROR: anio tiene {anio_no_convertible:,} "
            "valores no convertibles a entero."
        )

    # Las métricas deben ser numéricas.
    metricas_no_numericas = {}

    for columna in COLUMNAS_METRICAS:

        valores = pd.to_numeric(
            df[columna],
            errors="coerce"
        )

        errores = valores.isna().sum()

        metricas_no_numericas[columna] = errores

        if errores > 0:

            tipos_ok = False

            print(
                f"ERROR: {columna} tiene "
                f"{errores:,} valores no numéricos."
            )

    if tipos_ok:

        imprimir_resultado(
            "OK",
            "Los campos cumplen el contrato técnico esperado."
        )

        registrar_resultado(
            resultados,
            "Tipos",
            "Tipos de datos",
            "OK",
            "Códigos/textos como texto, año convertible a entero y métricas numéricas."
        )

    else:

        registrar_resultado(
            resultados,
            "Tipos",
            "Tipos de datos",
            "ERROR",
            "Se encontraron problemas de tipos o conversión."
        )

    # --------------------------------------------------------
    # 6. NULOS Y VACÍOS
    # --------------------------------------------------------

    print("\n[6/10] Validando nulos y valores vacíos...")

    nulos_total = int(df.isna().sum().sum())

    vacios_total = 0

    for columna in df.columns:

        vacios_total += int(
            df[columna]
            .astype(str)
            .str.strip()
            .eq("")
            .sum()
        )

    if nulos_total == 0 and vacios_total == 0:

        imprimir_resultado(
            "OK",
            "No existen valores nulos ni cadenas vacías."
        )

        registrar_resultado(
            resultados,
            "Calidad",
            "Nulos y vacíos",
            "OK",
            "Nulos: 0. Vacíos: 0."
        )

    else:

        imprimir_resultado(
            "ADVERTENCIA",
            f"Nulos: {nulos_total:,}. Vacíos: {vacios_total:,}."
        )

        registrar_resultado(
            resultados,
            "Calidad",
            "Nulos y vacíos",
            "ADVERTENCIA",
            f"Nulos: {nulos_total:,}. Vacíos: {vacios_total:,}."
        )

    # --------------------------------------------------------
    # 7. CÓDIGOS
    # --------------------------------------------------------

    print("\n[7/10] Validando códigos geográficos y de cultivo...")

    departamento_incorrecto = (
        df["codigo_departamento"]
        .astype(str)
        .str.len()
        .ne(2)
        .sum()
    )

    municipio_incorrecto = (
        df["codigo_municipio"]
        .astype(str)
        .str.len()
        .ne(5)
        .sum()
    )

    codigo_cultivo_vacio = (
        df["codigo_cultivo"]
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    if (
        departamento_incorrecto == 0
        and municipio_incorrecto == 0
        and codigo_cultivo_vacio == 0
    ):

        imprimir_resultado(
            "OK",
            "Los códigos cumplen las condiciones estructurales."
        )

        registrar_resultado(
            resultados,
            "Identificadores",
            "Longitud y presencia de códigos",
            "OK",
            "Departamento: 2 caracteres. Municipio: 5 caracteres. Código cultivo presente."
        )

    else:

        imprimir_resultado(
            "ERROR",
            "Se encontraron problemas en los códigos."
        )

        registrar_resultado(
            resultados,
            "Identificadores",
            "Longitud y presencia de códigos",
            "ERROR",
            f"Dept incorrectos: {departamento_incorrecto}. "
            f"Municipio incorrectos: {municipio_incorrecto}. "
            f"Cultivo vacío: {codigo_cultivo_vacio}."
        )

    # --------------------------------------------------------
    # 8. TIEMPO
    # --------------------------------------------------------

    print("\n[8/10] Validando Año vs Periodo...")

    anio_numerico = pd.to_numeric(
        df["anio"],
        errors="coerce"
    )

    anio_periodo = (
        df["periodo"]
        .astype(str)
        .str.extract(r"^(\d{4})")[0]
    )

    inconsistencia_tiempo = (
        anio_numerico.astype("Int64").astype(str)
        != anio_periodo.astype(str)
    )

    inconsistencias = int(
        inconsistencia_tiempo.sum()
    )

    if inconsistencias == 0:

        imprimir_resultado(
            "OK",
            "Año y Periodo son consistentes en todos los registros."
        )

        registrar_resultado(
            resultados,
            "Tiempo",
            "Año vs Periodo",
            "OK",
            "0 inconsistencias."
        )

    else:

        imprimir_resultado(
            "ERROR",
            f"Inconsistencias Año vs Periodo: {inconsistencias:,}"
        )

        registrar_resultado(
            resultados,
            "Tiempo",
            "Año vs Periodo",
            "ERROR",
            f"{inconsistencias:,} inconsistencias."
        )

    # --------------------------------------------------------
    # 9. GRANULARIDAD
    # --------------------------------------------------------

    print("\n[9/10] Validando granularidad...")

    claves = df[COLUMNAS_CLAVE].astype(str).agg(
        "|".join,
        axis=1
    )

    claves_unicas = claves.nunique()

    duplicados = registros - claves_unicas

    print(f"Registros     : {registros:,}")
    print(f"Claves únicas : {claves_unicas:,}")
    print(f"Duplicados    : {duplicados:,}")

    if duplicados == 0:

        imprimir_resultado(
            "OK",
            "La granularidad propuesta se mantiene única."
        )

        registrar_resultado(
            resultados,
            "Granularidad",
            "Municipio + Cultivo + Año + Periodo",
            "OK",
            f"{claves_unicas:,} claves únicas para {registros:,} registros."
        )

    else:

        imprimir_resultado(
            "ERROR",
            f"Se encontraron {duplicados:,} registros duplicados."
        )

        registrar_resultado(
            resultados,
            "Granularidad",
            "Municipio + Cultivo + Año + Periodo",
            "ERROR",
            f"{duplicados:,} registros duplican la clave propuesta."
        )

    # --------------------------------------------------------
    # 10. MÉTRICAS Y CONDICIONES SEMÁNTICAS
    # --------------------------------------------------------

    print("\n[10/10] Validando métricas y condiciones semánticas...")

    metricas = {}

    for columna in COLUMNAS_METRICAS:

        valores = pd.to_numeric(
            df[columna],
            errors="coerce"
        )

        metricas[columna] = valores

        negativos = int(
            (valores < 0).sum()
        )

        minimo = valores.min()
        maximo = valores.max()

        print(
            f"{columna:<20} "
            f"min={minimo} | max={maximo} | negativos={negativos}"
        )

        if negativos == 0:

            registrar_resultado(
                resultados,
                "Métricas",
                f"Valores negativos - {columna}",
                "OK",
                f"0 valores negativos. Rango: {minimo} a {maximo}."
            )

        else:

            registrar_resultado(
                resultados,
                "Métricas",
                f"Valores negativos - {columna}",
                "ADVERTENCIA",
                f"{negativos:,} valores negativos."
            )

    area_sembrada = metricas["area_sembrada"]
    area_cosechada = metricas["area_cosechada"]

    cosechada_mayor = int(
        (area_cosechada > area_sembrada).sum()
    )

    sembrada_cero_cosechada_mayor = int(
        (
            (area_sembrada == 0)
            & (area_cosechada > 0)
        ).sum()
    )

    print("\n--- Condiciones semánticas preservadas ---")

    print(
        "Área cosechada > área sembrada:",
        f"{cosechada_mayor:,}"
    )

    print(
        "Área sembrada = 0 y cosechada > 0:",
        f"{sembrada_cero_cosechada_mayor:,}"
    )

    registrar_resultado(
        resultados,
        "Semántica",
        "Área cosechada > área sembrada",
        "INFORMATIVO",
        f"{cosechada_mayor:,} registros. "
        "Se preservan deliberadamente; no constituyen regla automática de limpieza."
    )

    registrar_resultado(
        resultados,
        "Semántica",
        "Área sembrada = 0 y cosechada > 0",
        "INFORMATIVO",
        f"{sembrada_cero_cosechada_mayor:,} registros. "
        "Se preservan deliberadamente."
    )

    # ========================================================
    # RESUMEN
    # ========================================================

    print("\n" + "=" * 70)
    print("RESUMEN DE VALIDACIÓN")
    print("=" * 70)

    reporte = pd.DataFrame(resultados)

    conteo_estados = (
        reporte["estado"]
        .value_counts()
    )

    for estado, cantidad in conteo_estados.items():

        print(
            f"{estado:<15}: {cantidad}"
        )

    # --------------------------------------------------------
    # EXPORTACIÓN
    # --------------------------------------------------------

    os.makedirs(
        CARPETA_VALIDACION,
        exist_ok=True
    )

    reporte.to_csv(
        ARCHIVO_REPORTE,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nReporte generado:")
    print(ARCHIVO_REPORTE)

    print("\n" + "=" * 70)
    print("VALIDACIÓN FINALIZADA")
    print("=" * 70)


if __name__ == "__main__":
    ejecutar_validacion_staging()