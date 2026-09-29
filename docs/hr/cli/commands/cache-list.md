<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/cache-list.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Koje su općine pohranjene na vašem računalu

Podaci o granicama općine preuzimaju se jednom i zatim čuvaju na vašem računalu.
Ova naredba ispisuje što se čuva, koliko je veliko i kada je zadnji put
ažurirano.

## Kada vam ovo treba

- Želite znati ima li alat već podatke neke općine prije nego zatražite granicu.
- Želite vidjeti koliko prostora na disku zauzimaju pohranjeni podaci.

## Prije nego počnete

Ništa. Ova naredba ne traži unos i ništa ne mijenja.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz predmemorija popis
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz predmemorija popis -->
   ```text
   GIS podaci u predmemoriji (1 općina):

     Općina    Veličina    Zadnja izmjena
     334979      0.7 KB    2026-01-01 00:00

   Ukupna veličina predmemorije: 0.0 MB
   Lokacija predmemorije: ~/.cadastral_api_cache
   ```
   <!-- END GENERATED: output -->

4. Jedan redak po općini, s njezinom šifrom, veličinom podataka i datumom
   zadnjeg preuzimanja. Zadnji reci daju ukupnu veličinu i mapu u kojoj se
   podaci nalaze.

## Što možete odabrati

Nema ih.

<!-- BEGIN GENERATED: options -->
Ova naredba nema izbora. Upišite je kako jest.
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako još ništa nije preuzeto, alat kaže da je spremište prazno i predlaže naredbu
za preuzimanje. To nije greška.

## Povezane stranice

- [predmemorija info](cache-info.md) daje samo ukupne vrijednosti.
- [predmemorija obriši](cache-clear.md) briše pohranjene podatke.
- [preuzmi-gis](download-gis.md) dodaje općinu.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz predmemorija popis --help`:

```text
Uporaba: uz predmemorija popis [OPCIJE]

  Popis predmemoriranih općina.

  Primjer:
    uz predmemorija popis

Opcije:
  --help  Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
