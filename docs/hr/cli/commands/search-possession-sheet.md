<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/search-possession-sheet.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Pronađite posjedovni list po broju

Posjedovni list je katastarski zapis o tome tko posjeduje skupinu čestica. Ova
naredba provjerava postoji li broj lista u katastarskoj općini i prikazuje broj
pod kojim ga katastar interno vodi.

## Kada vam ovo treba

- Dokument navodi broj posjedovnog lista i želite potvrditi da on postoji u toj
  katastarskoj općini.
- Upisali ste dio broja lista i želite vidjeti koji listovi njime počinju.

## Prije nego počnete

Trebaju vam broj posjedovnog lista i katastarska općina; oboje je obično
otisnuto na izvatku iz posjedovnog lista.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz traži-posjedovni-list 363 -ko SAVAR
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz traži-posjedovni-list 363 -ko SAVAR -->
   ```text
   +--------------+------------+
   |   Broj lista |   ID lista |
   +==============+============+
   |          363 |   11731543 |
   +--------------+------------+

   💡 Posjednici i čestice lista: cadastral get-possession-sheet <BROJ_LISTA> -m 334979 --show-owners
   ```
   <!-- END GENERATED: output -->

4. Ispisan je svaki list čiji broj počinje onim što ste upisali. **ID lista** je
   interni broj lista u katastru; u pravilu vam neće trebati.

## Što možete odabrati

Ova naredba samo potvrđuje list. Za sam list, s posjednicima i svim česticama na
njemu, upotrijebite [get-possession-sheet](get-possession-sheet.md) s točnim
brojem.

`--format json` uz `--output` sprema rezultat kao datoteku.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `BROJ_POSJEDOVNOG_LISTA` | Vrijednost koju upisujete odmah iza naziva naredbe, bez naziva ispred nje | Obavezno |
| `--općina`, `-ko` `TEKST` | Naziv ili šifra općine (npr. SAVAR ili 334979) | Obavezno |
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako nijedan list ne počinje brojem koji ste upisali, alat staje s ovim retkom:

<!-- BEGIN GENERATED: output uz traži-posjedovni-list 999 -ko SAVAR -->
```text
✗ Greška: Posjedovni list '999' nije pronađen u katastarskoj općini SAVAR
```
<!-- END GENERATED: output -->

Provjerite broj i katastarsku općinu na vašem dokumentu. Ostale poruke
objašnjene su na [stranici o greškama](../errors.md).

## Povezane stranice

- [get-possession-sheet](get-possession-sheet.md) prikazuje list s njegovim
  posjednicima i česticama.
- [get-parcel](get-parcel.md) prikazuje posjedovni list čestice s njezinim
  posjednicima.
- [search](search.md) pronalazi česticu po broju.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz traži-posjedovni-list --help`:

```text
Uporaba: uz traži-posjedovni-list [OPCIJE] BROJ_POSJEDOVNOG_LISTA

  Pronađi posjedovni list po broju.

  Prikazuje brojeve listova koji počinju zadanim brojem i interni ID svakog
  lista. Za sam list, s posjednicima i česticama, upotrijebite naredbu
  posjedovni-list s točnim brojem.

  Primjeri:
    uz traži-posjedovni-list 363 -ko SAVAR
    uz traži-posjedovni-list 36 -ko 334979 --oblik json

Opcije:
  -ko, --općina TEKST             Naziv ili šifra općine (npr. SAVAR ili 334979)
                                  [obavezno]
  -ob, --oblik [tablica|json|csv]
                                  Format izlaza
  -dt, --datoteka PUTANJA         Spremi izlaz u datoteku
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
