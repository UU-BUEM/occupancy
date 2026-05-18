from __future__ import annotations

import pandas as pd


def plot_weekly_active_occupants(
    profile: pd.DataFrame,
    week_start: str = "2025-01-01",
) -> None:
    """Visualize active occupancy for four consecutive days."""
    import matplotlib.pyplot as plt

    week = pd.date_range(start=week_start, periods=4, freq="D")
    fig, axes = plt.subplots(4, 1, figsize=(6, 10), sharex=True)

    for i, day in enumerate(week):
        day_profile = profile.loc[day.strftime("%Y-%m-%d")]
        axes[i].step(
            day_profile.index.hour,
            day_profile["n_active"],
            where="post",
            linewidth=2,
        )
        axes[i].set_ylim(0, float(profile["n_active"].max()) + 0.5)
        axes[i].set_xlim(0, 24)
        axes[i].set_ylabel("Active\noccupants")
        axes[i].set_title(day.strftime("%A, %Y-%m-%d"))
        axes[i].grid(True, axis="y", linestyle="--", alpha=0.5)

    axes[-1].set_xlabel("Hour")
    plt.tight_layout()
    plt.show()
