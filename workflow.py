from enum import Enum
from typing import Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import inspect
import asyncio


class Scope(Enum):
    NORMAL = 'normal'
    ERROR = 'error'


class ExecutionMode(Enum):
    THREAD = 'thread'
    PROCESS = 'process'


class Workflow:
    def __init__(self, context: dict) -> None:
        self.context = context
        self.context['cancel'] = False
        self.steps = {
            Scope.NORMAL.value: [],
            Scope.ERROR.value: []
        }

    def add_step(self, name: str, func: Callable, params: list[str] = [], scope=Scope.NORMAL):
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
            scope=Scope.NORMAL):
        async def cond_step(*args):
            prev_result = self.context.get(
                self.steps[scope.value][-2]['name']) if self.steps[scope.value] else None
            step_func = on_true_step if prev_result else on_false_step
            return await self._run_step(step_func, *args)
        self.add_step(
            name,
            cond_step,
            params,
            scope
        )

    def add_parallel_steps(
            self,
            name: str,
            steps: list[Callable],
            execution_mode=ExecutionMode.THREAD,
            params: list[str] = [],
            scope=Scope.NORMAL):
        async def parallel_step(*args):
            tasks = []
            executor = ThreadPoolExecutor(
            ) if execution_mode == ExecutionMode.THREAD else ProcessPoolExecutor

            for func in steps:
                if asyncio.iscoroutinefunction(func):
                    task = asyncio.ensure_future(func(*args))
                else:
                    loop = asyncio.get_running_loop()
                    task = loop.run_in_executor(executor, func, *args)

                tasks.append(task)

            return await asyncio.gather(*tasks)

        self.add_step(
            name,
            parallel_step,
            params,
            scope
        )

    async def run_steps(self, scope: Scope):
        steps = self.steps[scope.value]
        for step in steps:
            if self.context.get('cancel', False):
                break

            func = step['func']
            params = step.get('params', [])
            args = self._get_step_args(func, params)
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

    def _get_step_args(self, func: Callable, params: list[str]):
        if 'context' in inspect.signature(func).parameters:
            return [self.context]
        else:
            return [self.context[arg] for arg in params]

    async def _run_step(self, func: Callable, *args):
        if asyncio.iscoroutinefunction(func):
            return await func(*args)
        else:
            return func(*args)
