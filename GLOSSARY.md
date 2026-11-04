# Sentiment API

Analyzes the transcripts produced by the transcription pipeline (WhisperX) with pysentimiento models.

## Language

**Job**:
One unit of queued work: a single audio's trip through transcription and analysis, tracked from upload to result.
_Avoid_: Task, request

**Transcript**:
The text WhisperX produces for one audio, split into Segments, with a detected language.
_Avoid_: Transcription (for the result), text

**Segment**:
A stretch of a Transcript with a start, an end, a speaker and its text; the smallest thing an Analysis labels.
_Avoid_: Sentence, chunk, utterance

**Speaker**:
A voice that diarization tells apart inside one Transcript, labelled per Job (`SPEAKER_00`); not a known person.
_Avoid_: Person, participant, user

**Voice**:
A pseudonymous identity that recognises the same voice across Jobs of one organisation; each Speaker points to at most one Voice.
_Avoid_: Speaker (that one lives inside a single Transcript), person, profile

**Analysis**:
One kind of NLP labelling run over Segments: sentiment, emotion, hate speech, irony, NER, POS or targeted sentiment.
_Avoid_: Task (pysentimiento's `task=` argument keeps that name), model
