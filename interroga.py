import os
import sys
from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings
from langchain_chroma import Chroma

# Disable SSL verification for corporate proxy/firewall environments
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

PERSIST_DIR = "./chroma_db"


def main():
    load_dotenv()

    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    embedding_deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION")

    if not all([api_key, endpoint, embedding_deployment, api_version]):
        print("Errore: variabili d'ambiente mancanti. Controlla il file .env")
        sys.exit(1)

    if not os.path.exists(PERSIST_DIR):
        print(f"Errore: database ChromaDB non trovato in '{PERSIST_DIR}'. Esegui prima vettorizza.py")
        sys.exit(1)

    embeddings = AzureOpenAIEmbeddings(
        azure_endpoint=endpoint,
        api_key=api_key,
        azure_deployment=embedding_deployment,
        api_version=api_version
    )

    try:
        vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings
        )
    except Exception as e:
        print(f"Errore nel caricamento del database ChromaDB: {e}")
        sys.exit(1)

    print(f"Database caricato da: {PERSIST_DIR}")
    print(f"Documenti totali: {vectorstore._collection.count()}\n")

    while True:
        try:
            query = input("Domanda (o 'esci'): ")
        except (KeyboardInterrupt, EOFError):
            print("\nUscita.")
            break

        if query.lower() in ['esci', 'exit', 'quit']:
            break

        try:
            results = vectorstore.similarity_search(query, k=5)
        except Exception as e:
            print(f"\nErrore nella ricerca: {e}\n")
            continue

        print(f"\nTrovati {len(results)} risultati:\n")

        for i, doc in enumerate(results, 1):
            print(f"--- Risultato {i} ---")
            print(doc.page_content)
            print(f"Fonte: {doc.metadata.get('source', 'N/A')}")
            print(f"Pagina: {doc.metadata.get('page', 'N/A')}\n")

if __name__ == "__main__":
    main()
