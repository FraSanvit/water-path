"""Quick-look plots for input data — for eyeballing what was loaded, not publication.

Requires ``matplotlib`` (install the ``viz`` extra: ``pip install water-path[viz]``).
The optional slippy-map backdrop additionally needs ``contextily`` and network access
at plot time; if either is missing the plot is drawn without it.
"""

from __future__ import annotations

import math
import warnings
from typing import TYPE_CHECKING

from waterpath.schemas.network import Network

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

__all__ = ["plot_network"]

_PAD = 0.15  # fraction of span added around the data as margin


def plot_network(
    network: Network,
    *,
    ax: "Axes | None" = None,
    annotate: bool = True,
    basemap: bool = True,
    basemap_source: object | None = None,
) -> "Figure":
    """Plot harbours and route paths on a lon/lat axis.

    Parameters
    ----------
    basemap:
        Draw an OpenStreetMap-style backdrop under the network (via ``contextily``).
        Silently skipped if ``contextily`` is unavailable or tiles cannot be fetched.
    basemap_source:
        A ``contextily`` tile provider; defaults to ``Esri.WorldGrayCanvas``.
    """
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(7, 7))
    fig = ax.figure

    lons: list[float] = []
    lats: list[float] = []

    for route in network.routes:
        rlons = [p.lon for p in route.path]
        rlats = [p.lat for p in route.path]
        lons += rlons
        lats += rlats
        (line,) = ax.plot(rlons, rlats, "-", lw=1.8, alpha=0.9, zorder=3)
        if annotate:
            mid = len(route.path) // 2
            ax.annotate(
                route.route_id,
                (route.path[mid].lon, route.path[mid].lat),
                fontsize=8,
                color=line.get_color(),
                xytext=(4, 4),
                textcoords="offset points",
                zorder=4,
            )

    hlons = [h.lon for h in network.harbours]
    hlats = [h.lat for h in network.harbours]
    lons += hlons
    lats += hlats
    ax.scatter(hlons, hlats, s=45, color="#1a1a1a", zorder=5)
    if annotate:
        for h in network.harbours:
            ax.annotate(
                h.name,
                (h.lon, h.lat),
                fontsize=8,
                fontweight="bold",
                xytext=(5, -10),
                textcoords="offset points",
                zorder=6,
            )

    # Fix the view before adding a basemap so the right tile zoom is chosen.
    span_x = max(max(lons) - min(lons), 1e-4)
    span_y = max(max(lats) - min(lats), 1e-4)
    ax.set_xlim(min(lons) - _PAD * span_x, max(lons) + _PAD * span_x)
    ax.set_ylim(min(lats) - _PAD * span_y, max(lats) + _PAD * span_y)

    mean_lat = sum(lats) / len(lats)
    ax.set_aspect(1.0 / max(math.cos(math.radians(mean_lat)), 1e-6))

    if basemap:
        _add_basemap(ax, basemap_source)

    ax.set_xlabel("longitude (°E)")
    ax.set_ylabel("latitude (°N)")
    fig.tight_layout()
    return fig


def _add_basemap(ax: "Axes", source: object | None) -> None:
    try:
        import contextily as cx
    except ImportError:
        warnings.warn("basemap=True but contextily is not installed; skipping backdrop", stacklevel=3)
        return

    if source is None:
        # key-free, muted backdrop that keeps the network readable
        source = cx.providers.Esri.WorldGrayCanvas
    try:
        cx.add_basemap(ax, crs="EPSG:4326", source=source, attribution_size=6)
    except Exception as exc:  # network/tile failures shouldn't break the plot
        warnings.warn(f"could not fetch basemap tiles ({exc}); skipping backdrop", stacklevel=3)
