import unittest
import asyncio

from workflow import Workflow


class TestWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = Workflow({})
        print(self.workflow.steps)
        print(self.workflow.context)

    def step(self):
        return 'hello_world'

    def step_with_context(self, context: dict):
        return context

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

    # async def async_step_a(self):
    #     print("async step a begin")
    #     await asyncio.sleep(5)
    #     print("async step a end")

    # async def outside_step(self):
    #     print("outside step begin")
    #     await asyncio.sleep(5)
    #     print("outside step end")

    def test_steps(self):
        expected_result = self.step()
        self.workflow.add_step('step_a', self.step)
        self.workflow.add_step('step_b', self.step)
        asyncio.run(self.workflow.run())
        context = self.workflow.context
        self.assertIsNone(context.get('error'))
        self.assertEqual(context['step_a'], expected_result)
        self.assertEqual(context['step_b'], expected_result)

    def test_steps_with_context(self):
        self.workflow.add_step('step_a', self.step_with_context)
        asyncio.run(self.workflow.run())
        context = self.workflow.context
        self.assertIsNone(context.get('error'))
        self.assertEqual(context['step_a'], context)

    def test_steps_with_param(self):
        self.workflow.add_step('step', self.step)
        self.workflow.add_step(
            'step_with_param', self.step_with_param)
        asyncio.run(self.workflow.run())
        context = self.workflow.context
        expected_param = context['step']
        self.assertIsNone(context.get('error'))
        self.assertEqual(context['step_with_param'], expected_param)

    def test_steps_with_multi_param(self):
        expected_result = [self.step(), self.step()]
        self.workflow.add_step('step_a', self.step)
        self.workflow.add_step('step_b', self.step)
        self.workflow.add_step('step_c',
                               self.step_with_multi_param)
        asyncio.run(self.workflow.run())
        context = self.workflow.context
        self.assertIsNone(context.get('error'))
        self.assertEqual(context['step_c'], expected_result)

    async def test_async_steps(self):
        expected_result = await self.step_async()
        self.workflow.add_step('step_a', self.step_async)
        asyncio.run(self.workflow.run())
        context = self.workflow.context
        self.assertIsNone(context.get('error'))
        self.assertEqual(context['step_a'], expected_result)

    def test_add_error_steps(self):
        expected_result = self.step()
        self.workflow.add_step('step_a', self.step_raise_err)
        self.workflow.add_error_step('step_a_err', self.step)
        asyncio.run(self.workflow.run())
        context = self.workflow.context
        self.assertIsNotNone(context.get('error'))
        self.assertEqual(context['error'], 'error_test')
        self.assertEqual(context['step_a_err'], expected_result)

    def test_context_init(self):
        db = 'test_db'
        workflow = Workflow({'db': db})
        context = workflow.context
        self.assertEqual(context['db'], 'test_db')

    def test_true_cond_step(self):
        expected_result = self.step()
        self.workflow.add_step('step_a', self.step_return_true)
        self.workflow.add_cond_step(
            'cond_step', self.step, self.step_return_false)
        asyncio.run(self.workflow.run())
        context = self.workflow.context
        self.assertIsNone(context.get('error'))
        self.assertEqual(context['cond_step'], expected_result)

    def test_false_cond_step(self):
        expected_result = self.step()
        self.workflow.add_step('step_a', self.step_return_false)
        self.workflow.add_cond_step(
            'cond_step', self.step_return_true, self.step)
        asyncio.run(self.workflow.run())
        context = self.workflow.context
        self.assertIsNone(context.get('error'))
        self.assertEqual(context['cond_step'], expected_result)

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
        context = self.workflow.context
        self.assertIsNone(context.get('error'))
        self.assertEquals(context['step_cond'], [self.step(), self.step()])

        # def test_io_simulate(self):
        #     async def main():
        #         self.workflow.add_step('async_step_a', self.async_step_a)
        #         await asyncio.gather(self.workflow.run(), self.outside_step())
        #     asyncio.run(main())
