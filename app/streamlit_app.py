import json
import streamlit as st
from cardistudio.presets import cardiac_mi_vs_sham
from cardistudio.population import PopulationBuilder
from cardistudio.validation import validate_challenge, validate_population
from cardistudio.analysis import summarize_population

st.set_page_config(page_title="CardiStudio", layout="wide")
st.title("Virelion CardiStudio")
st.caption("Reproducible cardiac challenge-population studio")

with st.sidebar:
    n = st.number_input("Population size", min_value=10, max_value=100000, value=1000, step=10)
    seed = st.number_input("Random seed", min_value=0, value=42, step=1)
    generate = st.button("Generate cohort", type="primary")

if generate or "population" not in st.session_state:
    spec = cardiac_mi_vs_sham(int(n), int(seed)); pop = PopulationBuilder(spec).build()
    st.session_state.spec, st.session_state.population = spec, pop

spec, pop = st.session_state.spec, st.session_state.population
report = validate_population(pop.rows, spec)
summary = summarize_population(pop.rows)

c1,c2,c3,c4 = st.columns(4)
c1.metric("Samples", summary["n"]); c2.metric("Groups", len(spec.population.groups)); c3.metric("Features", len(spec.features)); c4.metric("Valid", "Yes" if report.valid else "No")

st.subheader("Challenge")
st.json(spec.to_dict())
st.subheader("Population preview")
st.dataframe(pop.rows[:100], use_container_width=True)
st.subheader("Summary")
st.json(summary)
st.subheader("Provenance")
st.json(pop.provenance)
st.download_button("Download JSONL", pop.to_jsonl(), "population.jsonl", "application/jsonl")
