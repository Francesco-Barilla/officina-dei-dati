"""Mission-aware instructions for the learner, distinct from computer actions."""
import ast
from dataclasses import dataclass
import re
from engine import assign, expression_source, generate, output, placeholder_index, set_var, source_line, type_name, value

STEPS = {
    'ordine': ('Mostra "Accendi".', 'Poi mostra "Chiudi portello".', 'Infine mostra "Decolla".'),
    'interi': ('Leggi le casse in casse, come int.', 'Aumenta casse di 2.', 'Mostra il nuovo valore di casse.'),
    'decimali': ('Leggi il decimale in carburante.', 'Aumenta carburante di 2.5.', 'Mostra il nuovo carburante.'),
    'testo': ('Leggi il testo nella variabile nome.', 'Crea saluto: "Ciao, " seguito da nome.', 'Mostra saluto.'),
    'booleani': ('Leggi il booleano in pronto.', 'Crea bloccato con il contrario di pronto.', 'Mostra bloccato.'),
    'confronto': ('Leggi peso come intero.', 'Crea leggero: vero se peso è al massimo 10.', 'Mostra leggero.'),
    'misti': ('Leggi moduli come intero.', 'Calcola lunghezza: 1.5 metri per modulo.', 'Mostra lunghezza come decimale.'),
    'divisione': ('Leggi energia come intero.', 'Calcola quota: la metà, conservando i decimali.', 'Mostra quota.'),
    'converti': ('Leggi le cifre nella stringa testo.', 'Converti testo in numero e aumenta numero di 2.', 'Mostra numero come valore numerico.'),
    'media': ('Leggi prima a, poi b: sono decimali.', 'Calcola la loro media nella variabile media.', 'Mostra media.'),
    'rettangolo': ('Leggi larghezza, poi altezza: sono int.', 'Calcola il loro prodotto nella variabile area.', 'Mostra area.'),
    'copia': ('Leggi energia e copiane il valore in prima.', 'Aumenta energia di 5; conserva la copia.', 'Mostra prima, poi energia.'),
    'scambio': ('Leggi a, poi b: sono int.', 'Scambia a e b, usando temp per salvare un valore.', 'Mostra prima a, poi b.'),
    'prima_dopo': ('Leggi contatore come int e mostralo.', 'Aumenta contatore di 1.', 'Mostra ancora contatore.'),
    'sovrascrivi': ('Leggi il testo in messaggio e mostralo.', 'Sostituisci messaggio con il testo "Pronto".', 'Mostra di nuovo messaggio.'),
    'sonda': ('Leggi nome, pezzi, carica, pronto, in ordine.', 'Aumenta pezzi di 1 e carica di 0.5.', 'Mostra nome, pezzi, carica, pronto, in ordine.'),
}


@dataclass(frozen=True)
class Gap:
    start: int
    end: int
    line: int
    kind: str
    target: str = ''


def first_gap(code, language='Python'):
    index = placeholder_index(code, language)
    if index < 0:
        return None
    left = code[code.rfind('\n', 0, index) + 1:index]
    target = re.search(r'([A-Za-z_]\w*)\s*=\s*$', left)
    return Gap(index, index + 3, code[:index].count('\n') + 1,
               'expression' if target else 'line' if not left.strip() else 'fragment', target.group(1) if target else '')


def meaningful_code(code):
    return '\n'.join(line for line in code.splitlines() if line.strip() and not line.lstrip().startswith(('#', '//'))).strip()


def writing_issue(code, language='Python'):
    body = meaningful_code(code)
    if not body:
        return 'La zona di scrittura è vuota. Premi Scrivi qui e inserisci le istruzioni, una per riga.'
    if first_gap(code, language):
        return 'Ci sono ancora dei ??? da completare. Premi Completa i ???: seleziono il punto in cui devi scrivere.'
    try:
        node = ast.parse(body, mode='eval').body
        if (isinstance(node, ast.Constant) or isinstance(node, ast.Name) and node.id in ('true', 'false') or
                isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)) and isinstance(node.operand, ast.Constant)):
            return 'Hai scritto un valore finale. Qui devi scrivere le istruzioni che leggono i dati, calcolano e mostrano il risultato.'
    except (SyntaxError, ValueError, RecursionError):
        pass
    return ''


