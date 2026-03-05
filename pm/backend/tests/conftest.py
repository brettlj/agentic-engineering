import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure module-level FastAPI app import can initialize in tests.
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")


@pytest.fixture(autouse=True)
def set_required_openrouter_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tests do not exercise live OpenRouter calls by default.
    monkeypatch.setenv("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY", "test-key"))
