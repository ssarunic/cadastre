<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/get-zoning.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Saznajte je li čestica u građevinskom području

Kaže vam gdje čestica leži u odnosu na građevinska područja prostornih planova:
unutar građevinskog područja naselja, u izdvojenom području izvan naselja
(turističko naselje, kamp, gospodarska zona) ili izvan svih građevinskih
područja. Navodi zonu, njezinu oznaku namjene i plan iz kojega potječe. Ne
govori vam smije li se ondje što graditi.

## Kada vam ovo treba

- Stranka namjerava kupiti česticu i želite prvu provjeru leži li uopće u
  građevinskom području, prije čitanja plana.
- Želite znati je li čestica u turističkoj zoni prije procjene vrijednosti.
- Provjeravate koji se prostorni plan odnosi na česticu prije nego što od općine
  zatražite lokacijsku informaciju.

## Prije nego počnete

Trebate broj čestice i katastarsku općinu, kao i za [granica](get-geometry.md).
Podaci o granicama općine preuzimaju se jednom i čuvaju na vašem računalu.

Odgovor dolazi iz građevinskih područja koja su županijski zavodi za prostorno
uređenje iscrtali iz važećih planova. To je interpretacija planova, a ne sami
planovi: alat to kaže na kraju svakog odgovora, a za službeni odgovor i dalje
trebate plan ili lokacijsku informaciju općine.

Položaj unutar građevinskog područja nije dozvola za gradnju. Odredbe plana,
veličinu građevne čestice, pristup, komunalnu opremu, zaštićena područja i
obvezu izrade detaljnijeg plana ovaj alat ne provjerava, pa redak **Mogućnost
gradnje** uvijek kaže da nije utvrđena.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz namjena 396/1 -ko SAVAR
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz namjena 396/1 -ko SAVAR -->
   ```text
   PROSTORNI PLAN: GRAĐEVINSKA PODRUČJA
   ====================================
     Čestica              396/1
     Općina               334979
     Površina (GIS)       2077.00 m²
     Status               U izdvojenom građevinskom području izvan naselja
     Mogućnost gradnje    Nije utvrđena (samo provjera)
     Planovi              PPUO SALI - III. ID

                                                   Zone
   ┏━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
   ┃ Vrsta     ┃ Šifra ┃ Namjena                       ┃ Zona         ┃ Plan                ┃ Preklop ┃
   ┡━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
   │ izdvojeno │ T3    │ GOSPODARSKA - UGOSTITELJSKO   │ SAVAR - KAMP │ PPUO SALI - III. ID │ 27%     │
   │           │       │ TURISTIČKA (KAMP)             │              │                     │         │
   └───────────┴───────┴───────────────────────────────┴──────────────┴─────────────────────┴─────────┘

   Građevinska područja interpretacija su prostornih planova koju su izradili županijski zavodi za
   prostorno uređenje i mogu odstupati od važećih prostornih planova. Ne smiju se koristiti za
   izdavanje akata za provedbu zahvata u prostoru ni drugih javnih isprava; u službene svrhe koristite
   izvornike važećih prostornih planova.
   Izvor: Građevinska područja (MPGI)
   Smije li se što graditi ovdje se ne utvrđuje; pročitajte plan ili zatražite lokacijsku informaciju.
   ```
   <!-- END GENERATED: output -->

4. **Status** je kratki odgovor: unutar građevinskog područja naselja, u
   izdvojenom građevinskom području izvan naselja, dodiruje građevinsko područje
   ispod praga preklopa ili izvan građevinskih područja. Tablica **Zone** navodi
   svaku zonu koja pokriva dio čestice, s njezinom oznakom (**Šifra**, na
   primjer `T3` za kamp ili `GPN` za područje naselja), namjenom kako je
   zapisana u planu (**Namjena**), nazivom zone (**Zona**), planom iz kojega je
   očitana (**Plan**) i udjelom čestice koji pokriva (**Preklop**). Žuta
   napomena na kraju upozorenje je koje mora pratiti svaku uporabu ovog
   odgovora.

