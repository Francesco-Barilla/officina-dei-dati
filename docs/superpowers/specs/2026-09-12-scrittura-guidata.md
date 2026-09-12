# Scrittura guidata: che cosa fare, dove e in quale forma

## Problemi osservati
- Medio descrive ogni lacuna come istruzione, anche se `nome = ???` richiede solo un'espressione.
- Difficile parte da un commento e il cursore può rimanere dentro il commento.
- Gli ingressi forniti dal simulatore possono sembrare valori da digitare.
- Le istruzioni di Impara usano la seconda persona per descrivere azioni del computer.
- La guida ai comandi mescola quattro linguaggi invece di accompagnare la missione attuale.

## Intervento
Conservare le schermate approvate. Aggiungere un pulsante che seleziona la lacuna o attiva l'editor; evidenziare i `???` e distinguere calcolo, riga intera e programma completo. Mostrare un esempio di sintassi con nomi diversi dalla missione. Per Difficile usare un editor inizialmente vuoto; conservare le bozze precedenti, compresi i commenti.

La consegna guidata della missione elenca i dati automatici, i nomi da usare, le operazioni e le uscite nell'ordine richiesto. Gli aiuti mostrano il solo linguaggio selezionato. Messaggi specifici accompagnano editor vuoto, lacune residue e un risultato digitato al posto del programma. Impara dichiara chiaramente che si sceglie una risposta, mentre è il computer a leggere e scrivere in memoria.

## Piano e criteri di accettazione
1. Test con click e digitazione: selezionare una lacuna, sostituirla, verificare il programma nei quattro linguaggi; non alterare il testo circostante o una bozza.
2. `writing_guide.py`: descrizione delle lacune, sintassi e consegne specifiche; integrazione in `main.py`, `experience.py`, evidenza visiva in `ui.py`.
3. Controllare tutte le missioni, gli esempi visuali, gli stati vuoto/incompleto/da correggere e la leggibilità a 960×600 e 1280×800.
4. Ricostruire e verificare EXE e ZIP, aggiornare cartella e GitHub, preservare i progressi locali.
