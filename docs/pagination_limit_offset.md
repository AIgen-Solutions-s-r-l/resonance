# Meccanismo di Paginazione: `limit` e `offset`

## 1. Introduzione

La paginazione è una tecnica fondamentale utilizzata per dividere grandi set di dati in blocchi più piccoli e gestibili, chiamati "pagine". Questo è essenziale in molti contesti, specialmente nelle API (come le API REST) e nelle interfacce utente che interagiscono con database.

**Scopo Principale:**

*   **Prestazioni:** Evitare il trasferimento e l'elaborazione di enormi quantità di dati in una singola richiesta, migliorando i tempi di risposta e riducendo il carico sul server e sul client.
*   **Usabilità:** Presentare i dati agli utenti in porzioni digeribili, migliorando l'esperienza di navigazione (es. elenchi di prodotti, risultati di ricerca, feed di notizie).
*   **Gestione delle Risorse:** Limitare l'uso di memoria e banda di rete sia sul server che sul client.

Il metodo più comune per implementare la paginazione è attraverso l'uso dei parametri `limit` e `offset`.

## 2. Definizione dei Parametri

### `limit`

*   **Descrizione:** Il parametro `limit` specifica il **numero massimo di record** (o elementi) che devono essere restituiti in una singola pagina. Definisce la "dimensione della pagina".
*   **Ruolo:** Controlla quanti elementi riceverà il client per ogni richiesta di pagina.
*   **Valori Tipici:** I valori comuni variano a seconda del contesto, ma spesso si trovano tra 10 e 100 (es. 10, 20, 25, 50, 100).
*   **Considerazioni:**
    *   Un `limit` troppo piccolo richiede molte più richieste per visualizzare tutti i dati.
    *   Un `limit` troppo grande può vanificare i benefici della paginazione, portando a risposte lente e a un elevato consumo di risorse.
    *   È buona pratica impostare un `limit` predefinito e, talvolta, un `limit` massimo consentito per prevenire abusi.

### `offset`

*   **Descrizione:** Il parametro `offset` specifica il **numero di record da saltare** dall'inizio del set di dati completo prima di iniziare a selezionare i record per la pagina corrente. Indica il "punto di partenza".
*   **Ruolo:** Permette di richiedere pagine successive alla prima. Se `offset` è 0, si inizia dal primo record. Se `offset` è 10, si saltano i primi 10 record e si inizia a selezionare dall'undicesimo.
*   **Relazione con l'Indice:** L'`offset` è spesso basato su un indice a partire da 0. Un `offset` di `N` significa saltare i record con indice da 0 a `N-1`.

## 3. Meccanismo di Funzionamento Dettagliato

Il meccanismo `limit`/`offset` funziona selezionando una "finestra" specifica di dati da un set di risultati **ordinato**.

1.  **Ordinamento:** Il database (o il sistema che fornisce i dati) prima ordina l'intero set di risultati potenziale secondo un criterio stabile e consistente (es. `ORDER BY data_creazione DESC`, `ORDER BY nome ASC`). **Questo passaggio è cruciale**, altrimenti le pagine non avrebbero un significato coerente.
2.  **Salto (`offset`):** Il sistema salta i primi `N` record del set ordinato, dove `N` è il valore di `offset`. Questi record vengono ignorati per la pagina corrente.
3.  **Selezione (`limit`):** A partire dal record successivo a quelli saltati, il sistema seleziona i successivi `M` record, dove `M` è il valore di `limit`. Questi `M` record costituiscono la pagina richiesta.

**Illustrazione:**

Immagina un set di dati ordinato: `[R1, R2, R3, R4, R5, R6, R7, R8, R9, R10]`

*   **Richiesta Pagina 1:** `limit=3`, `offset=0`
    *   Salto (`offset=0`): Nessun record saltato.
    *   Selezione (`limit=3`): Prende `[R1, R2, R3]`. -> Pagina 1 restituita.
*   **Richiesta Pagina 2:** `limit=3`, `offset=3`
    *   Salto (`offset=3`): Salta `[R1, R2, R3]`.
    *   Selezione (`limit=3`): Prende `[R4, R5, R6]`. -> Pagina 2 restituita.
*   **Richiesta Pagina 3:** `limit=3`, `offset=6`
    *   Salto (`offset=6`): Salta `[R1, R2, R3, R4, R5, R6]`.
    *   Selezione (`limit=3`): Prende `[R7, R8, R9]`. -> Pagina 3 restituita.

**Importanza dell'Ordinamento Stabile:** Se l'ordinamento non è stabile o cambia tra le richieste (es. ordinando per un campo non univoco senza un secondo criterio di ordinamento), lo stesso record potrebbe apparire su pagine diverse o essere saltato completamente, rendendo la paginazione inaffidabile.

