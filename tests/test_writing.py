"""Real typing paths: select the gap, write in it, submit, and preserve drafts."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import tempfile
from pathlib import Path
import unittest
import pygame
from main import App
from engine import LANGUAGES, execute, type_name
from missions import MISSIONS
from writing_guide import example_for


class WritingTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = App(pygame.display.set_mode((1280, 800)), Path(self.temp.name) / 'progress.json', saving=False)
        self.app.mode = 'game'

    def click(self, key):
        app = self.app
        app.draw()
        options = [rect for name, rect, active in app.buttons if name == key and active]
        self.assertTrue(options, f'Manca il comando accessibile {key}')
        x, y = options[0].center
        pos = (round(x * 1280 / 1440), round(y * 800 / 900))
        for event in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            app.event(pygame.event.Event(event, pos=pos, button=1))

    def test_gap_button_selects_only_the_expression_and_typed_program_passes(self):
        app = self.app
        app.set_difficulty('Medio')
        for language in LANGUAGES:
            app.set_language(language)
            app.open_mission('interi')
            before = app.editor.value
            self.click('focus_code')
            a, b = sorted((app.editor.caret, app.editor.anchor))
            self.assertEqual(before[a:b], '???')
            app.event(pygame.event.Event(pygame.TEXTINPUT, text='casse + 2'))
            self.assertEqual(app.editor.value, before[:a] + 'casse + 2' + before[b:])
            self.click('verify')
            self.assertTrue(app.review.success, (language, app.review.message))

    def test_whole_line_gap_accepts_a_complete_print_statement(self):
        app = self.app
        app.set_difficulty('Medio')
        app.open_mission('ordine')
        self.click('focus_code')
        app.event(pygame.event.Event(pygame.TEXTINPUT, text='print("Decolla")'))
        self.click('verify')
        self.assertTrue(app.review.success)

    def test_hard_focus_places_typing_after_legacy_comments_and_keeps_draft(self):
        app = self.app
        app.set_difficulty('Difficile')
        app.open_mission('ordine')
        draft = '# La mia bozza\n'
        app.editor.set(draft)
        self.click('focus_code')
        app.event(pygame.event.Event(pygame.TEXTINPUT, text='print("Accendi")\nprint("Chiudi portello")\nprint("Decolla")'))
        self.assertTrue(app.editor.value.startswith(draft))
        self.click('verify')
        self.assertTrue(app.review.success)

    def test_focus_on_a_filled_draft_does_not_replace_the_program(self):
        app = self.app
        app.set_difficulty('Difficile')
        app.open_mission('interi')
        draft = 'casse = leggi_intero()\n'
        app.editor.set(draft)
        self.click('focus_code')
        self.assertEqual(app.editor.value, draft)
        self.assertEqual(app.editor.caret, app.editor.anchor)
        self.assertTrue(app.editor.focus)
        app.action('commands')
        self.assertEqual(app.editor.value, draft)
        app.action('close')
        self.click('focus_code')
        app.event(pygame.event.Event(pygame.TEXTINPUT, text='casse = casse + 2\nprint(casse)'))
        self.click('verify')
        self.assertTrue(app.review.success)

    def test_focus_preserves_a_nonempty_last_line(self):
        app = self.app
        app.set_difficulty('Difficile')
        app.open_mission('ordine')
        app.editor.set('print("Accendi")')
        self.click('focus_code')
        self.assertEqual(app.editor.value, 'print("Accendi")')

    def test_control_enter_checks_code_without_inserting_a_new_line(self):
        app = self.app
        app.set_difficulty('Medio')
        app.open_mission('interi')
        self.click('focus_code')
        app.event(pygame.event.Event(pygame.TEXTINPUT, text='casse + 2'))
        code = app.editor.value
        app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=pygame.KMOD_CTRL))
        self.assertEqual(app.editor.value, code)
        self.assertIsNotNone(app.review)
        self.assertTrue(app.review.success)

    def test_comment_without_newline_does_not_swallow_the_first_instruction(self):
        app = self.app
        app.set_difficulty('Difficile')
        app.open_mission('ordine')
        app.editor.set('# appunti')
        self.click('focus_code')
        app.event(pygame.event.Event(pygame.TEXTINPUT, text='print("Accendi")\nprint("Chiudi portello")\nprint("Decolla")'))
        self.assertTrue(app.editor.value.startswith('# appunti\nprint'))
        self.click('verify')
        self.assertTrue(app.review.success)

    def test_focus_skips_question_marks_in_comments_and_strings(self):
        app = self.app
        app.set_difficulty('Medio')
        for language in LANGUAGES:
            app.set_language(language)
            app.open_mission('interi')
            comment = '# dubbio ???\n' if language == 'Python' else '// dubbio ???\n'
            app.editor.set(comment + app.mission.starter(language, 'Medio'))
            self.click('focus_code')
            self.assertGreaterEqual(min(app.editor.caret, app.editor.anchor), len(comment))
            app.event(pygame.event.Event(pygame.TEXTINPUT, text='casse + 2'))
            self.click('verify')
            self.assertTrue(app.review.success, (language, app.review.message))
        result = execute('testo = "???"\nprint(testo)', (), 'Python')
        self.assertIsNone(result.error)
        self.assertEqual(result.frames[-1].outputs[-1].data, '???')

    def test_conversion_examples_demonstrate_numeric_conversion_and_decimal_division(self):
        for key, expected, kind in [('converti', 12, 'int'), ('divisione', 3.5, 'float')]:
            mission = next(item for item in MISSIONS if item.key == key)
            for language in LANGUAGES:
                _, sample = example_for(mission, language, '', 'Difficile')
                execution = execute('\n'.join(sample), (), language)
                self.assertIsNone(execution.error, (key, language))
                result = execution.frames[-1].outputs[-1]
                self.assertEqual(result.data, expected, (key, language))
                self.assertEqual(type_name(result, language), 'number' if language == 'JavaScript' else kind)

    def test_empty_code_and_a_bare_result_require_instructions_then_can_be_corrected(self):
        app = self.app
        app.set_difficulty('Difficile')
        app.open_mission('interi')
        for draft in ('', '2', '-3', '"2"'):
            app.editor.set(draft)
            self.click('verify')
            self.assertFalse(app.review.success)
            self.assertIn('istruzioni', app.review.message)
        app.editor.set(app.mission.solution('Python'))
        self.click('verify')
        self.assertTrue(app.review.success)


if __name__ == '__main__':
    unittest.main()
