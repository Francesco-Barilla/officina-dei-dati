import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
from engine import CodeError, LANGUAGES, TYPES, assign, execute, f32, generate, output, parse, set_var, type_name, value
from lessons import QUIZZES
from missions import BY_KEY, DIFFICULTIES, MISSIONS, validate
from main import App
import storage
from ui import SIZE, THEMES, font, palette


class SemanticsTests(unittest.TestCase):
    def test_all_64_solutions_and_each_declared_case(self):
        for mission in MISSIONS:
            for language in LANGUAGES:
                with self.subTest(mission=mission.key, language=language):
                    report = validate(mission, mission.solution(language), language)
                    self.assertTrue(report.success, report.message)
                    self.assertEqual(report.passed, len(mission.cases))

    def test_assignment_copies_and_immutable_snapshots(self):
        for language in LANGUAGES:
            mission = BY_KEY['copia']
            run = execute(mission.solution(language), mission.cases[0].inputs, language)
            self.assertIsNone(run.error)
            self.assertEqual(dict(run.frames[1].memory)['energia'].data, 10)
            self.assertEqual(dict(run.frames[3].memory)['energia'].data, 15)
            self.assertEqual(dict(run.frames[3].memory)['prima'].data, 10)
            self.assertEqual([v.data for v in run.frames[-1].outputs], [10, 15])
            self.assertFalse(run.frames[1].outputs)

    def test_c_and_java_integer_division_and_conversion_order(self):
        for language in LANGUAGES:
            for expression, expected in [('a / b', 2 if language in ('C', 'Java') else 2.5), ('float(a / b)', 2 if language in ('C', 'Java') else 2.5), ('float(a) / b', 2.5)]:
                code = generate([set_var('a', 'int', '5'), set_var('b', 'int', '2'), set_var('q', 'float', expression), output('q')], language)
                run = execute(code, (), language)
                self.assertIsNone(run.error, str(run.error))
                self.assertEqual(run.frames[-1].outputs[0].data, expected)
        for language in ('C', 'Java'):
            run = execute(generate([set_var('q', 'int', '-5 / 2'), output('q')], language), (), language)
            self.assertEqual(run.frames[-1].outputs[0].data, -2)

    def test_native_float_assignment_and_32_bit_storage(self):
        c_run = execute('int x = 2.9f; mostra(x);', (), 'C')
        self.assertEqual(c_run.frames[-1].outputs[0].data, 2)
        self.assertIsNotNone(execute('int x = 2.9f; System.out.println(x);', (), 'Java').error)
        self.assertIsNotNone(execute('float x = 0.1;', (), 'Java').error)
        java = execute('float x = 0.1f; System.out.println(x);', (), 'Java')
        self.assertEqual(java.frames[-1].outputs[0].data, f32(.1))
        self.assertEqual(java.frames[-1].outputs[0].bits, 32)
        python = execute('x = 0.1\nprint(x)', (), 'Python')
        self.assertEqual(python.frames[-1].outputs[0].bits, 64)
        self.assertEqual(type_name(value(3), 'JavaScript'), 'number')
        self.assertEqual(type_name(value(3.5), 'JavaScript'), 'number')

    def test_string_tokens_do_not_rewrite_variable_names_or_contents(self):
        for language in LANGUAGES:
            text = 'testo true false ! && ; # //'
            code = generate([set_var('testo', 'string', repr(text)), output('testo')], language)
            run = execute(code, (), language)
            self.assertIsNone(run.error)
            self.assertEqual(run.frames[-1].outputs[0].data, text)
            self.assertIn('testo', dict(run.frames[-1].memory))
        self.assertIsNotNone(execute('x = "5" + 2\nprint(x)', (), 'Python').error)
        for language in ('JavaScript', 'Java'):
            prefix = 'let' if language == 'JavaScript' else 'String'
            out = 'console.log' if language == 'JavaScript' else 'System.out.println'
            run = execute(f'{prefix} x = "5" + 2; {out}(x);', (), language)
            self.assertEqual(run.frames[-1].outputs[0].data, '52')
        run = execute('let x = 3.0; let t = String(x); console.log(t);', (), 'JavaScript')
        self.assertEqual(run.frames[-1].outputs[0].data, '3')

    def test_native_not_precedence_and_java_static_boolean_check(self):
        for language in ('C', 'JavaScript'):
            prefix, printer = ('int', 'mostra') if language == 'C' else ('let', 'console.log')
            run = execute(f'{prefix} x = 0; {printer}(!x >= 3);', (), language)
            self.assertIsNone(run.error)
            self.assertFalse(run.frames[-1].outputs[0].data)
        run = execute('x = 0\nprint(not x >= 3)', (), 'Python')
        self.assertTrue(run.frames[-1].outputs[0].data)
        for code in ('boolean b = false && 3;', 'boolean b = true || 3;', 'boolean b = true < false;', 'boolean b = false && manca;'):
            run = execute(code, (), 'Java')
            self.assertIsNotNone(run.error)
            self.assertEqual(len(run.frames), 1)
        self.assertIsNone(execute('boolean b = false && (1 / 0 > 0);', (), 'Java').error)

    def test_input_order_counts_and_types_are_checked(self):
        mission = BY_KEY['rettangolo']
        for language in LANGUAGES:
            order = list(mission.instructions)
            order[0], order[1] = order[1], order[0]
            report = validate(mission, generate(order, language), language)
            self.assertFalse(report.success)
            self.assertEqual(report.case, mission.cases[0])
        run = execute('x = leggi_intero()\n', (value('5'),), 'Python')
        self.assertIsNotNone(run.error)
        with self.assertRaises(CodeError):
            parse('x = leggi_intero() + leggi_intero()', 'Python')

    def test_wrong_program_does_not_pass_by_showing_only_expected_output(self):
        mission = BY_KEY['interi']
        self.assertFalse(validate(mission, 'print(5)', 'Python').success)
        mission = BY_KEY['prima_dopo']
        wrong = list(mission.instructions)
        wrong[1], wrong[2] = wrong[2], wrong[1]
        self.assertFalse(validate(mission, generate(wrong, 'Python'), 'Python').success)

    def test_language_and_subset_errors_are_bounded(self):
        rejected = ['import os', '__import__("os")', 'x = os.system("whoami")', 'x = [1,2]', 'x = (lambda: 1)()', 'while True:\n print(1)', 'if True:\n print(1)', 'x = 2 ** 100000', 'x = ' + '1' * 6000, 'x = None', 'if = 3']
        for code in rejected:
            try:
                result = execute(code, (), 'Python')
                self.assertIsNotNone(result.error, code)
            except CodeError:
                pass
        with self.assertRaises(CodeError):
            parse('#' * 9000, 'Python')
        with self.assertRaises(CodeError):
            parse('bool x = True;', 'C')
        for code in ('let x = 1; const x = 2;', 'const x = 1; x = 2;', 'x = 1;'):
            self.assertIsNotNone(execute(code, (), 'JavaScript').error)

    def test_quiz_behavior_in_every_language(self):
        expected = [[3], [2], [2, 3], ['5'], [False], None, None, [20.0], [9, 9], [8], ['nome'], [2.5], [2, 2.0], [True], [2, 2], 'error']
        self.assertEqual(len(QUIZZES), len(expected))
        for index, quiz in enumerate(QUIZZES):
            for language in LANGUAGES:
                run = execute(quiz.source(language), (), language)
                result = expected[index]
                if result == 'error':
                    self.assertIsNotNone(run.error)
                else:
                    self.assertIsNone(run.error, (quiz.key, language, str(run.error)))
                    if result is None:
                        result = [2.0 if language in ('C', 'Java') else 2.5]
                    self.assertEqual([item.data for item in run.frames[-1].outputs], result)


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1440, 900))

    @classmethod
    def tearDownClass(cls):
        font.cache_clear()
        pygame.quit()

    def setUp(self):
        self.app = App(self.screen, saving=False, state_path=Path(tempfile.gettempdir()) / 'nonexistent-officina-tests.json')

    def test_all_guided_lessons_can_be_completed_without_game_rewards(self):
        app = self.app
        for language in LANGUAGES:
            app.set_language(language)
            for mission in MISSIONS:
                app.open_mission(mission.key)
                steps = len(app.frames) - 1
                for index in range(steps):
                    expected = app.frames[app.frame_index + 1].after
                    correct = next(i for i, item in enumerate(app.prediction_options) if app.equivalent(item, expected))
                    app.choose_prediction((correct + 1) % len(app.prediction_options))
                    self.assertFalse(app.prediction_answered)
                    app.choose_prediction(correct)
                    self.assertTrue(app.prediction_answered)
                    self.assertEqual(app.frame_index, index + 1)
                    app.update(3)
                    self.assertFalse(app.playing)
                    if index + 1 < steps:
                        app.action('next_prediction')
                self.assertFalse(app.state['completed'])

    def test_swapping_cards_changes_the_program_and_invalidates_trace(self):
        app = self.app
        app.mode = 'game'
        app.open_mission('copia')
        app.order = list(range(len(app.mission.instructions)))
        app.start_trace(False)
        app.action('card:0')
        app.action('card:2')
        self.assertEqual(app.order[:3], [2, 1, 0])
        self.assertFalse(app.frames)
        app.verify()
        self.assertFalse(app.review.success)
        self.assertFalse(app.state['completed'])
        app.order = list(range(len(app.mission.instructions)))
        app.verify()
        self.assertIn(app.key(), app.state['completed'])

    def test_drafts_survive_language_difficulty_settings_and_learning(self):
        app = self.app
        app.mode = 'game'
        app.set_difficulty('Difficile')
        app.open_mission('scambio')
        app.editor.set('# mia bozza Python')
        app.set_language('Java')
        app.editor.set('// mia bozza Java')
        app.set_difficulty('Medio')
        self.assertIn('???', app.editor.value)
        app.set_difficulty('Difficile')
        self.assertEqual(app.editor.value, '// mia bozza Java')
        app.action('settings')
        app.set_language('Python')
        app.action('return')
        self.assertEqual(app.editor.value, '# mia bozza Python')
        app.action('learn')
        app.action('try')
        self.assertEqual(app.editor.value, '# mia bozza Python')
        app.action('solution')
        self.assertFalse(app.state['completed'])

    def test_pausing_and_resuming_preserves_prediction_and_memory(self):
        app = self.app
        app.open_mission('copia')
        app.choose_prediction(next(i for i, item in enumerate(app.prediction_options) if app.equivalent(item, app.frames[1].after)))
        app.update(.2)
        progress, frame = app.progress, app.frame
        for opening, closing in [('idea', 'close'), ('bank', 'bank_back'), ('settings', 'return')]:
            app.action(opening)
            app.update(5)
            app.action(closing)
            self.assertEqual(app.progress, progress)
            self.assertEqual(app.frame, frame)
        app.draw()
        self.assertTrue(any(key == 'resume' and active for key, _, active in app.buttons))
        app.action('resume')
        app.update(3)
        app.action('next_prediction')
        self.assertFalse(app.prediction_answered)

    def test_bank_distinguishes_typed_false_and_string_false(self):
        app = self.app
        app.action('bank')
        app.action('kind:bool')
        self.assertIs(app.bank_value().data, False)
        app.action('kind:string')
        app.bank_fields['string'].set('false')
        self.assertEqual(app.bank_value().data, 'false')
        app.action('bank_lang:JavaScript')
        self.assertEqual(app.language, 'Python')
        app.draw()
        app.bank_fields['string'].focus = True
        app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=pygame.KMOD_CTRL))
        app.event(pygame.event.Event(pygame.TEXTINPUT, text='0'))
        self.assertEqual(app.bank_value().data, '0')
        app.action('kind:float')
        app.bank_fields['float'].set('2,5')
        with self.assertRaises(CodeError):
            app.bank_value()

    def test_editor_undo_invalidates_old_result(self):
        app = self.app
        app.mode = 'game'
        app.set_difficulty('Difficile')
        app.open_mission('ordine')
        app.editor.set('print("Accendi")')
        app.editor.focus = True
        app.start_trace(False)
        app.event(pygame.event.Event(pygame.TEXTINPUT, text='\n'))
        self.assertFalse(app.frames)
        app.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z, mod=pygame.KMOD_CTRL))
        self.assertEqual(app.editor.value, 'print("Accendi")')

    def test_quiz_trace_and_rewards_require_an_answer(self):
        app = self.app
        app.open_quiz(8)
        app.draw()
        self.assertFalse(next(active for key, _, active in app.buttons if key == 'run'))
        app.quiz_choice = 0
        app.check_quiz()
        self.assertFalse(app.state['quizzes'])
        app.quiz_choice = app.quiz.correct(app.language)
        app.check_quiz()
        self.assertIn('scambio:Python', app.state['quizzes'])

    def test_all_pages_fit_and_all_cards_are_accessible(self):
        app = self.app
        for theme in THEMES:
            app.c = palette(theme)
            for mode in ('learn', 'game', 'quiz'):
                app.action('mode:' + mode)
                seen = set()
                for page in range(2):
                    app.catalog_page = page
                    app.draw()
                    seen.update(key for key, _, _ in app.buttons if key.startswith(('mission:', 'quiz:')))
                self.assertEqual(len(seen), 16)
            app.page, app.mode = 'home', 'game'
            for difficulty in DIFFICULTIES:
                app.set_difficulty(difficulty)
                for mission in MISSIONS:
                    app.open_mission(mission.key)
                    app.draw()
                    self.assertTrue(all(pygame.Rect(0, 0, *SIZE).contains(rect) for _, rect, _ in app.buttons))
            app.set_difficulty('Facile')
            app.open_mission('sonda')
            app.block_scroll = 10000
            app.draw()
            self.assertTrue(any(key == 'card:9' for key, _, _ in app.buttons))
            app.action('bank')
            for kind in TYPES:
                app.bank_kind = kind
                for language in LANGUAGES:
                    app.bank_language = language
                    app.draw()
            app.action('types')
            app.draw()
            self.assertGreater(app.modal_max, 0)
            app.action('close')


class PersistenceTests(unittest.TestCase):
    def test_roundtrip_and_malformed_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            state = storage.defaults()
            state['drafts']['copia:Difficile:Python'] = 'x = ???'
            state['orders']['ordine'] = [2, 0, 1]
            self.assertEqual(storage.save(state, path), '')
            self.assertEqual(storage.load(path), (state, ''))
            path.write_text(json.dumps({'orders': {'ordine': [1, True, 2]}, 'size': True}), encoding='utf-8')
            loaded, _ = storage.load(path)
            self.assertEqual(loaded['size'], 19)
            self.assertFalse(loaded['orders'])
            path.write_text('{invalid', encoding='utf-8')
            self.assertTrue(storage.load(path)[1])


if __name__ == '__main__':
    unittest.main()
