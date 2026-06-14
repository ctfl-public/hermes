from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def pytest_configure(config):
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


@pytest.fixture(scope="session")
def fixture_dir(tmp_path_factory):
    pytest.importorskip("numpy")
    pytest.importorskip("tifffile")
    from scripts.make_test_fixtures import generate_fixtures

    root = tmp_path_factory.mktemp("hermes-fixtures")
    generate_fixtures(root)
    return root


@pytest.fixture
def repo_root():
    return REPO_ROOT


@pytest.fixture
def tmp_output(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    return out
