import json

import plotly.express as px
import streamlit as st

from cardistudio.io import load_challenge
from cardistudio.population import PopulationBuilder
from cardistudio.validation import validate_population
from cardistudio.analysis import summarize_population, balance_report
from cardistudio.presets import cardiac_mi_vs_sham

st.set_page_config(page_title="CardiStudio", layout="wide")
st.title("Virelion CardiStudio")
st.caption("Reproducible cardiac challenge-population studio")

with st.sidebar:
    mode = st.radio("Specification", ["MI-vs-sham benchmark", "Upload JSON"])
    n = st.number_input("Population size", min_value=10, max_value=100000, value=1000, step=10)
    seed = st.number_input("Random seed", min_value=0, value=42, step=1)

    uploaded = st.file_uploader("Challenge JSON", type=["json"]) if mode == "Upload JSON" else None
    generate = st.button("Generate cohort", type="primary")

if generate or "population" not in st.session_state:
    try:
        if mode == "Upload JSON":
            if uploaded is None:
                st.error("Upload a challenge JSON before generating.")
                st.stop()
            payload = json.load(uploaded)
            from pathlib import Path
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "challenge.json"
                temp_path.write_text(json.dumps(payload), encoding="utf-8")
                spec = load_challenge(temp_path)
                spec.population.seed = int(seed)
        else:
            spec = cardiac_mi_vs_sham(int(n), int(seed))
        population = PopulationBuilder(spec).build()
        st.session_state.spec = spec
        st.session_state.population = population
    except Exception as exc:
        st.error(f"Generation failed: {exc}")
        st.stop()

spec = st.session_state.spec
population = st.session_state.population
report = validate_population(population.rows, spec)
summary = summarize_population(population.rows)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Samples", summary["n"])
c2.metric("Groups", len(spec.population.groups))
c3.metric("Features", len(spec.features))
c4.metric("Valid", "Yes" if report.valid else "No")

tab1, tab2, tab3, tab4 = st.tabs(["Challenge", "Population", "Signal", "Provenance"])

with tab1:
    st.json(spec.to_dict())

with tab2:
    st.dataframe(population.rows[:250], use_container_width=True)
    csv_bytes = __import__("io").StringIO()
    import csv
    writer = csv.DictWriter(csv_bytes, fieldnames=list(population.rows[0]))
    writer.writeheader()
    writer.writerows(population.rows)
    st.download_button("Download CSV", csv_bytes.getvalue(), "population.csv", "text/csv")
    st.download_button(
        "Download JSONL",
        population.to_jsonl(),
        "population.jsonl",
        "application/jsonl",
    )

with tab3:
    continuous = [
        f.name for f in spec.features
        if f.name in {"ejection_fraction", "fibrosis_fraction", "heart_rate"}
    ]
    if continuous and spec.population.group_field in population.rows[0]:
        default_feature = (\n            "ejection_fraction"\n            if "ejection_fraction" in continuous\n            else continuous[0]\n        )
        feature = st.selectbox("Feature", continuous, index=continuous.index(default_feature))
        figure = px.box(
            population.rows,
            x=spec.population.group_field,
            y=feature,
            points=False,
            title=f"{feature} by {spec.population.group_field}",
        )
        st.plotly_chart(figure, use_container_width=True)
    st.json(
        balance_report(
            population.rows,
            spec.population.group_field,
            [f.name for f in spec.features if f.distribution in {"normal", "uniform", "lognormal"}],
        )
    )

with tab4:
    st.json(population.provenance)
    st.download_button(
        "Download challenge JSON",
        json.dumps(spec.to_dict(), indent=2, sort_keys=True),
        "challenge.json",
        "application/json",
    )
