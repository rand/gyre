import dspy
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

def compile_programs(datasets):
    """Compile DSPy modules using small logged datasets.
    datasets: dict with keys rank_train, sum_train, ev_train, red_train, blue_train
    """
    rank_opt = MIPROv2(metric=lambda yhat,y: 0.0, auto="light")
    sum_opt  = MIPROv2(metric=lambda yhat,y: 0.0, auto="light")
    ev_opt   = COPRO(metric=lambda yhat,y: 0.0)
    red_opt  = COPRO(metric=lambda yhat,y: 0.0)
    blue_opt = MIPROv2(metric=lambda yhat,y: 0.0, auto="light")

    # NOTE: Replace dummy metrics with real ones in /scripts/seed_datasets.py
    rank_opt.compile(ranker,     trainset=datasets.get("rank_train", []))
    sum_opt.compile(summarizer,  trainset=datasets.get("sum_train", []))
    ev_opt.compile(ev_estimator, trainset=datasets.get("ev_train", []))
    red_opt.compile(redactor,    trainset=datasets.get("red_train", []))
    blue_opt.compile(composer,   trainset=datasets.get("blue_train", []))
