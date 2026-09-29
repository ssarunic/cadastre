<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/get-parcel.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Sve što katastar ima o čestici

Potpuni katastarski zapis jedne čestice: položaj, površina, način uporabe
zemljišta, posjedovni list s osobama koje katastar vodi i broj zemljišnoknjižnog
uloška u kojem su pravni vlasnici.

## Kada vam ovo treba

- Pripremate ugovor i trebate površinu, način uporabe zemljišta i katastarsko
  stanje čestice na jednom mjestu.
- Želite usporediti koga katastar vodi kao posjednika s onim koga zemljišna
  knjiga vodi kao vlasnika.
- Trebate broj zemljišnoknjižnog uloška čestice da biste pročitali njegove
  vlasnike i terete.
- Imate popis čestica, iz ugovora ili iz tablice, i želite isti zapis za svaku
  od njih.

## Prije nego počnete

Trebate broj čestice i katastarsku općinu, po nazivu ili šifri, kao za
[pretraži](search.md).

Dok čitate, imajte na umu jednu razliku. Katastar vodi posjednike; zemljišna
knjiga vodi vlasnike. Često su to iste osobe, ali ne uvijek, a samo je zemljišna
knjiga dokaz vlasništva. Ova stranica prikazuje katastar. Stranica
[uložak](get-lr-unit.md) prikazuje zemljišnu knjigu.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz čestica 103/2 -ko SAVAR --posjednici
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz čestica 103/2 -ko SAVAR --posjednici -->
   ```text
   INFORMACIJE O ČESTICI
   =====================
     Broj čestice             103/2
     ID čestice               6564817
     Općina                   SAVAR (334979)
     Adresa                   POLJE
     Površina                 1,200 m²
     Dozvoljeno građenje      Ne
     Katastar/ZK usklađeni    Da


   NAČIN UPORABE
   =============
     Vrsta        Površina (m²)    Postotak    Zgrade    Zadnja promjena
     MASLINJAK            1,200      100.0%    Ne        -


   POSJEDOVNI LIST (katastar) (2 posjednika)
   =========================================
   Napomena: posjednici u katastru mogu se razlikovati od upisanih vlasnika. Za vlasnike iz zemljišnih
   knjiga koristite: cadastral get-lr-unit
     Naziv                    Vlasništvo    Adresa
     IVIĆ MARKO, SIN PETRA           N/D    TESTNA ULICA 15, SPLIT
     IVIĆ ANA, KĆI PETRA             N/D    SAVAR


   ZEMLJIŠNA KNJIGA
   ================
     Broj uloška      657
     Glavna knjiga    N/D
     Institucija      N/D
     Status           Neaktivno
     Provjereno       Ne


   DODATNE INFORMACIJE
   ===================
     URL karte        https://oss.uredjenazemlja.hr/map?center=380616.77,4880907.83&zoom=19&layers=DO
                      F5_2023_2024,DKP_CESTICE,DKP_KATASTARSKE_OPCINE,zupanija,ulica,kucni_broj
     List pregleda    4
   ```
   <!-- END GENERATED: output -->

4. Zaslon ima pet dijelova. **INFORMACIJE O ČESTICI** određuje česticu; redak
   **Katastar/ZK usklađeni** kaže slažu li se katastar i zemljišna knjiga o
   njoj. **NAČIN UPORABE** dijeli površinu po katastarskoj kulturi. **POSJEDOVNI
   LIST (katastar)** ispisuje posjednike koje katastar vodi, s udjelom gdje ga
   katastar ima. **ZEMLJIŠNA KNJIGA** daje broj zemljišnoknjižnog uloška (**Broj
   uloška**) koji zatim možete potražiti. **DODATNE INFORMACIJE** sadrži
   poveznicu koja otvara česticu na javnoj karti.

5. Gdje vrijednost nije upisana, alat ispisuje **N/D**. U posjedovnom listu to
   je često: katastar nerijetko vodi tko posjeduje, a ne vodi udio.

## Što možete odabrati

Bez `--posjednici` posjedovni list se izostavlja i zaslon je kraći. Dodajte ga
kad god želite vidjeti osobe.

`--detalji` sužava zaslon na jedan dio: `basic` samo za identifikaciju, `owners`
za posjedovni list, `landuse` za podjelu po načinu uporabe, `geometry` za
koordinate granice, `registry` za zemljišnoknjižni uložak, `full` za sve.

Čestica zgrade na dokumentima se piše kao `35/1 ZGR`, `35/1.ZGR` ili `zgr.
35/1`. Upišite je u bilo kojem od tih oblika; alat je prikazuje kao `zgr. 35/1`
i označuje kao česticu zgrade. Čestice zgrade nemaju vlastiti zemljišnoknjižni
uložak, jer je zgrada upisana na svojoj zemljišnoj čestici.

