<!-- BEGIN GENERATED: banner -->
[English](../../en/cli/install.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Instalacija, za osobu koja postavlja alat

Ova je stranica za tehničkog kolegu koji instalira alat. Osoba koja će ga
koristiti ne mora je čitati. Traje oko deset minuta.

## Što instalirate

`uz` je alat naredbenog retka napisan u Pythonu. Razgovara s malim probnim
poslužiteljem, uključenim u isti repozitorij, koji odgovara izmišljenim
katastarskim podacima. Ništa ovdje ne spaja se na službene hrvatske sustave i
tako mora ostati.

## Preduvjeti

- Python 3.12 ili noviji.
- Git, za dohvat repozitorija.
- Terminal koji korisnik može otvoriti: Terminal na macOS-u, Windows Terminal
  ili PowerShell na Windowsima, bilo koji terminal na Linuxu.

## Korak 1: dohvatite repozitorij i stvorite okruženje

```bash
git clone https://github.com/ssarunic/cadastre.git
cd cadastre
python3 -m venv .venv
source .venv/bin/activate
```

Na Windowsima umjesto zadnjeg retka aktivirajte s `.venv\Scripts\activate`.

## Korak 2: instalirajte alat i probni poslužitelj

```bash
pip install -e ./api -e ./cli
pip install -r mock-server/requirements.txt
```

## Korak 3: pokrenite probni poslužitelj

Probni poslužitelj mora biti pokrenut kad god korisnik radi s alatom. Pokrenite
ga u zasebnom prozoru terminala i ostavite taj prozor otvoren:

```bash
cd mock-server
python src/main.py
```

Sluša na adresi `http://localhost:8000`. Alat koristi tu adresu ako mu nije
rečeno drukčije, pa za vježbu nije potrebno dodatno podešavanje.

Da se poslužitelj pokreće sam pri uključivanju računala, napravite korisnički
servis (launchd na macOS-u, zakazani zadatak na Windowsima, systemd korisničku
jedinicu na Linuxu) koji izvršava gornja dva retka unutar virtualnog okruženja.

## Korak 4: odaberite korisnikov jezik

Alat ispisuje na hrvatskom ako nije rečeno drukčije. Postavite varijablu
okruženja `CADASTRAL_LANG` u korisnikovu profilu ljuske na `hr` ili `en`, tako
da korisnik nikad ne mora zadavati `--jezik`. Na primjer, u `~/.zshrc`:

```bash
export CADASTRAL_LANG=hr
```

Dokumentacija postoji na oba jezika. Dajte korisniku poveznicu na izdanje koje
odgovara ovoj postavci.

Korak 2 instalira dva naziva programa, `cadastral` i `uz`. To je isti program.
Hrvatska dokumentacija koristi `uz` s hrvatskim nazivima naredbi i opcija, na
primjer `uz čestica 103/2 -ko SAVAR`; engleska dokumentacija koristi `cadastral`
s engleskim nazivima. Svaka naredba prihvaća oba načina pisanja, pa redak
kopiran iz bilo kojeg izdanja radi.

## Korak 5: provjerite

Otvorite novi terminal kao korisnik i pokrenite:

```bash
uz info
```

Trebali biste vidjeti ovo:

<!-- BEGIN GENERATED: output uz info -->
```text
Hrvatski katastarski CLI
========================
Verzija: 0.4.0
API osnova: http://localhost:8000

Informacije o predmemoriji
==========================
Direktorij predmemorije: ~/.cadastral_api_cache
Veličina predmemorije: 0.0 MB
Općine u predmemoriji: 1
  • 334979 (0.7 KB)
Predmemorija odgovora: memory, 0 unosa, 0.0 MB

API postavke
============
Ograničenje zahtjeva: 0.375 sekundi između zahtjeva
Timeout: 10.0 sekundi
Nepoznata polja poslužitelja: warn

Za brisanje predmemorije: cadastral cache clear --all
```
<!-- END GENERATED: output -->

## Popis za primopredaju

- Probni poslužitelj pokreće se sam, ili korisnik zna dva retka kojima ga
  pokreće.
- `uz info` ispisuje gornji zaslon u novom terminalu koji je korisnik otvorio.
- `CADASTRAL_LANG` je postavljen u korisnikovu profilu.
- Korisnik ima poveznicu na [Počnite ovdje](start-here.md) na svom jeziku.
- Korisnik ima vaš kontakt za slučaj da Terminal kaže da naredba nije pronađena.
