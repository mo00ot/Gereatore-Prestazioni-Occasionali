"""Ricevute Occasionali - interfaccia per compilare la ricevuta e generare il PDF."""

import json
import os
import subprocess
import sys
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import genera_pdf  # leggero: fpdf2 si carica solo alla generazione

NOME_APP = "RicevuteOccasionali"


# ---------------------------------------------------------------- dati salvati

def cartella_dati() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    cartella = base / NOME_APP
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella


FILE_DATI = cartella_dati() / "dati.json"
FILE_FIRMA = cartella_dati() / "firma.png"

DATI_VUOTI = {
    "prestatore": {"nome": "", "cf": "", "indirizzo": "", "nascita": "", "iban": "", "luogo": ""},
    "clienti": [],
    "ultimo_numero": 0,
    "ultimo_anno": date.today().year,
    "ultima_descrizione": "Consulenza",
    "cartella_pdf": str(Path.home()),
    "firma": None,
}


def carica_dati() -> dict:
    dati = json.loads(json.dumps(DATI_VUOTI))
    if FILE_DATI.exists():
        try:
            dati.update(json.loads(FILE_DATI.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            messagebox.showwarning("Dati", "Impossibile leggere i dati salvati: riparto da zero.")
    return dati


def salva_dati(dati: dict) -> None:
    temp = FILE_DATI.with_suffix(".tmp")
    temp.write_text(json.dumps(dati, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(FILE_DATI)


def apri_file(percorso: str) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", percorso])
        elif os.name == "nt":
            os.startfile(percorso)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", percorso])
    except OSError:
        pass


def leggi_importo(testo: str) -> float:
    """Accetta '1.234,56', '1234,56', '1234.56'."""
    testo = testo.strip().replace("€", "").replace(" ", "")
    if "," in testo:
        testo = testo.replace(".", "").replace(",", ".")
    return float(testo)


# ---------------------------------------------------------------- firma

class FinestraFirma(tk.Toplevel):
    LARG, ALT = 540, 180

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Firma")
        self.resizable(False, False)
        self.transient(app.root)
        self.tratti = []

        ttk.Label(self, text="Firma con il mouse o il trackpad nel riquadro:").pack(padx=12, pady=(12, 4), anchor="w")
        self.tela = tk.Canvas(self, width=self.LARG, height=self.ALT, bg="white",
                              highlightthickness=1, highlightbackground="#999", cursor="pencil")
        self.tela.pack(padx=12)
        self.tela.create_line(20, self.ALT - 35, self.LARG - 20, self.ALT - 35, fill="#ddd", dash=(4, 4))
        self.tela.bind("<ButtonPress-1>", self._inizio)
        self.tela.bind("<B1-Motion>", self._muovi)

        pulsanti = ttk.Frame(self)
        pulsanti.pack(fill="x", padx=12, pady=12)
        ttk.Button(pulsanti, text="Cancella", command=self._cancella).pack(side="left")
        ttk.Button(pulsanti, text="Carica immagine…", command=self._carica_immagine).pack(side="left", padx=6)
        ttk.Button(pulsanti, text="Salva firma", command=self._salva).pack(side="right")
        ttk.Button(pulsanti, text="Annulla", command=self.destroy).pack(side="right", padx=6)

        firma = app.dati.get("firma")
        if firma and firma.get("tipo") == "tratti":
            for tratto in firma["tratti"]:
                self.tratti.append([(x * self.LARG, y * self.ALT) for x, y in tratto])
            self._ridisegna()
        self.grab_set()

    def _inizio(self, e):
        self.tratti.append([(e.x, e.y)])
        self.tela.create_oval(e.x - 1, e.y - 1, e.x + 1, e.y + 1, fill="#14205a", outline="", tags="firma")

    def _muovi(self, e):
        x0, y0 = self.tratti[-1][-1]
        self.tratti[-1].append((e.x, e.y))
        self.tela.create_line(x0, y0, e.x, e.y, width=2.5, fill="#14205a",
                              capstyle="round", smooth=True, tags="firma")

    def _ridisegna(self):
        self.tela.delete("firma")
        for tratto in self.tratti:
            if len(tratto) > 1:
                self.tela.create_line(*[c for p in tratto for c in p], width=2.5, fill="#14205a",
                                      capstyle="round", smooth=True, tags="firma")

    def _cancella(self):
        self.tratti = []
        self.tela.delete("firma")

    def _salva(self):
        if not self.tratti:
            self.app.imposta_firma(None)
        else:
            # Ritaglia attorno alla firma e normalizza in 0..1
            xs = [x for t in self.tratti for x, _ in t]
            ys = [y for t in self.tratti for _, y in t]
            x0, y0 = min(xs) - 4, min(ys) - 4
            w, h = max(max(xs) + 4 - x0, 1), max(max(ys) + 4 - y0, 1)
            tratti = [[(round((x - x0) / w, 4), round((y - y0) / h, 4)) for x, y in t] for t in self.tratti]
            self.app.imposta_firma({"tipo": "tratti", "tratti": tratti, "rapporto": w / h})
        self.destroy()

    def _carica_immagine(self):
        percorso = filedialog.askopenfilename(
            parent=self, title="Scegli l'immagine della firma",
            filetypes=[("Immagini", "*.png *.jpg *.jpeg"), ("Tutti i file", "*.*")])
        if not percorso:
            return
        try:
            from PIL import Image  # incluso con fpdf2
            img = Image.open(percorso).convert("RGBA")
            # Sfondo chiaro -> trasparente, così la firma si appoggia sulla linea
            pixel = [(r, g, b, 0) if r > 220 and g > 220 and b > 220 else (r, g, b, a)
                     for r, g, b, a in img.getdata()]
            img.putdata(pixel)
            box = img.getbbox()
            if box:
                img = img.crop(box)
            img.thumbnail((1200, 400))
            img.save(FILE_FIRMA)
        except Exception as err:  # noqa: BLE001
            messagebox.showerror("Firma", f"Immagine non valida:\n{err}", parent=self)
            return
        self.app.imposta_firma({"tipo": "immagine", "percorso": str(FILE_FIRMA)})
        self.destroy()


# ---------------------------------------------------------------- finestra principale

class App:
    def __init__(self, root):
        self.root = root
        self.dati = carica_dati()
        root.title("Ricevute Prestazione Occasionale")
        root.minsize(860, 560)

        corpo = ttk.Frame(root, padding=12)
        corpo.pack(fill="both", expand=True)
        corpo.columnconfigure(0, weight=1, uniform="col")
        corpo.columnconfigure(1, weight=1, uniform="col")

        sinistra = ttk.Frame(corpo)
        sinistra.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        destra = ttk.Frame(corpo)
        destra.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._sezione_prestatore(sinistra)
        self._sezione_cliente(sinistra)
        self._sezione_ricevuta(destra)
        self._sezione_firma(destra)

        fondo = ttk.Frame(corpo)
        fondo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.stato = ttk.Label(fondo, text=f"Dati salvati in: {FILE_DATI.parent}", foreground="#777")
        self.stato.pack(side="left")
        ttk.Button(fondo, text="Genera PDF", command=self.genera).pack(side="right")

        if self.dati["clienti"]:
            self.combo_clienti.current(0)
            self.scegli_cliente()
        self.aggiorna_totali()

    # -- helpers
    @staticmethod
    def _campi(cornice, voci, valori):
        variabili = {}
        cornice.columnconfigure(1, weight=1)
        for i, (chiave, etichetta) in enumerate(voci):
            ttk.Label(cornice, text=etichetta).grid(row=i, column=0, sticky="w", pady=2, padx=(0, 8))
            var = tk.StringVar(value=valori.get(chiave, ""))
            ttk.Entry(cornice, textvariable=var).grid(row=i, column=1, sticky="ew", pady=2)
            variabili[chiave] = var
        return variabili

    # -- sezioni
    def _sezione_prestatore(self, genitore):
        cornice = ttk.LabelFrame(genitore, text="I miei dati (prestatore)", padding=10)
        cornice.pack(fill="x")
        self.v_prest = self._campi(cornice, [
            ("nome", "Nome e Cognome"), ("cf", "Codice Fiscale"), ("indirizzo", "Indirizzo"),
            ("nascita", "Luogo e data di nascita"), ("iban", "IBAN"), ("luogo", "Città (per la firma)"),
        ], self.dati["prestatore"])
        ttk.Button(cornice, text="Salva i miei dati", command=self.salva_prestatore).grid(
            row=10, column=1, sticky="e", pady=(6, 0))

    def _sezione_cliente(self, genitore):
        cornice = ttk.LabelFrame(genitore, text="Cliente (committente)", padding=10)
        cornice.pack(fill="x", pady=(10, 0))
        cornice.columnconfigure(1, weight=1)
        ttk.Label(cornice, text="Clienti salvati").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.combo_clienti = ttk.Combobox(cornice, state="readonly")
        self.combo_clienti.grid(row=0, column=1, sticky="ew", pady=(0, 6))
        self.combo_clienti.bind("<<ComboboxSelected>>", self.scegli_cliente)

        interno = ttk.Frame(cornice)
        interno.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.v_cliente = self._campi(interno, [
            ("nome", "Ragione sociale / Nome"), ("indirizzo", "Indirizzo"), ("piva", "P.IVA / C.F."),
        ], {})

        pulsanti = ttk.Frame(cornice)
        pulsanti.grid(row=2, column=0, columnspan=2, sticky="e", pady=(6, 0))
        ttk.Button(pulsanti, text="Nuovo", command=self.nuovo_cliente).pack(side="left")
        ttk.Button(pulsanti, text="Elimina", command=self.elimina_cliente).pack(side="left", padx=6)
        ttk.Button(pulsanti, text="Salva cliente", command=self.salva_cliente).pack(side="left")
        self.aggiorna_lista_clienti()

    def _sezione_ricevuta(self, genitore):
        cornice = ttk.LabelFrame(genitore, text="Ricevuta", padding=10)
        cornice.pack(fill="x")
        cornice.columnconfigure(1, weight=1)
        oggi = date.today()

        riga = ttk.Frame(cornice)
        riga.grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)
        numero = self.dati["ultimo_numero"] + 1 if self.dati["ultimo_anno"] == oggi.year else 1
        self.v_numero = tk.StringVar(value=str(numero))
        self.v_anno = tk.StringVar(value=str(oggi.year))
        ttk.Label(riga, text="N°").pack(side="left")
        ttk.Spinbox(riga, from_=1, to=9999, width=6, textvariable=self.v_numero).pack(side="left", padx=(6, 16))
        ttk.Label(riga, text="Anno").pack(side="left")
        ttk.Entry(riga, width=6, textvariable=self.v_anno).pack(side="left", padx=6)

        ttk.Label(cornice, text="Descrizione").grid(row=1, column=0, sticky="nw", pady=2, padx=(0, 8))
        self.t_descrizione = tk.Text(cornice, height=3, width=30, wrap="word", font="TkDefaultFont",
                                     relief="solid", borderwidth=1)
        self.t_descrizione.grid(row=1, column=1, sticky="ew", pady=2)
        self.t_descrizione.insert("1.0", self.dati.get("ultima_descrizione", ""))

        self.v_data_prest = tk.StringVar(value=oggi.strftime("%d/%m/%Y"))
        self.v_lordo = tk.StringVar()
        self.v_ritenuta_on = tk.BooleanVar(value=True)
        self.v_luogo_data = tk.StringVar(value=self._luogo_data_predefinito())

        ttk.Label(cornice, text="Data prestazione").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(cornice, textvariable=self.v_data_prest).grid(row=2, column=1, sticky="ew", pady=2)
        ttk.Label(cornice, text="Compenso lordo €").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(cornice, textvariable=self.v_lordo).grid(row=3, column=1, sticky="ew", pady=2)
        ttk.Checkbutton(cornice, text="Applica ritenuta d'acconto 20% (cliente con P.IVA)",
                        variable=self.v_ritenuta_on, command=self.aggiorna_totali).grid(
            row=4, column=1, sticky="w", pady=2)
        self.l_totali = ttk.Label(cornice, text="", foreground="#335")
        self.l_totali.grid(row=5, column=1, sticky="w", pady=(2, 6))
        ttk.Label(cornice, text="Luogo e data").grid(row=6, column=0, sticky="w", pady=2)
        ttk.Entry(cornice, textvariable=self.v_luogo_data).grid(row=6, column=1, sticky="ew", pady=2)
        self.v_lordo.trace_add("write", lambda *_: self.aggiorna_totali())

    def _sezione_firma(self, genitore):
        cornice = ttk.LabelFrame(genitore, text="Firma", padding=10)
        cornice.pack(fill="x", pady=(10, 0))
        self.anteprima_firma = tk.Canvas(cornice, width=300, height=90, bg="white",
                                         highlightthickness=1, highlightbackground="#bbb")
        self.anteprima_firma.pack(side="left")
        colonna = ttk.Frame(cornice)
        colonna.pack(side="left", padx=10, fill="y")
        ttk.Button(colonna, text="Disegna / carica…", command=lambda: FinestraFirma(self)).pack(fill="x")
        ttk.Button(colonna, text="Rimuovi", command=lambda: self.imposta_firma(None)).pack(fill="x", pady=6)
        self.v_usa_firma = tk.BooleanVar(value=True)
        ttk.Checkbutton(colonna, text="Inserisci nel PDF", variable=self.v_usa_firma).pack(anchor="w")
        self.disegna_anteprima_firma()

    # -- logica
    def _luogo_data_predefinito(self):
        luogo = self.dati["prestatore"].get("luogo", "").strip()
        oggi = date.today().strftime("%d/%m/%Y")
        return f"{luogo}, {oggi}" if luogo else oggi

    def aggiorna_totali(self):
        try:
            lordo = leggi_importo(self.v_lordo.get())
        except ValueError:
            self.l_totali.config(text="Inserisci il compenso lordo (es. 1.000,00)")
            return
        rit = round(lordo * 0.2, 2) if self.v_ritenuta_on.get() else 0
        self.l_totali.config(text=f"Ritenuta € {genera_pdf.euro(rit)}   →   Netto € {genera_pdf.euro(lordo - rit)}")

    def salva_prestatore(self, silenzioso=False):
        vecchio_luogo = self.dati["prestatore"].get("luogo", "")
        self.dati["prestatore"] = {k: v.get().strip() for k, v in self.v_prest.items()}
        if self.dati["prestatore"]["luogo"] != vecchio_luogo:
            self.v_luogo_data.set(self._luogo_data_predefinito())
        salva_dati(self.dati)
        if not silenzioso:
            self.stato.config(text="I tuoi dati sono stati salvati.")

    def aggiorna_lista_clienti(self):
        self.combo_clienti["values"] = [c["nome"] for c in self.dati["clienti"]]

    def scegli_cliente(self, _evento=None):
        indice = self.combo_clienti.current()
        if indice >= 0:
            cliente = self.dati["clienti"][indice]
            for k, var in self.v_cliente.items():
                var.set(cliente.get(k, ""))
            if cliente.get("descrizione"):
                self.t_descrizione.delete("1.0", "end")
                self.t_descrizione.insert("1.0", cliente["descrizione"])

    def nuovo_cliente(self):
        self.combo_clienti.set("")
        for var in self.v_cliente.values():
            var.set("")

    def salva_cliente(self, silenzioso=False):
        cliente = {k: v.get().strip() for k, v in self.v_cliente.items()}
        if not cliente["nome"]:
            if not silenzioso:
                messagebox.showinfo("Cliente", "Inserisci almeno la ragione sociale o il nome.")
            return
        cliente["descrizione"] = self.t_descrizione.get("1.0", "end").strip()
        nomi = [c["nome"].lower() for c in self.dati["clienti"]]
        if cliente["nome"].lower() in nomi:
            self.dati["clienti"][nomi.index(cliente["nome"].lower())] = cliente
        else:
            self.dati["clienti"].append(cliente)
            self.dati["clienti"].sort(key=lambda c: c["nome"].lower())
        salva_dati(self.dati)
        self.aggiorna_lista_clienti()
        self.combo_clienti.set(cliente["nome"])
        if not silenzioso:
            self.stato.config(text=f"Cliente «{cliente['nome']}» salvato.")

    def elimina_cliente(self):
        indice = self.combo_clienti.current()
        if indice < 0:
            return
        nome = self.dati["clienti"][indice]["nome"]
        if messagebox.askyesno("Elimina cliente", f"Eliminare «{nome}» dai clienti salvati?"):
            del self.dati["clienti"][indice]
            salva_dati(self.dati)
            self.aggiorna_lista_clienti()
            self.nuovo_cliente()

    def imposta_firma(self, firma):
        self.dati["firma"] = firma
        salva_dati(self.dati)
        self.disegna_anteprima_firma()

    def disegna_anteprima_firma(self):
        tela = self.anteprima_firma
        tela.delete("all")
        firma = self.dati.get("firma")
        if not firma:
            tela.create_text(150, 45, text="Nessuna firma", fill="#999")
            return
        if firma["tipo"] == "immagine" and Path(firma["percorso"]).exists():
            img = tk.PhotoImage(file=firma["percorso"])
            fattore = max(1, -(-img.width() // 290), -(-img.height() // 80))
            self._img_firma = img.subsample(fattore)
            tela.create_image(150, 45, image=self._img_firma)
        elif firma["tipo"] == "tratti":
            r = firma.get("rapporto", 3)
            h = min(80, 290 / r)
            w = h * r
            x0, y0 = (300 - w) / 2, (90 - h) / 2
            for tratto in firma["tratti"]:
                punti = [c for x, y in tratto for c in (x0 + x * w, y0 + y * h)]
                if len(punti) >= 4:
                    tela.create_line(*punti, fill="#14205a", width=2, smooth=True, capstyle="round")

    def genera(self):
        try:
            lordo = leggi_importo(self.v_lordo.get())
            numero = int(self.v_numero.get())
            anno = int(self.v_anno.get())
        except ValueError:
            messagebox.showerror("Dati mancanti", "Controlla numero, anno e compenso lordo.")
            return
        cliente = {k: v.get().strip() for k, v in self.v_cliente.items()}
        if not cliente["nome"]:
            messagebox.showerror("Dati mancanti", "Inserisci i dati del cliente.")
            return

        self.salva_prestatore(silenzioso=True)
        self.salva_cliente(silenzioso=True)

        nome_file = f"Ricevuta_{numero}_{anno}_{cliente['nome']}.pdf"
        nome_file = "".join(c for c in nome_file if c.isalnum() or c in "._- ").replace(" ", "_")
        percorso = filedialog.asksaveasfilename(
            title="Salva ricevuta", defaultextension=".pdf", initialfile=nome_file,
            initialdir=self.dati.get("cartella_pdf") or str(Path.home()),
            filetypes=[("PDF", "*.pdf")])
        if not percorso:
            return

        descrizione = self.t_descrizione.get("1.0", "end").strip()
        ricevuta = {
            "numero": numero, "anno": anno, "descrizione": descrizione,
            "data_prestazione": self.v_data_prest.get().strip(), "lordo": lordo,
            "ritenuta": self.v_ritenuta_on.get(), "luogo_data": self.v_luogo_data.get().strip(),
        }
        firma = self.dati.get("firma") if self.v_usa_firma.get() else None
        try:
            genera_pdf.genera(percorso, self.dati["prestatore"], cliente, ricevuta, firma)
        except Exception as err:  # noqa: BLE001
            messagebox.showerror("Errore", f"Impossibile creare il PDF:\n{err}")
            return

        if (anno, numero) >= (self.dati["ultimo_anno"], self.dati["ultimo_numero"]):
            self.dati["ultimo_anno"], self.dati["ultimo_numero"] = anno, numero
        self.dati["ultima_descrizione"] = descrizione
        self.dati["cartella_pdf"] = str(Path(percorso).parent)
        salva_dati(self.dati)
        self.v_numero.set(str(numero + 1))
        self.stato.config(text=f"Creato: {Path(percorso).name}")
        apri_file(percorso)


def main():
    if os.name == "nt":
        try:  # testo nitido sugli schermi ad alta risoluzione
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
