"""Run with CardiBridge installed; CI installs an audited immutable revision."""

import pytest

bridge = pytest.importorskip("cardibridge.contracts")
from cardistudio.io import cardi_bridge_envelope  # noqa: E402
from cardistudio.population import PopulationBuilder  # noqa: E402
from cardistudio.presets import cardiac_mi_vs_sham  # noqa: E402


def test_envelope_and_payload_pass_actual_cardibridge_contracts():
    spec = cardiac_mi_vs_sham(20)
    population = PopulationBuilder(spec).build()
    wire = cardi_bridge_envelope(spec, population)
    envelope = bridge.BridgeEnvelope.model_validate(wire)
    challenge = bridge.AgentChallenge.model_validate(envelope.payload)
    assert len(challenge.population) == 20
    assert (
        envelope.trace.provenance["generation"]["population_sha256"]
        == (population.provenance["population_sha256"])
    )
    assert wire == cardi_bridge_envelope(spec, population)
    assert (
        wire["idempotency_key"]
        != cardi_bridge_envelope(spec, population, "CardiTwin")["idempotency_key"]
    )
