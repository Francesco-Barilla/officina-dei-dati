"""Keep local drafts and progress independent of the other laboratories."""
import json
import os
from pathlib import Path
import sys
from engine import LANGUAGES, MAX_CODE
from missions import BY_KEY, DIFFICULTIES


def data_path():
    return (Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent) / 'progressi_sequenza.json'


def defaults():
    return dict(language='Python', difficulty='Facile', theme='Notte', size=19, speed=1, mission='ordine', completed=[], quizzes=[], drafts={}, orders={})


def load(path=None):
    state = defaults()
    try:
        incoming = json.loads(Path(path or data_path()).read_text(encoding='utf-8'))
        if not isinstance(incoming, dict):
            raise ValueError()
        for name, options in [('language', LANGUAGES), ('difficulty', DIFFICULTIES), ('theme', ('Notte', 'Giorno', 'Contrasto')), ('size', (17, 19, 21)), ('speed', (.5, 1, 2, 3)), ('mission', BY_KEY)]:
            raw = incoming.get(name)
            if raw in options and not (name in ('size', 'speed') and isinstance(raw, bool)):
                state[name] = raw
        for name in ('completed', 'quizzes'):
            if isinstance(incoming.get(name), list):
                state[name] = list(dict.fromkeys(item for item in incoming[name][:1000] if isinstance(item, str)))
        if isinstance(incoming.get('drafts'), dict):
            state['drafts'] = {key: text for key, text in list(incoming['drafts'].items())[:300] if isinstance(key, str) and isinstance(text, str) and len(text) <= MAX_CODE}
        if isinstance(incoming.get('orders'), dict):
            for key, order in incoming['orders'].items():
                if key in BY_KEY and isinstance(order, list) and all(type(index) is int for index in order) and sorted(order) == list(range(len(BY_KEY[key].instructions))):
                    state['orders'][key] = order
        return state, ''
    except FileNotFoundError:
        return state, ''
    except (OSError, TypeError, ValueError):
        return state, 'Salvataggio non leggibile: puoi continuare con una nuova sessione.'


def save(state, path=None):
    path = Path(path or data_path())
    temp = path.with_suffix('.tmp')
    try:
        temp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')
        os.replace(temp, path)
        return ''
    except OSError:
        return 'Non riesco a salvare qui. Estrai il programma in una cartella personale scrivibile.'
