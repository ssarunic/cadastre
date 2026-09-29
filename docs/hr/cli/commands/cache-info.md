<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/cache-info.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Koliko je podataka o granicama pohranjeno

Prikazuje mapu u kojoj alat čuva preuzete podatke o granicama, broj općina i
datoteka te ukupnu veličinu.

## Kada vam ovo treba

- Računalu nedostaje prostora na disku i želite znati koliko ga alat zauzima.
- Želite pronaći mapu da je sigurnosno kopirate ili predate kolegi.

## Prije nego počnete

Ništa. Ova naredba ne traži unos i ništa ne mijenja.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz predmemorija info
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz predmemorija info -->
   ```text
   INFORMACIJE O PREDMEMORIJI
   ==========================
   Lokacija: ~/.cadastral_api_cache
   Status: Aktivno
   Ukupna veličina: 0.00 MB
   Općine: 1
   ZIP datoteke: 1
   GML datoteke: 0

   Za popis općina u predmemoriji: cadastral cache list
   Za brisanje predmemorije: cadastral cache clear --all
   ```
   <!-- END GENERATED: output -->

4. **Lokacija** je mapa na vašem računalu. **Ukupna veličina** je zauzeti
   prostor na disku. Zadnja dva retka podsjećaju na naredbe kojima se podaci
   ispisuju i brišu.

## Što možete odabrati

Nema ih.

<!-- BEGIN GENERATED: options -->
Ova naredba nema izbora. Upišite je kako jest.
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ova naredba nema na čemu zapeti. Ako mapa još ne postoji, alat to kaže;
pokrenite bilo koji dohvat granice i mapa će biti stvorena.

## Povezane stranice

- [predmemorija popis](cache-list.md) ispisuje općine.
- [predmemorija obriši](cache-clear.md) briše pohranjene podatke.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz predmemorija info --help`:

```text
Uporaba: uz predmemorija info [OPCIJE]

  Prikaz detaljnih informacija o predmemoriji.

  Primjer:
    uz predmemorija info

Opcije:
  --help  Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
