import json

import plotly.express as px
import streamlit as st

from cardistudio.analysis import balance_report, summarize_population
from cardistudio.io import cardi_bridge_envelope, loads_challenge, population_csv
from cardistudio.population import PopulationBuilder
from cardistudio.presets import cardiac_mi_vs_sham
from cardistudio.validation import validate_population

st.set_page_config(page_title="CardiStudio", layout="wide")
st.title("Virelion CardiStudio")
st.caption("Reproducible cardiac challenge-population studio")
st.info(
    "Synthetic benchmark data. Observations within a subject are correlated; "
    "they are not additional biological replicates."
)

with st.sidebar:
    mode = st.radio("Specification", ["MI-vs-sham benchmark", "Upload JSON"])
    n = st.number_input("Population size", min_value=10, max_value=100000, value=1000, step=10)
    seed = st.number_input("Random seed", min_value=0, value=42, step=1)
    uploaded = st.file_uploader("Challenge JSON", type=["json"]) if mode == "Upload JSON" else None
    st.caption("For uploaded challenges, population size comes from the JSON.")
    generate = st.button("Generate cohort", type="primary")

selection = (mode, int(n), int(seed), uploaded.getvalue() if uploaded is not None else None)
if generate or "population" not in st.session_state:
    try:
        if mode == "Upload JSON":
            if uploaded is None:
                st.error("Upload a challenge JSON before generating.")
                st.stop()
            spec = loads_challenge(uploaded.getvalue())
            if spec.population.n > 100000:
                raise ValueError("The interactive app supports at most 100,000 observations.")
            spec.population.seed = int(seed)
        else:
            spec = cardiac_mi_vs_sham(int(n), int(seed))
        population = PopulationBuilder(spec).build()
        st.session_state.spec = spec
        st.session_state.population = population
        st.session_state.generated_selection = selection
    except (ValueError, TypeError, OSError) as exc:
        st.error(f"Generation failed: {exc}")
        st.stop()

if selection != st.session_state.generated_selection:
    st.warning(
        "Settings changed. Generate a cohort to apply them; results below show the saved cohort."
    )
spec = st.session_state.spec
population = st.session_state.population
report = validate_population(population.rows, spec)
summary = summarize_population(population.rows)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Observations", summary["n"])
c2.metric("Subjects", len({row[spec.population.subject_field] for row in population.rows}))
c3.metric("Features", len(spec.features))
c4.metric("Valid", "Yes" if report.valid else "No")
for warning in report.warnings:
    st.warning(warning)

tab1, tab2, tab3, tab4 = st.tabs(["Challenge", "Population", "Signal", "Provenance"])
with tab1:
    st.json(spec.to_dict())
with tab2:
    st.dataframe(population.rows[:250], width="stretch")
    st.download_button(
        "Download CSV", population_csv(population.rows), "population.csv", "text/csv"
    )
    st.download_button(
        "Download JSONL", population.to_jsonl(), "population.jsonl", "application/jsonl"
    )
    st.download_button(
        "Download provenance (required with JSONL)",
        json.dumps(population.provenance, indent=2, allow_nan=False),
        "population.jsonl.provenance.json",
        "application/json",
    )
    st.download_button(
        "Download CardiBridge envelope",
        json.dumps(cardi_bridge_envelope(spec, population), allow_nan=False),
        "bridge_envelope.json",
        "application/json",
    )
with tab3:
    numeric = [f.name for f in spec.features if f.dtype in {"continuous", "integer", "binary"}]
    if numeric:
        default = "ejection_fraction" if "ejection_fraction" in numeric else numeric[0]
        feature = st.selectbox("Feature", numeric, index=numeric.index(default))
        figure = px.box(
            population.rows,
            x=spec.population.group_field,
            y=feature,
            points=False,
            title=f"{feature} by {spec.population.group_field}",
        )
        st.plotly_chart(figure, width="stretch")
    st.json(balance_report(population.rows, spec.population.group_field, numeric))
with tab4:
    st.json(population.provenance)
    st.download_button(
        "Download challenge JSON",
        json.dumps(spec.to_dict(), indent=2, allow_nan=False),
        "challenge.json",
        "application/json",
    )
