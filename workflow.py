from enum import Enum
from typing import Callable
import inspect
import asyncio


class Scope(Enum):
    NORMAL = 'normal'
    ERROR = 'error'


class Workflow:
    def __init__(self, context: dict) -> None:
        self.context = context
        self.context['cancel'] = False
        self.steps = {
            Scope.NORMAL.value: [],
            Scope.ERROR.value: []
        }

    def add_step(self, name: str, func: Callable, params: list[str] = [], scope = Scope.NORMAL):
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

    def add_error_step(self, name: str, func: Callable, params: list[str] = []):
        self.add_step(
            name,
            func,
            params,
            Scope.ERROR
        )

    def add_cond_step(
            self,
            name: str,
            on_true_step: Callable,
            on_false_step: Callable,
            params: list[str] = [],
            scope = Scope.NORMAL):
        async def cond_step(*args):
            prev_result = self.context.get(self.steps[scope.value][-2]['name']) if self.steps[scope.value] else None
            step_func = on_true_step if prev_result else on_false_step
            return await self._run_step(step_func, *args)
        self.add_step(
            name,
            cond_step,
            params,
            scope
        )

    async def _run_step(self, func: Callable, *args):
        if asyncio.iscoroutinefunction(func):
            return await func(*args)
        else:
            return func(*args)

    async def run_steps(self, scope: Scope):
        steps = self.steps[scope.value]
        for step in steps:
            if self.context.get('cancel', False):
                break

            func: Callable = step['func']

            if 'context' in inspect.signature(func).parameters:
                args = [self.context]
            else:
                args = [self.context[arg] for arg in step.get('params', [])]

            result = await self._run_step(func, *args)
            self.context[step['name']] = result

    async def run(self):
        try:
            await self.run_steps(Scope.NORMAL)
        except Exception as e:
            self.context['error'] = str(e)
            await self.run_steps(Scope.ERROR)

    def cancel(self):
        self.context['cancel'] = True
