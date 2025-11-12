class DummyLM:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return {}


class Predict:
    def __init__(self, signature, lm=None):
        self.signature = signature
        self.lm = lm or DummyLM()

    def compile(self, *args, **kwargs):
        return None


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
