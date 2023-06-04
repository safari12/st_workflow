from enum import Enum
import inspect
import asyncio


class Scope(Enum):
    NORMAL = 'normal'
    ERROR = 'error'


class Workflow:
    context: dict = {}
    steps = {
        Scope.NORMAL.value: [],
        Scope.ERROR.value: []
    }

    def __init__(self, context: dict = {}) -> None:
        self.context = context
        self.context['cancel'] = False

    def add_step(self, name: str, func: callable, params: list[str] = [], scope = Scope.NORMAL):
        async def async_wrapper(*args):
            return await func(*args)

        if asyncio.iscoroutinefunction(func):
            self.steps[scope.value].append({
                'name': name,
                'func': async_wrapper,
                'params': params
            })
        else:
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

    async def run_steps(self, scope: Scope):
        steps = self.steps[scope.value]
        for step in steps:
            if self.context.get('cancel', False):
                break

            func: callable = step['func']

            if 'context' in inspect.signature(func).parameters:
                args = [self.context]
            else:
                args = [self.context[arg] for arg in step.get('params', [])]

            args = args ++ []

            if asyncio.iscoroutinefunction(func):
                result = await func(*args)
            else:
                result = func(*args)

            self.context[step['name']] = result

    async def run(self):
        try:
            await self.run_steps(Scope.NORMAL)
        except Exception as e:
            self.context['error'] = str(e)
            await self.run_steps(Scope.ERROR)

    def cancel(self):
        self.context['cancel'] = True
