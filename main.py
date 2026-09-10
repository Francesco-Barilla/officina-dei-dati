"""Officina dei dati: learn, arrange, execute and inspect a sequence."""
import json
import os
from pathlib import Path
import random
import sys

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
if '--smoke-test' in sys.argv:
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame

from engine import CodeError, Frame, LANGUAGES, TYPES, display, execute, generate, literal, source_line, type_name, value
from lessons import HOW_TO_PLAY, MISCONCEPTIONS, QUIZZES, TYPES_NOTES, commands_text
from missions import BY_KEY, DIFFICULTIES, GROUPS, MISSIONS, compare_case, validate
from experience import LabExperience
from scene import TYPE_COLORS, background, conveyor, icon
import storage
from ui import SIZE, THEMES, Editor, font, lines, mix, palette, panel, text, wrap

TITLE = 'Officina dei dati'


class App(LabExperience):
    def __init__(self, screen, state_path=None, saving=True):
        self.screen, self.canvas = screen, pygame.Surface(SIZE)
        self.state_path, self.saving = state_path, saving
        self.state, self.notice = storage.load(state_path)
        self.c = palette(self.state['theme'])
        self.mission = BY_KEY[self.state['mission']]
        self.page, self.return_page, self.mode = 'home', 'home', 'learn'
        self.filter, self.catalog_page, self.case_index = 'Tutte', 0, 0
        self.editor, self.modal_editor = Editor(), Editor()
        self.trace_editor = Editor()
        self.code_rect = pygame.Rect(742, 282, 658, 331)
        self.frames, self.frame_index = [], 0
        self.progress, self.playing, self.auto, self.time = 1, False, False, 0
        self.feedback, self.review, self.error_line = '', None, 0
        self.feedback_kind, self.result_scroll = 'neutral', 0
        self.order, self.selected, self.block_scroll, self.memory_page = [], None, 0, 0
        self.prediction_options, self.prediction_answered, self.prediction_choice = [], False, None
        self.quiz_index, self.quiz_choice, self.quiz_attempted = 0, None, False
        self.buttons, self.pointer, self.pressed, self.focus = [], (-1, -1), None, None
        self.modal, self.modal_title, self.modal_text = None, '', ''
        self.modal_scroll, self.modal_max = 0, 0
        self.bank_kind, self.bank_return, self.bank_language = 'int', 'home', self.language
        self.bank_origin_language = self.language
        self.bank_fields = {kind: Editor(initial) for kind, initial in [('int', '5'), ('float', '2.5'), ('string', '5'), ('bool', 'false')]}
        self.bank_code = Editor()
        self.fullscreen, self.window_size, self.alive = False, screen.get_size(), True

    @property
    def language(self):
        return self.state['language']

    @property
    def difficulty(self):
        return self.state['difficulty']

    @property
    def easy(self):
        return self.mode == 'game' and self.difficulty == 'Facile'

    @property
    def case(self):
        return self.mission.cases[self.case_index]

    @property
    def quiz(self):
        return QUIZZES[self.quiz_index]

    @property
    def frame(self):
        return self.frames[self.frame_index] if self.frames else Frame(0, 'Osserva il nastro', 'Esegui una riga per vedere cosa cambia.', (), (), 0)

    def key(self):
        return f'{self.mission.key}:{self.difficulty}:{self.language}'

    def persist(self):
        if self.page == 'lab' and self.mode == 'game':
            if self.easy:
                self.state['orders'][self.mission.key] = self.order.copy()
            else:
                self.state['drafts'][self.key()] = self.editor.value
        if self.saving:
            self.notice = storage.save(self.state, self.state_path)

    def invalidate(self):
        self.frames, self.frame_index, self.playing, self.progress = [], 0, False, 1
        self.feedback, self.review, self.error_line = '', None, 0
        self.feedback_kind, self.result_scroll = 'neutral', 0
        self.memory_page = 0

    def shuffled_order(self):
        result = list(range(len(self.mission.instructions)))
        random.shuffle(result)
        if result == list(range(len(result))):
            result[0], result[-1] = result[-1], result[0]
        return result

    def open_mission(self, key, case_index=0):
        self.persist()
        self.mission = BY_KEY[key]
        self.state['mission'] = key
        self.page, self.case_index = 'lab', case_index % len(self.mission.cases)
        self.selected, self.block_scroll = None, 0
        self.invalidate()
        if self.mode == 'learn':
            self.editor.set(self.mission.solution(self.language))
            self.prepare_learn()
        elif self.easy:
            self.order = list(self.state['orders'].get(key, self.shuffled_order()))
            self.editor.set(self.code())
        else:
            self.editor.set(self.state['drafts'].get(self.key(), self.mission.starter(self.language, self.difficulty)))
        self.editor.focus = False

    def code(self):
        if self.page == 'quiz':
            return self.quiz.source(self.language)
        if self.easy:
            return generate([self.mission.instructions[index] for index in self.order], self.language)
        return self.editor.value

    def set_language(self, language):
        if language == self.language:
            return
        self.persist()
        page = self.page
        destination = self.return_page if page == 'settings' else page
        # Save before changing the key; loading must not persist the old editor
        # into the new language's draft.
        self.page = 'transition'
        self.state['language'] = language
        if destination == 'lab':
            self.open_mission(self.mission.key, self.case_index)
        elif destination == 'quiz':
            self.open_quiz(self.quiz_index)
        self.page = page
        self.persist()

    def set_difficulty(self, difficulty):
        if difficulty != self.difficulty:
            self.persist()
            page = self.page
            self.page = 'transition'
            self.state['difficulty'] = difficulty
            if page == 'lab':
                self.open_mission(self.mission.key, self.case_index)
            self.page = page
            self.persist()

    def equivalent(self, left, right):
        if self.language == 'JavaScript' and {left.kind, right.kind} <= {'int', 'float'}:
            return left.data == right.data
        return left.kind == right.kind and left.data == right.data

    def prepare_learn(self):
        execution = execute(self.mission.solution(self.language), self.case.inputs, self.language)
        if execution.error:
            raise execution.error
        self.frames, self.frame_index, self.progress, self.playing = execution.frames, 0, 1, False
        self.prepare_prediction()

    def prepare_prediction(self):
        self.prediction_answered, self.prediction_choice = False, None
        self.feedback_kind = 'neutral'
        self.feedback = 'Scegli una risposta: il programma aspetta te.'
        self.prediction_options = []
        if self.frame_index + 1 >= len(self.frames):
            return
        target = self.frames[self.frame_index + 1]
        correct = target.after
        extras = [correct]
        if target.before is not None:
            extras.append(target.before)
        if correct.kind == 'int':
            extras += [value(correct.data + 1), value(correct.data - 1), value(str(correct.data))]
        elif correct.kind == 'float':
            extras += [value(int(correct.data)), value(correct.data + .5), value(str(correct.data)), value(correct.data - .5)]
        elif correct.kind == 'bool':
            extras += [value(not correct.data), value(display(correct, self.language))]
        else:
            extras += [value(''), value('nome'), value(correct.data + '!'), value(0)]
        for item in extras:
            if not any(self.equivalent(item, previous) for previous in self.prediction_options):
                self.prediction_options.append(item)
            if len(self.prediction_options) == 3:
                break
        random.shuffle(self.prediction_options)

    def choose_prediction(self, index):
        if self.prediction_answered or not 0 <= index < len(self.prediction_options):
            return
        self.prediction_choice = index
        expected = self.frames[self.frame_index + 1]
        if not self.equivalent(self.prediction_options[index], expected.after):
            self.feedback_kind = 'wrong'
            chosen = self.prediction_options[index]
            if type_name(chosen, self.language) != type_name(expected.after, self.language):
                self.feedback = f'Il tipo non coincide: hai scelto {type_name(chosen, self.language)}. Qui serve {type_name(expected.after, self.language)}. Controlla anche le virgolette.'
            else:
                self.feedback = f'Hai scelto {display(chosen, self.language)}. ' + self.prediction_hint(expected)
            return
        self.prediction_answered = True
        self.frame_index += 1
        self.progress, self.playing, self.auto = 0, True, False
        self.feedback_kind = 'correct'
        self.feedback = expected.message
        self.reveal_frame()

    def reveal_frame(self):
        if self.frame.line:
            editor = self.trace_editor if self.modal == 'trace' else self.editor
            rect = editor.rect if self.modal == 'trace' else self.code_rect
            visible = max(1, (rect.height - 16) // (editor.size + 8))
            if self.frame.line - 1 < editor.scroll or self.frame.line - 1 >= editor.scroll + visible:
                editor.scroll = max(0, self.frame.line - visible)
        if self.frame.target:
            self.memory_page = list(dict(self.frame.memory)).index(self.frame.target) // 4

    def start_trace(self, auto=True):
        self.playing = False
        try:
            execution = execute(self.code(), () if self.page == 'quiz' else self.case.inputs, self.language)
            self.frames, self.frame_index = execution.frames, 0
            self.progress, self.auto = 1, auto
            self.error_line = execution.error.line if execution.error else 0
            self.feedback = f'Riga {execution.error.line}: {execution.error}' if execution.error else ''
            if len(self.frames) > 1:
                self.frame_index, self.progress, self.playing = 1, 0, auto
                self.reveal_frame()
        except CodeError as error:
            self.frames, self.error_line = [], error.line
            self.feedback = f'Riga {error.line}: {error}'

    def verify(self):
        self.persist()
        self.playing = False
        self.review = validate(self.mission, self.code(), self.language)
        self.result_scroll = 0
        if self.review.case:
            self.case_index = self.mission.cases.index(self.review.case)
        execution, rows = compare_case(self.mission, self.code(), self.language, self.case)
        self.review.rows = rows
        self.frames, self.frame_index = execution.frames, len(execution.frames) - 1
        self.progress, self.auto = 1, False
        self.error_line = execution.error.line if execution.error else 0
        self.feedback_kind = 'correct' if self.review.success else 'wrong'
        self.feedback = self.review.message
        self.reveal_frame()
        if self.review.success:
            if self.key() not in self.state['completed']:
                self.state['completed'].append(self.key())
            self.persist()

    def move_card(self, index):
        if self.selected is None or not 0 <= index < len(self.order):
            return
        self.order[self.selected], self.order[index] = self.order[index], self.order[self.selected]
        self.selected = index
        self.invalidate()
        self.editor.set(self.code())
        self.block_scroll = max(0, (index - 4) * 74)
        self.persist()

    def open_quiz(self, index):
        self.persist()
        self.quiz_index, self.page = index % len(QUIZZES), 'quiz'
        self.quiz_choice, self.quiz_attempted = None, False
        self.invalidate()
        self.editor.set(self.quiz.source(self.language))

    def check_quiz(self):
        if self.quiz_choice is None:
            return
        self.quiz_attempted = True
        right = self.quiz_choice == self.quiz.correct(self.language)
        if right:
            key = self.quiz.key + ':' + self.language
            if key not in self.state['quizzes']:
                self.state['quizzes'].append(key)
            self.persist()
        self.start_trace()
        self.feedback = ('Previsione corretta. ' if right else 'Osserva il controesempio. ') + self.quiz.explanation

    def open_text(self, title, content, code=False):
        self.playing = False
        self.editor.focus = False
        self.modal, self.modal_title, self.modal_text = 'code' if code else 'text', title, content
        self.modal_scroll, self.modal_max = 0, 0
        if code:
            self.modal_editor.set(content)

    def button(self, key, label, rect, active=True, selected=False, primary=False, size=18):
        rect = pygame.Rect(rect)
        hover = active and rect.collidepoint(self.pointer)
        color = self.c['mint'] if primary else self.c['accent'] if selected else self.c['border']
        panel(self.canvas, rect, mix(self.c['card'], color, .14 if hover or selected or primary else 0), self.c['mint'] if hover else color, 10)
        color = self.c['text'] if active else mix(self.c['card'], self.c['muted'], .6)
        if font(size).size(label)[0] < rect.width - 18:
            text(self.canvas, label, rect.center, size, color, selected or primary, 'center')
        else:
            wrap(self.canvas, label, rect.inflate(-18, -9), size, color, selected or primary)
        self.buttons.append((key, rect, active))

    def header(self, subtitle='Un’istruzione alla volta. Un valore che cambia.'):
        self.canvas.blit(pygame.transform.smoothscale(icon(), (42, 42)), (36, 28))
        text(self.canvas, 'OFFICINA DEI DATI', (92, 29), 25, self.c['text'], True)
        text(self.canvas, subtitle, (93, 61), 15, self.c['muted'])
        if self.page != 'bank':
            self.button('bank', 'Banco dei tipi', (795, 30, 171, 46), size=17)
        self.button('catalog' if self.page != 'home' else 'help', 'Sfide' if self.page != 'home' else 'Guida', (978, 30, 112, 46))
        self.button('settings', 'Impostazioni', (1100, 30, 171, 46))
        self.button('home', 'Home', (1281, 30, 119, 46))

    def selectors(self, quiz=False):
        for i, language in enumerate(LANGUAGES):
            self.button('lang:' + language, language, (742 + i * 166, 141, 158, 40), selected=self.language == language, size=17)
        if not quiz:
            for i, difficulty in enumerate(DIFFICULTIES):
                self.button('diff:' + difficulty, difficulty, (742 + i * 222, 192, 214, 39), active=self.mode == 'game', selected=self.difficulty == difficulty, size=17)

    def draw_home(self):
        self.header()
        text(self.canvas, 'Ogni istruzione lascia una traccia.', (54, 128), 43, self.c['text'], True)
        wrap(self.canvas, 'Monta il programma della sonda: leggi un dato, trasformalo, osserva il risultato.\nScopri come ordine e tipi cambiano quello che succede.', pygame.Rect(56, 193, 1230, 85), 23, self.c['muted'])
        cards = [('learn', '01  IMPARA FACENDO', 'Prevedi la prossima mossa.', 'Leggi una riga, scegli valore e tipo, osserva cosa cambia in memoria.', 'mint'),
                 ('game', '02  GIOCA', 'Monta il nastro dei dati.', '16 missioni e 3 difficoltà. Riordina le tessere, completa o scrivi il programma.', 'blue'),
                 ('quiz', '03  SCOVA L’EQUIVOCO', 'Metti alla prova un’idea.', 'Copie, scambi, divisioni e tipi: 16 sfide per capire gli errori più comuni.', 'accent')]
        for i, (mode, title, headline, description, color) in enumerate(cards):
            rect = pygame.Rect(54 + i * 450, 299, 431, 218)
            panel(self.canvas, rect, self.c['panel'], self.c[color] if rect.collidepoint(self.pointer) else self.c['border'], 19)
            text(self.canvas, title, (rect.x + 22, rect.y + 25), 19, self.c[color], True)
            wrap(self.canvas, headline, pygame.Rect(rect.x + 22, rect.y + 73, 387, 59), 24, self.c['text'], True)
            wrap(self.canvas, description, pygame.Rect(rect.x + 22, rect.y + 137, 387, 68), 18, self.c['muted'])
            self.buttons.append(('mode:' + mode, rect, True))
        conveyor(self.canvas, pygame.Rect(55, 580, 840, 231), self.c, self.time)
        text(self.canvas, 'QUATTRO TIPI, TANTE TRASFORMAZIONI', (934, 573), 15, self.c['accent'], True)
        for i, (kind, example) in enumerate([('int', '5'), ('float', '2.5'), ('string', '"Ada"'), ('bool', 'true / false')]):
            color = self.c[TYPE_COLORS[kind]]
            text(self.canvas, kind, (944, 612 + i * 37), 23, color, True)
            text(self.canvas, example, (1113, 614 + i * 37), 22, self.c['text'])
        text(self.canvas, 'Python · JavaScript · C · Java', (944, 790), 19, self.c['muted'])

    def draw_catalog(self):
        self.header('Impara facendo' if self.mode == 'learn' else 'Gioca · costruisci una sequenza' if self.mode == 'game' else 'Scova l’equivoco')
        if self.mode != 'quiz':
            for i, group in enumerate(GROUPS):
                self.button('filter:' + group, group, (40 + i * 224, 103, 212, 40), selected=self.filter == group, size=16)
        text(self.canvas, self.language, (1398, 114), 18, self.c['muted'], anchor='topright')
        items = list(enumerate(QUIZZES)) if self.mode == 'quiz' else [(i, item) for i, item in enumerate(MISSIONS) if self.filter == 'Tutte' or item.group == self.filter]
        pages = max(1, (len(items) + 8) // 9)
        self.catalog_page = max(0, min(self.catalog_page, pages - 1))
        for index, (original, item) in enumerate(items[self.catalog_page * 9:(self.catalog_page + 1) * 9]):
            rect = pygame.Rect(40 + index % 3 * 463, 166 + index // 3 * 205, 446, 187)
            complete = item.key + ':' + self.language in self.state['quizzes'] if self.mode == 'quiz' else f'{item.key}:{self.difficulty}:{self.language}' in self.state['completed']
            panel(self.canvas, rect, self.c['panel'], self.c['mint'] if complete or rect.collidepoint(self.pointer) else self.c['border'], 15)
            tag = f'EQUIVOCO {original + 1:02}' if self.mode == 'quiz' else item.group.upper()
            text(self.canvas, tag, (rect.x + 20, rect.y + 16), 13, self.c['mint'] if complete else self.c['accent'], True)
            text(self.canvas, '✓' if complete else '→', (rect.right - 24, rect.y + 16), 21, self.c['mint'], anchor='topright')
            wrap(self.canvas, item.title, pygame.Rect(rect.x + 20, rect.y + 51, 406, 61), 22, self.c['text'], True)
            wrap(self.canvas, 'Prevedi il codice che vedi, anche quando sbaglia.' if self.mode == 'quiz' else item.subtitle, pygame.Rect(rect.x + 20, rect.y + 125, 406, 46), 17, self.c['muted'])
            self.buttons.append(('quiz:' + str(original) if self.mode == 'quiz' else 'mission:' + item.key, rect, True))
        self.button('catalog_page:-1', '← Precedenti', (40, 799, 225, 45), active=self.catalog_page > 0)
        self.button('catalog_page:1', 'Altre sfide →', (1175, 799, 225, 45), active=self.catalog_page + 1 < pages)
        text(self.canvas, f'{len(items)} sfide · pagina {self.catalog_page + 1} / {pages}', (720, 822), 19, self.c['muted'], anchor='center')

    def bank_value(self):
        raw = self.bank_fields[self.bank_kind].value
        try:
            if self.bank_kind == 'string':
                return value(raw)
            if self.bank_kind == 'bool':
                if raw.lower() not in ('true', 'false'):
                    raise ValueError()
                return value(raw.lower() == 'true')
            if ',' in raw or not raw.strip():
                raise ValueError()
            result = int(raw) if self.bank_kind == 'int' else float(raw)
            return value(result, 32 if self.bank_language in ('C', 'Java') and self.bank_kind == 'float' else 64)
        except (ValueError, CodeError):
            raise CodeError('Scrivi true oppure false.' if self.bank_kind == 'bool' else 'Scrivi un intero senza parte frazionaria.' if self.bank_kind == 'int' else 'Scrivi un decimale finito con il punto, per esempio 2.5.')

    def draw_bank(self):
        self.header('Banco dei tipi · cambia il valore e osserva la rappresentazione')
        text(self.canvas, 'Stesso aspetto, significati diversi.', (40, 112), 33, self.c['text'], True)
        for i, kind in enumerate(TYPES):
            self.button('kind:' + kind, kind, (40 + i * 346, 177, 322, 57), selected=self.bank_kind == kind, size=26)
        panel(self.canvas, pygame.Rect(40, 261, 660, 319), self.c['panel'], self.c['border'], 16)
        text(self.canvas, 'SCRIVI UN VALORE DEL TIPO SCELTO', (62, 282), 17, self.c['accent'], True)
        editor = self.bank_fields[self.bank_kind]
        editor.draw(self.canvas, pygame.Rect(62, 323, 615, 63), self.c, size=27, tick=self.time, line_numbers=False)
        presets = {'int': ('0', '5', '-3'), 'float': ('0.0', '2.5', '0.1'), 'string': ('', '5', 'false'), 'bool': ('true', 'false')}[self.bank_kind]
        for i, raw in enumerate(presets):
            self.button('preset:' + str(i), 'Vuoto' if raw == '' else raw, (62 + i * 210, 410, 195, 44), size=20)
        notes = {'int': 'Conta elementi interi: zero, positivi e negativi.', 'float': 'Misura quantità frazionarie. Nel codice usa il punto.',
                 'string': 'Il contenuto resta testo: anche cifre, spazi e la parola false.', 'bool': 'Due valori logici: vero e falso. Qui scrivi il valore, non una stringa da convertire.'}
        wrap(self.canvas, notes[self.bank_kind], pygame.Rect(62, 491, 611, 76), 21, self.c['muted'])
        panel(self.canvas, pygame.Rect(742, 261, 658, 218), self.c['panel'], self.c[TYPE_COLORS[self.bank_kind]], 16)
        text(self.canvas, 'LA CELLA DI MEMORIA', (764, 280), 16, self.c['muted'], True)
        try:
            item = self.bank_value()
            label = display(item, self.bank_language)
            wrap(self.canvas, label, pygame.Rect(766, 321, 610, 92), 32, self.c[TYPE_COLORS[item.kind]], True)
            text(self.canvas, 'Tipo nel linguaggio: ' + type_name(item, self.bank_language), (765, 438), 20, self.c['text'])
            from engine import set_var
            expression = display(item, self.bank_language) if item.kind == 'float' else repr(item.data)
            code = generate([set_var('dato', self.bank_kind, expression)], self.bank_language)
        except CodeError as error:
            wrap(self.canvas, str(error), pygame.Rect(766, 325, 606, 105), 23, self.c['danger'])
            code = ('# ' if self.bank_language == 'Python' else '// ') + 'Completa un valore valido per vedere il codice.'
        for i, language in enumerate(LANGUAGES):
            self.button('bank_lang:' + language, language, (742 + i * 166, 502, 158, 43), selected=self.bank_language == language, size=17)
        if self.bank_code.value != code:
            self.bank_code.set(code)
        self.bank_code.draw(self.canvas, pygame.Rect(742, 567, 658, 154), self.c, readonly=True, size=21)
        wrap(self.canvas, 'Prova 5 come int e come string. Poi prova false come bool e come string. Le virgolette e il tipo spiegano la differenza.', pygame.Rect(48, 618, 645, 110), 23, self.c['text'])
        self.button('types', 'Capire i tipi · differenze tra linguaggi', (40, 788, 660, 55), size=20)
        self.button('bank_back', 'Torna al laboratorio', (742, 788, 658, 55), primary=True, size=20)

    def draw_settings(self):
        self.header('Preferenze della tua officina')
        panel(self.canvas, pygame.Rect(180, 144, 1080, 639), self.c['panel'], self.c['border'], 20)
        for row, (label, prefix, options, current) in enumerate([
            ('Aspetto', 'theme:', tuple(THEMES), self.state['theme']),
            ('Testo del codice e delle spiegazioni', 'size:', ('17', '19', '21'), str(self.state['size'])),
            ('Velocità del nastro', 'speed:', ('0.5', '1', '2', '3'), str(self.state['speed'])),
            ('Linguaggio', 'lang:', LANGUAGES, self.language),
        ]):
            top = 173 + row * 115
            text(self.canvas, label, (209, top), 21, self.c['text'], True)
            for i, option in enumerate(options):
                self.button(prefix + option, option + ('×' if prefix == 'speed:' else ''), (210 + i * 252, top + 38, 234, 44), selected=option == current)
        wrap(self.canvas, 'Le bozze restano sul computer. Aprire questa pagina mette in pausa il nastro. F11: schermo intero.', pygame.Rect(211, 656, 994, 64), 19, self.c['muted'])
        self.button('return', 'Torna al laboratorio', (870, 723, 350, 45), primary=True)

    def draw_modal(self):
        if self.modal == 'trace':
            self.draw_trace()
            return
        veil = pygame.Surface(SIZE, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 175))
        self.canvas.blit(veil, (0, 0))
        self.buttons = []
        panel(self.canvas, pygame.Rect(174, 79, 1092, 748), self.c['panel'], self.c['border'], 20)
        text(self.canvas, self.modal_title, (204, 107), 25, self.c['text'], True)
        self.button('close', 'Chiudi', (1126, 99, 112, 42))
        if self.modal == 'code':
            rect = pygame.Rect(206, 166, 1030, 584)
            self.modal_max = max(0, len(self.modal_editor.value.splitlines()) - rect.height // (self.state['size'] + 8) + 1)
            self.modal_scroll = max(0, min(self.modal_scroll, self.modal_max))
            self.modal_editor.scroll = self.modal_scroll
            self.modal_editor.draw(self.canvas, rect, self.c, readonly=True, size=self.state['size'])
        else:
            rect = pygame.Rect(205, 168, 1030, 581)
            height = len(lines(self.modal_text, rect.width - 18, self.state['size'])) * (font(self.state['size']).get_linesize() + 4)
            self.modal_max = max(0, height - rect.height)
            self.modal_scroll = max(0, min(self.modal_scroll, self.modal_max))
            clip = self.canvas.get_clip()
            self.canvas.set_clip(rect)
            wrap(self.canvas, self.modal_text, pygame.Rect(rect.x, rect.y - self.modal_scroll, rect.width - 18, height + 5), self.state['size'], self.c['text'])
            self.canvas.set_clip(clip)
        text(self.canvas, 'Rotella · frecce · PagSu/PagGiù · Home/End per scorrere', (205, 782), 16, self.c['muted'])

    def draw(self):
        self.buttons = []
        background(self.canvas, self.c, self.time)
        if self.page == 'home':
            self.draw_home()
        elif self.page == 'catalog':
            self.draw_catalog()
        elif self.page == 'settings':
            self.draw_settings()
        elif self.page == 'bank':
            self.draw_bank()
        else:
            self.draw_lab(self.page == 'quiz')
        text(self.canvas, 'Realizzato dal Prof. Barillà Francesco', (40, 880), 14, self.c['muted'], anchor='midleft')
        text(self.canvas, self.notice or 'OFFLINE · LEGGI, TRASFORMA, OSSERVA', (1400, 880), 13, self.c['muted'], anchor='midright')
        if self.modal:
            self.draw_modal()
        try:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if any(active and rect.collidepoint(self.pointer) for _, rect, active in self.buttons) else pygame.SYSTEM_CURSOR_ARROW)
        except pygame.error:
            pass
        width, height = self.screen.get_size()
        scale = min(width / SIZE[0], height / SIZE[1])
        size = round(SIZE[0] * scale), round(SIZE[1] * scale)
        self.screen.fill('#000000')
        self.screen.blit(pygame.transform.smoothscale(self.canvas, size), ((width - size[0]) // 2, (height - size[1]) // 2))

    def action(self, key):
        if key == 'close':
            self.modal = None
        elif key == 'trace_view':
            self.editor.focus = False
            self.start_trace(False)
            self.frame_index, self.progress, self.playing = 0, 1, False
            self.trace_editor.set(self.code())
            self.modal = 'trace'
        elif key in ('help', 'types', 'commands', 'idea', 'details', 'solution'):
            if key == 'help':
                self.open_text('Come si gioca', HOW_TO_PLAY)
            elif key == 'types':
                self.open_text('Quattro tipi di dati', TYPES_NOTES)
            elif key == 'commands':
                self.open_text('Dati e comandi · ' + self.language, commands_text(self.language))
            elif key == 'idea':
                self.open_text('La regola e l’equivoco', self.mission.concept + '\n\nPROVA A CAMBIARE UN DATO\n' + self.mission.trap + '\n\n' + MISCONCEPTIONS)
            elif key == 'solution':
                self.open_text('Una sequenza possibile · ' + self.language, self.mission.solution(self.language), True)
            else:
                self.open_text('Leggi il passo', (self.feedback + '\n\n' if self.feedback else '') + self.frame.message + ('\n\n' + self.quiz.explanation if self.page == 'quiz' else '\n\n' + self.mission.concept))
        elif key.startswith('mode:'):
            self.persist()
            self.mode, self.page = key.split(':')[1], 'catalog'
            self.filter, self.catalog_page, self.playing = 'Tutte', 0, False
        elif key.startswith('mission:'):
            self.open_mission(key.split(':')[1])
        elif key.startswith('quiz:'):
            self.open_quiz(int(key.split(':')[1]))
        elif key.startswith('filter:'):
            self.filter, self.catalog_page = key.split(':')[1], 0
        elif key.startswith('catalog_page:'):
            self.catalog_page += int(key.split(':')[1])
        elif key.startswith('lang:'):
            self.set_language(key.split(':')[1])
        elif key.startswith('diff:'):
            self.set_difficulty(key.split(':')[1])
        elif key.startswith('theme:'):
            self.state['theme'] = key.split(':')[1]
            self.c = palette(self.state['theme'])
            self.persist()
        elif key.startswith('size:'):
            self.state['size'] = int(key.split(':')[1])
            self.persist()
        elif key.startswith('speed:'):
            self.state['speed'] = float(key.split(':')[1])
            self.persist()
        elif key in ('home', 'catalog', 'settings', 'return'):
            self.persist()
            self.playing = False
            if key == 'settings':
                if self.page != 'settings':
                    self.return_page = self.page
                self.page = 'settings'
            else:
                self.page = self.return_page if key == 'return' else key
        elif key in ('learn', 'try'):
            self.persist()
            self.page = 'transition'
            self.mode = 'learn' if key == 'learn' else 'game'
            self.open_mission(self.mission.key, self.case_index)
        elif key.startswith('case:'):
            self.case_index = (self.case_index + int(key.split(':')[1])) % len(self.mission.cases)
            self.invalidate()
            if self.mode == 'learn':
                self.prepare_learn()
        elif key.startswith('predict:'):
            self.choose_prediction(int(key.split(':')[1]))
        elif key == 'next_prediction':
            if self.prediction_answered and not self.playing and self.progress >= 1:
                if self.frame_index + 1 < len(self.frames):
                    self.prepare_prediction()
                else:
                    self.action('case:1')
        elif key == 'resume':
            self.playing = True
        elif key.startswith('shift:'):
            _, row, delta = key.split(':')
            row, destination = int(row), int(row) + int(delta)
            if 0 <= row < len(self.order) and 0 <= destination < len(self.order):
                self.selected = row
                self.move_card(destination)
                self.selected = None
        elif key.startswith('cards_scroll:'):
            self.block_scroll += int(key.split(':')[1]) * 222
        elif key == 'next_mission':
            index = MISSIONS.index(self.mission)
            if index + 1 < len(MISSIONS):
                self.open_mission(MISSIONS[index + 1].key)
            else:
                self.action('catalog')
        elif key.startswith('results:'):
            self.result_scroll = max(0, self.result_scroll + int(key.split(':')[1]))
        elif key == 'program':
            self.open_text('Il programma completo ? ' + self.language, self.mission.solution(self.language), True)
        elif key.startswith('card:'):
            index = int(key.split(':')[1])
            if self.selected is None or self.selected == index:
                self.selected = index if self.selected is None else None
            else:
                self.move_card(index)
                self.selected = None
        elif key.startswith('move:') and self.selected is not None:
            self.move_card(self.selected + int(key.split(':')[1]))
        elif key == 'shuffle':
            self.order, self.selected = self.shuffled_order(), None
            self.invalidate()
            self.editor.set(self.code())
            self.persist()
        elif key == 'run':
            if self.playing:
                self.playing = False
            elif self.frames and (self.frame_index < len(self.frames) - 1 or self.progress < 1):
                self.auto, self.playing = True, True
            else:
                self.start_trace()
        elif key == 'step':
            self.playing = False
            if not self.frames:
                self.start_trace(False)
            elif self.frame_index + 1 < len(self.frames):
                self.frame_index += 1
            self.progress = 1
            self.reveal_frame()
        elif key == 'restart':
            self.invalidate()
        elif key == 'verify':
            self.verify()
        elif key == 'memory':
            self.memory_page = (self.memory_page + 1) % max(1, (len(self.frame.memory) + 3) // 4)
        elif key.startswith('answer:'):
            self.quiz_choice = int(key.split(':')[1])
            self.quiz_attempted = False
            self.invalidate()
        elif key == 'check':
            self.check_quiz()
        elif key == 'next_quiz':
            self.open_quiz(self.quiz_index + 1)
        elif key == 'bank':
            self.persist()
            self.playing = False
            if self.page != 'bank':
                self.bank_return, self.bank_origin_language = self.page, self.language
                self.bank_language = self.language
            self.page = 'bank'
        elif key == 'bank_back':
            if self.bank_return == 'lab' and self.bank_origin_language != self.language:
                self.open_mission(self.mission.key, self.case_index)
            elif self.bank_return == 'quiz' and self.bank_origin_language != self.language:
                self.open_quiz(self.quiz_index)
            else:
                self.page = self.bank_return
        elif key.startswith('kind:'):
            self.bank_fields[self.bank_kind].focus = False
            self.bank_kind = key.split(':')[1]
        elif key.startswith('bank_lang:'):
            self.bank_language = key.split(':')[1]
        elif key.startswith('preset:'):
            values = {'int': ('0', '5', '-3'), 'float': ('0.0', '2.5', '0.1'), 'string': ('', '5', 'false'), 'bool': ('true', 'false')}[self.bank_kind]
            self.bank_fields[self.bank_kind].set(values[int(key.split(':')[1])])

    def logical(self, position):
        width, height = self.screen.get_size()
        scale = min(width / SIZE[0], height / SIZE[1])
        return ((position[0] - (width - SIZE[0] * scale) / 2) / scale, (position[1] - (height - SIZE[1] * scale) / 2) / scale)

    def event(self, event):
        if event.type == pygame.QUIT:
            self.persist()
            self.alive = False
            return
        if event.type == pygame.VIDEORESIZE and not self.fullscreen:
            self.screen = pygame.display.set_mode((max(960, event.w), max(600, event.h)), pygame.RESIZABLE)
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.pointer = self.logical(event.pos)
        bank = not self.modal and self.page == 'bank'
        editable = not self.modal and self.page == 'lab' and self.mode == 'game' and not self.easy
        active_editor = self.bank_fields[self.bank_kind] if bank else self.editor
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pressed = next((key for key, rect, active in reversed(self.buttons) if active and rect.collidepoint(self.pointer)), None)
            if bank or editable:
                active_editor.focus = active_editor.rect.collidepoint(self.pointer)
                if active_editor.focus:
                    active_editor.click(self.pointer, bool(pygame.key.get_mods() & pygame.KMOD_SHIFT))
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            target = next((key for key, rect, active in reversed(self.buttons) if active and rect.collidepoint(self.pointer)), None)
            if target and target == self.pressed:
                self.action(target)
            self.pressed = None
        if event.type == pygame.MOUSEWHEEL:
            if self.modal == 'trace':
                self.trace_editor.scroll = max(0, self.trace_editor.scroll - event.y * 3)
            elif self.modal:
                self.modal_scroll -= event.y * (3 if self.modal == 'code' else 75)
            elif self.page in ('lab', 'quiz') and self.code_rect.collidepoint(self.pointer):
                if self.easy and self.page == 'lab':
                    self.block_scroll -= event.y * 60
                elif pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    self.editor.xscroll = max(0, self.editor.xscroll - event.y * 5)
                else:
                    self.editor.scroll = max(0, self.editor.scroll - event.y * 3)
        if event.type == pygame.TEXTINPUT and (bank or editable) and active_editor.focus:
            content = event.text.replace('\n', '').replace('\r', '') if bank else event.text
            if not bank or len(active_editor.value) + len(content) - abs(active_editor.caret - active_editor.anchor) <= 40:
                active_editor.replace(content)
                if editable:
                    self.invalidate()
                    self.persist()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                if not self.fullscreen:
                    self.window_size = self.screen.get_size()
                    self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
                self.fullscreen = not self.fullscreen
            elif event.key == pygame.K_ESCAPE:
                self.action('close' if self.modal else 'return' if self.page == 'settings' else 'bank_back' if bank else 'home')
            elif self.modal and event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_HOME, pygame.K_END):
                self.modal_scroll += {pygame.K_UP: -60, pygame.K_DOWN: 60, pygame.K_PAGEUP: -400, pygame.K_PAGEDOWN: 400, pygame.K_HOME: -100000, pygame.K_END: 100000}[event.key] // (20 if self.modal == 'code' else 1)
            elif (bank or editable) and active_editor.focus:
                if not bank or event.key not in (pygame.K_RETURN, pygame.K_TAB):
                    changed = active_editor.key(event)
                    if bank:
                        cleaned = active_editor.value.replace('\n', '').replace('\r', '')[:40]
                        if cleaned != active_editor.value:
                            active_editor.set(cleaned)
                    elif changed:
                        self.invalidate()
                        self.persist()
            elif event.key == pygame.K_TAB:
                enabled = [key for key, _, active in self.buttons if active]
                if enabled:
                    index = enabled.index(self.focus) if self.focus in enabled else -1
                    self.focus = enabled[(index + (-1 if event.mod & pygame.KMOD_SHIFT else 1)) % len(enabled)]
                    self.pointer = next(rect.center for key, rect, _ in self.buttons if key == self.focus)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.focus:
                if any(key == self.focus and active for key, _, active in self.buttons):
                    self.action(self.focus)

    def update(self, dt):
        self.time += dt
        if self.playing and not self.modal and self.page in ('lab', 'quiz'):
            self.progress = min(1, self.progress + dt * .7 * self.state['speed'])
            if self.progress >= 1:
                if self.auto and self.frame_index + 1 < len(self.frames):
                    self.frame_index += 1
                    self.progress = 0
                    self.reveal_frame()
                else:
                    self.playing = False


def smoke(report, screenshots=None):
    app = App(pygame.display.set_mode((1280, 800)), saving=False)
    directory = Path(screenshots) if screenshots else None
    if directory:
        directory.mkdir(parents=True, exist_ok=True)
    def capture(name):
        app.draw()
        if directory:
            pygame.image.save(app.canvas, str(directory / (name + '.png')))
    capture('01-home')
    checks = 0
    for theme in THEMES:
        app.state['theme'], app.c = theme, palette(theme)
        for language in LANGUAGES:
            app.state['language'] = language
            for mode in ('learn', 'game'):
                app.page, app.mode = 'home', mode
                for mission in MISSIONS:
                    app.open_mission(mission.key)
                    app.draw()
                    assert all(pygame.Rect(0, 0, *SIZE).contains(rect) for _, rect, _ in app.buttons)
                    checks += 1
    app.state['theme'], app.c = 'Notte', palette('Notte')
    app.set_language('Python')
    app.action('mode:game')
    capture('02-missioni')
    app.mode = 'learn'
    app.open_mission('copia')
    capture('03-prevedi')
    app.choose_prediction(next(i for i, item in enumerate(app.prediction_options) if app.equivalent(item, app.frames[1].after)))
    app.update(2)
    capture('04-osserva')
    app.action('try')
    capture('05-riordina')
    app.order = list(range(len(app.mission.instructions)))
    app.editor.set(app.code())
    app.start_trace(False)
    app.frame_index = len(app.frames) - 1
    app.progress = 1
    app.verify()
    capture('06-sequenza-collaudata')
    for kind in TYPES:
        app.action('bank')
        app.action('kind:' + kind)
        capture('07-banco-' + kind)
        app.action('bank_back')
    app.action('mode:quiz')
    app.open_quiz(8)
    app.quiz_choice = app.quiz.correct(app.language)
    app.check_quiz()
    app.frame_index = len(app.frames) - 1
    app.progress, app.playing = 1, False
    capture('08-equivoco-scambio')
    app.action('settings')
    capture('09-impostazioni')
    app.action('return')
    app.page, app.mode = 'home', 'game'
    app.set_difficulty('Difficile')
    app.set_language('Java')
    app.open_mission('sonda')
    app.editor.set(app.mission.solution(app.language))
    app.start_trace(False)
    app.frame_index = len(app.frames) - 1
    capture('10-quattro-tipi-java')
    app.action('learn')
    app.set_language('Python')
    app.open_mission('interi', 1)
    app.choose_prediction(next(i for i, item in enumerate(app.prediction_options) if item.data != 3))
    capture('11-impara-riprova')
    app.open_mission('copia')
    while app.frame_index < len(app.frames) - 1:
        app.choose_prediction(next(i for i, item in enumerate(app.prediction_options) if app.equivalent(item, app.frames[app.frame_index + 1].after)))
        app.update(3)
        if app.frame_index < len(app.frames) - 1:
            app.action('next_prediction')
    capture('12-lezione-completata')
    app.action('try')
    app.set_difficulty('Facile')
    app.open_mission('ordine')
    app.order = [2, 1, 0]
    app.verify()
    capture('13-gioca-risultato-errato')
    app.open_mission('copia')
    app.order = [1, 0, 2, 3, 4]
    app.verify()
    capture('14-gioca-errore-riga')
    app.order = [0, 1, 2, 3, 4]
    app.invalidate()
    app.action('trace_view')
    app.action('step')
    capture('15-esecuzione-passo-passo')
    app.action('close')
    app.set_difficulty('Medio')
    app.open_mission('interi')
    capture('16-completa-il-codice')
    app.set_difficulty('Facile')
    app.set_language('Java')
    app.open_mission('sonda')
    app.block_scroll = 10000
    capture('17-sequenza-lunga-java')
    Path(report).parent.mkdir(parents=True, exist_ok=True)
    Path(report).write_text(json.dumps(dict(ok=True, missions=len(MISSIONS), quizzes=len(QUIZZES), languages=list(LANGUAGES), render_checks=checks)), encoding='utf-8')


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    pygame.display.set_icon(icon())
    pygame.key.set_repeat(450, 35)
    if '--smoke-test' in sys.argv:
        screenshots = sys.argv[sys.argv.index('--screenshots') + 1] if '--screenshots' in sys.argv else None
        smoke(sys.argv[sys.argv.index('--smoke-test') + 1], screenshots)
    else:
        app = App(pygame.display.set_mode((1280, 800), pygame.RESIZABLE))
        clock = pygame.time.Clock()
        app.draw()
        while app.alive:
            dt = min(.1, clock.tick(60) / 1000)
            for event in pygame.event.get():
                app.event(event)
            app.update(dt)
            app.draw()
            pygame.display.flip()
    pygame.quit()


if __name__ == '__main__':
    main()
