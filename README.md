# RAG Pipeline - Interroga i tuoi PDF con Azure OpenAI e ChromaDB

## Panoramica

Questo progetto implementa un sistema **RAG (Retrieval-Augmented Generation)** che permette di indicizzare documenti PDF e interrogarli in linguaggio naturale tramite Azure OpenAI.

Il flusso è composto da due fasi:

```
[PDF] → vettorizza.py → [ChromaDB] → interroga.py      (risultati grezzi)
                                    → interroga_llm.py   (risposta generata da LLM)
```

---

## Prerequisiti

- Python 3.10 - 3.13 (vedi nota sotto su Python 3.14)
- Un endpoint Azure OpenAI con accesso ai modelli:
  - `text-embedding-3-large` (embedding)
  - `gpt-4o` (chat)

### Compatibilita' Python

> **Python 3.14 NON e' supportato.** La libreria `chromadb` dipende internamente da `pydantic.v1.BaseSettings`, che non e' compatibile con Python 3.14+. L'import di `chromadb` fallisce con l'errore:
>
> ```
> pydantic.v1.errors.ConfigError: unable to infer type for attribute "chroma_server_nofile"
> ```
>
> Il problema e' tracciato nella issue [chroma-core/chroma#5996](https://github.com/chroma-core/chroma/issues/5996). Al momento (marzo 2026) nessuna versione di `chromadb` pubblicata su PyPI risolve il bug, inclusa la 1.5.2.
>
> **Versione consigliata: Python 3.13.x**
>
> ```bash
> # macOS con Homebrew
> brew install python@3.13
> /opt/homebrew/bin/python3.13 -m venv .venv
> source .venv/bin/activate
> pip install -r requirements.txt
> ```

### Installazione dipendenze

```bash
pip install -r requirements.txt
```

Pacchetti utilizzati:

| Pacchetto | Scopo |
|-----------|-------|
| `langchain-openai` | Integrazione con Azure OpenAI (embedding + chat) |
| `langchain-chroma` | Integrazione con ChromaDB come vector store |
| `langchain-community` | Loader per documenti (PyPDFLoader) |
| `langchain-text-splitters` | Splitting dei documenti in chunk |
| `chromadb` | Database vettoriale locale |
| `pypdf` | Parsing dei file PDF |
| `python-dotenv` | Caricamento variabili d'ambiente da file `.env` |

---

## Configurazione

La configurazione avviene tramite variabili d'ambiente nel file `.env`. Copia il template e inserisci i tuoi valori:

```bash
cp .env.example .env
```

Contenuto di `.env.example`:

```env
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=your_embedding_deployment_name
AZURE_OPENAI_CHAT_DEPLOYMENT=your_chat_deployment_name
AZURE_OPENAI_API_VERSION=2024-06-01
```

| Variabile | Descrizione |
|-----------|-------------|
| `AZURE_OPENAI_API_KEY` | Chiave di autenticazione per l'API Azure OpenAI |
| `AZURE_OPENAI_ENDPOINT` | URL dell'endpoint Azure OpenAI |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Nome del deployment per generare gli embedding |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Nome del deployment per la generazione di risposte (LLM) |
| `AZURE_OPENAI_API_VERSION` | Versione dell'API Azure OpenAI |

> **Nota**: il file `.env` e' incluso nel `.gitignore` e non viene tracciato da git. Solo `.env.example` (con placeholder generici) viene committato.

> **Nota SSL**: gli script disabilitano la verifica SSL (`urllib3.disable_warnings`, `CURL_CA_BUNDLE=''`). Questo e' necessario in ambienti corporate con proxy/firewall che intercettano il traffico HTTPS.

---

## Step 1 - Indicizzazione del PDF (`vettorizza.py`)

Questo script va eseguito **una sola volta** per ogni nuovo documento (o quando il documento cambia).

```bash
python vettorizza.py
```

### Cosa fa internamente

1. **Caricamento PDF**: usa `PyPDFLoader` per leggere il file PDF pagina per pagina
2. **Splitting in chunk**: il testo viene suddiviso in frammenti da 1000 caratteri con un overlap di 50 caratteri, usando `RecursiveCharacterTextSplitter`. I separatori usati in ordine di priorita' sono:
   - `\n\n` (doppio a capo)
   - `\n` (singolo a capo)
   - ` ` (spazio)
   - `""` (carattere per carattere, come ultima risorsa)
3. **Generazione embedding**: ogni chunk viene trasformato in un vettore numerico tramite il modello `text-embedding-3-large` di Azure OpenAI
4. **Persistenza**: i vettori e i metadati vengono salvati in un database ChromaDB locale nella cartella `./chroma_buste_paga`

### Output atteso

```
Vettorizzati 42 chunk da 08_Agosto_2025.pdf
Salvati in ./chroma_buste_paga
```

### Cosa viene generato su disco

