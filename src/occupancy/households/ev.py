"""Household EV defaults: loads ``data/ev.json`` into an
:class:`~occupancy.core.ev.EVConfig`.

The simulation engine itself is :mod:`occupancy.core.ev`; this module only
owns the household defaults, kept outside ``equipment.json`` because an EV
is a stateful battery, not an hourly-triggered appliance, and its charging
is not an internal heat gain.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from occupancy.core.ev import EVConfig, resolve_ev_config
from occupancy.core.loader import load_json_resource

_PACKAGE = "occupancy.households"
_EV_PATH = "data/ev.json"

_DEFAULT_EV_CONFIG = EVConfig.from_mapping(
    load_json_resource(_PACKAGE, _EV_PATH)
)


def default_ev_config() -> EVConfig:
    """The bundled household EV defaults (``households/data/ev.json``)."""
    return _DEFAULT_EV_CONFIG


def load_ev_config(
    overrides: EVConfig | Mapping[str, Any] | str | Path | None = None,
) -> EVConfig:
    """Bundled defaults with ``overrides`` applied.

    ``overrides`` may be a mapping (deep-merged; unknown keys raise), the
    path of a JSON file holding such a mapping (e.g. survey-derived
    distributions), a ready :class:`EVConfig`, or ``None`` for the plain
    defaults. Examples::

        load_ev_config({"ownership_probability": 0.35})
        load_ev_config({"charging_modes": {"slow": {"power_kw": 11.0}}})
        load_ev_config("loenen_survey_ev.json")
    """
    return resolve_ev_config(overrides, _DEFAULT_EV_CONFIG)


__all__ = ["default_ev_config", "load_ev_config"]
