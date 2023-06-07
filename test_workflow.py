import unittest
import asyncio
import time

from workflow import Workflow, ExecutionMode, Scope


def step_pickle():
    time.sleep(1)
    return 2


class TestWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = Workflow({})

    def step(self):
        return 'hello_world'

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
        return 'hello_world'

    def step_raise_err(self):
        raise ValueError('error_test')

    def step_with_time(self):
        time.sleep(1)
        return 'hello_world'
    
    def step_cancel(self, ctx):
        ctx['cancel'] = True

    def test_steps(self):
        expected_result = self.step()
        self.workflow.add_step('step_a', self.step)
        self.workflow.add_step('step_b', self.step)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertIsNone(ctx.get('error'))
        self.assertEqual(ctx['step_a'], expected_result)
        self.assertEqual(ctx['step_b'], expected_result)

    def test_steps_with_ctx(self):
        self.workflow.add_step('step_a', self.step_with_ctx)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertIsNone(ctx.get('error'))
        self.assertEqual(ctx['step_a'], ctx)

    def test_steps_with_param(self):
        self.workflow.add_step('step', self.step)
        self.workflow.add_step(
            'step_with_param', self.step_with_param)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        expected_param = ctx['step']
        self.assertIsNone(ctx.get('error'))
        self.assertEqual(ctx['step_with_param'], expected_param)

    def test_steps_with_multi_param(self):
        expected_result = [self.step(), self.step()]
        self.workflow.add_step('step_a', self.step)
        self.workflow.add_step('step_b', self.step)
        self.workflow.add_step('step_c',
                               self.step_with_multi_param)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertIsNone(ctx.get('error'))
        self.assertEqual(ctx['step_c'], expected_result)

    def test_add_error_steps(self):
        expected_result = self.step()
        self.workflow.add_step('step_a', self.step_raise_err)
        self.workflow.add_error_step('step_a_err', self.step)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        err_key = f'{Scope.NORMAL.value}_error'
        err = ctx.get(err_key, {})
        self.assertIsNotNone(err)
        self.assertEqual(err['step'], 'step_a')
        self.assertEqual(str(err['error']), 'error_test')
        self.assertEqual(ctx['step_a_err'], expected_result)

    def test_ctx_init(self):
        db = 'test_db'
        workflow = Workflow({'db': db})
        ctx = workflow.ctx
        self.assertEqual(ctx['db'], 'test_db')

    def test_true_cond_step(self):
        expected_result = self.step()
        self.workflow.add_step('step_a', self.step_return_true)
        self.workflow.add_cond_step(
            'cond_step', self.step, self.step_return_false)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertIsNone(ctx.get('error'))
        self.assertEqual(ctx['cond_step'], expected_result)

    def test_false_cond_step(self):
        expected_result = self.step()
        self.workflow.add_step('step_a', self.step_return_false)
        self.workflow.add_cond_step(
            'cond_step', self.step_return_true, self.step)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertIsNone(ctx.get('error'))
        self.assertEqual(ctx['cond_step'], expected_result)

    def test_cond_step_with_params(self):
        self.workflow.add_step('step_a', self.step)
        self.workflow.add_step('step_b', self.step)
        self.workflow.add_step('step_return_true', self.step_return_true)
        self.workflow.add_cond_step(
            'step_cond',
            self.step_with_multi_param,
            self.step_return_false
        )
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertIsNone(ctx.get('error'))
        self.assertEqual(ctx['step_cond'], [self.step(), self.step()])

    def test_parallel_steps(self):
        steps = [self.step_with_time] * 10
        blah = [step_pickle] * 10
        self.workflow.add_parallel_steps(
            'parallel_steps',
            steps
        )
        self.workflow.add_parallel_steps(
            'parallel_steps_with_process',
            blah,
            ExecutionMode.PROCESS
        )

        start_time = time.time()
        asyncio.run(self.workflow.run())
        end_time = time.time()

        ctx = self.workflow.ctx
        results = ctx.get('parallel_steps')
        proc_results = ctx.get('parallel_steps_with_process')

        self.assertIsNotNone(results)
        self.assertIsNotNone(proc_results)
        self.assertEqual(results, ['hello_world'] * 10)
        self.assertEqual(proc_results, [2] * 10)
        self.assertLess(end_time - start_time, 2 + 0.5)

    def test_cancel_step(self):
        self.workflow.add_step('step_a', self.step)
        self.workflow.add_step('step_b', self.step)
        self.workflow.add_step('step_cancel', self.step_cancel)
        self.workflow.add_step('step_c', self.step)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertIsNone(ctx.get('error'))
        self.assertIsNone(ctx.get('step_c'))
        self.assertEqual(ctx['step_b'], self.step())

    def test_sub_workflow_breaker(self):
        async def run_sub_workflow():
            sub_workflow = Workflow({})
            sub_workflow.add_step('step_a', self.step)
            await sub_workflow.run()
            return sub_workflow.ctx
        
        self.workflow.add_step('step_a', self.step_return_true)
        self.workflow.add_cond_step('sub_workflow', run_sub_workflow, self.step_return_false)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx.get('sub_workflow', {})
        self.assertIsNone(ctx.get('error'))
        self.assertEqual(ctx.get('step_a'), self.step())

    def test_exit_steps(self):
        self.workflow.add_step('step_a', self.step)
        self.workflow.add_exit_step('step_b', self.step)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertEqual(ctx.get('step_b'), self.step())

    def test_exit_steps_with_err(self):
        self.workflow.add_step('step_a', self.step_raise_err)
        self.workflow.add_exit_step('step_b', self.step)
        asyncio.run(self.workflow.run())
        ctx = self.workflow.ctx
        self.assertEqual(ctx.get('step_b'), self.step())

        # def test_io_simulate(self):
        #     async def main():
        #         self.workflow.add_step('async_step_a', self.async_step_a)
        #         await asyncio.gather(self.workflow.run(), self.outside_step())
        #     asyncio.run(main())
