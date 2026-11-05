"""pysentimiento analyzers keyed by Analysis and language; tests replace `load` with fakes.

Each deployment serves one language (`ANALYZER_LANG`, ADR-0007) and runs its models on
`ANALYZER_DEVICE`. pysentimiento ships no types; this is the only place it is touched.
"""

import os
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import cache
from typing import Any, Protocol, cast

import torch
from contracts import Analysis
from transformers import BatchEncoding, PreTrainedModel, PreTrainedTokenizerBase

LANGUAGE = os.environ.get("ANALYZER_LANG", "es")
DEVICE = torch.device(os.environ.get("ANALYZER_DEVICE", "cpu"))
BATCH_SIZE = 32  # pysentimiento's own default


class Prediction(Protocol):
    """One pysentimiento result: a label, or every label for multi-label Analyses."""

    output: str | list[str]
    probas: dict[str, float]


class TokenPrediction(Protocol):
    """A label per token; `entities` holds pysentimiento's `{type, text, start, end}` for NER."""

    tokens: list[str]
    labels: list[str]
    entities: list[dict[str, Any]] | None


class Predictor(Protocol):
    def predict(self, texts: list[str]) -> list[Prediction]: ...


class TokenPredictor(Protocol):
    def predict(self, texts: list[str]) -> list[TokenPrediction]: ...


class _SequenceAnalyzer(Protocol):
    """The parts of pysentimiento's sequence analyzer the forward pass needs."""

    model: PreTrainedModel
    tokenizer: PreTrainedTokenizerBase
    preprocessing_args: dict[str, Any]


class _SpacyToken(Protocol):
    text: str


class _TokenAnalyzer(Protocol):
    model: torch.nn.Module
    tokenizer: PreTrainedTokenizerBase
    spacy_tokenizer: Callable[[str], Iterable[_SpacyToken]]
    preprocessing_args: dict[str, Any]

    def predict(self, inputs: list[str]) -> list[TokenPrediction] | TokenPrediction: ...


@dataclass
class _Output:
    output: str | list[str]
    probas: dict[str, float]


@dataclass
class _TokenOutput:
    tokens: list[str]
    labels: list[str]
    entities: list[dict[str, Any]] | None


class Sequence:
    """Runs a sequence model's forward pass on `device`.

    pysentimiento's own `predict` goes through a Trainer, which picks the GPU by itself.
    """

    def __init__(self, analyzer: _SequenceAnalyzer, device: torch.device):
        self._model = analyzer.model
        torch.nn.Module.to(self._model, device).eval()  # PreTrainedModel.to's stub rejects a device
        self._tokenizer = analyzer.tokenizer
        self._preprocessing_args = analyzer.preprocessing_args
        self._device = device

    def predict(self, texts: list[str]) -> list[Prediction]:
        config = self._model.config
        multi_label = config.problem_type == "multi_label_classification"
        labels = cast(dict[int, str], config.id2label)
        outputs: list[Prediction] = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = [
                _preprocess(t, **self._preprocessing_args)
                for t in texts[start : start + BATCH_SIZE]
            ]
            inputs: BatchEncoding = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=cast(int, self._tokenizer.model_max_length),  # pyright: ignore[reportUnknownMemberType]
                return_tensors="pt",
            ).to(self._device)
            with torch.inference_mode():
                logits = cast(torch.Tensor, self._model(**inputs).logits)
            probabilities = logits.sigmoid() if multi_label else logits.softmax(-1)
            rows = cast(list[list[float]], probabilities.tolist())  # pyright: ignore[reportUnknownMemberType]
            for row in rows:
                probas = {labels[i]: p for i, p in enumerate(row)}
                output = (
                    [k for k, p in probas.items() if p > 0.5]
                    if multi_label
                    else max(probas, key=probas.__getitem__)
                )
                outputs.append(_Output(output=output, probas=probas))
        return outputs