## 4. Esempi Pratici e Calcoli

### Calcolo dell'`offset` per Numero di Pagina

Se un'interfaccia utente utilizza i numeri di pagina (iniziando da 1) invece dell'`offset` diretto, puoi calcolare l'`offset` necessario con la seguente formula:

`offset = (numero_pagina - 1) * limit`

**Esempi:**

Assumiamo `limit = 20`.

*   Per richiedere la **Pagina 1**:
    *   `numero_pagina = 1`
    *   `offset = (1 - 1) * 20 = 0`
    *   Richiesta: `limit=20`, `offset=0`
*   Per richiedere la **Pagina 2**:
    *   `numero_pagina = 2`
    *   `offset = (2 - 1) * 20 = 20`
    *   Richiesta: `limit=20`, `offset=20`
*   Per richiedere la **Pagina 5**:
    *   `numero_pagina = 5`
    *   `offset = (5 - 1) * 20 = 80`
    *   Richiesta: `limit=20`, `offset=80`

### Esempi di Codice Sorgente

*   **SQL:**
    ```sql
    -- Richiede la pagina 3, con 50 elementi per pagina
    SELECT *
    FROM prodotti
    ORDER BY data_inserimento DESC, id ASC -- Ordinamento stabile
    LIMIT 50 -- Numero di elementi da restituire
    OFFSET 100; -- Numero di elementi da saltare ( (3-1) * 50 )
    ```

*   **API REST (URL):**
    ```
    # Richiede la pagina 2, con 10 elementi per pagina
    GET /api/articoli?limit=10&offset=10

    # Richiede la pagina 1 (offset 0 implicito o esplicito), con 25 elementi
    GET /api/utenti?limit=25
    GET /api/utenti?limit=25&offset=0
    ```

*   **ORM (SQLAlchemy - Esempio Concettuale):**
    ```python
    # Richiede la pagina 4, con 30 elementi per pagina
    page_number = 4
    page_size = 30
    offset_value = (page_number - 1) * page_size # offset = 90

    query = session.query(Prodotto).order_by(Prodotto.nome)
    results = query.offset(offset_value).limit(page_size).all()
    ```

## 5. Casi d'Uso Comuni

*   **Interfacce Utente Web/Mobile:**
    *   Visualizzazione di elenchi di prodotti in un e-commerce.
    *   Feed di notizie o post di blog.
    *   Elenchi di utenti, commenti, transazioni.
    *   Risultati di ricerca.
*   **API RESTful:** Qualsiasi endpoint che restituisce una collezione potenzialmente grande di risorse dovrebbe supportare la paginazione (es. `/users`, `/orders`, `/products`).
*   **Elaborazione Batch:** Processi che devono elaborare grandi quantità di dati possono leggerli in blocchi paginati per evitare di caricare tutto in memoria contemporaneamente.
*   **Sincronizzazione Dati:** Sistemi che sincronizzano dati possono recuperare record in batch paginati.

## 6. Considerazioni Approfondite, Problematiche e Soluzioni

### Prestazioni con `offset` Elevati

*   **Problema:** Molti sistemi di database (specialmente SQL) implementano `OFFSET N` leggendo effettivamente le prime `N + M` righe del risultato ordinato e scartando le prime `N`. Questo significa che **più alto è l'offset, più lenta diventa la query**, poiché il database deve comunque accedere e scartare un numero crescente di righe. L'impatto può essere significativo su tabelle con milioni di righe.
*   **Soluzioni:**
    *   Utilizzare indici appropriati sulla colonna (o colonne) usata per l'`ORDER BY`.
    *   Considerare alternative come la paginazione basata su cursore (vedi sotto).
    *   Limitare la profondità massima della paginazione consentita nell'interfaccia utente.

### Consistenza dei Dati (The Page Drift Problem)

*   **Problema:** Se il set di dati sottostante cambia (vengono aggiunti o eliminati record) tra le richieste di pagine diverse, possono verificarsi problemi:
    *   **Record Duplicati:** Un record che era alla fine di Pagina 1 potrebbe apparire di nuovo all'inizio di Pagina 2 se un nuovo record viene inserito all'inizio del set di dati tra le due richieste.
    *   **Record Mancanti:** Un record all'inizio di Pagina 2 potrebbe essere saltato se un record precedente viene eliminato tra le richieste di Pagina 1 e Pagina 2.
*   **Illustrazione:**
    *   Dataset Iniziale: `[A, B, C, D, E, F]` (`limit=2`)
    *   Richiesta Pagina 1 (`offset=0`): Restituisce `[A, B]`
    *   *Modifica: Viene inserito un nuovo record `X` all'inizio: `[X, A, B, C, D, E, F]`*
    *   Richiesta Pagina 2 (`offset=2`): Il DB salta `[X, A]` e restituisce `[B, C]`. **Il record `B` è duplicato!**
