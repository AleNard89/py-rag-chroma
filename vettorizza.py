import os
import sys
import shutil
import glob
from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Disable SSL verification for corporate proxy/firewall environments
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

PERSIST_DIR = "./chroma_db"
DOCS_DIR = "./documenti"


def main():
    load_dotenv()

    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    embedding_deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION")

    if not all([api_key, endpoint, embedding_deployment, api_version]):
        print("Errore: variabili d'ambiente mancanti. Controlla il file .env")
        sys.exit(1)

    if not os.path.exists(DOCS_DIR):
        print(f"Errore: cartella '{DOCS_DIR}' non trovata")
        sys.exit(1)

    pdf_files = sorted(glob.glob(os.path.join(DOCS_DIR, "*.pdf")))
    if not pdf_files:
        print(f"Errore: nessun file PDF trovato in '{DOCS_DIR}'")
        sys.exit(1)

    print(f"Trovati {len(pdf_files)} PDF in '{DOCS_DIR}'")

    # Pulizia database esistente per evitare duplicati
    if os.path.exists(PERSIST_DIR):
        shutil.rmtree(PERSIST_DIR)
        print(f"Database precedente eliminato: {PERSIST_DIR}")

    all_chunks = []
    for pdf_path in pdf_files:
        nome_file = os.path.basename(pdf_path)
        try:
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
        except Exception as e:
            print(f"  Errore nel caricamento di '{nome_file}': {e}")
            continue

        if not documents:
            print(f"  Nessun contenuto estratto da '{nome_file}', saltato")
            continue

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(documents)
        all_chunks.extend(chunks)
        print(f"  {nome_file}: {len(chunks)} chunk")

    if not all_chunks:
        print("Errore: nessun chunk generato da nessun PDF")
        sys.exit(1)

    embeddings = AzureOpenAIEmbeddings(
        azure_endpoint=endpoint,
        api_key=api_key,
        azure_deployment=embedding_deployment,
        api_version=api_version
    )

    try:
        vectorstore = Chroma.from_documents(
            documents=all_chunks,
            embedding=embeddings,
            persist_directory=PERSIST_DIR
        )
    except Exception as e:
        print(f"Errore nella vettorizzazione: {e}")
        sys.exit(1)

    print(f"\nTotale: {len(all_chunks)} chunk da {len(pdf_files)} PDF")
    print(f"Salvati in {PERSIST_DIR}")

if __name__ == "__main__":
    main()
