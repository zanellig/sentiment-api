"""The Analyzer: labels every Segment of a Job in one batch per Analysis (ADR-0006)."""

from contracts import (
    Analysis,
    AnalysisResult,
    Entity,
    MultiLabelResult,
    NerResult,
    PosResult,
    Segment,
    SegmentAnalyses,
    SequenceResult,
)

from analyzer import models


def analyze(
    segments: list[Segment], analyses: list[Analysis], lang: str
) -> tuple[list[SegmentAnalyses], list[str]]:
    """Return the results per Segment and the warnings for Analyses that were skipped."""
    if lang != models.LANGUAGE:
        raise ValueError(f"This deployment analyses '{models.LANGUAGE}', not '{lang}'")
    results: dict[int, list[AnalysisResult]] = {
        segment.index: [] for segment in segments
    }
    warnings: list[str] = []
    texts = [segment.text for segment in segments]
    for analysis in analyses:
        # shortcut: pysentimiento's targeted_sentiment model labels a (text, target) pair and
        # Jobs carry no target; run it once the contracts say where targets come from.
        if analysis is Analysis.TARGETED_SENTIMENT:
            warnings.append(
                f"Analysis '{analysis}' needs a target, which Jobs do not carry; skipped"
            )
            continue
        if not models.supports(analysis, lang):
            warnings.append(
                f"Analysis '{analysis}' is not available for '{lang}'; skipped"
            )
            continue
        for segment, result in zip(
            segments, _label(analysis, texts, lang), strict=True
        ):
            results[segment.index].append(result)
    return [SegmentAnalyses(index=i, results=r) for i, r in results.items()], warnings


def _label(analysis: Analysis, texts: list[str], lang: str) -> list[AnalysisResult]:
    """One result per text, in the contract shape of the Analysis."""
    match analysis:
        case Analysis.NER:
            return [
                NerResult(
                    analysis=analysis,
                    tokens=p.tokens,
                    labels=p.labels,
                    entities=[Entity.model_validate(e) for e in p.entities or []],
                )
                for p in models.load_tokens(analysis, lang).predict(texts)
            ]
        case Analysis.POS:
            return [
                PosResult(analysis=analysis, tokens=p.tokens, labels=p.labels)
                for p in models.load_tokens(analysis, lang).predict(texts)
            ]
        case Analysis.HATE_SPEECH:
            results: list[AnalysisResult] = []
            for p in models.load(analysis, lang).predict(texts):
                if not isinstance(p.output, list):
                    raise TypeError(f"{analysis} returned a single label: {p.output}")
                results.append(
                    MultiLabelResult(
                        analysis=analysis, labels=p.output, probabilities=p.probas
                    )
                )
            return results
        case _:
            results = []
            for p in models.load(analysis, lang).predict(texts):
                if not isinstance(p.output, str):
                    raise TypeError(f"{analysis} returned several labels: {p.output}")
                results.append(
                    SequenceResult(
                        analysis=analysis, label=p.output, probabilities=p.probas
                    )
                )
            return results
