"""共用路徑設定。測試一律離線，不對政府主機發出任何請求。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REFERENCE = Path(__file__).resolve().parents[1]
ROOT = REFERENCE.parent
FIXTURES = ROOT / "fixtures"

sys.path.insert(0, str(REFERENCE))


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        rows.append(json.loads(line))
    return rows


@pytest.fixture(scope="session")
def controls() -> dict:
    return json.loads((FIXTURES / "controls.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def title_rows() -> list[dict]:
    return _read_jsonl(FIXTURES / "nme_titles.sample.jsonl")


@pytest.fixture(scope="session")
def ingredient_rows() -> list[dict]:
    return _read_jsonl(FIXTURES / "ingredients.sample.jsonl")


@pytest.fixture(scope="session")
def restraint_codes() -> dict:
    return json.loads(
        (FIXTURES / "restraint_codes.2026-08-05.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def lic_type_codes() -> dict:
    return json.loads(
        (FIXTURES / "lic_type_codes.2026-08-05.json").read_text(encoding="utf-8"))
