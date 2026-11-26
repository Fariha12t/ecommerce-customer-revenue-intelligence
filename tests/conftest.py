import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from olist_fixture import make_mini_olist  # noqa: E402


@pytest.fixture(scope="session")
def raw_dir(tmp_path_factory):
    return make_mini_olist(tmp_path_factory.mktemp("raw"))
