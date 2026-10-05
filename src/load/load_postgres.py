import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ESQUEMA = "agroindustria"


def crear_conexion():
    """Crea la conexión a PostgreSQL con las credenciales del archivo .env."""
    load_dotenv()
    url = (
        f"postgresql+psycopg2://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}"
        f"@{os.getenv('PG_HOST', 'localhost')}:{os.getenv('PG_PORT', '5432')}/{os.getenv('PG_DATABASE')}"
    )
    return create_engine(url)


def crear_esquema(engine, ruta_sql: Path) -> None:
    """Ejecuta el script SQL que crea el esquema, las tablas, las llaves y la vista."""
    with engine.begin() as conexion:
        conexion.execute(text(ruta_sql.read_text(encoding="utf-8")))
    print("Esquema creado")


def construir_tablas(silver: dict, gold: pd.DataFrame, nombres_subsector: dict, departamentos: dict) -> dict:
    """Arma las tablas del modelo estrella a partir de las capas silver y gold."""
    eam = silver["eam_agro"]

    dim_subsector = (
        gold[["ciiu3", "actividad_economica"]].drop_duplicates()
        .assign(nombre_corto=lambda d: d["ciiu3"].map(nombres_subsector))
        [["ciiu3", "nombre_corto", "actividad_economica"]]
    )

    dim_departamento = pd.DataFrame(
        {"cod_departamento": list(departamentos.keys()), "departamento": list(departamentos.values())}
    )

    dim_tiempo = pd.DataFrame({"anio": sorted(eam["anio"].unique())}).assign(fuente="EAM")

    fact_establecimiento = eam[[
        "id_establecimiento", "anio", "id_empresa", "ciiu4", "ciiu3", "cod_departamento",
        "personal_ocupado", "produccion_bruta", "valor_agregado", "ventas", "inversion_bruta",
        "sin_personal", "productividad_laboral",
    ]]

    fact_subsector_anio = gold[[
        "ciiu3", "anio", "n_establecimientos", "n_empresas", "establecimientos_sin_personal",
        "personal_ocupado", "produccion_bruta", "valor_agregado", "ventas", "inversion_bruta",
        "productividad_laboral",
    ]]

    fact_tecnologia_subsector = (
        gold.drop_duplicates("ciiu3")[[
            "ciiu3", "total_empresas_edit", "inversion_acti_prom", "inversion_maquinaria_prom",
            "inversion_tic_prom", "pct_empresas_innovadoras", "pct_empresas_invierten_acti",
            "inversion_tic_por_empresa", "inversion_maquinaria_por_empresa", "indice_digitalizacion",
        ]]
        .assign(periodo="2019-2020")
    )

    # Orden importante: primero dimensiones, después hechos (por las llaves foráneas)
    return {
        "dim_subsector": dim_subsector,
        "dim_departamento": dim_departamento,
        "dim_tiempo": dim_tiempo,
        "fact_establecimiento": fact_establecimiento,
        "fact_subsector_anio": fact_subsector_anio,
        "fact_tecnologia_subsector": fact_tecnologia_subsector,
        "ref_tic_nacional": silver["tic_industria"],
    }


def cargar_tablas(engine, tablas: dict) -> dict:
    """Inserta cada tabla en PostgreSQL y devuelve cuántas filas quedaron en la base."""
    conteos = {}
    for nombre, df in tablas.items():
        df.to_sql(nombre, engine, schema=ESQUEMA, if_exists="append", index=False, method="multi", chunksize=1000)
        with engine.connect() as conexion:
            conteos[nombre] = conexion.execute(text(f"SELECT COUNT(*) FROM {ESQUEMA}.{nombre}")).scalar()
        print(f"Cargada {nombre}: {conteos[nombre]} filas")
    return conteos