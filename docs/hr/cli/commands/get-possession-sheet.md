<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/get-possession-sheet.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Pogledajte posjedovni list s njegovim česticama

Posjedovni list je katastarski zapis o tome tko posjeduje skupinu čestica. Ova
naredba prikazuje cijeli list: svaku česticu na njemu, s površinom, načinom
uporabe i zemljišnoknjižnim uloškom, a na zahtjev i posjednike upisane na listu.

## Kada vam ovo treba

- Ostavinsko rješenje navodi posjedovni list, a vi želite popis čestica na njemu
  prije nego što svaku potražite u zemljišnoj knjizi.
- Klijent kaže „naša je zemlja na posjedovnom listu 363", a vi želite vidjeti
  koliko je to zemlje i koga katastar bilježi kao posjednika.
- Želite provjeriti je li čestica koju netko spominje na istom listu kao i
  ostale.

## Prije nego počnete

Trebate točan broj posjedovnog lista i katastarsku općinu; oboje je otisnuto na
izvatku iz posjedovnog lista i na većini ostavinskih rješenja. Ako znate samo
početak broja, [search-possession-sheet](search-possession-sheet.md) nabraja
listove koji njime počinju.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz posjedovni-list 363 -ko SAVAR
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz posjedovni-list 363 -ko SAVAR -->
   ```text
   POSJEDOVNI LIST
   ===============
     Broj lista         363
     ID lista           11731543
     Općina             SAVAR (334979)
     Posjednici         119
     Čestice            7
     Ukupna površina    127,299 m²

   ČESTICE
   =======
     Broj čestice    Površina (m²)    Način uporabe     Katastar/ZK usklađeni    ZK uložak
     1090                   48,494    PAŠNJAK 48,494             Ne              866 / 21277
     1098/1                  4,863    PAŠNJAK 4,863              Ne              866 / 21277
     1110/1                  2,604    PAŠNJAK 2,604              Ne              866 / 21277
     1111/1                  8,610    PAŠNJAK 8,610              Ne              866 / 21277
     1122/1                  1,618    VINOGRAD 1,618             Ne              449 / 21277
     1131/6                 59,747    CESTA 59,747               Ne              866 / 21277
     1198                    1,363    PAŠNJAK 1,363              Ne              866 / 21277

   💡 Upisani vlasnici (zemljišna knjiga): cadastral get-lr-unit --unit-number <ULOŽAK> --main-book
   <GLAVNA_KNJIGA> --show-owners
   ```
   <!-- END GENERATED: output -->

4. Prvi blok imenuje list i broji što je na njemu. **Ukupna površina** zbraja
   katastarske površine čestica. Tablica **ČESTICE** nabraja svaku česticu:
   **Način uporabe** je katastarska klasifikacija s površinom svake vrste,
   **Katastar/ZK usklađeni** kaže slažu li se katastar i zemljišna knjiga o
   čestici, a **ZK uložak** daje zemljišnoknjižni uložak i glavnu knjigu koje
   predajete naredbi [get-lr-unit](get-lr-unit.md) za upisane vlasnike.

## Što možete odabrati

Dodajte `--show-owners` da vidite posjednike upisane na listu, s udjelima i
adresama. To su posjednici prema katastru, ne upisani vlasnici; upisani vlasnici
su u zemljišnoknjižnom ulošku iz stupca **ZK uložak**, a posljednji redak ispisa
pokazuje naredbu koja ga čita.

Neki su listovi usklađeni sa zemljišnom knjigom: za njih katastar ne bilježi
vlastite posjednike, nego upućuje na zemljišnoknjižni uložak. Alat tada u retku
**Posjednici** ispisuje **u zemljišnoj knjizi (usklađeni list)**, a uz
`--show-owners` nabraja upisane vlasnike tog uloška pod **UPISANI VLASNICI
(ZEMLJIŠNA KNJIGA)**; u JSON-u je `posjednici_u_zemljisnoj_knjizi` `true`, a
osobe su pod `vlasnici`.

`--format json` zapisuje list kao jedan dokument, s `cestice`, `broj_cestica`,
`ukupna_povrsina_m2` i `popis_cestica_potpun`; `--format csv` zapisuje jedan
redak po čestici. Oboje ide u datoteku uz `--output`.

Katastarsko pretraživanje čestica nikad nije vratilo više od 30 čestica za jedan
list. Kad se list vrati s točno toliko čestica, alat upozorava da popis možda
nije potpun, a `popis_cestica_potpun` je `false`; u tom slučaju provjerite
izvadak iz posjedovnog lista.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `BROJ_POSJEDOVNOG_LISTA` | Vrijednost koju upisujete odmah iza naziva naredbe, bez naziva ispred nje | Obavezno |
| `--općina`, `-ko` `TEKST` | Naziv ili šifra općine (npr. SAVAR ili 334979) | Obavezno |
| `--posjednici` | Uključi posjednike upisane na listu | Nije uključeno |
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako u katastarskoj općini nema lista s tim točnim brojem, alat staje s ovim
retkom:

<!-- BEGIN GENERATED: output uz posjedovni-list 999 -ko SAVAR -->
```text
✗ Greška: Posjedovni list '999' nije pronađen u katastarskoj općini SAVAR
```
<!-- END GENERATED: output -->

Provjerite broj na svom dokumentu; broj mora biti potpun, pa pokušajte
[search-possession-sheet](search-possession-sheet.md) ako znate samo kako
počinje. Ostale poruke objašnjene su na [stranici o greškama](../errors.md).

## Povezane stranice

- [get-lr-unit](get-lr-unit.md) prikazuje upisane vlasnike i terete
  zemljišnoknjižnog uloška kojem čestica pripada.
- [get-parcel](get-parcel.md) prikazuje jednu česticu u cijelosti, s njezinim
  posjedovnim listom.
- [search-possession-sheet](search-possession-sheet.md) pronalazi listove čiji
  broj počinje zadanim tekstom.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz posjedovni-list --help`:

```text
Uporaba: uz posjedovni-list [OPCIJE] BROJ_POSJEDOVNOG_LISTA

  Dohvati posjedovni list s njegovim česticama.

  Prikazuje list, svaku česticu na njemu s površinom, načinom uporabe i
  zemljišnoknjižnim uloškom, a s --posjednici posjednike upisane na listu. Broj
  se traži točno; traži-posjedovni-list nabraja listove čiji broj počinje
  zadanim tekstom.

  Primjeri:
    uz posjedovni-list 363 -ko SAVAR
    uz posjedovni-list 363 -ko SAVAR --posjednici
    uz posjedovni-list 363 -ko 334979 --oblik json -dt list.json

Opcije:
  -ko, --općina TEKST             Naziv ili šifra općine (npr. SAVAR ili 334979)
                                  [obavezno]
  --posjednici                    Uključi posjednike upisane na listu
  -ob, --oblik [tablica|json|csv]
                                  Format izlaza
  -dt, --datoteka PUTANJA         Spremi izlaz u datoteku
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
