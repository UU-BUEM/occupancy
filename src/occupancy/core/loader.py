"""Shared package-data JSON loading, used by households/ and
services_buildings/.

Replaces the old fragile ``_defaults.py`` path traversal against a root
``configs/`` directory: every subpackage now loads its own bundled JSON via
``importlib.resources`` against its own ``data/`` folder, so there is a
single source of truth per subpackage instead of a duplicated root copy.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def load_json_resource(package: str, relative_path: str) -> dict[str, Any]:
    """Load and parse a JSON file bundled inside ``package``'s data files."""
    target = files(package).joinpath(relative_path)
    with target.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = json.load(handle)
    return data


def iter_json_resources(package: str, relative_dir: str) -> list[str]:
    """List the ``*.json`` filenames bundled under
    ``package``/``relative_dir``."""
    directory = files(package).joinpath(relative_dir)
    return sorted(
        entry.name
        for entry in directory.iterdir()
        if entry.name.endswith(".json") and not entry.name.startswith("_")
    )