```bash
uz čestica 35/1.ZGR -ko SAVAR --detalji basic
```

```bash
uz čestica 103/2 -ko SAVAR --detalji landuse
```

Da zapis spremite u datoteku, dodajte `--oblik json` i `--datoteka` s nazivom
datoteke. Taj oblik koristite kad podatke želite priložiti spisu ili
proslijediti kolegi.

```bash
uz čestica 103/2 -ko SAVAR --posjednici --oblik json --datoteka parcel-103-2.json
```

Za pretragu više čestica odjednom upišite njihove brojeve odvojene zarezima,
unutar navodnika. Dodajte `--detalji registry` da dobijete jedan redak po
čestici s njezinom površinom, ID-om čestice i zemljišnoknjižnim uloškom kojem
pripada:

```bash
uz čestica "103/2,45,396/1" -ko SAVAR --detalji registry
```

<!-- BEGIN GENERATED: output uz čestica "103/2,45,396/1" -ko SAVAR --detalji registry -->
```text
📊 Pronađene 3 čestice za obradu


REZULTATI
=========
                                               Površina                               Glavna
  #    Status    Čestica    Općina                 (m²)    ID čestice    ZK uložak    knjiga
  1      ✓       103/2      SAVAR                 1,200    6564817       657          21277
                            (334979)
  2      ✓       45         SAVAR                   981    6564715       138          21277
                            (334979)
  3      ✓       396/1      SAVAR                 2,077    6565198       645          21277
                            (334979)

✓ Uspješno obrađene sve 3 čestice
```
<!-- END GENERATED: output -->

Svaki redak tablice **REZULTATI** jedna je čestica. **Status** pokazuje kvačicu
za pronađenu i križić za nepronađenu česticu. **ZK uložak** i **Glavna knjiga**
označavaju zemljišnoknjižni uložak čestice, a to je ono što naredbi
[uložak](get-lr-unit.md) treba u sljedećem koraku. Bez `--detalji registry`
ispisuje se potpuni zapis svake čestice, jedan za drugim.

Za dulji popis pripremite datoteku. Najjednostavnija je CSV datoteka, koju
možete spremiti iz bilo kojeg programa za tablice. Ima dva stupca,
`broj_cestice` i `opcina`, i izgleda ovako:

<!-- BEGIN GENERATED: file parcels.csv -->
```text
broj_cestice,opcina
103/2,SAVAR
45,
396/1,
```
<!-- END GENERATED: file -->

Prazno polje općine znači „isto kao u retku iznad”. Prihvaća se i JSON datoteka
istog sadržaja. Primjeri datoteka: [parcels.csv](../examples/parcels.csv),
[parcels.json](../examples/parcels.json). Otvorite Terminal u mapi u kojoj je
datoteka i navedite je uz `--ulaz`:

```bash
uz čestica --ulaz parcels.csv --detalji registry
```

Za nastavak prema zemljišnoj knjizi spremite rezultat kao JSON datoteku pomoću
`--oblik json` i `--datoteka`. Stranica [uložak](get-lr-unit.md) tu datoteku
može izravno pročitati:

```bash
uz čestica "103/2,279/6,1122/1" -ko SAVAR --detalji registry --oblik json --datoteka parcels-found.json
uz uložak --ulaz parcels-found.json --sve
```

Nazivi polja u JSON ili CSV datoteci slijede jezik alata, pa kolega koji ga
pokreće na drugom jeziku dobiva nazive tog jezika. Alat datoteke čita natrag na
oba jezika.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `ČESTICE` | Neobavezno. Vrijednost koju upisujete odmah iza naziva naredbe | Ne koristi se |
| `--ulaz`, `-ul` `PUTANJA` | Datoteka (CSV ili JSON) s česticama za pretragu, umjesto upisivanja | Ne koristi se |
| `--općina`, `-ko` `TEKST` | Naziv ili šifra općine (obavezno osim uz --ulaz) | Ne koristi se |
| `--detalji` | Razina detalja; registry ispisuje svaku česticu s njezinim ZK uloškom (`basic`, `full`, `owners`, `landuse`, `geometry`, `registry`) | Koristi se `full` |
| `--posjednici` | Uključi vlasničke podatke | Nije uključeno |
| `--geometrija` | Uključi koordinate granica | Nije uključeno |
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--nastavi-kod-greške` / `--stani-kod-greške` | Nastavi obradu nakon grešaka (zadano: nastavi) | Koristi se `--nastavi-kod-greške` |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako općina nije prepoznata, alat to kaže i staje:

<!-- BEGIN GENERATED: output uz čestica 103/2 -ko NOWHERE -->
```text
✗ Greška: Općina 'NOWHERE' nije pronađena