```
chroma_buste_paga/
├── chroma.sqlite3              # Database SQLite con metadati e mapping
└── <uuid>/
    ├── data_level0.bin         # Vettori di embedding (HNSW index)
    ├── header.bin              # Header dell'indice
    ├── length.bin              # Lunghezze dei vettori
    └── link_lists.bin          # Struttura del grafo HNSW per la ricerca
```

---

## Step 2a - Interrogazione diretta (`interroga.py`)

Questa modalita' restituisce i **chunk grezzi** piu' simili alla domanda, senza rielaborazione da parte di un LLM.

```bash
python interroga.py
```

### Cosa fa internamente

1. Apre il database ChromaDB esistente
2. Avvia un loop interattivo: scrivi una domanda e premi Invio
3. Per ogni domanda:
   - La domanda viene trasformata in un vettore (embedding)
   - Viene eseguita una **similarity search** contro i chunk indicizzati
   - Vengono restituiti i **5 chunk piu' rilevanti** (`k=5`) con fonte e numero di pagina
4. Digita `esci`, `exit` o `quit` per uscire

### Output di esempio

```
Database caricato da: ./chroma_buste_paga
Documenti totali: 42

Domanda (o 'esci'): qual e' il netto in busta?

Trovati 5 risultati:

--- Risultato 1 ---
[contenuto del chunk piu' rilevante]
Fonte: 08_Agosto_2025.pdf
Pagina: 2
```

### Quando usare questa modalita'

- Per **verificare** cosa il sistema ha effettivamente indicizzato
- Per **debug**: controllare se i chunk recuperati contengono l'informazione cercata
- Quando non serve una risposta elaborata ma solo i dati grezzi

---

## Step 2b - Interrogazione con LLM (`interroga_llm.py`)

Questa modalita' implementa il **RAG completo**: recupera i chunk rilevanti e li passa a GPT-4o per generare una risposta in linguaggio naturale.

```bash
python interroga_llm.py
```

### Cosa fa internamente

1. Apre il database ChromaDB esistente
2. Inizializza il modello di chat `gpt-4o` via Azure (`temperature=0` per risposte deterministiche, `max_tokens=500`)
3. Avvia un loop interattivo
4. Per ogni domanda:
   - Recupera i 5 chunk piu' rilevanti (similarity search)
   - Concatena i chunk in un unico blocco di contesto
   - Costruisce un messaggio con:
     - **System prompt**: istruisce il modello a rispondere solo in base ai documenti forniti
     - **Human message**: contesto (i chunk) + domanda dell'utente
   - Invia il tutto a GPT-4o e stampa la risposta generata
5. Digita `esci`, `exit` o `quit` per uscire

### System prompt utilizzato

Il modello riceve queste istruzioni:

> Sei un assistente che analizza documenti.
> - Analizza attentamente i documenti forniti
> - Rispondi basandoti SOLO sulle informazioni presenti nei documenti
> - Se l'informazione non e' presente, dillo chiaramente
> - Sii preciso e cita i dati esatti quando possibile
> - Non fare assunzioni sul tipo di documento

Questo prompt e' fondamentale per evitare che il modello "inventi" informazioni non presenti nel PDF (problema noto come *hallucination*).

### Output di esempio

```
Sistema pronto. Documenti: 42

Domanda (o 'esci'): qual e' il netto in busta?

Il netto in busta per il mese di agosto 2025 risulta essere di 1.850,00 euro,
come indicato nella sezione "Netto da pagare" del documento.
```

---

## Riepilogo dei file

| File | Ruolo | Quando eseguirlo |
|------|-------|------------------|
| `.env.example` | Template configurazione | Copiare in `.env` e compilare |
| `.env` | Configurazione con segreti (non tracciato da git) | Modificare prima di iniziare |
| `vettorizza.py` | Indicizza il PDF in ChromaDB | Una volta per documento |
| `interroga.py` | Ricerca semantica (chunk grezzi) | Per debug o consultazione rapida |
| `interroga_llm.py` | RAG completo con risposta LLM | Per interrogare il documento |
| `chroma_buste_paga/` | Database vettoriale generato | Generato automaticamente |

---

## Come estendere il progetto

- **Aggiungere piu' PDF**: modificare `vettorizza.py` per iterare su una lista di file
- **Cambiare chunk size**: regolare `chunk_size` e `chunk_overlap` in `vettorizza.py` per bilanciare precisione e contesto
- **Aumentare/diminuire i risultati**: modificare il parametro `k` nella `similarity_search`
- **Cambiare modello LLM**: modificare `AZURE_OPENAI_CHAT_DEPLOYMENT` nel `.env` (es. `gpt-4o-mini` per risposte piu' economiche)
- **Aggiungere memoria conversazionale**: integrare `ConversationBufferMemory` di LangChain per mantenere il contesto tra domande successive
