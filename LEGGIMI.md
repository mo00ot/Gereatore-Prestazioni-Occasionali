# Ricevute Prestazione Occasionale

Piccola app per macOS, Windows e Linux che compila la ricevuta per prestazione
occasionale e la salva in PDF, con la stessa impaginazione del modulo Word.

## Cosa fa

- **I miei dati**: nome, codice fiscale, indirizzo, nascita, IBAN e città: si salvano una volta sola.
- **Clienti**: salvi più clienti e li scegli dal menu a tendina. Per ogni cliente si ricorda anche l'ultima descrizione usata.
- **Ricevuta**: il numero aumenta da solo e riparte da 1 col nuovo anno. Scrivi il lordo e l'app calcola la ritenuta del 20% e il netto. Se il cliente è un privato senza P.IVA, togli la spunta della ritenuta.
- **Firma**: la disegni con mouse o trackpad oppure carichi una foto o scansione (PNG/JPG). Lo sfondo bianco viene tolto in automatico.
- **Genera PDF**: scegli dove salvarlo e il file si apre da solo.

I dati restano solo sul tuo computer, in:

| Sistema | Cartella |
|---|---|
| macOS   | `~/Library/Application Support/RicevuteOccasionali/` |
| Windows | `%APPDATA%\RicevuteOccasionali\` |
| Linux   | `~/.config/RicevuteOccasionali/` |

Per fare un backup basta copiare questa cartella.

## Creare l'app

PyInstaller crea l'app solo per il sistema su cui gira, quindi ci sono due strade.

**A. Su ogni computer** (serve [Python 3](https://www.python.org/downloads/) installato):

- macOS / Linux: apri il Terminale nella cartella del progetto e lancia `./build.sh`
- Windows: doppio clic su `build.bat`

Trovi il risultato nella cartella `dist/` (`Ricevute.app`, `Ricevute.exe` o `Ricevute`).
Su Linux può servire prima `sudo apt install python3-tk python3-venv`.

**B. Tutti e tre insieme con GitHub** (gratis e senza installare niente):
carica questa cartella in un repository GitHub, apri la scheda **Actions**,
scegli **Compila app** e poi **Run workflow**. Dopo qualche minuto scarichi
i tre pacchetti dalla sezione *Artifacts*.

> Le app non sono firmate digitalmente. La prima volta macOS e Windows
> possono mostrare un avviso: su Mac fai clic destro e poi **Apri**, su
> Windows **Ulteriori informazioni** e poi **Esegui comunque**.

## Avviarla senza compilare

```
pip install fpdf2
python3 ricevute.py
```

## File

- `ricevute.py`: interfaccia (Tkinter, già incluso in Python)
- `genera_pdf.py`: disegna il PDF (fpdf2)
