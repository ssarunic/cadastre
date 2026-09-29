<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/search-municipality.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Matični broj katastarske općine

Svaka katastarska općina (k.o.) ima matični broj, koji alat ispisuje kao šifru.
Ova je naredba pronalazi iz naziva ili ispisuje općine koje pripadaju nekom
katastarskom uredu.

## Kada vam ovo treba

- Dvije općine imaju isti ili sličan naziv i želite biti sigurni koju gledate.
- Naredba je odbila naziv općine i umjesto njega trebate šifru.
- Želite znati kojem područnom uredu za katastar i odjelu općina pripada.

## Prije nego počnete

Trebate naziv općine ili njegov dio.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz traži-općinu SAVAR
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz traži-općinu SAVAR -->
   ```text
   Pronađeno 1 općina (search='SAVAR'):

   +---------+---------+--------+---------+
   |   Šifra | Naziv   |   Ured |   Odjel |
   +=========+=========+========+=========+
   |  334979 | SAVAR   |    114 |     116 |
   +---------+---------+--------+---------+
   ```
   <!-- END GENERATED: output -->

4. **Šifra** je matični broj koji svakoj drugoj naredbi možete zadati iza `-ko`.
   **Ured** i **Odjel** su brojevi katastarskog ureda i njegova odjela.

## Što možete odabrati

Da ispišete sve općine jednog ureda, zadajte broj ureda uz `--ured`. Možete ga
kombinirati s nazivom da suzite popis:

```bash
uz traži-općinu --ured 114
```

Ako samo želite znati koliko se općina podudara, dodajte `--samo-broj`. Da popis
spremite u datoteku, dodajte `--oblik csv` i `--datoteka` s nazivom datoteke.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `POJAM` | Neobavezno. Vrijednost koju upisujete odmah iza naziva naredbe | Ne koristi se |
| `--ured`, `-ur` `TEKST` | Filtriraj prema ID-u katastarskog ureda (npr. 114) | Ne koristi se |
| `--odjel`, `-od` `TEKST` | Filtriraj prema ID-u odjela (npr. 116) | Ne koristi se |
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--samo-broj` | Prikaži samo broj | Nije uključeno |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako se ništa ne podudara, vidjet ćete ovo:

<!-- BEGIN GENERATED: output uz traži-općinu NOWHERE -->
```text
✗ Greška: Nema pronađenih općina za 'NOWHERE'
```
<!-- END GENERATED: output -->

Pokušajte s kraćim dijelom naziva, ili ispišite cijeli ured uz `--ured` i
potražite naziv na popisu. Ostale poruke objašnjene su na [stranici o
greškama](../errors.md).

## Povezane stranice

- [općine](list-municipalities.md) radi isti posao s drukčijim filtrima.
- [uredi](list-offices.md) prikazuje brojeve ureda za `--ured`.
- [pretraži](search.md) je mjesto gdje pronađenu šifru koristite.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz traži-općinu --help`:

```text
Uporaba: uz traži-općinu [OPCIJE] POJAM

  Pretraživanje i filtriranje općina.

  Primjeri:
    uz traži-općinu SAVAR
    uz traži-općinu --ured 114
    uz traži-općinu --ured 114 --odjel 116
    uz traži-općinu SAVAR --ured 114

Opcije:
  -ur, --ured TEKST               Filtriraj prema ID-u katastarskog ureda (npr.
                                  114)
  -od, --odjel TEKST              Filtriraj prema ID-u odjela (npr. 116)
  -ob, --oblik [tablica|json|csv]
                                  Format izlaza
  -dt, --datoteka PUTANJA         Spremi izlaz u datoteku
  --samo-broj                     Prikaži samo broj
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
