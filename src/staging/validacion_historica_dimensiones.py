import pandas as pd
from pathlib import Path

def ejecutar_validacion_historica():
    # ============================================================
    # CONFIGURACIÓN
    # ============================================================

    RUTA_STAGING = Path("data/staging/eva_agricola_staging.csv")
    RUTA_SALIDA = Path("data/validation")

    RUTA_SALIDA.mkdir(parents=True, exist_ok=True)


    # ============================================================
    # CARGA DEL DATASET
    # ============================================================

    print("Cargando staging...")

    columnas_codigo = [
        "codigo_departamento",
        "codigo_municipio",
        "codigo_cultivo"
    ]

    df = pd.read_csv(
        RUTA_STAGING,
        dtype={
            "codigo_departamento": "string",
            "codigo_municipio": "string",
            "codigo_cultivo": "string"
        }
    )

    print(f"Registros cargados: {len(df):,}")


    # ============================================================
    # NORMALIZACIÓN MÍNIMA
    # ============================================================

    for columna in [
        "codigo_departamento",
        "codigo_municipio",
        "codigo_cultivo",
        "departamento",
        "municipio",
        "grupo_cultivo",
        "subgrupo",
        "cultivo",
        "desagregacion_cultivo",
        "nombre_cientifico",
        "ciclo_cultivo"
    ]:
        df[columna] = df[columna].astype("string").str.strip()


    # ============================================================
    # 1. VALIDACIÓN HISTÓRICA DE GEOGRAFÍA
    # ============================================================

    print("\n--- VALIDACIÓN HISTÓRICA DE GEOGRAFÍA ---")

    atributos_geografia = [
        "codigo_departamento",
        "departamento",
        "municipio"
    ]

    resultados_geografia = []

    for atributo in atributos_geografia:

        variaciones = (
            df.groupby("codigo_municipio")[atributo]
            .nunique(dropna=False)
            .reset_index(name="cantidad_valores")
        )

        variaciones = variaciones[
            variaciones["cantidad_valores"] > 1
        ].copy()

        resultados_geografia.append(
            {
                "atributo": atributo,
                "municipios_con_variacion": len(variaciones)
            }
        )

        print(
            f"{atributo}: "
            f"{len(variaciones):,} municipios con variación"
        )

        # Guardar detalle de inconsistencias
        if not variaciones.empty:

            codigos_problematicos = variaciones["codigo_municipio"]

            detalle = df[
                df["codigo_municipio"].isin(codigos_problematicos)
            ][
                [
                    "codigo_municipio",
                    "codigo_departamento",
                    "departamento",
                    "municipio",
                    "anio",
                    "periodo"
                ]
            ].drop_duplicates()

            detalle.to_csv(
                RUTA_SALIDA / f"08_variaciones_geografia_{atributo}.csv",
                index=False,
                encoding="utf-8-sig"
            )


    pd.DataFrame(resultados_geografia).to_csv(
        RUTA_SALIDA / "08_resumen_validacion_geografia.csv",
        index=False,
        encoding="utf-8-sig"
    )


    # ============================================================
    # 2. VALIDACIÓN HISTÓRICA DE CULTIVO
    # ============================================================

    print("\n--- VALIDACIÓN HISTÓRICA DE CULTIVO ---")

    atributos_cultivo = [
        "grupo_cultivo",
        "subgrupo",
        "cultivo",
        "desagregacion_cultivo",
        "nombre_cientifico",
        "ciclo_cultivo"
    ]

    resultados_cultivo = []

    for atributo in atributos_cultivo:

        variaciones = (
            df.groupby("codigo_cultivo")[atributo]
            .nunique(dropna=False)
            .reset_index(name="cantidad_valores")
        )

        variaciones = variaciones[
            variaciones["cantidad_valores"] > 1
        ].copy()

        resultados_cultivo.append(
            {
                "atributo": atributo,
                "cultivos_con_variacion": len(variaciones)
            }
        )

        print(
            f"{atributo}: "
            f"{len(variaciones):,} códigos de cultivo con variación"
        )

        # Guardar detalle de inconsistencias
        if not variaciones.empty:

            codigos_problematicos = variaciones["codigo_cultivo"]

            detalle = df[
                df["codigo_cultivo"].isin(codigos_problematicos)
            ][
                [
                    "codigo_cultivo",
                    "grupo_cultivo",
                    "subgrupo",
                    "cultivo",
                    "desagregacion_cultivo",
                    "nombre_cientifico",
                    "ciclo_cultivo",
                    "anio",
                    "periodo"
                ]
            ].drop_duplicates()

            detalle.to_csv(
                RUTA_SALIDA / f"08_variaciones_cultivo_{atributo}.csv",
                index=False,
                encoding="utf-8-sig"
            )


    pd.DataFrame(resultados_cultivo).to_csv(
        RUTA_SALIDA / "08_resumen_validacion_cultivo.csv",
        index=False,
        encoding="utf-8-sig"
    )


    # ============================================================
    # 3. VALIDACIÓN ESPECÍFICA DE CÓDIGOS DE CULTIVO
    # ============================================================

    print("\n--- VALIDACIÓN ESPECÍFICA DE CÓDIGOS DE CULTIVO ---")

    resumen_codigos = (
        df.groupby("codigo_cultivo")
        .agg(
            cantidad_registros=("codigo_cultivo", "size"),
            cantidad_anios=("anio", "nunique"),
            primer_anio=("anio", "min"),
            ultimo_anio=("anio", "max"),
            cantidad_cultivos=("cultivo", "nunique"),
            cantidad_grupos=("grupo_cultivo", "nunique"),
            cantidad_subgrupos=("subgrupo", "nunique"),
            cantidad_desagregaciones=("desagregacion_cultivo", "nunique"),
            cantidad_nombres_cientificos=("nombre_cientifico", "nunique"),
            cantidad_ciclos=("ciclo_cultivo", "nunique")
        )
        .reset_index()
    )

    resumen_codigos.to_csv(
        RUTA_SALIDA / "08_historial_por_codigo_cultivo.csv",
        index=False,
        encoding="utf-8-sig"
    )


    # ============================================================
    # 4. REVISIÓN DE CÓDIGOS ESPECÍFICOS
    # ============================================================

    codigos_revisar = [
        "1050600",
        "1051200",
        "1051500"
    ]

    detalle_codigos = df[
        df["codigo_cultivo"].isin(codigos_revisar)
    ][
        [
            "codigo_cultivo",
            "cultivo",
            "grupo_cultivo",
            "subgrupo",
            "desagregacion_cultivo",
            "nombre_cientifico",
            "ciclo_cultivo",
            "anio",
            "periodo"
        ]
    ].drop_duplicates().sort_values(
        ["codigo_cultivo", "anio", "periodo"]
    )

    detalle_codigos.to_csv(
        RUTA_SALIDA / "08_revision_codigos_ejemplo.csv",
        index=False,
        encoding="utf-8-sig"
    )


    # ============================================================
    # 5. CONCLUSIÓN AUTOMÁTICA
    # ============================================================

    problemas_geografia = sum(
        resultado["municipios_con_variacion"]
        for resultado in resultados_geografia
    )

    problemas_cultivo = sum(
        resultado["cultivos_con_variacion"]
        for resultado in resultados_cultivo
    )

    print("\n============================================================")
    print("CONCLUSIÓN")
    print("============================================================")

    if problemas_geografia == 0:
        print("GEOGRAFÍA: estable históricamente.")
    else:
        print(
            f"GEOGRAFÍA: se detectaron {problemas_geografia:,} "
            "variaciones de atributos."
        )

    if problemas_cultivo == 0:
        print("CULTIVOS: estables históricamente.")
    else:
        print(
            f"CULTIVOS: se detectaron {problemas_cultivo:,} "
            "variaciones de atributos."
        )

    print("\nArchivos generados en:")
    print(RUTA_SALIDA)

    return df

if __name__ == "__main__":
    ejecutar_validacion_historica()