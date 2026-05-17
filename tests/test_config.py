from occupancy.config import ScenarioConfig, load_scenario_config
from occupancy.electricity.electricity_consumption import (
    ElectricityConsumptionProfile,
)
from occupancy.internal_gains.occupancy_profile import OccupancyProfile


def test_default_scenario_config_round_trips() -> None:
    config = ScenarioConfig.default()

    assert config.year == 2026
    assert config.num_persons == 3
    assert config.home_probabilities.shape == (24, 2)
    assert config.weightage_table["tv"].weekday.shape == (24,)


def test_load_scenario_config_with_overrides(tmp_path) -> None:
    config_path = tmp_path / "scenario.json"
    config_path.write_text(
        """
        {
          "scenario": {
            "year": 2027,
            "num_persons": 4,
            "seed": 7,
            "include_electricity": true
          },
          "occupancy": {
            "home_probabilities": [
              [1.0, 1.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0],
              [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0],
              [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0],
              [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0],
              [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0],
              [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]
            ],
            "active_probabilities": [
              [0.0, 0.0], [1.0, 1.0], [0.0, 0.0], [0.0, 0.0],
              [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0],
              [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0],
              [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0],
              [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0],
              [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]
            ]
          },
          "electricity": {}
        }
        """,
        encoding="utf-8",
    )

    config = load_scenario_config(config_path)
    assert config.year == 2027
    assert config.num_persons == 4
    assert config.seed == 7
    assert config.include_electricity is True
    assert config.home_probabilities[0, 0] == 1.0
    assert config.active_probabilities[1, 1] == 1.0


def test_weightage_override_from_mapping() -> None:
    config = ScenarioConfig.from_mapping(
        {
            "scenario": {"year": 2028, "num_persons": 2},
            "electricity": {
                "weightage_table": {
                    "tv": {"weekday": [0.0] * 24, "weekend": [0.0] * 24},
                    "cooking": {"weekday": [0.0] * 24, "weekend": [0.0] * 24},
                    "laundry": {"weekday": [0.0] * 24, "weekend": [0.0] * 24},
                    "cleaning": {"weekday": [0.0] * 24, "weekend": [0.0] * 24},
                }
            },
        }
    )

    occupancy = OccupancyProfile(
        num_persons=config.num_persons,
        year=config.year,
        seed=config.seed,
        home_probabilities=config.home_probabilities,
        active_probabilities=config.active_probabilities,
    )
    electricity = ElectricityConsumptionProfile(
        occupancy_profile=occupancy,
        weightage_table=config.weightage_table,
    )

    assert electricity.get_weightage_table()["tv"].weekday[0] == 0.0
