"""Compatibility wrapper for directional porosity utilities.

New code should import from ``hermes.directional_porosity``.
"""

from hermes.directional_porosity import (
    directional_porosity,
    get1DPorosity,
    loadData,
    load_data,
    load_porosity_data,
    load_porosity_distributions,
    plot_porosity_scatter,
    porosity3DMap,
    porosity_3d_map,
    save_porosity_data,
)

__all__ = [
    "directional_porosity",
    "get1DPorosity",
    "loadData",
    "load_data",
    "load_porosity_data",
    "load_porosity_distributions",
    "plot_porosity_scatter",
    "porosity3DMap",
    "porosity_3d_map",
    "save_porosity_data",
]
