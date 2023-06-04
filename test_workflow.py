import unittest
import asyncio

from workflow import Workflow

class TestWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = Workflow({})

    async def step_a(self):
        print("hello step a")
        return 'step_a_results'

    def step_b(self, step_a):
        return f'step_b_results-{step_a}'

    def step_raise_err(self):
        raise ValueError('sample_error')

    def step_error(self):
        return "step_error_results"

    def step_with_context(self, context):
        return context['step_a']

    # async def async_step_a(self):
    #     print("async step a begin")
    #     await asyncio.sleep(5)
    #     print("async step a end")

    # async def outside_step(self):
    #     print("outside step begin")
    #     await asyncio.sleep(5)
    #     print("outside step end")


    def test_add_normal_steps(self):
        self.workflow.add_step('step_a', self.step_a)
        self.workflow.add_step('step_b', self.step_b, ['step_a'])
        asyncio.run(self.workflow.run())
        context = self.workflow.context
        self.assertIsNone(context.get('error'))
        self.assertEqual(context['step_a'], 'step_a_results')
        self.assertEqual(context['step_b'], 'step_b_results-step_a_results')

    def test_add_error_steps(self):
        self.workflow.add_step('step_raise_err', self.step_raise_err)
        self.workflow.add_error_step('step_error', self.step_error)
        asyncio.run(self.workflow.run())
        context = self.workflow.context
        self.assertIsNotNone(context.get('error'))
        self.assertEqual(context['error'], 'sample_error')
        self.assertEqual(context['step_error'], 'step_error_results')

    def test_pass_context(self):
        self.workflow.add_step('step_a', self.step_a)
        self.workflow.add_step('step_with_context', self.step_with_context)
        asyncio.run(self.workflow.run())
        context = self.workflow.context
        self.assertIsNotNone(context.get('step_with_context'))
        self.assertEqual(context['step_with_context'], 'step_a_results')

    def test_context_init(self):
        db = 'test_db'
        workflow = Workflow({'db': db})
        context = workflow.context
        self.assertEqual(context['db'], 'test_db')

    # def test_io_simulate(self):
    #     async def main():
    #         self.workflow.add_step('async_step_a', self.async_step_a)
    #         await asyncio.gather(self.workflow.run(), self.outside_step())
    #     asyncio.run(main())