*   **Soluzioni:**
    *   Accettare una certa inconsistenza (spesso sufficiente per molte UI).
    *   Utilizzare la paginazione basata su cursore.
    *   Ricaricare la pagina corrente se si sospetta una modifica significativa.

### Gestione dei Bordi

*   **Offset Oltre i Limiti:** Se l'`offset` richiesto è maggiore o uguale al numero totale di record, la query dovrebbe semplicemente restituire un set di risultati vuoto (una pagina vuota).
*   **Calcolo Totale Pagine:** Per mostrare all'utente il numero totale di pagine, è necessaria una query aggiuntiva (spesso `COUNT(*)` con le stesse clausole `WHERE` della query principale). Questo può aggiungere overhead.
    *   `numero_totale_pagine = ceil(conteggio_totale_record / limit)`

### Interfaccia Utente (UI)

*   Fornire controlli chiari: numeri di pagina cliccabili, pulsanti "Precedente" e "Successivo".
*   Indicare la pagina corrente e il numero totale di pagine (se disponibile).
*   Gestire lo stato dei pulsanti "Precedente"/"Successivo" (disabilitarli sulla prima/ultima pagina).
*   Considerare lo "scroll infinito" come alternativa UI, che spesso usa `limit`/`offset` (o cursori) dietro le quinte.

## 7. Alternative alla Paginazione Limit/Offset

### Paginazione basata su Cursore (Cursor-based / Keyset Pagination)

*   **Meccanismo:** Invece di un `offset`, il client passa un "cursore" che identifica l'ultimo elemento visto nella pagina precedente. Il server utilizza questo cursore per recuperare gli `M` (`limit`) elementi successivi. Il cursore è tipicamente il valore della colonna (o colonne) di ordinamento dell'ultimo elemento.
    *   Esempio SQL: `SELECT * FROM tabella WHERE (data_inserimento, id) > ('2023-10-26 10:00:00', 12345) ORDER BY data_inserimento ASC, id ASC LIMIT 10;` (Il client passa la `data_inserimento` e l'`id` dell'ultimo elemento visto).
*   **Vantaggi:**
    *   **Prestazioni Migliori:** Evita il problema delle prestazioni con `offset` elevati, poiché la clausola `WHERE` può utilizzare efficacemente gli indici per trovare rapidamente il punto di partenza.
    *   **Consistenza Migliore:** Meno suscettibile al "Page Drift Problem", specialmente se l'ordinamento è basato su valori univoci o timestamp crescenti.
*   **Svantaggi:**
    *   **Nessun Salto Diretto:** Non è possibile saltare direttamente a una pagina specifica (es. "vai a Pagina 5") senza aver prima recuperato le pagine precedenti.
    *   **Complessità:** Leggermente più complesso da implementare sia lato server (costruzione della query `WHERE`) che lato client (gestione del cursore).
    *   Richiede un criterio di ordinamento univoco o una combinazione di colonne che garantisca unicità.

### Seek Method

Simile alla paginazione basata su cursore, spesso utilizzata in contesti specifici di database.

## 8. Diagrammi Dettagliati (Mermaid)

### Diagramma di Flusso (Flowchart)

```mermaid
flowchart TD
    A[Client: Richiede Pagina N con Limit L e Offset O] --> B{Server API};
    B --> C{Calcola/Verifica Offset O / Limit L};
    C --> D[Database: Esegue Query con ORDER BY, LIMIT L, OFFSET O];
    D --> E{Recupera Sottoinsieme Dati};
    E --> B;
    B --> F[Server API: Costruisce Risposta (Dati Pagina + Info Paginazione?)];
    F --> G[Client: Riceve e Mostra Pagina N];
```

### Diagramma Concettuale (Visualizzazione Dati)

```
Dataset Ordinato: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, ...]

Richiesta: limit=4, offset=4 (Pagina 2)

+-----------------+-----------------+-----------------+
|   Offset=4      |     Limit=4     |    Restanti     |
| Salta [R1..R4]  | Prendi [R5..R8] |   [R9, R10, ...] |
+-----------------+-----------------+-----------------+
                  |                 |
                  V                 V
           Ignorati       Pagina Restituita
```

### Diagramma di Sequenza (Sequence Diagram)

