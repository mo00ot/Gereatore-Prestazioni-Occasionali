"""Generazione del PDF della ricevuta per prestazione occasionale.

Riproduce l'impaginazione del modulo Word originale disegnando il PDF
direttamente con fpdf2 (nessun bisogno di Word o LibreOffice).
"""

from pathlib import Path

FONT = "LiberationSans"  # stesse misure di Arial/Helvetica, licenza SIL OFL
CARTELLA_FONT = Path(__file__).resolve().parent / "font"

# Impaginazione (mm) ricavata dal .docx: margini 1" sopra/sotto, 1,25" ai lati
MARGINE_SX = 31.75
MARGINE_DX = 31.75
MARGINE_SU = 25.4
RIENTRO = 12.7          # rientro prima riga (0,5")
COLONNA_VALORI = 76.2   # larghezza prima colonna della tabella importi (3")
CORPO = 11
INTERLINEA = 5.6
BLU_TITOLO = (54, 95, 145)

DICHIARAZIONE = (
    "Il sottoscritto dichiara che la presente prestazione è di natura occasionale "
    "ai sensi dell’art. 2222 del Codice Civile, non abituale e non soggetta a IVA "
    "né a contribuzione previdenziale, in quanto il totale dei compensi percepiti "
    "nell’anno non supera € 5.000,00."
)


def euro(valore: float) -> str:
    """1234.5 -> '1.234,50'"""
    testo = f"{valore:,.2f}"
    return testo.replace(",", "X").replace(".", ",").replace("X", ".")


def _nuovo_pdf(numero, anno):
    # fpdf2 viene caricato solo quando serve: l'app aperta resta leggera in RAM
    from fpdf import FPDF

    pdf = FPDF(format="A4", unit="mm")
    # Font incorporato nel PDF: il risultato è identico su ogni lettore PDF
    pdf.add_font(FONT, "", CARTELLA_FONT / "LiberationSans-Regular.ttf")
    pdf.add_font(FONT, "B", CARTELLA_FONT / "LiberationSans-Bold.ttf")
    pdf.set_margins(MARGINE_SX, MARGINE_SU, MARGINE_DX)
    pdf.set_auto_page_break(True, 25.4)
    pdf.add_page()

    # Intestazione: numero a sinistra, anno a destra
    pdf.set_font(FONT, size=CORPO)
    pdf.set_xy(MARGINE_SX, 12.7)
    larghezza = pdf.w - MARGINE_SX - MARGINE_DX
    pdf.cell(larghezza / 2, 5, f"N° {numero}")
    pdf.cell(larghezza / 2, 5, str(anno), align="R")
    pdf.set_xy(MARGINE_SX, MARGINE_SU)
    return pdf


def _riga_etichetta(pdf, etichetta, valore):
    pdf.set_font(FONT, "B", CORPO)
    pdf.write(INTERLINEA, etichetta + " ")
    pdf.set_font(FONT, "", CORPO)
    pdf.write(INTERLINEA, valore or "")
    pdf.ln(INTERLINEA)


def _titoletto(pdf, testo):
    pdf.set_font(FONT, "", CORPO)
    pdf.set_x(MARGINE_SX + RIENTRO)
    pdf.cell(0, INTERLINEA, testo)
    pdf.ln(INTERLINEA + 3)


def _disegna_firma(pdf, firma, x, y_linea, larghezza, altezza):
    """Disegna la firma appoggiata sulla linea, sopra a (x, y_linea)."""
    if not firma:
        return
    y = y_linea - altezza + 2
    if firma.get("tipo") == "immagine" and firma.get("percorso"):
        pdf.image(firma["percorso"], x=x, y=y, h=altezza, keep_aspect_ratio=True,
                  w=larghezza)
    elif firma.get("tipo") == "tratti" and firma.get("tratti"):
        rapporto = firma.get("rapporto", 3.0)  # larghezza/altezza della tela
        h = min(altezza, larghezza / rapporto)
        w = h * rapporto
        y = y_linea - h + 2
        pdf.set_draw_color(20, 30, 90)
        pdf.set_line_width(0.45)
        for tratto in firma["tratti"]:
            punti = [(x + px * w, y + py * h) for px, py in tratto]
            if len(punti) == 1:
                punti.append((punti[0][0] + 0.2, punti[0][1]))
            pdf.polyline(punti)
        pdf.set_draw_color(0, 0, 0)