## Što možete odabrati

`--oblik` bira oblik odgovora. `tablica` je ono što vidite gore. `json` daje
iste podatke za druge programe, uključujući oznaku plana te županiju i općinu
zone. `csv` daje jedan redak po zoni za tablicu, uključujući zone ispod praga,
koje su označene u stupcu `podudaranje`. `geojson` daje obrise zona za
kartografski program, označene na isti način; dodajte `--geometrija` da ih
uključite i u oblik `json`.

Zone koje pokrivaju tek rub čestice navode se odvojeno, ispod tablice, jer se
granice planova crtaju na kartama sitnog mjerila i rijetko točno prate granice
čestica. `--najmanji-preklop` postavlja taj prag kao postotak čestice, između 0
i 100; uobičajena vrijednost je 2.

Da biste odgovor sačuvali, zapišite ga u datoteku pomoću `--datoteka`:

```bash
uz namjena 396/1 -ko SAVAR --oblik csv --datoteka zoning-396-1.csv
```

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `BROJ_ČESTICE` | Vrijednost koju upisujete odmah iza naziva naredbe, bez naziva ispred nje | Obavezno |
| `--općina`, `-ko` `TEKST` | Naziv ili šifra općine | Obavezno |
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`, `geojson`) | Koristi se `tablica` |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--geometrija` | Uključi poligone zona u JSON ispis | Nije uključeno |
| `--najmanji-preklop` `FLOAT RANGE` | Zone koje pokrivaju manji udio čestice od ovoga (postotak) navode se odvojeno | Koristi se `2.0` |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako čestice nema u podacima o granicama općine, vidjet ćete ovo:

<!-- BEGIN GENERATED: output uz namjena 999 -ko SAVAR -->
```text
✗ Greška: Geometrija nije pronađena za česticu '999'

Napomena: GIS podaci moraju biti prvo preuzeti (to se događa automatski)
```
<!-- END GENERATED: output -->

Podaci o granicama i katastar nisu uvijek usklađeni; prvo provjerite česticu
naredbom [pretraži](search.md).

Ako odgovor kaže da građevinska područja nisu dostupna, servis planova ne radi
ili alat za njega nije postavljen; obratite se osobi koja je alat instalirala.
Ostale poruke objašnjene su na [stranici o pogreškama](../errors.md).

## Povezane stranice

- [granica](get-geometry.md) prikazuje granicu čestice na kojoj se odgovor
  temelji.
- [čestica](get-parcel.md) prikazuje što katastar bilježi o čestici.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz namjena --help`:

```text
Uporaba: uz namjena [OPCIJE] BROJ_ČESTICE

  Saznajte u kojem je građevinskom području prostornog plana čestica.

  Uspoređuje granicu čestice s građevinskim područjima izvedenima iz važećih
  prostornih planova: unutar naselja, u izdvojenom području s njegovom namjenom
  (na primjer T2 turističko naselje) ili izvan njih. Ovo je samo provjera: ne
  govori smije li se što graditi, a rezultat je interpretacija planova, a ne
  sami planovi.

  Primjeri:
    uz namjena 103/2 -ko SAVAR
    uz namjena 396/1 -ko 334979 --oblik json
    uz namjena 45 -ko SAVAR --oblik csv -dt namjena.csv
    uz namjena 103/2 -ko SAVAR --oblik geojson --geometrija

Opcije:
  -ko, --općina TEKST             Naziv ili šifra općine  [obavezno]
  -ob, --oblik [tablica|json|csv|geojson]
                                  Format izlaza
  -dt, --datoteka PUTANJA         Spremi izlaz u datoteku
  --geometrija                    Uključi poligone zona u JSON ispis
  --najmanji-preklop FLOAT RANGE  Zone koje pokrivaju manji udio čestice od
                                  ovoga (postotak) navode se odvojeno  [zadano:
                                  2.0; 0<=x<=100]
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
