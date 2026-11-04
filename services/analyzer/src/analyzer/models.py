"""pysentimiento analyzers keyed by Analysis and language; tests replace `load` with fakes."""

from functools import cache

from contracts import Analysis


@cache
def load(analysis: Analysis, lang: str):
    """Load the model once per process; weights download on first use."""
    from pysentimiento import create_analyzer  # pulls in torch, so only when a model is needed

    return create_analyzer(task=analysis.value, lang=lang)
