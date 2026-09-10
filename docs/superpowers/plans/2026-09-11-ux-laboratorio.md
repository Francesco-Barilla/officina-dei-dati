# UX del laboratorio: piano di implementazione

**Goal:** rendere osservazione, azione, errore e completamento comprensibili in Impara e Gioca.

**Architecture:** `experience.py` contiene le schermate del laboratorio, `main.py` gestisce azioni e stato; `missions.py` produce confronti didattici strutturati dal motore esistente.

**Tech Stack:** Python 3.13, Pygame 2.6, PyInstaller; nessuna nuova dipendenza.

## Vincoli
Quattro linguaggi, tre difficoltà, 16 missioni, salvataggi compatibili. Procedere nella copia isolata `build/officina_ux`, poi aggiornare la cartella richiesta preservando progressi e Git.

## Attività
- [x] Aggiungere test di regressione in `tests/test_experience.py`: errore non avanza, corretto persiste, verifica mostra l'esecuzione finale, differenze richiesto/ottenuto, frecce spostano solo la tessera indicata.
- [x] Implementare `CheckRow` e `compare_case(mission, code, language, case)` in `missions.py`, usati dalla verifica e dalla tabella del risultato. Eseguire i test delle missioni.
- [x] Creare `experience.py`: schermata Impara, schermata Gioca, confronto, comandi di movimento e stato della risposta. Collegare `main.App` e conservare i percorsi di pausa, impostazioni e bozze.
- [x] Eseguire `python -m unittest discover -s tests -q`; riprodurre errori e successi con click Pygame e controllare screenshot anche a 1280×800 e 960×600.
- [x] Aggiornare istruzioni e immagini; eseguire `python build_release.py`; verificare l'EXE estratto dallo ZIP.
- [x] Copiare solo i file di distribuzione nella cartella `struttura_sequenziale`, verificare gli hash e i progressi locali.
