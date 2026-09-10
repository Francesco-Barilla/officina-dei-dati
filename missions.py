"""Original challenges: finite cases and independently specified outcomes."""
from dataclasses import dataclass
import math
from engine import CodeError, Value, assign as a, execute, generate, output as o, set_var as s, value

DIFFICULTIES = ('Facile', 'Medio', 'Difficile')
GROUPS = ('Tutte', 'Primi passi', 'Dati e calcoli', 'Testo e logica', 'Ordine e memoria')


@dataclass(frozen=True)
class Case:
    label: str
    inputs: tuple


def c(label, *inputs):
    return Case(label, tuple(value(item) for item in inputs))


@dataclass(frozen=True)
class Mission:
    key: str
    title: str
    subtitle: str
    group: str
    objective: str
    concept: str
    trap: str
    instructions: tuple
    cases: tuple
    expected: object

    def solution(self, language):
        return generate(self.instructions, language)

    def starter(self, language, difficulty):
        comment = '# ' if language == 'Python' else '// '
        if difficulty == 'Difficile':
            return comment + 'Costruisci il programma. Ingressi e comandi sono nella scheda Dati e comandi.\n'
        lines = self.solution(language).splitlines()
        # One missing calculation/output; leave dependencies visible.
        index = next((i for i, node in enumerate(self.instructions) if node.target and not node.kind), len(lines) - 1)
        if '=' in lines[index]:
            lines[index] = lines[index].split('=', 1)[0] + '= ???' + ('' if language == 'Python' else ';')
        else:
            lines[index] = '???'
        return '\n'.join(lines) + '\n'


