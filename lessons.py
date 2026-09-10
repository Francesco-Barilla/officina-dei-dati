"""Short teaching prompts and predictions tied to observable mistakes."""
from dataclasses import dataclass
from engine import assign as a, generate, output as o, set_var as s
from missions import c

HOW_TO_PLAY = '''IMPARA FACENDO
Leggi gli ingressi e la riga evidenziata. Prevedi il prossimo valore, indicando anche il suo tipo. La sonda percorre il nastro e mostra cosa è cambiato in memoria o sullo schermo. Una risposta errata aggiunge un indizio: puoi riprovare. Dopo l’osservazione scegli Prossima previsione. Cambia gli ingressi per mettere alla prova la stessa regola.

GIOCA · FACILE
Le istruzioni sono mescolate. Clicca una tessera e poi un’altra per scambiarle, oppure usa le frecce della tessera selezionata. Leggi prima la consegna: possono esistere più ordini corretti. Esegui mostra il risultato sul caso visibile. Verifica tutte le sonde controlla anche gli altri casi, le variabili richieste, i tipi e l’ordine delle uscite.

GIOCA · MEDIO E DIFFICILE
Medio propone codice da completare nei punti ???. Difficile offre una pagina da scrivere. Il comando Dati e comandi rimane disponibile. Esegui, Pausa, Un passo e Ricomincia permettono di vedere lo stato dopo ogni istruzione. Un programma errato non viene premiato.

IL BANCO DEI TIPI
Scegli int, float, string o bool; scrivi un valore e osserva il contenuto della cella. Prova 5 come intero e come stringa, oppure false come booleano e come testo. Il codice mostra la rappresentazione nel linguaggio scelto.

SCOVA L’EQUIVOCO
Qui devi prevedere il codice mostrato, anche se contiene un errore. Solo dopo la risposta parte la traccia. La spiegazione collega il risultato all’ordine e ai dati effettivi.

Non c’è un cronometro. Le sfide sono tutte accessibili. Aprire una scheda, le impostazioni o il banco mette in pausa il nastro. Le bozze sono separate per missione, lingua e difficoltà; consultare una soluzione non le sostituisce e non assegna completamenti.'''

TYPES_NOTES = '''INT · CONTARE
Un intero rappresenta quantità senza parte frazionaria: -3, 0, 12. Le virgolette cambiano il significato: "12" è testo. I nomi della variabile non ne stabiliscono il tipo.

FLOAT · MISURARE
Un decimale usa il punto nel codice: 3.5. Molti decimali sono rappresentati in modo approssimato in binario; non tutti i calcoli risultano esatti. Qui Python float e JavaScript number usano valori a 64 bit; le variabili float di C e Java usano 32 bit. Il suffisso f dei letterali C/Java dichiara un float. Un risultato mostrato con poche cifre può nascondere l’approssimazione interna.

STRING · CONSERVARE TESTO
"Ada", "5", "false" e "" sono stringhe. Il testo vuoto contiene zero caratteri. Unire testi concatena; convertire un testo numerico permette di calcolare sul suo valore. C non ha un tipo string incorporato: qui usiamo const char * per testi di sola lettura.

BOOL · CONSERVARE UNA RISPOSTA LOGICA
True/False in Python, true/false in JavaScript e Java. In C11 bool, true e false sono forniti da stdbool.h. Qui il simulatore li predispone. Un confronto come peso <= 10 può essere memorizzato in un bool senza scrivere if.

I LINGUAGGI NON SONO IDENTICI
JavaScript usa number per interi e decimali: int e float sono categorie didattiche, non due tipi nativi diversi. Python usa int, float, str e bool; una nuova assegnazione può cambiare il tipo del valore associato al nome. In C e Java il tipo dichiarato della variabile rimane fisso.

DIVIDERE E CONVERTIRE
5 / 2 produce 2.5 in Python e JavaScript. In C e Java, se entrambi gli operandi sono int, il risultato è 2. La conversione di un operando deve avvenire prima della divisione per conservare .5. Convertire dopo non recupera la parte persa. In C l’assegnazione di un float a un int tronca verso zero; in Java serve un cast esplicito. Queste sfide richiedono di conservare i tipi indicati.

NEL BANCO STAI SCRIVENDO UN VALORE
Scegliere bool e scrivere false inserisce il valore logico falso. Non è la conversione di una stringa tramite bool("false") o Boolean("false"): un testo non vuoto in questi casi produce vero. Presenza del testo e significato della parola sono concetti diversi.'''

