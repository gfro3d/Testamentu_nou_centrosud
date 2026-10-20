# Attivare la sincronizzazione delle TMX

GitHub Actions esegue il lavoro indipendentemente da ChatGPT. Il controllo avviene ogni ora al minuto 17 UTC; GitHub può ritardarlo. TMX_SYNC_ENABLED deve restare disattivata finché l'accesso Drive non è configurato. I test del codice non richiedono credenziali.

## Accesso Google Drive
1. Creare o usare un progetto Google Cloud e abilitare Google Drive API.
2. Creare un account di servizio dedicato, senza ruoli amministrativi o delega di dominio.
3. Condividere la sola cartella del progetto necessaria con l'email dell'account di servizio, come Lettore.
4. Creare una chiave JSON e conservarla nei segreti GitHub sotto indicati, mai nel repository o nei messaggi pubblici.

## Configurare entrambi i repository
In Settings > Secrets and variables > Actions aggiungere:
- Secret GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON: contenuto completo della chiave JSON.
- Secret GOOGLE_DRIVE_SYNC_CONFIG: JSON con le fonti, secondo lo schema sotto. Gli identificativi Drive rimangono soltanto nel secret.
- Variable TMX_SYNC_ENABLED: true solo dopo aver configurato i secret.

Ogni repository usa il proprio GITHUB_TOKEN per pubblicare; non serve un token personale GitHub. La variante è già impostata nel workflow.

Schema di GOOGLE_DRIVE_SYNC_CONFIG, con segnaposto da sostituire privatamente:
~~~json
{
  "books": [
    {"name": "Matteo", "prefix": "Mt", "folder_id": "ID_CARTELLA", "control_folder_id": "ID_CONTROLLO", "italian_file_id": "ID_CEI74"},
    {"name": "Marco", "prefix": "Mc", "folder_id": "ID_CARTELLA", "control_folder_id": "ID_CONTROLLO", "italian_file_id": "ID_CEI74"},
    {"name": "Luca", "prefix": "Lc", "folder_id": "ID_CARTELLA", "control_folder_id": "ID_CONTROLLO", "italian_file_id": "ID_CEI74"},
    {"name": "Giovanni", "prefix": "Gv", "folder_id": "ID_CARTELLA", "control_folder_id": null, "italian_file_id": "ID_CEI74"}
  ]
}
~~~

Con control_folder_id null, cercare una cartella di controllo all'interno della sola cartella del Vangelo; senza fonti sarde non generare traduzioni inventate. Confermare che ciascun italian_file_id punti alla CEI 1974 prima di attivare la sincronizzazione.

## Prima prova
Aprire Actions > TMX Vangeli da Drive > Run workflow, ramo main. Verificare test e job sync verdi, riepilogo della copertura e commit con TMX sotto tm/controllo-teologia/.
Il job sync saltato significa che la sincronizzazione è disattivata: un test verde da solo non prova la pubblicazione.

## Comportamento e limiti
- Un versetto intero per segmento in entrambe le lingue, con Mt1,1, Mc1,1, Lc1,1 o Gv1,1.
- Nomi stabili e versioni precedenti conservate nella cronologia Git.
- Nessun commit se testi e stato degli output non cambiano.
- Nessuna modifica a project_save.tmx, source/, target/, glossari o segmentazione OmegaT.
- Rifiutare perdita di versetti pubblicati, numerazione ambigua e variante non identificabile.
- Le fonti che intrecciano due versetti richiedono revisione editoriale.
- I test sintetici non verificano l'accesso Drive, la copertura reale o il comportamento dentro OmegaT. Verificare la prima sincronizzazione reale prima di considerare il flusso operativo.
- Un errore conserva le memorie esistenti. Consultare Actions e attivare le notifiche GitHub dei job falliti.
- Disattivare TMX_SYNC_ENABLED per sospendere i controlli.

Documentazione ufficiale:
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- https://developers.google.com/workspace/drive/api/guides/manage-downloads
- https://developers.google.com/workspace/drive/api/guides/ref-roles
