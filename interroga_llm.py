import os
import sys
from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage
from anonimizza import anonimizza

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
    chat_deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION")

    if not all([api_key, endpoint, embedding_deployment, chat_deployment, api_version]):
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

    llm = AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        azure_deployment=chat_deployment,
        api_version=api_version,
        temperature=0,
        max_tokens=500
    )

    print(f"Sistema pronto. Documenti: {vectorstore._collection.count()}\n")

    while True:
        try:
            query = input("Domanda (o 'esci'): ")
        except (KeyboardInterrupt, EOFError):
            print("\nUscita.")
            break

        if query.lower() in ['esci', 'exit', 'quit']:
            break

        try:
            docs = vectorstore.similarity_search(query, k=5)
        except Exception as e:
            print(f"\nErrore nella ricerca: {e}\n")
            continue

        context_raw = "\n\n".join([d.page_content for d in docs])
        context = anonimizza(context_raw)

        prompt = """Sei un assistente che analizza documenti. 

                    REGOLE:
                    - Analizza attentamente i documenti forniti
                    - Rispondi basandoti SOLO sulle informazioni presenti nei documenti
                    - Se l'informazione non è presente, dillo chiaramente
                    - Sii preciso e cita i dati esatti quando possibile
                    - Non fare assunzioni sul tipo di documento"""

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"Documenti:\n{context}\n\nDomanda: {query}")
        ]

        try:
            risposta = llm.invoke(messages)
            if not risposta.content.strip():
                print("\nAttenzione: il modello ha restituito una risposta vuota (possibile rate limit). Riprova tra qualche secondo.\n")
            else:
                print(f"\n{risposta.content}\n")
        except Exception as e:
            print(f"\nErrore nella chiamata al LLM: {e}\n")

if __name__ == "__main__":
    main()
