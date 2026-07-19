from pathlib import Path

import pytest

from server import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def app():
    return create_app(testing=True)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def sample_bytes():
    return (PROJECT_ROOT / "examples" / "sample_raw_epoch.csv").read_bytes()
