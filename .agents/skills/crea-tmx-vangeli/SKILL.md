---
name: crea-tmx-vangeli
description: Generare e sincronizzare TMX Vangeli italiano CEI 1974 e sardo centro nord e centro sud da Google Drive ai progetti OmegaT GitHub, con un solo versetto per segmento.
---

# TMX Vangeli italiano sardo
Leggere .tmx-sync/state.json per lo stato degli output. Le fonti Drive e le credenziali restano nei segreti GitHub Actions; leggere .tmx-sync/SETUP.md per l'attivazione.
Repository autorizzati: gfro3d/Testamentu_nou_centronord e gfro3d/Testamentu_nou_centrosud, ramo main.
Leggere omegat.project: con tm_dir __DEFAULT__ usare tm/controllo-teologia/ (minuscolo).
Creare una TMX per Vangelo e variante con nomi stabili: Matteo_it_sc_centro_nord.tmx, Marco_it_sc_centro_nord.tmx, Luca_it_sc_centro_nord.tmx, Giovanni_it_sc_centro_nord.tmx; nel centro sud usare centro_sud.

## Controllare le fonti
Elencare i file nelle cartelle di controllo (non solo la data della cartella), confrontare ID, appartenenza, versioni, date e hash dei testi con l'ultimo stato. Rilevare file aggiunti, modificati, rinominati e rimossi, gestendo la paginazione. Cercare nuove cartelle di controllo esclusivamente nelle cartelle dei quattro Vangeli autorizzate. Se non esiste una TMX gestita o manca initial_sync_completed, eseguire la sincronizzazione iniziale delle fonti disponibili.
Leggere tutti i capitoli necessari del Vangelo cambiato e il relativo italiano CEI 1974 nella cartella del Vangelo, verificandone la versione. Non inventare testi mancanti. Per DOCX estrarre anche le tabelle: un'estrazione vuota non prova che il documento sia vuoto.
Distinguere le varianti dal contenuto e dalle intestazioni, non dall'ordine. Luca presenta ordine variabile. Riconoscere numeri completi e abbreviati, punti/virgole, numeri adiacenti alla punteggiatura e spazi non separabili. Verificare progressione, buchi e duplicati.
Conservare parole e alternative lessicali. Correggere solo riferimenti inequivocabilmente errati annotando il cambiamento. Isolare rimandi e commenti editoriali, senza rimuovere arbitrariamente parentesi o alternative.

## Segmentazione obbligatoria
TMX 1.4 UTF-8. Header con attributi obbligatori; lingue it-IT e sc.
Una tu per versetto, due tuv con xml:lang, un seg per lingua. Ogni seg contiene l'intero versetto su una sola riga, con spazi normalizzati.
In ENTRAMBE le lingue iniziare con sigla/capitolo/versetto e spazio: Mt1,1 Testo; Mc1,1 Testo; Lc1,1 Testo; Gv1,1 Testo.
Non segmentare per frase, punto, riga poetica o paragrafo. Non usare intervalli o duplicati. Separare versetti riuniti solo con confine verificabile; altrimenti segnalare il caso senza inventare tagli o traduzioni. Il caso Mc7,21–22 centro sud già riscontrato richiede decisione editoriale: ricontrollare la fonte e non trasferire automaticamente una vecchia esclusione se è stato corretto.
Rileggere l'XML e confrontare segmenti, prefissi, conteggi, unicità, copertura e confini con le fonti. Non dichiarare un test in OmegaT se non eseguito.

## Pubblicare
Aggiornare solo i file gestiti della variante corretta. Mantenere nomi stabili: ogni commit rappresenta una nuova versione, senza copie datate nella cartella TM attiva.
Non modificare omegat/project_save.tmx, source/, target/, glossari, TMX manuali o la configurazione della segmentazione di OmegaT.
Leggere gli SHA correnti prima di scrivere, usare commit senza force push, preferibilmente atomico per TMX e stato. Su concorrenza rileggere e riconciliare. Verificare pubblicazione mediante readback.
Aggiornare lo stato pubblico solo con hash degli output, conteggi e riferimenti di copertura. Non pubblicare identificativi Drive, URL privati, nomi o date delle fonti. Aggiornare lo stato soltanto dopo il successo. Se fallisce un repository, non dichiararlo riuscito né ripetere i successi dell'altro.
Su perdita inattesa di capitoli o ambiguità, preservare la TMX valida e segnalare il blocco. Non sostituirla con dati vuoti o incompleti senza istruzione esplicita.
Nessuna notifica e nessun commit TMX se il contenuto non cambia. Segnalare aggiornamenti con link ai commit e segnalare errori. Le sole modifiche di commenti o formattazione non richiedono TMX nuove.

## Esecuzione
Il workflow .github/workflows/tmx-sync.yml esegue test e sincronizzazione su GitHub Actions, indipendentemente dall'ambiente della chat. Leggere .tmx-sync/SETUP.md. Il programma .tmx-sync/sync_gospels.py estrae le fonti e valida le TMX; i test sono in .tmx-sync/test_sync.py. La variabile TMX_SYNC_ENABLED deve essere true per abilitare i controlli ogni ora; prima configurare GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON e GOOGLE_DRIVE_SYNC_CONFIG nei segreti Actions di ciascun repository. Il vecchio controllo ChatGPT resta in pausa. Una configurazione presente o un test sintetico verde non equivalgono alla pubblicazione: verificare la prima esecuzione reale e i file TMX.
