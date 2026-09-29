<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/search.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Brza provjera čestice

Upišite broj čestice i katastarsku općinu i dobit ćete osnovne podatke na jednom
zaslonu: gdje je čestica, kolika je, čemu zemljište služi i koliko osoba
katastar na njoj vodi.

## Kada vam ovo treba

- Klijent spominje česticu i želite potvrditi da postoji prije nego nastavite.
- Trebate površinu i način uporabe zemljišta čestice za ugovor ili procjenu.
- Želite matični broj općine i interni broj čestice za kasniji, detaljniji
  dohvat.

## Prije nego počnete

Trebate dvoje: broj katastarske čestice (na primjer 103/2) i katastarsku općinu
kojoj pripada. Oboje je na svakom izvatku iz katastra ili zemljišne knjige i na
većini ugovora.

Općinu možete zadati nazivom (SAVAR) ili šifrom (334979). Alat prihvaća oboje.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz pretraži 103/2 -ko SAVAR
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz pretraži 103/2 -ko SAVAR -->
   ```text
   Broj čestice         103/2
   Općina               SAVAR (334979)
   Adresa               POLJE
   Površina             1,200 m²
   Način uporabe        MASLINJAK
   Dozvoljeno građenje  Ne
   Posjednici           2 posjednika

   💡 Za potpune detalje: cadastral get-parcel 103/2 -m 334979
   ```
   <!-- END GENERATED: output -->

4. Čitajte retke odozgo prema dolje. **Broj čestice** i **Općina** potvrđuju da
   je alat pronašao česticu koju ste mislili. **Površina** je površina u
   četvornim metrima. **Način uporabe** je katastarska kultura, u rječniku
   katastra. **Dozvoljeno građenje** kaže je li prema katastru na čestici
   dopušteno graditi. **Posjednici** je broj osoba koje katastar vodi na
   čestici. To su posjednici, a ne nužno vlasnici; vlasnike vodi zemljišna
   knjiga.

5. Zadnji redak predlaže naredbu za potpune detalje. Kopirajte je ako trebate
   više od ovog sažetka.

## Što možete odabrati

Dio iza `-ko` je općina. Može biti naziv ili šifra. Ako dvije općine dijele
naziv, upotrijebite šifru, koju možete pronaći naredbom
[traži-općinu](search-municipality.md).

Ako znate samo početak broja čestice, dodajte `--djelomično` da vidite sve
čestice koje počinju onim što ste upisali:

```bash
uz pretraži 1 -ko SAVAR --djelomično
```

Da rezultat spremite u datoteku umjesto čitanja na zaslonu, dodajte `--oblik
json` ili `--oblik csv` i `--datoteka` s nazivom datoteke. JSON datoteku mogu
čitati drugi programi; CSV datoteka otvara se u programu za tablice.

```bash
uz pretraži 103/2 -ko SAVAR --oblik csv --datoteka parcel.csv
```

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `BROJ_ČESTICE` | Vrijednost koju upisujete odmah iza naziva naredbe, bez naziva ispred nje | Obavezno |
| `--općina`, `-ko` `TEKST` | Naziv ili šifra općine (npr. SAVAR ili 334979) | Obavezno |
| `--točno` / `--djelomično` | Točno podudaranje ili djelomična pretraga | Koristi se `--točno` |
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako broj čestice ne postoji u toj općini, alat to kaže i staje:

<!-- BEGIN GENERATED: output uz pretraži 999 -ko SAVAR -->
```text
✗ Greška: Čestica '999' nije pronađena u općini 334979
```
<!-- END GENERATED: output -->

Provjerite broj na svom dokumentu. Brojevi čestica često sadrže kosu crtu, a 103
nije ista čestica kao 103/2.

Ako općina nije prepoznata, poruka je imenuje. Provjerite pravopis ili umjesto
naziva upotrijebite šifru. Ostale poruke objašnjene su na [stranici o
greškama](../errors.md).

## Povezane stranice

- [čestica](get-parcel.md) prikazuje sve što katastar ima o čestici, uključujući
  upisane posjednike.
- [uložak](get-lr-unit.md) prikazuje zemljišnoknjižni uložak: vlasnike, udjele i
  terete.
- [traži-općinu](search-municipality.md) pronalazi šifru katastarske općine.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz pretraži --help`:

```text
Uporaba: uz pretraži [OPCIJE] BROJ_ČESTICE

  Brzo pretraživanje čestica s osnovnim podacima.

  Primjeri:
    uz pretraži 103/2 --općina SAVAR
    uz pretraži 103/2 -ko 334979
    uz pretraži 114 -ko 334979 --djelomično

Opcije:
  -ko, --općina TEKST             Naziv ili šifra općine (npr. SAVAR ili 334979)
                                  [obavezno]
  --točno / --djelomično          Točno podudaranje ili djelomična pretraga
  -ob, --oblik [tablica|json|csv]
                                  Format izlaza
  -dt, --datoteka PUTANJA         Spremi izlaz u datoteku
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
