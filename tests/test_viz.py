import matplotlib
import pytest

matplotlib.use("Agg")

from waterpath.io import load_network
from waterpath.viz import plot_network


def test_plot_network_smoke(demo_network_dir):
    # basemap=False keeps the test offline and fast
    fig = plot_network(load_network(demo_network_dir), basemap=False)
    ax = fig.axes[0]
    # one Line2D per route, plus a PathCollection of harbours
    assert len(ax.lines) == 2
    assert len(ax.collections) == 1


def test_plot_network_missing_contextily_warns(demo_network_dir, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def no_contextily(name, *args, **kwargs):
        if name == "contextily":
            raise ImportError("simulated")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_contextily)
    with pytest.warns(UserWarning, match="contextily is not installed"):
        plot_network(load_network(demo_network_dir), basemap=True)
