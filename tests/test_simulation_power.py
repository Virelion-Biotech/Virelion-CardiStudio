import pytest
from cardistudio.power import simulation_power


def test_simulated_rejection_rate_is_reproducible_and_interval_covers_boundary():
    def simulate(rng):
        return rng.random()

    def test(sample):
        return sample < 0.5

    a = simulation_power(simulate, test, repetitions=100, seed=4)
    assert a == simulation_power(simulate, test, repetitions=100, seed=4)
    assert a["monte_carlo_interval"][0] < a["rejection_rate"] < a["monte_carlo_interval"][1]
    boundary = simulation_power(simulate, lambda _: False, repetitions=20)
    assert boundary["monte_carlo_interval"][1] > 0
    with pytest.raises(ValueError):
        simulation_power(simulate, lambda _: 0.4, repetitions=2)
