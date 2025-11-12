import os
from pathlib import Path

MOCK_DSPY = os.environ.get("DSPY_MOCK", "0") == "1"

CACHE_ROOT = Path(__file__).resolve().parents[1] / "data" / "dspy_cache"
CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DSP_CACHEDIR", str(CACHE_ROOT))
os.environ.setdefault("DSP_NOTEBOOK_CACHEDIR", str(CACHE_ROOT / "notebook"))
os.environ.setdefault("DSPY_CACHEDIR", str(CACHE_ROOT / "litellm"))

try:
    if not MOCK_DSPY:
        import dspy  # type: ignore
        if hasattr(dspy, "OpenAI"):
            dspy.configure(lm=dspy.OpenAI())
        else:
            raise ImportError
    else:
        raise ImportError
except ImportError:
    from . import dspy_mock as dspy
    dspy.configure()

from .signatures import (
    ObserveSession, ProposePatches, RankCandidates, SummarizeForSlot,
    EVofDeferredQuery, RedactForScope, BlueprintFill
)

# Choose backends; swap to your preferred models
FAST_LM  = dspy.OpenAI(model="gpt-4o-mini")  # inexpensive, low-latency
TRUST_LM = dspy.OpenAI(model="gpt-4.1")      # higher quality

# Modules
observe      = dspy.Predict(ObserveSession, lm=FAST_LM)
propose      = dspy.ChainOfThought(ProposePatches, lm=TRUST_LM)
ranker       = dspy.Predict(RankCandidates, lm=FAST_LM)
summarizer   = dspy.ChainOfThought(SummarizeForSlot, lm=TRUST_LM)
ev_estimator = dspy.Predict(EVofDeferredQuery, lm=FAST_LM)
redactor     = dspy.Predict(RedactForScope, lm=FAST_LM)
composer     = dspy.Predict(BlueprintFill, lm=FAST_LM)

# Optimizers (compile later when datasets exist)
from dspy.teleprompt import MIPROv2, COPRO

def compile_programs(datasets, prompt_model=None, task_model=None):
    """Compile DSPy modules using logged datasets."""
    shared_kwargs = {"auto": "light", "prompt_model": prompt_model or dspy.settings.lm, "task_model": task_model or dspy.settings.lm}
    rank_opt = MIPROv2(metric=_rank_metric, **shared_kwargs)
    sum_opt  = MIPROv2(metric=_summary_metric, **shared_kwargs)
    ev_opt   = COPRO(metric=_ev_metric, prompt_model=shared_kwargs["prompt_model"], task_model=shared_kwargs["task_model"])
    red_opt  = COPRO(metric=_redact_metric, prompt_model=shared_kwargs["prompt_model"], task_model=shared_kwargs["task_model"])
    blue_opt = MIPROv2(metric=_blueprint_metric, **shared_kwargs)

    if datasets.get("rank_train"):
        rank_opt.compile(ranker, trainset=datasets["rank_train"])
    if datasets.get("sum_train"):
        sum_opt.compile(summarizer, trainset=datasets["sum_train"])
    if datasets.get("ev_train"):
        ev_opt.compile(ev_estimator, trainset=datasets["ev_train"])
    if datasets.get("red_train"):
        red_opt.compile(redactor, trainset=datasets["red_train"])
    if datasets.get("blue_train"):
        blue_opt.compile(composer, trainset=datasets["blue_train"])

def _rank_metric(yhat, y):
    return 1.0 if yhat == y else 0.0

def _summary_metric(yhat, y):
    return 1.0

def _ev_metric(yhat, y):
    return 1.0

def _redact_metric(yhat, y):
    return 1.0

def _blueprint_metric(yhat, y):
    return 1.0
