import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Permite importar los módulos de src/ desde la carpeta dashboard/
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
from src.load.load_postgres import crear_conexion  # noqa: E402

st.set_page_config(page_title="Agroindustria colombiana", page_icon="🌾", layout="wide")

# Paleta del dashboard: verde (acento, igual al tema de .streamlit/config.toml) y gris (contexto)
VERDE, GRIS = "#2E7D32", "#B5BDB0"


# ---------------------------------------------------------------------
# 1. DATOS (desde PostgreSQL, con caché)
# ---------------------------------------------------------------------
@st.cache_data
def cargar_subsectores() -> pd.DataFrame:
    """Vista analítica: un subsector por año, con productividad e indicadores EDIT."""
    return pd.read_sql("SELECT * FROM agroindustria.vw_subsector_digitalizacion", crear_conexion())


@st.cache_data
def cargar_departamentos() -> pd.DataFrame:
    """Establecimientos por departamento, subsector y año (agregado en la base de datos)."""
    consulta = """
        SELECT d.departamento, f.anio, f.ciiu3,
               COUNT(*)                AS n_establecimientos,
               SUM(f.personal_ocupado) AS personal_ocupado
        FROM agroindustria.fact_establecimiento f
        JOIN agroindustria.dim_departamento d ON d.cod_departamento = f.cod_departamento
        GROUP BY d.departamento, f.anio, f.ciiu3
    """
    return pd.read_sql(consulta, crear_conexion())


def miles(valor: float) -> str:
    """Formato colombiano: 1.287 en lugar de 1,287."""
    return f"{valor:,.0f}".replace(",", ".")


subsectores = cargar_subsectores()
departamentos = cargar_departamentos()

# ---------------------------------------------------------------------
# 2. FILTROS (barra lateral)
# ---------------------------------------------------------------------
st.sidebar.header("Filtros")
anio = st.sidebar.radio("Año", sorted(subsectores["anio"].unique(), reverse=True), horizontal=True)
todos = sorted(subsectores["nombre_corto"].unique())
seleccion = st.sidebar.multiselect("Subsectores", todos, default=todos)
st.sidebar.caption("El índice de digitalización proviene de la EDIT 2019-2020 y no cambia con el año.")

if not seleccion:
    st.warning("Selecciona al menos un subsector en la barra lateral.")
    st.stop()

datos = subsectores[subsectores["nombre_corto"].isin(seleccion)]
datos_anio = datos[datos["anio"] == anio]
ciiu_sel = datos["ciiu3"].unique()

# ---------------------------------------------------------------------
# 3. ENCABEZADO E INDICADORES
# ---------------------------------------------------------------------
st.title("🌾 Digitalización y productividad de la agroindustria colombiana")
st.caption("Fuente: DANE (EAM 2021 y 2024, EDIT 2019-2020) · Pipeline ETL propio · Base de datos PostgreSQL · "
           "Valores monetarios en pesos colombianos corrientes")


def productividad(df: pd.DataFrame) -> float:
    return df["valor_agregado"].sum() / df["personal_ocupado"].sum()


anterior = datos[datos["anio"] == 2021]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Subsectores", len(seleccion))
col2.metric(
    f"Establecimientos {anio}", miles(datos_anio["n_establecimientos"].sum()),
    delta=None if anio == 2021 else miles(datos_anio["n_establecimientos"].sum() - anterior["n_establecimientos"].sum()) + " vs 2021",
)
col3.metric(
    f"Productividad {anio} (millones de $ por persona)", miles(productividad(datos_anio) / 1000),
    delta=None if anio == 2021 else f"{(productividad(datos_anio) / productividad(anterior) - 1) * 100:.1f} % vs 2021".replace(".", ","),
)
col4.metric("Índice de digitalización promedio", f"{datos_anio['indice_digitalizacion'].mean():.1f}".replace(".", ","))

# ---------------------------------------------------------------------
# 4. HISTORIA EN PESTAÑAS
# ---------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["1. Rezago digital", "2. ¿Digital = productivo?", "3. Evolución", "4. Territorio", "5. Datos"]
)

