import unittest

from workflow import Workflow

class TestWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = Workflow({})

    def step_a(self):
        return 'step_a_results'

    def step_b(self, step_a):
        return f'step_b_results-{step_a}'

    def step_raise_err(self):
        raise ValueError('sample_error')

    def step_error(self):
        return "step_error_results"

    def step_with_context(self, context):
        return context['step_a']


    def test_add_normal_steps(self):
        self.workflow.add_step('step_a', self.step_a)
        self.workflow.add_step('step_b', self.step_b, ['step_a'])
        self.workflow.run()
        context = self.workflow.context
        self.assertIsNone(context.get('error'))
        self.assertEqual(context['step_a'], 'step_a_results')
        self.assertEqual(context['step_b'], 'step_b_results-step_a_results')

    def test_add_error_steps(self):
        self.workflow.add_step('step_raise_err', self.step_raise_err)
        self.workflow.add_error_step('step_error', self.step_error)
        self.workflow.run()
        context = self.workflow.context
        self.assertIsNotNone(context.get('error'))
        self.assertEqual(context['error'], 'sample_error')
        self.assertEqual(context['step_error'], 'step_error_results')

    def test_pass_context(self):
        self.workflow.add_step('step_a', self.step_a)
        self.workflow.add_step('step_with_context', self.step_with_context)
        self.workflow.run()
        context = self.workflow.context
        self.assertIsNotNone(context.get('step_with_context'))
        self.assertEqual(context['step_with_context'], 'step_a_results')