MISCONCEPTIONS = '''= NON È ==
L’assegnazione legge la parte destra e aggiorna la destinazione a sinistra. Un confronto == produce invece un valore logico.

LE ISTRUZIONI NON AVVENGONO INSIEME
Ogni riga trova la memoria lasciata dalla riga precedente. Un’istruzione usa soltanto dati già disponibili.

LA COPIA NON È UN COLLEGAMENTO
b = a conserva il valore di a in quel momento. Con i valori semplici delle missioni, modificare a dopo non modifica b.

LO SCHERMO NON SI AGGIORNA DA SOLO
Una stampa registra il valore attuale. Le assegnazioni successive non riscrivono le uscite precedenti.

UN NOME NON È UN TESTO
nome legge la variabile. "nome" rappresenta quei quattro caratteri.

IL TIPO NON DIPENDE DAL NOME
Una variabile chiamata numero può contenere testo. Guarda il valore e, nei linguaggi con dichiarazioni, il tipo dichiarato.

I DECIMALI NON SONO SEMPRE ESATTI
float è una rappresentazione numerica finita. Nel laboratorio si verificano i risultati decimali con una piccola tolleranza, senza arrotondarli a interi.

UNO SCAMBIO RICHIEDE DI SALVARE IL VECCHIO VALORE
a = b; b = a; sovrascrive a prima di salvarlo. temp conserva il dato che altrimenti andrebbe perso.

SEQUENZA NON SIGNIFICA RIPETIZIONE
Il programma passa una volta per ogni istruzione scritta. Rigiocare con altri ingressi avvia un’altra esecuzione.'''


def commands_text(language):
    return '''INGRESSI DELLA SIMULAZIONE
leggi_intero(), leggi_decimale(), leggi_testo(), leggi_booleano() leggono il prossimo dato della fila. La tessera indica il tipo atteso. Sono comandi didattici dell’officina, predisposti dal simulatore: non funzioni standard dei quattro linguaggi. Nel programma reale l’input dipende dall’ambiente.

USCITA
Python: print(valore)
JavaScript: console.log(valore);
Java: System.out.println(valore);
C: mostra(valore); — comando didattico che visualizza anche il tipo. In un programma C reale occorrono formati adeguati, per esempio con printf.

TESTI E CONVERSIONI
In Python, JavaScript e Java + unisce due testi. In C usa unisci(testo_a, testo_b): è un aiuto del simulatore. Per leggere un intero da un testo: int(testo) in Python, parseInt(testo, 10) in JavaScript, atoi(testo) in C e Integer.parseInt(testo) in Java. Le missioni forniscono stringhe numeriche valide; queste funzioni non hanno la stessa gestione dei testi non validi.
Per un numero decimale: float(numero) in Python, Number(numero) in JavaScript, (float)(numero) in C e Java. Per trasformare un valore in testo: str, String, testo (aiuto C), String.valueOf, rispettivamente.

FRAMMENTI ACCETTATI
Una assegnazione o uscita per istruzione. In C/Java dichiara il tipo alla prima assegnazione; in JavaScript usa let o const. Qui JavaScript è trattato in ambito rigoroso: le variabili vanno dichiarate. Nel programma reale alcune sintassi aggiuntive sono valide, ma fuori dal sottoinsieme del laboratorio.
Sono disponibili +, -, *, /, confronti singoli, negazione e AND/OR; parentesi, numeri, testi, booleani. Non si simulano assegnazioni multiple, array, oggetti, puntatori, cicli, if, import o funzioni scritte dallo studente. I testi C restano di sola lettura. Scrivi una sola lettura per istruzione per rendere esplicito l’ordine degli ingressi.

LIMITI
8000 caratteri, 80 righe, 32 istruzioni, 8 variabili, testi di 200 caratteri, numeri finiti tra -10000000 e 10000000. I tempi dell’animazione servono alla lettura, non misurano la velocità del linguaggio. La verifica riguarda i casi dichiarati nella missione: non è una prova su tutti i numeri possibili.
\n\nTIPI\n''' + TYPES_NOTES


@dataclass(frozen=True)
class Quiz:
    key: str
    title: str
    instructions: tuple
    question: str
    choices: tuple
    answer: object
    explanation: str

    def source(self, language):
        return generate(self.instructions, language)

    def correct(self, language):
        return self.answer(language) if callable(self.answer) else self.answer


