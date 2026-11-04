# voice-insights

Audio analysis pipeline under construction: transcription with diarization (WhisperX) and per-segment sentiment, emotion and NLP analysis (pysentimiento), behind a multi-tenant Jobs API.

**Status:** early development. The code in `app/` is the legacy synchronous service; the target architecture lives in `docs/adr/`, the vocabulary in `GLOSSARY.md`, and the build order in `plans/migracion-monorepo.md`.

## Credits

Built on [pysentimiento](https://github.com/pysentimiento/pysentimiento) and [WhisperX](https://github.com/m-bain/whisperX).

## License

MIT. See `LICENSE`.
