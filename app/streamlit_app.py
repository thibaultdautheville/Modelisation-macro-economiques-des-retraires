
"""Interface experimentale du simulateur de retraites."""

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from src.simulation import run_aod_simulation


st.set_page_config(
    page_title="Simulateur des retraites - MEDEF",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def simulate(
    baseline_aod_months: int,
    reform_aod_months: int,
    behavioural_delay_share: float,
    absorption_rate: float,
    transition_method: str,
    effective_date: date | None,
) -> dict:
    return run_aod_simulation(
        scenario_id="benchmark_aod_plus_1",
        baseline_aod_months=baseline_aod_months,
        reform_aod_months=reform_aod_months,
        behavioural_delay_share=behavioural_delay_share,
        absorption_rate=absorption_rate,
        transition_method=transition_method,
        effective_date=effective_date,
    )


def annual_series(results: dict) -> pd.DataFrame:
    stock = results["transition_stock_selection"][
        ["year", "selected_delayed_stock"]
    ].copy()

    labour = results["labour_trajectory"][
        [
            "year",
            "delta_labour_force_reform",
            "delta_employment_reform",
            "delta_unemployment_reform",
        ]
    ].copy()

    return stock.merge(
        labour,
        on="year",
        validate="one_to_one",
    )


st.title("Simulateur macroeconomique des retraites")
st.caption("MEDEF | Prototype experimental V0.1 | Horizon 2026-2070")

st.warning(
    "Les resultats sont exploratoires. La calibration des "
    "liquidations et les comportements sur le marche du travail "
    "ne sont pas encore valides economiquement."
)

with st.sidebar:
    st.header("Parametres du scenario")

    baseline_age = 64

    st.number_input(
        "AOD de reference (annees)",
        value=64,
        disabled=True,
    )

    increase_months = 12

    st.number_input(
    "Relevement de l'AOD (mois)",
    value=12,
    disabled=True,
    )

    st.caption(
    "Le moteur V0.1 valide actuellement le scenario "
    "juridique de relèvement de 12 mois."
    )

    behavioural_delay_share = st.slider(
        "Part des liquidations retardees avec effet sur l'activite",
        min_value=0.0,
        max_value=1.0,
        value=1.0,
        step=0.05,
    )

    absorption_rate = st.slider(
        "Taux d'absorption en emploi",
        min_value=0.0,
        max_value=1.0,
        value=1.0,
        step=0.05,
    )

    transition_method = st.selectbox(
        "Methode de transition",
        options=[
            "historique",
            "calendrier_cohortes",
            "double_ajustement",
        ],
        format_func=lambda value: {
            "historique": "Historique",
            "calendrier_cohortes": "Calendrier par cohortes",
            "double_ajustement": "Double ajustement (diagnostic)",
        }[value],
    )

    effective_date = None

    if transition_method != "historique":
        effective_date = st.date_input(
            "Date d'effet candidate",
            value=date(2026, 9, 1),
        )
        st.caption(
            "Date de simulation, non validee juridiquement."
        )

    launch = st.button(
        "Calculer le scenario",
        type="primary",
        use_container_width=True,
    )

if "simulation_results" not in st.session_state:
    st.session_state["simulation_results"] = None


scenario_parameters = {
    "baseline_aod_months": baseline_age * 12,
    "reform_aod_months": baseline_age * 12 + increase_months,
    "behavioural_delay_share": behavioural_delay_share,
    "absorption_rate": absorption_rate,
    "transition_method": transition_method,
    "effective_date": effective_date,
}


if (
    st.session_state.get("last_scenario_parameters")
    != scenario_parameters
):
    st.session_state["simulation_results"] = None


if launch:
    try:
        with st.spinner("Calcul de la trajectoire..."):
            st.session_state["simulation_results"] = simulate(
                baseline_aod_months=baseline_age * 12,
                reform_aod_months=baseline_age * 12 + increase_months,
                behavioural_delay_share=behavioural_delay_share,
                absorption_rate=absorption_rate,
                transition_method=transition_method,
                effective_date=effective_date,
            )

        st.session_state["last_scenario_parameters"] = (
            scenario_parameters.copy()
        )

    except (ValueError, KeyError, FileNotFoundError) as exc:
        st.error(f"Simulation impossible : {exc}")
        st.session_state["simulation_results"] = None


results = st.session_state["simulation_results"]

if results is None:
    st.info(
        "Configurez les parametres puis cliquez sur "
        "'Calculer le scenario'."
    )
    st.stop()


trajectory = annual_series(results)

year = st.select_slider(
    "Annee d'observation",
    options=trajectory["year"].astype(int).tolist(),
    value=2035,
)

observation = trajectory.loc[
    trajectory["year"].eq(year)
].iloc[0]

c1, c2, c3 = st.columns(3)

c1.metric(
    "Liquidations retardees - stock moyen",
    f"{observation['selected_delayed_stock']:,.0f}",
)

c2.metric(
    "Emploi supplementaire",
    f"{observation['delta_employment_reform']:,.0f}",
)

c3.metric(
    "Population active supplementaire",
    f"{observation['delta_labour_force_reform']:,.0f}",
)

st.subheader("Trajectoire des effets")

long = trajectory.melt(
    id_vars="year",
    value_vars=[
        "selected_delayed_stock",
        "delta_employment_reform",
        "delta_labour_force_reform",
        "delta_unemployment_reform",
    ],
    var_name="indicateur",
    value_name="personnes",
)

names = {
    "selected_delayed_stock": "Stock de liquidations retardees",
    "delta_employment_reform": "Emploi",
    "delta_labour_force_reform": "Population active",
    "delta_unemployment_reform": "Chomage",
}

long["indicateur"] = long["indicateur"].map(names)

fig = px.line(
    long,
    x="year",
    y="personnes",
    color="indicateur",
    labels={
        "year": "Annee",
        "personnes": "Personnes",
        "indicateur": "Indicateur",
    },
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Decomposition comportementale")

if "labour_behaviour_trajectory" in results:
    behaviour = results["labour_behaviour_trajectory"].copy()

    if "sex" in behaviour.columns:
        selected = behaviour.loc[
            behaviour["year"].eq(year)
        ].copy()

        fig_status = px.bar(
            selected,
            x="sex",
            y=[
                "delta_employment_reform",
                "delta_unemployment_reform",
            ],
            barmode="group",
            labels={
                "sex": "Sexe",
                "value": "Personnes",
                "variable": "Effet",
            },
        )

        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info(
            "Ventilation par sexe indisponible dans cette sortie."
        )

st.caption(
    "La decomposition comportementale constitue un diagnostic "
    "distinct du calcul agrege. Ses parametres peuvent differer."
)

st.subheader("Export des resultats")

st.download_button(
    label="Exporter la trajectoire CSV",
    data=trajectory.to_csv(
        index=False,
        sep=";",
    ).encode("utf-8-sig"),
    file_name="simulation_retraites_beta.csv",
    mime="text/csv",
)

with st.expander("Methodologie et limites"):
    st.markdown(
        "Le simulateur calcule un stock de liquidations retardees "
        "par cohorte, puis une variation de population active, "
        "d'emploi et de chomage. "
        "La methode historique est conservee par defaut. "
        "Le calendrier par cohortes et le double ajustement "
        "sont des variantes experimentales. "
        "Les finances des retraites, le PIB et les finances "
        "publiques ne sont pas encore integres."
    )
