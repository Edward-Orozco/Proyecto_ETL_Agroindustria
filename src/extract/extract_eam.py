import pandas as pd


def extraer_eam(ruta: str, tipo_archivo: str, columnas: list) -> pd.DataFrame:
    """Lee la Encuesta Anual Manufacturera (EAM) y devuelve solo las columnas indicadas."""
    print(f"Empezando a extraer EAM desde {ruta}...")

    if tipo_archivo == "stata":
        df = pd.read_stata(ruta, columns=columnas, convert_categoricals=False)
    elif tipo_archivo == "csv":
        df = pd.read_csv(ruta, usecols=columnas)
    else:
        raise ValueError(f"Tipo de archivo no soportado: {tipo_archivo}")

    print(f"EAM extraída: {df.shape[0]} filas y {df.shape[1]} columnas")
    return df