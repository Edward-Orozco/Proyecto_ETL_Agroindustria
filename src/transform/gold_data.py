import pandas as pd


def agregar_eam(eam: pd.DataFrame) -> pd.DataFrame:
    """Agrega la EAM a la unidad de análisis: grupo CIIU (3 dígitos) x año."""
    print("Agregando EAM por grupo CIIU y año...")

    resumen = eam.groupby(["ciiu3", "anio"]).agg(
        n_establecimientos=("id_establecimiento", "nunique"),
        n_empresas=("id_empresa", "nunique"),
        establecimientos_sin_personal=("sin_personal", "sum"),
        personal_ocupado=("personal_ocupado", "sum"),
        produccion_bruta=("produccion_bruta", "sum"),
        valor_agregado=("valor_agregado", "sum"),
        ventas=("ventas", "sum"),
        inversion_bruta=("inversion_bruta", "sum"),
    ).reset_index()

    # Productividad del grupo: valor agregado / personal, solo con establecimientos que tienen personal
    con_personal = eam[~eam["sin_personal"]]
    productividad = (
        con_personal.groupby(["ciiu3", "anio"])
        .apply(lambda g: g["valor_agregado"].sum() / g["personal_ocupado"].sum(), include_groups=False)
        .rename("productividad_laboral")
        .reset_index()
    )

    resumen = resumen.merge(productividad, on=["ciiu3", "anio"], how="left")
    return resumen


def preparar_edit(inversion: pd.DataFrame, innovacion: pd.DataFrame) -> pd.DataFrame:
    """Une los dos cuadros de la EDIT y calcula indicadores de tecnología por grupo CIIU."""
    print("Preparando indicadores EDIT...")

    edit = inversion.merge(innovacion, on="ciiu3", how="inner")

    # Promedio del periodo 2019-2020 (miles de pesos)
    edit["inversion_acti_prom"] = edit[["inversion_total_2019", "inversion_total_2020"]].mean(axis=1)
    edit["inversion_maquinaria_prom"] = edit[["inversion_maquinaria_2019", "inversion_maquinaria_2020"]].mean(axis=1)
    edit["inversion_tic_prom"] = edit[["inversion_tic_2019", "inversion_tic_2020"]].mean(axis=1)
    edit["empresas_invirtieron_prom"] = edit[["empresas_invirtieron_2019", "empresas_invirtieron_2020"]].mean(axis=1)

    # Indicadores (porcentajes y montos por empresa)
    edit["pct_empresas_innovadoras"] = (
        (edit["innovadoras_estricto"] + edit["innovadoras_amplio"]) / edit["total_empresas_edit"] * 100
    )
    edit["pct_empresas_invierten_acti"] = edit["empresas_invirtieron_prom"] / edit["total_empresas_edit"] * 100
    edit["inversion_tic_por_empresa"] = edit["inversion_tic_prom"] / edit["total_empresas_edit"]
    edit["inversion_maquinaria_por_empresa"] = edit["inversion_maquinaria_prom"] / edit["total_empresas_edit"]

    columnas = [
        "ciiu3", "actividad_economica", "total_empresas_edit",
        "inversion_acti_prom", "inversion_maquinaria_prom", "inversion_tic_prom",
        "pct_empresas_innovadoras", "pct_empresas_invierten_acti",
        "inversion_tic_por_empresa", "inversion_maquinaria_por_empresa",
    ]
    return edit[columnas]


def calcular_indice_digitalizacion(edit: pd.DataFrame) -> pd.DataFrame:
    """Índice de digitalización e innovación (0 a 100).

    Variables (peso igual, 1/3 cada una), normalizadas con min-max entre los grupos:
      - pct_empresas_innovadoras
      - pct_empresas_invierten_acti
      - inversion_tic_por_empresa
    Es un índice relativo: 100 = grupo con mejor desempeño, 0 = grupo con menor desempeño.
    """
    variables = ["pct_empresas_innovadoras", "pct_empresas_invierten_acti", "inversion_tic_por_empresa"]
    edit = edit.copy()

    normalizadas = []
    for var in variables:
        minimo, maximo = edit[var].min(), edit[var].max()
        edit[f"{var}_norm"] = (edit[var] - minimo) / (maximo - minimo) if maximo > minimo else 0
        normalizadas.append(f"{var}_norm")

    edit["indice_digitalizacion"] = (edit[normalizadas].mean(axis=1) * 100).round(1)
    return edit.drop(columns=normalizadas)


def integrar_gold(eam_agregada: pd.DataFrame, edit: pd.DataFrame) -> pd.DataFrame:
    """JOIN final por ciiu3: tabla gold lista para análisis y Power BI."""
    print("Integrando capa gold...")

    gold = eam_agregada.merge(edit, on="ciiu3", how="left", validate="many_to_one")

    # Orden de columnas: llaves, descripción, EAM, EDIT
    primeras = ["ciiu3", "actividad_economica", "anio"]
    gold = gold[primeras + [c for c in gold.columns if c not in primeras]]

    return gold.sort_values(["ciiu3", "anio"]).reset_index(drop=True)


def validar_gold(gold: pd.DataFrame, grupos_agro: list) -> dict:
    """Métricas de calidad e integración (sirven como evidencia de los KR)."""
    grupos_con_edit = gold.dropna(subset=["actividad_economica"])["ciiu3"].nunique()
    return {
        "filas": len(gold),
        "cobertura_grupos_pct": round(grupos_con_edit / len(grupos_agro) * 100, 1),
        "celdas_nulas": int(gold.isna().sum().sum()),
        "duplicados_llave": int(gold.duplicated(subset=["ciiu3", "anio"]).sum()),
    }