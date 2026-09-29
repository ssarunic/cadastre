<!-- BEGIN GENERATED: banner -->
[English](../../en/cli/reference.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Potpuni pregled naredbi

<!-- BEGIN GENERATED: reference -->
Sve naredbe, s poveznicom na stranicu svake od njih. Naredba je ono što upisujete; poveznica govori čemu služi.

## Pretraga čestica i uložaka

- `uz pretraži`: [Brza provjera čestice](commands/search.md). Brzo pretraživanje čestica s osnovnim podacima.
- `uz čestica`: [Sve što katastar ima o čestici](commands/get-parcel.md). Dohvat potpunih podataka o čestici s podacima o posjedu.
- `uz uložak`: [Uvid u zemljišnoknjižni uložak: vlasnici, čestice, tereti](commands/get-lr-unit.md). Dohvat detaljnih podataka o zemljišnoknjižnom ulošku.

## Pronalaženje općina i ureda

- `uz traži-općinu`: [Matični broj katastarske općine](commands/search-municipality.md). Pretraživanje i filtriranje općina.
- `uz općine`: [Popis katastarskih općina jednog ureda](commands/list-municipalities.md). Popis općina uz mogućnost filtriranja.
- `uz uredi`: [Popis katastarskih ureda](commands/list-offices.md). Popis svih katastarskih ureda u Hrvatskoj.

## Granice i karte

- `uz granica`: [Granica čestice za kartu](commands/get-geometry.md). Dohvat koordinata granica čestice za GIS integraciju.
- `uz preuzmi-gis`: [Preuzimanje podataka o granicama cijele općine](commands/download-gis.md). Preuzimanje potpunih GIS podataka za općinu.

## Provjera samog alata

- `uz info`: [Provjera je li alat postavljen](commands/info.md). Prikaz informacija o sustavu i stanju predmemorije.
- `uz predmemorija popis`: [Koje su općine pohranjene na vašem računalu](commands/cache-list.md). Popis predmemoriranih općina.
- `uz predmemorija info`: [Koliko je podataka o granicama pohranjeno](commands/cache-info.md). Prikaz detaljnih informacija o predmemoriji.
- `uz predmemorija obriši`: [Brisanje pohranjenih podataka o granicama](commands/cache-clear.md). Brisanje predmemoriranih GIS podataka.

## Ostalo

- `uz posjedovni-list`: [Pogledajte posjedovni list s njegovim česticama](commands/get-possession-sheet.md). Dohvati posjedovni list s njegovim česticama.
- `uz namjena`: [Saznajte je li čestica u građevinskom području](commands/get-zoning.md). Saznajte u kojem je građevinskom području prostornog plana čestica.
- `uz kpu`: [Popis knjiga položenih ugovora](commands/list-books-of-dc.md). Popis knjiga položenih ugovora (KPU).
- `uz glavne-knjige`: [Pronađite glavnu knjigu katastarske općine](commands/list-main-books.md). Popis glavnih knjiga zemljišne knjige.
- `uz traži-posjedovni-list`: [Pronađite posjedovni list po broju](commands/search-possession-sheet.md). Pronađi posjedovni list po broju.
<!-- END GENERATED: reference -->

## Ostale stranice

- [Počnite ovdje](start-here.md): vodič za početak.
- [Pojmovnik](glossary.md): riječi zemljišne knjige i katastra.
- [Greške](errors.md): što znače poruke.
- [Instalacija](install.md): za tehničkog kolegu koji postavlja alat.
