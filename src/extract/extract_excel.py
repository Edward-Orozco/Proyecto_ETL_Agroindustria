import pandas as pd


def extraer_anexo(ruta: str, hoja: str, fila_inicio: int) -> pd.DataFrame:
    """Lee una hoja de un anexo del DANE saltando los títulos de la parte superior.

    Los encabezados de los anexos tienen celdas combinadas, por eso se leen
    sin encabezado (header=None) y los nombres de columna se asignan en la
    etapa de transformación.
    """
    print(f"Empezando a extraer la hoja {hoja} de {ruta}...")

    df = pd.read_excel(ruta, sheet_name=hoja, header=None, skiprows=fila_inicio)

    # Quitar filas y columnas completamente vacías
    df = df.dropna(how="all").dropna(axis=1, how="all")

    print(f"Hoja {hoja} extraída: {df.shape[0]} filas y {df.shape[1]} columnas")
    return df