Prijedlozi:
  • Pretražite općine: cadastral search-municipality NOWHERE
  • Ispišite sve općine: cadastral list-municipalities
  • Koristite šifru općine izravno: --municipality 334979
```
<!-- END GENERATED: output -->

Provjerite pravopis ili umjesto naziva upotrijebite šifru. Možete je pronaći
naredbom [traži-općinu](search-municipality.md).

Ako čestica nije pronađena, provjerite broj na svom dokumentu, uključujući dio
iza kose crte. Ostale poruke objašnjene su na [stranici o
greškama](../errors.md).

Čestica koja ne postoji ne prekida popis. Dobiva križić u stupcu **Status** i
objašnjenje u tablici **GREŠKE** na kraju:

<!-- BEGIN GENERATED: output uz čestica "103/2,999" -ko SAVAR --detalji registry -->
```text
📊 Pronađene 2 čestice za obradu


REZULTATI
=========
                                               Površina                               Glavna
  #    Status    Čestica    Općina                 (m²)    ID čestice    ZK uložak    knjiga
  1      ✓       103/2      SAVAR                 1,200    6564817       657          21277
                            (334979)
  2      ✗       999        SAVAR               Čestica    -             -            -
                                                   nije
                                              pronađena

GREŠKE
======
  #    Čestica        Vrsta greške              Poruka greške
  2    999 (SAVAR)    Čestica nije pronađena    Čestica nije pronađena (parcel_number=999,
                                                municipality_reg_num=334979)

⚠️  Obrađeno 1/2 čestica (50.0% stopa uspjeha)
   1 čestica nije uspjela - pogledajte ispis za detalje
```
<!-- END GENERATED: output -->

Ispravite broj i ponovno pokrenite naredbu samo za tu česticu. Ako radije želite
stati kod prvog problema, dodajte `--stani-kod-greške`. Ako alat ne može pronaći
datoteku koju ste naveli uz `--ulaz`, provjerite je li Terminal u mapi u kojoj
je datoteka, ili upišite njezinu punu putanju.

## Povezane stranice

- [uložak](get-lr-unit.md) čita zemljišnoknjižni uložak čiji se broj pojavljuje
  pod naslovom zemljišne knjige.
- [pretraži](search.md) je kraći oblik ove naredbe.
- [granica](get-geometry.md) daje granicu čestice za kartu.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz čestica --help`:

```text
Uporaba: uz čestica [OPCIJE] ČESTICE

  Dohvat potpunih podataka o čestici s podacima o posjedu.

  Jedna čestica ili popis čestica: više brojeva odvojenih zarezima (ili zadanih
  kao zasebni argumenti), ili datoteka uz --ulaz. Za popis je rezultat jedan
  zapis po čestici s njezinim statusom; čestica koja nije pronađena ne
  zaustavlja ostale.

  Primjeri:
    uz čestica 103/2 -ko SAVAR
    uz čestica 103/2 -ko 334979 --posjednici
    uz čestica 103/2 -ko 334979 --detalji owners
    uz čestica 103/2 -ko 334979 --oblik json -dt parcel.json

    # Popis: jedan redak po čestici s njezinim ZK uloškom
    uz čestica "103/2,45,396/1" -ko SAVAR --detalji registry

    # Popis iz datoteke (CSV ili JSON), spremljen kao JSON za uložak --ulaz
    uz čestica --ulaz parcels.csv --detalji registry --oblik json -dt parcels-found.json

  CSV datoteka (prazno polje općine ponavlja redak iznad):
    parcel_number,municipality
    103/2,SAVAR
    45,

  JSON datoteka:
    [{"parcel_number": "103/2", "municipality": "SAVAR"}, {"parcel_id": "6564715"}]

Opcije:
  -ul, --ulaz PUTANJA             Datoteka (CSV ili JSON) s česticama za
                                  pretragu, umjesto upisivanja
  -ko, --općina TEKST             Naziv ili šifra općine (obavezno osim uz
                                  --ulaz)
  --detalji [basic|full|owners|landuse|geometry|registry]
                                  Razina detalja; registry ispisuje svaku
                                  česticu s njezinim ZK uloškom
  --posjednici                    Uključi vlasničke podatke
  --geometrija                    Uključi koordinate granica
  -ob, --oblik [tablica|json|csv]
                                  Format izlaza
  -dt, --datoteka PUTANJA         Spremi izlaz u datoteku
  --nastavi-kod-greške / --stani-kod-greške
                                  Nastavi obradu nakon grešaka (zadano: nastavi)
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