def genera(percorso_pdf, prestatore, cliente, ricevuta, firma=None):
    """Crea il PDF.

    prestatore: nome, cf, indirizzo, nascita, iban
    cliente:    nome, indirizzo, piva
    ricevuta:   numero, anno, descrizione, data_prestazione, lordo (float),
                ritenuta (bool), luogo_data
    firma:      None | {"tipo": "tratti", "tratti": [...], "rapporto": r}
                     | {"tipo": "immagine", "percorso": "..."}
    """
    lordo = round(float(ricevuta["lordo"]), 2)
    ritenuta = round(lordo * 0.20, 2) if ricevuta.get("ritenuta", True) else 0.0
    netto = round(lordo - ritenuta, 2)

    pdf = _nuovo_pdf(ricevuta["numero"], ricevuta["anno"])
    pdf.set_title(f"Ricevuta prestazione occasionale N° {ricevuta['numero']}/{ricevuta['anno']}")
    pdf.set_author(prestatore.get("nome", ""))

    # Titolo
    pdf.ln(8)
    pdf.set_font(FONT, "B", 14)
    pdf.set_text_color(*BLU_TITOLO)
    pdf.cell(0, 7, "Ricevuta per Prestazione Occasionale")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(9)

    _titoletto(pdf, "Dati del prestatore:")
    _riga_etichetta(pdf, "Nome e Cognome:", prestatore.get("nome"))
    _riga_etichetta(pdf, "Codice Fiscale:", prestatore.get("cf"))
    _riga_etichetta(pdf, "Indirizzo:", prestatore.get("indirizzo"))
    _riga_etichetta(pdf, "Luogo e data di nascita:", prestatore.get("nascita"))
    _riga_etichetta(pdf, "IBAN:", prestatore.get("iban"))
    pdf.ln(INTERLINEA + 3)

    _titoletto(pdf, "Dati del committente:")
    _riga_etichetta(pdf, "Ragione sociale / Nome:", cliente.get("nome"))
    _riga_etichetta(pdf, "Indirizzo:", cliente.get("indirizzo"))
    _riga_etichetta(pdf, "P.IVA / C.F.:", cliente.get("piva"))
    pdf.ln(INTERLINEA + 3)

    _titoletto(pdf, "Descrizione della prestazione:")
    pdf.set_font(FONT, "", CORPO)
    pdf.set_left_margin(MARGINE_SX + 2 * RIENTRO)
    pdf.set_x(MARGINE_SX + 2 * RIENTRO)
    pdf.multi_cell(0, INTERLINEA, ricevuta.get("descrizione", "").strip(), align="L")
    pdf.set_left_margin(MARGINE_SX)
    pdf.ln(INTERLINEA + 3)

    pdf.set_x(MARGINE_SX + RIENTRO)
    pdf.cell(0, INTERLINEA, f"Data della prestazione: {ricevuta.get('data_prestazione', '')}")
    pdf.ln(INTERLINEA * 2 + 3)

    # Importi
    righe = [
        ("Compenso lordo (€):", euro(lordo)),
        ("Ritenuta d’acconto 20% (€):",
         euro(ritenuta) if ricevuta.get("ritenuta", True) else "non applicata"),
        ("Totale netto da corrispondere (€):", euro(netto)),
    ]
    for etichetta, valore in righe:
        pdf.set_font(FONT, "", CORPO)
        pdf.cell(COLONNA_VALORI, INTERLINEA, etichetta)
        pdf.set_font(FONT, "B" if etichetta.startswith("Totale") else "", CORPO)
        pdf.cell(0, INTERLINEA, valore)
        pdf.ln(INTERLINEA + 2.5)
    pdf.ln(INTERLINEA + 2)

    pdf.set_font(FONT, "", CORPO)
    pdf.multi_cell(0, INTERLINEA, DICHIARAZIONE, align="L")
    pdf.ln(INTERLINEA * 2)

    pdf.cell(0, INTERLINEA, f"Luogo e data: {ricevuta.get('luogo_data', '')}")
    pdf.ln(INTERLINEA * 4)

    # Firma con spazio sopra la linea
    pdf.cell(pdf.get_string_width("Firma: "), INTERLINEA, "Firma: ")
    x_linea = pdf.get_x()
    y_linea = pdf.get_y() + INTERLINEA - 0.8
    pdf.set_line_width(0.25)
    pdf.line(x_linea, y_linea, x_linea + 62, y_linea)
    _disegna_firma(pdf, firma, x_linea + 2, y_linea, 58, 18)

    pdf.output(percorso_pdf)
    return lordo, ritenuta, netto
