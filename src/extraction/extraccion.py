import pandas as pd

def ejecutar_extraccion():
    ruta_fuente = "data/raw/Evaluaciones_Agropecuarias_Municipales_–_EVA._2019_-_2025._Base_Agrícola_20260905.csv"
    ruta_raw = "data/raw/eva_agricola_raw.csv"

    df = pd.read_csv(
        ruta_fuente,
        sep=",",
        encoding="utf-8"
    )

    print(f"Registros extraídos: {len(df):,}")
    print(f"Columnas extraídas: {len(df.columns)}")
    print(df.columns.tolist())

    df.to_csv(
        ruta_raw,
        index=False,
        encoding="utf-8"
    )

    return df

if __name__ == "__main__":
    ejecutar_extraccion()