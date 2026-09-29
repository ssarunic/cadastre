<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/list-main-books.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Pronađite glavnu knjigu katastarske općine

Zemljišna knjiga vodi uloške u glavnim knjigama, u pravilu po jednoj za svaku
katastarsku općinu. Ova naredba pronalazi glavnu knjigu po nazivu i prikazuje
broj koji alat zove identifikator glavne knjige (main book ID), zajedno sa sudom
koji knjigu vodi.

## Kada vam ovo treba

- S dokumenta imate broj zemljišnoknjižnog uloška i znate katastarsku općinu,
  ali ne i identifikator glavne knjige koji traži [get-lr-unit](get-lr-unit.md).
- Želite znati koji općinski sud vodi zemljišnu knjigu za neko mjesto.

## Prije nego počnete

Treba vam naziv katastarske općine kako je napisan na vašem dokumentu. Glavna
knjiga u pravilu nosi isti naziv.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz glavne-knjige --traži SAVAR
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz glavne-knjige --traži SAVAR -->
   ```text
   Glavne knjige (1):

   +--------------------+---------+-------+-------------+
   |   ID glavne knjige | Naziv   | Sud   |   ID odjela |
   +====================+=========+=======+=============+
   |              21277 | SAVAR   | ZADAR |         284 |
   +--------------------+---------+-------+-------------+
   ```
   <!-- END GENERATED: output -->

4. **ID glavne knjige** je broj koji zadajete nakon `--main-book` u naredbi
   [get-lr-unit](get-lr-unit.md). **Sud** je općinski sud čiji zemljišnoknjižni
   odjel vodi knjigu.

## Što možete odabrati

Ako broj ne želite prvo tražiti, zadajte naziv izravno naredbi
[get-lr-unit](get-lr-unit.md) opcijom `--main-book-name`; alat će ovu pretragu
obaviti za vas i upotrijebiti knjigu koju pronađe:

```bash
uz uložak --broj-uloška 769 --naziv-glavne-knjige SAVAR
```

Dodajte `--office` s brojem zemljišnoknjižnog odjela da biste ispisali sve
glavne knjige koje taj odjel vodi, ili `--count-only` da biste dobili samo broj
knjiga. `--format csv` uz `--output` sprema popis kao tablicu.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `--traži`, `-tr` `TEKST` | Pretraga po nazivu glavne knjige | Ne koristi se |
| `--ured`, `-ur` `TEKST` | Filtriraj po identifikatoru zemljišnoknjižnog odjela (npr. 284) | Ne koristi se |
| `--ustanova` `TEKST` | Filtriraj po nazivu ustanove | Ne koristi se |
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--samo-broj` | Prikaži samo broj | Nije uključeno |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako nijedna glavna knjiga nema naziv koji ste upisali, alat to kaže:

<!-- BEGIN GENERATED: output uz glavne-knjige --traži NOWHERE -->
```text
Nije pronađena nijedna glavna knjiga
```
<!-- END GENERATED: output -->

Provjerite kako je katastarska općina napisana na vašem dokumentu ili pretražite
dio naziva. Ostale poruke objašnjene su na [stranici o greškama](../errors.md).

## Povezane stranice

- [get-lr-unit](get-lr-unit.md) daje uvid u uložak kad imate glavnu knjigu.
- [list-books-of-dc](list-books-of-dc.md) ispisuje knjige položenih ugovora,
  drugu vrstu zemljišnoknjižne knjige.
- [search-municipality](search-municipality.md) pronalazi samu katastarsku
  općinu.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz glavne-knjige --help`:

```text
Uporaba: uz glavne-knjige [OPCIJE]

  Popis glavnih knjiga zemljišne knjige.

  Identifikator glavne knjige (main book ID) traži naredba uz uložak uz
  --glavna-knjiga; pretragom po nazivu katastarske općine pronalazi se knjiga
  koja sadrži njezine uloške.

  Primjeri:
    uz glavne-knjige --traži SAVAR
    uz glavne-knjige --ured 284
    uz glavne-knjige --traži SAVAR --oblik json

Opcije:
  -tr, --traži TEKST              Pretraga po nazivu glavne knjige
  -ur, --ured TEKST               Filtriraj po identifikatoru zemljišnoknjižnog
                                  odjela (npr. 284)
  --ustanova TEKST                Filtriraj po nazivu ustanove
  -ob, --oblik [tablica|json|csv]
                                  Format izlaza
  -dt, --datoteka PUTANJA         Spremi izlaz u datoteku
  --samo-broj                     Prikaži samo broj
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
