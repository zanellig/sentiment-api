"""The Analyzer: labels every Segment of a Job in one batch per Analysis (ADR-0006)."""

from contracts import Analysis, AnalysisResult, Segment, SegmentAnalyses, SequenceResult

from analyzer import models


def analyze(
    segments: list[Segment], analyses: list[Analysis], lang: str
) -> tuple[list[SegmentAnalyses], list[str]]:
    """Return the results per Segment and the warnings for Analyses that were skipped."""
    results: dict[int, list[AnalysisResult]] = {
        segment.index: [] for segment in segments
    }
    warnings: list[str] = []
    texts = [segment.text for segment in segments]
    for analysis in analyses:
        # shortcut: only sentiment exists so far; add each Analysis with the ticket that needs it.
        if analysis is not Analysis.SENTIMENT:
            warnings.append(
                f"Analysis '{analysis}' is not available for '{lang}'; skipped"
            )
            continue
        predictions = models.load(analysis, lang).predict(texts)
        for segment, prediction in zip(segments, predictions, strict=True):
            if not isinstance(prediction.output, str):
                raise TypeError(
                    f"{analysis} returned several labels: {prediction.output}"
                )
            results[segment.index].append(
                SequenceResult(
                    analysis=analysis,
                    label=prediction.output,
                    probabilities=prediction.probas,
                )
            )
    return [SegmentAnalyses(index=i, results=r) for i, r in results.items()], warnings
