import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.fixtures import phantom  # noqa: E402


@pytest.fixture(scope="session")
def rgb_and_mask():
    return phantom(seed=7)


@pytest.fixture(scope="session")
def system(rgb_and_mask):
    from src.pipeline import System
    return System(b"unit-test-key")
