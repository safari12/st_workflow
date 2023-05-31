from enum import Enum
import inspect


class Scope(Enum):
    NORMAL = 'normal'
    ERROR = 'error'


class Workflow:
    deps: dict = {}
    context: dict = {}
    steps = {
        Scope.NORMAL.value: [],
        Scope.ERROR.value: []
    }

    def __init__(self, deps: dict, context: dict = {}) -> None:
        self.deps = deps
        self.context = context
        self.context['cancel'] = False

    def add_step(self, name: str, func: callable, params: list[str] = [], scope = Scope.NORMAL):
        self.steps[scope.value].append({
            'name': name,
            'func': func,
            'params': params
        })

    def add_error_step(self, name: str, func: callable, params: list[str] = []):
        self.add_step(
            name,
            func,
            params,
            Scope.ERROR
        )

    def run_steps(self, scope: Scope):
        steps = self.steps[scope.value]
        for step in steps:
            if self.context.get('cancel', False):
                break

            if 'context' in inspect.signature(step['func']).parameters:
                args = [self.context]
            else:
                args = [self.context[arg] for arg in step.get('params', [])]

            result = step['func'](*args)
            self.context[step['name']] = result

    def run(self):
        try:
            self.run_steps(Scope.NORMAL)
        except Exception as e:
            self.context['error'] = str(e)
            self.run_steps(Scope.ERROR)

    def cancel(self):
        self.context['cancel'] = True
