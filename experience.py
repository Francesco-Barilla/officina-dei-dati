"""Focused teaching views: observe one instruction, act, understand the result."""
import re
import pygame
from engine import LANGUAGES, display, source_line, type_name, value
from missions import DIFFICULTIES, MISSIONS
from scene import TYPE_COLORS
from ui import font, mix, panel, robot, text, wrap
from writing_guide import STEPS, example_for, first_gap, meaningful_code, writing_task


class LabExperience:
    def prediction_hint(self, target):
        before = self.frames[self.frame_index]
        if target.consumed > before.consumed:
            item = self.case.inputs[before.consumed]
            return 'Il gioco fornisce ' + display(item, self.language) + '. Il computer lo copia nella variabile: scegli quel valore.'
        if not target.target:
            return 'La stampa mostra il valore dell’espressione tra parentesi, senza modificarlo.'
        return 'Parti dai valori nel riquadro “Da usare”: calcola a destra di =, poi sostituisci il valore a sinistra.'

    def lab_button(self, key, label, rect, primary=False, active=True, tone=None, selected=False, size=19):
        """Buttons communicate the action and its state without relying on color alone."""
        rect = pygame.Rect(rect)
        hover = active and rect.collidepoint(self.pointer)
        focus = active and self.focus == key
        edge = self.c[tone] if tone else self.c['mint'] if primary else self.c['accent'] if selected else self.c['border']
        fill = edge if primary and active else mix(self.c['panel'], edge, .23 if selected or tone else .15 if hover else 0)
        if self.pressed == key:
            fill = mix(fill, self.c['text'], .13)
        panel(self.canvas, rect, fill, edge, 10)
        if focus or hover:
            pygame.draw.rect(self.canvas, self.c['text'] if focus else self.c['mint'], rect.inflate(-4, -4), 2, border_radius=8)
        color = self.c['bg'] if primary and active else self.c['text'] if active or tone else self.c['muted']
        if font(size, True).size(label)[0] > rect.width - 24:
            wrap(self.canvas, label, rect.inflate(-24, -14), size, color, True)
        else:
            text(self.canvas, label, rect.center, size, color, True, 'center')
        self.buttons.append((key, rect, active))

    def fitted(self, label, rect, size=24, color=None, mono=False):
        size = min(size, 32)
        while size > 16 and font(size, True, mono).size(str(label))[0] > rect.width:
            size -= 1
        clip = self.canvas.get_clip()
        self.canvas.set_clip(rect.clip(clip))
        text(self.canvas, label, rect.midleft, size, color or self.c['text'], True, 'midleft', mono=mono)
        self.canvas.set_clip(clip)

    def draw_lab(self, quiz=False):
        if quiz:
            self.draw_quiz()
            return
        learn = self.mode == 'learn'
        s, c = self.canvas, self.c
        text(s, '← OFFICINA DEI DATI', (32, 25), 21, c['text'], True)
        self.buttons.append(('home', pygame.Rect(32, 19, 282, 43), True))
        self.lab_button('learn', 'Impara', (331, 19, 112, 42), selected=learn, size=17)
        self.lab_button('try', 'Gioca', (451, 19, 100, 42), selected=not learn, size=17)
        self.lab_button('catalog', 'Tutte le missioni', (902, 19, 183, 42), size=16)
        self.lab_button('help', 'Aiuto', (1097, 19, 97, 42), size=16)
        self.lab_button('settings', 'Impostazioni', (1206, 19, 202, 42), size=16)
        pygame.draw.line(s, c['border'], (32, 76), (1408, 76))
        text(s, self.mission.title, (32, 92), 32, c['text'], True)
        text(s, 'LA TUA MISSIONE', (34, 138), 13, c['accent'], True)
        wrap(s, self.mission.objective, pygame.Rect(34, 158, 1350, 49), 20, c['text'])
        text(s, 'Codice:', (34, 218), 16, c['muted'])
        for i, language in enumerate(LANGUAGES):
            self.lab_button('lang:' + language, language, (109 + i * 125, 209, 117, 34), selected=self.language == language, size=15)
        if learn:
            self.lab_button('case:-1', '‹', (638, 209, 32, 34), active=len(self.mission.cases) > 1, size=22)
            text(s, f'Esempio {self.case_index + 1}/{len(self.mission.cases)}', (684, 217), 15, c['muted'])
            self.lab_button('case:1', '›', (846, 209, 32, 34), active=len(self.mission.cases) > 1, size=22)
            text(s, 'Osserva → rispondi → scopri cosa cambia', (916, 220), 16, c['muted'])
        else:
            text(s, 'Modalità:', (699, 218), 16, c['muted'])
            for i, (difficulty, label) in enumerate(zip(DIFFICULTIES, ('Facile · riordina', 'Medio · completa', 'Difficile · scrivi'))):
                self.lab_button('diff:' + difficulty, label, (782 + i * 211, 209, 203, 34), selected=self.difficulty == difficulty, size=15)
        if learn:
            self.draw_lesson_board()
            self.draw_lesson_action()
        else:
            self.draw_program_board()
            self.draw_game_action()

    def lesson_target(self):
        if self.prediction_answered:
            return self.frame, self.frames[max(0, self.frame_index - 1)]
        if self.frame_index + 1 < len(self.frames):
            return self.frames[self.frame_index + 1], self.frame
        return self.frame, self.frame

    def draw_lesson_board(self):
        s, c = self.canvas, self.c
        target, before = self.lesson_target()
        panel(s, pygame.Rect(32, 260, 852, 589), c['panel'], radius=16)
        total = max(1, len(self.frames) - 1)
        step = self.frame_index if self.prediction_answered else self.frame_index + 1
        text(s, f'1  OSSERVA  ·  PASSO {step} DI {total}', (55, 282), 17, c['mint'], True)
        self.lab_button('program', 'Tutto il programma', (637, 274, 224, 36), size=15)
        pygame.draw.rect(s, c['border'], (55, 321, 806, 4), border_radius=2)
        pygame.draw.rect(s, c['mint'], (55, 321, max(4, int(806 * self.frame_index / total)), 4), border_radius=2)
        code = self.mission.solution(self.language).splitlines()[target.line - 1] if target.line else ''
        panel(s, pygame.Rect(55, 343, 806, 69), c['bg'], c['mint'], 10)
        text(s, f'{target.line:02}', (70, 365), 20, c['mint'], True, mono=True)
        self.fitted(code, pygame.Rect(117, 350, 726, 54), 27, mono=True)
        read = target.consumed > before.consumed
        description = ('Il computer leggerà il dato del gioco e lo metterà in ' + target.target + '.') if read else (
            'Il computer mostrerà il valore sullo schermo, senza cambiare la memoria.' if not target.target else
            f'Il computer calcolerà a destra di = e aggiornerà {target.target}. Tu prevedi il valore.')
        if self.prediction_answered:
            description = ('Il computer ha letto il dato del gioco e lo ha messo in ' + target.target + '.') if read else (
                'Il computer ha mostrato il valore. La memoria non è cambiata.' if not target.target else
                f'Il computer ha calcolato a destra di = e ha aggiornato {target.target}.')
        wrap(s, description, pygame.Rect(57, 428, 800, 53), 21, c['text'])
        left, right = pygame.Rect(55, 493, 354, 126), pygame.Rect(508, 493, 353, 126)
        for rect in (left, right):
            panel(s, rect, c['bg'], c['border'], 12)
        text(s, 'INGRESSO DA LEGGERE' if read else 'DA USARE', (72, 508), 14, c['muted'], True)
        if read:
            item = self.case.inputs[before.consumed]
            self.fitted(display(item, self.language), pygame.Rect(72, 536, 315, 38), 30, c[TYPE_COLORS[item.kind]])
            text(s, type_name(target.after, self.language), (73, 586), 17, c['muted'])
        else:
            used = [(name, item) for name, item in before.memory if re.search(r'\b' + re.escape(name) + r'\b', code)]
            if used:
                for i, (name, item) in enumerate(used[:3]):
                    self.fitted(name + ' = ' + display(item, self.language), pygame.Rect(72, 536 + i * 24, 316, 27), 22)
            else:
                wrap(s, 'Il valore scritto\nnella riga qui sopra.', pygame.Rect(73, 539, 310, 75), 22, c['text'])
        text(s, target.target if target.target else 'SULLO SCHERMO', (525, 508), 14, c['muted'], True)
        if self.prediction_answered:
            color = c[TYPE_COLORS[target.after.kind]]
            self.fitted(display(target.after, self.language), pygame.Rect(525, 540, 313, 39), 31, color)
            text(s, type_name(target.after, self.language), (526, 586), 17, c['muted'])
        else:
            text(s, '?', (527, 536), 40, c['mint'], True)
            text(s, 'Scegli la risposta a destra →', (526, 590), 17, c['muted'])
        pygame.draw.line(s, c['mint'], (428, 556), (484, 556), 3)
        pygame.draw.polygon(s, c['mint'], [(485, 556), (475, 549), (475, 563)])
        if self.prediction_answered and self.progress < 1:
            pygame.draw.circle(s, c['accent'], (round(426 + 62 * self.progress), 556), 7)
        self.draw_live_state(pygame.Rect(55, 642, 806, 184))

    def draw_live_state(self, rect):
        s, c = self.canvas, self.c
        half = (rect.width - 28) // 2
        text(s, 'MEMORIA ADESSO', (rect.x, rect.y), 14, c['muted'], True)
        text(s, 'SCHERMO ADESSO', (rect.x + half + 28, rect.y), 14, c['muted'], True)
        pygame.draw.line(s, c['border'], (rect.x + half + 13, rect.y), (rect.x + half + 13, rect.bottom))
        memory = list(self.frame.memory)
        pages = max(1, (len(memory) + 3) // 4)
        self.memory_page = min(self.memory_page, pages - 1)
        if pages > 1:
            self.lab_button('memory', f'{self.memory_page + 1}/{pages} →', (rect.x + half - 79, rect.y - 5, 78, 28), size=13)
        if not memory:
            wrap(s, 'Ancora vuota.\nNessuna variabile creata.', pygame.Rect(rect.x, rect.y + 39, half, 72), 20, c['muted'])
        for i, (name, item) in enumerate(memory[self.memory_page * 4:self.memory_page * 4 + 4]):
            y = rect.y + 31 + i * 35
            if name == self.frame.target:
                panel(s, pygame.Rect(rect.x - 5, y - 2, half + 8, 32), mix(c['panel'], c['mint'], .13), radius=5)
            self.fitted(name + ' = ' + display(item, self.language), pygame.Rect(rect.x + 3, y, half - 81, 29), 20)
            text(s, type_name(item, self.language), (rect.x + half - 3, y + 6), 14, c[TYPE_COLORS[item.kind]], anchor='topright')
        outputs = self.frame.outputs
        x = rect.x + half + 28
        if not outputs:
            wrap(s, 'Ancora vuoto.\nUna stampa farà comparire un valore.', pygame.Rect(x, rect.y + 39, half, 105), 20, c['muted'])
        for i, item in enumerate(outputs[-4:]):
            self.fitted(f'{max(0, len(outputs) - 4) + i + 1}.  ' + display(item, self.language), pygame.Rect(x, rect.y + 31 + i * 35, half, 29), 21, c['blue'])

    def draw_lesson_action(self):
        s, c = self.canvas, self.c
        target, before = self.lesson_target()
        answered = self.prediction_answered
        finished = answered and self.frame_index == len(self.frames) - 1
        panel(s, pygame.Rect(908, 260, 500, 589), c['panel'], radius=16)
        if finished and self.progress >= 1:
            self.draw_lesson_finish()
            return
        text(s, '2  SCEGLI UNA RISPOSTA' if not answered else '2  RISPOSTA CORRETTA', (932, 282), 17, c['mint'], True)
        prompt = f'Che valore avrà {target.target}?' if target.target else 'Che cosa apparirà sullo schermo?'
        wrap(s, prompt, pygame.Rect(932, 324, 449, 76), 28, c['text'], True)
        for i, item in enumerate(self.prediction_options):
            selected = self.prediction_choice == i
            tone = ('mint' if answered else 'danger') if selected else None
            prefix = 'Corretto:  ' if selected and answered else 'Riprova:  ' if selected else ''
            label = prefix + display(item, self.language) + '   ·   ' + type_name(item, self.language)
            self.lab_button('predict:' + str(i), label, (932, 418 + i * 72, 452, 61), active=not answered, tone=tone, selected=selected, size=22)
        if self.feedback_kind == 'wrong':
            title, color = '×  Da rivedere. Puoi riprovare.', 'danger'
        elif answered:
            title, color = 'Corretto. Ecco cosa è cambiato.', 'mint'
        else:
            title, color = 'Fai clic su una delle tre risposte.', 'muted'
        text(s, title, (932, 648), 20, c[color], True)
        wrap(s, self.feedback, pygame.Rect(932, 681, 450, 96), 19, c['text'])
        if answered:
            paused = not self.playing and self.progress < 1
            key = 'resume' if paused else 'try' if finished else 'next_prediction'
            label = 'Riprendi il passaggio' if paused else 'Lezione conclusa · ora prova tu →' if finished else 'Ho capito · passo successivo →'
            self.lab_button(key, label, (932, 788, 452, 43), primary=True, active=not self.playing, size=18)
        else:
            self.lab_button('idea', 'Mi serve un indizio', (932, 788, 452, 43), size=18)

    def draw_lesson_finish(self):
        s, c = self.canvas, self.c
        text(s, 'TUTTI I PASSI COMPLETATI', (932, 282), 17, c['mint'], True)
        robot(s, (1157, 365), 1.3, tick=self.time)
        text(s, 'Hai eseguito la sequenza.', (932, 427), 26, c['text'], True)
        text(s, 'CHE COSA HAI SCOPERTO', (932, 481), 14, c['mint'], True)
        wrap(s, self.mission.concept, pygame.Rect(932, 506, 451, 131), 21, c['text'])
        text(s, 'OCCHIO A QUESTO ERRORE', (932, 644), 14, c['accent'], True)
        wrap(s, self.mission.trap, pygame.Rect(932, 672, 451, 96), 19, c['text'])
        self.lab_button('try', 'Ora costruisci tu la sequenza →', (932, 788, 452, 43), primary=True, size=18)

    def instruction_description(self, item):
        if 'leggi_' in item.expression:
            return 'Leggi un dato → ' + item.target
        if not item.target:
            return 'Mostra sullo schermo'
        if item.kind:
            return 'Crea ' + item.target + ' · ' + item.kind
        return 'Aggiorna ' + item.target

    def draw_program_board(self):
        s, c = self.canvas, self.c
        panel(s, pygame.Rect(32, 260, 852, 589), c['panel'], radius=16)
        title = '1  SPOSTA LE TESSERE' if self.easy else '1  COMPLETA IL CODICE' if self.difficulty == 'Medio' else '1  SCRIVI IL CODICE'
        text(s, title, (55, 282), 17, c['mint'], True)
        if self.easy:
            wrap(s, 'Usa ↑ e ↓ per cambiare l’ordine. Quando sei pronto, premi Controlla a destra.', pygame.Rect(55, 319, 806, 53), 20, c['text'])
            self.code_rect = pygame.Rect(55, 377, 806, 370)
        else:
            self.draw_writing_instructions()
        if self.easy:
            self.draw_program_cards()
        else:
            self.editor.draw(s, self.code_rect, c, active=self.frame.line, error=self.error_line, size=self.state['size'] + 2, tick=self.time)
            if not meaningful_code(self.editor.value) and not self.editor.focus:
                text(s, 'Scrivi qui le istruzioni', (79, 438), 26, c['muted'], True)
                wrap(s, 'Premi il pulsante Scrivi qui, poi usa la tastiera.\nPer andare a capo premi Invio.', pygame.Rect(79, 486, 735, 69), 20, c['muted'])
            self.draw_writing_example()
        if self.easy:
            text(s, f'{len(self.order)} tessere · clicca due tessere per scambiarle.', (56, 759), 15, c['muted'])
            if len(self.order) > 5:
                self.lab_button('cards_scroll:-1', 'Scorri ↑', (623, 753, 114, 30), active=self.block_scroll > 0, size=14)
                self.lab_button('cards_scroll:1', 'Scorri ↓', (747, 753, 114, 30), active=self.block_scroll < len(self.order) * 74 - self.code_rect.height, size=14)
        self.lab_button('commands', 'Cosa devo scrivere?' if not self.easy else 'Consegna guidata', (55, 791, 226, 42), size=17)
        self.lab_button('learn', 'Fammi vedere un esempio', (293, 791, 315, 42), size=17)
        self.lab_button('solution', 'Mostra una soluzione', (620, 791, 241, 42), size=16)

    def draw_writing_instructions(self):
        s, c = self.canvas, self.c
        gap = first_gap(self.editor.value, self.language)
        label = 'Completa i ???' if gap else 'Scrivi qui'
        self.lab_button('focus_code', label, (637, 274, 224, 38), selected=self.editor.focus, size=18)
        title, instruction = writing_task(self.mission, self.editor.value, self.difficulty, self.language)
        wrap(s, title + '\n' + instruction, pygame.Rect(55, 323, 806, 62), 18, c['text'])
        status = f'Stai scrivendo in {self.language} · Invio va a capo · Ctrl+Invio controlla' if self.editor.focus else (
            f'Punto da completare: riga {gap.line} · premi Completa i ???' if gap else f'Zona di scrittura · {self.language}')
        text(s, status, (57, 389), 14, c['accent'] if self.editor.focus or gap else c['muted'])
        self.code_rect = pygame.Rect(55, 416, 806, 240)

    def draw_writing_example(self):
        s, c = self.canvas, self.c
        caption, sample = example_for(self.mission, self.language, self.editor.value, self.difficulty)
        text(s, caption, (57, 670), 15, c['blue'], True)
        for i, line in enumerate(sample):
            self.fitted(line, pygame.Rect(58, 696 + i * 25, 797, 27), 19, mono=True)
        if len(sample) == 1:
            tip = 'Usa i nomi e i valori della tua missione. Questo è solo un esempio di sintassi.'
            wrap(s, tip, pygame.Rect(58, 736, 797, 42), 16, c['muted'])

    def draw_program_cards(self):
        rect, s, c = self.code_rect, self.canvas, self.c
        row_height = 74
        total = len(self.order) * row_height
        self.block_scroll = max(0, min(self.block_scroll, max(0, total - rect.height)))
        clip = s.get_clip()
        viewport = rect.clip(clip)
        s.set_clip(viewport)
        for index, original in enumerate(self.order):
            item = self.mission.instructions[original]
            row = pygame.Rect(rect.x, rect.y + index * row_height - self.block_scroll, rect.width - 12, 65)
            if not row.colliderect(viewport):
                continue
            selected = self.selected == index
            error = self.error_line == index + 1
            edge = c['danger'] if error else c['accent'] if selected else c['border']
            panel(s, row, mix(c['bg'], edge, .16 if selected or error else 0), edge, 10)
            text(s, f'{index + 1:02}', (row.x + 15, row.y + 19), 25, c['accent'] if selected else c['muted'], True, mono=True)
            text(s, self.instruction_description(item), (row.x + 66, row.y + 7), 16, c['mint'], True)
            self.fitted(source_line(item, self.language), pygame.Rect(row.x + 66, row.y + 29, row.width - 204, 31), 22, mono=True)
            hit = pygame.Rect(row.x, row.y, row.width - 115, row.height).clip(viewport)
            self.buttons.append(('card:' + str(index), hit, True))
            for delta, arrow, x in ((-1, '↑', row.right - 107), (1, '↓', row.right - 57)):
                arrow_rect = pygame.Rect(x, row.y + 9, 43, 46)
                active = 0 <= index + delta < len(self.order)
                self.lab_button(f'shift:{index}:{delta}', arrow, arrow_rect, active=active, size=25)
                # Hit areas must stay inside the scrolling viewport too.
                key, bounds, enabled = self.buttons[-1]
                self.buttons[-1] = (key, bounds.clip(viewport), enabled and bounds.clip(viewport).height >= 28)
        s.set_clip(clip)
        if total > rect.height:
            height = rect.height * rect.height / total
            y = rect.y + (rect.height - height) * self.block_scroll / (total - rect.height)
            panel(s, pygame.Rect(rect.right - 5, y, 4, height), c['muted'], radius=2)

    def draw_game_action(self):
        s, c = self.canvas, self.c
        panel(s, pygame.Rect(908, 260, 500, 589), c['panel'], radius=16)
        success = self.review is not None and self.review.success
        text(s, '2  CONTROLLA IL RISULTATO', (932, 282), 17, c['mint'], True)
        if self.review:
            color = 'mint' if success else 'danger'
            title = 'Missione completata' if success else 'Da correggere: riprova'
            text(s, title, (932, 322), 24, c[color], True)
            wrap(s, self.review.message, pygame.Rect(932, 362, 449, 87), 19, c['text'])
            self.lab_button('details', 'Spiegazione', (1244, 460, 140, 31), size=14)
            text(s, f'{self.review.passed}/{self.review.total} esempi riusciti', (932, 466), 16, c[color], True)
        else:
            text(s, 'Che cosa deve fare il codice?', (932, 322), 24, c['text'], True)
            instructions = '\n'.join(f'{i + 1}. {step}' for i, step in enumerate(STEPS[self.mission.key]))
            wrap(s, instructions, pygame.Rect(932, 365, 449, 124), 18, c['text'])
        self.draw_case_goal()
        if self.review:
            self.draw_comparison()
        else:
            _, outputs = self.mission.expected([item.data for item in self.case.inputs])
            panel(s, pygame.Rect(932, 552, 452, 161), c['bg'], radius=10)
            text(s, 'IL CODICE DEVE MOSTRARE, IN ORDINE', (949, 565), 13, c['blue'], True)
            for i, raw in enumerate(outputs[:4]):
                item = value(raw, 32 if self.language in ('C', 'Java') and type(raw) is float else 64)
                self.fitted(f'{i + 1}.  ' + display(item, self.language), pygame.Rect(949, 590 + i * 27, 418, 28), 22)
        if success:
            label = 'Prossima missione →' if MISSIONS.index(self.mission) + 1 < len(MISSIONS) else 'Tutte le missioni →'
            self.lab_button('next_mission', label, (932, 733, 452, 52), primary=True, size=21)
        else:
            label = ('Ricontrolla la sequenza' if self.review else 'Controlla la mia sequenza') if self.easy else ('Ricontrolla il mio codice' if self.review else 'Controlla il mio codice')
            self.lab_button('verify', label, (932, 733, 452, 52), primary=True, size=21)
        self.lab_button('trace_view', 'Guarda l’esecuzione passo per passo', (932, 798, 452, 35), size=16)

    def draw_case_goal(self):
        s, c = self.canvas, self.c
        self.lab_button('case:-1', '‹', (932, 499, 34, 35), active=len(self.mission.cases) > 1, size=24)
        self.lab_button('case:1', '›', (1350, 499, 34, 35), active=len(self.mission.cases) > 1, size=24)
        data = ', '.join(display(item, self.language) for item in self.case.inputs)
        label = f'{self.case_index + 1}/{len(self.mission.cases)} · ' + ('Dati del gioco: ' + data if data else 'Nessun dato da leggere')
        self.fitted(label, pygame.Rect(976, 499, 364, 35), 17)

    def draw_comparison(self):
        s, c = self.canvas, self.c
        rows = list(self.review.rows)
        # Put the first actionable mismatch in view, preserving relative order.
        rows.sort(key=lambda row: row.ok)
        self.result_scroll = min(self.result_scroll, max(0, len(rows) - 2))
        text(s, 'RICHIESTO', (932, 552), 12, c['muted'], True)
        text(s, 'OTTENUTO', (1168, 552), 12, c['muted'], True)
        for i, row in enumerate(rows[self.result_scroll:self.result_scroll + 2]):
            y = 575 + i * 59
            color = c['mint'] if row.ok else c['danger']
            text(s, ('OK · ' if row.ok else '× ') + row.label, (932, y), 15, color, True)
            self.fitted(row.expected, pygame.Rect(932, y + 23, 223, 29), 18)
            self.fitted(row.actual, pygame.Rect(1168, y + 23, 216, 29), 18, color)
        if len(rows) > 2:
            self.lab_button('results:-2', '↑', (1287, 692, 43, 29), active=self.result_scroll > 0, size=18)
            self.lab_button('results:2', '↓', (1341, 692, 43, 29), active=self.result_scroll + 2 < len(rows), size=18)
            text(s, f'Confronti {self.result_scroll + 1}–{min(self.result_scroll + 2, len(rows))} di {len(rows)}', (932, 698), 14, c['muted'])

    def draw_trace(self):
        """A secondary inspection view, distinct from submitting a game answer."""
        s, c = self.canvas, self.c
        veil = pygame.Surface((1440, 900), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 180))
        s.blit(veil, (0, 0))
        self.buttons = []
        panel(s, pygame.Rect(160, 88, 1120, 728), c['panel'], c['border'], 18)
        text(s, 'Dentro la tua sequenza', (190, 117), 31, c['text'], True)
        self.lab_button('close', 'Torna al gioco', (1048, 108, 203, 43), size=17)
        wrap(s, 'Segui una riga alla volta. Qui osservi l’esecuzione; “Controlla la mia sequenza” verifica la missione.', pygame.Rect(191, 177, 1046, 65), 21, c['muted'])
        self.trace_editor.draw(s, pygame.Rect(191, 261, 1048, 213), c, active=self.frame.line, error=self.error_line, readonly=True, size=23)
        self.draw_live_state(pygame.Rect(191, 503, 1048, 181))
        wrap(s, self.feedback if self.error_line else self.frame.message, pygame.Rect(191, 698, 735, 81), 18, c['danger'] if self.error_line else c['text'])
        self.lab_button('step', 'Esegui la prossima riga →', (929, 733, 312, 51), primary=True,
                        active=bool(self.frames) and self.frame_index + 1 < len(self.frames), size=18)

    def draw_quiz(self):
        s, c = self.canvas, self.c
        self.header('Scova l’equivoco · prevedi, controlla, capisci')
        text(s, self.quiz.title, (32, 112), 32, c['text'], True)
        wrap(s, 'Il computer esegue quello che legge. Prevedi il codice qui sotto, anche quando contiene un errore.', pygame.Rect(32, 165, 1350, 47), 21, c['muted'])
        for i, language in enumerate(LANGUAGES):
            self.lab_button('lang:' + language, language, (32 + i * 160, 215, 148, 34), selected=self.language == language, size=16)
        panel(s, pygame.Rect(32, 270, 852, 579), c['panel'], radius=16)
        panel(s, pygame.Rect(908, 270, 500, 579), c['panel'], radius=16)
        text(s, '1  LEGGI QUESTO PROGRAMMA', (55, 291), 17, c['mint'], True)
        self.code_rect = pygame.Rect(55, 334, 806, 258)
        self.editor.draw(s, self.code_rect, c, active=self.frame.line, error=self.error_line, readonly=True, size=24)
        self.draw_live_state(pygame.Rect(55, 612, 806, 155))
        self.lab_button('run', 'Pausa' if self.playing else 'Rivedi l’esecuzione', (55, 792, 332, 41), active=self.quiz_attempted, size=18)
        self.lab_button('details', 'Spiegazione completa', (400, 792, 461, 41), active=self.quiz_attempted, size=18)
        text(s, '2  SCEGLI LA PREVISIONE', (932, 291), 17, c['mint'], True)
        wrap(s, self.quiz.question, pygame.Rect(932, 338, 449, 93), 28, c['text'], True)
        correct = self.quiz.correct(self.language)
        for i, choice in enumerate(self.quiz.choices):
            selected = self.quiz_choice == i
            tone = ('mint' if i == correct else 'danger') if self.quiz_attempted and selected else None
            self.lab_button('answer:' + str(i), choice, (932, 440 + i * 66, 452, 56), selected=selected, tone=tone, size=21)
        if self.quiz_attempted:
            right = self.quiz_choice == correct
            text(s, 'Corretto.' if right else 'Da rivedere. Guarda il risultato.', (932, 654), 22, c['mint'] if right else c['danger'], True)
            wrap(s, self.quiz.explanation, pygame.Rect(932, 691, 452, 90), 19, c['text'])
        else:
            wrap(s, 'Seleziona una risposta e premi Controlla. Il risultato resta nascosto fino alla tua previsione.', pygame.Rect(932, 654, 452, 120), 20, c['muted'])
        self.lab_button('check', 'Controlla', (932, 792, 204, 41), primary=not self.quiz_attempted or self.quiz_choice != correct, active=self.quiz_choice is not None, size=19)
        self.lab_button('next_quiz', 'Prossimo equivoco →', (1148, 792, 236, 41), primary=self.quiz_attempted and self.quiz_choice == correct, size=17)