MISSIONS = (
    Mission('ordine', '01 · Prima questo, poi quello', 'Le uscite seguono l’ordine scritto.', 'Primi passi',
        'Prepara la sonda: mostra prima "Accendi", poi "Chiudi portello", infine "Decolla". Ogni istruzione deve essere eseguita una volta.',
        'Una sequenza esegue le istruzioni dall’alto verso il basso. Nessuna viene scelta o ripetuta automaticamente.',
        'Il computer non riordina le azioni in base al loro significato: Decolla scritto prima viene eseguito prima.',
        (o('"Accendi"'), o('"Chiudi portello"'), o('"Decolla"')), (c('Preparazione della sonda'),),
        lambda x: ({}, ['Accendi', 'Chiudi portello', 'Decolla'])),
    Mission('interi', '02 · Il carico aumenta', 'int: conta oggetti interi.', 'Primi passi',
        'Leggi il numero intero di casse, memorizzalo in casse, aggiungi 2 e mostra il nuovo totale.',
        'casse = casse + 2 legge il valore attuale, calcola il risultato e sostituisce il contenuto di casse.',
        '= non è un’uguaglianza matematica: le due casse ai lati hanno ruoli diversi, destinazione e valore da leggere.',
        (s('casse', 'int', 'leggi_intero()'), a('casse', 'casse + 2'), o('casse')),
        (c('Stiva vuota', 0), c('Tre casse', 3), c('Una cassa', 1), c('Carico grande', 12), c('Cinque casse', 5)),
        lambda x: ({'casse': x[0] + 2}, [x[0] + 2])),
    Mission('decimali', '03 · Un pieno con la virgola', 'float: misura quantità frazionarie.', 'Primi passi',
        'Leggi il carburante decimale in litri. Memorizzalo in carburante, aggiungi 2.5 litri e mostra il risultato.',
        'float rappresenta numeri con parte frazionaria. Nel codice il separatore decimale è il punto: 2.5.',
        '2.5 non è 25 e non è il testo "2.5". La virgola nel codice non sostituisce il punto decimale.',
        (s('carburante', 'float', 'leggi_decimale()'), a('carburante', 'carburante + 2.5'), o('carburante')),
        (c('Serbatoio vuoto', 0.0), c('Un litro e mezzo', 1.5), c('Quasi pieno', 7.25), c('Poco carburante', .5), c('Riserva', 3.0)),
        lambda x: ({'carburante': x[0] + 2.5}, [x[0] + 2.5])),
    Mission('testo', '04 · Il saluto della sonda', 'string: conserva testo, anche cifre.', 'Primi passi',
        'Leggi il nome come testo, prepara saluto unendo "Ciao, " e nome, poi mostra saluto. Lo spazio dopo la virgola fa parte del testo.',
        'Una stringa è testo tra virgolette. Unire stringhe costruisce un testo nuovo; non esegue calcoli sulle cifre contenute.',
        '"nome" è una parola fissa; nome senza virgolette legge la variabile. Anche "0" è una stringa.',
        (s('nome', 'string', 'leggi_testo()'), s('saluto', 'string', 'unisci("Ciao, ", nome)'), o('saluto')),
        (c('Pilota Ada', 'Ada'), c('Pilota Leo', 'Leo'), c('Nome numerico', '007'), c('Nome vuoto', ''), c('Nome breve', 'Io')),
        lambda x: ({'nome': x[0], 'saluto': 'Ciao, ' + x[0]}, ['Ciao, ' + x[0]])),
    Mission('booleani', '05 · Pronto oppure no', 'bool: vero e falso sono valori.', 'Testo e logica',
        'Leggi pronto come booleano. Memorizza in bloccato la negazione di pronto, poi mostra bloccato. Qui non serve un if.',
        'Una variabile bool conserva un valore logico. NOT calcola il contrario e può essere usato anche in una semplice assegnazione.',
        'Il testo "false" non è il booleano false. Calcolare un booleano non obbliga a usare una selezione.',
        (s('pronto', 'bool', 'leggi_booleano()'), s('bloccato', 'bool', 'not pronto'), o('bloccato')),
        (c('Sonda pronta', True), c('Sonda non pronta', False)),
        lambda x: ({'pronto': x[0], 'bloccato': not x[0]}, [not x[0]])),
    Mission('confronto', '06 · Un risultato logico', 'Un confronto produce un bool.', 'Testo e logica',
        'Leggi il peso intero. Calcola leggero: è vero quando peso <= 10. Mostra leggero senza usare if.',
        'Il confronto restituisce vero o falso, che puoi memorizzare e mostrare come qualunque altro dato.',
        '<= include il confine 10. L’assegnazione memorizza il risultato del confronto, non la formula da ricalcolare per sempre.',
        (s('peso', 'int', 'leggi_intero()'), s('leggero', 'bool', 'peso <= 10'), o('leggero')),
        (c('Sotto il limite', 9), c('Sul limite', 10), c('Sopra il limite', 11), c('Vuoto', 0), c('Pesante', 25)),
        lambda x: ({'peso': x[0], 'leggero': x[0] <= 10}, [x[0] <= 10])),
    Mission('misti', '07 · Dal conteggio alla misura', 'Un calcolo può produrre un float.', 'Dati e calcoli',
        'Leggi il numero intero di moduli. Ogni modulo misura 1.5 metri. Calcola lunghezza come float e mostrala.',
        'Il prodotto di un intero per una quantità decimale può avere una parte frazionaria: scegli un tipo capace di conservarla.',
        'Un intero in ingresso non obbliga tutti i risultati a restare interi. JavaScript usa number per entrambe le categorie.',
        (s('moduli', 'int', 'leggi_intero()'), s('lunghezza', 'float', 'moduli * 1.5'), o('lunghezza')),
        (c('Un modulo', 1), c('Tre moduli', 3), c('Nessun modulo', 0), c('Due moduli', 2), c('Otto moduli', 8)),
        lambda x: ({'moduli': x[0], 'lunghezza': x[0] * 1.5}, [x[0] * 1.5])),
    Mission('divisione', '08 · Dividere senza perdere pezzi', 'La conversione va fatta prima.', 'Dati e calcoli',
        'Leggi energia come intero. Calcola quota come metà reale dell’energia, conservando anche .5. Converti prima della divisione quando necessario.',
        'In C e Java due interi si dividono con troncamento. Convertire un operando prima di / permette una divisione decimale.',
        'Mettere il risultato intero in una variabile float non recupera la parte già persa. Python / e JavaScript / eseguono invece la divisione reale.',
        (s('energia', 'int', 'leggi_intero()'), s('quota', 'float', 'float(energia) / 2'), o('quota')),
        (c('Energia dispari', 5), c('Energia pari', 8), c('Una unità', 1), c('Zero', 0), c('Sette unità', 7)),
        lambda x: ({'energia': x[0], 'quota': x[0] / 2}, [x[0] / 2])),
    Mission('converti', '09 · Il numero dentro il testo', 'Converti prima di calcolare.', 'Testo e logica',
        'Leggi testo, che contiene cifre di un intero. Converti in numero, aggiungi 2 a numero e mostra il risultato numerico.',
        'Leggere cifre come testo e leggerle come numero sono operazioni diverse. Una conversione esplicita prepara il dato per il calcolo.',
        '"5" + 2 non significa sempre 7: Java e JavaScript concatenano; Python richiede una conversione. Le funzioni di conversione differiscono tra linguaggi.',
        (s('testo', 'string', 'leggi_testo()'), s('numero', 'int', 'int(testo)'), a('numero', 'numero + 2'), o('numero')),
        (c('Cinque scritto', '5'), c('Zero scritto', '0'), c('Numero negativo', '-3'), c('Due cifre', '12'), c('Con zeri iniziali', '007')),
        lambda x: ({'testo': x[0], 'numero': int(x[0]) + 2}, [int(x[0]) + 2])),
    Mission('media', '10 · La temperatura media', 'Le parentesi organizzano il calcolo.', 'Dati e calcoli',
        'Leggi prima a e poi b, due temperature decimali. Memorizza media come (a + b) / 2 e mostrala.',
        'Le istruzioni hanno un ordine; anche gli operatori dentro un’espressione hanno una precedenza. Le parentesi rendono esplicita la somma da dividere.',
        'a + b / 2 divide soltanto b. Il computer non indovina che volevi la media dei due valori.',
        (s('a', 'float', 'leggi_decimale()'), s('b', 'float', 'leggi_decimale()'), s('media', 'float', '(a + b) / 2.0'), o('media')),
        (c('Due sensori', 10.0, 20.0), c('Valori uguali', 7.5, 7.5), c('Sopra e sotto zero', -2.0, 8.0), c('Mezza unità', 1.0, 2.0), c('Zero iniziale', 0.0, 10.0)),
        lambda x: ({'a': x[0], 'b': x[1], 'media': (x[0] + x[1]) / 2}, [(x[0] + x[1]) / 2])),
    Mission('rettangolo', '11 · Costruisci il pannello', 'Gli ingressi hanno un ordine.', 'Dati e calcoli',
        'Il primo ingresso è larghezza, il secondo altezza: entrambi int. Calcola area moltiplicandoli e mostra area.',
        'Ogni lettura consuma il prossimo dato della fila. Una variabile può essere usata dopo che ha ricevuto un valore.',
        'Scambiare le due letture conserva il prodotto, ma scambia il significato di larghezza e altezza. La verifica controlla anche la memoria.',
        (s('larghezza', 'int', 'leggi_intero()'), s('altezza', 'int', 'leggi_intero()'), s('area', 'int', 'larghezza * altezza'), o('area')),
        (c('Pannello lungo', 3, 5), c('Pannello alto', 2, 7), c('Quadrato', 4, 4), c('Una striscia', 1, 9), c('Area nulla', 0, 6)),
        lambda x: ({'larghezza': x[0], 'altezza': x[1], 'area': x[0] * x[1]}, [x[0] * x[1]])),
    Mission('copia', '12 · Una fotografia del valore', 'Una copia non segue gli aggiornamenti.', 'Ordine e memoria',
        'Leggi energia int, copiala in prima, poi aggiungi 5 a energia. Mostra prima e poi energia.',
        'prima = energia prende il valore in quell’istante. Aggiornare energia dopo non cambia la copia già memorizzata.',
        'L’assegnazione non crea un collegamento permanente tra le due variabili. Questo vale per i valori semplici usati qui.',
        (s('energia', 'int', 'leggi_intero()'), s('prima', 'int', 'energia'), a('energia', 'energia + 5'), o('prima'), o('energia')),
        (c('Prima e dopo', 10), c('Partenza da zero', 0), c('Una unità', 1), c('Riserva', 25), c('Valore negativo', -2)),
        lambda x: ({'prima': x[0], 'energia': x[0] + 5}, [x[0], x[0] + 5])),
    Mission('scambio', '13 · Scambia le due casse', 'Una variabile temporanea salva il dato.', 'Ordine e memoria',
        'Leggi a e poi b, due int. Scambia i loro valori usando temp e mostra a, poi b. Il vecchio a non deve andare perso.',
        'Salva a in temp, copia b in a, infine copia temp in b. Ogni istruzione usa la memoria lasciata dalla precedente.',
        'a = b seguito da b = a non scambia: il vecchio valore di a è già stato sovrascritto.',
        (s('a', 'int', 'leggi_intero()'), s('b', 'int', 'leggi_intero()'), s('temp', 'int', 'a'), a('a', 'b'), a('b', 'temp'), o('a'), o('b')),
        (c('Casse diverse', 2, 9), c('Valori invertiti', 9, 2), c('Con zero', 0, 5), c('Valori uguali', 4, 4), c('Valore negativo', -3, 8)),
        lambda x: ({'a': x[1], 'b': x[0], 'temp': x[0]}, [x[1], x[0]])),
    Mission('prima_dopo', '14 · Lo schermo ricorda', 'Un’uscita non cambia retroattivamente.', 'Ordine e memoria',
        'Leggi contatore int. Mostralo, aggiungi 1 al contatore e mostralo di nuovo. Sullo schermo devono restare entrambi i valori, in ordine.',
        'L’uscita registra il valore al momento della stampa. Un’assegnazione successiva aggiorna la memoria, non il testo già apparso.',
        'Spostare la prima uscita dopo l’incremento cambia ciò che si vede. Non basta usare gli stessi comandi.',
        (s('contatore', 'int', 'leggi_intero()'), o('contatore'), a('contatore', 'contatore + 1'), o('contatore')),
        (c('Contatore a quattro', 4), c('Contatore a zero', 0), c('Dieci', 10), c('Valore negativo', -1), c('Novantanove', 99)),
        lambda x: ({'contatore': x[0] + 1}, [x[0], x[0] + 1])),
    Mission('sovrascrivi', '15 · L’ultima assegnazione', 'La memoria cambia, il passato resta.', 'Ordine e memoria',
        'Leggi messaggio come stringa e mostralo. Poi assegna "Pronto" a messaggio e mostralo di nuovo.',
        'Assegnare un nuovo valore sostituisce il contenuto della variabile. Lo schermo conserva le uscite precedenti.',
        'La variabile non accumula automaticamente vecchio e nuovo testo. Per unirli servirebbe un’operazione esplicita.',
        (s('messaggio', 'string', 'leggi_testo()'), o('messaggio'), a('messaggio', '"Pronto"'), o('messaggio')),
        (c('In avvio', 'Avvio'), c('Stringa vuota', ''), c('Testo false', 'false'), c('Numero scritto', '0'), c('In attesa', 'Attesa')),
        lambda x: ({'messaggio': 'Pronto'}, [x[0], 'Pronto'])),
    Mission('sonda', '16 · Una sonda, quattro tipi', 'Tutti i dati sullo stesso nastro.', 'Ordine e memoria',
        'Leggi nell’ordine: nome string, pezzi int, carica float, pronto bool. Aumenta pezzi di 1, carica di 0.5 e mostra nome, pezzi, carica, pronto.',
        'Una sequenza può combinare tipi diversi. Ogni dato mantiene il proprio ruolo e ogni istruzione usa lo stato attuale della memoria.',
        'Il tipo dipende dal valore e dal linguaggio, non dal nome scelto. Una stringa di cifre non diventa un numero da sola.',
        (s('nome', 'string', 'leggi_testo()'), s('pezzi', 'int', 'leggi_intero()'), s('carica', 'float', 'leggi_decimale()'), s('pronto', 'bool', 'leggi_booleano()'),
         a('pezzi', 'pezzi + 1'), a('carica', 'carica + 0.5'), o('nome'), o('pezzi'), o('carica'), o('pronto')),
        (c('Sonda Ada', 'Ada', 2, 3.5, True), c('Sonda Leo', 'Leo', 0, 0.0, False), c('Nome numerico', '007', 3, 1.25, True), c('In attesa', 'Io', 8, 7.5, False), c('Stringa vuota', '', 1, .5, True)),
        lambda x: ({'nome': x[0], 'pezzi': x[1] + 1, 'carica': x[2] + .5, 'pronto': x[3]}, [x[0], x[1] + 1, x[2] + .5, x[3]])),
)
BY_KEY = {mission.key: mission for mission in MISSIONS}


