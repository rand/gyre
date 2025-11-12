import json
from typing import List


class DummyLM:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return {}


class MockPrediction:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"MockPrediction({self.__dict__})"


class Predict:
    def __init__(self, signature, lm=None):
        self.signature = signature
        self.lm = lm or DummyLM()

    def compile(self, *args, **kwargs):
        return None

    def __call__(self, *args, **kwargs):
        name = getattr(self.signature, "__name__", "")
        if name == "RankCandidates":
            items_raw = kwargs.get("items_json", "[]")
            if isinstance(items_raw, str):
                try:
                    items = json.loads(items_raw)
                except json.JSONDecodeError:
                    items = []
            else:
                items = items_raw
            ranked_ids: List[str] = []
            for item in items:
                if isinstance(item, dict) and item.get("id"):
                    ranked_ids.append(str(item["id"]))
            return MockPrediction(ranked_ids_json=json.dumps(ranked_ids))
        return MockPrediction(**kwargs)


class ChainOfThought(Predict):
    pass


class OpenAI(DummyLM):
    pass

class settings:
    lm = DummyLM()

def configure(lm=None):
    if lm:
        settings.lm = lm


class teleprompt:
    class MIPROv2:
        def __init__(self, *args, **kwargs):
            self.metric = kwargs.get("metric")

        def compile(self, *args, **kwargs):
            return None

    class COPRO(MIPROv2):
        pass