def writing_task(mission, code, difficulty, language='Python'):
    gap = first_gap(code, language)
    if gap and difficulty == 'Medio':
        if gap.kind == 'expression':
            node = next((item for item in mission.instructions if item.target == gap.target and not item.kind), None)
            if node and re.fullmatch(r'[A-Za-z_]\w*', node.expression):
                prompt = f'Scrivi il nome della variabile da copiare in {gap.target}.'
            elif node and node.expression.startswith(('"', "'")):
                prompt = f'Scrivi il testo da assegnare a {gap.target}, tra virgolette.'
            else:
                prompt = f'Scrivi il calcolo che aggiorna {gap.target}, usando il suo valore attuale.'
            return prompt, 'Lascia il nome e = già presenti. Sostituisci soltanto i tre punti interrogativi.'
        if gap.kind == 'line':
            original = first_gap(mission.starter(language, 'Medio'), language)
            if original and original.kind == 'line' and original.line == gap.line:
                return f'Alla riga {gap.line} manca una stampa: scrivi l’istruzione intera.', 'Sostituisci ??? con il comando che mostra il valore richiesto dalla missione.'
            return f'Completa la riga {gap.line} con un’istruzione intera.', 'Leggi i tre passi della consegna e scrivi il comando mancante.'
        return 'Completa la parte segnata con ???.', 'Premi Completa i ??? e digita soltanto la parte mancante.'
    if not meaningful_code(code):
        return f'Scrivi il programma della missione, una istruzione per riga.', 'Premi Scrivi qui. Gli ingressi vengono dal gioco; il tuo codice deve leggerli.'
    return 'Continua il tuo programma, poi premi Controlla.', 'Scrivi qui porta il cursore alla fine della bozza. Puoi anche cliccare una riga per modificarla.'


def example_for(mission, language, code, difficulty):
    gap = first_gap(code, language)
    if difficulty == 'Medio' and gap:
        if gap.kind == 'expression':
            node = next((item for item in mission.instructions if item.target == gap.target and not item.kind), None)
            if node and re.fullmatch(r'[A-Za-z_]\w*', node.expression):
                return 'Esempio: per copiare il valore di origine, scrivi il suo nome.', ['origine']
            if node and node.expression.startswith(('"', "'")):
                return 'Esempio: per assegnare un testo, usa le virgolette.', ['"Salve"']
            return 'Esempio: per aumentare punti di 4, al posto di ??? scrivi:', ['punti + 4']
        return 'Esempio di stampa (usa il dato richiesto dalla tua missione):', [source_line(output('"Pronto"'), language)]
    special = {
        'converti': ('Esempio: trasforma il testo "12" nel numero 12.',
                     [set_var('cifre', 'string', '"12"'), set_var('risultato', 'int', 'int(cifre)'), output('risultato')]),
        'divisione': ('Esempio: metà di 7 è 3.5. Converti prima di dividere.',
                      [set_var('punti', 'int', '7'), set_var('parte', 'float', 'float(punti) / 2'), output('parte')]),
        'confronto': ('Esempio: verifica se un numero è al massimo 20.',
                      [set_var('numero', 'int', '12'), set_var('piccolo', 'bool', 'numero <= 20'), output('piccolo')]),
    }
    if mission.key in special:
        caption, instructions = special[mission.key]
        return caption, generate(instructions, language).splitlines()
    readers = [item for item in mission.instructions if item.expression.startswith('leggi_')]
    if not readers:
        return 'Esempio di sintassi: questa riga mostra il testo "Pronto".', [source_line(output('"Pronto"'), language)]
    kind = readers[0].kind
    name, expression = {'int': ('punti', 'punti + 4'), 'float': ('misura', 'misura + 1.5'),
                        'string': ('parola', 'unisci("Eco: ", parola)'), 'bool': ('segnale', 'not segnale')}[kind]
    instructions = [set_var(name, kind, readers[0].expression), assign(name, expression), output(name)]
    return 'Esempio di sintassi con altri nomi: adatta le righe alla missione.', generate(instructions, language).splitlines()