```mermaid
sequenceDiagram
    participant Client
    participant APIServer as API Server
    participant Database

    Client->>APIServer: GET /api/items?limit=10&offset=20  (Richiesta Pagina 3)
    APIServer->>Database: SELECT * FROM items ORDER BY created_at DESC, id DESC LIMIT 10 OFFSET 20


## 9. Diagramma di Flusso Specifico (Matching Service)

Questo diagramma illustra il flusso effettivo dei parametri `limit` e `offset` all'interno del codice specifico del *matching service* analizzato:

```mermaid
sequenceDiagram
    participant API Endpoint as API
    participant MatchingService as MS (matching_service.py)
    participant JobMatcher as JM (matcher.py)
    participant Cache as C (cache.py)
    participant VectorMatcher as VM (vector_matcher.py)
    participant SimilaritySearcher as SS (similarity_searcher.py)
    participant DBUtils as DU (db_utils.py)
    participant Database as DB

    API->>MS: match_jobs_with_resume(resume, ..., offset=N, experience=...)
    Note over MS: 'limit' non è un parametro diretto qui.
    MS->>JM: process_job(resume, ..., offset=N, limit=50, experience=..., use_cache=True)
    Note over JM: 'limit' ha default 50, 'use_cache' default True.
    JM->>C: generate_key(resume_id, offset=N, location, keywords, experience)
    C-->>JM: cache_key
    JM->>C: get(cache_key)

    alt Cache Hit
        C-->>JM: cached_results {"jobs": [...]}
        Note over JM: Filtra i job applicati da `cached_results` usando `applied_jobs_service` (se user_id presente).
        JM-->>MS: filtered_cached_results
        MS-->>API: results
    else Cache Miss
        C-->>JM: null
        Note over JM: Procede con la ricerca vettoriale.
        JM->>VM: get_top_jobs_by_vector_similarity(cv_embedding, location, keywords, offset=N, limit=5, experience=...)
        Note over VM: 'limit' ha default 5 qui.
        VM->>DU: get_db_cursor("default")
        DU-->>VM: cursor
        VM->>DU: get_filtered_job_count(cursor, where_clauses, query_params, fast=True)
        DU->>DB: Esegue query COUNT(...) LIMIT 6
        DB-->>DU: count_result
        DU-->>VM: row_count (<=6)

        alt row_count <= 5 (Fallback)
            VM->>SS: _execute_fallback_query(cursor, where_clauses, query_params, limit=5)
            SS->>DB: Esegue query SELECT senza vettori LIMIT 5
            DB-->>SS: fallback_raw_results
            SS-->>VM: List[JobMatch] (fallback_results)
        else row_count > 5 (Vector Search)
            VM->>SS: _execute_vector_query(cursor, cv_embedding, where_clauses, query_params, limit=5, offset=N)
            SS->>DU: execute_vector_similarity_query(cursor, cv_embedding, where_clauses, query_params, limit=5, offset=N)
            Note over DU: Imposta ISOLATION LEVEL e enable_seqscan=OFF.
            DU->>DB: Esegue query SELECT con `embedding <=> %s` ... ORDER BY score LIMIT 5 OFFSET N
            DB-->>DU: vector_raw_results
            DU-->>SS: vector_raw_results
            SS-->>VM: List[JobMatch] (vector_results)
        end

        VM-->>JM: List[JobMatch] (job_matches)
        Note over JM: Converte JobMatch in dict, filtra i job applicati (se user_id presente).
        JM->>C: generate_key(resume_id, offset=N, location, keywords, experience)
        C-->>JM: cache_key
        JM->>C: set(cache_key, filtered_results_dict)
        C-->>JM: ack
        JM-->>MS: filtered_results_dict
        MS-->>API: results
    end

```

**Punti Chiave Specifici di Questa Implementazione:**

1.  **Default `limit` Diversi:** `JobMatcher.process_job` ha un `limit` predefinito di 50, ma lo passa a `VectorMatcher.get_top_jobs_by_vector_similarity` che a sua volta ha un `limit` predefinito di 5. Questo `limit=5` viene poi usato nella query al database.
2.  **Cache:** La cache (`cache.py`) gioca un ruolo centrale, usando l'`offset` nella chiave.
3.  **Fallback Query:** Se ci sono 5 o meno risultati potenziali (determinato da `get_filtered_job_count`), viene usata una query più semplice senza `offset`.
4.  **Query Vettoriale:** Solo se ci sono più di 5 risultati potenziali, viene eseguita la query vettoriale completa che utilizza sia `LIMIT 5` che l'`offset=N`.
5.  **Filtro Post-Query:** Dopo aver ottenuto i risultati, `JobMatcher` applica un filtro aggiuntivo per rimuovere i lavori già applicati dall'utente.

    Database-->>APIServer: Righe 21-30 del set ordinato
    APIServer-->>Client: 200 OK { data: [...], pagination: { total: ..., limit: 10, offset: 20 } }