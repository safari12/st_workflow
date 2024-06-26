import unittest
import asyncio
import time

from st_workflow import Workflow, ExecutionMode, Scope


def step_pickle():
    time.sleep(1)
    return 2


class TestWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = Workflow({})

    def step(self):
        return "hello_world"

    def step_a(self):
        return "hello_world b"

    def step_b(self):
        return "hello_world"

    def step_with_ctx(self, ctx: dict):
        return ctx

    def step_with_param(self, step: str):
        return step

    def step_with_multi_param(self, step_a: str, step_b: str):
        return [step_a, step_b]

    def step_return_true(self):
        return True

    def step_return_false(self):
        return False

    async def step_async(self):
        await asyncio.sleep(300)
        return "hello_world"

    def step_raise_err(self):
        raise ValueError("error_test")

    def step_raise_err_two(self):
        raise ValueError("error_test")

    def step_with_time(self):
        time.sleep(1)
        return "hello_world"

    def step_cancel(self, ctx):
        ctx["cancel"] = True

    def step_set_ctx(self, ctx):
        ctx["step"] = "hello_world"

    def step_with_retries(self, ctx):
        retries = ctx.get("retries", 1)
        if retries >= 3:
            return retries

        retries += 1
        ctx["retries"] = retries
        raise ValueError()

    async def step_with_timeout(self):
        await asyncio.sleep(3)
        return "hello_world"

    def test_steps(self):
        self.workflow.add_step(self.step_a)
        self.workflow.add_step(self.step_b)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertFalse(ctx["error"])
        self.assertEqual(ctx["step_a"], self.step_a())
        self.assertEqual(ctx["step_b"], self.step_b())

    def test_steps_with_ctx(self):
        self.workflow.add_step(self.step_with_ctx)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertFalse(ctx["error"])
        self.assertEqual(ctx["step_with_ctx"], ctx)

    def test_steps_with_param(self):
        self.workflow.add_step(self.step)
        self.workflow.add_step(self.step_with_param)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        expected_param = ctx["step"]
        self.assertFalse(ctx["error"])
        self.assertEqual(ctx["step_with_param"], expected_param)

    def test_steps_with_multi_param(self):
        expected_result = [self.step_a(), self.step_b()]
        self.workflow.add_step(self.step_a)
        self.workflow.add_step(self.step_b)
        self.workflow.add_step(self.step_with_multi_param)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertFalse(ctx["error"])
        self.assertEqual(ctx["step_with_multi_param"], expected_result)

    def test_add_error_steps(self):
        expected_result = self.step()
        self.workflow.add_step(self.step_raise_err)
        self.workflow.add_error_step(self.step)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        err_key = f"{Scope.NORMAL.value}_error"
        err = ctx.get(err_key, {})
        self.assertIsNotNone(err)
        self.assertEqual(err["step"], "step_raise_err")
        self.assertEqual(str(err["error"]), "error_test")
        self.assertEqual(ctx["step"], expected_result)

    def test_err_raise_in_error_steps(self):
        self.workflow.add_step(self.step_raise_err, name="step_a")
        self.workflow.add_error_step(self.step_raise_err, name="step_b")
        with self.assertRaises(Exception) as results:
            asyncio.run(self.workflow.run())
        self.assertTrue("error_test" in str(results.exception))

    def test_err_raise_in_exit_steps(self):
        self.workflow.add_step(self.step_raise_err, name="step_a")
        self.workflow.add_exit_step(self.step_raise_err, name="step_b")
        with self.assertRaises(Exception) as results:
            asyncio.run(self.workflow.run())
        self.assertTrue("error_test" in str(results.exception))

    def test_step_retries(self):
        self.workflow.add_step(self.step_with_retries, retries=3)
        asyncio.run(self.workflow.run())
        retries = self.workflow.ctx.get("step_with_retries")
        self.assertEqual(retries, 3)

    def test_step_with_timeout(self):
        self.workflow.add_step(self.step_with_timeout, timeout=1)
        with self.assertRaises(Exception) as results:
            asyncio.run(self.workflow.run())
        self.assertIsInstance(results.exception, asyncio.TimeoutError)

    def test_ctx_init(self):
        db = "test_db"
        workflow = Workflow({"db": db})
        ctx = workflow.ctx
        self.assertEqual(ctx["db"], "test_db")

    def test_true_cond_step(self):
        expected_result = self.step()
        self.workflow.add_step(self.step_return_true)
        self.workflow.add_cond_step(self.step, self.step_return_false)
        self.workflow.add_step(self.step_return_false)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertFalse(ctx["error"])
        self.assertEqual(ctx["step"], expected_result)

    def test_false_cond_step(self):
        expected_result = self.step()
        self.workflow.add_step(self.step_return_false)
        self.workflow.add_cond_step(self.step_return_true, self.step)
        self.workflow.add_step(self.step_return_true)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertFalse(ctx["error"])
        self.assertEqual(ctx["step"], expected_result)

    def test_cond_step_with_params(self):
        self.workflow.add_step(self.step_a)
        self.workflow.add_step(self.step_b)
        self.workflow.add_step(self.step_return_true)
        self.workflow.add_cond_step(self.step_with_multi_param, self.step_return_false)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertFalse(ctx["error"])
        self.assertEqual(ctx["step_with_multi_param"], [self.step_a(), self.step_b()])

    def test_parallel_steps(self):
        steps = [self.step_with_time] * 10
        blah = [step_pickle] * 10
        self.workflow.add_parallel_steps("parallel_steps", steps)
        self.workflow.add_parallel_steps(
            "parallel_steps_with_process", blah, ExecutionMode.PROCESS
        )

        start_time = time.time()
        asyncio.run(self.workflow.run())
        end_time = time.time()

        ctx = self.workflow.ctx
        results = ctx.get("parallel_steps")
        proc_results = ctx.get("parallel_steps_with_process")

        self.assertIsNotNone(results)
        self.assertIsNotNone(proc_results)
        self.assertEqual(results, ["hello_world"] * 10)
        self.assertEqual(proc_results, [2] * 10)
        self.assertLess(end_time - start_time, 2 + 0.5)

    def test_cancel_step(self):
        self.workflow.add_step(self.step_a)
        self.workflow.add_step(self.step_b)
        self.workflow.add_step(self.step_cancel)
        self.workflow.add_step(self.step)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertFalse(ctx.get("error"))
        self.assertIsNone(ctx.get("step"))
        self.assertEqual(ctx["step_b"], self.step_b())

    def test_sub_workflow_breaker(self):
        async def run_sub_workflow():
            sub_workflow = Workflow({})
            sub_workflow.add_step(self.step_a)
            await sub_workflow.run()
            return sub_workflow.ctx

        self.workflow.add_step(self.step_return_true)
        self.workflow.add_cond_step(run_sub_workflow, self.step_return_false)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx.get("run_sub_workflow", {})
        self.assertFalse(ctx.get("error"))
        self.assertEqual(ctx.get("step_a"), self.step_a())

    def test_exit_steps(self):
        self.workflow.add_step(self.step_a)
        self.workflow.add_exit_step(self.step_b)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertEqual(ctx.get("step_b"), self.step_b())

    def test_exit_steps_with_err(self):
        self.workflow.add_step(self.step_raise_err)
        self.workflow.add_exit_step(self.step)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertEqual(ctx.get("step"), self.step())

    def test_cont_on_err(self):
        self.workflow.add_step(self.step_raise_err, cont_on_err=True)
        self.workflow.add_step(self.step)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertEqual(ctx.get("step"), self.step())

    def test_raise_err_no_steps(self):
        self.workflow.add_step(self.step_raise_err)
        self.workflow.add_step(self.step)
        with self.assertRaises(Exception) as results:
            asyncio.run(self.workflow.run())
        self.assertTrue("error_test" in str(results.exception))

    def test_run_with_args(self):
        self.workflow.add_step(self.step_with_multi_param)
        asyncio.run(self.workflow.run(step_a="hello", step_b="world"))
        ctx = self.workflow.ctx
        self.assertEqual(ctx.get("step_with_multi_param"), ["hello", "world"])

    def test_error_step_with_step_func(self):
        self.workflow.add_step(self.step_raise_err)
        self.workflow.add_error_step(self.step, step_func=self.step_raise_err)
        asyncio.run(self.workflow.run())
        self.assertEqual(self.workflow.ctx.get("step"), "hello_world")

    def test_multiple_error_step_with_func(self):
        self.workflow.add_step(self.step_raise_err)
        self.workflow.add_step(self.step_raise_err_two)
        self.workflow.add_error_step(self.step_a, step_func=self.step_raise_err)
        self.workflow.add_error_step(self.step_b, step_func=self.step_raise_err_two)
        asyncio.run(self.workflow.run())
        self.assertEqual(self.workflow.ctx.get("step_a"), self.step_a())
        self.assertIsNone(self.workflow.ctx.get("step_b"))

    def test_multiple_cont_error_step_with_func(self):
        self.workflow.add_step(self.step_raise_err, cont_on_err=True)
        self.workflow.add_step(self.step_raise_err_two)
        self.workflow.add_error_step(self.step_a, step_func=self.step_raise_err)
        self.workflow.add_error_step(self.step_b, step_func=self.step_raise_err_two)
        asyncio.run(self.workflow.run())
        self.assertEqual(self.workflow.ctx.get("step_a"), self.step_a())
        self.assertEqual(self.workflow.ctx.get("step_b"), self.step_b())

    def test_error_step_with_step_func_throw_err(self):
        self.workflow.add_step(self.step_raise_err)
        self.workflow.add_error_step(
            self.step_raise_err_two, step_func=self.step_raise_err
        )
        self.workflow.add_error_step(self.step)
        asyncio.run(self.workflow.run())
        self.assertEqual(self.workflow.ctx.get("step"), self.step())

    def test_true_cond_multi_steps(self):
        self.workflow.add_step(self.step_return_true)
        self.workflow.add_cond_step([self.step_a, self.step_b], self.step_return_false)
        asyncio.run(self.workflow.run())
        self.assertIsNone(self.workflow.ctx.get("step_return_false"))
        self.assertEqual(self.workflow.ctx["step_a"], self.step_a())
        self.assertEqual(self.workflow.ctx["step_b"], self.step_b())

    def test_false_cond_multi_steps(self):
        self.workflow.add_step(self.step_return_false)
        self.workflow.add_cond_step(self.step_return_true, [self.step_a, self.step_b])
        asyncio.run(self.workflow.run())
        self.assertIsNone(self.workflow.ctx.get("step_return_true"))
        # self.assertEqual()

        # def test_io_simulate(self):
        #     async def main():
        #         self.workflow.add_step('async_step_a', self.async_step_a)
        #         await asyncio.gather(self.workflow.run(), self.outside_step())
        #     asyncio.run(main())