class Tokens:
    """pysentimiento's token analyzer, with its model moved to `device`.

    pysentimiento truncates at the model's subword limit, which leaves later words without a
    label (NER) or crashes (POS), so a long text runs as several chunks that each fit.
    """

    def __init__(self, analyzer: _TokenAnalyzer, device: torch.device):
        analyzer.model.to(device)
        self._analyzer = analyzer
        self._max_length = cast(int, analyzer.tokenizer.model_max_length)  # pyright: ignore[reportUnknownMemberType]

    def predict(self, texts: list[str]) -> list[TokenPrediction]:
        spans = [self._split(text, [m.span() for m in re.finditer(r"\S+", text)]) for text in texts]
        chunks = [text[start:end] for text, s in zip(texts, spans) for start, end in s]
        predictions: list[TokenPrediction] = []
        with torch.inference_mode():
            for start in range(0, len(chunks), BATCH_SIZE):
                outputs = self._analyzer.predict(chunks[start : start + BATCH_SIZE])
                predictions += outputs if isinstance(outputs, list) else [outputs]  # one text gives no list
        joined: list[TokenPrediction] = []
        remaining = iter(predictions)
        for text, s in zip(texts, spans):
            parts = [(start, end, next(remaining)) for start, end in s]
            entities = None
            if parts[0][2].entities is not None:
                entities = [
                    self._in_text(entity, text, start, end)
                    for start, end, p in parts
                    for entity in p.entities or []
                ]
            joined.append(
                _TokenOutput(
                    tokens=[t for _, _, p in parts for t in p.tokens],
                    labels=[label for _, _, p in parts for label in p.labels],
                    entities=entities,
                )
            )
        return joined

    def _split(self, text: str, words: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Spans of `text` that each fit the model, halving the words until they do.

        shortcut: an entity across a split comes back as two, and a single word past the limit
        is still truncated; split at sentence ends if long Segments turn out common.
        """
        if not words:
            return [(0, len(text))]
        start, end = words[0][0], words[-1][1]
        if len(words) == 1 or self._fits(text[start:end]):
            return [(start, end)]
        half = len(words) // 2
        return self._split(text, words[:half]) + self._split(text, words[half:])

    def _fits(self, chunk: str) -> bool:
        """Whether pysentimiento would see every subword token of `chunk`, tokenized as it does."""
        analyzer = self._analyzer
        words = [t.text for t in analyzer.spacy_tokenizer(_preprocess(chunk, **analyzer.preprocessing_args))]
        encoding = analyzer.tokenizer(words, is_split_into_words=True)
        return len(cast(list[int], encoding["input_ids"])) <= self._max_length

    def _in_text(self, entity: dict[str, Any], text: str, start: int, end: int) -> dict[str, Any]:
        """pysentimiento's offsets are into the preprocessed chunk; they hold in `text` only when
        preprocessing changed nothing."""
        chunk = text[start:end]
        if _preprocess(chunk, **self._analyzer.preprocessing_args) != chunk:
            return {**entity, "start": None, "end": None}
        return {**entity, "start": start + entity["start"], "end": start + entity["end"]}


def supports(analysis: Analysis, lang: str) -> bool:
    """Whether pysentimiento has a model for this Analysis in this language."""
    from pysentimiento.analyzer import models  # pyright: ignore[reportMissingTypeStubs]

    return analysis.value in cast(dict[str, dict[str, Any]], models).get(lang, {})


def _create(analysis: Analysis, lang: str) -> object:
    """Weights download on first use. On a GPU host the analyzer's Trainer briefly places the
    model on the GPU even when `DEVICE` is the CPU; hide the GPU from CPU deployments."""
    from pysentimiento import create_analyzer  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]

    return create_analyzer(task=analysis.value, lang=lang)  # pyright: ignore[reportUnknownVariableType]


@cache
def load(analysis: Analysis, lang: str) -> Predictor:
    """A sequence Analysis' model, loaded once per process."""
    return Sequence(cast(_SequenceAnalyzer, _create(analysis, lang)), DEVICE)


@cache
def load_tokens(analysis: Analysis, lang: str) -> TokenPredictor:
    """The NER or POS model, loaded once per process."""
    return Tokens(cast(_TokenAnalyzer, _create(analysis, lang)), DEVICE)


def _preprocess(text: str, **args: Any) -> str:
    from pysentimiento.preprocessing import preprocess_tweet  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]

    return cast(Callable[..., str], preprocess_tweet)(text, **args)
