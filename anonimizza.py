import re


# Codice Fiscale: 6 lettere + 2 cifre + 1 lettera + 2 cifre + 1 lettera + 3 cifre + 1 lettera
RE_CODICE_FISCALE = re.compile(
    r'\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b'
)

# IBAN italiano: IT + 2 cifre + 1 lettera + 22 caratteri alfanumerici
RE_IBAN = re.compile(
    r'\bIT\d{2}[A-Z]\d{22}\b'
)

# Email
RE_EMAIL = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
)

# Telefono: solo con prefisso +39 oppure cellulari 3xx con separatori evidenti
RE_TELEFONO = re.compile(
    r'\+39[\s.-]?\d{2,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b'
)

# Data: DD-MM-YYYY o DD/MM/YYYY
RE_DATA = re.compile(
    r'\b\d{2}[-/]\d{2}[-/]\d{4}\b'
)

# Indirizzo italiano: VIA/VIALE/PIAZZA/CORSO/LARGO + testo + CAP + citta'
RE_INDIRIZZO = re.compile(
    r'(?:VIA|VIALE|PIAZZA|CORSO|LARGO|P\.ZZA|V\.LE)\s+[A-Z][A-Za-z\s.]+\d*\s*\n?\s*\d{5}\s+[A-Z][A-Za-z\s]+(?:\([A-Z]{2}\))?',
    re.MULTILINE
)

# Matricola/codice dipendente: pattern numerico tipico delle buste paga
RE_MATRICOLA = re.compile(
    r'\b\d{6,}/\d{7,}/\d{7,}/?\b'
)

# Nome di persona: 2-4 parole consecutive di sole lettere maiuscole (min 2 char ciascuna)
RE_NOME_PERSONA = re.compile(
    r'\b[A-Z]{2,}(?:\s+[A-Z]{2,}){1,3}\b'
)

# Parole da NON anonimizzare (nomi aziende, voci busta paga, etc.)
WHITELIST = {
    'PAGA', 'BASE', 'TICKET', 'RESTAURANT',
    'LAVORO', 'DIPENDENTE', 'LIVELLO', 'IMPIEGATO', 'DIRIGENTE',
    'OPERAIO', 'QUADRO', 'APPRENDISTA',
    'CONTING', 'SUPPL', 'FUNZ',
    'IRPEF', 'INPS', 'INAIL', 'TFR', 'IBAN',
    'FERIE', 'PERMESSI', 'MALATTIA', 'MATERNITA',
    'RETRIBUZIONE', 'TRATTENUTA', 'COMPETENZA',
    'NETTO', 'LORDO', 'TOTALE', 'IMPONIBILE',
    'FILIALE', 'BANK', 'BANCA', 'ILLIMITY',
    'GENNAIO', 'FEBBRAIO', 'MARZO', 'APRILE', 'MAGGIO', 'GIUGNO',
    'LUGLIO', 'AGOSTO', 'SETTEMBRE', 'OTTOBRE', 'NOVEMBRE', 'DICEMBRE',
    'MILANO', 'ROMA', 'TORINO', 'NAPOLI', 'BOLOGNA', 'FIRENZE',
    'GENOVA', 'VENEZIA', 'PALERMO', 'CATANIA', 'BARI', 'MODENA',
    'TERZIARIO', 'COMMERCIO', 'INDUSTRIA', 'METALMECCANICO',
    'PERIODO', 'RIFERIMENTO', 'VARIABILI', 'MERAVIGLI',
    'VINCENZO', 'GIOBERTI',  # nomi di strade comuni
}


def _estrai_nomi(testo):
    """Estrae nomi di persona trovandoli vicino ai codici fiscali."""
    nomi = set()
    righe = testo.split('\n')
    for i, riga in enumerate(righe):
        if RE_CODICE_FISCALE.search(riga):
            cf_match = RE_CODICE_FISCALE.search(riga)
            # Testo prima del CF sulla stessa riga (rimuovi eventuali numeri iniziali)
            prima_del_cf = riga[:cf_match.start()].strip()
            nome_match = re.search(r'([A-Z]{2,}(?:\s+[A-Z]{2,}){1,3})\s*$', prima_del_cf)
            if nome_match:
                nomi.add(nome_match.group(1))
            # Controlla anche la riga precedente
            if i > 0:
                riga_prec = righe[i - 1].strip()
                if riga_prec and re.match(r'^[A-Z]{2,}(?:\s+[A-Z]{2,}){1,3}$', riga_prec):
                    nomi.add(riga_prec)
    return nomi


def anonimizza(testo):
    """Anonimizza dati personali nel testo prima di inviarlo al LLM."""
    risultato = testo

    # Estrai e sostituisci nomi associati a codici fiscali
    nomi = _estrai_nomi(testo)
    for nome in nomi:
        risultato = risultato.replace(nome, '[NOME]')

    risultato = RE_CODICE_FISCALE.sub('[CODICE_FISCALE]', risultato)
    risultato = RE_IBAN.sub('[IBAN]', risultato)
    risultato = RE_EMAIL.sub('[EMAIL]', risultato)
    risultato = RE_INDIRIZZO.sub('[INDIRIZZO]', risultato)
    risultato = RE_MATRICOLA.sub('[MATRICOLA]', risultato)
    risultato = RE_TELEFONO.sub('[TELEFONO]', risultato)
    risultato = RE_DATA.sub('[DATA]', risultato)

    return risultato


if __name__ == "__main__":
    chunk = """000001 AZIENDA ESEMPIO S.P.A.
VIA ROMA 1
00100 ROMA (RM)
0000000001
SEDE ROMA
Agosto 2025
0012345 ROSSI MARIO RSSMRA85A01H501Z
Impiegato Livello Q
PAGA BASE
2.000,00000
IBAN IT60X0542811101000000123456
Tel: +39 333 1234567
email: test@esempio.it"""

    print("=== ORIGINALE ===")
    print(chunk)
    print("\n=== ANONIMIZZATO ===")
    print(anonimizza(chunk))
