from pathlib import Path

import pandas as pd


def guardar_parquet(df: pd.DataFrame, carpeta: Path, nombre: str) -> Path:
    """Guarda un DataFrame en formato Parquet dentro de la carpeta indicada."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre}.parquet"
    df.to_parquet(ruta, index=False)
    print(f"Guardado: {ruta}")
    return ruta


def guardar_csv(df: pd.DataFrame, carpeta: Path, nombre: str) -> Path:
    """Guarda un DataFrame en CSV."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre}.csv"
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    print(f"Guardado: {ruta}")
    return ruta