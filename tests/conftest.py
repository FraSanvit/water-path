from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def demo_network_dir() -> Path:
    return REPO_ROOT / "examples" / "demo" / "network"


@pytest.fixture
def demo_conditions_path() -> Path:
    return REPO_ROOT / "examples" / "demo" / "environment" / "conditions.nc"
