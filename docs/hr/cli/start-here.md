<!-- BEGIN GENERATED: banner -->
[English](../../en/cli/start-here.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Počnite ovdje

Ovaj vam alat omogućuje da katastar i zemljišnu knjigu čitate s vlastitog
računala, jednom naredbom po upitu. Ova vas stranica vodi kroz pet stvari koje
ćete najčešće raditi. Svaki zadatak završava poveznicom na stranicu koja naredbu
objašnjava u cijelosti.

## Prije prve uporabe

Zamolite tehničkog kolegu da slijedi [stranicu o instalaciji](install.md). Kad
završi, otvorite Terminal, upišite sljedeći redak i pritisnite Enter:

```bash
uz info
```

Ako vidite tablicu s brojem verzije i bez crvenog teksta, spremni ste. Ako
Terminal kaže da naredba nije pronađena, vratite se kolegi.

Dvije stvari prije početka. Prvo, svaka naredba počinje riječju `uz`. Drugo,
alat radi s probnim podacima na vašem računalu; ništa što upišete ne stiže do
službenih registara.

## Zadatak 1: provjerite tko je vlasnik čestice

1. Pronađite broj čestice i katastarsku općinu na svom dokumentu.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz uložak --od-čestice 103/2 -ko SAVAR --vlasnici
   ```

3. Pročitajte tablicu s naslovom **VLASTOVNICA (LIST B)**. Svaki redak jedan je
   vlasnik s njegovim udjelom.

Potpuno objašnjenje: [uložak](commands/get-lr-unit.md).

## Zadatak 2: provjerite hipoteke i druge terete

1. Uzmite istu česticu i općinu.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz uložak --od-čestice 103/2 -ko SAVAR --sve --plombe
   ```

3. Pročitajte **TERETOVNICA (LIST C)**. Ako piše **Nema tereta**, list C je
   prazan.
4. Potražite redak **Plombe (u tijeku)** pri vrhu. Ako ga ima, neki prijedlog za
   upis čeka odluku i listovi se mogu promijeniti.

Potpuno objašnjenje: [uložak](commands/get-lr-unit.md).

## Zadatak 3: potražite više čestica odjednom

1. Napišite brojeve čestica u jednom retku, odvojene zarezima, unutar navodnika.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz čestica "103/2,45,396/1" -ko SAVAR --detalji registry
   ```

3. Svaki redak tablice **REZULTATI** jedna je čestica. Stupac **ZK uložak** je
   zemljišnoknjižni uložak svake od njih.

Potpuno objašnjenje: [čestica](commands/get-parcel.md), a
[uložak](commands/get-lr-unit.md) uz `--ulaz` za uvid u sve te uloške odjednom.

## Zadatak 4: spremite rezultat u datoteku ili za kolegu

1. Uzmite bilo koju naredbu s ove stranice.
2. Na kraj dodajte `--oblik json --datoteka` i naziv datoteke:

   ```bash
   uz čestica 103/2 -ko SAVAR --posjednici --oblik json --datoteka parcel-103-2.json
   ```

3. Datoteka se pojavljuje u mapi u kojoj je Terminal, obično u vašoj osobnoj
   mapi. Priložite je spisu ili proslijedite. `--oblik csv` umjesto toga daje
   datoteku koja se otvara u programu za tablice.

Potpuno objašnjenje: odjeljak „Što možete odabrati” na stranici bilo koje
naredbe.

## Zadatak 5: pogledajte česticu na karti

1. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz čestica 103/2 -ko SAVAR
   ```

2. Pri dnu, pod **DODATNE INFORMACIJE**, nalazi se **URL karte**. Kopirajte ga u
   svoj web preglednik da vidite česticu na javnoj karti.

Potpuno objašnjenje: [čestica](commands/get-parcel.md), a
[granica](commands/get-geometry.md) ako trebate granicu za kartografski program.

## Kad nešto ne uspije

Svaka greška počinje crvenim križićem i kratkom porukom. [Stranica o
greškama](errors.md) ih ispisuje i kaže što učiniti. Najčešći je uzrok pogrešno
upisan broj čestice ili općine.

## Kamo dalje

- [Potpuni pregled naredbi](reference.md): sve naredbe na jednoj stranici, s
  poveznicama.
- [Pojmovnik](glossary.md): riječi zemljišne knjige i kako ih alat naziva.
