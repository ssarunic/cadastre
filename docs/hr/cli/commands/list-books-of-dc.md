<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/list-books-of-dc.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Popis knjiga položenih ugovora

Osim glavnih knjiga, zemljišna knjiga vodi i knjige položenih ugovora (KPU). U
njima su stanovi i poslovni prostori prodani prije nego što je zgrada dobila
zemljišnoknjižni uložak. Ova naredba ispisuje te knjige zajedno sa
zemljišnoknjižnim odjelom koji svaku od njih vodi.

## Kada vam ovo treba

- Stan koji provjeravate nije ni u jednom zemljišnoknjižnom ulošku i sumnjate da
  je upisan u knjigu položenih ugovora.
- Želite znati koji zemljišnoknjižni odjeli vode takve knjige za neko mjesto.

## Prije nego počnete

Treba vam naziv mjesta, obično grada ili katastarske općine, kako je napisan na
vašem dokumentu. Bez naziva alat ispisuje sve knjige koje poznaje, a taj popis
može biti dugačak.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz kpu --traži ZADAR
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz kpu --traži ZADAR -->
   ```text
   Knjige položenih ugovora (1):

   +-------------+---------+------------------------------+-------------+
   |   ID knjige | Naziv   | Zemljišnoknjižni odjel       |   ID odjela |
   +=============+=========+==============================+=============+
   |       20501 | ZADAR   | Zemljišnoknjižni odjel Zadar |         284 |
   +-------------+---------+------------------------------+-------------+
   ```
   <!-- END GENERATED: output -->

4. **ID knjige** je broj knjige, a posljednja dva stupca imenuju
   zemljišnoknjižni odjel koji je vodi.

## Što možete odabrati

Dodajte `--office` s brojem zemljišnoknjižnog odjela da biste ispisali samo
njegove knjige, ili `--count-only` da biste dobili samo broj knjiga. `--format
csv` uz `--output` sprema popis kao tablicu.

Alat još ne može otvoriti knjigu položenih ugovora onako kako otvara
zemljišnoknjižni uložak; on knjigu samo pronalazi. Za sam upis obratite se
zemljišnoknjižnom odjelu navedenom u popisu.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `--traži`, `-tr` `TEKST` | Pretraga po nazivu knjige | Ne koristi se |
| `--ured`, `-ur` `TEKST` | Filtriraj po identifikatoru zemljišnoknjižnog odjela (npr. 284) | Ne koristi se |
| `--ustanova` `TEKST` | Filtriraj po nazivu ustanove | Ne koristi se |
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--samo-broj` | Prikaži samo broj | Nije uključeno |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako nijedna knjiga nema naziv koji ste upisali, alat to kaže:

<!-- BEGIN GENERATED: output uz kpu --traži NOWHERE -->
```text
Nije pronađena nijedna knjiga položenih ugovora
```
<!-- END GENERATED: output -->

Pokušajte s kraćim dijelom naziva ili izostavite `--search` da biste vidjeli
cijeli popis. Ostale poruke objašnjene su na [stranici o
greškama](../errors.md).

## Povezane stranice

- [list-main-books](list-main-books.md) ispisuje glavne knjige, u kojima je
  većina zemljišnoknjižnih uložaka.
- [get-lr-unit](get-lr-unit.md) daje uvid u zemljišnoknjižni uložak.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz kpu --help`:

```text
Uporaba: uz kpu [OPCIJE]

  Popis knjiga položenih ugovora (KPU).

  Knjiga položenih ugovora sadrži stanove prodane prije nego što je zgrada
  dobila zemljišnoknjižni uložak. Popis daje identifikator knjige i
  zemljišnoknjižni odjel koji je vodi.

  Primjeri:
    uz kpu --traži ZADAR
    uz kpu --ured 284 --oblik json

Opcije:
  -tr, --traži TEKST              Pretraga po nazivu knjige
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
