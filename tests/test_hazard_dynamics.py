from rescumind.hazard_dynamics import (
    HazardCell,
    HazardParameters,
    HazardPropagationModel,
)


def test_fire_spreads_to_adjacent_flammable_cell() -> None:
    model = HazardPropagationModel(3, 1)
    model.set_cell(1, 0, HazardCell(fire=1.0))

    snapshot = model.step()

    assert snapshot.cell(0, 0).fire > 0.0
    assert snapshot.cell(2, 0).fire > 0.0


def test_blocked_cell_stops_direct_hazard_transfer() -> None:
    model = HazardPropagationModel(3, 1)
    model.set_cell(0, 0, HazardCell(fire=1.0, smoke=1.0, toxic_gas=1.0))
    model.set_cell(1, 0, HazardCell(blocked=True))

    snapshot = model.step()

    assert snapshot.cell(1, 0).blocked
    assert snapshot.cell(2, 0).fire == 0.0
    assert snapshot.cell(2, 0).smoke == 0.0
    assert snapshot.cell(2, 0).toxic_gas == 0.0


def test_fire_generates_smoke() -> None:
    model = HazardPropagationModel(1, 1)
    model.set_cell(0, 0, HazardCell(fire=0.8))

    assert model.step().cell(0, 0).smoke > 0.0


def test_hazards_decay_without_incoming_sources() -> None:
    parameters = HazardParameters(
        fire_spread=0.0,
        smoke_diffusion=0.0,
        gas_diffusion=0.0,
    )
    model = HazardPropagationModel(1, 1, parameters=parameters)
    model.set_cell(0, 0, HazardCell(fire=0.8, smoke=0.6, toxic_gas=0.4))

    snapshot = model.step()

    assert snapshot.cell(0, 0).fire < 0.8
    assert snapshot.cell(0, 0).smoke < 0.6 + parameters.smoke_generation * 0.8
    assert snapshot.cell(0, 0).toxic_gas < 0.4


def test_wind_biases_smoke_transport_downwind() -> None:
    parameters = HazardParameters(wind_x=1.0, wind_strength=1.0)
    model = HazardPropagationModel(3, 1, parameters=parameters)
    model.set_cell(1, 0, HazardCell(smoke=1.0))

    snapshot = model.step()

    assert snapshot.cell(2, 0).smoke > snapshot.cell(0, 0).smoke


def test_forecast_does_not_mutate_current_state() -> None:
    model = HazardPropagationModel(2, 1)
    model.set_cell(0, 0, HazardCell(fire=1.0))
    before = model.snapshot()

    forecast = model.forecast(3)

    assert len(forecast) == 3
    assert model.snapshot() == before
    assert forecast[-1].time == 3.0


def test_risk_query_uses_normalized_weights() -> None:
    model = HazardPropagationModel(1, 1)
    model.set_cell(0, 0, HazardCell(fire=1.0, smoke=0.5, toxic_gas=0.0))

    assert model.risk_at(0, 0, fire_weight=1.0, smoke_weight=1.0, gas_weight=0.0) == 0.75


def test_unsafe_cells_are_reported_deterministically() -> None:
    model = HazardPropagationModel(2, 2)
    model.set_cell(1, 0, HazardCell(fire=1.0))
    model.set_cell(0, 1, HazardCell(smoke=1.0))

    assert model.unsafe_cells(0.3) == ((1, 0), (0, 1))


def test_invalid_dimensions_and_rates_are_rejected() -> None:
    try:
        HazardPropagationModel(0, 1)
    except ValueError:
        pass
    else:
        raise AssertionError("zero-width grid should be rejected")

    try:
        HazardParameters(fire_spread=1.1)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range rates should be rejected")


def test_snapshot_access_checks_bounds() -> None:
    snapshot = HazardPropagationModel(1, 1).snapshot()

    try:
        snapshot.cell(1, 0)
    except IndexError:
        pass
    else:
        raise AssertionError("out-of-bounds access should fail")
