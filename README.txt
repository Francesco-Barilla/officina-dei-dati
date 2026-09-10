OFFICINA DEI DATI
Realizzato dal Prof. Barillà Francesco

AVVIO
Fai doppio clic su OfficinaDati.exe o Avvia_Officina.cmd.
Per gli alunni: dist/OfficinaDati-Windows.zip. Estrai tutto prima dell'avvio.
La versione Windows funziona offline, senza Python, compilatori o account.

IMPARA FACENDO
Scegli una missione, leggi la riga evidenziata e prevedi valore e tipo.
Osserva il nastro, la memoria e lo schermo, poi passa alla previsione successiva.
Cambia caso per capire come la stessa sequenza usa ingressi diversi.

GIOCA
Facile: riordina le tessere cliccandone due, oppure con le frecce.
Medio: completa ???. Difficile: scrivi il programma.
Esegui mostra il caso attuale; Verifica tutte le sonde controlla i casi dichiarati,
anche i tipi, le variabili richieste e l'ordine delle uscite.
Le missioni sono 16. Non c'è un limite di tempo.

BANCO DEI TIPI
Scegli int, float, string o bool. Scrivi un valore e osserva la cella.
Prova 5 e "5", false e "false", 2.5 e un testo vuoto.
JavaScript usa number per interi e decimali; gli altri linguaggi differiscono.

SCOVA L'EQUIVOCO
16 previsioni su copie, scambi, sovrascritture, divisioni, testo e numeri.
Prima rispondi, poi guarda la traccia e il perché.

COMANDI
F11: schermo intero. Esc: chiudi una scheda o torna indietro.
Rotella e frecce per scorrere le spiegazioni e i programmi lunghi.
Editor: Ctrl+A/C/X/V, Ctrl+Z/Y, Tab, Shift+rotella.
Schede, impostazioni e banco mettono in pausa il nastro.
Progressi e bozze si salvano in progressi_sequenza.json accanto all'app.

L'editor interpreta frammenti sequenziali, non programmi completi.
leggi_intero(), leggi_decimale(), leggi_testo(), leggi_booleano() sono ingressi
didattici della simulazione, non funzioni standard dei quattro linguaggi.
In C mostra(), unisci() e testo() sono aiuti del simulatore.

SORGENTI
python -m pip install -r requirements.txt
python main.py

Istruzioni complete e riferimenti: README.md.
