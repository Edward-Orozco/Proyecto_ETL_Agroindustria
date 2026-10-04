import pandas as pd


def limpiar_edit_inversion(df: pd.DataFrame, grupos_agro: list) -> pd.DataFrame:
    """Cuadro 2.1 EDIT: inversión en actividades científicas, tecnológicas y de innovación (miles de pesos)."""
    print("Empezando a limpiar EDIT inversión...")

    # Seleccionar y renombrar solo las columnas que se usan (posiciones del cuadro 2.1)
    columnas = {
        0: "ciiu3",
        1: "actividad_economica",
        2: "empresas_invirtieron_2019",
        3: "inversion_total_2019",
        4: "empresas_invirtieron_2020",
        5: "inversion_total_2020",
        10: "inversion_maquinaria_2019",
        11: "inversion_maquinaria_2020",
        12: "inversion_tic_2019",
        13: "inversion_tic_2020",
    }
    df = df[list(columnas.keys())].rename(columns=columnas)

    # Llave numérica: elimina filas como 'Total', notas al pie o agregaciones '141-143'
    df["ciiu3"] = pd.to_numeric(df["ciiu3"], errors="coerce")
    df = df.dropna(subset=["ciiu3"])
    df["ciiu3"] = df["ciiu3"].astype(int)
    df = df[df["ciiu3"].isin(grupos_agro)]

    # En los anexos del DANE una celda vacía significa cero
    numericas = df.columns.drop(["ciiu3", "actividad_economica"])
    df[numericas] = df[numericas].apply(pd.to_numeric, errors="coerce").fillna(0)

    df["actividad_economica"] = df["actividad_economica"].str.strip()

    print(f"EDIT inversión limpia: {df.shape[0]} grupos")
    return df.reset_index(drop=True)


def limpiar_edit_innovacion(df: pd.DataFrame, grupos_agro: list) -> pd.DataFrame:
    """Cuadro 1.1 EDIT: número de empresas según tipología de innovación."""
    print("Empezando a limpiar EDIT innovación...")

    columnas = {
        0: "ciiu3",
        2: "total_empresas_edit",
        3: "innovadoras_estricto",
        4: "innovadoras_amplio",
        7: "potencialmente_innovadoras",
        8: "no_innovadoras",
    }
    df = df[list(columnas.keys())].rename(columns=columnas)

    df["ciiu3"] = pd.to_numeric(df["ciiu3"], errors="coerce")
    df = df.dropna(subset=["ciiu3"])
    df["ciiu3"] = df["ciiu3"].astype(int)
    df = df[df["ciiu3"].isin(grupos_agro)]

    numericas = df.columns.drop("ciiu3")
    df[numericas] = df[numericas].apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)

    print(f"EDIT innovación limpia: {df.shape[0]} grupos")
    return df.reset_index(drop=True)


def limpiar_tic(df: pd.DataFrame) -> pd.DataFrame:
    """Cuadro 1 TIC: referencia nacional de uso de herramientas TIC en la industria."""
    print("Empezando a limpiar TIC...")

    df = df.iloc[:, :3].copy()
    df.columns = ["indicador", "empresas", "porcentaje"]

    # Quitar notas al pie: se conservan solo filas con número de empresas
    df["empresas"] = pd.to_numeric(df["empresas"], errors="coerce")
    df = df.dropna(subset=["empresas"])

    # 'N.A.' -> NaN y quitar números de nota al pie pegados al texto ('Usan computador3')
    df["porcentaje"] = pd.to_numeric(df["porcentaje"], errors="coerce").round(2)
    df["indicador"] = df["indicador"].str.strip().str.replace(r"\d+$", "", regex=True)
    df["empresas"] = df["empresas"].astype(int)
    df["anio"] = 2024

    print(f"TIC limpia: {df.shape[0]} indicadores")
    return df.reset_index(drop=True)