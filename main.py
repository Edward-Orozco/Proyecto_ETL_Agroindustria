import datetime
from pathlib import Path

import pandas as pd
import yaml

# Mis módulos
import src.extract.extract_eam as eam
import src.extract.extract_excel as anexos
import src.transform.clean_eam as clean_eam
import src.transform.clean_anexos as clean_anexos
import src.transform.gold_data as gold_data
import src.load.save_files as save
import src.load.load_postgres as pg

# Carpeta raíz del proyecto (donde está este main.py)
BASE_DIR = Path(__file__).resolve().parent


def escribir_log(mensaje: str, ruta_log: Path, nivel: str = "INFO") -> None:
    """Agrega una línea con fecha, hora y nivel (INFO o ERROR) al archivo de logs."""
    with open(ruta_log, "a", encoding="utf-8") as file:
        file.write(f"{datetime.datetime.now()} - {nivel} - {mensaje}\n")


def main():
    # 1. Leer el archivo de configuración
    with open(BASE_DIR / "config" / "config.yaml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    ruta_log = BASE_DIR / config["path"]["logs_file"]
    silver_dir = BASE_DIR / config["path"]["silver_dir"]
    gold_dir = BASE_DIR / config["path"]["gold_dir"]
    fuentes = config["sources"]
    columnas_eam = config["constant"]["columnas_eam"]
    grupos_agro = config["constant"]["grupos_agro"]

    # 2. Extracción (capa bronze)
    escribir_log("Iniciando la extracción", ruta_log)

    datos_extraidos = {}

    for nombre, fuente in fuentes.items():
        ruta = BASE_DIR / fuente["path"]
        try:
            if fuente["file_type"] in ["stata", "csv"]:
                df = eam.extraer_eam(ruta, fuente["file_type"], columnas_eam)
            elif fuente["file_type"] == "excel":
                df = anexos.extraer_anexo(ruta, fuente["sheet"], fuente["header_row"])
            else:
                raise ValueError(f"Tipo de archivo no soportado: {fuente['file_type']}")

            datos_extraidos[nombre] = df
            escribir_log(f"Fuente '{nombre}' extraída: {df.shape[0]} filas, {df.shape[1]} columnas", ruta_log)

        except Exception as error:
            print(f"Error extrayendo '{nombre}': {error}")
            escribir_log(f"Extrayendo '{nombre}': {error}", ruta_log, "ERROR")

    escribir_log(f"Extracción finalizada: {len(datos_extraidos)} de {len(fuentes)} fuentes", ruta_log)

    # 3. Transformación (capa silver)
    escribir_log("Iniciando la transformación silver", ruta_log)

    # Unir las dos EAM en una sola tabla antes de limpiar
    eam_unida = pd.concat([datos_extraidos["eam_2021"], datos_extraidos["eam_2024"]], ignore_index=True)

    silver = {
        "eam_agro": clean_eam.limpiar_eam(eam_unida, grupos_agro),
        "edit_inversion": clean_anexos.limpiar_edit_inversion(datos_extraidos["edit_inversion"], grupos_agro),
        "edit_innovacion": clean_anexos.limpiar_edit_innovacion(datos_extraidos["edit_innovacion"], grupos_agro),
        "tic_industria": clean_anexos.limpiar_tic(datos_extraidos["tic_industria"]),
    }

    for nombre, df in silver.items():
        save.guardar_parquet(df, silver_dir, nombre)
        escribir_log(f"Silver '{nombre}' guardada: {df.shape[0]} filas, {df.shape[1]} columnas", ruta_log)

    sin_personal = silver["eam_agro"]["sin_personal"].sum()
    escribir_log(f"Calidad: {sin_personal} establecimientos sin personal ocupado (excluidos de productividad)", ruta_log)

        # 4. Integración (capa gold)
    escribir_log("Iniciando la integración gold", ruta_log)

    eam_agregada = gold_data.agregar_eam(silver["eam_agro"])
    edit = gold_data.preparar_edit(silver["edit_inversion"], silver["edit_innovacion"])
    edit = gold_data.calcular_indice_digitalizacion(edit)
    gold = gold_data.integrar_gold(eam_agregada, edit)

    # Validación de calidad e integración
    metricas = gold_data.validar_gold(gold, grupos_agro)
    escribir_log(f"Validación gold: {metricas}", ruta_log)
    if metricas["cobertura_grupos_pct"] < 100 or metricas["duplicados_llave"] > 0:
        escribir_log("La tabla gold no cumple la validación de integración", ruta_log, "ERROR")

    # 5. Carga (gold en Parquet y CSV + referencia nacional TIC)
    save.guardar_parquet(gold, gold_dir, "gold_agroindustria")
    save.guardar_csv(gold, gold_dir, "gold_agroindustria")
    save.guardar_csv(silver["tic_industria"], gold_dir, "referencia_tic_nacional")
    escribir_log(f"Gold guardada: {gold.shape[0]} filas, {gold.shape[1]} columnas", ruta_log)
    
    # 6. Carga en PostgreSQL (modelo estrella)
    escribir_log("Iniciando la carga en PostgreSQL", ruta_log)
    try:
        engine = pg.crear_conexion()
        pg.crear_esquema(engine, BASE_DIR / config["path"]["sql_schema"])
        tablas = pg.construir_tablas(silver, gold, config["constant"]["nombres_subsector"], config["constant"]["departamentos"])
        conteos = pg.cargar_tablas(engine, tablas)

        # Validación: filas en la base = filas en los DataFrames
        for nombre, df in tablas.items():
            estado = "INFO" if conteos[nombre] == len(df) else "ERROR"
            escribir_log(f"PostgreSQL '{nombre}': {conteos[nombre]} de {len(df)} filas", ruta_log, estado)
    except Exception as error:
        print(f"Error en la carga a PostgreSQL: {error}")
        escribir_log(f"Carga PostgreSQL: {error}", ruta_log, "ERROR")

    escribir_log("Pipeline finalizado", ruta_log)

if __name__ == "__main__":
    main()