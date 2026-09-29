<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/get-geometry.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Granica čestice za kartu

Ispisuje lomne točke čestice u službenom hrvatskom koordinatnom sustavu, tako da
je geodet ili kartografski program može nacrtati. Može izračunati i površinu iz
tih točaka.

## Kada vam ovo treba

- Želite geodetu ili arhitektu predati točan obris čestice.
- Želite usporediti površinu izračunatu iz granice s površinom upisanom u
  katastru.
- Želite smjestiti česticu na kartu u programu koji razumije geografske podatke.

## Prije nego počnete

Trebate broj čestice i katastarsku općinu. Podaci o granicama cijele općine
preuzimaju se jednom i čuvaju na vašem računalu; prvi dohvat u nekoj općini
stoga traje dulje od sljedećih.

Koordinate su u sustavu HTRS96/TM (EPSG:3765), službenoj projekciji za Hrvatsku.
To nisu stupnjevi kakve vidite u automobilskoj navigaciji. Kartografski program
znat će što s njima.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz granica 103/2 -ko SAVAR --statistika
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz granica 103/2 -ko SAVAR --statistika -->
   ```text
   STATISTIKA GEOMETRIJE
   =====================
     Čestica               103/2
     Koordinatni sustav    EPSG:3765
     Vrhovi                5
     Površina (GIS)        1200.00 m²

     Granični okvir
       Min X               380,596.77 m
       Min Y               4,880,892.83 m
       Max X               380,636.77 m
       Max Y               4,880,922.83 m
       Širina              40.00 m
       Visina              30.00 m

     URL karte             https://oss.uredjenazemlja.hr/map?center=380616.77,4880907.83&zoom=19&laye
                           rs=DOF5_2023_2024,DKP_CESTICE,DKP_KATASTARSKE_OPCINE,zupanija,ulica,kucni_
                           broj

   POLYGON((380596.77 4880892.83, 380636.77 4880892.83, 380636.77 4880922.83, 380596.77 4880922.83, 380596.77 4880892.83))
   ```
   <!-- END GENERATED: output -->

4. **STATISTIKA GEOMETRIJE** sažima oblik: broj lomnih točaka (**Vrhovi**),
   površinu izračunatu iz njih (**Površina (GIS)**), najmanji pravokutnik koji
   obuhvaća česticu (**Granični okvir**) i poveznicu (**URL karte**) koja otvara
   službenu interaktivnu kartu centriranu na česticu. Zadnji blok je sama
   granica, zapisana kao poligon u standardnom tekstualnom obliku. Svaki par
   brojeva jedna je lomna točka.

## Što možete odabrati

`--oblik` bira oblik granice. `wkt` je standardni tekstualni oblik prikazan
gore. `geojson` je oblik koji čita većina web karata. `csv` daje jednu lomnu
točku po retku za tablicu. `json` daje iste podatke za druge programe. Oblici
`geojson` i `json` sadrže i poveznicu na kartu (`map_url`; u obliku `json` ključ
je `url_karte`).

Da biste granicu nekome predali, zapišite je u datoteku pomoću `--datoteka`.
GeoJSON datoteku možete povući na mnoge mrežne preglednike karata:

```bash
uz granica 103/2 -ko SAVAR --oblik geojson --datoteka parcel-103-2.geojson
```

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `BROJ_ČESTICE` | Vrijednost koju upisujete odmah iza naziva naredbe, bez naziva ispred nje | Obavezno |
| `--općina`, `-ko` `TEKST` | Naziv ili šifra općine | Obavezno |
| `--oblik`, `-ob` | Format izvoza (`wkt`, `geojson`, `csv`, `json`) | Koristi se `wkt` |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--statistika` | Uključi statistiku geometrije | Nije uključeno |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako čestice nema u podacima o granicama općine, vidjet ćete ovo:

<!-- BEGIN GENERATED: output uz granica 999 -ko SAVAR -->
```text
✗ Greška: Geometrija nije pronađena za česticu '999'

Napomena: GIS podaci moraju biti prvo preuzeti (to se događa automatski)
```
<!-- END GENERATED: output -->

Podaci o granicama i katastar nisu uvijek usklađeni; prvo provjerite česticu
naredbom [pretraži](search.md).

Ako se podaci o granicama općine ne mogu preuzeti, pitajte osobu koja je
instalirala alat je li probni poslužitelj pokrenut. Ostale poruke objašnjene su
na [stranici o greškama](../errors.md).

## Povezane stranice

- [preuzmi-gis](download-gis.md) preuzima podatke o granicama cijele općine.
- [predmemorija popis](cache-list.md) pokazuje koje su općine već na vašem
  računalu.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz granica --help`:

```text
Uporaba: uz granica [OPCIJE] BROJ_ČESTICE

  Dohvat koordinata granica čestice za GIS integraciju.

  Primjeri:
    uz granica 103/2 -ko SAVAR
    uz granica 103/2 -ko 334979 --oblik wkt
    uz granica 103/2 -ko 334979 --oblik geojson -dt parcel.geojson
    uz granica 103/2 -ko 334979 --oblik csv -dt coords.csv

Opcije:
  -ko, --općina TEKST             Naziv ili šifra općine  [obavezno]
  -ob, --oblik [wkt|geojson|csv|json]
                                  Format izvoza
  -dt, --datoteka PUTANJA         Spremi izlaz u datoteku
  --statistika                    Uključi statistiku geometrije
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
