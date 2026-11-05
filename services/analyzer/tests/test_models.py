"""Seam 3: the real adapters on tiny, randomly initialised models built from a config.

No weights are downloaded. `torch.cuda.is_available` is forced to True so the test host
looks like a GPU host: anything that picked the GPU on its own would fail here.
"""

import pytest
import torch
from pysentimiento.analyzer import AnalyzerForSequenceClassification, AnalyzerForTokenClassification
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from transformers import (
    BertConfig,
    BertForSequenceClassification,
    BertForTokenClassification,
    PreTrainedTokenizerFast,
)

from analyzer.models import Sequence, Tokens

TEXTS = ["me encanta el producto", "pésimo servicio", "pablo vive en madrid", "hola"]
CPU = torch.device("cpu")


def tokenizer():
    words = {w for t in TEXTS for w in t.split()}
    vocab = {w: i for i, w in enumerate(["[PAD]", "[UNK]", *sorted(words)])}
    backend = Tokenizer(WordLevel(vocab, unk_token="[UNK]"))
    backend.pre_tokenizer = Whitespace()
    return PreTrainedTokenizerFast(tokenizer_object=backend, unk_token="[UNK]", pad_token="[PAD]")


def config(labels, **kwargs):
    torch.manual_seed(0)
    return BertConfig(
        vocab_size=32,
        hidden_size=8,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=8,
        id2label=dict(enumerate(labels)),
        label2id={label: i for i, label in enumerate(labels)},
        **kwargs,
    )


def record_devices(model):
    """Devices of every parameter and every input tensor seen by the forward pass."""
    seen = set()

    def hook(module, args, kwargs):
        seen.update(t.device for t in [*args, *kwargs.values()] if isinstance(t, torch.Tensor))
        seen.update(p.device for p in module.parameters())

    model.register_forward_pre_hook(hook, with_kwargs=True)
    return seen


@pytest.fixture
def gpu_host(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # pysentimiento's Trainer is given output_dir="."
    return lambda: monkeypatch.setattr(torch.cuda, "is_available", lambda: True)


@pytest.mark.parametrize(
    "problem_type", ["single_label_classification", "multi_label_classification"]
)
def test_sequence_forward_pass_matches_pysentimiento_on_the_configured_device(
    gpu_host, problem_type
):
    model = BertForSequenceClassification(config(["NEG", "NEU", "POS"], problem_type=problem_type))
    reference = AnalyzerForSequenceClassification(
        model.eval(), tokenizer(), "sentiment", {"lang": "es"}
    )
    expected = reference.predict(TEXTS)
    seen = record_devices(model)
    gpu_host()

    predictions = Sequence(reference, CPU).predict(TEXTS)

    assert seen == {CPU}
    assert [p.output for p in predictions] == [e.output for e in expected]
    for p, e in zip(predictions, expected, strict=True):
        assert p.probas == pytest.approx(e.probas, abs=1e-5)


def test_sequence_batches_long_jobs(gpu_host, monkeypatch):
    model = BertForSequenceClassification(config(["NEG", "POS"])).eval()
    reference = AnalyzerForSequenceClassification(model, tokenizer(), "sentiment", {"lang": "es"})
    monkeypatch.setattr("analyzer.models.BATCH_SIZE", 3)
    calls = []
    model.register_forward_pre_hook(
        lambda m, a, k: calls.append(k["input_ids"].shape[0]), with_kwargs=True
    )

    predictions = Sequence(reference, CPU).predict(TEXTS * 2)

    assert calls == [3, 3, 2] and len(predictions) == 8


@pytest.mark.parametrize("task, chunk", [("ner", True), ("pos", False)])
def test_token_model_runs_on_the_configured_device(gpu_host, task, chunk):
    model = BertForTokenClassification(config(["O", "B-PER", "I-PER", "B-LOC"])).eval()
    analyzer = AnalyzerForTokenClassification(model, tokenizer(), task, lang="es", chunk=chunk)
    seen = record_devices(model)
    gpu_host()

    predictions = Tokens(analyzer, CPU).predict(TEXTS)
    [single] = Tokens(analyzer, CPU).predict(TEXTS[:1])

    assert seen == {CPU}
    assert [p.tokens for p in predictions] == [t.split() for t in TEXTS]
    assert single.tokens == TEXTS[0].split()
    assert all(isinstance(p.entities, list) == chunk for p in predictions)
    assert Tokens(analyzer, CPU).predict([]) == []
