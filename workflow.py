from enum import Enum
from typing import Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import inspect
import asyncio


class Scope(Enum):
    NORMAL = 'normal'
    ERROR = 'error'
    EXIT = 'exit'


class ExecutionMode(Enum):
    THREAD = 'thread'
    PROCESS = 'process'


class Workflow:
    def __init__(self, ctx: dict) -> None:
        self.ctx = ctx
        self.ctx['cancel'] = False
        self.thread_executor = ThreadPoolExecutor()
        self.process_executor = ProcessPoolExecutor()
        self.steps = {
            Scope.NORMAL.value: [],
            Scope.ERROR.value: [],
            Scope.EXIT.value: []
        }

    def __del__(self):
        self.thread_executor.shutdown()
        self.process_executor.shutdown()

    def add_step(self, name: str, func: Callable, scope=Scope.NORMAL):
        self.steps[scope.value].append({
            'name': name,
            'func': func,
        })

    def add_error_step(self, name: str, func: Callable):
        self.add_step(
            name,
            func,
            Scope.ERROR
        )

    def add_exit_step(self, name: str, func: Callable):
        self.add_step(
            name,
            func,
            Scope.EXIT
        )

    def add_cond_step(
            self,
            name: str,
            on_true_step: Callable,
            on_false_step: Callable,
            scope=Scope.NORMAL):
        async def cond_step():
            prev_result = self.ctx.get(
                self.steps[scope.value][-2]['name']) if self.steps[scope.value] else None
            step_func = on_true_step if prev_result else on_false_step
            args = self._get_step_args(step_func)
            return await self._run_step(step_func, *args)
        self.add_step(
            name,
            cond_step,
            scope
        )

    def add_parallel_steps(
            self,
            name: str,
            steps: list[Callable],
            execution_mode=ExecutionMode.THREAD,
            scope=Scope.NORMAL):
        async def parallel_step():
            tasks = []
            executor = self.thread_executor if execution_mode == ExecutionMode.THREAD else self.process_executor

            for func in steps:
                args = self._get_step_args(func)
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
            scope
        )

    async def run_steps(self, scope: Scope):
        steps = self.steps[scope.value]
        for step in steps:
            if self.ctx.get('cancel', False):
                break

            func = step['func']
            args = self._get_step_args(func)
            result = await self._run_step(func, *args)
            self.ctx[step['name']] = result

    async def run(self):
        try:
            await self.run_steps(Scope.NORMAL)
        except Exception as e:
            self.ctx['error'] = str(e)
            await self.run_steps(Scope.ERROR)
        finally:
            await self.run_steps(Scope.EXIT)

    def cancel(self):
        self.ctx['cancel'] = True

    def _get_step_args(self, func: Callable):
        func_args = inspect.signature(func).parameters
        if 'ctx' in func_args:
            return [self.ctx]
        else:
            return [self.ctx[arg] for arg in func_args]

    async def _run_step(self, func: Callable, *args):
        if asyncio.iscoroutinefunction(func):
            return await func(*args)
        else:
            return func(*args)
