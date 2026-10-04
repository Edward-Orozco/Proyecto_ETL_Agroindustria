import numpy as np
import pandas as pd


def limpiar_eam(df: pd.DataFrame, grupos_agro: list) -> pd.DataFrame:
    """Limpia la EAM: tipos de dato, homologación CIIU, filtro agroindustrial y nombres claros."""
    print("Empezando a limpiar EAM...")

    df = df.copy()

    # 1. Eliminar duplicados
    df = df.drop_duplicates()

    # 2. Convertir llaves a entero (en el .dta vienen como decimales: 1040.0)
    for col in ["nordemp", "nordest", "dpto", "ciiu4", "periodo"]:
        df[col] = df[col].astype(int)

    # 3. Homologación: CIIU 4 dígitos -> grupo de 3 dígitos (1040 -> 104)
    df["ciiu3"] = df["ciiu4"] // 10

    # 4. Filtrar solo la agroindustria
    df = df[df["ciiu3"].isin(grupos_agro)]

    # 5. Renombrar columnas a nombres descriptivos
    df = df.rename(columns={
        "nordemp": "id_empresa",
        "nordest": "id_establecimiento",
        "dpto": "cod_departamento",
        "periodo": "anio",
        "PERSOCU": "personal_ocupado",
        "PRODBR2": "produccion_bruta",
        "VALAGRI": "valor_agregado",
        "VALORVEN": "ventas",
        "INVEBRTA": "inversion_bruta",
    })

    # 6. Marcar establecimientos sin personal (no sirven para calcular productividad)
    df["sin_personal"] = df["personal_ocupado"] == 0

    # 7. Productividad laboral por establecimiento (NaN si no hay personal)
    df["productividad_laboral"] = np.where(
        df["sin_personal"], np.nan, df["valor_agregado"] / df["personal_ocupado"]
    )

    print(f"EAM limpia: {df.shape[0]} establecimientos agroindustriales")
    return df.reset_index(drop=True)