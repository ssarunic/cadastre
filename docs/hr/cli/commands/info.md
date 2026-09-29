<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/info.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.3.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Provjera je li alat postavljen

Prikazuje verziju alata, poslužitelj s kojim razgovara i podatke o granicama
koje je pohranio na vašem računalu. To je prvo što pokrećete nakon instalacije i
prvo što pokrećete kad nešto ne radi.

## Kada vam ovo treba

- Alat je upravo instaliran i želite potvrditi da radi.
- Naredba nije uspjela i želite vidjeti je li alat usmjeren na pravi
  poslužitelj.

## Prije nego počnete

Ništa. Ova naredba ne traži unos i ništa ne mijenja.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz info
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz info -->
   ```text
   Hrvatski katastarski CLI
   ========================
   Verzija: 0.3.0
   API osnova: http://localhost:8000

   Informacije o predmemoriji
   ==========================
   Direktorij predmemorije: ~/.cadastral_api_cache
   Veličina predmemorije: 0.0 MB
   Općine u predmemoriji: 1
     • 334979 (0.7 KB)
   Predmemorija odgovora: memory, 0 unosa, 0.0 MB

   API postavke
   ============
   Ograničenje zahtjeva: 0.375 sekundi između zahtjeva
   Timeout: 10.0 sekundi
   Nepoznata polja poslužitelja: warn

   Za brisanje predmemorije: cadastral cache clear --all
   ```
   <!-- END GENERATED: output -->

4. **API osnova** je adresa poslužitelja s kojim alat razgovara. Za vježbu to je
   adresa probnog poslužitelja na vašem računalu. **Informacije o predmemoriji**
   ispisuje općine čiji su podaci o granicama pohranjeni na vašem računalu; alat
   tu pohranu naziva predmemorijom. Redak **Predmemorija odgovora** kaže čuvaju
   li se odgovori poslužitelja u memoriji dok naredba radi (čuvaju se, osim ako
   piše `off`). **API postavke** pokazuje koliko alat čeka između zahtjeva i
   koliko dugo čeka odgovor.

## Što možete odabrati

Nema ih. Ako alat ispiše ovaj zaslon, ispravno je instaliran.

<!-- BEGIN GENERATED: options -->
Ova naredba nema izbora. Upišite je kako jest.
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako Terminal kaže da naredba nije pronađena, alat nije instaliran za vaš
korisnički račun ili je Terminal otvoren prije nego što je instalacija završila.
Zatvorite Terminal, otvorite ga ponovno i pokušajte opet. Ako i dalje ne radi,
obratite se osobi koja je instalirala alat.

## Povezane stranice

- [predmemorija popis](cache-list.md) detaljnije prikazuje pohranjene podatke o
  granicama.
- [Počnite ovdje](../start-here.md) je vodič za početak.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz info --help`:

```text
Uporaba: uz info [OPCIJE]

  Prikaz informacija o sustavu i stanju predmemorije.

  Primjer:
    uz info

Opcije:
  --help  Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