def mission_brief(mission, language, difficulty, code, case):
    title, instruction = writing_task(mission, code, difficulty, language)
    sections = [f'COSA SCRIVERE IN {language.upper()}\n{title}\n{instruction}' if difficulty != 'Facile' else
                'COSA FARE\nSposta le tessere: il programma deve eseguire le azioni elencate sotto, dall’alto verso il basso.']
    sections.append('LA CONSEGNA, IN TRE PASSI\n' + '\n'.join(f'{i + 1}. {step}' for i, step in enumerate(STEPS[mission.key])))
    reads = [item for item in mission.instructions if item.expression.startswith('leggi_')]
    if reads:
        sections.append('INGRESSI FORNITI DAL GIOCO\nNon devi digitare gli ingressi in un campo: ogni lettura prende il prossimo dato dell’esempio.\n' +
                        '\n'.join(f'{i + 1}. Per leggere {item.target}: {source_line(item, language)}' for i, item in enumerate(reads)))
    else:
        sections.append('INGRESSI\nQuesta missione usa testi già scritti nelle istruzioni. Non richiede letture.')
    defaults = {'int': 0, 'float': 0.0, 'string': '', 'bool': False}
    declarations = [(item.target, type_name(value(defaults[item.kind], 32), language)) for item in mission.instructions if item.kind]
    if declarations:
        sections.append('NOMI DA USARE\n' + '\n'.join(name + ' : ' + kind for name, kind in declarations) +
                        '\nLa verifica cerca questi nomi e questi tipi.' +
                        (' In JavaScript interi e decimali sono entrambi number.' if language == 'JavaScript' else ''))
    caption, sample = example_for(mission, language, code, difficulty)
    sections.append('COME SI SCRIVE\n' + caption + '\n' + '\n'.join(sample))
    references = {
        'converti': [('Da cifre in un testo a numero intero', 'int(cifre)')],
        'divisione': [('Da intero a decimale, prima della divisione', 'float(punti)'), ('Divisione con decimali', 'float(punti) / 2')],
        'testo': [('Unisci due testi', 'unisci("Ciao, ", persona)')],
        'booleani': [('Il contrario di un booleano', 'not segnale')],
        'confronto': [('Al massimo: minore o uguale', 'numero <= 20')],
        'media': [('Le parentesi fanno calcolare prima la somma', '(primo + secondo) / 2')],
        'rettangolo': [('Moltiplica due valori', 'base * lato')],
        'misti': [('Moltiplica usando un decimale', 'quantita * 1.5')],
    }
    operations = references.get(mission.key, [])
    if operations:
        sections.append('IL COMANDO UTILE IN QUESTA SFIDA\nGli esempi usano altri nomi: sostituiscili con quelli della consegna.\n' +
                        '\n'.join(label + ': ' + expression_source(expression, language) for label, expression in operations))
    check = 'Controlla la mia sequenza' if difficulty == 'Facile' else 'Controlla il mio codice'
    sections.append(f'QUANDO SEI PRONTO\nPremi {check}. Il controllo usa tutti gli esempi della missione. Correggi le righe indicate e riprova.\n' +
                    ('In Python vai a capo dopo ogni istruzione.' if language == 'Python' else 'Termina ogni istruzione con ; e poi vai a capo.') +
                    '\nQui bastano le istruzioni: il laboratorio prepara già l’ambiente di esecuzione.\nI comandi leggi_* sono aiuti didattici del simulatore.')
    return '\n\n'.join(sections)
