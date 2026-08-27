import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "validation" / "samples"

import pytest

from app.main import create_app


@pytest.fixture()
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def sample1():
    return (SAMPLES_DIR / "sample1_simple.py").read_text()


@pytest.fixture()
def sample2():
    return (SAMPLES_DIR / "sample2_vulnerable.py").read_text()


@pytest.fixture()
def sample3():
    return (SAMPLES_DIR / "sample3_sample.java").read_text()
