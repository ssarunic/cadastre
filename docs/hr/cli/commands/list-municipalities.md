<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/list-municipalities.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Popis katastarskih općina jednog ureda

Prikazuje katastarske općine s njihovim šiframa, filtrirane po katastarskom
uredu, po odjelu ili po dijelu naziva.

## Kada vam ovo treba

- Radite s jednim katastarskim uredom i želite šifre svih njegovih općina na
  jednom listu.
- Želite provjeriti kojem odjelu općina pripada prije nego se obratite uredu.

## Prije nego počnete

Trebate broj katastarskog ureda. Stranica [uredi](list-offices.md) prikazuje sve
urede.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz općine --ured 114
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz općine --ured 114 -->
   ```text
   9 općina (office=114):

   +---------+----------+--------+---------+
   |   Šifra | Naziv    |   Ured |   Odjel |
   +=========+==========+========+=========+
   |  334731 | LUKA     |    114 |     116 |
   +---------+----------+--------+---------+
   |  223417 | BIBINJE  |    114 |     116 |
   +---------+----------+--------+---------+
   |  228826 | SUKOŠAN  |    114 |     116 |
   +---------+----------+--------+---------+
   |  229652 | KALI     |    114 |     117 |
   +---------+----------+--------+---------+
   |  334488 | PAŠMAN   |    114 |     117 |
   +---------+----------+--------+---------+
   |  335355 | PREKO    |    114 |     117 |
   +---------+----------+--------+---------+
   |  443512 | VRSI     |    114 |     116 |
   +---------+----------+--------+---------+
   |  332445 | NOVIGRAD |    114 |     116 |
   +---------+----------+--------+---------+
   |  334979 | SAVAR    |    114 |     116 |
   +---------+----------+--------+---------+
   ```
   <!-- END GENERATED: output -->

4. **Šifra** je matični broj općine koji u ostalim naredbama upisujete iza
   `-ko`. Prvi redak kaže koliko općina ured ima.

## Što možete odabrati

Dodajte `--odjel` da popis suzite na jedan odjel ureda, ili `--traži` s dijelom
naziva da potražite jednu općinu:

```bash
uz općine --ured 114 --traži KALI
```

Bez ikakvog filtra alat ispisuje sve općine koje poznaje, a to je dug popis.
Dodajte `--samo-broj` da dobijete samo broj, ili `--oblik csv` s `--datoteka` da
popis spremite kao datoteku za tablice.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `--ured`, `-ur` `TEKST` | Filtriraj po ID-u katastarskog ureda | Ne koristi se |
| `--odjel`, `-od` `TEKST` | Filtriraj po ID-u odjela | Ne koristi se |
| `--traži`, `-tr` `TEKST` | Pretraži po nazivu | Ne koristi se |
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--samo-broj` | Prikaži samo broj | Nije uključeno |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako je broj ureda pogrešan, vidjet ćete ovo:

<!-- BEGIN GENERATED: output uz općine --ured 999 -->
```text
✗ Greška: API greška: Općina nije pronađena (office_id=999)
```
<!-- END GENERATED: output -->

Provjerite broj na stranici [uredi](list-offices.md). Ostale poruke objašnjene
su na [stranici o greškama](../errors.md).

## Povezane stranice

- [traži-općinu](search-municipality.md) pretražuje po nazivu.
- [uredi](list-offices.md) daje brojeve ureda.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz općine --help`:

```text
Uporaba: uz općine [OPCIJE]

  Popis općina uz mogućnost filtriranja.

  Primjeri:
    uz općine
    uz općine --ured 114
    uz općine --ured 114 --odjel 116
    uz općine --traži ZADAR

Opcije:
  -ur, --ured TEKST               Filtriraj po ID-u katastarskog ureda
  -od, --odjel TEKST              Filtriraj po ID-u odjela
  -tr, --traži TEKST              Pretraži po nazivu
  -ob, --oblik [tablica|json|csv]
                                  Format izlaza
  -dt, --datoteka PUTANJA         Spremi izlaz u datoteku
  --samo-broj                     Prikaži samo broj
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