# 4.1 Ranking del índice
with tab1:
    ranking = datos_anio.sort_values("indice_digitalizacion")
    rezagados = ranking[ranking["indice_digitalizacion"] < 20]["nombre_corto"].tolist()
    st.subheader("¿Qué subsectores están más rezagados en digitalización?")
    if rezagados:
        verbo = "tiene" if len(rezagados) == 1 else "tienen"
        st.info(f"**{', '.join(rezagados)}** {verbo} un índice menor a 20 sobre 100.")
    fig = px.bar(
        ranking, x="indice_digitalizacion", y="nombre_corto", orientation="h", text="indice_digitalizacion",
        color=ranking["indice_digitalizacion"] < 20, color_discrete_map={True: VERDE, False: GRIS},
        labels={"indice_digitalizacion": "Índice de digitalización e innovación (0 a 100)", "nombre_corto": ""},
        hover_data={"pct_empresas_innovadoras": ":.1f", "inversion_tic_por_empresa": ":,.0f"},
        custom_data=["pct_empresas_innovadoras", "inversion_tic_por_empresa"],
    )
    fig.update_traces(
        texttemplate="%{text:.1f}", textposition="outside",
        hovertemplate="<b>%{y}</b><br>Índice: %{x:.1f}<br>Empresas innovadoras: %{customdata[0]:.1f} %"
                      "<br>Inversión TIC por empresa: $ %{customdata[1]:,.0f} mil<extra></extra>",
    )
    fig.update_layout(showlegend=False, xaxis_range=[0, 105], height=420)
    st.plotly_chart(fig, width="stretch")

# 4.2 Índice vs productividad
with tab2:
    corr = datos_anio["indice_digitalizacion"].corr(datos_anio["productividad_laboral"])
    st.subheader("¿Más digitalización significa más productividad?")
    if len(datos_anio) > 2:
        mensaje = f"La correlación entre índice y productividad en {anio} es **{corr:.2f}**".replace(".", ",") + "."
        if "Café" in seleccion:
            mensaje += " El café tiene el índice más bajo y una de las productividades más altas."
        st.info(mensaje)
    else:
        st.info("Selecciona al menos 3 subsectores para calcular la correlación.")
    fig = px.scatter(
        datos_anio, x="indice_digitalizacion", y=datos_anio["productividad_laboral"] / 1000,
        size="n_establecimientos", text="nombre_corto", size_max=45,
        color=datos_anio["nombre_corto"] == "Café", color_discrete_map={True: VERDE, False: GRIS},
        labels={"indice_digitalizacion": "Índice de digitalización (0 a 100)", "y": f"Productividad {anio} (millones de $ por persona)"},
    )
    fig.add_hline(y=productividad(datos_anio) / 1000, line_dash="dash", line_color="gray",
                  annotation_text="Productividad del conjunto", annotation_position="top left")
    fig.update_traces(textposition="top center")
    fig.update_layout(showlegend=False, height=480, xaxis_range=[-5, 105])
    st.plotly_chart(fig, width="stretch")
    st.caption("Tamaño de la burbuja = número de establecimientos.")

# 4.3 Productividad 2021 vs 2024
with tab3:
    st.subheader("¿Cómo cambió la productividad entre 2021 y 2024?")
    evolucion = datos.sort_values(["anio", "productividad_laboral"])
    subieron = (datos.pivot(index="nombre_corto", columns="anio", values="productividad_laboral").diff(axis=1)[2024] > 0).sum()
    st.info(f"La productividad subió en **{subieron} de {len(seleccion)}** subsectores (pesos corrientes, sin ajustar por inflación).")
    fig = px.bar(
        evolucion, x=evolucion["productividad_laboral"] / 1000, y="nombre_corto", color=evolucion["anio"].astype(str),
        barmode="group", orientation="h", color_discrete_map={"2021": GRIS, "2024": VERDE},
        labels={"x": "Productividad (millones de $ por persona ocupada)", "nombre_corto": "", "color": "Año"},
    )
    fig.update_layout(height=480)
    st.plotly_chart(fig, width="stretch")

