"""pysentimiento analyzers keyed by Analysis and language; tests replace `load` with fakes."""

from functools import cache
from typing import Protocol, cast

from contracts import Analysis


class Prediction(Protocol):
    """One pysentimiento result: a label, or every label for multi-label Analyses."""

    output: str | list[str]
    probas: dict[str, float]


class Predictor(Protocol):
    def predict(self, texts: list[str]) -> list[Prediction]: ...


@cache
def load(analysis: Analysis, lang: str) -> Predictor:
    """Load the model once per process; weights download on first use."""
    # pysentimiento ships no types; this is the only place it is touched.
    from pysentimiento import create_analyzer  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]

    return cast(Predictor, create_analyzer(task=analysis.value, lang=lang))
