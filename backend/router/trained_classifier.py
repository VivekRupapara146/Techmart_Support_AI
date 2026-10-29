"""
Router v2b: loads the pre-trained TF-IDF + Logistic Regression classifier
(ml/train_router_v2b.py) and exposes the same RouteDecision contract as
v1 and v2.

Unlike v1 (multi-agent by design) and v2 (can return multiple agents),
this classifier is single-label — Banking77 examples are singly-labeled,
so the model was trained for one best-fit category, not multi-select.
This is a real, disclosed limitation for the capstone comparison, not
hidden: v2b cannot express "this spans billing AND technical" the way
v1/v2 can.
"""
import joblib

from router.types import RouteDecision, VALID_AGENTS, DEFAULT_AGENT
from core.logging import get_logger

logger = get_logger(__name__)

ARTIFACT_PATH = "artifacts/router_v2b/model.joblib"

_model = None


def _load_model():
    global _model
    if _model is None:
        try:
            _model = joblib.load(ARTIFACT_PATH)
        except FileNotFoundError:
            raise RuntimeError(
                f"Router v2b model not found at {ARTIFACT_PATH}. "
                f"Run `python -m ml.train_router_v2b` first."
            )
    return _model


def route(query: str) -> RouteDecision:
    model = _load_model()
    prediction = str(model.predict([query])[0])

    if prediction not in VALID_AGENTS:
        logger.warning(f"v2b predicted an unrecognized label {prediction!r}, defaulting to faq")
        prediction = DEFAULT_AGENT

    return RouteDecision(agents=[prediction], confidence="trained_classifier")