# 4.4 Departamentos
with tab4:
    st.subheader("¿Dónde se concentra la agroindustria?")
    dpto = (departamentos[(departamentos["anio"] == anio) & (departamentos["ciiu3"].isin(ciiu_sel))]
            .groupby("departamento", as_index=False)["n_establecimientos"].sum()
            .sort_values("n_establecimientos", ascending=False))
    pct_top5 = dpto.head(5)["n_establecimientos"].sum() / dpto["n_establecimientos"].sum() * 100
    st.info(f"5 departamentos concentran el **{pct_top5:.0f} %** de los establecimientos de los subsectores seleccionados.")
    top = dpto.head(10).sort_values("n_establecimientos")
    fig = px.bar(
        top, x="n_establecimientos", y="departamento", orientation="h", text="n_establecimientos",
        color=top["departamento"].isin(dpto.head(5)["departamento"]), color_discrete_map={True: VERDE, False: GRIS},
        labels={"n_establecimientos": f"Establecimientos {anio}", "departamento": ""},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, height=440)
    st.plotly_chart(fig, width="stretch")

# 4.5 Tabla
with tab5:
    st.subheader("Datos de la capa gold (vista en PostgreSQL)")
    st.caption("La EAM y la EDIT reportan los montos en **miles de pesos**. Aquí se convierten a millones "
               "o billones de pesos para facilitar la lectura. Pasa el mouse sobre cada encabezado para ver qué mide.")

    # 1. Convertir unidades (la base guarda miles de pesos)
    #    miles de pesos / 1.000     = millones de pesos
    #    miles de pesos / 1.000.000.000 = billones de pesos
    tabla = datos_anio.assign(
        valor_agregado_bill=datos_anio["valor_agregado"] / 1_000_000_000,
        productividad_mm=datos_anio["productividad_laboral"] / 1_000,
        tic_mm=datos_anio["inversion_tic_por_empresa"] / 1_000,
        maquinaria_mm=datos_anio["inversion_maquinaria_por_empresa"] / 1_000,
    )[[
        "ciiu3", "nombre_corto", "anio", "n_establecimientos", "personal_ocupado", "valor_agregado_bill",
        "productividad_mm", "pct_empresas_innovadoras", "pct_empresas_invierten_acti", "tic_mm",
        "maquinaria_mm", "indice_digitalizacion",
    ]]

    # 2. Dar formato: cada valor muestra su unidad (est., personas, $, %, pts)
    st.dataframe(
        tabla, width="stretch", hide_index=True,
        column_config={
            "ciiu3": st.column_config.NumberColumn("CIIU", format="%d"),
            "nombre_corto": st.column_config.TextColumn("Subsector"),
            "anio": st.column_config.NumberColumn("Año", format="%d"),
            # Unidades (conteos)
            "n_establecimientos": st.column_config.NumberColumn(
                "Establecimientos", format="%d est.", help="Número de establecimientos (unidades)"),
            "personal_ocupado": st.column_config.NumberColumn(
                "Personal ocupado", format="%d personas", help="Número de personas que trabajan en el subsector"),
            # Valores monetarios
            "valor_agregado_bill": st.column_config.NumberColumn(
                "Valor agregado", format="$ %.2f billones", help="Billones de pesos corrientes en el año"),
            "productividad_mm": st.column_config.NumberColumn(
                "Productividad", format="$ %.1f M por persona",
                help="Millones de pesos de valor agregado por persona ocupada en el año"),
            "tic_mm": st.column_config.NumberColumn(
                "Inversión TIC por empresa", format="$ %.1f M", help="Millones de pesos, promedio 2019-2020"),
            "maquinaria_mm": st.column_config.NumberColumn(
                "Inversión maquinaria por empresa", format="$ %.1f M", help="Millones de pesos, promedio 2019-2020"),
            # Porcentajes
            "pct_empresas_innovadoras": st.column_config.NumberColumn(
                "Empresas innovadoras", format="%.1f %%", help="Porcentaje de empresas (EDIT 2019-2020)"),
            "pct_empresas_invierten_acti": st.column_config.NumberColumn(
                "Invierten en ACTI", format="%.1f %%", help="Porcentaje de empresas (EDIT 2019-2020)"),
            # Índice (puntos de 0 a 100)
            "indice_digitalizacion": st.column_config.ProgressColumn(
                "Índice de digitalización", format="%.1f pts", min_value=0, max_value=100,
                help="Índice relativo de 0 a 100 puntos"),
        },
    )
    st.download_button("Descargar CSV", datos_anio.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"agroindustria_{anio}.csv", mime="text/csv")