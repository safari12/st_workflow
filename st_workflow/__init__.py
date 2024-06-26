from dataclasses import dataclass
from enum import Enum
from itertools import chain
from typing import Callable, List, Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import inspect
import asyncio


class Scope(Enum):
    NORMAL = "normal"
    ERROR = "error"
    EXIT = "exit"


class ExecutionMode(Enum):
    THREAD = "thread"
    PROCESS = "process"


@dataclass
class Step:
    func: Callable
    name: Optional[str] = None
    timeout: Optional[int] = None
    retries: int = 0
    cont_on_err: bool = False
    err_step: Optional["Step"] = None


type CondSteps = Callable | Step | List[Callable] | List[Step]


class Workflow:
    def __init__(self, ctx: dict) -> None:
        self.ctx = ctx
        self.ctx["cancel"] = False
        self.ctx["error"] = False
        self.thread_executor = ThreadPoolExecutor()
        self.process_executor = ProcessPoolExecutor()
        self.steps: dict[str, list[Step]] = {
            Scope.NORMAL.value: [],
            Scope.ERROR.value: [],
            Scope.EXIT.value: [],
        }

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)

    def add_step(
        self,
        func: Callable,
        scope=Scope.NORMAL,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        retries: int = 0,
        cont_on_err: bool = False,
        err_step: Optional[Step] = None,
    ):
        if name is None:
            name = func.__name__

        self.steps[scope.value].append(
            Step(
                func=func,
                name=name,
                err_step=err_step,
                timeout=timeout,
                retries=retries,
                cont_on_err=cont_on_err,
            )
        )

    def add_error_step(
        self,
        func: Callable,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        step_func: Optional[Callable] = None,
        retries: int = 0,
    ):
        if step_func:
            steps = filter(
                lambda s: s.name == step_func.__name__, self.steps[Scope.NORMAL.value]
            )
            step = next(steps)
            step.err_step = Step(
                name=func.__name__, func=func, timeout=timeout, retries=retries
            )
        else:
            self.add_step(func, Scope.ERROR, name, timeout, retries)

    def add_exit_step(
        self,
        func: Callable,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        retries: int = 0,
    ):
        self.add_step(func, Scope.EXIT, name, timeout, retries)

    def add_cond_step(
        self,
        on_true_steps: CondSteps,
        on_false_steps: CondSteps,
        scope=Scope.NORMAL,
    ):
        prev_step = self.steps[scope.value][-1]

        async def cond_step():
            prev_result = self.ctx.get(prev_step.name)

            next_steps = on_true_steps if prev_result else on_false_steps

            if not isinstance(next_steps, List):
                next_steps = [next_steps]

            for step in next_steps:
                if isinstance(step, Callable):
                    step = Step(func=step, name=step.__name__)
                results = await self._run_step(step)

                if results:
                    self.ctx[results[0]] = results[1]

        self.add_step(cond_step, scope)

    def add_parallel_steps(
        self,
        name: str,
        steps: list[Callable],
        execution_mode=ExecutionMode.THREAD,
        scope=Scope.NORMAL,
        timeout: Optional[int] = None,
        retries: int = 0,
    ):
        async def parallel_step():
            tasks = []
            executor = (
                self.thread_executor
                if execution_mode == ExecutionMode.THREAD
                else self.process_executor
            )

            for func in steps:
                args = self._get_step_args(func)
                if asyncio.iscoroutinefunction(func):
                    task = asyncio.ensure_future(func(*args))
                else:
                    loop = asyncio.get_running_loop()
                    task = loop.run_in_executor(executor, func, *args)  # type: ignore

                tasks.append(task)

            return await asyncio.gather(*tasks)

        self.add_step(parallel_step, scope, name, timeout, retries)

    async def run_steps(self, scope: Scope):
        steps = self.steps[scope.value]
        for step in steps:
            try:
                if self.ctx.get("cancel", False):
                    break

                results = await self._run_step(step)
                if results:
                    step_name = results[0]
                    result = results[1]
                    self.ctx[step_name] = result
                    if (
                        step.err_step
                        and step_name == step.err_step.name
                        and not step.cont_on_err
                    ):
                        break
            except Exception as e:
                self.ctx[f"{scope.value}_error"] = {"step": step.name, "error": e}
                if not step.cont_on_err:
                    raise e

    async def run(self, **kwargs):
        self.ctx.update(kwargs)
        try:
            await self.run_steps(Scope.NORMAL)
        except Exception as e:
            self.ctx["error"] = True
            if (
                len(self.steps[Scope.ERROR.value]) == 0
                and len(self.steps[Scope.EXIT.value]) == 0
            ):
                raise e
            else:
                await self.run_steps(Scope.ERROR)
        finally:
            await self.run_steps(Scope.EXIT)

    def cancel(self):
        self.ctx["cancel"] = True

    def get_step_value(self, func: Callable):
        try:
            steps = list(chain.from_iterable(self.steps.values()))
            steps = filter(lambda s: s.func.__name__ == func.__name__, steps)
            step = next(steps)
            return self.ctx[step.name]
        except StopIteration:
            return None

    def _get_step_args(self, func: Callable):
        func_args = inspect.signature(func).parameters
        if "ctx" in func_args:
            return [self.ctx]
        else:
            return [self.ctx[arg] for arg in func_args]

    async def _run_step(self, step: Step):
        args = self._get_step_args(step.func)

        for i in range(step.retries + 1):
            try:
                if asyncio.iscoroutinefunction(step.func):
                    if step.timeout is not None:
                        result = await asyncio.wait_for(
                            step.func(*args), timeout=step.timeout
                        )
                        return (step.name, result)
                    else:
                        result = await step.func(*args)
                        return (step.name, result)
                else:
                    return (step.name, step.func(*args))
            except Exception as e:
                if step.err_step:
                    return await self._run_step(step.err_step)
                if i == step.retries:
                    raise e