@dataclass
class Review:
    success: bool
    message: str
    passed: int
    total: int
    case: object = None


def same(actual, expected, language):
    item = value(expected)
    if item.kind == 'float':
        return actual.kind in ('int', 'float') and math.isclose(actual.data, expected, rel_tol=2e-6, abs_tol=2e-6) and (language == 'JavaScript' or actual.kind == 'float')
    return actual.kind == item.kind and actual.data == expected


def validate(mission, code, language):
    passed, first = 0, None
    for case in mission.cases:
        try:
            execution = execute(code, case.inputs, language)
            if execution.error:
                raise execution.error
            frame = execution.frames[-1]
            memory, outputs = mission.expected([item.data for item in case.inputs])
            actual = dict(frame.memory)
            okay = frame.consumed == len(case.inputs) and len(frame.outputs) == len(outputs)
            okay = okay and all(name in actual and same(actual[name], expected, language) for name, expected in memory.items())
            okay = okay and all(same(item, expected, language) for item, expected in zip(frame.outputs, outputs))
            if okay:
                passed += 1
            elif first is None:
                first = (case, 'Le uscite, il loro ordine, i tipi o i valori finali in memoria non corrispondono alla consegna.')
        except CodeError as error:
            if first is None:
                first = (case, f'Riga {error.line}: {error}')
    total = len(mission.cases)
    if first:
        return Review(False, f'{passed}/{total} casi riusciti. Caso da ricontrollare: {first[0].label}.\n{first[1]}', passed, total, first[0])
    return Review(True, f'Nastro collaudato: {total}/{total} casi riusciti! Hai controllato ingressi, memoria e uscite. Prova la prossima missione.', passed, total)
