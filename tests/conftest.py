import os
import sys
from pathlib import Path

# Tests never call a model: the explainer must work (and fall back) with no backend.
os.environ["SAHAYAK_LLM"] = "none"
os.environ.setdefault("SAHAYAK_HOME", str(Path(__file__).resolve().parent / ".sahayak-test"))
# Test data stays in the test home, but the (large) speech models are shared with the real node
# when they are installed; voice tests that need them skip otherwise.
_models = Path.home() / ".sahayak" / "models"
if _models.is_dir():
    os.environ.setdefault("SAHAYAK_MODELS", str(_models))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
