from typing import Callable
from copy import deepcopy

class Typer:
    def __init__(self):
        self.callables = {}
        self.typed = {}
        for function_name, function in phpfunctions.functionlist:
            self.callables[function_name] = self.type_sig(function)

    def type_sig(self, function: Callable):
        if hasattr(function, "__annotations__"):
            return function.__annotations__
        else:
            return None

def test(bob: str) -> int:
    pass

if __name__ == "__main__":
    print(test)
    print(test.__annotations__)
    t = Typer()
    import pprint
    pprint.pprint(t.callables)
