-- =====================================================================
-- Modelo dimensional (esquema estrella) - Agroindustria colombiana
-- Base de datos: etl_agroindustria   Esquema: agroindustria
-- =====================================================================

DROP SCHEMA IF EXISTS agroindustria CASCADE;
CREATE SCHEMA agroindustria;
SET search_path TO agroindustria;

-- ---------------------------------------------------------------------
-- DIMENSIONES
-- ---------------------------------------------------------------------
CREATE TABLE dim_subsector (
    ciiu3               SMALLINT PRIMARY KEY,
    nombre_corto        VARCHAR(40)  NOT NULL,
    actividad_economica VARCHAR(200) NOT NULL
);

CREATE TABLE dim_departamento (
    cod_departamento SMALLINT PRIMARY KEY,
    departamento     VARCHAR(40) NOT NULL
);

CREATE TABLE dim_tiempo (
    anio   SMALLINT PRIMARY KEY,
    fuente VARCHAR(40) NOT NULL
);

-- ---------------------------------------------------------------------
-- HECHOS
-- ---------------------------------------------------------------------
-- Grano: un establecimiento en un año (EAM)
CREATE TABLE fact_establecimiento (
    id_establecimiento    INTEGER  NOT NULL,
    anio                  SMALLINT NOT NULL REFERENCES dim_tiempo (anio),
    id_empresa            INTEGER  NOT NULL,
    ciiu4                 SMALLINT NOT NULL,
    ciiu3                 SMALLINT NOT NULL REFERENCES dim_subsector (ciiu3),
    cod_departamento      SMALLINT NOT NULL REFERENCES dim_departamento (cod_departamento),
    personal_ocupado      NUMERIC(12, 0),
    produccion_bruta      NUMERIC(18, 0),
    valor_agregado        NUMERIC(18, 0),
    ventas                NUMERIC(18, 0),
    inversion_bruta       NUMERIC(18, 0),
    sin_personal          BOOLEAN  NOT NULL,
    productividad_laboral NUMERIC(18, 2),
    PRIMARY KEY (id_establecimiento, anio)
);

-- Grano: un subsector en un año (EAM agregada)
CREATE TABLE fact_subsector_anio (
    ciiu3                         SMALLINT NOT NULL REFERENCES dim_subsector (ciiu3),
    anio                          SMALLINT NOT NULL REFERENCES dim_tiempo (anio),
    n_establecimientos            INTEGER  NOT NULL,
    n_empresas                    INTEGER  NOT NULL,
    establecimientos_sin_personal INTEGER  NOT NULL,
    personal_ocupado              NUMERIC(14, 0),
    produccion_bruta              NUMERIC(20, 0),
    valor_agregado                NUMERIC(20, 0),
    ventas                        NUMERIC(20, 0),
    inversion_bruta               NUMERIC(20, 0),
    productividad_laboral         NUMERIC(18, 2),
    PRIMARY KEY (ciiu3, anio)
);

-- Grano: un subsector, periodo 2019-2020 (EDIT)
CREATE TABLE fact_tecnologia_subsector (
    ciiu3                            SMALLINT PRIMARY KEY REFERENCES dim_subsector (ciiu3),
    periodo                          VARCHAR(10) NOT NULL,
    total_empresas_edit              INTEGER  NOT NULL,
    inversion_acti_prom              NUMERIC(18, 2),
    inversion_maquinaria_prom        NUMERIC(18, 2),
    inversion_tic_prom               NUMERIC(18, 2),
    pct_empresas_innovadoras         NUMERIC(6, 2),
    pct_empresas_invierten_acti      NUMERIC(6, 2),
    inversion_tic_por_empresa        NUMERIC(18, 2),
    inversion_maquinaria_por_empresa NUMERIC(18, 2),
    indice_digitalizacion            NUMERIC(5, 1)
);

-- Referencia nacional (no se une por subsector)
CREATE TABLE ref_tic_nacional (
    indicador  VARCHAR(120) PRIMARY KEY,
    empresas   INTEGER NOT NULL,
    porcentaje NUMERIC(6, 2),
    anio       SMALLINT NOT NULL
);

-- Índices para las consultas más frecuentes
CREATE INDEX idx_establecimiento_subsector ON fact_establecimiento (ciiu3, anio);
CREATE INDEX idx_establecimiento_departamento ON fact_establecimiento (cod_departamento);

-- ---------------------------------------------------------------------
-- VISTA ANALÍTICA (equivale a la tabla gold, lista para Power BI)
-- ---------------------------------------------------------------------
CREATE VIEW vw_subsector_digitalizacion AS
SELECT
    s.ciiu3,
    s.nombre_corto,
    s.actividad_economica,
    f.anio,
    f.n_establecimientos,
    f.personal_ocupado,
    f.valor_agregado,
    f.productividad_laboral,
    t.pct_empresas_innovadoras,
    t.pct_empresas_invierten_acti,
    t.inversion_tic_por_empresa,
    t.inversion_maquinaria_por_empresa,
    t.indice_digitalizacion
FROM fact_subsector_anio f
JOIN dim_subsector s ON s.ciiu3 = f.ciiu3
LEFT JOIN fact_tecnologia_subsector t ON t.ciiu3 = f.ciiu3;