# Officina dei dati: la sequenza diventa visibile

Il tema è un nastro di montaggio per sonde. La continuità con gli altri
laboratori comprende colori, mascotte, Impara/Gioca, quattro linguaggi,
tre difficoltà, equivoci, impostazioni e progressi locali.

## Che cosa deve capire lo studente

Una sequenza esegue le istruzioni nell'ordine scritto. Prima si legge il valore
di destra, poi si aggiorna la destinazione di sinistra. I valori in memoria
cambiano nel tempo; una copia e una precedente uscita non si aggiornano
automaticamente. Il tipo distingue un conteggio, una misura, un testo e
un valore logico, con le differenze proprie di ciascun linguaggio.

## Dal gesto alla regola

1. Nel banco scrivi 5 come int e come string. Osserva tipo e virgolette.
2. In Impara / Il carico aumenta prevedi il risultato di casse = casse + 2.
   Prima della risposta la memoria conserva lo stato precedente; poi il nastro
   mostra il nuovo stato. La spiegazione collega il gesto all'assegnazione.
3. In Gioca riordina le istruzioni mescolate. Prima di eseguire, motiva perché
   una lettura deve precedere un calcolo. Se il programma fallisce, usa il caso
   segnalato come controesempio e modifica la sequenza.
4. Passa ai livelli Medio e Difficile: i medesimi concetti vengono espressi
   completando e scrivendo il codice.
5. Con Scova l'equivoco prevedi un programma concreto: le domande non chiedono
   che cosa sarebbe giusto fare, ma che cosa produrrà quel codice.

## Progressione delle sfide

Le prime missioni separano ordine, int, float e string. Poi entrano bool,
confronti, calcoli misti e conversioni. Gli ultimi problemi richiedono di
ragionare sulla memoria: copia, scambio, stampa prima/dopo, sovrascrittura.
La missione finale usa tutti e quattro i tipi in un'unica sequenza.

La difficoltà cresce nel modo di costruire il programma, senza aggiungere
pressione temporale. Il livello Facile usa tessere; Medio propone lacune;
Difficile richiede il frammento completo. Consultare gli aiuti non distrugge
la bozza. Il completamento richiede che il programma superi tutti i casi
dichiarati, comprese le variabili e i tipi richiesti.

## Equivoci da rendere osservabili

- = è un'assegnazione, non un'uguaglianza da risolvere.
- Una copia cattura il valore in un istante, non un collegamento permanente.
- La stampa legge il valore; non lo consuma e non si aggiorna dopo.
- Un numero scritto tra virgolette è testo.
- Il nome della variabile non ne stabilisce il tipo.
- Due copie in direzioni opposte non bastano a scambiare due valori.
- Convertire dopo una divisione intera non recupera la parte persa.
- Le parentesi cambiano il calcolo; i nomi come media non ne cambiano il significato.
- JavaScript usa number sia per conteggi sia per decimali.
- I float rappresentano molti decimali solo approssimativamente.

## Verifiche del progetto

Il motore ha risultati attesi indipendenti dalle soluzioni di riferimento.
I test coprono tutte le soluzioni nei quattro linguaggi, casi sbagliati,
divisioni, tipi, immutabilità delle fotografie della memoria, ingressi,
quiz, previsioni complete, bozze, pause, temi e tessere fuori dalla prima pagina.
Il pacchetto Windows viene provato anche dopo l'estrazione dello ZIP.

Le API di input e gli aiuti C sono dichiarati come funzioni didattiche del
simulatore. Questo rende possibile concentrarsi sulla sequenza senza attribuire
ai linguaggi funzioni standard inesistenti. README e schede specificano il
sottoinsieme, le differenze e i limiti numerici.
