"""One-time, reproducible extraction of real EN 12831-3 Annex Table B.2
hourly DHW-demand shapes into
``src/occupancy/households/data/dhw_demand_shape_categories.csv``.

Not part of the installed ``occupancy`` package -- a dev-only tool, run
once (or re-run if the source workbook is ever replaced), mirroring
``scripts/extract_dhw_tapping_categories.py``/``extract_crest_tpm.py``'s
established pattern exactly.

**Why this table exists**: `docs/dhw/design.md`'s open item #2 flags
`generate_dhw_draws()`'s ``washing_and_dressing`` timing as a
transition-weighted proxy over ``n_active``, not a real measured curve --
"the one item that would most benefit from a genuinely sourced
replacement." EN 12831-3's Annex Table B.2 is exactly that replacement,
surfaced by buem's own DHW/cooking work
(``D:\\test\\buem\\.claude\\dhw_cooking_heat_handoff.md``'s "Real EN
12831-3 Annex data found" section, 2026-08-18): buem extracted the same
workbook's ΔT/annual-volume constants for its own energy conversion but
deliberately left Table B.2 itself for occupancy, since it is a
*behavioral timing shape* (occupancy's domain), not an energy constant
(buem's domain) -- see this repo's `CLAUDE.md` ownership-boundary note.

Unlike ``tpm_crest.json`` (pure derived data, "generated, do not
hand-edit"), the output CSV is also meant to stay directly user-editable
afterward, matching ``dhw_tapping_categories.csv``'s convention -- see
``households/dhw.py``'s module docstring and ``docs/dhw/design.md``.

**Requires** ``openpyxl`` (not an ``occupancy`` runtime/dev dependency --
install ad hoc: ``pip install openpyxl`` or ``conda install -c conda-forge
openpyxl`` into the dev env before running this script).

**Source**: ``data/inputs/Demo_EN_12831-3_DHW_needs_2021-09-02.xlsx``
(EPB Center's free EN 12831-3:2017 "Domestic hot water needs"
demonstration spreadsheet, https://epb.center/document/demo-en-12831-3/),
gitignored and not committed to this repo -- same posture as the CREST
workbooks (redistribution license not verified). This is the *same* copy
buem's own ``scripts/extract_dhw_reference_values.py`` reads (that repo's
``src/buem/data/reference/``) -- both repos independently obtained it from
the user's own local reading-materials archive
(``OneDrive - Universiteit Utrecht/Old computer/Reading materials/Journal
papers/past_work/5r1c/``); no redistribution between the two repos, each
keeps its own gitignored copy.

**Cross-checked, not solely relied on**: the same Table B.2 percentages
(byte-identical, weekday/Saturday/Sunday sections all agree) also appear
in a second, independently-obtained EPB Center workbook,
``Demo_EN_16798-1_Use_Profile_Generator_2021-09-01.xlsm``'s
``DHW_Tap_profiles`` sheet (from the user's
``.../past_work/occupancy/`` folder) -- inspected directly this session,
not assumed. Not read by this script (the 12831-3 workbook alone is
sufficient and is the one already bundled here / in buem), but recorded
in ``.claude/residential/dhw_cooking_literature_review.md`` as
independent corroboration that this is the real, stable published table,
not a transcription artifact of one specific spreadsheet.

**What this reads**: ``Annex_B`` sheet, rows 68-91 (hour 0:00-1:00 through
23:00-0:00) of the "Tables from EN 12831-3, corrected, assembled and extra
profiles added" section ("These data are used in the calculation" --
row 64's own label) -- deliberately *not* the "ORIGINAL Table B.2" section
a few rows above it (rows 37-60), which the workbook itself flags with
"<-- SUM is not 100%" and is captioned "This table is not used in the
calculation, it is here for reference". Columns L-P: single family
dwelling, apartment dwelling, residential home for the elderly, student
residence, hospital -- percentages of each category's own daily DHW
volume total, by hour. Values are converted from percent (0-100, the
workbook's own unit) to fraction (0-1) on write; ``generate_dhw_draws()``
normalizes by each column's own sum before use as timing-choice
probabilities regardless, so this rescaling is for the CSV's readability
as a probability table, not a correctness requirement.

Usage::

    python scripts/extract_dhw_demand_shape_categories.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_XLSX_PATH = (
    _REPO_ROOT
    / "data"
    / "inputs"
    / "Demo_EN_12831-3_DHW_needs_2021-09-02.xlsx"
)
_OUTPUT_PATH = (
    _REPO_ROOT
    / "src"
    / "occupancy"
    / "households"
    / "data"
    / "dhw_demand_shape_categories.csv"
)

_SHEET = "Annex_B"
_HEADER_ROW = 66
_FIRST_HOUR_ROW = 68  # 0:00 <=t< 1:00
_TOTAL_ROW = 92
_NUM_HOURS = 24

# (column, this repo's category label), in the sheet's own left-to-right
# order.
_CATEGORY_COLUMNS = [
    (12, "single_family_dwelling"),  # L: "single family dwelling "
    (13, "apartment_dwelling"),  # M: "appartment dwelling"
    (14, "elderly_home"),  # N: "residential home for the elderly "
    (15, "student_residence"),  # O: "Student residence "
    (16, "hospital"),  # P: "Hospital "
]

# Regression anchors, confirmed by direct inspection this session. Catch a
# row/column-offset error in the read before it can silently corrupt the
# extracted data.
_ANCHOR_HEADER_LABEL = "single family dwelling "  # L66
_ANCHOR_FIRST_HOUR_SINGLE_FAMILY = 1.8  # L68, hour 0:00-1:00
_ANCHOR_TOTAL_APARTMENT = 100.0  # M92 -- the "corrected, assembled" table
# sums to a clean 100% (unlike the "ORIGINAL" reference table above it,
# which the workbook itself flags as not summing to 100%).

_CSV_HEADER_COMMENT = """\
# Real hourly DHW-demand shapes by building category -- EN 12831-3:2017
# Annex Table B.2 ("Hourly values of the relative hot-water demand based
# on volume for different building categories"), corrected/assembled
# variant (the workbook's own "used in the calculation" version, not its
# "ORIGINAL"/reference-only copy, which it flags as not summing to 100%).
#
# SOURCE: EPB Center's free EN 12831-3:2017 demonstration spreadsheet
# (Demo_EN_12831-3_DHW_needs_2021-09-02.xlsx, https://epb.center/document/
# demo-en-12831-3/), `Annex_B` sheet, rows 68-91. Read directly, not a
# secondary citation. Cross-checked (2026-08-18) against a second,
# independently-obtained workbook (Demo_EN_16798-1_Use_Profile_Generator_
# 2021-09-01.xlsm's `DHW_Tap_profiles` sheet) -- byte-identical
# percentages in both. See .claude/residential/dhw_cooking_literature_
# review.md for the full provenance trail, and docs/dhw/design.md for how
# this table is used.
#
# Surfaced by buem's own DHW/cooking work (D:\\test\\buem\\.claude\\
# dhw_cooking_heat_handoff.md's "Real EN 12831-3 Annex data found"
# section), which extracted this same workbook's delta-T/annual-volume
# constants for its own energy conversion but deliberately left this
# *timing-shape* table for occupancy -- an occupant-behavior curve is
# this repo's ownership boundary (CLAUDE.md), not buem's.
#
# WHAT THIS REPLACES: generate_dhw_draws()'s `washing_and_dressing`
# timing envelope is a transition-weighted n_active proxy (see
# households/dhw.py's `_washing_and_dressing_envelope`) -- a principled
# derivation from data already on hand, not a measured curve. This table
# is that measured curve. Pass `demand_shape_category=<a column name
# below>` to generate_dhw_draws() to use it instead of the per-fixture
# activity_link envelopes -- see that function's own docstring for why
# this is a *whole-household aggregate* alternative, not a drop-in
# replacement for one specific fixture's envelope: EN 12831-3's Table B.2
# is not decomposed by fixture (it covers all hot-water end uses combined,
# kitchen-sink draws included), so opting in overrides every owned
# fixture's timing uniformly for that household/building.
#
# Values are fractions (0-1) of each category's own daily DHW-volume
# total, one column per building category, converted from the workbook's
# own percent (0-100) units. generate_dhw_draws() re-normalizes by each
# column's own sum before use regardless, so this rescaling is for this
# file's own readability as a probability table, not load-bearing for
# correctness.
#
# Generated by scripts/extract_dhw_demand_shape_categories.py from the
# source workbook -- re-run that script to regenerate this file from
# scratch. Like dhw_tapping_categories.csv, this file is also meant to
# stay directly user-editable afterward (e.g. to add a region-specific
# variant column, or hand-tune a category for a specific scenario) --
# generate_dhw_draws() validates the table's shape (hour 0-23 present,
# non-negative, each column roughly summing to 1), not its exact values.
"""


def _cell(ws: Any, row: int, col: int) -> Any:
    return ws.cell(row=row, column=col).value


def main() -> None:
    try:
        import openpyxl
    except ImportError as exc:
        raise SystemExit(
            "openpyxl is required to run this script -- install ad hoc "
            "(`pip install openpyxl` or `conda install -c conda-forge "
            "openpyxl`), it is not an occupancy runtime/dev dependency."
        ) from exc

    if not _XLSX_PATH.exists():
        raise SystemExit(
            f"EN 12831-3 workbook not found at {_XLSX_PATH}. Obtain it "
            "directly from https://epb.center/document/demo-en-12831-3/ "
            "(free); see .claude/residential/dhw_cooking_literature_"
            "review.md for provenance notes."
        )

    print(f"Reading {_XLSX_PATH} ...")
    workbook = openpyxl.load_workbook(
        _XLSX_PATH, read_only=True, data_only=True
    )
    ws = workbook[_SHEET]

    # Regression anchor checks before trusting anything else in the file.
    header_label = _cell(ws, _HEADER_ROW, _CATEGORY_COLUMNS[0][0])
    if header_label != _ANCHOR_HEADER_LABEL:
        raise SystemExit(
            f"Regression anchor check failed: {_SHEET} row {_HEADER_ROW} "
            f"col {_CATEGORY_COLUMNS[0][0]} (category header) read "
            f"{header_label!r}, expected {_ANCHOR_HEADER_LABEL!r}. The "
            "row/column layout may no longer match this workbook -- "
            "aborting rather than emitting silently wrong data."
        )
    first_hour_value = _cell(ws, _FIRST_HOUR_ROW, _CATEGORY_COLUMNS[0][0])
    if first_hour_value != _ANCHOR_FIRST_HOUR_SINGLE_FAMILY:
        raise SystemExit(
            f"Regression anchor check failed: {_SHEET} row "
            f"{_FIRST_HOUR_ROW} col {_CATEGORY_COLUMNS[0][0]} (hour 0, "
            f"single family dwelling) read {first_hour_value!r}, expected "
            f"{_ANCHOR_FIRST_HOUR_SINGLE_FAMILY!r}."
        )
    total_apartment = _cell(ws, _TOTAL_ROW, _CATEGORY_COLUMNS[1][0])
    if abs(total_apartment - _ANCHOR_TOTAL_APARTMENT) > 1e-6:
        raise SystemExit(
            f"Regression anchor check failed: {_SHEET} row {_TOTAL_ROW} "
            f"col {_CATEGORY_COLUMNS[1][0]} (apartment dwelling TOTAL) "
            f"read {total_apartment!r}, expected "
            f"{_ANCHOR_TOTAL_APARTMENT!r}."
        )
    print("Regression anchor checks passed.")

    rows: list[dict[str, float]] = []
    for offset in range(_NUM_HOURS):
        row_num = _FIRST_HOUR_ROW + offset
        row_data: dict[str, float] = {"hour": offset}
        for col, label in _CATEGORY_COLUMNS:
            percent = _cell(ws, row_num, col)
            # Rounded to 6 decimal places -- the source workbook itself
            # only carries 1-2 significant decimal digits per cell (e.g.
            # "1.8", "0.3"); dividing by 100.0 in float arithmetic
            # otherwise introduces spurious noise (e.g. 0.018000000000002)
            # this table's own precision doesn't support.
            row_data[label] = round(float(percent) / 100.0, 6)
        rows.append(row_data)

    workbook.close()

    # Sum check -- each category column should sum close to 1.0 (the
    # source table's own rounding noise is float-precision-level, not a
    # real gap; see the TOTAL row anchor check above).
    for _, label in _CATEGORY_COLUMNS:
        total = sum(row[label] for row in rows)
        if abs(total - 1.0) > 0.01:
            raise SystemExit(
                f"Extracted column {label!r} sums to {total!r}, expected "
                "~1.0 -- aborting rather than emitting a silently "
                "miscalibrated shape."
            )
        print(f"  {label}: sums to {total:.6f}")

    fieldnames = ["hour"] + [label for _, label in _CATEGORY_COLUMNS]
    with _OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(_CSV_HEADER_COMMENT)
        handle.write(",".join(fieldnames) + "\n")
        for row in rows:
            handle.write(
                ",".join(
                    str(int(row[f])) if f == "hour" else repr(row[f])
                    for f in fieldnames
                )
                + "\n"
            )
    print(f"Wrote {_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