QUIZZES = (
    Quiz('assegna', 'Una strana uguaglianza?', (s('x', 'int', '2'), a('x', 'x + 1'), o('x')), 'Che cosa appare sullo schermo?', ('3: leggo 2 e aggiungo 1', 'Errore: x non può essere uguale a x + 1', '2: il nome non cambia'), 0, '= assegna un nuovo valore. La parte destra usa il vecchio 2, poi x riceve 3.'),
    Quiz('copia', 'La copia segue l’originale?', (s('a', 'int', '2'), s('b', 'int', 'a'), a('a', '5'), o('b')), 'Quanto vale b alla fine?', ('5: segue a', '2: conserva il valore copiato', '7: accumula i valori'), 1, 'b riceve 2 prima che a cambi. Non è un collegamento permanente.'),
    Quiz('uscite', 'Due fotografie sullo schermo', (s('x', 'int', '2'), o('x'), a('x', 'x + 1'), o('x')), 'Quali uscite restano, in ordine?', ('3 e 3', 'Soltanto 3', '2 e 3'), 2, 'La prima uscita registra 2. L’aggiornamento cambia x, non la prima uscita.'),
    Quiz('cifre', 'Cifre tra virgolette', (s('codice', 'string', '"5"'), o('codice')), 'Quale tipo di valore contiene codice?', ('int', 'string: il testo "5"', 'bool'), 1, 'Le virgolette costruiscono un testo. Avere l’aspetto di un numero non basta a renderlo numerico.'),
    Quiz('false', 'La parola e il valore', (s('pronto', 'bool', 'False'), o('pronto')), 'Che cosa contiene pronto?', ('Il booleano falso', 'La stringa "false"', 'Una variabile vuota'), 0, 'False/false è un valore logico. Non servono virgolette e non significa che la variabile sia vuota.'),
    Quiz('divisione', 'Cinque diviso due', (s('a', 'int', '5'), s('b', 'int', '2'), s('quota', 'float', 'a / b'), o('quota')), 'Nel linguaggio scelto, quale valore appare?', ('2.5', '2.0', 'Sempre un errore'), lambda language: 1 if language in ('C', 'Java') else 0, 'In C/Java la divisione int/int produce prima 2, poi la variabile float riceve 2.0. Python e JavaScript producono 2.5.'),
    Quiz('tardi', 'Convertire dopo è troppo tardi?', (s('a', 'int', '5'), s('b', 'int', '2'), s('quota', 'float', 'float(a / b)'), o('quota')), 'La conversione esterna recupera .5?', ('Sì, sempre 2.5', 'In C/Java resta 2.0; negli altri è 2.5', 'Converte in stringa'), 1, 'Le parentesi fanno calcolare a / b prima della conversione. In C/Java la parte frazionaria è già persa.'),
    Quiz('parentesi', 'Era davvero una media?', (s('a', 'float', '10.0'), s('b', 'float', '20.0'), s('media', 'float', 'a + b / 2.0'), o('media')), 'Il programma mostra 15 oppure 20?', ('15: somma e divide', '20: divide soltanto b', '30: ignora la divisione'), 1, '/ precede +. Prima 20 / 2 = 10, poi 10 + 10 = 20. Per la media servono parentesi attorno ad a + b.'),
    Quiz('scambio', 'Uno scambio senza salvataggio', (s('a', 'int', '2'), s('b', 'int', '9'), a('a', 'b'), a('b', 'a'), o('a'), o('b')), 'Quali valori vengono mostrati?', ('9 e 2', '2 e 9', '9 e 9'), 2, 'La prima copia sovrascrive a con 9. La seconda legge quel nuovo 9. Il vecchio 2 è perso.'),
    Quiz('ultima', 'Chi resta nella cella?', (s('x', 'int', '3'), a('x', '8'), o('x')), 'Qual è il valore finale?', ('3', '8', '11'), 1, 'L’ultima assegnazione sostituisce il valore precedente. Non somma automaticamente.'),
    Quiz('nome', 'Nome o contenuto?', (s('nome', 'string', '"Ada"'), o('"nome"')), 'Che cosa viene mostrato?', ('Ada', 'Il testo nome', 'Niente'), 1, 'Le virgolette indicano un testo letterale. Senza virgolette verrebbe letto il contenuto di nome.'),
    Quiz('float', 'Un valore frazionario', (s('litri', 'float', '2.5'), o('litri')), 'Quale valore conserva litri?', ('2, perché conta litri interi', '25, senza separatore', '2.5: due litri e mezzo'), 2, 'Il tipo numerico decimale conserva la parte frazionaria. In C/Java il suffisso f identifica il letterale float.'),
    Quiz('number', 'Quattro linguaggi, stessi nomi?', (s('a', 'int', '2'), s('b', 'float', '2.0'), o('a'), o('b')), 'int e float sono due tipi nativi distinti anche in JavaScript?', ('Sì, in tutti e quattro', 'No: JavaScript usa number per entrambi', 'No: JavaScript usa string'), 1, 'Le categorie didattiche intero/decimale non introducono tipi che il linguaggio non possiede. JavaScript usa number.'),
    Quiz('confronto', 'La risposta si ricalcola da sola?', (s('peso', 'int', '9'), s('leggero', 'bool', 'peso <= 10'), a('peso', '20'), o('leggero')), 'Alla fine leggero è ancora vero?', ('Sì: il confronto era stato calcolato con 9', 'No: segue automaticamente peso', 'Non si può memorizzare un confronto'), 0, 'L’assegnazione conserva il risultato vero. Per aggiornarlo occorre eseguire di nuovo il confronto e assegnarlo.'),
    Quiz('stampa', 'Mostrare consuma il dato?', (s('x', 'int', '2'), o('x'), o('x')), 'Quali uscite si ottengono?', ('2 e 3', '2 e poi niente', '2 e 2'), 2, 'Mostrare legge x senza modificarla. La seconda uscita legge ancora 2.'),
    Quiz('prima', 'Una variabile ancora vuota?', (o('casse'), s('casse', 'int', '3')), 'La prima riga può leggere il valore assegnato dopo?', ('Sì: trova 3', 'Sì: usa automaticamente 0', 'No: manca un valore disponibile'), 2, 'Le istruzioni non tornano indietro nel tempo. Python/JavaScript incontrano una lettura non disponibile; C/Java richiedono una dichiarazione valida prima dell’uso.'),
)
