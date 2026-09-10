"""Regression paths for feedback that a learner can act on."""
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import tempfile
import unittest
from pathlib import Path
import pygame
from main import App
from missions import BY_KEY, validate


class ExperienceTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = App(pygame.display.set_mode((1280, 800)), Path(self.directory.name) / 'state.json', saving=False)

    def test_wrong_prediction_has_explicit_feedback_and_keeps_memory(self):
        app = self.app
        app.open_mission('interi', 1)
        before = app.frame
        app.choose_prediction(next(i for i, item in enumerate(app.prediction_options) if item.data != 3))
        self.assertEqual(app.frame, before)
        self.assertFalse(app.prediction_answered)
        self.assertEqual(getattr(app, 'feedback_kind', None), 'wrong')
        app.choose_prediction(next(i for i, item in enumerate(app.prediction_options) if item.data == 3))
        app.update(3)
        self.assertEqual(getattr(app, 'feedback_kind', None), 'correct')
        self.assertEqual(dict(app.frame.memory)['casse'].data, 3)
        app.action('next_prediction')
        self.assertEqual(app.feedback_kind, 'neutral')
        self.assertEqual(dict(app.frame.memory)['casse'].data, 3)

    def test_successful_check_shows_result_instead_of_an_empty_simulation(self):
        app = self.app
        app.mode = 'game'
        app.open_mission('interi', 1)
        app.order = [0, 1, 2]
        app.verify()
        self.assertTrue(app.review.success)
        self.assertEqual([item.data for item in app.frame.outputs], [5])
        self.assertEqual(dict(app.frame.memory)['casse'].data, 5)
        self.assertEqual(getattr(app, 'feedback_kind', None), 'correct')

    def test_check_explains_the_concrete_output_difference(self):
        mission = BY_KEY['ordine']
        result = validate(mission, 'print("Decolla")\nprint("Chiudi portello")\nprint("Accendi")', 'Python')
        self.assertFalse(result.success)
        rows = getattr(result, 'rows', ())
        self.assertTrue(rows, 'The failure needs an expected/actual comparison')
        first = next(row for row in rows if not row.ok)
        self.assertIn('Accendi', first.expected)
        self.assertIn('Decolla', first.actual)

    def test_adjacent_arrow_moves_the_requested_card_and_clears_old_success(self):
        app = self.app
        app.mode = 'game'
        app.open_mission('ordine')
        app.order = [0, 1, 2]
        app.verify()
        app.action('shift:1:-1')
        self.assertEqual(app.order, [1, 0, 2])
        self.assertIsNone(app.review)
        self.assertFalse(app.frames)
        app.action('shift:0:-1')
        self.assertEqual(app.order, [1, 0, 2])

    def test_next_mission_does_not_wrap_to_first_after_last(self):
        app = self.app
        app.mode = 'game'
        app.open_mission('ordine')
        app.action('next_mission')
        self.assertEqual(app.mission.key, 'interi')
        app.open_mission('sonda')
        app.action('next_mission')
        self.assertEqual(app.page, 'catalog')

    def click(self, key):
        app = self.app
        app.draw()
        rect = next(rect for name, rect, active in app.buttons if name == key and active)
        w, h = app.screen.get_size()
        scale = min(w / 1440, h / 900)
        pos = (round((w - 1440 * scale) / 2 + rect.centerx * scale), round((h - 900 * scale) / 2 + rect.centery * scale))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            app.event(pygame.event.Event(kind, button=1, pos=pos))

    def test_real_clicks_repair_a_sequence_at_supported_window_sizes(self):
        app = self.app
        for size in ((960, 600), (1280, 800), (1440, 900), (1600, 900)):
            app.screen = pygame.display.set_mode(size)
            app.mode = 'game'
            app.open_mission('ordine')
            app.order = [1, 0, 2]
            self.click('verify')
            self.assertFalse(app.review.success)
            self.click('shift:1:-1')
            self.assertEqual(app.order, [0, 1, 2])
            self.click('verify')
            self.assertTrue(app.review.success)
            self.click('trace_view')
            self.assertEqual(app.frame_index, 0)
            self.click('step')
            self.assertEqual([v.data for v in app.frame.outputs], ['Accendi'])
            self.click('close')
            self.click('next_mission')
            self.assertEqual(app.mission.key, 'interi')

    def test_invalid_editor_code_can_be_checked_and_repaired(self):
        app = self.app
        app.mode = 'game'
        app.set_difficulty('Medio')
        app.open_mission('interi')
        self.click('verify')
        self.assertFalse(app.review.success)
        self.assertGreater(app.error_line, 0)
        app.editor.set('casse = leggi_intero()\ncasse = casse + 2\nprint(casse)')
        app.invalidate()
        self.click('verify')
        self.assertTrue(app.review.success)
        self.assertEqual(app.error_line, 0)

    def test_new_quiz_choice_clears_previous_feedback_until_checked(self):
        app = self.app
        app.open_quiz(8)
        self.click('answer:0')
        self.click('check')
        self.assertTrue(app.quiz_attempted)
        self.click('answer:1')
        self.assertFalse(app.quiz_attempted)
        self.assertFalse(app.frames)

    def test_trace_can_show_valid_steps_before_a_runtime_error(self):
        app = self.app
        app.mode = 'game'
        app.set_difficulty('Difficile')
        app.open_mission('interi', 1)
        app.editor.set('casse = leggi_intero()\ncasse = casse / 0\nprint(casse)')
        self.click('trace_view')
        self.click('step')
        self.assertEqual(dict(app.frame.memory)['casse'].data, 3)
        app.draw()
        self.assertFalse(next(active for key, _, active in app.buttons if key == 'step'))

    def test_trace_follows_long_program_and_keeps_manual_scroll(self):
        app = self.app
        app.mode = 'game'
        app.set_difficulty('Difficile')
        app.open_mission('sonda')
        app.editor.set(app.mission.solution('Python'))
        self.click('trace_view')
        for _ in range(9):
            self.click('step')
        trace = getattr(app, 'trace_editor', app.editor)
        app.draw()
        self.assertGreater(trace.scroll, 0)
        self.assertLessEqual(trace.scroll, 8)
        self.assertGreaterEqual(trace.scroll + (trace.rect.height - 16) // (trace.size + 8), 9)
        app.event(pygame.event.Event(pygame.MOUSEWHEEL, y=1, x=0))
        scroll = trace.scroll
        app.draw()
        self.assertEqual(trace.scroll, scroll)


if __name__ == '__main__':
    unittest.main()
